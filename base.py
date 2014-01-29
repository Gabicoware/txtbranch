# -*- coding: utf-8 -*-
import logging
import webapp2
from webapp2_extras import auth, sessions, jinja2
from jinja2.runtime import TemplateNotFound
from google.appengine.api import users


class BaseRequestHandler(webapp2.RequestHandler):
        
    def controller(self,controllerClass):
        controller = controllerClass();
        user_dict = self.auth.get_user_by_session()
        if user_dict is not None:
                controller.oauth_user_id = user_dict['user_id']
        google_user = users.get_current_user()
        if user_dict is not None:
                controller.google_user = google_user
        return controller
    
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
    
    @webapp2.cached_property    
    def jinja2(self):
        """Returns a Jinja2 renderer cached in the app registry"""
        return jinja2.get_jinja2(app=self.app)
        
    @webapp2.cached_property
    def session(self):
        """Returns a session using the default cookie key"""
        return self.session_store.get_session()
        
    @webapp2.cached_property
    def auth(self):
            return auth.get_auth()
    
    @webapp2.cached_property
    def current_user(self):
        """Returns currently logged in user"""
        user_dict = self.auth.get_user_by_session()
        return self.auth.store.user_model.get_by_id(user_dict['user_id'])
            
    @webapp2.cached_property
    def logged_in(self):
        """Returns true if a user is currently logged in, false otherwise"""
        return self.auth.get_user_by_session() is not None
    
            
    def render(self, template_name, template_vars={}):
        # Preset values for the template
        values = {
            'url_for': self.uri_for,
            'logged_in': self.logged_in,
            'flashes': self.session.get_flashes()
        }
        
        # Add manually supplied template values
        values.update(template_vars)
        
        # read the template or 404.html
#        try:
        self.response.write(self.jinja2.render_template(template_name, **values))
#        except TemplateNotFound:
#            self.abort(404)

    def head(self, *args):
        """Head is used by Twitter. If not there the tweet button shows 0"""
        pass
