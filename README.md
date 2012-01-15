#Overview
I've been writing up APIs interfacing with OAuth in Python like no other the past week or so, so here is another... Flickr API.

Hope this documentation explains everything you need to get started. Any questions feel free to email me or inbox me.

#Authorization URL
*Get an authorization url for your user*

```python
f = FlickrAPI(api_key='*your app key*',
              api_secret='*your app secret*',
              callback_url='http://www.example.com/callback/')

auth_props = f.get_authentication_tokens()
auth_url = auth_props['auth_url']

#Store this token in a session or something for later use in the next step.
oauth_token_secret = auth_props['oauth_token_secret']

print 'Connect with Flickr via: %s' % auth_url
```

Once you click "Allow" be sure that there is a URL set up to handle getting finalized tokens and possibly adding them to your database to use their information at a later date. \n\n'

#Handling the callback
```python
# In Django, you'd do something like
# oauth_token = request.GET.get('oauth_verifier')
# oauth_verifier = request.GET.get('oauth_verifier')

oauth_token = *Grab oauth token from URL*
oauth_verifier = *Grab oauth verifier from URL*

#Initiate the FlickrAPI class in your callback.
f = FlickrAPI(api_key='*your app key*',
              api_secret='*your app secret*',
              oauth_token=oauth_token,
              oauth_token_secret=session['flickr_session_keys']['oauth_token_secret'])

authorized_tokens = f.get_auth_tokens(oauth_verifier)

final_oauth_token = authorized_tokens['oauth_token']
final_oauth_token_secret = authorized_tokens['oauth_token_secret']

# Save those tokens to the database for a later use?
```

#Getting some user information & adding comments to photos.
```python
# Get the final tokens from the database or wherever you have them stored

f = FlickrAPI(api_key = '*your app key*',
              api_secret = '*your app secret*',
              oauth_token=final_tokens['oauth_token'],
              oauth_token_secret=final_tokens['oauth_token_secret'])

# Return the users recent activity feed.
recent_activity = f.get('flickr.activity.userComments')
print recent_activity

# Add comment on a photo
add_comment = f.post('flickr.photos.comments.addComment', params={'photo_id':'6620847285', 'comment_text':'This is a test comment.'})

#This returns the comment id if successful.
print add_comment

# Remove comment on a photo
# If the comment is already deleted, it will throw a FlickrAPIError (In this case, with code 2: Comment not found.)
del_comment = f.post('flickr.photos.comments.deleteComment', params={'comment_id':'45887890-6620847285-72157628767110559'})
print del_comment
```

#Uploading a Photo
```python
f = FlickrAPI(api_key = '*your app key*',
              api_secret = '*your app secret*',
              oauth_token=final_tokens['oauth_token'],
              oauth_token_secret=final_tokens['oauth_token_secret'])

f.post(params={'title':'Test Title!'}, files='/path/to/image.jpg')
```