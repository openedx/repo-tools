#!/usr/bin/env python
"""List the webhooks in all the repos."""

from __future__ import print_function

import pprint

from helpers import paginated_get
from repos import Repo

repos = Repo.from_yaml()
repo_names = sorted(repo.name for repo in repos)
for repo_name in repo_names:
    print("\n-- {} ---------------------".format(repo_name))
    url = "https://api.github.com/repos/{name}/hooks".format(name=repo_name)
    for r in paginated_get(url):
        print("{r[name]}".format(r=r))
        for k, v in sorted(r['config'].items()):
            print("  {k}: {v}".format(k=k, v=v))
