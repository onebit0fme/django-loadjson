import os
import json


class LoaderNotConfigured(Exception):
    pass


class DefaultDataFinder(object):

    def __init__(self, data_dirs):
        self.data_dirs = data_dirs

    def find(self, data_name):
        file_name = data_name
        if '.json' not in file_name:
            file_name += '.json'
        return self.find_locations(file_name)

    def find_manifest(self, data_name):
        if '.json' in data_name:
            d_file, d_ext = os.path.splitext(data_name)
            manifest_path = "{path}.manifest{ext}".format(path=d_file, ext=d_ext)
        else:
            manifest_path = data_name + '.manifest.json'
        return self.find_locations(manifest_path)

    def find_locations(self, file_name):
        for d_dir in self.data_dirs:
            file_path = os.path.join(d_dir, file_name)
            if os.path.isfile(file_path):
                with open(file_path) as data:
                    return json.load(data)
