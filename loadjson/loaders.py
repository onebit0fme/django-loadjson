import os
import sys
import json
from collections import defaultdict
from datetime import datetime
from django.apps import apps
from django.db.utils import IntegrityError


class TransferValidationError(Exception):
    pass


class TransferData(object):
    defaults = {
        'lookup_allow_null': False,
        'rk_lookup': 'pk',
        'update': True
    }
    object_defaults = []

    def _fill_defaults(self, data):
        if self.object_defaults is None:
            return data
        data = self.object_defaults(data, transfer_instance=self)
        return data

    def __init__(self, data_path):
        if not os.path.isfile(data_path):
            raise ValueError("{} file does not exist".format(data_path))
        d_file, d_ext = os.path.splitext(data_path)
        manifest_path = "{path}.manifest{ext}".format(path=d_file, ext=d_ext)
        if not os.path.isfile(manifest_path):
            raise ValueError("{} file does not exist".format(manifest_path))
        self.data_path = data_path
        with open(data_path) as data:
            self.data = json.load(data)
        with open(manifest_path) as manifest:
            self.manifest = json.load(manifest)

        self.model = self._get_model(self.get_manifest_value('model'))
        self.object_defaults = DEFAULTS.get(self.get_manifest_value('model'))
        if self.model is None:
            raise ValueError("manifest does not define 'model'")
        self.__dependencies = {}
        self.__indices = {}

    def get_manifest_value(self, field, default=None):
        return self.manifest.get(field, default or self.defaults.get(field))

    def get_dependency(self, file_name):
        if self.__dependencies.get(file_name) is not None:
            return self.__dependencies[file_name]
        current = os.path.split(self.data_path)[0]
        dep_path = os.path.join(current, file_name)
        if not os.path.isfile(dep_path):
            raise ValueError("{} file is specified as dependency, but file {} does not exist".format(file_name,
                                                                                                     dep_path))
        td = TransferData(dep_path)
        # cache dependency
        self.__dependencies[file_name] = td
        return td

    def get_rk(self, rk, value, many=False, raw_data=False):
        """
        Get internal object based on relative lookup.
        1.Scan the file for required `rk` value. 2. Convert to internal value.
        """
        # cache rk lookup
        if self.__indices.get(rk) is None:
            indexed_by_rk = defaultdict(list)
            for item in self.data:
                rk_val = item
                for p in rk.split('.'):
                    rk_val = rk_val[p]
                indexed_by_rk[rk_val].append(item)
            self.__indices[rk] = indexed_by_rk
        indexed_by_rk = self.__indices[rk]
        if many:
            values = []
            for val in value:
                values.extend(indexed_by_rk.get(val))
        else:
            values = indexed_by_rk.get(value)

        if values is None:
            return None

        if not raw_data:
            values = [self._to_internal(v) for v in values]

        if len(values) == 1:
            return values if many else values[0]
        elif len(values) > 1:
            if many:
                return values
            raise ValueError("Multiple {} relative keys found: {}".format(rk,
                                                                          ",".join(values)))

    def get_rk_obj(self, *args, **kwargs):
        kwargs['raw_data'] = False
        lookup_overwrite = kwargs.pop('lookup', None)
        rk_values = self.get_rk(*args, **kwargs)
        if rk_values is None:
            return None
        many = isinstance(rk_values, list)
        if many:
            objects = []
            for item in rk_values:
                lookup_kwargs = self._lookup_by(item, lookup_overwrite)
                objects.append(self._get(lookup_kwargs))
            return objects
        lookup_kwargs = self._lookup_by(rk_values, lookup_overwrite)
        return self._get(lookup_kwargs)

    def _get_model(self, label):
        assert label is not None, "manifest must define 'model'"
        app_label, app_model = label.split('.')
        model = apps.get_model(app_label, app_model)
        return model

    def _field_is_nullable(self, field):
        nullable = self.manifest.get('nullable', [])
        return field in nullable

    def _to_internal_type(self, field, value):
        parsers = self.manifest.get('parsers', {})
        field_parser = parsers.get(field)
        if field_parser is None:
            return value
        field_type = field_parser.get('type')
        if field_type == 'string':
            return str(value)
        elif field_type == 'integer':
            return int(value)
        elif field_type == 'boolean':
            invert = field_parser.get('invert', False)
            return not value if invert else value
        elif field_type == 'datetime':
            field_format = field_parser.get('format', '%Y-%m-%dT%H:%M:%S.%f%z')
            dt = datetime.strptime(value, field_format)
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = pytz.utc.localize(dt)
            return dt
        elif field_type == 'relative_key':
            dependency = self.get_dependency(field_parser.get('file'))
            fk_obj = dependency.get_rk_obj(rk=field_parser.get('rk_lookup', self.get_manifest_value('pk')),
                                           value=value,
                                           many=field_parser.get('many', False),
                                           lookup=field_parser.get('lookup'))
            return fk_obj
        raise ValueError("'{}' field type is not supported".format(field_type))

    def _to_internal(self, item):
        internal = self.manifest.get('mapping')
        assert internal is not None, "manifest must define 'mapping'"
        final_internal = {}
        for field in internal.keys():
            mapping_path = internal[field].split('.')
            raw_value = item
            for p in mapping_path:
                if isinstance(raw_value, list):
                    print mapping_path
                    print raw_value
                raw_value = raw_value.get(p)
            if not self._field_is_nullable(field):
                assert raw_value is not None, "Invalid mapping '{}'".format(internal[field])
            internal_value = self._to_internal_type(field, raw_value)
            final_internal[field] = internal_value
        return final_internal

    def _lookup_by(self, data, lookup_overwrite=None):
        lookup_fields = self.get_manifest_value('lookup')
        if lookup_overwrite is not None:
            lookup_fields = lookup_overwrite

        if lookup_fields is None:
            return None
        if isinstance(lookup_fields, (str, unicode)):
            lookup_fields = [lookup_fields]
        lf = {}
        for field in lookup_fields:
            lv = data.get(field)
            if not self.get_manifest_value('lookup_allow_null'):
                assert lv is not None, "'lookup' fields can't be null"
            lf[field] = lv
        return lf

    def _m2m(self, data):
        m2m_fields = M2M.get(self.get_manifest_value('model'), [])
        m2m_data = {}
        for f in m2m_fields:
            m2m_data[f] = data.pop(f, None)
        return data, m2m_data

    def _m2m_fill(self, obj, fields, m2m_clear=True):
        # TODO: make m2m_clear configurable in manifest
        for field, m2m_array in fields.iteritems():
            if m2m_array is None:
                continue
            m2m_field = getattr(obj, field)
            if type(m2m_field).__name__ == 'RelatedManager':
                # Some m2m fields are custom and should be handled at post_save
                continue
            if m2m_clear:
                m2m_field.clear()
            m2m_field.add(*m2m_array)
        return obj

    def _post_save(self, obj, data, m2m_data):
        self.object_defaults.post_save(obj, data, m2m_data)
        return obj

    def _update_or_create(self, model, lookup_kwargs, data, m2m_clear=True):
        # TODO: make m2m_clear configurable in manifest
        data = self._fill_defaults(data)
        data, m2m_data = self._m2m(data)
        obj, _ = model.objects.update_or_create(defaults=data, **lookup_kwargs)
        obj = self._m2m_fill(obj, m2m_data)
        obj = self._post_save(obj, data, m2m_data)
        return obj, _

    def _create(self, model, data, m2m_clear=False):
        data = self._fill_defaults(data)
        data, m2m_data = self._m2m(data)
        obj = model.objects.create(**data)
        obj = self._m2m_fill(obj, m2m_data)
        obj = self._post_save(obj, data, m2m_data)
        return obj

    def _get(self, lookup_kwargs):
        return self.model.objects.get(**lookup_kwargs)

    def _get_or_create(self, model, lookup_kwargs, data):
        data = self._fill_defaults(data)
        return model.objects.get_or_create(defaults=data, **lookup_kwargs)

    def _get_or_none(self, *args, **kwargs):
        try:
            return self._get(*args, **kwargs)
        except self.model.DoesNotExist:
            return None

    def _validate(self):
        pass

    def write(self, message):
        sys.stdout.write(message)
        sys.stdout.flush()

    def valid(self, silent=True):
        try:
            self._validate()
        except AssertionError as e:
            if not silent:
                raise e
            return False
        return True

    def import_data(self):
        if not isinstance(self.data, list):
            raise ValueError("Data must be a list, got {} instead.".format(type(self.data)))
        self.valid(silent=False)
        data_model = self._get_model(self.get_manifest_value('model'))
        created = 0
        updated = 0
        exceptions = defaultdict(list)
        for item in self.data:
            to_internal = self._to_internal(item)

            lookup_kwargs = self._lookup_by(to_internal)
            try:
                if lookup_kwargs is not None:
                    if self.get_manifest_value('update'):
                        obj, _created = self._update_or_create(data_model, lookup_kwargs, to_internal)
                    else:
                        obj, _created = self._get_or_create(data_model, lookup_kwargs, to_internal)
                    if _created:
                        created += 1
                    elif self.get_manifest_value('update'):
                        updated += 1
                else:
                    obj = self._create(data_model, to_internal)
                    created += 1
            except IntegrityError as e:
                exceptions['IntegrityError'].append(e)

        # REPORT
        if exceptions:
            print("EXCEPTIONS")
        for exc_type, exc_list in exceptions.iteritems():
            print(exc_type + "<" * 30)
            if len(exc_list) > 10 and False:
                print("    - {} ERRORS".format(len(exc_list)))
            else:
                for message in exc_list:
                    print("    - {}".format(message))
            print "^" * 40

        print("CREATED - {}".format(created))
        print("UPDATED - {}".format(updated))
