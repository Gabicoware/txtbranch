
import cgi
import urllib
import os
import logging
import webapp2


from google.appengine.api import users

from defaulttext import *
from models import *
import jinja2
import uuid

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])



class MockPageHandler(webapp2.RequestHandler):
    
    def get(self):
        
        template_values = self.template_values()
                
        template = JINJA_ENVIRONMENT.get_template('page.html')
        self.response.write(template.render(template_values))
    
    def post(self):
        self.get(self)
    
    def template_values(self):
        page = Page()
        page.link = "Here is a mock page link"
        page.content = "Here is a mock page content"
    
        parent_page = Page()
        parent_page.link = "Here is a mock parent page link"
        parent_page.content = "Here is a mock parent page content"
    
        result = {
            'parent_href': self.request.uri,
            'parent_page': parent_page,
            'page_href': self.request.uri,
            'page': page,
            'child_count': 0,
            'like_value': 0,
            'like_count': 0,
            'unlike_count': 0,
            'has_page_links' : False,
            'page_links': [],
            'link_max' : config["pages"]["link_max"],
            'content_max' : config["pages"]["content_max"],
            'depth_max' : config["pages"]["depth_max"],
            'add_page_url': self.request.uri,
            'session_info': SessionLink.session_info(self.request.uri),
            'at_depth_max': False,
        }
        
        return result
        
class MockPageDepthLimitHandler(MockPageHandler):

    def template_values(self):
        result = super(MockPageDepthLimitHandler, self).template_values()
        
        result['at_depth_max'] = True
        
        return result
        
class MockPageIdenticalLinkHandler(MockPageHandler):

    def template_values(self):
        result = super(MockPageIdenticalLinkHandler, self).template_values()
        
        result['identical_link'] = True
        
        return result
        

handlers = [
    ('/mock/page/depth_max', MockPageDepthLimitHandler),
    ('/mock/page/identical_link', MockPageIdenticalLinkHandler),
    ('/mock/page', MockPageHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)