import unittest

import time

from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util
from google.appengine.api import memcache


import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
from controllers import *
from models import *


class BranchControllerTestCase(unittest.TestCase):
    
    parent_branch = None
    
    user_info = None
    
    tree = None
    
    child_branchs = []
    
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
        
        self.testbed.setup_env(USER_EMAIL=username+'@example.com',USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.tree = Tree(id=tree_name,name=tree_name)
        self.tree.conventions = ''
        self.tree.put()
        
        
        
        self.parent_branch = Branch(id=tree_name)
        
        self.parent_branch.link = ''
        self.parent_branch.content = ''
        self.parent_branch.tree = self.tree.key
        self.parent_branch.put()
        
        self.user_info = UserInfo.put_new(username)
    
    def tearDown(self):
        for branch in self.child_branchs:
            branch.key.delete()
        
        self.parent_branch.key.delete()
        self.tree.key.delete()
        
        self.testbed.deactivate()

    def testEmptyBranchLink(self):
        success, result = BranchController.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'','some_content')
        
        self.assertFalse(success)
        self.assertTrue(result['empty_branch_link'])
        
    def testEmptyBranchContent(self):
        success, result = BranchController.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'testEmptyBranchLink.unique_link','')
        
        self.assertFalse(success)
        self.assertTrue(result['empty_branch_content'])
        
    def testIdenticalLink(self):
        success, result = BranchController.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'testIdenticalLink.some_link','some_content')
        
        if success == False:
            logging.info(result)
            
        self.assertTrue(success)
        
        
        if success and result.key:
            self.child_branchs.append(result)
        
        success, result = BranchController.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertFalse(success)
        self.assertTrue(result['has_identical_link'])
        
    def testSaveBranch(self):
        success, result = BranchController.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testBranch.unique_link', 'testBranch.unique_content' )
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success)
        
class TreeControllerTestCase(unittest.TestCase):
    
    user_info = None
    invalid_user_info = None
    invalid_username = None
    
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
        
        username = 'test_user' + str(millis)
        
        self.testbed.setup_env(USER_EMAIL=username+'@example.com',USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.user_info = UserInfo.put_new(username)
    
        self.invalid_username = 'inv_u' + str(millis)
        
        self.invalid_user_info = UserInfo(id=self.invalid_username)
        self.invalid_user_info.date = datetime.datetime.now()
        self.invalid_user_info.put()
        
    def testSaveTree(self):        
        millis = int(round(time.time() * 1000))
        tree_name = 's' + str(millis)
        
        success, result = TreeController.save_tree( tree_name,self.user_info.username,'', 'testSaveTree.unique_link', 'testSaveTree.unique_content' )
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success)
        
        self.assertFalse(result.get_root_branch() is None)
        
        result.get_root_branch().key.delete()
        
        result.key.delete()
    
    
    def testErrors(self):
        
        success, result = TreeController.save_tree( 'some_name',None,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['unauthenticated'])
    
        success, result = TreeController.save_tree( 'some_name','DNE.','',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['unauthenticated'])
        
        success, result = TreeController.save_tree( 'some_name',self.invalid_username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['unauthenticated'])
        
        success, result = TreeController.save_tree( None,self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['empty_name'])
        
        success, result = TreeController.save_tree( '',self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['empty_name'])
        
        success, result = TreeController.save_tree( 'q q q q q ',self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['invalid_name'])
    
        success, result = TreeController.save_tree( 'TestTree',self.user_info.username,None,None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['empty_root_branch_link'])
        self.assertTrue(result['empty_root_branch_content'])
    
    
    
    
    
    
    
    
    
    def tearDown(self):
        
        self.testbed.deactivate()
        
if __name__ == '__main__':
    unittest.main()
