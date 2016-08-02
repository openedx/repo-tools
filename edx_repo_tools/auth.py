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
except:
    LOGGER.debug('Unable to load auth settings', exc_info=True)
    AUTH_SETTINGS = {}


TWO_FACTOR_CODE = None


def do_two_factor():
    global TWO_FACTOR_CODE
    if TWO_FACTOR_CODE is None:
        TWO_FACTOR_CODE = raw_input('Two-factor code: ')

    return TWO_FACTOR_CODE


def pass_github(f):
    @click.command(context_settings=dict(default_map=AUTH_SETTINGS))
    @click.option('--username', prompt=True, help='Specify the user to log in to GitHub with')
    @click.option('--password', help='Password to log in to GitHub with')
    @click.option('--token', help='Personal access token to log in to GitHub with')
    @click.option('--debug/--no-debug', help='Enable debug logging', default=False)
    @click.pass_context
    @functools.wraps(f)
    def wrapped(ctx, username, password, token, debug, *args, **kwargs):
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

        # Log in with password, if it's supplied
        if password is not None and username == AUTH_SETTINGS.get('username'):
            hub = login(username, password, two_factor_callback=do_two_factor)

        # Otherwise, log in with the stored token
        elif token is not None and username == AUTH_SETTINGS.get('username'):
            hub = login(username, token)

        # If no password or token, prompt for a password
        # and generate a token, and then store the token
        else:
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

            with open(AUTH_CONFIG_FILE, 'w') as auth_config:
                yaml.safe_dump({
                    'username': username,
                    'token': token.token,
                }, auth_config)

        ctx.invoke(f, hub, *args, **kwargs)
    return wrapped
