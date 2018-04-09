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

    desired_colors = {label: data['color'] for label, data in new_labels.items() if 'color' in data}
    undesired_names = {label for label, data in new_labels.items() if data.get('delete', False)}
    existing_labels = {label.name: label for label in repo.iter_labels()}
    existing_names = set(existing_labels.keys())
    desired_names = set(desired_colors.keys())

    for label in desired_names - existing_names:
        dry_echo(
            dry,
            "Creating label '{}' ({})".format(label, desired_colors[label]),
            fg="green"
        )
        if not dry:
            repo.create_label(label, desired_colors[label])

    for label in desired_names & existing_names:
        if existing_labels[label].color.lower() != desired_colors[label].lower():
            dry_echo(
                dry,
                "Updating label '{}' to {}".format(label, desired_colors[label]),
                fg="yellow"
            )
            if not dry:
                existing_labels[label].update(label, desired_colors[label])

    for label in undesired_names & existing_names:
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
@click.option('--repo')
@dry
def sync_labels(hub, repo_tools_data, org, repo, dry):
    if repo is not None:
        repos = [(hub.repository(*repo.split('/')), None)]
    else:
        repos = sorted(iter_openedx_yaml(hub, org))
    for repo, _ in repos:
        print("Updating labels in {}".format(repo))
        set_or_delete_labels(
            dry,
            repo,
            repo_tools_data.labels
        )
