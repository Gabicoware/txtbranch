import re
import logging

from models import Branch, UserInfo, Tree, Like, BranchVersion, Notification
from google.appengine.ext import ndb

class BaseController:
    def __init__(self):
        self.oauth_user_id = None
        self.google_user = None
        self.user_info = None
        self.username = None

    def current_user_info(self):
        
        if self.user_info is None:
            """Get the current user by lookup if we can"""
            if self.username:
                self.user_info = UserInfo.get_by_username(self.username)
            
            """Gets the current user. This involves a query. Its more efficient to perform 
            lookups with the username and verify that the user_info is current."""
            if self.google_user is not None:
                users_query = UserInfo.query( UserInfo.google_user==self.google_user)
                self.user_info = users_query.get()
            
            if self.oauth_user_id is not None:
                users_query = UserInfo.query( UserInfo.oauth_user_id==self.oauth_user_id)
                self.user_info = users_query.get()
            
            if self.user_info and self.username is None:
                self.username = self.user_info.username
            
            
        if self.user_info is not None and self.is_user_info_current(self.user_info):
            return self.user_info
        else:
            return None

    def is_user_info_current(self, user_info):
    
        if user_info is None:
            return False
        
        if self.google_user is not None:
            return self.google_user == user_info.google_user
        
        if self.oauth_user_id is not None:
            return self.oauth_user_id == user_info.oauth_user_id
        
        return False

class BranchController(BaseController):
    
    def validate_branch(self,tree,branch,authorname):
        errors = []
        
        if tree.moderatorname != authorname:
            if len(branch.link) == 0 and not tree.link_moderator_only:
                errors.append('empty_branch_link')
            if len(branch.content) == 0 and not tree.content_moderator_only:
                errors.append('empty_branch_content')
            
            if len(branch.link) != 0 and tree.link_moderator_only:
                errors.append('invalid_branch_link')
            
            if len(branch.content) != 0 and tree.content_moderator_only:
                errors.append('invalid_branch_content')
        else:
            if len(branch.link) == 0:
                errors.append('empty_branch_link')
            
            if len(branch.content) == 0:
                errors.append('empty_branch_content')
        return errors
    
    def save_branch(self,authorname,parent_urlsafe_key,link,content):
        
        userinfo = UserInfo.get_by_username(authorname)    
        if userinfo is None or not self.is_user_info_current(userinfo):
            
            return False, [ 'unauthenticated' ]
        
        branch = Branch()
        branch.authorname = authorname
        
        parent_key = ndb.Key(urlsafe=parent_urlsafe_key)
        parent_branch = parent_key.get()
        
        if parent_branch is None:
            return False, ['parent_branch_not_found']
        
        branch.tree_name = parent_branch.tree_name
        
        tree = Tree.get_by_name(parent_branch.tree_name)
        
        if tree is None:
            return False, ['tree_not_found']

        if tree.moderatorname == authorname or not tree.link_moderator_only:
            branch.link = link
        else:
            branch.link = ""
        
        if tree.moderatorname == authorname or not tree.content_moderator_only:
            branch.content = content
        else:
            branch.content = ""
        
        errors = self.validate_branch(tree, branch,authorname)
                    
