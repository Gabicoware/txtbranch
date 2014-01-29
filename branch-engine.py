from secrets import SESSION_KEY

from webapp2 import WSGIApplication, Route

from handlers import *


# webapp2 config
app_config = {
  'webapp2_extras.sessions': {
    'cookie_name': '_simpleauth_sess',
    'secret_key': SESSION_KEY
  },
  'webapp2_extras.auth': {
    'user_attributes': []
  }
}

handlers = [
    (r'/user/([\d\w_\-]+)', UserHandler),
    ('/login', LoginHandler),
    ('/post_login', PostLoginHandler),
    ('/post_logout', PostLogoutHandler),
    ('/about', AboutHandler),
    ('/', MainHandler),
    ('/tree/new', CreateTreeHandler),
    (r'/tree/([\d\w_\-]+)/edit', EditTreeHandler),
    (r'/tree/([\d\w_\-]+)', TreeHandler),
  Route('/login', handler='handlers.LoginHandler:login', name='login'),
  Route('/google_login', handler='handlers.LoginHandler:google_login', name='google_login'),
  Route('/logout', handler='handlers.AuthHandler:logout', name='logout'),
  Route('/auth/<provider>', 
    handler='handlers.AuthHandler:_simple_auth', name='auth_login'),
  Route('/auth/<provider>/callback', 
    handler='handlers.AuthHandler:_auth_callback', name='auth_callback')
]

application = WSGIApplication(handlers, config=app_config, debug=True)
