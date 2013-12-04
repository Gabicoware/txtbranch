import webapp2

from handlers import *

handlers = [
    ('/user', UserHandler),
    ('/page', HtmlPageHandler),
    ('/story', StoryHandler),
    ('/about', AboutHandler),
    ('/admin/story/new', CreateStoryHandler),
    ('/', MainHandler),
]

if config["stories"]["custom_enabled"]:
    handlers.append(('/story/new', CreateStoryHandler))

application = webapp2.WSGIApplication(handlers, debug=True)
