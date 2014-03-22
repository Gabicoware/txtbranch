import re
import logging

from models import Branch, UserInfo, Tree, Like, BranchVersion
from google.appengine.ext import ndb

class BaseController:
    def __init__(self):
        self.oauth_user_id = None
        self.google_user = None
        self.user_info = None
        self.username = None

    def current_user_info(self):
        
        if self.user_info is not None and self.is_user_info_current(self.user_info):
            return self.user_info
        
        """Gets the current user. This involves a query. Its more efficient to perform 
        lookups with the username and verify that the user_info is current."""
        if self.google_user is not None:
            users_query = UserInfo.query( UserInfo.google_user==self.google_user)
            return users_query.get()
        
        if self.oauth_user_id is not None:
            users_query = UserInfo.query( UserInfo.oauth_user_id==self.oauth_user_id)
            return users_query.get()
        
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
    
    def save_branch(self,authorname,parent_urlsafe_key,link,content):
        
        userinfo = UserInfo.get_by_username(authorname)    
        if userinfo is None or not self.is_user_info_current(userinfo):
            
            return False, [ 'unauthenticated' ]
        
        errors = []
        
        branch = Branch()
        branch.link = link
        branch.content = content
        
        parent_key = ndb.Key(urlsafe=parent_urlsafe_key)
        parent_branch = parent_key.get()
        
        branch.tree_name = parent_branch.tree_name
        
        if len(branch.link) == 0:
            errors.append('empty_branch_link')
        
        if len(branch.content) == 0:
            errors.append('empty_branch_content')
        
        
#Comment on thread safety:
#Branch creation will be a VERY frequent operation. Multiple branchs with identical links
#Isn't an application error, just an annoyance for the user. So we allow this to occur
#without a lock in place
        
        authored_branch_count = 0
                
        branchs = parent_branch.children()
        
        for branch_branch in branchs:
            if branch_branch.link == branch.link:
                errors.append('has_identical_link')
            if branch_branch.authorname == authorname:
                authored_branch_count += 1
        
        if 2 <= authored_branch_count:
            errors.append('has_branches')
        
        if len(errors) == 0:
            branch.revision = 0
            branch.parent_branch = parent_key
            branch.authorname = authorname
            branch.parent_branch_authorname = parent_branch.authorname
            branch.put()
            self.create_branch_version(branch)
            
            parent_branch.append_child(branch)
            
            return True, branch
        else:
            return False, errors
        
    
    def update_branch(self,authorname,urlsafe_key,link,content):
        
        userinfo = UserInfo.get_by_username(authorname)    
        logging.info(authorname)
        logging.info(userinfo)
        if userinfo is None or not self.is_user_info_current(userinfo):
            return False, [ 'unauthenticated' ]
        
        
        branch = ndb.Key(urlsafe=urlsafe_key).get()
        
        if branch.authorname != authorname:
            return False, [ 'not_author' ]
        
        errors = []
        
        branch.link = link
        branch.content = content
                
        if len(branch.link) == 0:
            errors.append('empty_branch_link')
        
        if len(branch.content) == 0:
            errors.append('empty_branch_content')
        
        
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
        
        default_tree_dict = {
            "tree_name":None,
            "moderatorname":None,
            "conventions":None, 
            "root_branch_link":None, 
            "root_branch_content":None,
            "links_moderator_only":False,
            "link_max_length":0,
            "link_prompt":None,
            "content_moderator_only":False,
            "content_max_length":0,
            "content_prompt":None
        }
        
        tree_dict = dict(default_tree_dict.items() + tree_dict.items())
        
        try:
            if tree_dict["content_max_length"] is not int:
                tree_dict["content_max_length"] = int(tree_dict["content_max_length"])
            if tree_dict["link_max_length"] is not int:
                tree_dict["link_max_length"] = int(tree_dict["link_max_length"])
            if tree_dict["content_moderator_only"] is not bool:
                tree_dict["content_moderator_only"] = bool(int(tree_dict["content_moderator_only"]))
            if tree_dict["links_moderator_only"] is not bool:
                tree_dict["links_moderator_only"] = bool(int(tree_dict["links_moderator_only"]))
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
        
        if tree_dict['content_max_length'] < 16:
            errors.append('min_content_max_length')
            
        if tree_dict['link_max_length'] < 16:
            errors.append('min_link_max_length')
            
        if len(tree_dict['link_prompt']) > tree_dict['link_max_length']:
            errors.append('link_prompt_too_large')
            
        if len(tree_dict['content_prompt']) > tree_dict['content_max_length']:
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
            tree = Tree(id=tree_dict['tree_name'],name=tree_dict['tree_name'])
            tree.moderatorname = tree_dict['moderatorname']
            tree.conventions = tree_dict['conventions']
            
            tree.links_moderator_only = tree_dict['links_moderator_only']
            tree.link_max_length = tree_dict['link_max_length']
            tree.link_prompt = tree_dict['link_prompt']
            
            tree.content_moderator_only = tree_dict['content_moderator_only']
            tree.content_max_length = tree_dict['content_max_length']
            tree.content_prompt = tree_dict['content_prompt']
            
            branch.put()
            tree.put()
        
        if len(errors) == 0:
            return True, tree
        else:
            return False, errors
        
        
    def update_tree(self,tree,moderatorname,conventions):
        
        if tree is None:
            return False, ['tree_not_found']
        
        if moderatorname is None:
            return False, ['unauthenticated']
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not self.is_user_info_current(author_info):
            return False, ['unauthenticated']
        
        if author_info.username is None:
            return False, ['invalid_user']
        
        
        tree.conventions = conventions
        tree.put()

        return True, tree

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
                user_info_key = ndb.Key('UserInfo',username)
                
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
            return False, ['no_page_key']
        
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
    