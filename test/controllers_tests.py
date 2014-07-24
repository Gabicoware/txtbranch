import unittest

import time

from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util
from google.appengine.api import users


import os, sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir) 
from controllers import *
from models import *

base_tree_dict = {
            "tree_name":None,
            "moderatorname":None,
            "conventions":'',
            "root_branch_link":'testSaveTree.unique_link',
            "root_branch_content":'testSaveTree.unique_content',
            "link_prompt":"A",
            "link_max":100,
            "link_moderator_only":False,
            "content_prompt":"A",
            "content_max":100,
            "content_moderator_only":False,
            "branch_max":5,
}

def lj(result):
    if isinstance(result, list):
        return ','.join(result)
    else:
        return None

class BranchControllerTestCase(unittest.TestCase):
    
    def setUp(self):
                
        # the memcache will contain values that will break the tests
        # dont run this on production!
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
        
        tree_name = 'bc_' + str(millis % 3600000)
        
        username = 'bc_' + str(millis % 3600000)
        
        self.testbed.setup_env(USER_EMAIL=username + '@example.com', USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.user_info = UserInfo.put_new(username, users.get_current_user())
        
        tree_controller = TreeController()
        tree_controller.user_info = self.user_info
        tree_controller.google_user = users.get_current_user()
        
        tree_dict = base_tree_dict.copy()
        tree_dict['tree_name'] = tree_name
        tree_dict['moderatorname'] = username
        
        success, result = tree_controller.save_tree(tree_dict)
        
        if success:
            self.tree = result
        else:
            self.tree = None
        
        self.assertTrue(self.tree is not None, lj(result));
        
        self.parent_branch = Branch(id=tree_name)
        
        self.parent_branch.authorname = username
        self.parent_branch.link = ''
        self.parent_branch.content = ''
        self.parent_branch.tree_name = tree_name
        self.parent_branch.put()
        
    
        self.controller = BranchController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()
        
        self.child_branchs = []
        
    def tearDown(self):
        for branch in self.child_branchs:
            branch.key.delete()
        
        self.user_info.key.delete()
        self.parent_branch.key.delete()
        self.tree.key.delete()
        
        self.testbed.deactivate()

    def testEmptyBranchLink(self):
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), '', 'some_content')
        
        self.assertFalse(success)
        self.assertTrue('empty_branch_link' in result, lj(result))
        
    def testEmptyBranchContent(self):
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testEmptyBranchLink.unique_link', '')
        
        self.assertFalse(success)
        self.assertTrue('empty_branch_content' in result, lj(result))
        
    def testIdenticalLink(self):
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertTrue(success, lj(result))
        
        if success and result.key:
            self.child_branchs.append(result)
        
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertFalse(success)
        self.assertTrue('has_identical_link' in result, lj(result))
        
    def testRootBranchUpdate(self):
        newlink = 'testIdenticalLink.different_link'
        newcontent = 'different_content'
        success, result = self.controller.update_branch(self.user_info.username, self.parent_branch.key.urlsafe(), newlink, newcontent)
        
        self.assertTrue(success, lj(result))
        
        branch = result.key.get();
        
        self.child_branchs.append(result)
        
        self.child_branchs.append(branch)
        self.assertTrue(branch.link == newlink)
                
        self.assertTrue(branch.content == newcontent)
        
    def testUpdate(self):
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertTrue(success, lj(result))
        
        if success and result.key:
            self.child_branchs.append(result)
            
        newlink = 'testIdenticalLink.different_link'
        newcontent = 'different_content'
        success, result = self.controller.update_branch(self.user_info.username, result.key.urlsafe(), newlink, newcontent)
        
        self.assertTrue(success, lj(result))
        
        branch = result.key.get();
        
        self.assertTrue(branch.link == newlink)
                
        self.assertTrue(branch.content == newcontent)
        
    def testUpdateSameLink(self):
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertTrue(success, lj(result))
        
        if success and result.key:
            self.child_branchs.append(result)
            
        success, result = self.controller.update_branch(self.user_info.username, result.key.urlsafe(), result.link, result.content)
        
        self.assertTrue(success, lj(result))
        
    def testSaveBranch(self):
        
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testBranch.unique_link', 'testBranch.unique_content')
        
        self.assertTrue(success, lj(result))
        
    def testBranchMax(self):
        
        self.tree.branch_max = 1
        self.tree.put()
        
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testBranch.unique_link.1', 'testBranch.unique_content.1')
        
        self.assertTrue(success, lj(result))
        
        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testBranch.unique_link.2', 'testBranch.unique_content.2')
        
        self.assertFalse(success, lj(result))
        self.assertTrue('has_branches' in result, lj(result))
        
        self.tree.branch_max = 0;
        self.tree.put()

        success, result = self.controller.save_branch(self.user_info.username, self.parent_branch.key.urlsafe(), 'testBranch.unique_link.2', 'testBranch.unique_content.2')
        
        self.assertTrue(success, lj(result))
        
        
