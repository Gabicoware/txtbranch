import webapp2

from handlers import *

handlers = [
    (r'/user/([\d\w_\-]+)', UserHandler),
    ('/post_login', PostLoginHandler),
    ('/post_logout', PostLogoutHandler),
    ('/about', AboutHandler),
    ('/', MainHandler),
    ('/tree/new', CreateTreeHandler),
    (r'/tree/([\d\w_\-]+)/edit', EditTreeHandler),
    (r'/tree/([\d\w_\-]+)', TreeHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)
