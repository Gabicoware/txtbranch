import threading
import re

from models import Branch, UserInfo, Tree
from google.appengine.ext import ndb

class BranchController:
    @classmethod
    def save_branch(cls,authorname,parent_urlsafe_key,link,content):
        
        userinfo = UserInfo.get_by_username(authorname)    
        if userinfo is None or not userinfo.is_current():
            
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
        
class TreeController:
    
    _create_tree_lock = threading.Lock()
    
    @classmethod
    def save_tree(cls,tree_name,moderatorname,conventions,root_branch_link,root_branch_content):
        
        if moderatorname is None:
            return False, { 'unauthenticated':True}
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not author_info.is_current():
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
        
        
    @classmethod
    def update_tree(cls,tree,moderatorname,conventions):
        
        if tree is None:
            return False, { 'tree_not_found':True}
        
        if moderatorname is None:
            return False, { 'unauthenticated':True}
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not author_info.is_current():
            return False, { 'unauthenticated':True}
        
        if author_info.username is None:
            return False, { 'invalid_user':True}
        
        
        tree.conventions = conventions
        tree.put()

        return True, tree

class UserInfoController:
    
    _update_user_lock = threading.Lock()
    
    @classmethod
    def set_username(cls,username):
        errors = {}
                
        match = re.search(r'^[\d\w_\-]+$', username)
        
        isvalid = match and 4 <= len(username) and len(username) <= 20;
        
        if not isvalid:
            errors['invalid_name'] = True
        else:
            
            user_info = UserInfo.get_current()
            
            if user_info is None:
                user_info_key = ndb.Key('UserInfo',username)
                
                #in the circumstances of a collision whoever asked last is the winner
                #of course if fifty 'Daniels' pile up then we have an issue
                user_info = user_info_key.get()
                if user_info is None:
                    user_info = UserInfo.put_new(username)
                else:
                    errors['other_has_name'] = True
            
        if len(errors.keys()) == 0:
            return True, user_info
        else:
            return False, errors
