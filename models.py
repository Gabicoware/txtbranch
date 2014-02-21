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
        max_chars = config['branchs']['link_max']
    elif prop._name == 'content':
        max_chars = config['branchs']['content_max']
    
    if max_chars < len(value):
        value = value[:max_chars]
        
    return value
    
    
def branch_url(tree_name, branch_key):
    query_params = {'branch_key': branch_key.urlsafe()}
    return '/branch?%s' % (urllib.urlencode(query_params))

def user_url(username):
    return '/user/'+username

class Tree(ndb.Model):
    """Models an individual Tree"""
    moderatorname = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=False,validator=string_validator)
    conventions = ndb.TextProperty(validator=string_validator)
    
    @classmethod
    def create_key(cls, tree_name=config['trees']['default_name']):
        """Constructs a Datastore key for a Game entity with tree_name."""
        return ndb.Key('Tree', tree_name)
    
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
    def main_trees(cls):
        memcache_key = 'main_trees'
        data = memcache.get(memcache_key)  # @UndefinedVariable
        if data is None:
            trees_query = Tree.query()
            data = trees_query.fetch(64)
            if not memcache.add(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('main_branchs - memcache add failed.')
        return data
    

class Like(ndb.Model):
    """Models a Like on a branch"""
    username = ndb.StringProperty(indexed=True)
    branch = ndb.KeyProperty(kind='Branch',indexed=True)
    #denormalizing here, but will make queries much quicker
    branchauthorname = ndb.StringProperty(indexed=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    value = ndb.IntegerProperty(indexed=True)
    
    #assumes that the 
    @classmethod
    def create_key(cls, branch_key, username):
        return ndb.Key('Like', username+"_"+branch_key.urlsafe())
    
class BranchVersion(ndb.Model):
    content = ndb.StringProperty(indexed=False)
    link = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    
class Branch(ndb.Model):
    authorname = ndb.StringProperty(indexed=True)
    tree_name = ndb.StringProperty(indexed=True)
    content = ndb.StringProperty(indexed=False, validator=string_validator)
    link = ndb.StringProperty(indexed=False, validator=string_validator)
    date = ndb.DateTimeProperty(auto_now_add=True)
    update = ndb.DateTimeProperty(auto_now=True)
    parent_branch = ndb.KeyProperty(kind='Branch',indexed=True)
    parent_branch_authorname = ndb.StringProperty(indexed=True)
    revision = ndb.IntegerProperty(indexed=True)
    
    _like_count = None
    _unlike_count = None
    _child_count = None
    
    def url(self):
        if self.key:
            query_params = {'branch_key': self.key.urlsafe()}
            return '/branch#%s' % (urllib.urlencode(query_params))
        return None
    
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
            if not memcache.add(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('get_children - memcache add failed.')
        return sorted(data, key=lambda branch: branch.score(), reverse=True)
    
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
    
    def update_child(self,child):
        memcache_key = self.children_key()
        data = memcache.get(memcache_key)  # @UndefinedVariable
        
        if data is not None:
            for other_child in data:
                if other_child.key.urlsafe() == child.key.urlsafe():
                    original_child = other_child
            if original_child is not None:
                data.remove(original_child)
            
            data.append(child)
            if not memcache.replace(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                logging.error('append_child - memcache replace failed.')
            else:
                logging.info('append_child - replace succeeded')
        else:
            logging.info('append_child - child exists')
    
    @classmethod
    def main_branchdatas(cls):
            memcache_key = 'main_branchs_key'
            data = memcache.get(memcache_key)  # @UndefinedVariable
            if data is None:
                branchs_query = Branch.query()
                branchs = branchs_query.fetch(64)
                data = {}
                for branch in branchs:
                    branchdata = branch.to_dict()
                    branchdata['time_ago'] = Branch.format_time_ago(branch.date)
                    branchdata['branch_key'] = branch.key.urlsafe()
                    branchdata['score'] = branch.score()
                    if branchdata['tree_name'] not in data:
                        data[branchdata['tree_name']] = []
                    tree_branchdatas = data[branchdata['tree_name']]
                    tree_branchdatas.append(branchdata)
                if not memcache.add(key=memcache_key, value=data, time=60):  # @UndefinedVariable
                    logging.error('main_branchs - memcache add failed.')
            return data
    
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

class UserInfo(ndb.Model):
    username = ndb.StringProperty(validator=string_validator)
    google_user = ndb.UserProperty(indexed=True)
    oauth_user_id = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def put_new(cls,username,google_user=None,oauth_user_id=None):
        user_info = UserInfo(id=username)
        user_info.google_user = google_user
        user_info.oauth_user_id = oauth_user_id
        user_info.username = username
        user_info.put()
        return user_info
            
    @classmethod
    def get_by_username(cls,username):
        
        if username:
            return ndb.Key('UserInfo',username).get()
        return None
            
    def branchs(self):
        data = Branch.query(Branch.authorname == self.username)
        return sorted(data, key=lambda branch: branch.score(), reverse=True)
    
    def branch_branchs(self):
        data = Branch.query(Branch.authorname != self.username , Branch.parent_branch_authorname == self.username)
        return sorted(data, key=lambda branch: branch.score(), reverse=True)
    
class SessionInfo:
    link_text = ""
    url = "/"
    username = ""
    isloggedin = False
