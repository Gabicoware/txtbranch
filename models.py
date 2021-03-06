import urllib
import logging

from google.appengine.api import memcache
from google.appengine.ext import ndb
import datetime

from HTMLParser import HTMLParser

config = {
    "trees": {
        "default_name": "default_tree",
        "custom_enabled": False,
    },
    "branchs": {
        "link_max": 64,
        "content_max": 256,
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
    return value
    
    
#for use when classes have "safe" key components
class BaseModel(ndb.Model):
    def to_dict(self):
        result = super(BaseModel,self).to_dict()
        result['key'] = self.key.urlsafe()
        return result
    def before_put(self):
        pass
    def after_put(self):
        pass
    def put(self, **kwargs):
        self.before_put()
        super(BaseModel,self).put(**kwargs)
        self.after_put()

class Tree(BaseModel):
    """Models an individual Tree"""
    moderatorname = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=False,validator=string_validator)
    conventions = ndb.TextProperty(validator=string_validator)
    
    link_prompt = ndb.StringProperty(indexed=False,validator=string_validator)
    link_max = ndb.IntegerProperty(indexed=False)
    link_moderator_only = ndb.BooleanProperty(indexed=False)
    
    content_prompt = ndb.StringProperty(indexed=False,validator=string_validator)
    content_max = ndb.IntegerProperty(indexed=False)
    content_moderator_only = ndb.BooleanProperty(indexed=False)
    
    single_thread = ndb.BooleanProperty(indexed=False)
    
    branch_max = ndb.IntegerProperty(indexed=False)
    
    def to_dict(self):
        result = super(Tree,self).to_dict()
        result['root_branch_key'] = self.get_root_branch_key().urlsafe()
        return result
    
    @classmethod
    def create_key(cls, tree_name=config['trees']['default_name']):
        return ndb.Key('Tree', tree_name.lower())
    
    @classmethod
    def get_by_name(cls,tree_name):
        if tree_name:
            return Tree.create_key(tree_name).get()
        return None
    
    #we store the root branch with an id equali to the name of the tree
    #all other branchs are stored with random integer ids
    def get_root_branch(self):
        return self.get_root_branch_key().get()
    
    def get_root_branch_key(self):
        return ndb.Key('Branch',self.name)
    
    @classmethod
    def get_by_names(cls,names):
        result = {}
        for name in names:
            result[name] = Tree.get_by_name(name)
        return result
    
    @classmethod
    def get_by_moderatorname(cls,moderator):
        return Tree.query(Tree.moderatorname==moderator).fetch()
     
    @classmethod
    def main_trees(cls):
        memcache_key = 'main_trees'
        data = memcache.get(memcache_key)  # @UndefinedVariable
        if data is None:
            trees_query = Tree.query()
            data = trees_query.fetch(64)
            if data and not memcache.add(key=memcache_key, value=data, time=7200):  # @UndefinedVariable
                logging.error('main_branchs - memcache add failed.')
        return data
    
    def after_put(self):
        memcache_key = 'main_trees'
        memcache.delete(memcache_key)

class Like(BaseModel):
    """Models a Like on a branch"""
    username = ndb.StringProperty(indexed=True)
    branch = ndb.KeyProperty(kind='Branch',indexed=True)
    #denormalizing here, but will make queries much quicker
    branchauthorname = ndb.StringProperty(indexed=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    value = ndb.IntegerProperty(indexed=True)
    
    def to_dict(self):
        result = super(Like,self).to_dict()
        result['branch_key'] = result.pop('branch')
        return result
    
    #assumes that the 
    @classmethod
    def create_key(cls, branch_key, username):
        return ndb.Key('Like', username+"_"+branch_key.urlsafe())
    
class BranchVersion(BaseModel):
    content = ndb.StringProperty(indexed=False)
    link = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    
class Branch(BaseModel):
    authorname = ndb.StringProperty(indexed=True)
    tree_name = ndb.StringProperty(indexed=True)
    content = ndb.StringProperty(indexed=False, validator=string_validator)
    link = ndb.StringProperty(indexed=False, validator=string_validator)
    date = ndb.DateTimeProperty(auto_now_add=True)
    update = ndb.DateTimeProperty(auto_now=True)
    parent_branch = ndb.KeyProperty(kind='Branch',indexed=True)
    parent_branch_authorname = ndb.StringProperty(indexed=True)
    #when a branch is deleted, it is just detached from parent, setting parent_branch to none
    #the old value is here
    detached_parent_branch = ndb.KeyProperty(kind='Branch',indexed=True)
    
    revision = ndb.IntegerProperty(indexed=True)
    
    _like_count = None
    _unlike_count = None
    _child_count = None
    
    def to_dict(self):
        result = super(Branch,self).to_dict()
        result['parent_branch_key'] = result.pop('parent_branch')
        result['detached_parent_branch_key'] = result.pop('detached_parent_branch')
        return result

    def like_count(self):
        if self._like_count is None:
            self._like_count = Like.query(Like.branch==self.key,Like.value==1).count()
        return self._like_count
    
    def unlike_count(self):
        if self._unlike_count is None:
            self._unlike_count = Like.query(Like.branch==self.key,Like.value==-1).count()
        return self._unlike_count
    
    def child_count(self):
        if self._child_count is None:
            self._child_count = Branch.query( Branch.parent_branch==self.key).count()
        return self._child_count
    
    def score(self):
        return self.child_count() + self.like_count() - self.unlike_count()
    
    def children_key(self):
        return self.key.urlsafe()+"_children"
    
    def children(self):
        memcache_key = self.children_key()
        data = memcache.get(memcache_key)  # @UndefinedVariable
        if data is None:
            branchs_query = Branch.query( Branch.parent_branch==self.key)
            data = branchs_query.fetch(64)
            self._child_count = len(data)
            if data and not memcache.add(key=memcache_key, value=data, time=7200):  # @UndefinedVariable
                logging.error('get_children - memcache add failed.')
        return sorted(data, key=lambda branch: branch.score(), reverse=True)
    
    def append_child(self,child):
        memcache_key = self.children_key()
        data = memcache.get(memcache_key)  # @UndefinedVariable
        
        if self._child_count is not None:
            self._child_count += 1
        
        if data is None:
            data = self.children()
        if child not in data:
            data.append(child)
            if not memcache.replace(key=memcache_key, value=data, time=7200):  # @UndefinedVariable
                logging.error('append_child - memcache replace failed.')
    
    def empty_children_cache(self):
        memcache_key = self.children_key()
        memcache.replace(key=memcache_key, value=None, time=1)  # @UndefinedVariable
            
    def update_child(self,child):
        memcache_key = self.children_key()
        data = memcache.get(memcache_key)  # @UndefinedVariable
        
        if data is not None:
            original_child = None
            for other_child in data:
                if other_child.key.urlsafe() == child.key.urlsafe():
                    original_child = other_child
            if original_child is not None:
                data.remove(original_child)
            
            data.append(child)
            if not memcache.replace(key=memcache_key, value=data, time=7200):  # @UndefinedVariable
                logging.error('append_child - memcache replace failed.')
    
    @classmethod
    def get_first_branchs(cls,trees):
        result = {}
        for tree in trees:
            result[tree.name] = ndb.Key(Branch,tree.name).get()
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

class UserInfo(BaseModel):
    username = ndb.StringProperty(validator=string_validator)
    google_user = ndb.UserProperty(indexed=True)
    oauth_user_id = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def create_key(cls, username):
        return ndb.Key('UserInfo', username.lower())
    
    @classmethod
    def put_new(cls,username,google_user=None,oauth_user_id=None):
        user_info = UserInfo(id=username.lower())
        user_info.google_user = google_user
        user_info.oauth_user_id = oauth_user_id
        user_info.username = username
        user_info.put()
        return user_info
    
    def after_put(self):
        if self.username:
            memcache_key = "UserInfo.get.username."+self.username
            memcache.delete(memcache_key)

    @classmethod
    def get_by_username(cls,username):
        
        data = None
        if username:
            memcache_key = "UserInfo.get.username."+username
            data = memcache.get(memcache_key)  # @UndefinedVariable
            if data is None:
                data = UserInfo.create_key(username).get()
                if data and not memcache.add(key=memcache_key, value=data, time=7200):  # @UndefinedVariable
                    logging.error('UserInfo.get_by_username - memcache add failed.')

        return data
            
    def branchs(self):
        data = Branch.query(Branch.authorname == self.username)
        return sorted(data, key=lambda branch: branch.score(), reverse=True)
        
class Notification(BaseModel):
    from_username = ndb.StringProperty(validator=string_validator,indexed=True)
    to_username = ndb.StringProperty(validator=string_validator,indexed=True)
    notification_type = ndb.StringProperty(validator=string_validator)
    branch = ndb.KeyProperty(kind='Branch',indexed=True)
    branch_link = ndb.StringProperty(validator=string_validator, indexed=False)
    tree_name = ndb.StringProperty(validator=string_validator)
    date = ndb.DateTimeProperty(auto_now_add=True)

    def to_dict(self):
        result = super(Notification,self).to_dict()
        result['branch_key'] = result.pop('branch')
        return result
    
    def after_put(self):
        if self.tree_name is not None:
            memcache_key = "Notification.list.tree_name."+self.tree_name
            memcache.delete(memcache_key)
        if self.from_username is not None:
            memcache_key = "Notification.list.from_username."+self.from_username
            memcache.delete(memcache_key)
        if self.to_username is not None:
            memcache_key = "Notification.list.to_username."+self.to_username
            memcache.delete(memcache_key)
    
    @classmethod
    def get_all_by_tree_name(cls,tree_name):
        memcache_key = "Notification.list.tree_name."+tree_name
        return Notification.get_all_cached(memcache_key, Notification.query( Notification.tree_name==tree_name))

    @classmethod
    def get_all_by_from_username(cls,from_username):
        memcache_key = "Notification.list.from_username."+from_username
        return Notification.get_all_cached(memcache_key, Notification.query( Notification.from_username==from_username))
    
    @classmethod
    def get_all_by_to_username(cls,to_username):
        memcache_key = "Notification.list.to_username."+to_username
        return Notification.get_all_cached(memcache_key, Notification.query( Notification.to_username==to_username))
    
    
    @classmethod
    def get_all_cached(cls,memcache_key, query):
        data = memcache.get(memcache_key)  # @UndefinedVariable
        if data is None:
            data = query.order(-Notification.date).fetch(50)
            if data and not memcache.add(key=memcache_key, value=data, time=7200):  # @UndefinedVariable
                logging.error('Notification.get_all_cached - memcache add failed.')
        return data
    
class SessionInfo:
    link_text = ""
    url = "/"
    username = ""
    isloggedin = False
