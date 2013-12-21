import threading
import re

from models import Page, UserInfo, Story
from google.appengine.ext import ndb

class PageController:
    @classmethod
    def save_page(cls,authorname,parent_urlsafe_key,link,content):
        
        userinfo = UserInfo.get_by_username(authorname)    
        if userinfo is None or not userinfo.is_current():
            
            return False, { 'unauthenticated':True }
        
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
            if branch_page.authorname == authorname:
                authored_branch_count += 1
        
        if 2 <= authored_branch_count:
            errors['has_branches'] = True
        
        if len(errors.keys()) == 0:
            page.parent_page = parent_key
            page.authorname = authorname
            page.parent_page_authorname = parent_page.authorname
            page.put()
            
            parent_page.append_child(page)
            
            return True, page
        else:
            return False, errors
        
class StoryController:
    
    _create_story_lock = threading.Lock()
    
    @classmethod
    def save_story(cls,story_name,moderatorname,conventions,root_page_link,root_page_content):
        
        if moderatorname is None:
            return False, { 'unauthenticated':True}
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not author_info.is_current():
            return False, { 'unauthenticated':True}
        
        if author_info.username is None:
            return False, { 'invalid_user':True}
        
        story_key = Story.create_key(story_name)
        
        errors = {}
        
        empty_name = story_name is None or len(story_name) == 0
        
        if empty_name:
            errors['empty_name'] = True
        else:
            match = re.search(r'^[\d\w_\-]+$', story_name)
            isvalid = match and 4 <= len(story_name) and len(story_name) <= 20;
            if not isvalid:
                errors['invalid_name'] = True
        
        page = Page(id=story_name)
        page.authorname = moderatorname
        page.link = root_page_link
        page.content = root_page_content
        page.story_name = story_name
        
        if page.link == None or len(page.link) == 0:
            errors['empty_root_page_link'] = True
        
        if page.content == None or len(page.content) == 0:
            errors['empty_root_page_content'] = True
        
#let the user complete the other validation before trying to create the story        
        if len(errors.keys()) != 0:
            return False, errors
        
        
        story = story_key.get();
        
        if story:
            errors['story_exists'] = True
        
        if len(errors.keys()) == 0:
            #if two users enter identical information at the same time, then
            #whoever gets it second is the winner
            story = Story(id=story_name,name=story_name)
            story.moderatorname = moderatorname
            story.conventions = conventions
            page.put()
            story.put()
        
        if len(errors.keys()) == 0:
            return True, story
        else:
            return False, errors
        
        
    @classmethod
    def update_story(cls,story,moderatorname,conventions):
        
        if story is None:
            return False, { 'story_not_found':True}
        
        if moderatorname is None:
            return False, { 'unauthenticated':True}
        
        author_info = UserInfo.get_by_username(moderatorname)
        
        if author_info is None or not author_info.is_current():
            return False, { 'unauthenticated':True}
        
        if author_info.username is None:
            return False, { 'invalid_user':True}
        
        
        story.conventions = conventions
        story.put()

        return True, story

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
