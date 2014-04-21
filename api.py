
import webapp2
from webapp2 import Route
import json
import datetime
import logging

import base
from secrets import SESSION_KEY
from json import JSONEncoder

from controllers import *

class ModelEncoder(JSONEncoder):
#TODO make non models passthrough objects
    def default(self,o):
        if isinstance(o,ndb.Model):
            return o.to_dict()
        elif isinstance(o,ndb.Key):
            return o.urlsafe()
        return str(o);

class APIRequestHandler(base.BaseRequestHandler):
    def write_success_response(self, result):
        self.response.write(json.dumps({'status':'OK','result':result},cls=ModelEncoder))
    def write_fail_response(self, result):
        self.response.write(json.dumps({'status':'ERROR','result':result}))
        
class LikeHandler(APIRequestHandler):
    
    def get(self):
        
        branch_urlsafe_key = self.request.get('branch_key')
        
        like_value = self.request.get('value','0')
            
        success, result = self.controller(LikeController).set_like( branch_urlsafe_key, like_value)
        
        if success:
            like_dict = { 'like_value':result.value }
            self.write_success_response(like_dict)
        else:
            self.write_fail_response(result)
        
class UserInfoHandler(APIRequestHandler):
    
    def get(self):
        
        user_info = None
        username = self.request.get('username')
        if username:
            user_info = UserInfo.get_by_username(username)
        else:
            if self.request.get('set_cookie'):
                user_info = self.controller(BaseController).current_user_info()
                if user_info is not None:
                    self.set_cookie(user_info,True)
            else:
                username = self.request.cookies.get('username')
                
                if username:
                    user_info = UserInfo.get_by_username(username)
                                    
        if user_info is not None:
            self.write_success_response(user_info.to_dict())
        else:
            self.write_fail_response([])

    def post(self):
        username = self.request.get('username')
        success, result = self.controller(UserInfoController).set_username(username)
        
        if success:
            self.set_cookie(result,True)
            
            self.write_success_response(result.to_dict())
        else:
            self.write_fail_response(result)
    
    def set_cookie(self,user_info,remember):
        if remember:
            now = datetime.datetime.now()
            delta = datetime.timedelta(seconds=self.request.app.config['webapp2_extras.sessions']['cookie_args']['max_age'])
            logging.info(delta)
            then = delta + now
        else:
            then = None
        self.response.set_cookie('username',value=user_info.username,expires=then)
        
    
class BranchHandler(APIRequestHandler):

    def get(self):
    
        branch_keys = self.request.GET.getall('branch_key')
        
        parent_branch_key_urlsafe = self.request.get('parent_branch_key')
        authorname = self.request.get('authorname')
        
        branches = []
            
        if len(branch_keys) != 0:
            
            for branch_key in branch_keys:
            
                branch = ndb.Key(urlsafe=str(branch_key)).get()
                branches.append(branch)
        
        if len(branches) == 0 and parent_branch_key_urlsafe:
            parent_branch_key = ndb.Key(urlsafe=parent_branch_key_urlsafe)
            parent_branch = parent_branch_key.get()
            branches = parent_branch.children()
            
        if len(branches) == 0 and authorname:
            branches = Branch.query(Branch.authorname == authorname).order(-Branch.date).fetch(64)

        branch_dicts = []
        
        for branch in branches:
            
            branch_dict = self.expanded_branch(branch)
            branch_dicts.append(branch_dict)
        
        self.write_success_response(branch_dicts)
            

    def expanded_branch(self,branch):
        
        like_value = self.controller(LikeController).get_like_value(branch)
                
        child_count = branch.child_count()
        like_count = branch.like_count()
        unlike_count = branch.unlike_count()
        
        #adjust the like count based on the like value
        if like_value == 1:
            like_count -= 1
        if like_value == -1:
            unlike_count -= 1
        
        branch_dict = branch.to_dict();
        
        branch_dict['child_count'] = child_count
        branch_dict['like_value'] = like_value
        branch_dict['like_count'] = like_count
        branch_dict['unlike_count'] = unlike_count
                
        return branch_dict

    def post(self):
        parent_urlsafe_key = self.request.get('parent_branch_key')
        
        success, result = self.controller(BranchController).save_branch(
          self.request.cookies.get('username'),
          parent_urlsafe_key,
          self.request.get('link',''),
          self.request.get('content',''))
         
        if success:
            branch_dict = result.to_dict()
            branch_dict['child_count'] = 0
            branch_dict['like_value'] = 0
            branch_dict['like_count'] = 0
            branch_dict['unlike_count'] = 0
    
            self.write_success_response(branch_dict)
        else:
            self.write_fail_response(result)
        
    def put(self):
        urlsafe_key = self.request.get('branch_key')
        
        success, result = self.controller(BranchController).update_branch(
          self.request.cookies.get('username'),
          urlsafe_key,
          self.request.get('link',''),
          self.request.get('content',''))
         
        if success:
            
            branch_dict = self.expanded_branch(result)
            
            self.write_success_response(branch_dict)
        else:
            self.write_fail_response(result)

    def delete(self):
        urlsafe_key = self.request.get('branch_key')
        
        success, result = self.controller(BranchController).delete_branch(
          self.request.cookies.get('username'),
          urlsafe_key)
         
        if success:
            self.write_success_response([])
        else:
            self.write_fail_response(result)
        

