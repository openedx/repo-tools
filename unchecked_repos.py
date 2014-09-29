#!/usr/bin/env python
"""List repos missing from repos.yaml."""

from __future__ import print_function

import json

import yaml

from helpers import paginated_get

REPOS_URL = "https://api.github.com/orgs/{org}/repos"

with open("repos.yaml") as repos_yaml:
    tracked_repos = yaml.load(repos_yaml)

for r in paginated_get(REPOS_URL.format(org="edX")):
    if not r['private'] and not r['fork']:
        if r['full_name'] not in tracked_repos:
            print("{r[full_name]}: {r[description]}".format(r=r))
