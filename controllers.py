import threading
import re
import logging

from models import Page, UserInfo, Story
from google.appengine.ext import ndb

class PageController:
    @classmethod
    def save_page(cls,parent_urlsafe_key,link,content):
        
        user_info_key = UserInfo.current_get()
        
        if user_info_key is None:
            return False, { 'unauthenticated':True}
        
        errors = {}
        
        page = Page()
        page.link = link
        page.content = content
        
        parent_key = ndb.Key(urlsafe=parent_urlsafe_key)
        parent_page = parent_key.get()
        
        page.story_name = parent_page.story_name
        
        if len(page.link) == 0:
            errors['empty_page_link'] = True
        
        if len(page.content) == 0:
            errors['empty_page_content'] = True
        
        
#Comment on thread safety:
#Page creation will be a VERY frequent operation. Multiple pages with identical links
#Isn't an application error, just an annoyance for the user. So we allow this to occur
#without a lock in place
        
        authored_branch_count = 0
                
        pages = parent_page.children()
        
        for branch_page in pages:
            if branch_page.link == page.link:
                errors['has_identical_link'] = True
            if branch_page.author_info == user_info_key:
                authored_branch_count += 1
        
        if 2 <= authored_branch_count:
            errors['has_branches'] = True
        
        if len(errors.keys()) == 0:
            page.parent_page = parent_key
            page.author_info = UserInfo.current_get()
            page_key = page.put()
            
            logging.info(page_key)
            logging.info(page.key)
            logging.info(page_key.get().key)
        
            parent_page.append_child(page)
            
            return True, page
        else:
            return False, errors
        
class StoryController:
    
    _create_story_lock = threading.Lock()
    
    @classmethod
    def save_story(cls,story_name,introduction,conventions,root_page_link,root_page_content):
        
        if UserInfo.current_get() is None:
            return False, { 'unauthenticated':True}
        
        if UserInfo.current_get().get().name is None:
            return False, { 'invalid_user':True}
        
        story_key = Story.create_key(story_name)
        
        errors = {}
        
        empty_name = story_name is None or len(story_name) == 0
        
        if empty_name:
            errors['empty_name'] = False
        
        match = re.search(r'^[\d\w_\-]+$', story_name)
        
        isvalid = match and 4 <= len(story_name) and len(story_name) <= 20;
        
        if not isvalid:
            errors['invalid_name'] = True
        
        page = Page(id=story_name)
        page.author_info = UserInfo.current_get()
        page.link = root_page_link
        page.content = root_page_content
        page.story_name = story_name
        
        if len(page.link) == 0:
            errors['empty_root_page_link'] = True
        
        if len(page.content) == 0:
            errors['empty_root_page_content'] = True
        
#The frequency of story creation should be low enough to ensure that this won't
#lead to any long standing locking issues
        
        with StoryController._create_story_lock:
            
            story = story_key.get();
            
            if story:
                errors['story_exists'] = True
            
            if len(errors.keys()) == 0:
                
                page.put()
                story = Story(id=story_name,name=story_name)
                story.moderator_info = UserInfo.current_get()
                story.introduction = introduction
                story.conventions = conventions
                story.put()
        
        if len(errors.keys()) == 0:
            return True, story
        else:
            return False, errors

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
            
            user_info = UserInfo.current_get()
            
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
