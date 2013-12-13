import webapp2

from handlers import *

handlers = [
    (r'/user/([\d\w_\-]+)', UserHandler),
    ('/post_login', PostLoginHandler),
    ('/post_logout', PostLogoutHandler),
    ('/story/([\d\w_\-]+)', StoryHandler),
    ('/about', AboutHandler),
    ('/admin/story/new', CreateStoryHandler),
    ('/admin/edit/([\d\w_\-]+)', EditStoryHandler),
    ('/', MainHandler),
]

if config["stories"]["custom_enabled"]:
    handlers.append(('/story/new', CreateStoryHandler))

application = webapp2.WSGIApplication(handlers, debug=True)
