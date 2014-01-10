
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



class MockBranchHandler(webapp2.RequestHandler):
    
    def get(self):
        
        template_values = self.template_values()
                
        template = JINJA_ENVIRONMENT.get_template('branch.html')
        self.response.write(template.render(template_values))
    
    def post(self):
        self.get(self)
    
    def template_values(self):
        branch = Branch()
        branch.link = "Here is a mock branch link"
        branch.content = "Here is a mock branch content"
    
        parent_branch = Branch()
        parent_branch.link = "Here is a mock parent branch link"
        parent_branch.content = "Here is a mock parent branch content"
    
        result = {
            'parent_href': self.request.uri,
            'parent_branch': parent_branch,
            'branch_href': self.request.uri,
            'branch': branch,
            'child_count': 0,
            'like_value': 0,
            'like_count': 0,
            'unlike_count': 0,
            'has_branch_links' : False,
            'branch_links': [],
            'link_max' : config["branchs"]["link_max"],
            'content_max' : config["branchs"]["content_max"],
            'depth_max' : config["branchs"]["depth_max"],
            'add_branch_url': self.request.uri,
            'session_info': SessionLink.session_info(self.request.uri),
            'at_depth_max': False,
        }
        
        return result
        
class MockBranchDepthLimitHandler(MockBranchHandler):

    def template_values(self):
        result = super(MockBranchDepthLimitHandler, self).template_values()
        
        result['at_depth_max'] = True
        
        return result
        
class MockBranchIdenticalLinkHandler(MockBranchHandler):

    def template_values(self):
        result = super(MockBranchIdenticalLinkHandler, self).template_values()
        
        result['identical_link'] = True
        
        return result
        

handlers = [
    ('/mock/branch/depth_max', MockBranchDepthLimitHandler),
    ('/mock/branch/identical_link', MockBranchIdenticalLinkHandler),
    ('/mock/branch', MockBranchHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)