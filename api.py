
from google.appengine.ext import ndb
from google.appengine.api import memcache

import webapp2

from models import Like
from models import UserInfo

class LikeHandler(webapp2.RequestHandler):
    
    def get(self):
        page_urlsafe_key = self.request.get('page_key')
        like_value = self.request.get('value','0')
        hasParams = page_urlsafe_key is not None
        
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
        
        
        user_info_key = UserInfo.get_current_key()
        
        if user_info_key:
            
            user_info = user_info_key.get()
            
            if user_info is None:
                user_info = UserInfo(id=user_info_key.string_id())
            
            user_info.username = self.request.get('username')
            
            user_info.put()
            
            self.response.write('OK')
        else:
            self.response.write('UNAUTHENTICATED')

handlers = [
    ('/api/v1/like', LikeHandler),
    ('/api/v1/userinfo', UserInfoHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)