#currently there is a db lock on unique links
#eventually we should have a memcache lcok
        
        authored_branch_count = 0
                
        branchs = parent_branch.children()
        
        if tree.single_thread and parent_branch.authorname == authorname:
            errors.append('has_single_thread_parent_branch')
        
        if tree.single_thread and len(branchs) > 0:
            errors.append('has_single_thread_branch')
        
        for branch_branch in branchs:
            if branch_branch.link == branch.link:
                errors.append('has_identical_link')
            if branch_branch.authorname == authorname:
                authored_branch_count += 1
        
        if tree.branch_max > 0 and tree.branch_max <= authored_branch_count:
            errors.append('has_branches')
        
        if len(errors) == 0:
            branch.revision = 0
            branch.parent_branch = parent_key
            branch.parent_branch_authorname = parent_branch.authorname
            branch.put()
            self.create_branch_version(branch)
            
            parent_branch.append_child(branch)
            
            notification = Notification()
            notification.from_username = branch.authorname
            if branch.authorname != parent_branch.authorname:
                notification.to_username = parent_branch.authorname
            notification.notification_type = 'new_branch'
            notification.branch = branch.key
            notification.branch_link = branch.link
            notification.tree_name = branch.tree_name
            notification.put()
            
            return True, branch
        else:
            return False, errors
        
    
    def delete_branch(self,authorname,urlsafe_key):
        
        #check in order of least to most expensive operation
        if not urlsafe_key:
            return False, ['parameter_error']
        
        userinfo = UserInfo.get_by_username(authorname)
        
        if userinfo is None or not self.is_user_info_current(userinfo):
            return False, [ 'unauthenticated' ]
        
        branch = ndb.Key(urlsafe=urlsafe_key).get()
        
        if branch.parent_branch == None and branch.detached_parent_branch is not None:
            return False, [ 'already_deleted' ]
        
        if len(branch.children()) != 0:
            return False, [ 'not_empty' ]
        
        tree = Tree.get_by_name(branch.tree_name)
        
        if branch.authorname != authorname and tree.moderatorname != authorname:
            return False, [ 'not_author' ]
                
        branch.detached_parent_branch = branch.parent_branch
        branch.parent_branch = None
        
        branch.put();
        branch.detached_parent_branch.get().remove_child(branch)
        
        return True, None
    
    
    def update_branch(self,authorname,urlsafe_key,link,content):
        
        userinfo = UserInfo.get_by_username(authorname)
        
        if userinfo is None or not self.is_user_info_current(userinfo):
            return False, [ 'unauthenticated' ]
        
        branch = ndb.Key(urlsafe=urlsafe_key).get()
        tree = Tree.get_by_name(branch.tree_name)
        
        if tree is None:
            return False, [ 'tree_not_found' ]
        
        if branch.authorname != authorname and tree.moderatorname != authorname:
            return False, [ 'not_author' ]
        
        if tree.moderatorname == authorname or not tree.link_moderator_only:
            branch.link = link
        if tree.moderatorname == authorname or not tree.content_moderator_only:
            branch.content = content
                
        errors = self.validate_branch(tree, branch,authorname)
        
#Comment on thread safety:
#Branch creation will be a VERY frequent operation. Multiple branchs with identical links
#Isn't an application error, just an annoyance for the user. So we allow this to occur
#without a lock in place
        parent_branch = None

        if branch.parent_branch is not None:
            parent_branch = branch.parent_branch.get();
                    
            branchs = parent_branch.children()
            
            for branch_branch in branchs:
                if branch_branch.link == branch.link and branch.key != branch_branch.key:
                    errors.append('has_identical_link')
            
        if len(errors) == 0:
            if branch.revision is None:
                branch.revision = 1
            else:
                branch.revision = branch.revision + 1
                
            branch.put()
            self.create_branch_version(branch)
            if parent_branch is not None:
                parent_branch.update_child(branch)
            
            notification = Notification()
            notification.from_username = authorname
            #only set the to_username when a different user is performing the action
            if branch.authorname != authorname:
                notification.to_username = branch.authorname
            notification.notification_type = 'edit_branch'
            notification.branch = branch.key
            notification.branch_link = branch.link
            notification.tree_name = branch.tree_name
            notification.put()
                
            return True, branch
        else:
            return False, errors
        
    def create_branch_version(self,branch):
        branch_version = BranchVersion(id=branch.revision,parent=branch.key)
        branch_version.content = branch.content
        branch_version.link = branch.link
        branch_version.put()
        
