import urllib
import logging

from google.appengine.api import users, memcache
from google.appengine.ext import ndb
import datetime

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

def user_url(username):
    return '/user/'+username

class Story(ndb.Model):
    """Models an individual Story"""
    moderatorname = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=False,validator=string_validator)
    conventions = ndb.TextProperty(validator=string_validator)
    
    @classmethod
    def create_key(cls, story_name=config['stories']['default_name']):
        """Constructs a Datastore key for a Game entity with story_name."""
        return ndb.Key('Story', story_name)
    
    @classmethod
    def get_by_name(cls,story_name):
        if story_name:
            return Story.create_key(story_name).get()
        return None
    
    #we store the root page with an id equali to the name of the story
    #all other pages are stored with random integer ids
    def get_root_page(self):
        return ndb.Key('Page',self.name).get()
    
    @classmethod
    def get_by_names(cls,names):
        result = {}
        for name in names:
            result[name] = Story.get_by_name(name)
        return result
    
    @classmethod
    def main_stories(cls):
        memcache_key = 'main_stories'
        data = memcache.get(memcache_key)  # @UndefinedVariable
        if data is None:
            stories_query = Story.query()
            data = stories_query.fetch(64)
            if not memcache.add(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('main_pages - memcache add failed.')
        return data
    

class Like(ndb.Model):
    """Models a Like on a page"""
    username = ndb.StringProperty(indexed=True)
    page = ndb.KeyProperty(kind='Page',indexed=True)
    #denormalizing here, but will make queries much quicker
    pageauthorname = ndb.StringProperty(indexed=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    value = ndb.IntegerProperty(indexed=True)
    
    #assumes that the 
    @classmethod
    def create_key(cls, page_key, username):
        return ndb.Key('Like', username+"_"+page_key.urlsafe())
    
class Page(ndb.Model):
    authorname = ndb.StringProperty(indexed=True)
    story_name = ndb.StringProperty(indexed=True)
    content = ndb.StringProperty(indexed=False, validator=string_validator)
    link = ndb.StringProperty(indexed=False, validator=string_validator)
    date = ndb.DateTimeProperty(auto_now_add=True)
    parent_page = ndb.KeyProperty(kind='Page',indexed=True)
    parent_page_authorname = ndb.StringProperty(indexed=True)
    
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
            data = self.children()
        if child not in data:
            data.append(child)
            if not memcache.replace(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('append_child - memcache replace failed.')
            else:
                logging.info('append_child - replace succeeded')
        else:
            logging.info('append_child - child exists')
            
    @classmethod
    def main_pagedatas(cls):
            memcache_key = 'main_pages_key'
            data = memcache.get(memcache_key)  # @UndefinedVariable
            if data is None:
                pages_query = Page.query()
                pages = pages_query.fetch(64)
                data = {}
                for page in pages:
                    pagedata = page.to_dict()
                    pagedata['time_ago'] = Page.format_time_ago(page.date)
                    pagedata['page_key'] = page.key.urlsafe()
                    pagedata['score'] = page.score()
                    if pagedata['story_name'] not in data:
                        data[pagedata['story_name']] = []
                    story_pagedatas = data[pagedata['story_name']]
                    story_pagedatas.append(pagedata)
                if not memcache.add(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                    logging.error('main_pages - memcache add failed.')
            return data
    
    @classmethod
    def get_first_pages(cls,stories):
        result = {}
        for story in stories:
            result[story.name] = ndb.Key(Page,story.name).get()
        return result
    
    
    @classmethod
    def format_time_ago(cls,t):
        """
        Get a datetime object or a int() Epoch timestamp and return a
        pretty string like 'an hour ago', 'Yesterday', '3 months ago',
        'just now', etc
        """
        now = datetime.datetime.now()
        if type(t) is int:
            diff = now - datetime.datetime.fromtimestamp(t)
        elif isinstance(t,datetime.datetime):
            diff = now - t 
        elif not t:
            diff = now - now
        second_diff = diff.seconds
        day_diff = diff.days
    
        if day_diff < 0:
            return ''
    
        if day_diff == 0:
            if second_diff < 10:
                return "just now"
            if second_diff < 60:
                return str(second_diff) + " seconds ago"
            if second_diff < 120:
                return  "a minute ago"
            if second_diff < 3600:
                return str( second_diff / 60 ) + " minutes ago"
            if second_diff < 7200:
                return "an hour ago"
            if second_diff < 86400:
                return str( second_diff / 3600 ) + " hours ago"
        if day_diff == 1:
            return "Yesterday"
        if day_diff < 7:
            return str(day_diff) + " days ago"
        if day_diff < 31:
            return str(day_diff/7) + " weeks ago"
        if day_diff < 365:
            return str(day_diff/30) + " months ago"
        return str(day_diff/365) + " years ago"
            
#Container for the user data
#Needs:
#1. follow a link to the user, regardless of state
#2. lookup the userInfo without a query

class UserInfo(ndb.Model):
    username = ndb.StringProperty(validator=string_validator)
    google_user = ndb.UserProperty(indexed=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    
    def is_current(self):
        return self.google_user == users.get_current_user()
    
    @classmethod
    def put_new(cls,username):
        user_info = UserInfo(id=username)
                
        user_info.username = username
        user_info.google_user = users.get_current_user()
        user_info.put()
        return user_info
            
    @classmethod
    def get_by_username(cls,username):
        
        if username:
            return ndb.Key('UserInfo',username).get()
        return None
    
    @classmethod
    def get_current(cls):
        """Gets the current user. This involves a query. Its more efficient to perform 
        lookups with the username and verify that the user_info is current."""
        
        users_query = UserInfo.query( UserInfo.google_user==users.get_current_user())
        return users_query.get()
        
    @classmethod
    def session_info(cls, username):
        result = SessionInfo()
        if users.get_current_user():
            result.url = users.create_logout_url('/post_logout')
            result.link_text = 'Logout'
            result.isloggedin = True
        else:
            result.url = users.create_login_url('/post_login')
            result.link_text = 'Login'
        result.username = username
        return result
        
    def pages(self):
        data = Page.query(Page.authorname == self.username)
        return sorted(data, key=lambda page: page.score(), reverse=True)
    
    def branch_pages(self):
        data = Page.query(Page.authorname != self.username , Page.parent_page_authorname == self.username)
        return sorted(data, key=lambda page: page.score(), reverse=True)
    
class SessionInfo:
    link_text = ""
    url = "/"
    username = ""
    isloggedin = False
