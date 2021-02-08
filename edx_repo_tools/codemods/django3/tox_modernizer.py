import io
import re
from configparser import ConfigParser, NoSectionError

import click

TOX_SECTION = "tox"
ENVLIST = "envlist"
TEST_ENV_SECTION = "testenv"
TEST_ENV_DEPS = "deps"
PYTHON_SUBSTITUTE = "py38"
DJANGO_SUBSTITUTE = "django{22,30,31}"

DJANGO_22_DEPENDENCY = "django22: Django>=2.2,<2.3\n"
DJANGO_30_DEPENDENCY = "django30: Django>=3.0,<3.1\n"
DJANGO_31_DEPENDENCY = "django31: Django>=3.1,<3.2\n"
NEW_DJANGO_DEPENDENCIES = DJANGO_22_DEPENDENCY + DJANGO_30_DEPENDENCY + DJANGO_31_DEPENDENCY

SECTIONS = [TOX_SECTION, TEST_ENV_SECTION]

PYTHON_PATTERN = "(py{.*?}-?|py[0-9]+,|py[0-9]+-)"

DJANGO_PATTERN = "(django[0-9]+,|django[0-9]+\n|django{.*}\n|django{.*?}|django[0-9]+-|django{.*}-)"

DJANGO_DEPENDENCY_PATTERN = "([^\n]*django[0-9]+:.*\n?)"


class ConfigReader:
    def __init__(self, file_path=None, config_dict=None):
        self.config_dict = config_dict
        self.file_path = file_path

    def get_modernizer(self):
        config_parser = ConfigParser()
        if self.config_dict is not None:
            config_parser.read_dict(self.config_dict)
        else:
            config_parser.read(self.file_path)
        return ToxModernizer(config_parser, self.file_path)


class ToxModernizer:
    def __init__(self, config_parser, file_path):
        self.file_path = file_path
        self.config_parser = config_parser
        self._validate_tox_config_sections()

    def _validate_tox_config_sections(self):
        if not self.config_parser.sections():
            raise NoSectionError("Bad Config. No sections found.")

        if all(section not in SECTIONS for section in self.config_parser.sections()):
            raise NoSectionError("File doesn't contain required sections")

    def _update_env_list(self):
        tox_section = self.config_parser[TOX_SECTION]
        env_list = tox_section[ENVLIST]

        env_list = ToxModernizer._replace_runners(PYTHON_PATTERN, PYTHON_SUBSTITUTE, env_list)
        env_list = ToxModernizer._replace_runners(DJANGO_PATTERN, DJANGO_SUBSTITUTE, env_list)
        self.config_parser[TOX_SECTION][ENVLIST] = env_list

    @staticmethod
    def _replace_runners(pattern, substitute, env_list):
        matches = re.findall(pattern, env_list)
        if not matches:
            return env_list
        substitute = ToxModernizer._get_runner_substitute(matches, substitute)
        return ToxModernizer._replace_matches(pattern, substitute, env_list, matches)

    @staticmethod
    def _replace_matches(pattern, substitute, target, matches):
        if not matches:
            return target
        occurrences_to_replace = len(matches) - 1
        if occurrences_to_replace > 0:
            target = re.sub(pattern, '', target, occurrences_to_replace)
        target = re.sub(pattern, substitute, target)
        return target

    @staticmethod
    def _get_runner_substitute(matches, substitute):
        last_match = matches[-1]
        has_other_runners = last_match.endswith('-')
        return substitute + "-" if has_other_runners else substitute

    def _replace_django_versions(self):
        test_environment = self.config_parser[TEST_ENV_SECTION]
        dependencies = test_environment[TEST_ENV_DEPS]
        matches = re.findall(DJANGO_DEPENDENCY_PATTERN, dependencies)
        dependencies = self._replace_matches(DJANGO_DEPENDENCY_PATTERN, NEW_DJANGO_DEPENDENCIES, dependencies, matches)

        self.config_parser[TEST_ENV_SECTION][TEST_ENV_DEPS] = dependencies

    def _update_config_file(self):
        # ConfigParser insists on using tabs for output. We want spaces.
        with io.StringIO() as configw:
            self.config_parser.write(configw)
            new_ini = configw.getvalue()
        new_ini = new_ini.replace("\t", "    ")
        with open(self.file_path, 'w') as configfile:
            configfile.write(new_ini)

    def modernize(self):
        self._update_env_list()
        self._replace_django_versions()
        self._update_config_file()


@click.command()
@click.option(
    '--path', default='tox.ini',
    help="Path to target tox config file")
def main(path):
    modernizer = ConfigReader(path).get_modernizer()
    modernizer.modernize()


if __name__ == '__main__':
    main()
