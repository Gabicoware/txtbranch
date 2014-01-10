
from google.appengine.ext import ndb

import webapp2
import json
import datetime

import logging

from json import JSONEncoder

from models import Like, UserInfo, Branch
from controllers import UserInfoController, BranchController

class ModelEncoder(JSONEncoder):
#TODO make non models passthrough objects
    def default(self,o):
        if isinstance(o,ndb.Model):
            return o.to_dict()
        elif isinstance(o,ndb.Key):
            return o.urlsafe()
        return str(o);
                
class LikeHandler(webapp2.RequestHandler):
    
    def get(self):
        branch_urlsafe_key = self.request.get('branch_key')
        
        if branch_urlsafe_key is None or branch_urlsafe_key == '':
            return self.response.write('NO PAGE KEY SPECIFIED')
        
        username = self.request.cookies.get('username')
        userinfo = UserInfo.get_by_username(username)    
        if userinfo and userinfo.is_current():
            
            like_value = self.request.get('value','0')
            branch_key = ndb.Key(urlsafe=branch_urlsafe_key)
             
            like_key = Like.create_key(branch_key,self.request.cookies.get('username'))
            like = like_key.get();
            
            if like is None:
                branch = branch_key.get()
                like = Like(key=like_key,username=username,branch=branch_key,branchauthorname=branch.authorname)
            
            like.value = int(like_value)
            
            like.put()
                
            self.response.write('OK')
        else:
            self.response.write('UNAUTHENTICATED')

class UserInfoHandler(webapp2.RequestHandler):
    
    def get(self):
        
        username = self.request.get('username')
        if username:
            user_info = UserInfo.get_by_username(username)
        else:
            username = self.request.cookies.get('username')
            if username:
                user_info = UserInfo.get_by_username(username)
            else:
                user_info = UserInfo.get_current()
        
        if user_info is not None:
            self.response.write(json.dumps({'status':'OK','result':user_info.to_dict()},cls=ModelEncoder))
        else:
            self.response.write(json.dumps({'status':'ERROR','result':None}))

    def post(self):
        username = self.request.get('username')
        success, result = UserInfoController.set_username(username)
        
        if success:
            now = datetime.datetime.now()
            delta = datetime.timedelta(days=28)
            then = delta + now
            
            self.response.set_cookie('username',value=result.username,expires=then)
            
            self.response.write(json.dumps({'status':'OK','result':result.to_dict()},cls=ModelEncoder))
        else:
            self.response.write(json.dumps({'status':'ERROR','result':result}))
    
class BranchHandler(webapp2.RequestHandler):

    def get(self):
    
        items = self.request.GET.getall('branch_key')
        
        if len(items) == 0:
            parent_branch_key_urlsafe = self.request.get('parent_branch_key')
            if parent_branch_key_urlsafe:
                parent_branch_key = ndb.Key(urlsafe=parent_branch_key_urlsafe)
                parent_branch = parent_branch_key.get()
                items = parent_branch.children()
        
        branchs = []
        
        for item in items:
            
            logging.info(str(item))
            
            branch = None
            
            if isinstance(item,Branch):
                branch = item
            else:
                branch_key = ndb.Key(urlsafe=str(item))
                branch = branch_key.get()
                
            if branch:
                branch_dict = self.expanded_branch(branch)
                branchs.append(branch_dict)
        
        self.response.write(json.dumps({'status':'OK','result':branchs}, cls=ModelEncoder))
            

    def expanded_branch(self,branch):
        
        like_value = 0
        
        username = self.request.cookies.get('username')
        userinfo = UserInfo.get_by_username(username)    
        if userinfo and userinfo.is_current():
            like_key = Like.create_key(branch.key,self.request.cookies.get('username'))
            like = like_key.get();
            if like:
                like_value = like.value
        
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
        
        branch_dict['key'] = branch.key.urlsafe()
        
        return branch_dict

    def post(self):
        parent_urlsafe_key = self.request.get('parent_branch_key')
        
        success, result = BranchController.save_branch(
          self.request.cookies.get('username'),
          parent_urlsafe_key,
          self.request.get('link',''),
          self.request.get('content',''))
         
        if success:
            branch_dict = result.to_dict()
            branch_dict['key'] = result.key.urlsafe();
            branch_dict['child_count'] = 0
            branch_dict['like_value'] = 0
            branch_dict['like_count'] = 0
            branch_dict['unlike_count'] = 0
    
            self.response.write(json.dumps({'status':'OK','result':branch_dict},cls=ModelEncoder))
        else:
            self.response.write(json.dumps({'status':'ERROR','result':result}))
        
#        redirect_url = '/branch?' + urllib.urlencode(query_params)
        
#        self.redirect(redirect_url)





handlers = [
    ('/api/v1/likes', LikeHandler),
    ('/api/v1/branchs', BranchHandler),
    ('/api/v1/userinfos', UserInfoHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)
