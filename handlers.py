#TODO AUTOMATICALLY TEST SYSTEM LIMITS

#TODO: figure out limits to branch count

#TODO: Ranking algorithm

import json
import threading
import base
from simpleauth import SimpleAuthHandler

import secrets
from defaulttext import *
from models import *
from controllers import TreeController, BaseController
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

class CreateTreeHandler(RequestHandler):
    
    _create_tree_lock = threading.Lock()
    
    def get(self):
        self.render_create_tree_form()
        
    def post(self):
        tree_name = self.request.get('tree_name',config['trees']['default_name'])
        
        success, tree = self.controller(TreeController).save_tree(tree_name,
          self.username(),
          self.request.get('conventions', DEFAULT_CONVENTIONS),
          self.request.get('root_branch_link',''),
          self.request.get('root_branch_content',''))
        
        if success:
            redirect_url = '/tree/' + tree_name
            self.redirect(redirect_url)
        else:
            self.render_create_tree_form(tree)
    
    def render_create_tree_form(self,errors=None):
        template_vars = {
            'conventions' : self.request.get('conventions', DEFAULT_CONVENTIONS),

            'tree_name' : self.request.get('tree_name', ''),
            'root_branch_link' : self.request.get('root_branch_link', ''),
            'root_branch_content' : self.request.get('root_branch_content', ''),
            
            'new_tree_endpoint' : self.request.uri,
            'link_max' : config["branchs"]["link_max"],
            'content_max' : config["branchs"]["content_max"],
            'errors' : json.dumps(errors),
        }
        
        self.render('new_tree.html', template_vars)

class EditTreeHandler(RequestHandler):
    
    def get(self,tree_name):
        tree = Tree.get_by_name(tree_name)
        if tree == None:
            return self.redirect('/')
        elif tree.moderatorname != self.username():
            return self.redirect('/tree/'+tree_name)
        
        self.render_edit_tree_form(tree)
        
    def post(self,tree_name):
        
        tree = Tree.get_by_name(tree_name)
        
        success, result = self.controller(TreeController).update_tree(
          tree,
          self.username(),
          self.request.get('conventions'))
        
        if success:
            self.render_edit_tree_form(tree)
        else:
            self.render_edit_tree_form(tree, errors=result)
            
    def render_edit_tree_form(self,tree,errors=None):
        template_values = {
            'conventions' : self.request.get('conventions', tree.conventions),
            'tree_name' : tree.name,
            'edit_tree_endpoint' : self.request.uri,
            'errors' : json.dumps(errors),
        }
        self.render('edit_tree.html',template_values)
         
class TreeHandler(RequestHandler):
    def get(self, tree_name):
        
        key = Tree.create_key(tree_name)
        
        tree = key.get()
        
        if tree:
        
            
            template_values = {
                'root_branch_key': tree.get_root_branch_key(),
                'tree': tree,
                'link_max' : config["branchs"]["link_max"],
                'content_max' : config["branchs"]["content_max"],
            }
            
            self.render('tree.html',template_values)
        else:
            template_values = {
                'tree_name': tree_name,
            }
            self.response.status = 404
            self.render('tree_not_found.html',template_values)
        
class AboutHandler(RequestHandler):

    def get(self):
        self.render('about.html',{})

class UserHandler(RequestHandler):
    
    def get(self,username):
        
        
        user_info_key = ndb.Key('UserInfo',username)
        
        user_info = user_info_key.get()
        
        if user_info is None:
            user_info = UserInfo(id=user_info_key.string_id())
            user_info.put()
        
        branchs = user_info.branchs()
        branch_branchs = user_info.branch_branchs()
        
        template_values = {
            'branchs' : branchs,
            'branch_branchs' : branch_branchs,
            'user_info' : user_info,
        }
        self.render('user.html',template_values)
                            
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
                self.auth.store.user_to_dict(user))
            
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
            self._set_username_cookie(user_info)
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
            self._set_username_cookie(user_info)
            
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
    def _set_username_cookie(self,user_info):
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=28)
        then = delta + now
        
        self.response.set_cookie('username',value=user_info.username,expires=then)
