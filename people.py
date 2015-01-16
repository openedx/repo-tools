"""Access to the people.yaml database."""

import os

import yaml

from helpers import requests


class People(object):
    """
    A database of people.
    """
    the_people = None

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, f):
        """Returns a People object loaded from a yaml file."""
        return cls(yaml.safe_load(f))

    @classmethod
    def from_string(cls, s):
        """Returns a People object loaded from a yaml string."""
        return cls(yaml.safe_load(s))

    @classmethod
    def people(cls):
        """
        Returns the main people database.
        """
        if cls.the_people is None:
            # Define REPO_TOOLS_LATEST_PEOPLE=1 in the environment to force code to
            # get people.yaml from GitHub instead of the local copy.
            if int(os.environ.get('REPO_TOOLS_LATEST_PEOPLE', '0')):
                # Read people.yaml from GitHub.
                people_resp = requests.get("https://raw.githubusercontent.com/edx/repo-tools/master/people.yaml")
                if not people_resp.ok:
                    people_resp.raise_for_status()
                cls.the_people = cls.from_string(people_resp.text)
            else:
                with open("people.yaml") as fpeople:
                    cls.the_people = cls.from_file(fpeople)
        return cls.the_people

    def get(self, who, when=None):
        """
        Get the details for a person, optionally at a point in the past.
        """
        user_info = self.data.get(who)
        if user_info is None:
            user_info = {"institution": "unsigned", "agreement": "none"}

        if when is not None and "before" in user_info:
            # There's history, let's get the institution as of the pull
            # request's created date.
            when = when.date()  # Get just the date from a datetime.
            history = sorted(user_info["before"].items(), reverse=True)
            for then, info in history:
                if then < when:
                    break
                user_info.update(info)
        return user_info
