from __future__ import unicode_literals
import dateutil.parser
from django.test import TestCase
from loadjson.loaders import TransferData, LoadNotConfigured
from loadjson.tests.models import MyModel


class LoadersTest(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_loader_no_data(self):
        with self.assertRaises(LoadNotConfigured) as err:
            TransferData(data_name='test_data')
        self.assertTrue("Can't find data" in str(err.exception))

    def test_loader_no_manifest(self):
        with self.assertRaises(LoadNotConfigured) as err:
            TransferData(data_name='dataset_no_manifest')
        self.assertTrue("Can't find manifest" in str(err.exception))

    def test_loader_manual_manifest(self):
        manifest = {"model": "tests.MyModel", "mapping": {}}
        td = TransferData(data_name='dataset_no_manifest', manifest=manifest)
        self.assertEqual(td.manifest, manifest)

    def test_loader_manual_data(self):
        data = {"id": "123", "foo": "bar"}
        td = TransferData(data_name='dataset_one', data=data)
        self.assertEqual(td.data, data)

    def test_loader_basic_field_import(self):
        data = [{"name": "Test CharField",
                 "description": "Test TextField",
                 "is_truthy": True,
                 "number": 345}]
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "text_field": "description",
                                "bool_field": "is_truthy",
                                "int_field": "number"}}
        td = TransferData(data=data, manifest=manifest)
        imported_objects = td.import_data()
        self.assertIsInstance(imported_objects[0], MyModel)
        self.assertEqual(imported_objects[0].char_field, data[0]['name'])
        self.assertEqual(imported_objects[0].text_field, data[0]['description'])
        self.assertEqual(imported_objects[0].bool_field, data[0]['is_truthy'])
        self.assertEqual(imported_objects[0].int_field, data[0]['number'])

    def test_loader_date_fields_no_parser(self):
        data = [{"some_date": "2016-03-08",
                 "some_datetime": "2016-03-08T21:45:00Z"}]
        manifest = {"model": "tests.MyModel",
                    "mapping": {"datetime_field": "some_datetime",
                                "date_field": "some_date"}}
        td = TransferData(data=data, manifest=manifest)
        imported_objects = td.import_data()
        self.assertIsInstance(imported_objects[0], MyModel)
        self.assertNotEqual(imported_objects[0].date_field, dateutil.parser.parse(data[0]['some_date']).date())
        self.assertNotEqual(imported_objects[0].datetime_field, dateutil.parser.parse(data[0]['some_datetime']))

    def test_field_path(self):
        data = {"object": {"name": "Test CharField",
                           "description": {"content": "Test TextField"},
                           "other": {"some_field": {"is_truthy": True,
                                                    "number": 345}}}}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "object.name",
                                "text_field": "object.description.content",
                                "bool_field": "object.other.some_field.is_truthy",
                                "int_field": "object.other.some_field.number"}}
        td = TransferData(data=[data], manifest=manifest)
        imported_objects = td.import_data()
        self.assertIsInstance(imported_objects[0], MyModel)
        self.assertEqual(imported_objects[0].char_field, data['object']['name'])
        self.assertEqual(imported_objects[0].text_field, data['object']['description']['content'])
        self.assertEqual(imported_objects[0].bool_field, data['object']['other']['some_field']['is_truthy'])
        self.assertEqual(imported_objects[0].int_field, data['object']['other']['some_field']['number'])
