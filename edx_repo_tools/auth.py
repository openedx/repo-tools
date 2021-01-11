"""
Utility functions for accessing a logged-in connection to GitHub (with
consistent handling of passwords and tokens).
"""

import functools
import logging
import netrc
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

TWO_FACTOR_CODE = None


def do_two_factor():
    """
    Capture two-factor auth input for use by the GitHub object.
    """
    global TWO_FACTOR_CODE  # pylint: disable=global-statement
    if TWO_FACTOR_CODE is None:
        TWO_FACTOR_CODE = input('Two-factor code: ')

    return TWO_FACTOR_CODE


def login_github(username=None, password=None, token=None, token_file=None):
    """
    Log in to GitHub using the specified username, password, token, or
    token_file.

    The token_file is used preferentially, containing a personal access token.
    If not specified, read from an auth.yaml file in the user settings
    directory.  if that doesn't exist, read ~/.netrc.  If that doesn't exist,
    prompt for username and password, create a token, and store it in the user
    settings directory.

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
        token_file (string):
            File containing the personal access token to log in with. Overrides
            token argument. File can be a named pipe (bash process
            substitution) for increased security.

    Returns: (:class:`~github3.GitHub`)
        A logged-in `~github3.GitHub` instance
    """
    hub = None

    try:
        with open(AUTH_CONFIG_FILE) as auth_config:
            AUTH_SETTINGS = yaml.safe_load(auth_config)
        LOGGER.info(f"Read auth from {AUTH_CONFIG_FILE!r}")
    except:  # pylint: disable=bare-except
        LOGGER.debug('Unable to load auth settings', exc_info=True)
        AUTH_SETTINGS = {}

    if username is None:
        username = AUTH_SETTINGS.get('username')

    if token is None:
        token = AUTH_SETTINGS.get('token')

    # Log in with token from file, if it's supplied
    if token_file is not None and username is not None:
        with open(token_file) as tf:
            token = tf.readline()[:-1]
            if token:
                hub = login(username, token)
            else:
                LOGGER.warn("No token in file")

    # Otherwise, fall back to password, if supplied
    elif password is not None and username == AUTH_SETTINGS.get('username'):
        hub = login(username, password, two_factor_callback=do_two_factor)

    # Otherwise, log in with the stored token
    elif username is not None and token is not None:
        hub = login(username, token)

    else:
        # Try .netrc
        try:
            netrc_data = netrc.netrc()
        except OSError:
            # No .netrc file, that's fine.
            pass
        else:
            LOGGER.info("Read .netrc for auth")
            authenticator = netrc_data.authenticators("api.github.com")
            if authenticator is not None:
                username, _, token = authenticator
            hub = login(username, token)

    # If no password or token, prompt for a password
    # and generate a token, and then store the token
    if hub is None:
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

            authorizations = hub.authorizations()
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
            LOGGER.info(f"Wrote credentials to {AUTH_CONFIG_FILE!r}")

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
            hub.organization('edx').repositories()
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
    )
    @click.option('--password', help='Password to log in to GitHub with')
    @click.option(
        '--token',
        help='Personal access token to log in to GitHub with',
    )
    @click.option(
        '--token-file',
        help='File containing personal access token to log in to GitHub with',
    )
    @click.option(
        '--debug/--no-debug',
        help='Enable debug logging',
        default=False
    )
    @functools.wraps(f)
    def wrapped(username, password, token, token_file, debug, *args, **kwargs):

        if debug:
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)

        hub = login_github(username, password, token, token_file)

        f(hub=hub, *args, **kwargs)

    return wrapped