class TreeController(BaseController):
    
    def save_tree(self,tree_dict):
        
        try:
            tree_dict = self.merged_tree(tree_dict)
        except:
            return False, ['invalid_parameters']
            
        #tree_name,moderatorname,conventions,root_branch_link,root_branch_content
        
        if tree_dict['moderatorname'] is None:
            return False, ['unauthenticated','no_moderator']
        
        if tree_dict['tree_name'] is None:
            return False, ['empty_name']
        
        author_info = UserInfo.get_by_username(tree_dict['moderatorname'])
        
        if author_info is None:
            return False, ['unauthenticated','moderator_not_found']
        
        if not self.is_user_info_current(author_info):
            return False, ['unauthenticated','moderator_not_current']
        
        if author_info.username is None:
            return False, ['invalid_user']
        
        errors = []
        
        if tree_dict['content_max'] < 16:
            errors.append('min_content_max')
            
        if tree_dict['link_max'] < 16:
            errors.append('min_link_max')
            
        if len(tree_dict['link_prompt']) > tree_dict['link_max']:
            errors.append('link_prompt_too_large')
            
        if len(tree_dict['content_prompt']) > tree_dict['content_max']:
            errors.append('content_prompt_too_large')
        
        tree_key = Tree.create_key(tree_dict['tree_name'])
        
        empty_name = tree_dict['tree_name'] is None or len(tree_dict['tree_name']) == 0
        
        if empty_name:
            errors.append('empty_name')
        else:
            match = re.search(r'^[\d\w_\-]+$', tree_dict['tree_name'])
            isvalid = match and 4 <= len(tree_dict['tree_name']) and len(tree_dict['tree_name']) <= 20;
            if not isvalid:
                errors.append('invalid_name')
        
        branch = Branch(id=tree_dict['tree_name'])
        branch.authorname = tree_dict['moderatorname']
        branch.link = tree_dict['root_branch_link']
        branch.content = tree_dict['root_branch_content']
        branch.tree_name = tree_dict['tree_name']
        
        if branch.link == None or len(branch.link) == 0:
            errors.append('empty_root_branch_link')
        
        if branch.content == None or len(branch.content) == 0:
            errors.append('empty_root_branch_content')
        
#let the user complete the other validation before trying to create the tree        
        if len(errors) != 0:
            return False, errors
        
        
        tree = tree_key.get();
        
        if tree:
            errors.append('tree_exists')
        
        if len(errors) == 0:
            #if two users enter identical information at the same time, then
            #whoever gets it second is the winner
            tree = Tree(id=tree_dict['tree_name'].lower(),name=tree_dict['tree_name'])
            tree.moderatorname = tree_dict['moderatorname']
            tree.conventions = tree_dict['conventions']
            
            tree.link_moderator_only = tree_dict['link_moderator_only']
            tree.link_max = tree_dict['link_max']
            tree.link_prompt = tree_dict['link_prompt']
            
            tree.content_moderator_only = tree_dict['content_moderator_only']
            tree.content_max = tree_dict['content_max']
            tree.content_prompt = tree_dict['content_prompt']
            
            tree.single_thread = tree_dict['single_thread']
            
            tree.branch_max = tree_dict['branch_max']
            
            branch.put()
            tree.put()
        
            notification = Notification()
            notification.from_username = tree.moderatorname
            #only set the to_username when a different user is performing the action
            notification.notification_type = 'new_tree'
            notification.tree_name = tree_dict['tree_name']
            notification.put()

        
        if len(errors) == 0:
            return True, tree
        else:
            return False, errors
        
        
    def update_tree(self,tree_dict):
        
        try:
            tree_dict = self.merged_tree(tree_dict)
        except:
            return False, ['invalid_parameters']
        
        if tree_dict['tree_name'] is None:
            return False, ['tree_not_found']
        
        if tree_dict['moderatorname'] is None:
            return False, ['unauthenticated']
        
        author_info = UserInfo.get_by_username(tree_dict['moderatorname'])
        
        if author_info is None or not self.is_user_info_current(author_info):
            return False, ['unauthenticated']
        
        if author_info.username is None:
            return False, ['invalid_user']
        
        tree = Tree.get_by_name(tree_dict['tree_name'])
        
        tree.conventions = tree_dict['conventions']
        
        tree.link_moderator_only = tree_dict['link_moderator_only']
        tree.link_max = tree_dict['link_max']
        tree.link_prompt = tree_dict['link_prompt']
        
        tree.content_moderator_only = tree_dict['content_moderator_only']
        tree.content_max = tree_dict['content_max']
        tree.content_prompt = tree_dict['content_prompt']
            
        tree.single_thread = tree_dict['single_thread']
        
        tree.branch_max = tree_dict['branch_max']
        
        tree.put()
        
        notification = Notification()
        notification.from_username = tree.moderatorname
        #only set the to_username when a different user is performing the action
        notification.notification_type = 'edit_tree'
        notification.tree_name = tree_dict['tree_name']
        notification.put()
            
        return True, tree
    
    def merged_tree(self,tree_dict):
        default_tree_dict = {
            "tree_name":None,
            "moderatorname":"",
            "conventions":"", 
            "root_branch_link":"", 
            "root_branch_content":"",
            "link_moderator_only":False,
            "link_max":0,
            "link_prompt":"",
            "content_moderator_only":False,
            "content_max":0,
            "content_prompt":"",
            "single_thread":False,
            "branch_max":0
        }
        
        result = dict(default_tree_dict.items() + tree_dict.items())
        
        if result["branch_max"] is not int:
            result["branch_max"] = int(result["branch_max"])
        if result["content_max"] is not int:
            result["content_max"] = int(result["content_max"])
        if result["link_max"] is not int:
            result["link_max"] = int(result["link_max"])
        if result["content_moderator_only"] is not bool:
            result["content_moderator_only"] = bool(int(result["content_moderator_only"]))
        if result["single_thread"] is not bool:
            result["single_thread"] = bool(int(result["single_thread"]))
        if result["link_moderator_only"] is not bool:
            result["link_moderator_only"] = bool(int(result["link_moderator_only"]))
        
        return result


