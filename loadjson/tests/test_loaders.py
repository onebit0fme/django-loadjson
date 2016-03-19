from __future__ import unicode_literals
from django.test import TestCase
from loadjson.loaders import TransferData, LoadNotConfigured


class LoadersTest(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_loader_no_data(self):
        with self.assertRaises(LoadNotConfigured) as err:
            TransferData(data_name='test_data')
        self.assertTrue("Can't find data" in str(err.exception))
