import unittest

from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util


import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
from models import Page


class EventuallyConsistentTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        # Initialize the datastore stub with this policy.
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)

    def tearDown(self):
        self.testbed.deactivate()

    def testValidator(self):
    
        test_link_text = "a"*24
        test_content_text = "b"*24
        
        page = Page()
        page.link = test_link_text
        page.content = test_content_text
        page.put()
        
        self.assertEqual(page.link, test_link_text)
        self.assertEqual(page.content, test_content_text)
        
        page = Page()
        page.link = "<a>"+test_link_text+"</a>"
        page.content = "<a>"+test_content_text+"</a>"
        page.put()
        
        self.assertEqual(page.link, test_link_text)
        self.assertEqual(page.content, test_content_text)
        
        long_test_link_text = "a"*128
        long_test_content_text = "b"*512
        
        page = Page()
        page.link = long_test_link_text
        page.content = long_test_content_text
        page.put()
        
        trunc_test_link_text = "a"*64
        trunc_test_content_text = "b"*256
        
        self.assertEqual(page.link, trunc_test_link_text)
        self.assertEqual(page.content, trunc_test_content_text)
        
        page = Page()
        page.link = "<a>"+long_test_link_text+"</a>"
        page.content = "<a>"+long_test_content_text+"</a>"
        page.put()
        
        self.assertEqual(page.link, trunc_test_link_text)
        self.assertEqual(page.content, trunc_test_content_text)


if __name__ == '__main__':
    unittest.main()