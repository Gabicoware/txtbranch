import webapp2

from handlers import CreateStoryHandler, EditStoryHandler

handlers = [
    ('/admin/story/new', CreateStoryHandler),
    ('/admin/story/edit/([\d\w_\-]+)', EditStoryHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)