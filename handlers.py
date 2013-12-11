#TODO: USER CAN SUBMIT 1 BRANCH PER PARENT, and only after 5 minutes

#TODO AUTOMATICALLY TEST SYSTEM LIMITS

#TODO: Make adding a page an in page experience
#TODO: figure out limits to branch count

#TODO: Ranking algorithm

import os
import webapp2
import json
import datetime
import threading
import jinja2

from defaulttext import *
from models import *
from controllers import StoryController


class RequestHandler(webapp2.RequestHandler):
    def username(self):
        return self.request.cookies.get('username')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

class MainHandler(RequestHandler):
    
    def get(self):
        
        pagedatas = Page.main_pagedatas();
        
        stories = Story.get_by_names(pagedatas.keys())
        logging.info(stories)
        template_values = {
            'stories': stories,
            'pagedatas': pagedatas,
            'username': self.username(),
            'session_info': UserInfo.session_info(self.username()),
        }
        
        template = JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render(template_values))
        # Write the submission form and the footer of the page

class CreateStoryHandler(RequestHandler):
    
    _create_story_lock = threading.Lock()
    
    def get(self):
        self.render_create_story_form()
        
    def post(self):
        story_name = self.request.get('story_name',config['stories']['default_name'])
        
        success, story = StoryController.save_story(story_name,
          self.username(),
          self.request.get('introduction', DEFAULT_INTRODUCTION),
          self.request.get('conventions', DEFAULT_CONVENTIONS),
          self.request.get('root_page_link',''),
          self.request.get('root_page_content',''))
        
        if success:
            redirect_url = '/story/' + story_name
            self.redirect(redirect_url)
        else:
            self.render_create_story_form(story)
    
    def render_create_story_form(self,errors=None):
        template = JINJA_ENVIRONMENT.get_template('new_story.html')
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
            'introduction' : self.request.get('introduction', DEFAULT_INTRODUCTION),
            'conventions' : self.request.get('conventions', DEFAULT_CONVENTIONS),

            'story_name' : self.request.get('story_name', ''),
            'root_page_link' : self.request.get('root_page_link', ''),
            'root_page_content' : self.request.get('root_page_content', ''),
            
            'new_story_endpoint' : self.request.uri,
            'link_max' : config["pages"]["link_max"],
            'content_max' : config["pages"]["content_max"],
            'errors' : json.dumps(errors),
        }
        self.response.write(template.render(template_values))
        

class EditStoryHandler(RequestHandler):
    
    def get(self,story_name):
        story = Story.get_by_name(story_name)
        if story == None:
            return self.redirect('/')
        elif story.moderatorname != self.username():
            return self.redirect('/story/'+story_name)
        
        self.render_edit_story_form(story)
        
    def post(self,story_name):
        
        story = Story.get_by_name(story_name)
        
        success, result = StoryController.update_story(
          story,
          self.username(),
          self.request.get('introduction'),
          self.request.get('conventions'))
        
        if success:
            self.render_edit_story_form(story)
        else:
            self.render_edit_story_form(story, errors=result)
            
    def render_edit_story_form(self,story,errors=None):
        template = JINJA_ENVIRONMENT.get_template('edit_story.html')
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
            'introduction' : self.request.get('introduction', story.introduction),
            'conventions' : self.request.get('conventions', story.conventions),
            'story_name' : story.name,
            'edit_story_endpoint' : self.request.uri,
            'errors' : json.dumps(errors),
        }
        self.response.write(template.render(template_values))
         
class StoryHandler(RequestHandler):
    def get(self, story_name):
        
        key = Story.create_key(story_name)
        
        story = key.get()
        
        if story:
        
            root_page = story.get_root_page()
            
            template_values = {
                'root_page_key': root_page.key,
                'story': story,
                'link_max' : config["pages"]["link_max"],
                'content_max' : config["pages"]["content_max"],
                'session_info': UserInfo.session_info(self.username()),
            }
            
            template = JINJA_ENVIRONMENT.get_template('story.html')
            self.response.write(template.render(template_values))
        else:
            template_values = {
                'story_name': story_name,
                'session_info': UserInfo.session_info(self.username()),
            }
            template = JINJA_ENVIRONMENT.get_template('story_not_found.html')
            self.response.status = 404
            self.response.write(template.render(template_values))
        

class HtmlPageHandler(RequestHandler):

    def get(self):
        
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
            'link_max' : config["pages"]["link_max"],
            'content_max' : config["pages"]["content_max"],
        }
        
        template = JINJA_ENVIRONMENT.get_template('page.html')
        self.response.write(template.render(template_values))
        
class AboutHandler(RequestHandler):

    def get(self):
        
        template_values = {
            'session_info': UserInfo.session_info(self.username()),
        }
        template = JINJA_ENVIRONMENT.get_template('about.html')
        self.response.write(template.render(template_values))

class UserHandler(RequestHandler):
    
    def get(self,username):
        
        
        user_info_key = ndb.Key('UserInfo',username)
        
        user_info = user_info_key.get()
        
        if user_info is None:
            user_info = UserInfo(id=user_info_key.string_id())
            user_info.put()
        
        pages = user_info.pages()
        
        template_values = {
            'pages' : pages,
            'user_info' : user_info,
            'session_info': UserInfo.session_info(self.username()),
        }
        template = JINJA_ENVIRONMENT.get_template('user.html')
        
        self.response.write(template.render(template_values))
        
class PostLoginHandler(RequestHandler):
    
    def get(self):
        user_info = UserInfo.get_current()
        if user_info is None:
            template = JINJA_ENVIRONMENT.get_template('post_login.html')
            
            self.response.write(template.render({'cancel_link':users.create_logout_url('/')}))
        else:
            #don't worry about redirects for now
            
            now = datetime.datetime.now()
            delta = datetime.timedelta(days=28)
            then = delta + now
            
            self.response.set_cookie('username',value=user_info.username,expires=then)
            
            self.redirect('/')

class PostLogoutHandler(RequestHandler):
    
    def get(self):
        self.redirect('/')
        self.response.delete_cookie('username')
        