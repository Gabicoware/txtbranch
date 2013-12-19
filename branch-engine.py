import webapp2

from handlers import *

handlers = [
    (r'/user/([\d\w_\-]+)', UserHandler),
    ('/post_login', PostLoginHandler),
    ('/post_logout', PostLogoutHandler),
    ('/about', AboutHandler),
    ('/', MainHandler),
    ('/story/new', CreateStoryHandler),
    (r'/story/([\d\w_\-]+)/edit', EditStoryHandler),
    (r'/story/([\d\w_\-]+)', StoryHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)
