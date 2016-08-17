"""
``oep2 explode``: Split out edx/repo-tools-data:repos.yaml into individual
openedx.yaml files in specific repos.
"""

import click
import logging
import yaml

from edx_repo_tools.auth import pass_github

LOGGER = logging.getLogger(__name__)

BRANCH_NAME = 'add-openedx-yaml'
OPEN_EDX_YAML = 'openedx.yaml'


@click.command()
@pass_github
@click.option(
    '--dry/--yes',
    default=True,
    help='Actually create the pull requests',
)
def explode(hub, dry):
    """
    Explode the repos.yaml file out into pull requests for all of the
    repositories specified in that file.
    """

    repo_tools_data = hub.repository('edx', 'repo-tools-data')
    repos_yaml = repo_tools_data.contents('repos.yaml').decoded

    repos = yaml.safe_load(repos_yaml)

    for repo, repo_data in repos.items():
        user, _, repo_name = repo.partition('/')

        if repo_data is None:
            repo_data = {}

        if 'owner' not in repo_data:
            repo_data['owner'] = 'MUST FILL IN OWNER'
        if 'area' in repo_data:
            repo_data.setdefault('tags', []).append(repo_data['area'])
            del repo_data['area']
        repo_data.setdefault('oeps', {})

        file_contents = yaml.safe_dump(repo_data, indent=4)

        if dry:
            click.secho(
                'Against {}/{}'.format(user, repo_name),
                fg='yellow', bold=True
            )
            click.secho(
                'Would have created openedx.yaml file:',
                fg='yellow', bold=True
            )
            click.secho(file_contents)
            continue

        gh_repo = hub.repository(user, repo_name)

        gh_repo.create_ref(
            'refs/heads/{}'.format(BRANCH_NAME),
            gh_repo.branch('master').commit.sha,
        )
        gh_repo.create_file(
            path=OPEN_EDX_YAML,
            message='Add an OEP-2 compliant openedx.yaml file',
            content=file_contents,
            branch=BRANCH_NAME,
        )
        pull = gh_repo.create_pull(
            title='Add an OEP-2 compliant openedx.yaml file',
            base='master',
            head=BRANCH_NAME,
        )
        click.secho('Created pull request {} against {}'.format(
            pull.html_url,
            repo,
        ), fg='green')


@click.command()
@pass_github
@click.option('--org', multiple=True, default=['edx', 'edx-ops'])
def implode(hub, org):
    """
    Implode all openedx.yaml files, and print the results as formatted output.
    """
    data = dict(iter_openedx_yaml(hub, org))
    click.echo(yaml.safe_dump(data, encoding=None, indent=4))


def iter_openedx_yaml(hub, orgs):
    for org in orgs:
        for repo in hub.organization(org).iter_repos():
            if repo.fork:
                LOGGER.debug("Skipping %s because it is a fork", repo.full_name)
                continue

            contents = repo.contents(OPEN_EDX_YAML)
            if contents is None:
                LOGGER.debug("Skipping %s because there is no %s", repo.full_name, OPEN_EDX_YAML)
                continue

            yield repo.full_name, yaml.safe_load(contents.decoded)
