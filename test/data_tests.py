import unittest
import time

from google.appengine.api import memcache

from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util


import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
from models import Branch


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
        
        branch = Branch()
        branch.link = test_link_text
        branch.content = test_content_text
        branch.put()
        
        self.assertEqual(branch.link, test_link_text)
        self.assertEqual(branch.content, test_content_text)
        
        branch = Branch()
        branch.link = "<a>"+test_link_text+"</a>"
        branch.content = "<a>"+test_content_text+"</a>"
        branch.put()
        
        self.assertEqual(branch.link, test_link_text)
        self.assertEqual(branch.content, test_content_text)
        
#         long_test_link_text = "a"*128
#         long_test_content_text = "b"*512
#         
#         branch = Branch()
#         branch.link = long_test_link_text
#         branch.content = long_test_content_text
#         branch.put()
#         
#         trunc_test_link_text = "a"*64
#         trunc_test_content_text = "b"*256
#         
#         self.assertEqual(branch.link, trunc_test_link_text)
#         self.assertEqual(branch.content, trunc_test_content_text)
#         
#         branch = Branch()
#         branch.link = "<a>"+long_test_link_text+"</a>"
#         branch.content = "<a>"+long_test_content_text+"</a>"
#         branch.put()
#         
#         self.assertEqual(branch.link, trunc_test_link_text)
#         self.assertEqual(branch.content, trunc_test_content_text)


class BranchTestCase(unittest.TestCase):
    
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
        
        tree_name = 'test_tree' + str(millis)
        
        username = 'test_user' + str(millis)
        
        self.parent_branch = Branch(id=tree_name)
        
        self.parent_branch.author_name = username
        self.parent_branch.link = ''
        self.parent_branch.content = ''
        self.parent_branch.put()
        
        self.child_branchs = []
        
    def tearDown(self):
        for branch in self.child_branchs:
            branch.key.delete()
        
        self.parent_branch.key.delete()
        
        self.testbed.deactivate()
        
    def testUpdateNoDuplicate(self):
        
        
        branch = Branch()
        branch.link = 'testIdenticalLink.some_link'
        branch.content = 'some_content'
        
        branch.revision = 0
        branch.parent_branch = self.parent_branch.key
        branch.parent_branch_authorname = self.parent_branch.authorname
        branch.put()
        
        self.parent_branch.append_child(branch)
        
        self.assertTrue(len(self.parent_branch.children()) == 1)
        
        self.child_branchs.append(branch)
   
if __name__ == '__main__':
    unittest.main()