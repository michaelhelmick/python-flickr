#!/usr/bin/env python

""" Python-Flickr """
'''
For Flickr API documentation, visit: http://www.flickr.com/services/api/
'''

__author__ = 'Mike Helmick <mikehelmick@me.com>'
__version__ = '0.2.0'

import urllib
import urllib2
import mimetypes
import mimetools
import codecs
from io import BytesIO

import httplib2
import oauth2 as oauth


try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except ImportError:
            raise ImportError('A json library is required to use this python library. Lol, yay for being verbose. ;)')


# We need to import a XML Parser because Flickr doesn't return JSON for photo uploads -_-
try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                #normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    print("Failed to import ElementTree from any known place")

writer = codecs.lookup('utf-8')[3]


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def iter_fields(fields):
    """Iterate over fields.

    Supports list of (k, v) tuples and dicts.
    """
    if isinstance(fields, dict):
        return ((k, v) for k, v in fields.iteritems())
    return ((k, v) for k, v in fields)


class FlickrAPIError(Exception):
    """ Generic error class, catch-all for most Tumblpy issues.

        from Tumblpy import FlickrAPIError, FlickrAuthError
    """
    def __init__(self, msg, error_code=None):
        self.msg = msg
        self.code = error_code
        if error_code is not None and error_code < 100:
            raise FlickrAuthError(msg, error_code)

    def __str__(self):
        return repr(self.msg)


class FlickrAuthError(FlickrAPIError):
    """ Raised when you try to access a protected resource and it fails due to some issue with your authentication. """
    def __init__(self, msg, error_code=None):
        self.msg = msg
        self.code = error_code

    def __str__(self):
        return repr(self.msg)


