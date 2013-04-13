#!/usr/bin/env python

""" Python-Flickr """
'''
For Flickr API documentation, visit: https://www.flickr.com/services/api/
'''

__author__ = 'Mike Helmick <mikehelmick@me.com>'
__version__ = '0.4.0'

import urllib

import requests
from requests_oauthlib import OAuth1

try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

try:
    import simplejson as json
except ImportError:
    import json


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
    def __init__(self, api_key=None, api_secret=None, oauth_token=None, oauth_token_secret=None, headers=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret

        self.api_base = 'https://api.flickr.com/services'
        self.up_api_base = 'https://up.flickr.com/services'
        self.rest_api_url = '%s/rest' % self.api_base

        self.upload_api_url = '%s/upload/' % self.api_base
        self.replace_api_url = '%s/replace/' % self.api_base

        self.request_token_url = '%s/oauth/request_token' % self.api_base
        self.access_token_url = '%s/oauth/access_token' % self.api_base
        self.authorize_url = '%s/oauth/authorize' % self.api_base

        # If there's headers, set them, otherwise be an embarassing parent for their own good.
        self.headers = headers or {'User-Agent': 'Python-Flickr v' + __version__}

        # Allow for unauthenticated requests
        self.client = requests.Session()
        self.auth = None

        if self.api_key is not None and self.api_secret is not None and \
           self.oauth_token is None and self.oauth_token_secret is None:
            self.auth = OAuth1(self.api_key, self.app_secret,
                               signature_type='auth_header')

        if self.api_key is not None and self.api_secret is not None and \
           self.oauth_token is not None and self.oauth_token_secret is not None:
            self.auth = OAuth1(self.api_key, self.api_secret,
                               self.oauth_token, self.oauth_token_secret,
                               signature_type='auth_header')

        if self.auth is not None:
            self.client = requests.Session()
            self.client.headers = self.headers
            self.client.auth = self.auth

    def __repr__(self):
        return u'<FlickrAPI: %s>' % self.api_key

    def get_authentication_tokens(self, callback_url, perms=None):
        """ Returns request tokens including an authorization url to give to your user.

            :param callback_url: (required) The URL the user will be directed to - to authorize using your application
            :param perms: (optional) If None, this is ignored and uses your applications default perms. If set, will overwrite applications perms; acceptable perms (read, write, delete)
                        * read - permission to read private information
                        * write - permission to add, edit and delete photo metadata (includes 'read')
                        * delete - permission to delete photos (includes 'write' and 'read')
        """

        response = self.client.get(self.request_token_url, params={'oauth_callback': callback_url})

        if response.status_code != 200:
            raise FlickrAuthError(response.content)

        request_tokens = dict(parse_qsl(response.content))

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

            :param oauth_token: (required) oauth_verifier returned in the url from when the user is redirected after hitting the get_auth_url() function
        """

        params = {
            'oauth_verifier': oauth_verifier,
        }

        response = self.client.get(self.access_token_url, params=params)
        if response.status_code != 200:
            raise FlickrAuthError(response.content)

        return dict(parse_qsl(response.content))

    def request(self, endpoint, method='GET', params={}, files=None, replace=False):
        #if endpoint is None and files is None:
        #   raise FlickrAPIError('Please supply an API endpoint to hit.')

        method = method.lower()
        if not method in ('get', 'post'):
            raise FlickrAPIError('Method must be of GET or POST')

        params = params or {}
        params.update({
            'format': 'json',
            'nojsoncallback': 1,
            'method': endpoint,
            'api_key': self.api_key
        })
        # requests doesn't like items that can't be converted to unicode,
        # so let's be nice and do that for the user
        for k, v in params.items():
            if isinstance(v, (int, bool)):
                params[k] = u'%s' % v

        if not files:
            url = self.rest_api_url
        else:
            url = self.replace_api_url if replace else self.upload_api_url

        func = getattr(self.client, method)
        if method == 'get':
            response = func(url, params=params)
        else:
            response = func(url, data=params, files=files)

        print response.content
        content = response.content.decode('utf-8')
        try:
            try:
                content = content.json()
            except AttributeError:
                content = json.loads(response.content)
        except ValueError:
            content = {}

        return content

    def get(self, endpoint, params=None):
        return self.request(endpoint, 'GET', params)

    def post(self, endpoint, params=None, files=None, replace=False):
        return self.request(endpoint, 'POST', params, files, replace)
