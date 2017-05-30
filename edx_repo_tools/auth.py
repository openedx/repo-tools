"""
Utility functions for accessing a logged-in connection to GitHub (with
consistent handling of passwords and tokens).
"""

import functools
import logging
import os.path

from appdirs import user_config_dir
import click
from github3 import login, GitHubError
import yaml


logging.basicConfig()
LOGGER = logging.getLogger(__name__)

CONFIG_DIR = user_config_dir('edx-repo-tools', 'edx')
AUTH_CONFIG_FILE = os.path.join(CONFIG_DIR, 'auth.yaml')

AUTHORIZATION_NOTE = 'edx-repo-tools'


try:
    with open(AUTH_CONFIG_FILE) as auth_config:
        AUTH_SETTINGS = yaml.safe_load(auth_config)
except:  # pylint: disable=bare-except
    LOGGER.debug('Unable to load auth settings', exc_info=True)
    AUTH_SETTINGS = {}


TWO_FACTOR_CODE = None


def do_two_factor():
    """
    Capture two-factor auth input for use by the GitHub object.
    """
    global TWO_FACTOR_CODE  # pylint: disable=global-statement
    if TWO_FACTOR_CODE is None:
        TWO_FACTOR_CODE = raw_input('Two-factor code: ')

    return TWO_FACTOR_CODE


def login_github(username=None, password=None, token=None):
    """
    Log in to GitHub using the specified username, password, and token.

    Arguments:
        username (string):
            The user to log in as. If not specified, checks the AUTH_SETTINGS
            dictionary.
        password (string):
            The password to log in with. If not specified, and no ``token`` is
            specified, then prompts the user.
        token (string):
            The personal access token to log in with. If not specified, checks
            the AUTH_SETTINGS dictionary.
    Returns: (:class:`~github3.GitHub`)
        A logged-in `~github3.GitHub` instance
    """
    if username is None:
        username = AUTH_SETTINGS.get('username')

    if token is None:
        token = AUTH_SETTINGS.get('token')

    # Log in with password, if it's supplied
    if password is not None and username == AUTH_SETTINGS.get('username'):
        hub = login(username, password, two_factor_callback=do_two_factor)

    # Otherwise, log in with the stored token
    elif token is not None:
        hub = login(username, token)

    # If no password or token, prompt for a password
    # and generate a token, and then store the token
    else:
        if username is None:
            username = click.prompt('Username')

        password = click.prompt('Password', hide_input=True)

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

        # pylint: disable=redefined-outer-name
        with open(AUTH_CONFIG_FILE, 'w') as auth_config:
            yaml.safe_dump({
                'username': username,
                'token': token.token,
            }, auth_config)

    hub.set_user_agent(AUTHORIZATION_NOTE)

    LOGGER.debug('Rate limit remaining: %d', hub.ratelimit_remaining)

    return hub


def pass_github(f):
    """
    A click decorator that passes a logged-in GitHub instance to a click
    interface (and exposes the appropriate arguments to configure that
    instance).

    For example:

        @click.command()
        @pass_github
        @click.option(
            '--dry/--yes',
            default=True,
            help='Actually create the pull requests',
        )
        def explode(hub, dry):
            hub.organization('edx').iter_repos()
    """

    # Mark that pass_github has been applied already to
    # `f`, so that if the decorator is applied multiple times,
    # it won't pass the `hub` argument multiple times, and
    # so that multiple copies of the click arguments won't be added.
    if getattr(f, '_pass_github_applied', False):
        return f
    f._pass_github_applied = True

    # pylint: disable=missing-docstring
    @click.option(
        '--username',
        help='Specify the user to log in to GitHub with',
        default=AUTH_SETTINGS.get('username'),
    )
    @click.option('--password', help='Password to log in to GitHub with')
    @click.option(
        '--token',
        help='Personal access token to log in to GitHub with',
        default=AUTH_SETTINGS.get('token'),
    )
    @click.option(
        '--debug/--no-debug',
        help='Enable debug logging',
        default=False
    )
    @functools.wraps(f)
    def wrapped(username, password, token, debug, *args, **kwargs):

        if debug:
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)

        hub = login_github(username, password, token)

        f(hub=hub, *args, **kwargs)

    return wrapped
