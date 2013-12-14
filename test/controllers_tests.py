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


class PageControllerTestCase(unittest.TestCase):
    
    parent_page = None
    
    user_info = None
    
    story = None
    
    child_pages = []
    
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
        
        story_name = 'test_story' + str(millis)
        
        username = 'test_user' + str(millis)
        
        self.testbed.setup_env(USER_EMAIL=username+'@example.com',USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        self.story = Story(id=story_name,name=story_name)
        self.story.conventions = ''
        self.story.put()
        
        
        
        self.parent_page = Page(id=story_name)
        
        self.parent_page.link = ''
        self.parent_page.content = ''
        self.parent_page.story = self.story.key
        self.parent_page.put()
        
        self.user_info = UserInfo.put_new(username)
    
    def tearDown(self):
        for page in self.child_pages:
            page.key.delete()
        
        self.parent_page.key.delete()
        self.story.key.delete()
        
        self.testbed.deactivate()

    def testEmptyPageLink(self):
        success, result = PageController.save_page(self.user_info.username,self.parent_page.key.urlsafe(),'','some_content')
        
        self.assertFalse(success)
        self.assertTrue(result['empty_page_link'])
        
    def testEmptyPageContent(self):
        success, result = PageController.save_page(self.user_info.username,self.parent_page.key.urlsafe(),'testEmptyPageLink.unique_link','')
        
        self.assertFalse(success)
        self.assertTrue(result['empty_page_content'])
        
    def testIdenticalLink(self):
        success, result = PageController.save_page(self.user_info.username,self.parent_page.key.urlsafe(),'testIdenticalLink.some_link','some_content')
        
        if success == False:
            logging.info(result)
            
        self.assertTrue(success)
        
        
        if success and result.key:
            self.child_pages.append(result)
        
        success, result = PageController.save_page(self.user_info.username,self.parent_page.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertFalse(success)
        self.assertTrue(result['has_identical_link'])
        
    def testSavePage(self):
        success, result = PageController.save_page(self.user_info.username, self.parent_page.key.urlsafe(), 'testPage.unique_link', 'testPage.unique_content' )
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success)
        
class StoryControllerTestCase(unittest.TestCase):
    
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
        
    def testSaveStory(self):        
        millis = int(round(time.time() * 1000))
        story_name = 's' + str(millis)
        
        success, result = StoryController.save_story( story_name,self.user_info.username,'', 'testSaveStory.unique_link', 'testSaveStory.unique_content' )
        
        if success == False:
            logging.info(result)
        
        self.assertTrue(success)
        
        self.assertFalse(result.get_root_page() is None)
        
        result.get_root_page().key.delete()
        
        result.key.delete()
    
    
    def testErrors(self):
        
        success, result = StoryController.save_story( 'some_name',None,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['unauthenticated'])
    
        success, result = StoryController.save_story( 'some_name','DNE.','',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['unauthenticated'])
        
        success, result = StoryController.save_story( 'some_name',self.invalid_username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['unauthenticated'])
        
        success, result = StoryController.save_story( None,self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['empty_name'])
        
        success, result = StoryController.save_story( '',self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['empty_name'])
        
        success, result = StoryController.save_story( 'q q q q q ',self.user_info.username,'',None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['invalid_name'])
    
        success, result = StoryController.save_story( 'TestStory',self.user_info.username,None,None,None)
        
        self.assertFalse(success)
        self.assertTrue(result['empty_root_page_link'])
        self.assertTrue(result['empty_root_page_content'])
    
    
    
    
    
    
    
    
    
    def tearDown(self):
        
        self.testbed.deactivate()
        
if __name__ == '__main__':
    unittest.main()