class ExportHandler(APIRequestHandler):
    
    def get(self):
        
        tree = self.request.get('tree')
        
        if tree is not None:
            branchdatas = Branch.query( Branch.tree_name==tree).fetch()
            
            all_branch_dict = {};
            
            #there's likely a map function for this
            
            for branch in branchdatas:
                branch_dict = branch.to_dict()
                branch_dict['children'] = []
                all_branch_dict[branch.key.urlsafe()] = branch_dict
                if branch.parent_branch is None:
                    root_branch = branch_dict
            
            if root_branch is None:
                self.write_fail_response(['no_root'])
            else:
                                    
                for key in all_branch_dict:
                    
                    branch_dict = all_branch_dict[key]
                    
                    if branch_dict['parent_branch']:
                        parent_branch_key = branch_dict['parent_branch'].urlsafe()
                        
                        parent_branch = all_branch_dict[parent_branch_key]
                    
                        parent_branch['children'].append(branch_dict)
                    
                self.write_success_response(root_branch)
        else:
            self.write_fail_response(['no_tree'])


class TreeHandler(APIRequestHandler):
    
    def get(self):
        
        list_type = self.request.get('list')
        
        tree_name = self.request.get('name')
        
        if list_type == "main":
            self.get_main_list()
        elif tree_name is not None and tree_name != '':
            self.get_tree(tree_name)
        else:
            self.abort(404)
    
    def post(self):
        tree_dict = {}
        
        for key, value in self.request.POST.items():
            tree_dict[key] = value
        
        tree_dict['moderatorname'] = self.request.cookies.get('username')
                
        success, result = self.controller(TreeController).save_tree(tree_dict)
        
        if success:
            
            tree_dict = result.to_dict()
            tree_dict['root_branch_key'] = result.get_root_branch_key().urlsafe()
            self.write_success_response(tree_dict)
        else:
            self.write_fail_response(result)
            
    
    def get_main_list(self):
        trees = Tree.main_trees()
        self.write_success_response(trees)
        
        
    def get_tree(self,tree_name):
        tree = ndb.Key('Tree', tree_name).get()
        
        if tree is not None:
            tree_dict = tree.to_dict()
            
            tree_dict['root_branch_key'] = tree.get_root_branch_key().urlsafe()
        
            self.write_success_response(tree_dict)
        else:
            self.write_fail_response(['not_found'])
        
class NotificationHandler(APIRequestHandler):
    
    def get_notifications(self):
        if self.request.get('from_username'):
            success, result = self.controller(NotificationController).get_notifications(from_username=self.request.get('from_username'))
        elif self.request.get('tree_name'):
            success, result = self.controller(NotificationController).get_notifications(tree_name=self.request.get('tree_name'))
        else:
            success, result = self.controller(NotificationController).get_notifications()
        if success:
            self.write_success_response(result)
        else:
            self.write_fail_response(result)
        
    def get_unread_count(self):
        success, result = self.controller(NotificationController).get_unread_count()
        if success:
            self.write_success_response(result)
        else:
            self.write_fail_response(result)
        
    def reset_unread_count(self):
        success, result = self.controller(NotificationController).reset_unread_count()
        if success:
            self.write_success_response(result)
        else:
            self.write_fail_response(result)
            
    
# webapp2 config
app_config = {
  'webapp2_extras.sessions': {
    'cookie_name': '_simpleauth_sess',
    'secret_key': SESSION_KEY,
    'cookie_args':{ "max_age":31536000 }
  },
  'webapp2_extras.auth': {
    'user_attributes': [],
    "token_max_age":31536000
  }
}


handlers = [
    ('/api/v1/export', ExportHandler),
    ('/api/v1/likes', LikeHandler),
    ('/api/v1/branchs', BranchHandler),
    ('/api/v1/trees', TreeHandler),
    ('/api/v1/userinfos', UserInfoHandler),
    Route('/api/v1/notifications', handler='api.NotificationHandler:get_notifications', name='get_notifications',methods=['GET']),
    Route('/api/v1/notifications/unread_count', handler='api.NotificationHandler:get_unread_count', name='get_count',methods=['GET']),
    Route('/api/v1/notifications/unread_count', handler='api.NotificationHandler:reset_unread_count', name='reset_count',methods=['DELETE']),
]

application = webapp2.WSGIApplication(handlers, config=app_config, debug=True)
