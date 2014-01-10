import webapp2

from handlers import CreateTreeHandler, EditTreeHandler

handlers = [
    ('/admin/tree/new', CreateTreeHandler),
    ('/admin/tree/edit/([\d\w_\-]+)', EditTreeHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)