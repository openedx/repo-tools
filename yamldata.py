"""Convenient access to data stored in yaml files."""

import os

import yaml

from helpers import requests


class YamlData(object):
    """Data stored in yaml, conveniently"""

    # A dict mapping filenames to the data we read from the file.
    _the_data = {}

    # Where we read repo-tools-data from.
    _data_dir = "../repo-tools-data"

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, f):
        """Returns a YamlData object loaded from an open yaml file."""
        return cls(yaml.safe_load(f))

    @classmethod
    def from_string(cls, s):
        """Returns a YamlData object loaded from a yaml string."""
        return cls(yaml.safe_load(s))

    @classmethod
    def the_data(cls, filename):
        """
        Returns the data from a particular file name, either locally or remote.
        """
        if filename not in cls._the_data:
            # Define REPO_TOOLS_LATEST_PEOPLE=1 in the environment to force code to
            # get the data from GitHub instead of the local copy.
            if int(os.environ.get('REPO_TOOLS_LATEST_PEOPLE', '0')):
                # Read from GitHub.
                resp = requests.get("https://raw.githubusercontent.com/edx/repo-tools-data/master/" + filename)
                if not resp.ok:
                    resp.raise_for_status()
                cls._the_data[filename] = cls.from_string(resp.text)
            else:
                # Read from a file.
                with open(os.path.join(cls._data_dir, filename)) as f:
                    cls._the_data[filename] = cls.from_file(f)

        return cls._the_data[filename]
