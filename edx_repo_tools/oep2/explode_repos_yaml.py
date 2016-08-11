"""
``oep2 explode``: Split out edx/repo-tools-data:repos.yaml into individual
openedx.yaml files in specific repos.
"""

import click
import yaml

from edx_repo_tools.auth import pass_github

BRANCH_NAME = 'add-openedx-yaml'


@click.command()
@pass_github
@click.option(
    '--dry/--yes',
    default=True,
    help='Actually create the pull requests',
)
def cli(hub, dry):
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
            path='openedx.yaml',
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
