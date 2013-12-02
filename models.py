import urllib
import logging

from google.appengine.api import users, memcache
from google.appengine.ext import ndb

from HTMLParser import HTMLParser

config = {
    "stories": {
        "default_name": "default_story",
        "custom_enabled": False,
    },
    "pages": {
        "link_max": 64,
        "content_max": 256,
        "depth_max": 512,
    }
}

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def string_validator(prop, value):
    stripper = MLStripper()
    stripper.feed(value)
    value = stripper.get_data()
    max_chars = 10000
    if prop._name == 'link':
        max_chars = config['pages']['link_max']
    elif prop._name == 'content':
        max_chars = config['pages']['content_max']
    
    if max_chars < len(value):
        value = value[:max_chars]
        
    return value
    
    
def page_url(story_name, page_key):
    query_params = {'page_key': page_key.urlsafe()}
    return '/page?%s' % (urllib.urlencode(query_params))

def user_url(user_info_key):
    query_params = {'user_key': user_info_key.urlsafe()}
    return '/user?%s' % (urllib.urlencode(query_params))

class Story(ndb.Model):
    """Models an individual Story"""
    moderator_info = ndb.KeyProperty(kind='UserInfo',indexed=True)
    name = ndb.StringProperty(indexed=False,validator=string_validator)
    introduction = ndb.TextProperty(validator=string_validator)
    conventions = ndb.TextProperty(validator=string_validator)
    
    @classmethod
    def create_key(cls, story_name=config['stories']['default_name']):
        """Constructs a Datastore key for a Game entity with story_name."""
        return ndb.Key('Story', story_name)
    
    #we store the root page with an id equali to the name of the story
    #all other pages are stored with random integer ids
    def get_root_page(self):
        return ndb.Key('Page',self.name).get()
        
    

class Like(ndb.Model):
    """Models a Like on a page"""
    user_info = ndb.KeyProperty(kind='UserInfo',indexed=True)
    page = ndb.KeyProperty(kind='Page',indexed=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    value = ndb.IntegerProperty(indexed=True)
    
    #assumes that the 
    @classmethod
    def create_key(cls, page):
        user_info_key = UserInfo.get_current_key()
        if user_info_key:
            return ndb.Key('Like', user_info_key.string_id()+"_"+str(page.key.integer_id()))
        return None
    
    
class Page(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    author_info = ndb.KeyProperty(kind='UserInfo',indexed=True)
    story = ndb.KeyProperty(kind='Story',indexed=True)
    content = ndb.StringProperty(indexed=False, validator=string_validator)
    link = ndb.StringProperty(indexed=False, validator=string_validator)
    date = ndb.DateTimeProperty(auto_now_add=True)
    parent_page = ndb.KeyProperty(kind='Page',indexed=True)
    
    _like_count = None
    _unlike_count = None
    _child_count = None
    
    def url(self):
        if self.key:
            query_params = {'page_key': self.key.urlsafe()}
            return '/page#%s' % (urllib.urlencode(query_params))
        return None
    
    def like_count(self):
        if self._like_count is None:
            self._like_count = Like.query(Like.page==self.key,Like.value==1).count()
        return self._like_count
    
    def unlike_count(self):
        if self._unlike_count is None:
            self._unlike_count = Like.query(Like.page==self.key,Like.value==-1).count()
        return self._unlike_count
    
    def child_count(self):
        if self._child_count is None:
            self._child_count = Page.query( Page.parent_page==self.key).count()
        return self._child_count
    
    def score(self):
        return self.child_count() + self.like_count() - self.unlike_count()
    
    def children_key(self):
        return self.key.urlsafe()+"_children"
    
    def children(self):
        memcache_key = self.children_key()
        data = memcache.get(memcache_key)  # @UndefinedVariable
        if data is None:
            pages_query = Page.query( Page.parent_page==self.key)
            data = pages_query.fetch(64)
            self._child_count = len(data)
            if not memcache.add(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('get_children - memcache add failed.')
        return sorted(data, key=lambda page: page.score(), reverse=True)
    
    def append_child(self,child):
        memcache_key = self.children_key()
        data = memcache.get(memcache_key)  # @UndefinedVariable
        
        if self._child_count is not None:
            self._child_count += 1
        
        if data is None:
            logging.info('append_child - loading data from memcache')
            data = self.get_children()
        if child not in data:
            data.append(child)
            if not memcache.replace(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('append_child - memcache replace failed.')
            else:
                logging.info('append_child - replace succeeded')
        else:
            logging.info('append_child - child exists')

#Container for the user data
#Needs:
#1. follow a link to the user, regardless of state
#2. lookup the userInfo without a query
#3. All users are Anonymous until they choose a display name

class UserInfo(ndb.Model):
    username = ndb.StringProperty(validator=string_validator)
    google_user = ndb.UserProperty(indexed=True)
    
    #uniquely identify the username via the user
    @classmethod
    def get_id(cls, user):
        
        return user.user_id()
        
    @classmethod
    def get_current_key(cls):
        
        if users.get_current_user():
            return ndb.Key('UserInfo',users.get_current_user().user_id())
        return None
    
    @classmethod
    def session_info(cls, uri):
        result = SessionInfo()
        if users.get_current_user():
            result.url = users.create_logout_url(uri)
            result.link_text = 'Logout'
        else:
            result.url = users.create_login_url(uri)
            result.link_text = 'Login'
        
        user_info_key = UserInfo.get_current_key()
        
        result.user_key = user_info_key
        
        if user_info_key:
            result.profile_url = user_url(user_info_key)
            user_info = user_info_key.get()
            if user_info and user_info.username:
                result.profile_text = user_info.username
            else:
                result.profile_text = 'Anonymous'
        
        return result
        
    def pages(self):
        data = Page.query(Page.author_info == self.key)
        return sorted(data, key=lambda page: page.score(), reverse=True)
        
class SessionInfo:
    link_text = ""
    url = "/"
    profile_text = None
    profile_url = None
    user_key = None
