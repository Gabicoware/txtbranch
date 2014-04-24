#TODO AUTOMATICALLY TEST SYSTEM LIMITS

#TODO: figure out limits to branch count

#TODO: Ranking algorithm

import json
import threading
import base
from simpleauth import SimpleAuthHandler

import secrets
import logging
from models import Tree
from models import Branch
from controllers import BaseController
from google.appengine.api import users


class RequestHandler(base.BaseRequestHandler):
    def username(self):
        return self.request.cookies.get('username')

class MainHandler(RequestHandler):
    
    def get(self):
        
        trees = Tree.main_trees()
        branchdatas = Branch.get_first_branchs(trees)
        logging.info(trees)
        template_values = {
            'trees': trees,
            'branchdatas': branchdatas,
            'username': self.username()
        }
        
        self.render('main.html', template_values)

class TreeFormHandler(RequestHandler):
    
    def get(self):
        self.render('tree_form.html', {})
        
class TreeHandler(RequestHandler):
    def get(self, tree_name):
        
        self.render('tree.html',{})
        
class AboutHandler(RequestHandler):

    def get(self):
        self.render('about.html',{})

class UserHandler(RequestHandler):
    
    def get(self,username):
        self.render('user.html',{})
                            
class AuthHandler(RequestHandler, SimpleAuthHandler):
    """Authentication handler for OAuth 2.0, 1.0(a) and OpenID."""

    # Enable optional OAuth 2.0 CSRF guard
    OAUTH2_CSRF_STATE = True
    
    USER_ATTRS = {
        'facebook' : {
            'name'   : 'name',
            'link'   : 'link',
            '_attrs' : [
                ('id' , lambda id: ('avatar_url', 'http://graph.facebook.com/{0}/picture?type=large'.format(id)))
            ]
        },
        'google'   : {
            'picture': 'avatar_url',
            'name'   : 'name',
            'profile': 'link'
        },
        'windows_live': {
            'avatar_url': 'avatar_url',
            'name'      : 'name',
            'link'      : 'link'
        },
        'twitter'  : {
            'profile_image_url': 'avatar_url',
            'screen_name'      : 'name',
            'link'             : 'link'
        },
        'reddit'  : {
            'name'             : 'name',
            '_attrs'           : [
                  ('id', lambda id: ('avatar_url', '/img/missing-avatar.png') ),
                  ('name', lambda name: ('link', 'http://reddit.com/u/{0}'.format(name)) )
            ]
        },
        'linkedin' : {
            'picture-url'       : 'avatar_url',
            'first-name'        : 'name',
            'public-profile-url': 'link'
        },
        'linkedin2' : {
            'picture-url'       : 'avatar_url',
            'first-name'        : 'name',
            'public-profile-url': 'link'
        },
        'foursquare'   : {
            'firstName': 'firstName',
            'lastName' : 'lastName',
            '_attrs' : [
                ('photo'    , lambda photo: ('avatar_url', photo.get('prefix') + '100x100' + photo.get('suffix'))),
                ('contact'  , lambda contact: ('email',contact.get('email'))),
                ('id'       , lambda id: ('link', 'http://foursquare.com/user/{0}'.format(id))),
            ]
        },
        'openid'   : {
            'nickname': 'name',
            'email'   : 'link',
            '_attrs' : [
                ('id'      , lambda id: ('avatar_url', '/img/missing-avatar.png'))
            ]
        }
    }
    
    def _on_signin(self, data, auth_info, provider):
        """Callback whenever a new or existing user is logging in.
         data is a user info dictionary.
         auth_info contains access token or oauth token and secret.
        """
        auth_id = '%s:%s' % (provider, data['id'])
        logging.info('Looking for a user with id %s', auth_id)
        
        user = self.auth.store.user_model.get_by_auth_id(auth_id)
        _attrs = self._to_user_model_attrs(data, self.USER_ATTRS[provider])
        
        remember = True

        if user:
            logging.info('Found existing user to log in')
            # Existing users might've changed their profile data so we update our
            # local model anyway. This might result in quite inefficient usage
            # of the Datastore, but we do this anyway for demo purposes.
            #
            # In a real app you could compare _attrs with user's properties fetched
            # from the datastore and update local user in case something's changed.
            user.populate(**_attrs)
            user.put()
            self.auth.set_session(
                self.auth.store.user_to_dict(user), remember=remember)
            
        else:
            # check whether there's a user currently logged in
            # then, create a new user if nobody's signed in, 
            # otherwise add this auth_id to currently logged in user.

            if self.logged_in:
                logging.info('Updating currently logged in user')
                
                u = self.current_user
                u.populate(**_attrs)
                # The following will also do u.put(). Though, in a real app
                # you might want to check the result, which is
                # (boolean, info) tuple where boolean == True indicates success
                # See webapp2_extras.appengine.auth.models.User for details.
                u.add_auth_id(auth_id)
                
            else:
                logging.info('Creating a brand new user')
                ok, user = self.auth.store.user_model.create_user(auth_id, **_attrs)
                if ok:
                    self.auth.set_session(self.auth.store.user_to_dict(user))
        user_info = self.controller(BaseController).current_user_info()
        if user_info is not None:
            self._set_username_cookie(user_info,remember)
            #figure out where to send the user
            self.redirect('/')
        else:
            #create an account
            self.redirect('/post_login')

    def logout(self):
        self.auth.unset_session()
        self.response.delete_cookie('username')
        self.redirect('/')

    def login(self):
        self.render('login.html', {})
        
    def google_login(self):
        url = users.create_login_url('/post_login')
        self.redirect(url, permanent=True)
        
    def google_logout(self):
        url = users.create_logout_url('/')
        self.response.delete_cookie('username')
        self.redirect(url, permanent=True)
    
    def post_login(self):
                
        user_info = self.controller(BaseController).current_user_info()
        if user_info is None:
            self.render('post_login.html',{})
        else:
            #don't worry about redirects for now
            self._set_username_cookie(user_info, True)
            
            self.redirect('/')
            
    def handle_exception(self, exception, debug):
        logging.exception(exception)
        self.render('error.html', {'exception': exception})
        
    def _callback_uri_for(self, provider):
        return self.uri_for('auth_callback', provider=provider, _full=True)
        
    def _get_consumer_info_for(self, provider):
        """Returns a tuple (key, secret) for auth init requests."""
        return secrets.AUTH_CONFIG[provider]
        
    def _to_user_model_attrs(self, data, attrs_map):
        """Get the needed information from the provider dataset."""
        user_attrs = {}
        for k, v in attrs_map.iteritems():
            if k == '_attrs':
                for key, lamb in v:
                    attr = lamb(data.get(key))
            else:
                attr = (v, data.get(k))
            user_attrs.setdefault(*attr)

        return user_attrs
    def _set_username_cookie(self,user_info,remember):
        if remember:
            now = datetime.datetime.now()
            delta = datetime.timedelta(seconds=self.request.app.config['webapp2_extras.sessions']['cookie_args']['max_age'])
            logging.info(delta)
            then = delta + now
        else:
            then = None
        self.response.set_cookie('username',value=user_info.username,expires=then)
