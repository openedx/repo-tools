#!/usr/bin/env python
"""Sync labels across all repos using labels.yaml."""

from __future__ import print_function

import json

import requests
import yaml

import click
from helpers import paginated_get
from edx_repo_tools.auth import pass_github
from edx_repo_tools.data import pass_repo_tools_data, iter_openedx_yaml
from edx_repo_tools.utils import dry_echo, dry


def set_or_delete_labels(dry, repo, new_labels):

    new_labels = {label: data['color'] for label, data in new_labels.items()}
    existing_labels = {label.name: label for label in repo.iter_labels()}
    existing_names = set(existing_labels.keys())
    desired_names = set(new_labels.keys())

    for label in desired_names - existing_names:
        dry_echo(
            dry,
            "Creating label '{}' ({})".format(label, new_labels[label]),
            fg="green"
        )
        if not dry:
            repo.create_label(label, new_labels[label])

    for label in desired_names & existing_names:
        if existing_labels[label].color.lower() != new_labels[label].lower():
            dry_echo(
                dry,
                "Updating label '{}' to {}".format(label, new_labels[label]),
                fg="yellow"
            )
            if not dry:
                existing_labels[label].update(label, new_labels[label])

    for label in existing_names - desired_names:
        dry_echo(
            dry,
            "Deleting label '{}'".format(label),
            fg="red"
        )
        if not dry:
            existing_labels[label].delete()


@click.command()
@pass_github
@pass_repo_tools_data
@click.option('--org', multiple=True, default=['edx', 'edx-ops'])
@dry
def sync_labels(hub, repo_tools_data, org, dry):
    for repo, openedx_yaml in sorted(iter_openedx_yaml(hub, org)):
        print("Copying labels into {}".format(repo))
        set_or_delete_labels(
            dry,
            repo,
            repo_tools_data.labels
        )
