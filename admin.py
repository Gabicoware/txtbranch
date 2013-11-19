import webapp2

from handlers import CreateStoryHandler

handlers = [
    ('/admin/story/new', CreateStoryHandler),
]

application = webapp2.WSGIApplication(handlers, debug=True)