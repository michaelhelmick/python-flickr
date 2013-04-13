Python-Flickr
=============

Python-Flickr is A Python library to interface with `Flickr REST API <http://www.flickr.com/services/api/>`_ & OAuth

Features
--------

* Photo Uploading
* Retrieve user information
* Common Flickr methods
   - Add/edit/delete comments
   - Add/edit/delete notes
   - And many more (very dynamic library)!!
* All responses return as nice dicts

Installation
------------

Installing Python-Flickr is simple: ::

    $ pip install python-flickr

Usage
-----

Authorization URL
~~~~~~~~~~~~~~~~~
::

    f = FlickrAPI('YOUR_APP_KEY', 'YOUR_APP_SECRET')

    auth_props = f.get_authentication_tokens('http://www.example.com/callback/')
    auth_url = auth_props['auth_url']

You set a permission (read, write, or delete) in your application settings,
if you wish to override the permission you can pass a second argument to the ``get_authenticaation_tokens`` method

::

    f = FlickrAPI('YOUR_APP_KEY', 'YOUR_APP_SECRET')

    auth_props = f.get_authentication_tokens('http://www.example.com/callback/', perms='delete')
    auth_url = auth_props['auth_url']


::
    # Store the oauth_token_secret from auth_props in a session var or something for later use in the next step
    # in Django, you'd do something like this
    # request.session['oauth_token_secret'] = auth_props['oauth_token_secret']

    print 'Connect with Flickr via: %s' % auth_url

Once the user clicks "Ok, I'll Authorize It" be sure that there is a URL set up to handle getting finalized tokens and possibly adding them to your database to use their information at a later date.


Handling the Callback
~~~~~~~~~~~~~~~~~~~~~
::

    # oauth_token_secret come from the previous step
    # oauth_token and oauth_verifier can be found in the query string

    # in Django, you'd do something like this
    # oauth_verifier = request.GET.get('oauth_verifier')
    # oauth_token = request.GET.get('oauth_token')
    # oauth_token_secret = request.session.get('oauth_token_secret')

    f = FlickrAPI('YOUR_APP_KEY', 'YOUR_APP_SECRET',
                  oauth_token, oauth_token_secret)

    authorized_tokens = f.get_auth_tokens(oauth_verifier)

    final_oauth_token = authorized_tokens['oauth_token']
    final_oauth_token_secret = authorized_tokens['oauth_token_secret']

    # Save those tokens to the database for a later use!


Getting the Users recent activity feed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    # Get the final tokens from the database or wherever you have them stored

    f = FlickrAPI('YOUR_APP_KEY', 'YOUR_APP_SECRET',
                  final_tokens['oauth_token'], final_tokens['oauth_token_secret'])

    recent_activity = f.get('flickr.activity.userComments')
    print recent_activity


Add comment on a photo
~~~~~~~~~~~~~~~~~~~~~~
::

    # Assume you are using the FlickrAPI instance from the previous section

    add_comment = f.post('flickr.photos.comments.addComment',
                         params={'photo_id': '6620847285', 'comment_text': 'This is a test comment.'})

    #This returns the comment id if successful.
    print add_comment


Remove comment on a photo
~~~~~~~~~~~~~~~~~~~~~~~~~
::

    # Assume you are using the FlickrAPI instance from the previous section
    # If the comment is already deleted, it will throw a FlickrAPIError (In this case, with code 2: Comment not found.)

    del_comment = f.post('flickr.photos.comments.deleteComment', params={'comment_id':'45887890-6620847285-72157628767110559'})
    print del_comment


Upload a photo
~~~~~~~~~~~~~~
::

    # Assume you are using the FlickrAPI instance from the previous section

    files = open('/path/to/file/image.jpg', 'rb')
    add_photo = f.post(params={'title':'Test Title!'}, files=files)

    print add_photo  # Returns the photo id of the newly added photo


Catching errors
~~~~~~~~~~~~~~~
::

    # Assume you are using the FlickrAPI instance from the previous section

    try:
        # This comment was already deleted
        del_comment = f.post('flickr.photos.comments.deleteComment', params={'comment_id':'45887890-6620847285-72157628767110559'})
    except FlickrAPIError, e:
        print e.msg
        print e.code
        print 'Something bad happened :('
