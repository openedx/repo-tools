from collections import defaultdict
import logging

import click
from lazy import lazy
from tabulate import tabulate
import yaml

from edx_repo_tools.auth import pass_github

LOGGER = logging.getLogger(__name__)


class Oep2Result(object):
    def __init__(self, passed, reasons):
        self.passed = passed
        self.reasons = reasons

    def __nonzero__(self):
        return self.passed

    def __add__(self, other):
        if other is None:
            return self

        if not isinstance(other, Oep2Result):
            raise TypeError('Can only add Oep2Results to each other')

        return Oep2Result(self.passed and other.passed, self.reasons + other.reasons)

    def __radd__(self, other):
        if other is None:
            return self

        raise TypeError('Can only add Oep2Results to each other')


class Oep2Check(object):
    def __init__(self, number, repo, contents):
        self.number = number
        self.repo = repo
        self.contents = contents

    @lazy
    def explicit_value(self):
        if self.contents is None:
            return None

        value = self.contents.get('oeps', {}).get('oep-{}'.format(self.number))

        if isinstance(value, dict):
            return Oep2Result(value['state'], [value['reason']])
        else:
            return Oep2Result(value, [['N/A']])

    @lazy
    def result(self):
        expl = self.explicit_value

        if expl is None:
            return self.implicit_value

        return expl

    @lazy
    def implicit_value(self):
        checker = globals().get('check_oep{}'.format(self.number))

        if checker is None:
            return None

        return checker(self.contents)

    def __unicode__(self):
        if self.result is None:
            style = {'fg': 'yellow'}
        elif self.result:
            style = {'fg': 'green', 'bold': True}
        else:
            style = {'fg': 'red'}

        return click.style("\n".join(self.result.reasons), **style)


@click.command()
@pass_github
@click.option('-o', '--org', multiple=True, show_default=True, default=['edx', 'edx-ops'])
def cli(hub, org):
    oeps = range(10)
    results = defaultdict(dict)

    for repo, contents in iter_openedx_yamls(hub, org):
        for oep in oeps:
            results[repo][oep] = Oep2Check(oep, repo, contents)

    inactive_oeps = []
    for oep in oeps:
        if all(results[repo][oep].result is None for repo in results):
            for repo in results:
                del results[repo][oep]
            inactive_oeps.append(oep)

    for oep in inactive_oeps:
        oeps.remove(oep)

    header = ['Repo']
    header.extend('OEP-{}'.format(oep) for oep in oeps)
    table = []

    for repo in sorted(results, key=lambda repo: repo.full_name):
        repo_row = [repo]
        repo_row.extend(results[repo][oep] for oep in oeps)
        table.append(repo_row)

    print tabulate(table, headers=header)


def iter_openedx_yamls(hub, orgs):
    for org in orgs:
        for repo in hub.organization(org).iter_repos():
            if repo.fork:
                LOGGER.debug('skipping %s because it is a fork', repo.full_name)
                continue

            raw_contents = repo.contents('openedx.yaml')
            if raw_contents is None:
                yield repo, None
            else:
                yaml_contents = yaml.safe_load(raw_contents.decoded)
                yield repo, yaml_contents


def check_oep2(openedx_yaml):
    if openedx_yaml is None:
        return Oep2Result(False, ['openedx.yaml is missing'])

    return sum(
        [
            Oep2Result(
                openedx_yaml.get('owner') != "MUST FILL IN OWNER",
                "'owner' is required'",
            ),
            Oep2Result('nick' in openedx_yaml, "'nick' is required"),
            Oep2Result('tags' in openedx_yaml, "'tags' is required"),
            Oep2Result('oeps' in openedx_yaml, "'oeps' is required"),
        ],
        start=None,
    )
