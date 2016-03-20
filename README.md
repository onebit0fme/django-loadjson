# django-loadjson
[ ![Codeship Status for onebit0fme/django-loadjson](https://codeship.com/projects/6e3309b0-d07e-0133-fd7c-1e2b23aa142a/status?branch=master)](https://codeship.com/projects/141380)

Django management command to load json data of any shape by defining "manifest" that describes mapping instructions.

## Requirements

Python 2.7, 3.4, 3.5
Django >= 1.7

## Installation

`pip install django-loadjson`

## Quick setup

Include loadjson in settings.py

```
INSTALLED_APPS = [
    ... ,
    'loadjson',
    ...
]
```

Define loadjson data directories - a place loadjson will look for data (.json) files.

```
LOAD_JSON = {
    'DATA_DIRS': [os.path.join(BASE_DIR, 'dumpdata')],
}
```

Dump all your .json files inside the specified directory(ies).

Each `*.json` file must also have corresponding `*.manifest.json` that describes how the data should be handled.
For "manifest" reference, see `Manifest` section.

Once the data and manifest is in place, run

`python manage.py loadjson <data_name>`, where \<data_name> corresponds to the filename of the data (with or without the
.json part).
 
Note, loadjson will look in all specified directories for the requested \<data_name> and will use the first file
it will find. Same goes for the manifest file. Data file and manifest do not have to live in the same directory,
but both must be in a path of defined "DATA_DIRS".

It is also possible to handle data and manifest in other ways by providing custom "finder_classes".
 See `Advanced Usage` for instructions.

## Manifest

+ model (required) - a string in format "<app_label>.<model_name>"
+ mapping (required) - an object representing the model - data mapping.
+ parsers (optional) - an object the describes how to parse the data. Supported types:
    + `string` - convert to string
    + `integer` - convert to integer
    + `boolean` - convert to boolean. Optional, define `"invert": true` to invert.
    + `datetime` - parse datetime string
    + `relative_key` - lookup the relative key by the field value in another dataset. Required:
        + `data_name` - is a data name where related object should be looked up.
        + `rk_lookup` - the field for the lookup in the related dataset using one key. Ex., "email".
        + `lookup` - overwrite the related data lookup field(s). By default will use the lookup fields that are defined
        in data manifest.
        + `many` (optional) - for many-to-many relationship.
    + `relative_object` - get/create/update a related object. `data_name` or `manifest` required
        + `data_name` - for regular manifest lookup
        + `manifest` - define manifest right on the spot
        + `many` - one related object or many-to-many relationship.
+ lookup (required for updates are relative lookups) - a string or a list of fields to use when looking up an object.
Ex., `id`, `email`, `["username", "email"]`. Note, lookup fields are used to lookup an object. The result of a lookup
must be one object, so choose accordingly.
+ nullable (optional) - a list of fields that are nullable.
+ m2m_fields (optional) - a list of many-to-many fields. Note, if data contains many-to-many field, this field should
include it, or alternatively use custom adaptors to handle it, otherwise Django will throw an error when saving.

### Example:

users.json
```
[
    {
        "username": "PinkRabbit",
        "email": "pink.rabbit@example.com"
        "member_since": "",
        "active": true,
        "not_superuser": true,
        "preferences": {
            "email_notifications: true,
            "number_of_friends": "2"
        },
        "friends": ["blue.hippo@example.com", "funny.tiger@example.com"],
        "badges": [
            {
                "name": "For being pink",
                "date_awarded": ""
            },
            {
                "name": "For being there for friends",
                "date_awarded": ""
            }
         ]
    },
    ...
]
```

users.manifest.json
```
{
    "model": "account.User",
    "lookup": "pk",
    "mapping": {
        "username": "username",
        "email": "email",
        "date_joined": "member_since",
        "active": "active",
        "is_superuser": "not_superuser",
        "email_notifications": "preferences.email_notifications",
        "friends_number": "preferences.number_of_friends",
        "friends": "friends",
        "badges": "badges"
    },
    "parsers": {
        "is_superuser: {
            "type": "boolean",
            "invert": true
        },
        "date_joined": {
            "type": "datetime"
        },
        "friends": {
            "type": "relative_key",
            "data_name": "users",
            "rk_lookup": "email",
            "lookup": "username",
            "many": true
        },
        "badges": {
            "type": "relative_object",
            "many": true,
            "manifest" {
                "model": "account.Badge"
                "mapping": {
                    "name": "name",
                    "awarded": "date_awarded"
                },
                "parsers": {
                    "awarded": {
                        "type": "datetime"
                    }
                },
                "lookup": "name"
            }
        }
    }
}
```

## LOAD_JSON settings

All loadjson-related settings should go into `LOAD_JSON` var inside project's settings.py.

Possible LOAD_JSON settings:

+ `DATA_DIRS` (required) - a list of absolute paths to use by the default finder to find data and manifest.
+ `ADAPTOR_CLASSES` (optional) - a list of classes that are used to customize the import. Extend `loadjson.adaptors.BaseAdaptor`
to define your custom adaptors. Defaults to None.
+ `MODEL_HANDLER` (optional) - a string that references a class that handles model lookups. Defaults to 
`loadjson.adaptors.ModelHandler`
+ `FINDER_CLASSES` (optional) - a list of classes that are used to find data. By default loadjson uses 
`loadjson.finders.DefaultDataFinder` that uses defined `DATA_DIRS` to find data and manifest.
+ `MANIFEST_DEFAULTS` (optional) - a dictionary of default manifest values to use.

### Defining ADAPTOR_CLASSES

`ADAPTOR_CLASSES` are used to further massage the data before saving. To define Adaptor Class, extend
`loadjson.adaptors.BaseAdaptor` and overwrite `adapt` and/or `adapt_post_save` methods like so:

```
from loadjson.adaptors import BaseAdaptor


class MyCusomAdaptor(BaseAdaptor):
    """
    Available attributes:
    - model - model class
    - app_model - a string in format <app_label>.<model_name>
    - manifest - a dictionary with defined manifest values
    """

    def adapt(self, data):
        """
        Method provides a base hook to provide additional data, set defaults,
        or modify the data before saving.

        Usage: what returned gets saved
        """
        return data

    def adapt_post_save(self, obj, data, m2m_data):
        """
        In some cases (like saving many-to-many relations) data might require
        some additional tweaks. That is done here.
        Note: Many-to-Many objects are attached by default, however in case if many-to-many relationship
        is done through a custom model, this method provides a hook to process such customization.
        """
        pass
```

Don't forget to include your custom adaptors in LOAD_JSON.ADAPTOR_CLASSES.

## Advanced usage

### MODEL_HANDLER

Define custom ModelHandle if you want to use custom model manager, or your same method has any customization.
`get`, `create`, `get_or_create`, `update_or_create` methods are available for overwrite.

### FINDER_CLASSES

It is also possible to overwrite or extend the default finder classes. The purpose of the finder class is to lookup
the data by data_name. `DefaultDataFinder` is a default finder, but can be extended by defining `FINDER_CLASSES` in
LOAD_JSON settings. Note, if you define this setting and not include `DefaultDataFinder`, then it will not be used,
unless you add it explicitly as well. 

It is possible to define as many finders as you will, but be aware that only the first occurrence found will be used.