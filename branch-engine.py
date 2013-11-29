import webapp2

from handlers import *

handlers = [
    ('/user', UserHandler),
    ('/page', HtmlPageHandler),
    ('/story', StoryHandler),
    ('/about', AboutHandler),
    ('/admin/story/new', CreateStoryHandler),
]

if config["stories"]["custom_enabled"]:
    handlers.append(('/story/new', CreateStoryHandler))
    handlers.append(('/', MainHandler))
else:
    handlers.append(('/', DefaultRedirectHandler))

application = webapp2.WSGIApplication(handlers, debug=True)