class FlickrAPI(object):
    def __init__(self, api_key=None, api_secret=None, oauth_token=None, oauth_token_secret=None, callback_url=None, headers=None, client_args=None):
        if not api_key or not api_secret:
            raise FlickrAPIError('Please supply an api_key and api_secret.')

        self.api_key = api_key
        self.api_secret = api_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.callback_url = callback_url

        self.api_base = 'http://api.flickr.com/services'
        self.rest_api_url = '%s/rest' % self.api_base
        self.upload_api_url = '%s/upload/' % self.api_base
        self.request_token_url = 'http://www.flickr.com/services/oauth/request_token'
        self.access_token_url = 'http://www.flickr.com/services/oauth/access_token'
        self.authorize_url = 'http://www.flickr.com/services/oauth/authorize'

        self.headers = headers
        if self.headers is None:
            self.headers = {'User-agent': 'Python-Flickr v%s' % __version__}

        self.consumer = None
        self.token = None

        client_args = client_args or {}

        if self.api_key is not None and self.api_secret is not None:
            self.consumer = oauth.Consumer(self.api_key, self.api_secret)

        if self.oauth_token is not None and self.oauth_token_secret is not None:
            self.token = oauth.Token(oauth_token, oauth_token_secret)

        # Filter down through the possibilities here - if they have a token, if they're first stage, etc.
        if self.consumer is not None and self.token is not None:
            self.client = oauth.Client(self.consumer, self.token, **client_args)
        elif self.consumer is not None:
            self.client = oauth.Client(self.consumer, **client_args)
        else:
            # If they don't do authentication, but still want to request unprotected resources, we need an opener.
            self.client = httplib2.Http(**client_args)

    def get_authentication_tokens(self, perms=None):
        """ Returns an authorization url to give to your user.

            Parameters:
            perms - If None, this is ignored and uses your applications default perms. If set, will overwrite applications perms; acceptable perms (read, write, delete)
                        * read - permission to read private information
                        * write - permission to add, edit and delete photo metadata (includes 'read')
                        * delete - permission to delete photos (includes 'write' and 'read')
        """

        request_args = {}
        resp, content = self.client.request('%s?oauth_callback=%s' % (self.request_token_url, self.callback_url), 'GET', **request_args)

        if resp['status'] != '200':
            raise FlickrAuthError('There was a problem retrieving an authentication url.')

        request_tokens = dict(parse_qsl(content))

        auth_url_params = {
            'oauth_token': request_tokens['oauth_token']
        }

        accepted_perms = ('read', 'write', 'delete')
        if perms and perms in accepted_perms:
            auth_url_params['perms'] = perms

        request_tokens['auth_url'] = '%s?%s' % (self.authorize_url, urllib.urlencode(auth_url_params))
        return request_tokens

    def get_auth_tokens(self, oauth_verifier):
        """ Returns 'final' tokens to store and used to make authorized calls to Flickr.

            Parameters:
                oauth_token - oauth_token returned from when the user is redirected after hitting the get_auth_url() function
                verifier - oauth_verifier returned from when the user is redirected after hitting the get_auth_url() function
        """

        params = {
            'oauth_verifier': oauth_verifier,
        }

        resp, content = self.client.request('%s?%s' % (self.access_token_url, urllib.urlencode(params)), 'GET')
        if resp['status'] != '200':
            raise FlickrAuthError('Getting access tokens failed: %s Response Status' % resp['status'])

        return dict(parse_qsl(content))

    def api_request(self, endpoint=None, method='GET', params={}, files=None):
        self.headers.update({'Content-Type': 'application/json'})

        if endpoint is None and files is None:
            raise FlickrAPIError('Please supply an API endpoint to hit.')

        qs = {
            'format': 'json',
            'nojsoncallback': 1,
            'method': endpoint,
            'api_key': self.api_key
        }

        if method == 'POST':

            if files is not None:
                # When uploading a file, we need to create a fake request
                # to sign parameters that are not multipart before we add
                # the multipart file to the parameters...
                # OAuth is not meant to sign multipart post data
                faux_req = oauth.Request.from_consumer_and_token(self.consumer,
                                                                 token=self.token,
                                                                 http_method="POST",
                                                                 http_url=self.upload_api_url,
                                                                 parameters=params)

                faux_req.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                                      self.consumer,
                                      self.token)

                all_upload_params = dict(parse_qsl(faux_req.to_postdata()))

                # For Tumblr, all media (photos, videos)
                # are sent with the 'data' parameter
                all_upload_params['photo'] = (files.name, files.read())
                body, content_type = self.encode_multipart_formdata(all_upload_params)

                self.headers.update({
                    'Content-Type': content_type,
                    'Content-Length': str(len(body))
                })

                req = urllib2.Request(self.upload_api_url, body, self.headers)
                try:
                    req = urllib2.urlopen(req)
                except urllib2.HTTPError, e:
                    # Making a fake resp var because urllib2.urlopen doesn't
                    # return a tuple like OAuth2 client.request does
                    resp = {'status': e.code}
                    content = e.read()

                # If no error, assume response was 200
                resp = {'status': 200}

                content = req.read()
                content = etree.XML(content)

                stat = content.get('stat') or 'ok'

                if stat == 'fail':
                    if content.find('.//err') is not None:
                        code = content.findall('.//err[@code]')
                        msg = content.findall('.//err[@msg]')

                        if len(code) > 0:
                            if len(msg) == 0:
                                msg = 'An error occurred making your Flickr API request.'
                            else:
                                msg = msg[0].get('msg')

                            code = int(code[0].get('code'))

                            content = {
                                'stat': 'fail',
                                'code': code,
                                'message': msg
                            }
                else:
                    photoid = content.find('.//photoid')
                    if photoid is not None:
                        photoid = photoid.text

                    content = {
                        'stat': 'ok',
                        'photoid': photoid
                    }

            else:
                url = self.rest_api_url + '?' + urllib.urlencode(qs)
                resp, content = self.client.request(url, 'POST', urllib.urlencode(params), headers=self.headers)
                print content
        else:
            params.update(qs)
            resp, content = self.client.request('%s?%s' % (self.rest_api_url, urllib.urlencode(params)), 'GET', headers=self.headers)

        #try except for if content is able to be decoded
        try:
            if type(content) != dict:
                content = json.loads(content)
        except ValueError:
            raise FlickrAPIError('Content is not valid JSON, unable to be decoded.')

        status = int(resp['status'])
        if status < 200 or status >= 300:
            raise FlickrAPIError('Flickr returned a Non-200 response.', error_code=status)

        if content.get('stat') and content['stat'] == 'fail':
            raise FlickrAPIError('Flickr returned error code: %d. Message: %s' % \
                                (content['code'], content['message']),
                                error_code=content['code'])

        return dict(content)

    def get(self, endpoint=None, params=None):
        params = params or {}
        return self.api_request(endpoint, method='GET', params=params)

    def post(self, endpoint=None, params=None, files=None):
        params = params or {}
        return self.api_request(endpoint, method='POST', params=params, files=files)

    # Thanks urllib3 <3
    def encode_multipart_formdata(self, fields, boundary=None):
        """
        Encode a dictionary of ``fields`` using the multipart/form-data mime format.

        :param fields:
            Dictionary of fields or list of (key, value) field tuples.  The key is
            treated as the field name, and the value as the body of the form-data
            bytes. If the value is a tuple of two elements, then the first element
            is treated as the filename of the form-data section.

            Field names and filenames must be unicode.

        :param boundary:
            If not specified, then a random boundary will be generated using
            :func:`mimetools.choose_boundary`.
        """
        body = BytesIO()
        if boundary is None:
            boundary = mimetools.choose_boundary()

        for fieldname, value in iter_fields(fields):
            body.write('--%s\r\n' % (boundary))

            if isinstance(value, tuple):
                filename, data = value
                writer(body).write('Content-Disposition: form-data; name="%s"; '
                                   'filename="%s"\r\n' % (fieldname, filename))
                body.write('Content-Type: %s\r\n\r\n' %
                           (get_content_type(filename)))
            else:
                data = value
                writer(body).write('Content-Disposition: form-data; name="%s"\r\n'
                                   % (fieldname))
                body.write(b'Content-Type: text/plain\r\n\r\n')

            if isinstance(data, int):
                data = str(data)  # Backwards compatibility

            if isinstance(data, unicode):
                writer(body).write(data)
            else:
                body.write(data)

            body.write(b'\r\n')

        body.write('--%s--\r\n' % (boundary))

        content_type = 'multipart/form-data; boundary=%s' % boundary

        return body.getvalue(), content_type
