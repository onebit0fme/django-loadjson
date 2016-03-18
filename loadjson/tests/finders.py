
TEST_DATA = {}

TEST_MANIFEST = {}

class TestDataFinder(object):
    """
    Data finder for tests.
    """

    def find(self, data_name):
        return TEST_DATA.get(data_name)

    def find_manifest(self, data_name):
        return TEST_MANIFEST.get(data_name)
