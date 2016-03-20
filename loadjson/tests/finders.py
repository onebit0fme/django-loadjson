from __future__ import unicode_literals

TEST_DATA = {
    "dataset_no_manifest": [
        {
            "char_field": "Sample string",
            "text_field": "Sample text"
        }
    ]
}

TEST_MANIFEST = {
    "dataset_one": {
        "model": "tests.MyModel",
        "mapping": {}
    },
    "related_data": {
        "model": "tests.MyRelatedModel",
        "mapping": {
            "name": "name",
            "key": "key"
        },
        "lookup": "key"
    }
}

# Fill related model data for tests
TEST_DATA['related_data'] = []
for n in range(5):
    item = {
        "name": "Name {}".format(n),
        "key": n
    }
    TEST_DATA['related_data'].append(item)


class TestDataFinder(object):
    """
    Data finder for tests.
    """

    def find(self, data_name):
        return TEST_DATA.get(data_name)

    def find_manifest(self, data_name):
        return TEST_MANIFEST.get(data_name)
