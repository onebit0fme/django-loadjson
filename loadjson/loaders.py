import sys
import importlib
import dateutil.parser
import six
from collections import defaultdict
from django.conf import settings
from django.db.utils import IntegrityError
from .compat import get_model
from .finders import DefaultDataFinder


class LoadNotConfigured(Exception):
    pass


class TransferValidationError(Exception):
    pass


def get_settings():
    loadjson_settings = getattr(settings, 'LOAD_JSON', None)
    if loadjson_settings is None or not isinstance(loadjson_settings, dict):
        raise LoadNotConfigured("\"LOAD_JSON\" is not defined in project settings")
    return loadjson_settings


def find_data(data_name):
    loadjson_settings = get_settings()
    data_dirs = loadjson_settings.get('DATA_DIRS', [])
    finder_classes = loadjson_settings.get('FINDER_CLASSES')
    finders = [DefaultDataFinder(data_dirs)]
    if isinstance(finder_classes, list):
        for class_string in finder_classes:
            try:
                finder_class = import_from_string(class_string)
                finders.append(finder_class())
            except ImportError:
                raise ImportError("Unable to import {}".format(class_string))
    data = None
    data_manifest = None
    for finder in finders:
        if data is None:
            data = finder.find(data_name)
        if data_manifest is None:
            data_manifest = finder.find_manifest(data_name)

    return data, data_manifest


def import_from_string(class_path):
    parts = class_path.split('.')
    module_path, class_name = '.'.join(parts[:-1]), parts[-1]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_adaptor_classes():
    loadjson_settings = get_settings()
    adaptor_classes_settings = loadjson_settings.get('ADAPTOR_CLASSES', [])
    adaptor_classes = []
    for class_string in adaptor_classes_settings:
        try:
            adaptor_classes.append(import_from_string(class_string))
        except ImportError:
            raise ImportError("Unable to import {}".format(class_string))
    return adaptor_classes


def get_model_handler_class():
    loadjson_settings = get_settings()
    model_handler_setting = loadjson_settings.get('MODEL_HANDLER')
    if model_handler_setting is None:
        model_handler_setting = 'loadjson.adaptors.ModelHandler'
    return import_from_string(model_handler_setting)()


class BaseLoader(object):
    manifest_defaults = {
        'lookup_allow_null': False,
        'rk_lookup': 'pk',
        'update': True
    }

    def __init__(self, *args, **kwargs):
        # Load settings
        load_settings = get_settings()
        defaults = load_settings.get('MANIFEST_DEFAULTS', {})
        if defaults and isinstance(defaults, dict):
            self.manifest_defaults.update(defaults)

        # Load data
        data_name = kwargs.get('data_name')
        self.data = kwargs.get('data')
        self.manifest = kwargs.get('manifest')
        if self.data is None or self.manifest is None:
            data, manifest = find_data(data_name)
            if self.data is None:
                self.data = data
            if self.manifest is None:
                self.manifest = manifest
        if self.data is None:
            raise LoadNotConfigured("Can't find data for {}".format(data_name or ''))
        if self.manifest is None:
            raise LoadNotConfigured("Can't find manifest for {}".format(data_name or ''))

    def get_manifest_value(self, field, default=None):
        return self.manifest.get(field, default if default is not None else self.manifest_defaults.get(field))

    def _field_is_nullable(self, field):
        nullable = self.manifest.get('nullable', [])
        return field in nullable

    def _validate(self):
        assert isinstance(self.data, list), "Data must be a list, got {} instead.".format(type(self.data))

    def valid(self, silent=True):
        try:
            self._validate()
        except AssertionError as e:
            if not silent:
                raise e
            return False
        return True


