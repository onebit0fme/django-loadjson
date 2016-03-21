from __future__ import unicode_literals
import dateutil.parser
from django.test import TestCase
from loadjson.loaders import TransferData, RelativeKeyDoesNotExist, InvalidManifest
from loadjson.tests.models import MyModel, MyRelatedModel


class BaseTestCase(TestCase):

    def import_related(self):
        td = TransferData(data_name='related_data')
        td.import_data()


class ParsersTest(BaseTestCase):

    def test_datetime_parser(self):
        data = [{"some_date": "2016-03-08",
                 "some_datetime": "2016-03-08T21:45:00Z"}]
        manifest = {"model": "tests.MyModel",
                    "mapping": {"datetime_field": "some_datetime",
                                "date_field": "some_date"},
                    "parsers": {"datetime_field": {"type": "datetime"},
                                "date_field": {"type": "datetime"}}}
        td = TransferData(data=data, manifest=manifest)
        self.assertEqual(td.data, data)
        self.assertEqual(td.manifest, manifest)
        imported_objects = td.import_data()
        self.assertIsInstance(imported_objects[0], MyModel)
        self.assertEqual(imported_objects[0].datetime_field, dateutil.parser.parse(data[0]['some_datetime']))
        self.assertEqual(imported_objects[0].date_field, dateutil.parser.parse(data[0]['some_date']))

    def test_string_parser(self):
        data = [{"name": "Some string",
                 "number": 35,
                 "decimal": 2.54,
                 "bool": True,
                 "list": [1, 2, 3],
                 "object": {"foo": "bar", "boo": 123}}]
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name"},
                    "parsers": {"char_field": {"type": "string"}}}
        td = TransferData(data=data, manifest=manifest)
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].char_field, data[0]['name'])
        # int to string
        td.manifest['mapping']['char_field'] = "number"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].char_field, str(data[0]['number']))
        # decimal to string
        td.manifest['mapping']['char_field'] = "decimal"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].char_field, str(data[0]['decimal']))
        # boolean to string
        td.manifest['mapping']['char_field'] = "bool"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].char_field, str(data[0]['bool']))
        # list to string
        td.manifest['mapping']['char_field'] = "list"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].char_field, str(data[0]['list']))
        # object to string
        td.manifest['mapping']['char_field'] = "object"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].char_field, str(data[0]['object']))

    def test_integer_parser(self):
        data = [{"string_int": "34",
                 "string": "foo",
                 "int": 32,
                 "decimal": 3.55,
                 "bool": True,
                 "invalid": {"foo": 123}}]
        manifest = {"model": "tests.MyModel",
                    "mapping": {"int_field": "int"},
                    "parsers": {"int_field": {"type": "integer"}}}
        td = TransferData(data=data, manifest=manifest)
        imported_objects = td.import_data()
        self.assertEqual(len(imported_objects), 1)
        self.assertEqual(imported_objects[0].int_field, data[0]['int'])
        # int string to int
        td.manifest['mapping']['int_field'] = "string_int"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].int_field, 34)
        # decimal to int
        td.manifest['mapping']['int_field'] = "decimal"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].int_field, 3)
        # bool to int
        td.manifest['mapping']['int_field'] = "bool"
        imported_objects = td.import_data()
        self.assertEqual(imported_objects[0].int_field, 1)
        # INVALID
        # invalid int
        td.manifest['mapping']['int_field'] = "invalid"
        with self.assertRaises(TypeError):
            td.import_data()
        # string to int
        td.manifest['mapping']['int_field'] = "string"
        with self.assertRaises(ValueError):
            td.import_data()

    def test_boolean_parser(self):
        data = {"bool": True,
                "false": False,
                "str_bool": "True",
                "str": "foo",
                "empty_str": "",
                "list": [1, 2, 3],
                "empty_list": [],
                "object": {"foo": 123},
                "empty_object": {}}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"bool_field": "bool"},
                    "parsers": {"bool_field": {"type": "boolean"}}}
        should_be_true = ["bool", "str_bool", "str", "list", "object"]
        should_be_false = ["false", "empty_str", "empty_list", "empty_object"]
        td = TransferData(data=[data], manifest=manifest)
        for field_name in should_be_true:
            td.manifest['mapping']['bool_field'] = field_name
            import_objects = td.import_data()
            self.assertEqual(type(import_objects[0].bool_field), bool)
            self.assertEqual(import_objects[0].bool_field, True)
        for field_name in should_be_false:
            td.manifest['mapping']['bool_field'] = field_name
            import_objects = td.import_data()
            self.assertEqual(type(import_objects[0].bool_field), bool)
            self.assertEqual(import_objects[0].bool_field, False)

    def test_relative_key_parser(self):
        data = {"name": "foo",
                "related": 1}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "related_obj": "related"},
                    "parsers": {"related_obj": {"type": "relative_key",
                                                "data_name": "related_data",
                                                "rk_lookup": "key"}}}
        self.import_related()
        td = TransferData(data=[data], manifest=manifest)
        imported_objects = td.import_data()
        rel_obj = MyRelatedModel.objects.get(key=1)
        self.assertEqual(imported_objects[0].related_obj, rel_obj)

    def test_relative_key_many(self):
        data = {"name": "foo",
                "related": [1, 2, 3]}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "many_related_objs": "related"},
                    "parsers": {"many_related_objs": {"type": "relative_key",
                                                      "data_name": "related_data",
                                                      "rk_lookup": "key",
                                                      "many": True}},
                    "m2m_fields": ["many_related_objs"]}
        self.import_related()
        td = TransferData(data=[data], manifest=manifest)
        imported_objects = td.import_data()
        rel_obj1 = MyRelatedModel.objects.get(key=1)
        rel_obj2 = MyRelatedModel.objects.get(key=2)
        rel_obj3 = MyRelatedModel.objects.get(key=3)
        self.assertIn(rel_obj1, imported_objects[0].many_related_objs.all())
        self.assertIn(rel_obj2, imported_objects[0].many_related_objs.all())
        self.assertIn(rel_obj3, imported_objects[0].many_related_objs.all())

    def test_relative_key_does_not_exist(self):
        data = {"name": "foo",
                "related": 100}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "related_obj": "related"},
                    "parsers": {"related_obj": {"type": "relative_key",
                                                "data_name": "related_data",
                                                "rk_lookup": "key"}}}
        self.import_related()
        td = TransferData(data=[data], manifest=manifest)
        with self.assertRaises(RelativeKeyDoesNotExist):
            td.import_data()

    def test_relative_key_rk_lookup_not_defined(self):
        data = {"name": "foo",
                "related": 100}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "related_obj": "related"},
                    "parsers": {"related_obj": {"type": "relative_key",
                                                "data_name": "related_data"}}}  # missing rk_lookup
        self.import_related()
        td = TransferData(data=[data], manifest=manifest)
        with self.assertRaises(InvalidManifest):
            td.import_data()

    def test_relative_object_parser(self):
        data = {"name": "foo",
                "related": {"name": "Foo",
                            "key": 321}}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "related_obj": "related"},
                    "parsers": {"related_obj": {"type": "relative_object",
                                                "data_name": "related_data"}}}
        self.import_related()
        td = TransferData(data=[data], manifest=manifest)
        objs = td.import_data()
        rel = MyRelatedModel.objects.get(key=321)
        self.assertEqual(objs[0].related_obj, rel)

    def test_relative_object_many(self):
        data = {"name": "foo",
                "related": [{"name": "Foo",
                             "key": 321},
                            {"name": "Bar",
                             "key": 322}]}
        manifest = {"model": "tests.MyModel",
                    "mapping": {"char_field": "name",
                                "many_related_objs": "related"},
                    "parsers": {"many_related_objs": {"type": "relative_object",
                                                      "data_name": "related_data",
                                                      "many": True}},
                    "m2m_fields": ["many_related_objs"]}
        self.import_related()
        td = TransferData(data=[data], manifest=manifest)
        objs = td.import_data()
        rel1 = MyRelatedModel.objects.get(key=321)
        rel2 = MyRelatedModel.objects.get(key=322)
        self.assertIn(rel1, objs[0].many_related_objs.all())
        self.assertIn(rel2, objs[0].many_related_objs.all())