class UserInfoController(BaseController):
    
    def set_username(self,username):
        errors = []
                
        match = re.search(r'^[\d\w_\-]+$', username)
        
        isvalid = match and 4 <= len(username) and len(username) <= 20;
        
        if not isvalid:
            errors.append('invalid_name')
        else:
            user_info = self.current_user_info()
            if user_info is None:
                user_info_key = UserInfo.create_key(username)
                
                #in the circumstances of a collision whoever asked last is the winner
                #of course if fifty 'Daniels' pile up then we have an issue
                user_info = user_info_key.get()
                if user_info is None:
                    user_info = UserInfo.put_new(username,oauth_user_id=self.oauth_user_id,google_user=self.google_user)
                else:
                    errors.append('other_has_name')
        
        if len(errors) == 0:
            return True, user_info
        else:
            return False, errors

class LikeController(BaseController):
    
    def get_like_value(self,branch):
        userinfo = UserInfo.get_by_username(self.username)    
        if userinfo and self.is_user_info_current(userinfo):
            like_key = Like.create_key(branch.key,self.username)
            like = like_key.get();
            if like:
                return like.value
        return 0
    
    def set_like(self,branch_urlsafe_key,like_value):
        
        if branch_urlsafe_key is None or branch_urlsafe_key == '':
            return False, ['invalid_parameters']
        
        userinfo = self.current_user_info()
        if userinfo is None:
            return False, ['unauthenticated']
        
        branch_key = ndb.Key(urlsafe=branch_urlsafe_key)
        
        like_key = Like.create_key(branch_key,userinfo.username)
        like = like_key.get()
        
        if like is None:
            branch = branch_key.get()
            like = Like(key=like_key,username=userinfo.username,branch=branch_key,branchauthorname=branch.authorname)
        
        like.value = int(like_value)
        
        like.put()
        
        return True, like
    
class NotificationController(BaseController):
    
    def get_notifications(self,tree_name=None,from_username=None):
        data = None
        if tree_name is not None:
            data = Notification.get_all_by_tree_name(tree_name)
        elif from_username is not None:
            data = Notification.get_all_by_from_username(from_username)
        elif self.current_user_info() is not None:
            #default to the users inbox
            data = Notification.get_all_by_to_username(self.current_user_info().username)
        else:
            return False,  [ 'unauthenticated' ]
            
        if data is not None:
            return True, data
        else:
            #if we could not get to the default, then the user must be logged out
            return False,  [ ]
    #todo...
    def get_unread_count(self):
        return False, None
    
    def reset_unread_count(self):
        return False, None
