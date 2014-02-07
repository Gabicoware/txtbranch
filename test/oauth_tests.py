import unittest
import logging
import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 

from handlers import AuthHandler


class EventuallyConsistentTestCase(unittest.TestCase):


    def testAuthAttributes(self):
        handler = AuthHandler()
        
        reddit_data = {u'link_karma': 28, u'over_18': False, u'id': u'ahzo1', u'has_verified_email': False, u'created': 1360171116.0, u'is_gold': False, u'comment_karma': 24, u'is_mod': False, u'name': u'Gabicoware_Dan', u'created_utc': 1360171116.0}
        
        attrs = handler._to_user_model_attrs(reddit_data, handler.USER_ATTRS['reddit'])
        
        logging.info(attrs)
        
        self.assertTrue(attrs['link'] == 'http://reddit.com/u/Gabicoware_Dan')