class TransferData(BaseLoader):
    adaptors = None

    def _apply_adaptors(self, data):
        if self.adaptors is None:
            return data
        for adaptor in self.adaptors:
            if adaptor.models is None or self.app_model in adaptor.models:
                data = adaptor.adapt(data)
        return data

    def _post_save(self, obj, data, m2m_data):
        if self.adaptors is not None:
            for adaptor in self.adaptors:
                adaptor.adapt_post_save(obj, data, m2m_data)
        return obj

    def __init__(self, *args, **kwargs):
        super(TransferData, self).__init__(*args, **kwargs)

        # Initialize manifest
        self.app_model = self.get_manifest_value('model')
        self.model = self._get_model(self.get_manifest_value('model'))
        self.model_handler = get_model_handler_class()
        adaptor_classes = get_adaptor_classes()
        if isinstance(adaptor_classes, list):
            self.adaptors = [adaptor(self.model, self.app_model, self.manifest) for adaptor in adaptor_classes]
        if self.model is None:
            raise ValueError("manifest does not define 'model'")
        self.__dependencies = {}
        self.__indices = {}

        # Import status
        self.report = type('Report', (object,),
                           dict(created=0, updated=0, exceptions=defaultdict(list),
                                count=len(self.data), item=0))()

    def write_std_out(self):
        message = "\r{item}/{count} (Created: {created}, Updated: {updated})".format(
            count=self.report.count,
            item=self.report.item,
            created=self.report.created,
            updated=self.report.updated
        )
        sys.stdout.write(message)
        sys.stdout.flush()

    def get_dependency(self, file_name):
        if self.__dependencies.get(file_name) is not None:
            return self.__dependencies[file_name]
        td = TransferData(data_name=file_name)
        # cache dependency for later use
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
        model = get_model(app_label, app_model)
        return model

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
            return not bool(value) if invert else bool(value)
        elif field_type == 'datetime':
            dt = dateutil.parser.parse(value)
            return dt
        elif field_type == 'relative_key':
            dependency = self.get_dependency(field_parser.get('data_name'))
            fk_obj = dependency.get_rk_obj(rk=field_parser.get('rk_lookup', self.get_manifest_value('pk')),
                                           value=value,
                                           many=field_parser.get('many', False),
                                           lookup=field_parser.get('lookup'))
            return fk_obj
        elif field_type == 'relative_object':
            data_name = field_parser.get('data_name')
            manifest = field_parser.get('manifest')
            return self._handle_relative_objects(value, data_name=data_name,
                                                 manifest=manifest, many=field_parser.get('many', False))

        raise ValueError("'{}' field type is not supported".format(field_type))

    def _handle_relative_objects(self, data, data_name=None, manifest=None, many=False):
        dt = TransferData(data=data, manifest=manifest, data_name=data_name)
        if many:
            return dt.import_data(write_to_std_out=False)
        else:
            return dt.import_item(data, dt.get_manifest_value('update', True),
                                  dt.get_manifest_value('skip_integrity_errors', False))[0]

    def _to_internal(self, item):
        internal = self.get_manifest_value('mapping')
        assert internal is not None, "manifest must define 'mapping'"
        final_internal = {}
        for field in internal.keys():
            if not isinstance(field, six.string_types):
                raise TransferValidationError("\"mapping\" improperly configured")
            mapping_path = internal[field].split('.')
            raw_value = item
            for p in mapping_path:
                raw_value = raw_value.get(p, {})
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
        if isinstance(lookup_fields, six.string_types):
            lookup_fields = [lookup_fields]
        lf = {}
        for field in lookup_fields:
            lv = data.get(field)
            if not self.get_manifest_value('lookup_allow_null'):
                assert lv is not None, "'lookup' fields can't be null"
            lf[field] = lv
        return lf

    def _m2m(self, data):
        # m2m_fields = M2M.get(self.get_manifest_value('model'), [])
        m2m_fields = self.get_manifest_value('m2m_fields', default=[])
        m2m_data = {}
        for f in m2m_fields:
            m2m_data[f] = data.pop(f, None)
        return data, m2m_data

    def _m2m_fill(self, obj, fields, m2m_clear=True):
        # TODO: make m2m_clear configurable in manifest
        for field, m2m_array in iter(fields.items()):
            if m2m_array is None:
                continue
            m2m_field = getattr(obj, field)
            if type(m2m_field).__name__ == 'RelatedManager':
                # Some m2m fields are custom and should be handled at post_save adaptor
                continue
            if m2m_clear:
                m2m_field.clear()
            m2m_field.add(*m2m_array)
        return obj

    def _update_or_create(self, lookup_kwargs, data, m2m_clear=True):
        # TODO: make m2m_clear configurable in manifest
        data = self._apply_adaptors(data)
        data, m2m_data = self._m2m(data)
        obj, _ = self.model_handler.update_or_create(self.model, data, lookup_kwargs)
        obj = self._m2m_fill(obj, m2m_data, m2m_clear=m2m_clear)
        obj = self._post_save(obj, data, m2m_data)
        return obj, _

    def _create(self, model, data, m2m_clear=False):
        data = self._apply_adaptors(data)
        data, m2m_data = self._m2m(data)
        obj = self.model_handler.create(model, data)
        obj = self._m2m_fill(obj, m2m_data)
        obj = self._post_save(obj, data, m2m_data)
        return obj

    def _get(self, lookup_kwargs):
        return self.model_handler.get(self.model, lookup_kwargs)

    def _get_or_create(self, lookup_kwargs, data, m2m_clear=True):
        data = self._apply_adaptors(data)
        data, m2m_data = self._m2m(data)
        obj, _ = self.model_handler.get_or_create(self.model, data, lookup_kwargs)
        if _:
            obj = self._m2m_fill(obj, m2m_data, m2m_clear=m2m_clear)
            obj = self._post_save(obj, data, m2m_data)
        return obj, _

    def _get_or_none(self, lookup_kwargs):
        try:
            return self._get(lookup_kwargs)
        except self.model.DoesNotExist:
            return None

    def import_item(self, item, update=False, skip_integrity_errors=False):
        to_internal = self._to_internal(item)

        lookup_kwargs = self._lookup_by(to_internal)
        try:
            if lookup_kwargs is not None:
                if update:
                    obj, _created = self._update_or_create(lookup_kwargs, to_internal)
                else:
                    obj, _created = self._get_or_create(lookup_kwargs, to_internal)
                return obj, _created
            else:
                obj = self._create(self.model, to_internal)
                return obj, True
        except IntegrityError as e:
            if skip_integrity_errors:
                self.report.exceptions['IntegrityError'].append(e)
            else:
                raise e
            return None, None

    def import_data(self, write_to_std_out=False):
        self.valid(silent=False)
        skip_integrity_errors = self.get_manifest_value('skip_integrity_errors', False)
        objs = []
        for item in self.data:
            self.report.item += 1
            obj, _created = self.import_item(item,
                                             update=self.get_manifest_value('update', default=True),
                                             skip_integrity_errors=skip_integrity_errors)
            objs.append(obj)
            if _created:
                self.report.created += 1
            elif self.get_manifest_value('update'):
                self.report.updated += 1

            if write_to_std_out:
                self.write_std_out()
        return objs
