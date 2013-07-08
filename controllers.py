import threading

from models import *

class PageController:
    @classmethod
    def save_page(cls,parent_urlsafe_key,link,content):
        
        user_info_key = UserInfo.get_current_key()
        
        if user_info_key is None:
            return False, { 'unauthenticated':True}
        
        errors = {}
        
        page = Page()
        page.link = link
        page.content = content
        
        parent_key = ndb.Key(urlsafe=parent_urlsafe_key)
        parent_page = parent_key.get()
        
        page.story = parent_page.story
        
        if len(page.link) == 0:
            errors['empty_page_link'] = True
        
        if len(page.content) == 0:
            errors['empty_page_content'] = True
        
        
#Comment on thread safety:
#Page creation will be a VERY frequent operation. Multiple pages with identical links
#Isn't an application error, just an annoyance for the user. So we allow this to occur
#without a lock in place
        
        has_identical_link = False
        
        pages = parent_page.children()
        
        for branch_page in pages:
            if branch_page.link == page.link:
                errors['has_identical_link'] = True
            if branch_page.author_info == user_info_key:
                errors['has_authored_page'] = True
        
        if len(errors.keys()) == 0:
            page.parent_page = parent_key
            page.author_info = UserInfo.get_current_key()
            page.put()
            
            parent_page.append_child(page)
            
            return True, page
        else:
            return False, errors
        
class StoryController:
    
    _create_story_lock = threading.Lock()
    
    @classmethod
    def save_story(cls,story_name,introduction,conventions,root_page_link,root_page_content):
        
        if UserInfo.get_current_key() is None:
            return False, { 'unauthenticated':True}
        
        story_key = Story.create_key(story_name)
        
        errors = {}
        
        empty_name = story_name is None or len(story_name) == 0
        
        if empty_name:
            errors['empty_name'] = False
        
        page = Page(id=story_name)
        page.author_info = UserInfo.get_current_key()
        page.link = root_page_link
        page.content = root_page_content
        
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
                story.moderator_info = UserInfo.get_current_key()
                story.introduction = introduction
                story.conventions = conventions
                story.put()
        
        if len(errors.keys()) == 0:
            return True, story
        else:
            return False, errors