class TreeControllerTestCase(unittest.TestCase):
            
    def setUp(self):
        
        # the memcache will contain values that will break the tests
        # dont run this on production!
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
        
        self.testbed.setup_env(USER_EMAIL=username + '@example.com', USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.user_info = UserInfo.put_new(username, users.get_current_user())
    
        self.invalid_username = 'inv_u' + str(millis)
        
        self.invalid_user_info = UserInfo(id=self.invalid_username)
        self.invalid_user_info.date = datetime.datetime.now()
        self.invalid_user_info.put()
        
        self.controller = TreeController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()
        
    def tearDown(self):
        
        self.user_info.key.delete()
        self.invalid_user_info.key.delete()
        
        self.testbed.deactivate()


    def testSaveTree(self):        
        millis = int(round(time.time() * 1000))
        tree_name = 's' + str(millis)
        
        tree_dict = base_tree_dict.copy()
        
        tree_dict['tree_name'] = tree_name
        tree_dict['moderatorname'] = self.user_info.username
        
        success, result = self.controller.save_tree(tree_dict)
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success, lj(result))
        
        self.assertFalse(result.get_root_branch() is None)
        
        result.get_root_branch().key.delete()
        
        result.key.delete()
    
    
    def testErrors(self):
        
        tree_dict = base_tree_dict.copy()
        
        tree_dict['tree_name'] = 'some_name'
        tree_dict['moderatorname'] = None
        
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('unauthenticated' in result)
        
        tree_dict["moderatorname"] = 'DNE.'
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('unauthenticated' in result)
        
        tree_dict["moderatorname"] = self.invalid_username
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('unauthenticated' in result)
        
        tree_dict["tree_name"] = None
        tree_dict["moderatorname"] = self.user_info.username
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('empty_name' in result)
        
        tree_dict["tree_name"] = ''
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('empty_name' in result)
        
        tree_dict["tree_name"] = 'q q q q q '
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('invalid_name' in result)
    
        tree_dict["tree_name"] = 'TestTree'
        tree_dict["conventions"] = None
        tree_dict["root_branch_link"] = None
        tree_dict["root_branch_content"] = None
        success, result = self.controller.save_tree(tree_dict)
        
        self.assertFalse(success)
        self.assertTrue('empty_root_branch_link' in result)
        self.assertTrue('empty_root_branch_content' in result)
            
class BaseControllerTestCase(unittest.TestCase):
    
    def setUp(self):
        
        # the memcache will contain values that will break the tests
        # dont run this on production!
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
        
        self.testbed.setup_env(USER_EMAIL=username + '@example.com', USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.user_info = UserInfo.put_new(username, users.get_current_user())
    
        self.invalid_username = 'inv_u' + str(millis)
        
        self.invalid_user_info = UserInfo(id=self.invalid_username)
        self.invalid_user_info.date = datetime.datetime.now()
        self.invalid_user_info.put()
        
        self.controller = BaseController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()
        
    def tearDown(self):
        self.invalid_user_info.key.delete()
        self.user_info.key.delete()
        self.testbed.deactivate()
        
    def testCurrentUser(self):
        
        self.assertTrue(self.controller.is_user_info_current(self.user_info), "userinfo should be current")
        self.assertFalse(self.controller.is_user_info_current(self.invalid_user_info), "userinfo should not be current")
    
        
class LikeControllerTestCase(unittest.TestCase):
    
    def setUp(self):
        
        # the memcache will contain values that will break the tests
        # dont run this on production!
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
        
        self.testbed.setup_env(USER_EMAIL=username + '@example.com', USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.user_info = UserInfo.put_new(username, users.get_current_user())
    
        self.controller = LikeController();
        self.controller.user_info = self.user_info
        self.controller.google_user = users.get_current_user()

        self.branch = Branch(id="LikeControllerTestCase.branch" + str(millis))
        
        self.branch.put()
        
    def tearDown(self):
        self.user_info.key.delete()
        self.branch.key.delete()
        self.testbed.deactivate()
        
    def testLike(self):
        
        branch_urlsafe_key = self.branch.key.urlsafe()
        
        like_value = '1'
            
        success, result = self.controller.set_like(branch_urlsafe_key, like_value)
        
        self.assertTrue(success, lj(result))
        self.assertEquals(result.value, 1)
        
        result.key.delete()
            
           
if __name__ == '__main__':
    unittest.main()
