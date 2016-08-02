import getpass
import os.path
import sys
import yaml

from appdirs import user_config_dir
import click
from github3 import login, GitHubError

import logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)


BRANCH_NAME = 'add-openedx-yaml'
CONFIG_DIR = user_config_dir('edx-repo-tools', 'edx')
AUTH_CONFIG_FILE = os.path.join(CONFIG_DIR, 'auth.yaml')

AUTHORIZATION_NOTE = 'edx-repo-tools'


try:
    with open(AUTH_CONFIG_FILE) as auth_config:
        AUTH_SETTINGS = yaml.safe_load(auth_config)
except:
    LOGGER.debug('Unable to load auth settings', exc_info=True)
    AUTH_SETTINGS = {}


TWO_FACTOR_CODE = None


def do_two_factor():
    global TWO_FACTOR_CODE
    if TWO_FACTOR_CODE is None:
        TWO_FACTOR_CODE = raw_input('Two-factor code: ')

    return TWO_FACTOR_CODE


@click.command(context_settings=dict(default_map=AUTH_SETTINGS))
@click.option('--username', prompt=True, help='Specify the user to log in to GitHub with')
@click.option('--password', help='Password to log in to GitHub with')
@click.option('--token', help='Personal access token to log in to GitHub with')
@click.option('--debug/--no-debug', help='Enable debug logging', default=False)
@click.option('--dry/--yes', help='Actually create the pull requests', default=True)
def cli(username, password, token, debug, dry):
    """
    Explode the repos.yaml file out into pull requests for all of the
    repositories specified in that file.
    """

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Log in with password, if it's supplied
    if password is not None:
        hub = login(username, password, two_factor_callback=do_two_factor)

    # Otherwise, log in with the stored token
    elif token is not None:
        hub = login(username, token)

    # If no password or token, prompt for a password
    # and generate a token, and then store the token
    else:
        password = getpass.getpass()

        hub = login(username, password, two_factor_callback=do_two_factor)

        try:
            token = hub.authorize(
                login=username,
                password=password,
                note=AUTHORIZATION_NOTE,
            )
        except GitHubError as exc:
            if exc.msg != "Validation Failed":
                raise

            LOGGER.debug('Attempting to delete existing authorization')

            authorizations = hub.iter_authorizations()
            for authorization in authorizations:
                if authorization.note == AUTHORIZATION_NOTE:
                    authorization.delete()

            token = hub.authorize(
                login=username,
                password=password,
                scopes=['repo'],
                note=AUTHORIZATION_NOTE,
            )

        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)

        with open(AUTH_CONFIG_FILE, 'w') as auth_config:
            yaml.safe_dump({
                'username': username,
                'token': token.token,
            }, auth_config)

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
            click.secho('Against {}/{}'.format(user, repo_name), fg='yellow', bold=True)
            click.secho('Would have created openedx.yaml file:', fg='yellow', bold=True)
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
