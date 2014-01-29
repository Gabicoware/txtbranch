import re

from models import Branch, UserInfo, Tree, Like
from google.appengine.ext import ndb

class BaseController:
    def __init__(self):
        self.oauth_user_id = None
        self.google_user = None
        self.user_info = None

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
            
            return False, { 'unauthenticated':True }
        
        errors = {}
        
        branch = Branch()
        branch.link = link
        branch.content = content
        
        parent_key = ndb.Key(urlsafe=parent_urlsafe_key)
        parent_branch = parent_key.get()
        
        branch.tree_name = parent_branch.tree_name
        
        if len(branch.link) == 0:
            errors['empty_branch_link'] = True
        
        if len(branch.content) == 0:
            errors['empty_branch_content'] = True
        
        
#Comment on thread safety:
#Branch creation will be a VERY frequent operation. Multiple branchs with identical links
#Isn't an application error, just an annoyance for the user. So we allow this to occur
#without a lock in place
        
        authored_branch_count = 0
                
        branchs = parent_branch.children()
        
        for branch_branch in branchs:
            if branch_branch.link == branch.link:
                errors['has_identical_link'] = True
            if branch_branch.authorname == authorname:
                authored_branch_count += 1
        
        if 2 <= authored_branch_count:
            errors['has_branches'] = True
        
        if len(errors.keys()) == 0:
            branch.parent_branch = parent_key
            branch.authorname = authorname
            branch.parent_branch_authorname = parent_branch.authorname
            branch.put()
            
            parent_branch.append_child(branch)
            
            return True, branch
        else:
            return False, errors
        
class TreeController(BaseController):
    
    def save_tree(self,tree_name,moderatorname,conventions,root_branch_link,root_branch_content):
        
        if moderatorname is None:
            return False, { 'unauthenticated':True}
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not self.is_user_info_current(author_info):
            return False, { 'unauthenticated':True}
        
        if author_info.username is None:
            return False, { 'invalid_user':True}
        
        tree_key = Tree.create_key(tree_name)
        
        errors = {}
        
        empty_name = tree_name is None or len(tree_name) == 0
        
        if empty_name:
            errors['empty_name'] = True
        else:
            match = re.search(r'^[\d\w_\-]+$', tree_name)
            isvalid = match and 4 <= len(tree_name) and len(tree_name) <= 20;
            if not isvalid:
                errors['invalid_name'] = True
        
        branch = Branch(id=tree_name)
        branch.authorname = moderatorname
        branch.link = root_branch_link
        branch.content = root_branch_content
        branch.tree_name = tree_name
        
        if branch.link == None or len(branch.link) == 0:
            errors['empty_root_branch_link'] = True
        
        if branch.content == None or len(branch.content) == 0:
            errors['empty_root_branch_content'] = True
        
#let the user complete the other validation before trying to create the tree        
        if len(errors.keys()) != 0:
            return False, errors
        
        
        tree = tree_key.get();
        
        if tree:
            errors['tree_exists'] = True
        
        if len(errors.keys()) == 0:
            #if two users enter identical information at the same time, then
            #whoever gets it second is the winner
            tree = Tree(id=tree_name,name=tree_name)
            tree.moderatorname = moderatorname
            tree.conventions = conventions
            branch.put()
            tree.put()
        
        if len(errors.keys()) == 0:
            return True, tree
        else:
            return False, errors
        
        
    def update_tree(self,tree,moderatorname,conventions):
        
        if tree is None:
            return False, { 'tree_not_found':True}
        
        if moderatorname is None:
            return False, { 'unauthenticated':True}
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not self.is_user_info_current(author_info):
            return False, { 'unauthenticated':True}
        
        if author_info.username is None:
            return False, { 'invalid_user':True}
        
        
        tree.conventions = conventions
        tree.put()

        return True, tree

class UserInfoController(BaseController):
    
    def set_username(self,username):
        errors = {}
                
        match = re.search(r'^[\d\w_\-]+$', username)
        
        isvalid = match and 4 <= len(username) and len(username) <= 20;
        
        if not isvalid:
            errors['invalid_name'] = True
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
                    errors['other_has_name'] = True
        
        if len(errors.keys()) == 0:
            return True, user_info
        else:
            return False, errors

class LikeController(BaseController):
    
    def set_like(self,branch_urlsafe_key,like_value):
        
        if branch_urlsafe_key is None or branch_urlsafe_key == '':
            return False, {'no_page_key':True}
        
        userinfo = self.current_user_info()
        if userinfo is None:
            return False, {'unauthenticated':True}
        
        branch_key = ndb.Key(urlsafe=branch_urlsafe_key)
        
        like_key = Like.create_key(branch_key,userinfo.username)
        like = like_key.get()
        
        if like is None:
            branch = branch_key.get()
            like = Like(key=like_key,username=userinfo.username,branch=branch_key,branchauthorname=branch.authorname)
        
        like.value = int(like_value)
        
        like.put()
        
        return True, like
    