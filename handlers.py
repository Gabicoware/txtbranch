#TODO: USER CAN SUBMIT 1 BRANCH PER PARENT, and only after 5 minutes

#TODO AUTOMATICALLY TEST SYSTEM LIMITS

#TODO: Make adding a branch an in branch experience
#TODO: figure out limits to branch count

#TODO: Ranking algorithm

import os
import webapp2
import json
import datetime
import threading
import jinja2

from defaulttext import *
from models import *
from controllers import TreeController


class RequestHandler(webapp2.RequestHandler):
    def username(self):
        return self.request.cookies.get('username')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

class MainHandler(RequestHandler):
    
    def get(self):
        
        trees = Tree.main_trees()
        branchdatas = Branch.get_first_branchs(trees)
        logging.info(trees)
        template_values = {
            'trees': trees,
            'branchdatas': branchdatas,
            'username': self.username(),
            'session_info': UserInfo.session_info(self.username()),
        }
        
        template = JINJA_ENVIRONMENT.get_template('templates/main.html')
        self.response.write(template.render(template_values))
        # Write the submission form and the footer of the branch

class CreateTreeHandler(RequestHandler):
    
    _create_tree_lock = threading.Lock()
    
    def get(self):
        self.render_create_tree_form()
        
    def post(self):
        tree_name = self.request.get('tree_name',config['trees']['default_name'])
        
        success, tree = TreeController.save_tree(tree_name,
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
        template = JINJA_ENVIRONMENT.get_template('templates/new_tree.html')
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
            'conventions' : self.request.get('conventions', DEFAULT_CONVENTIONS),

            'tree_name' : self.request.get('tree_name', ''),
            'root_branch_link' : self.request.get('root_branch_link', ''),
            'root_branch_content' : self.request.get('root_branch_content', ''),
            
            'new_tree_endpoint' : self.request.uri,
            'link_max' : config["branchs"]["link_max"],
            'content_max' : config["branchs"]["content_max"],
            'errors' : json.dumps(errors),
        }
        self.response.write(template.render(template_values))
        

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
        
        success, result = TreeController.update_tree(
          tree,
          self.username(),
          self.request.get('conventions'))
        
        if success:
            self.render_edit_tree_form(tree)
        else:
            self.render_edit_tree_form(tree, errors=result)
            
    def render_edit_tree_form(self,tree,errors=None):
        template = JINJA_ENVIRONMENT.get_template('templates/edit_tree.html')
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
            'conventions' : self.request.get('conventions', tree.conventions),
            'tree_name' : tree.name,
            'edit_tree_endpoint' : self.request.uri,
            'errors' : json.dumps(errors),
        }
        self.response.write(template.render(template_values))
         
class TreeHandler(RequestHandler):
    def get(self, tree_name):
        
        key = Tree.create_key(tree_name)
        
        tree = key.get()
        
        if tree:
        
            root_branch = tree.get_root_branch()
            
            template_values = {
                'root_branch_key': root_branch.key,
                'tree': tree,
                'link_max' : config["branchs"]["link_max"],
                'content_max' : config["branchs"]["content_max"],
                'session_info': UserInfo.session_info(self.username()),
            }
            
            template = JINJA_ENVIRONMENT.get_template('templates/tree.html')
            self.response.write(template.render(template_values))
        else:
            template_values = {
                'tree_name': tree_name,
                'session_info': UserInfo.session_info(self.username()),
            }
            template = JINJA_ENVIRONMENT.get_template('templates/tree_not_found.html')
            self.response.status = 404
            self.response.write(template.render(template_values))
        
class AboutHandler(RequestHandler):

    def get(self):
        
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
        }
        template = JINJA_ENVIRONMENT.get_template('templates/about.html')
        self.response.write(template.render(template_values))

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
            'session_info': UserInfo.session_info(self.username()),
        }
        template = JINJA_ENVIRONMENT.get_template('templates/user.html')
        
        self.response.write(template.render(template_values))
        
class PostLoginHandler(RequestHandler):
    
    def get(self):
        user_info = UserInfo.get_current()
        if user_info is None:
            template = JINJA_ENVIRONMENT.get_template('templates/post_login.html')
            
            self.response.write(template.render({'cancel_link':users.create_logout_url('/')}))
        else:
            #don't worry about redirects for now
            
            now = datetime.datetime.now()
            delta = datetime.timedelta(days=28)
            then = delta + now
            
            self.response.set_cookie('username',value=user_info.username,expires=then)
            
            self.redirect('/')

class PostLogoutHandler(RequestHandler):
    
    def get(self):
        self.redirect('/')
        self.response.delete_cookie('username')
        