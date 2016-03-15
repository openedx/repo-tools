#!/usr/bin/env python
"""List repos missing from repos.yaml."""

from __future__ import print_function

import yaml

from helpers import paginated_get

REPOS_URL = "https://api.github.com/orgs/{org}/repos"

# This is hacky; you need to have repo-tools-data cloned locally one dir up.
# To do this properly, you should use yamldata.py
with open("../repo-tools-data/repos.yaml") as repos_yaml:
    tracked_repos = yaml.load(repos_yaml)

ORGS = ["edX", "edx-solutions"]
repos = []
for org in ORGS:
    repos.extend(paginated_get(REPOS_URL.format(org=org)))

shown_any = False
for r in repos:
    if not r['private'] and not r['fork']:
        if r['full_name'] not in tracked_repos:
            if not shown_any:
                print("\n### Untracked repos:")
            print("{r[full_name]}: {r[description]}".format(r=r))
            shown_any = True

shown_any = False
actual_repos = set(r['full_name'] for r in repos)
for tracked in tracked_repos:
    if tracked not in actual_repos:
        if not shown_any:
            print("\n### Disappeared repos:")
        print(tracked)
        shown_any = True
