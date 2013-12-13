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
        
        self.testbed.setup_env(USER_EMAIL='usermail@example.com',USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
        
        millis = int(round(time.time() * 1000))
        
        story_name = 'test_story' + str(millis)
        
        logging.info(story_name)
        
        self.story = Story(id=story_name,name=story_name)
        self.story.conventions = ''
        self.story.put()
        
        self.parent_page = Page(id=story_name)
        
        self.parent_page.link = ''
        self.parent_page.content = ''
        self.parent_page.story = self.story.key
        self.parent_page.put()
        
        self.story.put()
        
    
    def tearDown(self):
        for page in self.child_pages:
            page.key.delete()
        
        self.parent_page.key.delete()
        self.story.key.delete()
        
        self.testbed.deactivate()

    def testEmptyPageLink(self):
        success, object = PageController.save_page('dummy_author',self.parent_page.key.urlsafe(),'','some_content')
        
        self.assertFalse(success)
        self.assertTrue(object['empty_page_link'])
        
    def testEmptyPageContent(self):
        success, object = PageController.save_page('dummy_author',self.parent_page.key.urlsafe(),'testEmptyPageLink.unique_link','')
        
        self.assertFalse(success)
        self.assertTrue(object['empty_page_content'])
        
    def testIdenticalLink(self):
        success, object = PageController.save_page('dummy_author',self.parent_page.key.urlsafe(),'testIdenticalLink.some_link','some_content')
        
        if success == False:
            logging.info(object)
            
        self.assertTrue(success)
        
        
        if success and object.key:
            self.child_pages.append(object)
        
        success, object = PageController.save_page('dummy_author',self.parent_page.key.urlsafe(), 'testIdenticalLink.some_link', 'some_content')
        
        self.assertFalse(success)
        self.assertTrue(object['has_identical_link'])
        
    def testSavePage(self):
        success, object = PageController.save_page('dummy_author', self.parent_page.key.urlsafe(), 'testPage.unique_link', 'testPage.unique_content' )
        
        if success == False:
            logging.info(object)
        
        self.assertTrue(success)
        
class StoryControllerTestCase(unittest.TestCase):
    
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
        
        self.testbed.setup_env(USER_EMAIL='usermail@example.com',USER_ID='1', USER_IS_ADMIN='0')
        self.testbed.init_user_stub()
    
    
    def testSaveStory(self):        
        millis = int(round(time.time() * 1000))
        story_name = 'testSaveStory.test_story' + str(millis)
        
        success, object = StoryController.save_story( story_name,'dummy_author','', 'testSaveStory.unique_link', 'testSaveStory.unique_content' )
        
        if success == False:
            logging.info(object)
        
        self.assertTrue(success)
        
        self.assertFalse(object.get_root_page() is None)
        
        object.get_root_page().key.delete()
        
        object.key.delete()
        
    def tearDown(self):
        
        self.testbed.deactivate()
        
if __name__ == '__main__':
    unittest.main()
