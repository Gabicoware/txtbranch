import unittest

import time

from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util
from google.appengine.api import memcache, users


import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
from controllers import *
from models import *


class BranchControllerTestCase(unittest.TestCase):
    
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
        
        self.parent_branch.authorname = username
        self.parent_branch.link = ''
        self.parent_branch.content = ''
        self.parent_branch.tree = self.tree.key
        self.parent_branch.put()
        
        self.user_info = UserInfo.put_new(username,users.get_current_user())
    
        self.controller = BranchController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()
        
        self.child_branchs = []
        
    def tearDown(self):
        for branch in self.child_branchs:
            branch.key.delete()
        
        self.parent_branch.key.delete()
        self.tree.key.delete()
        
        self.testbed.deactivate()

    def testEmptyBranchLink(self):
        success, result = self.controller.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'','some_content')
        
        self.assertFalse(success)
        self.assertTrue('empty_branch_link' in result)
        
    def testEmptyBranchContent(self):
        success, result = self.controller.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'testEmptyBranchLink.unique_link','')
        
        self.assertFalse(success)
        self.assertTrue('empty_branch_content' in result)
        
    def testIdenticalLink(self):
        success, result = self.controller.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'testIdenticalLink.some_link','some_content')
        
        if success == False:
            logging.info(result)
            
        self.assertTrue(success)
        
        
        if success and result.key:
            self.child_branchs.append(result)
        
        success, result = self.controller.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertFalse(success)
        self.assertTrue('has_identical_link' in result)
        
    def testRootBranchUpdate(self):
        newlink = 'testIdenticalLink.different_link'
        newcontent = 'different_content'
        success, result = self.controller.update_branch(self.user_info.username,self.parent_branch.key.urlsafe(),newlink,newcontent)
        
        self.assertTrue(success)
        
        branch = result.key.get();
        
        self.assertTrue(branch.link == newlink)
                
        self.assertTrue(branch.content == newcontent)
        
    def testUpdate(self):
        success, result = self.controller.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'testIdenticalLink.some_link','some_content')
        
        self.assertTrue(success)
        
        if success and result.key:
            self.child_branchs.append(result)
            
        newlink = 'testIdenticalLink.different_link'
        newcontent = 'different_content'
        success, result = self.controller.update_branch(self.user_info.username,result.key.urlsafe(),newlink,newcontent)
        
        self.assertTrue(success)
        
        branch = result.key.get();
        
        self.assertTrue(branch.link == newlink)
                
        self.assertTrue(branch.content == newcontent)
        
    def testUpdateSameLink(self):
        success, result = self.controller.save_branch(self.user_info.username,self.parent_branch.key.urlsafe(),'testIdenticalLink.some_link','some_content')
        
        self.assertTrue(success)
        
        if success and result.key:
            self.child_branchs.append(result)
            
        success, result = self.controller.update_branch(self.user_info.username,result.key.urlsafe(),result.link,result.content)
        
        self.assertTrue(success)
        
    def testSaveBranch(self):
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testBranch.unique_link', 'testBranch.unique_content' )
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success)
        
class TreeControllerTestCase(unittest.TestCase):
            
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
        
        self.user_info = UserInfo.put_new(username,users.get_current_user())
    
        self.invalid_username = 'inv_u' + str(millis)
        
        self.invalid_user_info = UserInfo(id=self.invalid_username)
        self.invalid_user_info.date = datetime.datetime.now()
        self.invalid_user_info.put()
        
        self.controller = TreeController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()
        
    def testSaveTree(self):        
        millis = int(round(time.time() * 1000))
        tree_name = 's' + str(millis)
        
        success, result = self.controller.save_tree( tree_name,self.user_info.username,'', 'testSaveTree.unique_link', 'testSaveTree.unique_content' )
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success)
        
        self.assertFalse(result.get_root_branch() is None)
        
        result.get_root_branch().key.delete()
        
        result.key.delete()
    
    
    def testErrors(self):
        
        success, result = self.controller.save_tree( 'some_name',None,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue('unauthenticated' in result)
    
        success, result = self.controller.save_tree( 'some_name','DNE.','',None,None)
        
        self.assertFalse(success)
        self.assertTrue('unauthenticated' in result)
        
        success, result = self.controller.save_tree( 'some_name',self.invalid_username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue('unauthenticated' in result)
        
        success, result = self.controller.save_tree( None,self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue('empty_name' in result)
        
        success, result = self.controller.save_tree( '',self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue('empty_name' in result)
        
        success, result = self.controller.save_tree( 'q q q q q ',self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue('invalid_name' in result)
    
        success, result = self.controller.save_tree( 'TestTree',self.user_info.username,None,None,None)
        
        self.assertFalse(success)
        self.assertTrue('empty_root_branch_link' in result)
        self.assertTrue('empty_root_branch_content' in result)
    
    def tearDown(self):
        
        self.testbed.deactivate()
        
class BaseControllerTestCase(unittest.TestCase):
    
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
        
        self.user_info = UserInfo.put_new(username,users.get_current_user())
    
        self.invalid_username = 'inv_u' + str(millis)
        
        self.invalid_user_info = UserInfo(id=self.invalid_username)
        self.invalid_user_info.date = datetime.datetime.now()
        self.invalid_user_info.put()
        
        self.controller = BaseController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()
        
    def testCurrentUser(self):
        
        self.assertTrue(self.controller.is_user_info_current(self.user_info),"userinfo should be current")
        self.assertFalse(self.controller.is_user_info_current(self.invalid_user_info),"userinfo should not be current")
    
    def tearDown(self):
        
        self.testbed.deactivate()
        
class LikeControllerTestCase(unittest.TestCase):
    
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
        
        self.user_info = UserInfo.put_new(username,users.get_current_user())
    
        self.controller = LikeController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()

        self.branch = Branch(id="LikeControllerTestCase.branch"+str(millis))
        
        self.branch.put()
        
    def testLike(self):
        
        branch_urlsafe_key = self.branch.key.urlsafe()
        
        like_value = '1'
            
        success, result = self.controller.set_like( branch_urlsafe_key, like_value)
        
        self.assertTrue(success)
        self.assertEquals(result.value,1)
    
    def tearDown(self):
        
        self.testbed.deactivate()
                
if __name__ == '__main__':
    unittest.main()
