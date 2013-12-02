
from google.appengine.ext import ndb

import webapp2
import json

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
        like_value = self.request.get('value','0')
        
        if page_urlsafe_key is None or page_urlsafe_key == '':
            self.response.write('NO PAGE KEY SPECIFIED')
        elif UserInfo.get_current_key:
            
            page_key = ndb.Key(urlsafe=page_urlsafe_key)
             
            like_key = Like.create_key(page_key.get())
            like = like_key.get();
            
            if like is None:
                like = Like(id=like_key.string_id(),user_info=UserInfo.get_current_key(),page=page_key)
            
            like.value = int(like_value)
            
            like.put()
                
            self.response.write('OK')
        else:
            self.response.write('UNAUTHENTICATED')

class UserInfoHandler(webapp2.RequestHandler):
    
    def get(self):
        
        username = self.request.get('username')
            
        success, userinfo = UserInfoController.update(username)        
        
        if success:
            self.response.write('OK')
        else:
            self.response.write(json.dumps(userinfo))

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
        
        if UserInfo.get_current_key():
            like_key = Like.create_key(page)
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
        
        author_info = page.author_info.get()
        if author_info and author_info.username:
            page_dict['author_name'] = author_info.username
        return page_dict

    def post(self):
        parent_urlsafe_key = self.request.get('parent_page_key')
        
        success, result = PageController.save_page(
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
            author_info = result.author_info.get()
            if author_info and author_info.username:
                page_dict['author_name'] = author_info.username
    
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
