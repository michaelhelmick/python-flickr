#!/usr/bin/env python

""" Python-Flickr """
'''
For Flickr API documentation, visit: http://www.flickr.com/services/api/
'''

__author__ = 'Mike Helmick <mikehelmick@me.com>'
__version__ = '0.1.0'

import time
import urllib
import urllib2
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

class FlickrAPIError(Exception): pass
class FlickrAuthError(FlickrAPIError): pass

class FlickrAPI(object):
    def __init__(self, api_key=None, api_secret=None, oauth_token=None, oauth_token_secret=None, callback_url=None, headers=None, client_args={}):
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

        self.default_params = {'api_key':self.api_key}

        self.headers = headers
        if self.headers is None:
            self.headers = {'User-agent': 'Python-Flickr v%s' % __version__}

        self.consumer = None
        self.token = None

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

    def get_auth_tokens(self, oauth_verifier=None):
        """ Returns 'final' tokens to store and used to make authorized calls to Flickr.

            Parameters:
                oauth_token - oauth_token returned from when the user is redirected after hitting the get_auth_url() function
                verifier - oauth_verifier returned from when the user is redirected after hitting the get_auth_url() function
        """

        if not oauth_verifier:
            raise FlickrAuthError('No OAuth Verifier supplied.')

        params = {
            'oauth_verifier': oauth_verifier,
        }

        resp, content = self.client.request('%s?%s' % (self.access_token_url, urllib.urlencode(params)), 'GET')
        if resp['status'] != '200':
            raise FlickrAuthError('Getting access tokens failed: %s Response Status' % resp['status'])

        return dict(parse_qsl(content))

    def api_request(self, endpoint=None, method='GET', params={}, format='json', files=None):
        self.headers.update({'Content-Type': 'application/json'})

        if endpoint is None and files is None:
            raise FlickrAPIError('Please supply an API endpoint to hit.')

        
        params.update(self.default_params)
        params.update({'method': endpoint, 'format':format})

        if format == 'json':
            params['nojsoncallback'] = 1

        if method == 'POST':
            oauth_params = {
                'oauth_version': "1.0",
                'oauth_nonce': oauth.generate_nonce(),
                'oauth_timestamp': int(time.time())
            }
            params.update(oauth_params)

            if files is not None:
                files = [('photo', files, open(files, 'rb').read())]
                
                #create a fake request with your upload url and parameters
                faux_req = oauth.Request(method='POST', url=self.upload_api_url, parameters=params)
        
                #sign the fake request.
                signature_method = oauth.SignatureMethod_HMAC_SHA1()
                faux_req.sign_request(signature_method, self.consumer, self.token)
        
                #create a dict out of the fake request signed params
                params = dict(parse_qsl(faux_req.to_postdata()))
        
                content_type, body = self.encode_multipart_formdata(params, files)
                headers = {'Content-Type': content_type, 'Content-Length': str(len(body))}
                r = urllib2.Request('%s' % self.upload_api_url, body, headers)
                return urllib2.urlopen(r).read()


            req = oauth.Request(method='POST', url=self.rest_api_url, parameters=params)

            ## Sign the request.
            signature_method = oauth.SignatureMethod_HMAC_SHA1()
            req.sign_request(signature_method, self.consumer, self.token)

            resp, content = self.client.request(req.to_url(), 'POST', body=req.to_postdata(), headers=self.headers)
        else:
            resp, content = self.client.request('%s?%s' % (self.rest_api_url, urllib.urlencode(params)), 'GET', headers=self.headers)
        
        status = int(resp['status'])
        if status < 200 or status >= 300:
            raise FlickrAPIError('Something when wrong making the request, returned a %d code.' % status)

        #try except for if content is able to be decoded
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            raise FlickrAPIError('Content is not valid JSON, unable to be decoded.')

        if content.get('stat') and content['stat'] == 'fail':
            raise FlickrAPIError('Something when wrong finishing the request. Flickr returned Error Code: %d. Message: %s' % (content['code'], content['message']))

        return dict(content)

    def get(self, endpoint=None, params={}):
        return self.api_request(endpoint, method='GET', params=params)

    def post(self, endpoint=None, params={}, files=None):
        return self.api_request(endpoint, method='POST', params=params, files=files)

    @staticmethod
    def encode_multipart_formdata(fields, files):
        import mimetools
        import mimetypes
        BOUNDARY = mimetools.choose_boundary()
        CRLF = '\r\n'
        L = []
        for (key, value) in fields.items():
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % mimetypes.guess_type(filename)[0] or 'application/octet-stream')
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body