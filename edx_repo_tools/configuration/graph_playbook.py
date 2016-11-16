#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from io import open

from path import Path
from pygraphviz import AGraph
import click
import yaml

click.disable_unicode_literals_warning = True

SERVICES = (
    'analytics_api',
    'certs',
    'ecommerce',
    'ecomworker',
    'edxapp',
    'elasticsearch',
    'forum',
    'insights',
    'memcache',
    'mongo',
    'mysql',
    'nginx',
    'notifier',
    'programs',
    'rabbitmq',
    'supervisor',
    'xqueue',
)
SERVICE_COLOR = 'cornflowerblue'
OPTIONAL_SERVICE_COLOR = 'darkolivegreen1'


class Role(object):
    def __init__(self, name, is_optional=False):
        self.name = name
        self.is_optional = is_optional
        self.dependencies = []

    @property
    def color(self):
        color = 'transparent'
        if self.is_optional:
            color = OPTIONAL_SERVICE_COLOR
        elif self.is_service:
            color = SERVICE_COLOR
        return color

    @property
    def is_service(self):
        return self.name in SERVICES

    @property
    def style(self):
        if self.is_service:
            return 'filled'
        else:
            return ''


def _parse_raw_list(raw_list):
    roles = []

    for r in raw_list:
        if isinstance(r, basestring):
            roles.append(Role(r))
        if isinstance(r, dict):
            is_optional = False
            if 'when' in r:
                is_optional = True
            roles.append(Role(r['role'], is_optional))
    return roles


def _get_role_dependencies(role, role_dir):
    deps_file = Path(role_dir).joinpath(role.name, 'meta', 'main.yml')
    if not deps_file.exists():
        return []

    with open(deps_file, 'rb') as f:
        meta = yaml.safe_load(f.read())
    if meta:
        deps = _parse_raw_list(meta.get('dependencies', []))
    else:
        deps = []
    return deps


def _graph_role(graph, role):
    graph.add_node(role.name, style=role.style, fillcolor=role.color)
    edge_options = dict(
        arrowsize=.5,
        dir='back',
        style='dashed',
    )
    for dep in role.dependencies:
        graph.add_node(dep.name, style=dep.style, fillcolor=dep.color)
        graph.add_edge(dep.name, role.name, **edge_options)


def expand_roles(raw_list, role_dir):
    role_list = _parse_raw_list(raw_list)
    roles = {}

    while role_list:
        role = role_list.pop(0)
        role.dependencies = _get_role_dependencies(role, role_dir)
        roles[role.name] = role
        role_list.extend(role.dependencies)

    return roles


def graph_roles(roles, outfile, name):
    label = Path(name).basename()
    graph = AGraph(directed=True, label=label)
    for legend, color in (
            ('Service', SERVICE_COLOR),
            ('Optional Service', OPTIONAL_SERVICE_COLOR)
    ):
        graph.add_node(legend, style='filled', fillcolor=color)
    for k, role in roles.items():
        _graph_role(graph, role)
    graph.draw(outfile, prog='dot')


@click.command()
@click.argument('yaml-file', type=click.File('rb'))
@click.argument('role-dir', type=click.Path(exists=True))
@click.argument('output-file')
def cli(yaml_file, role_dir, output_file):
    """
    Graph role dependencies for an Ansible playbook.
    """
    playbook = yaml.safe_load(yaml_file.read())
    role_list = playbook[0]['roles']
    roles = expand_roles(role_list, role_dir)
    graph_roles(roles, output_file, yaml_file.name)
