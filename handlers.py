#TODO: USER CAN SUBMIT 1 BRANCH PER PARENT, and only after 5 minutes

#TODO AUTOMATICALLY TEST SYSTEM LIMITS

#TODO: Make adding a page an in page experience
#TODO: figure out limits to branch count

#TODO: user_id instead of UserProperty
#TODO: Ranking algorithm

import os
import webapp2
import json

from defaulttext import *
from models import *
from controllers import *
import jinja2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

class MainHandler(webapp2.RequestHandler):
    
    def get(self):
        stories_query = Story.query()
        stories = stories_query.fetch(10)
        
        story_links = []
        
        for story in stories:
            query_params = {'story_name': story.name}
            href = '/story?%s' % (urllib.urlencode(query_params))
            story_links.append(( href, story.name ))
        
        template_values = {
            'is_home': True,
            'story_links': story_links,
            'user_key': UserInfo.get_current_key(),
            'session_info': UserInfo.session_info(self.request.uri),
        }
        
        template = JINJA_ENVIRONMENT.get_template('main.html')
        self.response.write(template.render(template_values))
        # Write the submission form and the footer of the page

class DefaultRedirectHandler(webapp2.RequestHandler):
    
    def get(self):
        query_params = {'story_name': config["stories"]["default_name"]}
        redirect_url = '/story?%s' % (urllib.urlencode(query_params))
        self.redirect(redirect_url)

class CreateStoryHandler(webapp2.RequestHandler):
    
    _create_story_lock = threading.Lock()
    
    def get(self):
        self.render_create_story_form()
        
    def post(self):
        story_name = self.request.get('story_name',DEFAULT_STORY_NAME)
        
        success, story = StoryController.save_story(story_name,
          self.request.get('introduction', DEFAULT_INTRODUCTION),
          self.request.get('conventions', DEFAULT_CONVENTIONS),
          self.request.get('root_page_link',''),
          self.request.get('root_page_content',''))
        
        if success:
            query_params = {'story_name': story_name}
            redirect_url = '/story?' + urllib.urlencode(query_params)
        
            self.redirect(redirect_url)
        else:
            self.render_create_story_form(story)
    
    def render_create_story_form(self,errors=None):
        template = JINJA_ENVIRONMENT.get_template('new_story.html')
        template_values = {
            'session_info': UserInfo.session_info(self.request.uri),
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
        
        
class StoryHandler(webapp2.RequestHandler):
    def get(self):
        story_name = self.request.get('story_name',DEFAULT_STORY_NAME)
        
        key = Story.create_key(story_name)
        
        story = key.get()
        
        if story:
        
            root_page = story.get_root_page()
            
            root_page_href = ''
            root_page_link = ''
            
            if root_page:
                root_page_href = page_url(story_name, root_page.key)
                root_page_link = root_page.link
            else:
                logging.error("root_page not found for Story(id='%s')"%story_name)
            
            template_values = {
                'root_page_href': root_page_href,
                'root_page_link': root_page_link,
                'story': story,
                'session_info': UserInfo.session_info(self.request.uri),
            }
            
            template = JINJA_ENVIRONMENT.get_template('story.html')
            self.response.write(template.render(template_values))
        else:
            template_values = {
                'story_name': story_name,
                'session_info': UserInfo.session_info(self.request.uri),
            }
            template = JINJA_ENVIRONMENT.get_template('story_not_found.html')
            self.response.status = 404
            self.response.write(template.render(template_values))
        

class HtmlPageHandler(webapp2.RequestHandler):

    def get(self):
        
        template_values = {
            'session_info': UserInfo.session_info(self.request.uri),
            'link_max' : config["pages"]["link_max"],
            'content_max' : config["pages"]["content_max"],
        }
        
        template = JINJA_ENVIRONMENT.get_template('page.html')
        self.response.write(template.render(template_values))
        
class AboutHandler(webapp2.RequestHandler):

    def get(self):
        
        template_values = {
            'session_info': UserInfo.session_info(self.request.uri),
            'is_about': True,
        }
        template = JINJA_ENVIRONMENT.get_template('about.html')
        self.response.write(template.render(template_values))

class UserHandler(webapp2.RequestHandler):
    
    def get(self):
        
        
        user_urlsafe_key = self.request.get('user_key')
        user_info_key = ndb.Key(urlsafe=user_urlsafe_key)
        
        user_info = user_info_key.get()
        
        if user_info is None:
            user_info = UserInfo(id=user_info_key.string_id())
            user_info.put()
        
        pages = user_info.pages()
        
        template_values = {
            'pages' : pages,
            'user_info' : user_info,
            'session_info': UserInfo.session_info(self.request.uri),
        }
        if user_info_key == UserInfo.get_current_key():
            template = JINJA_ENVIRONMENT.get_template('profile.html')
        else:
            template = JINJA_ENVIRONMENT.get_template('user.html')
        
        self.response.write(template.render(template_values))