import collections
from copy import deepcopy
import re
import sys
import yaml

MAPPING_TAG = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG


def dict_representer(dumper, data):
    return dumper.represent_mapping(MAPPING_TAG, data.items())


def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))


def setup_ordered_yaml_parser():
    """
    Default yaml parser does not maintains the order of elements.
    This function overrides the default mapping to maintain
    the original order of elements in the travis file.
    """
    yaml.add_representer(collections.OrderedDict, dict_representer)
    yaml.add_constructor(MAPPING_TAG, dict_constructor)


class TravisModernizer:
    def __init__(self, file_path):
        setup_ordered_yaml_parser()
        self.file_path = file_path
        self.travis_dict = None
        self.DJANGO_PATTERN = re.compile("django[0-2][0-1]")  # creates regex to match django111, django20 && django21

    def remove_django_envs(self):
        with open(self.file_path, 'r') as file:
            self.travis_dict = yaml.load(file, Loader=yaml.FullLoader)
            if 'matrix' in self.travis_dict.keys():
                env_list = self.travis_dict['matrix']['include']
                updated_list = [
                    env for env in env_list if not self.DJANGO_PATTERN.search(env['env'])
                ]
                self.travis_dict['matrix']['include'] = updated_list
            if 'env' in self.travis_dict.keys():
                env_list = self.travis_dict['env']
                updated_list = [
                    env for env in env_list if not self.DJANGO_PATTERN.search(env)
                ]
                self.travis_dict['env'] = updated_list
            return self.travis_dict

    def update_python_version(self):
        """
        Add py38, remove py36 if present.
        """
        with open(self.file_path, 'r') as file:
            self.travis_dict = yaml.load(file, Loader=yaml.FullLoader)
            if 'python' in self.travis_dict.keys():
                self.travis_dict['python'].append('3.8')
                if '3.6' in self.travis_dict['python']:
                    self.travis_dict['python'].remove('3.6')
            if 'matrix' in self.travis_dict.keys():
                env_list = self.travis_dict['matrix']['include']
                # remove python 3.6 if present
                allowed_envs = []
                for env in env_list:
                    if 'python' in env.keys():
                        if env['python'] != 3.6:
                            allowed_envs.append(deepcopy(env))
                # add python 3.8 in env_list
                new_python_envs = []
                for env in allowed_envs:
                    if 'python' in env.keys():
                        #  copy whole element and add it in env_list with python3.8 version.
                        env_copy = deepcopy(env)
                        env_copy['python'] = '3.8'
                        new_python_envs.append(deepcopy(env_copy))
                self.travis_dict['matrix']['include'] = allowed_envs + new_python_envs
            return self.travis_dict

    def write_updated_data(self):
        with open(self.file_path, 'w') as file:
            yaml.dump(self.travis_dict, file, default_flow_style=False, sort_keys=True)

    def modernize(self):
        self.update_python_version()
        self.write_updated_data()
        self.remove_django_envs()
        self.write_updated_data()


if __name__ == '__main__':
    modernizer = TravisModernizer(file_path=sys.argv[1])
    modernizer.modernize()
