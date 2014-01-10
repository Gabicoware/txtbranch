import unittest

import time
import webapp2

from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util
from google.appengine.api import memcache


import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
from controllers import *
from models import *
import api


class LikeAPITestCase(unittest.TestCase):
    
    user_info = None
    branch = None
    
    def setUp(self):
        #the memcache will contain values that will break the tests
        #dont run this on production!
        memcache.flush_all()
        
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        # Initialize the datastore stub with this policy.
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        
        millis = int(round(time.time() * 1000))
        strmillis = str(millis)
        username = 'test_user' + strmillis
        
        self.testbed.setup_env(USER_EMAIL=username+'@example.com',USER_ID=strmillis, USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.user_info = UserInfo.put_new(username)
        
        self.branch = Branch()
        self.branch.link = "link"+strmillis
        self.branch.content = "content"+strmillis
        
        self.branch.tree_name = "tree_name"+strmillis
        self.branch.authorname = "branchauthorname"+strmillis
        self.branch.put()
        
        
        
    def testLikeAPI(self):
        # Build a request object passing the URI path to be tested.
        # You can also pass headers, query arguments etc.
        cookie = "username=\""+str(self.user_info.username)+"\""
        #logging.info(cookie)
        #cookie = "username=\"test_user1387317668650:False:185804764220139124118\""
        headers = [("Cookie",cookie)] 
        #"username=\""+self.user_info.username+"\"")]
        request = webapp2.Request.blank('/api/v1/likes?value=1&branch_key='+self.branch.key.urlsafe(),headers=headers)
        request.method = "GET"
        
        response = request.get_response(api.application)
        
        # Let's check if the response is correct.
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body, "OK")
    
    def tearDown(self):
        
        self.testbed.deactivate()
        
if __name__ == '__main__':
    unittest.main()