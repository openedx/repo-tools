#!/usr/bin/env python
"""Copy tags from one repo to others."""

from __future__ import print_function

import json

import requests
import yaml

from helpers import paginated_get


LABELS_URL = "https://api.github.com/repos/{owner_repo}/labels"

def get_labels(owner_repo):
    url = LABELS_URL.format(owner_repo=owner_repo)
    labels = paginated_get(url)
    labels = list(labels)
    for label in labels:
        del label['url']
    return labels

def set_labels(owner_repo, labels):
    for label in labels:
        url = LABELS_URL.format(owner_repo=owner_repo)
        r = requests.post(url, data=json.dumps(label))
        if r.status_code != 200:
            print(r.status_code)
            print(r.text)

def copy_labels(source_owner_repo):

    labels = get_labels(source_owner_repo)

    with open("repos.yaml") as repos_file:
        REPO_INFO = yaml.load(repos_file)

    for owner_repo in sorted(REPO_INFO):
        if owner_repo == source_owner_repo:
            continue

        print("Copying labels into {}".format(owner_repo))
        set_labels(owner_repo, labels)

if __name__ == "__main__":
    copy_labels("edx/edx-platform")
