
from google.appengine.ext import ndb

import webapp2
import json
import datetime

import logging

from json import JSONEncoder

from models import Like, UserInfo, Page
from controllers import UserInfoController, PageController

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
        page_urlsafe_key = self.request.get('page_key')
        
        if page_urlsafe_key is None or page_urlsafe_key == '':
            return self.response.write('NO PAGE KEY SPECIFIED')
        
        username = self.request.cookies.get('username')
        userinfo = UserInfo.get_by_username(username)    
        if userinfo and userinfo.is_current():
            
            like_value = self.request.get('value','0')
            page_key = ndb.Key(urlsafe=page_urlsafe_key)
             
            like_key = Like.create_key(page_key,self.request.cookies.get('username'))
            like = like_key.get();
            
            if like is None:
                page = page_key.get()
                like = Like(key=like_key,username=username,page=page_key,pageauthorname=page.authorname)
            
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
    
class PageHandler(webapp2.RequestHandler):

    def get(self):
    
        items = self.request.GET.getall('page_key')
        
        if len(items) == 0:
            parent_page_key_urlsafe = self.request.get('parent_page_key')
            if parent_page_key_urlsafe:
                parent_page_key = ndb.Key(urlsafe=parent_page_key_urlsafe)
                parent_page = parent_page_key.get()
                items = parent_page.children()
        
        pages = []
        
        for item in items:
            
            logging.info(str(item))
            
            page = None
            
            if isinstance(item,Page):
                page = item
            else:
                page_key = ndb.Key(urlsafe=str(item))
                page = page_key.get()
                
            if page:
                page_dict = self.expanded_page(page)
                pages.append(page_dict)
        
        self.response.write(json.dumps({'status':'OK','result':pages}, cls=ModelEncoder))
            

    def expanded_page(self,page):
        
        like_value = 0
        
        username = self.request.cookies.get('username')
        userinfo = UserInfo.get_by_username(username)    
        if userinfo and userinfo.is_current():
            like_key = Like.create_key(page.key,self.request.cookies.get('username'))
            like = like_key.get();
            if like:
                like_value = like.value
        
        child_count = page.child_count()
        like_count = page.like_count()
        unlike_count = page.unlike_count()
        
        #adjust the like count based on the like value
        if like_value == 1:
            like_count -= 1
        if like_value == -1:
            unlike_count -= 1
        
        page_dict = page.to_dict();
        
        page_dict['child_count'] = child_count
        page_dict['like_value'] = like_value
        page_dict['like_count'] = like_count
        page_dict['unlike_count'] = unlike_count
        
        page_dict['key'] = page.key.urlsafe()
        
        return page_dict

    def post(self):
        parent_urlsafe_key = self.request.get('parent_page_key')
        
        success, result = PageController.save_page(
          self.request.cookies.get('username'),
          parent_urlsafe_key,
          self.request.get('link',''),
          self.request.get('content',''))
         
        if success:
            page_dict = result.to_dict()
            page_dict['key'] = result.key.urlsafe();
            page_dict['child_count'] = 0
            page_dict['like_value'] = 0
            page_dict['like_count'] = 0
            page_dict['unlike_count'] = 0
    
            self.response.write(json.dumps({'status':'OK','result':page_dict},cls=ModelEncoder))
        else:
            self.response.write(json.dumps({'status':'ERROR','result':result}))
        
#        redirect_url = '/page?' + urllib.urlencode(query_params)
        
#        self.redirect(redirect_url)





handlers = [
    ('/api/v1/likes', LikeHandler),
    ('/api/v1/pages', PageHandler),
    ('/api/v1/userinfos', UserInfoHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)
