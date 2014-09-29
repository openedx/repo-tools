#!/usr/bin/env python
"""Sync labels across all repos using labels.yaml."""

from __future__ import print_function

import json

import requests
import yaml

from helpers import paginated_get


LABELS_URL = "https://api.github.com/repos/{owner_repo}/labels"

def get_labels(owner_repo):
    url = LABELS_URL.format(owner_repo=owner_repo)
    labels = paginated_get(url)
    for label in labels:
        del label['url']
        yield label


def set_or_delete_labels(owner_repo, new_labels):
    # Set new labels
    for label in new_labels:
        url = LABELS_URL.format(owner_repo=owner_repo)
        r = requests.post(url, data=json.dumps(label))
        if r.status_code == 201:
            print("Copied {}".format(label['name']))
            continue
        if r.status_code == 422 and r.json()['errors'][0]['code'] == 'already_exists':
            continue

        print(r.status_code)
        print(r.text)

    # Delete stale labels
    label_names = set(l['name'] for l in new_labels)
    for stale_label in (set(l['name'] for l in get_labels(owner_repo)) - label_names):
        r = requests.delete(url + "/" + stale_label.replace(' ', '%20'))
        if r.status_code == 204:
            print("Removed label {}".format(stale_label))
        elif r.status_code == 404:
            print("Failed to remove label {}".format(stale_label))
        else:
            print(r.status_code, r.text)


def sync_labels():
    with open("labels.yaml") as label_names:
        labels = yaml.load(label_names)
        LABEL_NAMES = []
        for name, info in labels.iteritems():
            # Need a dictionary that is {'name': 'label_name', 'color': 'colorhex'}
            ldict = {'name': name}
            ldict.update(info)
            LABEL_NAMES.append(ldict)

    with open("repos.yaml") as repos_file:
        REPO_INFO = yaml.load(repos_file)

    for repo in sorted(REPO_INFO):
        print("Copying labels into {}".format(repo))
        set_or_delete_labels(repo, LABEL_NAMES)


if __name__ == "__main__":
    sync_labels()
