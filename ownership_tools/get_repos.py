# coding: utf-8
import csv
import os
import github

from collections import OrderedDict
from pprint import pprint

import yaml
import re

from cache_to_disk import cache_to_disk
from github import Github

ORGS = ['edx','edx-ops','edx-solutions']
LANGUAGE = "Python"

# Collected by running `get_edx_owned_requirements.py`
REPOS_THAT_EDX_PLATFORM_DEPENDS_ON = [
        "https://github.com/edx/edx-ora2",
        "https://github.com/edx/edx-django-release-util",
        "https://github.com/edx/edx-submissions",
        "https://github.com/edx/edx-val",
        "https://github.com/dementrock/pystache_custom",
        "https://github.com/edx/acid-block",
        "https://github.com/edx/ccx-keys",
        "https://github.com/edx/codejail",
        "https://github.com/edx/completion",
        "https://github.com/edx/django-config-models",
        "https://github.com/edx/django-oauth2-provider",
        "https://github.com/edx/django-splash",
        "https://github.com/edx/django-user-tasks",
        "https://github.com/edx/DoneXBlock",
        "https://github.com/edx/edx-ace",
        "https://github.com/edx/edx-celeryutils",
        "https://github.com/edx/edx-django-sites-extensions",
        "https://github.com/edx/edx-django-utils",
        "https://github.com/edx/edx-drf-extensions",
        "https://github.com/edx/edx-enterprise",
        "https://github.com/edx/edx-milestones",
        "https://github.com/edx/edx-oauth2-provider",
        "https://github.com/edx/edx-organizations",
        "https://github.com/edx/edx-proctorin",
        "https://github.com/edx/edx-rbac",
        "https://github.com/edx/edx-rest-api-clien",
        "https://github.com/edx/edx-search",
        "https://github.com/edx/edx-when",
        "https://github.com/edx/event-trackin",
        "https://github.com/edx/help-tokens",
        "https://github.com/edx/i18n-tools",
        "https://github.com/edx/opaque-keys",
        "https://github.com/edx/RateXBlock",
        "https://github.com/edx-solutions/xblock-google-drive",
        "https://github.com/edx/user-util",
        "https://github.com/edx/web-fragments",
        "https://github.com/edx/XBlock",
        "https://github.com/edx/xblock-utils",
        "https://github.com/jazkarta/edx-jsme",
    ]


g = Github(os.environ["GITHUB_TOKEN"])

orgs = [g.get_organization(org) for org in ORGS]

@cache_to_disk(1)
def has_python_code(repo: github.Repository.Repository):
    return LANGUAGE in repo.get_languages()

@cache_to_disk(1)
def python_bytes(repo):
    repo_langs = repo.get_languages()
    if LANGUAGE in repo_langs:
        return repo_langs[LANGUAGE]
    else:
        return 0

@cache_to_disk(1)
def total_language_bytes(repo):
    repo_langs = repo.get_languages()
    total_bytes = 0
    for language, lang_bytes in repo_langs.items():
        total_bytes += lang_bytes

    return total_bytes

@cache_to_disk(1)
def expanded_repos_list(orgs):
    repo_list = []
    for org in orgs:
        for repo in org.get_repos():
            repo_list.append(repo)

    return repo_list

@cache_to_disk(1)
def get_remote_yaml(repo, path):
    """
    Throws the following exceptions:
        github.UnknownObjecTException: if the file does not exist in the repo.
        yaml.YAMLError: if the file is not valid YAML
    """
    # Check to see if the file exists
    content = repo.get_contents(path)

    # make sure the file is valid yaml
    text = content.decoded_content.decode('utf-8')
    yaml_content = yaml.safe_load(text)

    return yaml_content

@cache_to_disk(1)
def is_oep_compliant(repo, oep_name):
    """
    Check to see if a repo is compliant with a given oep

    repo - pygithub repo object.
    oep_name - name of oep as it should show up in openedx.yaml eg. oep-2

    returns (bool,str): whether it's compliant and reason it's not if bool is false.
    """
    # Check to see if the file exists
    try:
        metadata = get_remote_yaml(repo, 'openedx.yaml')
    except github.UnknownObjectException as e:
        return (False, "No openedx.yaml file")
    except yaml.YAMLError as e:
        return (False, "openedx.yaml is not valid yaml.")

    # check to see if oep is compliant within oeps dict.
    if 'oeps' in metadata:
        if oep_name in metadata['oeps']:
            oep_data = metadata['oeps'][oep_name]
            if oep_data == True:
                return (True, "")
            elif isinstance(oep_data, dict):
                if "applicable" not in oep_data or oep_data["applicable"] == "True":
                    if "state" in oep_data and oep_data['state'] == True:
                        return (True, "")
                    else:
                        return (False, oep_data["reason"])
                else:
                    return (False, oep_data["reason"])
            else:
                return (False, "Stated in openedx.yaml")
        else:
            return (False, "No '{}' entry in oeps dictinary.".format(oep_name))
    else:
        return (False, "No oeps dictionary to indicate oep compliance status.")

def is_oep2_compliant(repo):
    """
    OEP-2 is the one that says all our repos need a metadata file with useful information.
    Including but not limited to which OEPs the repo is compliant with.

    returns (bool,str): whether it's compliant and reason it's not if bool is false.
    """

    return is_oep_compliant(repo, "oep-2")

def is_oep7_compliant(repo):
    """
    OEP-7 is the OEP about migrating to python3.  If we are compliant with it, it means that
    the repo is ready to run on python3.

    https://open-edx-proposals.readthedocs.io/en/latest/oep-0007-bp-migrate-to-python3.html

    returns (bool,str): whether it's compliant and reason it's not if bool is false.
    """

    # Check to see if openedx.yaml has an oeps section
    return is_oep_compliant(repo, "oep-7")

@cache_to_disk(1)
def is_oep18_compliant(repo):
    """
    OEP-18 is the one about Python Dependency Management
        -mainly includes implementing make upgrade and placing all the dependencies in requirement directory
    returns (bool,str): whether it's compliant and reason it's not if bool is false.
    """
    return is_oep_compliant(repo, "oep-18")

@cache_to_disk(1)
def might_be_oep18_compliant(repo):
    """
    Use alternate indicators to see if a repo is oep18 complaint. Checks to see if upgrade target is in Makefile

    returns (bool,str): whether it might compliant and reason we think so if it's true.
    """
    try:
        makefile_contentfile= repo.get_contents("Makefile")
        makefile_content_file_string = makefile_contentfile.decoded_content.decode('utf-8')
        search_output = re.search("^upgrade:", makefile_content_file_string, re.MULTILINE)
        if search_output:
            return (True, "upgrade target exists in Makefile")
        return (False, "upgrade target does not exist in makefile")
    except github.UnknownObjectException as e:
        return (False, "Makefile does not exit in repo")

def filter_valid_pythons(version_list):
    """
    Yield versions of python3 that we currently consider valid.
    """
    for version in version_list:
        if version == 'pypy':
            continue

        elif version == 'nightly':
            yield version

        elif version == 'pypy3.5':
            yield version

        elif type(version) == float and version >= 3.5:
            yield version

        elif type(version) == str:
            parsed_version = re.search("^\d+(\.\d+)?", version)
            if parsed_version:
                if float(parsed_version.group(0)) >= 3.5:
                    yield version

def might_be_oep7_compliant(repo):
    """
    Use alternate indicators to see if a repo supports python3

    returns (bool,str): whether it might compliant and reason we think so if it's true.
    """

    # Don't check for a tox.ini because services might have this setup
    # even if they're not passing with python3 so they can at_least run python3

    # It would be nice to check setup.py classifiers but it's not clear that
    # there is an easy way to read this.

    # Check to see if the library uses travis and runs tests on python3
    # The value of the 'python' key in yaml can be a list of numbers, a string or
    # a list of strings so we need to handle all those cases.
    try:
        travis_config = get_remote_yaml(repo, ".travis.yml")

        if 'python' in travis_config:
            python_data = travis_config['python']
            if type(python_data) == str or type(python_data) == float:
                if float(python_data) >= 3.5:
                    return (True, "Running only on python {}".format(python_data))
                else:
                    return (False, "Running older python({})".format(python_data))
            elif type(python_data) == list:
                valid_versions = list(filter_valid_pythons(python_data))
                if len(valid_versions) > 0:
                    return (True, "Running tests on the following valid pythons: {}".format(valid_versions))
                else:
                    return (False, "Running older pythons: {}".format(python_data))
        else:
            return (False, "No python section in travis.yaml.")

    except github.UnknownObjectException as e:
        return (False, "No .travis.yml file to use as an indicator.")
    except yaml.YAMLError as e:
        return (False, "Invalid travis config so can't use this as an indicator.")

def get_repo_owner(repo):
    """
    Return None if no owner found.
    """

    try:
        openedx = get_remote_yaml(repo, "openedx.yaml")
        return openedx.get('owner')
    except github.UnknownObjectException as e:
        return None
    except yaml.YAMLError as e:
        return None

def is_in_openedx(repo):
    """
    Return True if this repo is tagged as a part of the openedx releases, False otherwise.
    """
    try:
        openedx = get_remote_yaml(repo, "openedx.yaml")
        if openedx.get('openedx-release'):
            return True
        elif repo.html_url in REPOS_THAT_EDX_PLATFORM_DEPENDS_ON:
            return True
    except github.UnknownObjectException as e:
        return False
    except yaml.YAMLError as e:
        return False

    return False

def get_openedx_tags(repo):
    try:
        openedx = get_remote_yaml(repo, "openedx.yaml")
        return openedx.get("tags", [])

    except github.UnknownObjectException as e:
        return []
    except yaml.YAMLError as e:
        return []

    return []

class Milestones:
    M2 = "M2: OpenedX Libraries"
    M3 = "M3: edX Owned Forks"
    M4 = "M4: OpenedX Webservices"
    M7 = "M7: edX Webservices"
    M9 = "M9: Non-public edX services"
    OPENEDX_OTHER = "M4: OpenedX Other"
    EDX_OTHER = "M9: edX Other"

def bin_repo_to_milestone(repo):
    """
    Given a repo figure out which python 3 conversion milestone it should be done by.
    per: https://openedx.atlassian.net/wiki/spaces/AC/pages/997818579/WIP+Project+Plan+Python3
    """

    # Assume all forks are part of milestone 3
    if repo.fork:
        return Milestones.M3

    tags = get_openedx_tags(repo)
    if is_in_openedx(repo):
        if "library" in tags:
            return Milestones.M2
        if "webservice" in tags:
            return Milestones.M4

        return Milestones.OPENEDX_OTHER
    else:
        if "webservice" in tags:
            return Milestones.M7
        if "backend-service" in tags:
            return Milestones.M9

        return Milestones.EDX_OTHER


if __name__ == "__main__":
    with open('python_state.csv', 'w', newline='') as csvfile:

        ### NOTE: Only add new fields to the bottom of this list otherwise
        #         it will screw up the pivot tables in the spreadsheet this
        #         feeds: https://docs.google.com/spreadsheets/d/1xMIhQZ4_VHdS6qS91Ya8lOzuwdfcYau-U9pHZbfXG9U/edit#gid=651103923
        fieldnames = ['python_bytes',
                      'html_url',
                      'owner',
                      'is_archived',
                      'is_fork',
                      'oep2_compliant',
                      'oep2_compliant_reason',
                      'oep7_compliant',
                      'oep7_compliant_reason',
                      'oep7_maybe',
                      'oep7_maybe_reason',
                      'is_in_openedx',
                      'edx-platform dependency',
                      'python_3_milestone',
                      'oep18_compliant',
                      'oep18_compliant_reason',
                      'oep18_maybe',
                      'oep18_maybe_reason'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for repo in expanded_repos_list(orgs):
            repo_data = {}
            repo_data['python_bytes'] = python_bytes(repo)

            if repo_data['python_bytes'] > 0:
                oep2_compliance = is_oep2_compliant(repo)
                oep7_compliance = is_oep7_compliant(repo)
                oep7_maybe = might_be_oep7_compliant(repo)
                oep18_compliance = is_oep18_compliant(repo)
                oep18_maybe = might_be_oep18_compliant(repo)

                repo_data['html_url'] = repo.html_url
                repo_data['is_archived'] = repo.archived
                repo_data['is_fork'] = repo.fork
                repo_data['oep2_compliant'] = oep2_compliance[0]
                repo_data['oep2_compliant_reason'] = oep2_compliance[1]
                repo_data['oep7_compliant'] = is_oep7_compliant(repo)[0]
                repo_data['oep7_compliant_reason'] = is_oep7_compliant(repo)[1]
                repo_data['oep7_maybe'] = might_be_oep7_compliant(repo)[0]
                repo_data['oep7_maybe_reason'] = might_be_oep7_compliant(repo)[1]
                repo_data['oep18_compliant'] = oep18_compliance[0]
                repo_data['oep18_compliant_reason'] = oep18_compliance[1]
                repo_data['oep18_maybe'] = oep18_maybe[0]
                repo_data['oep18_maybe_reason'] = oep18_maybe[1]
                repo_data['owner'] = get_repo_owner(repo)
                repo_data['is_in_openedx'] = is_in_openedx(repo)
                repo_data['edx-platform dependency'] = repo.html_url in REPOS_THAT_EDX_PLATFORM_DEPENDS_ON
                repo_data['python_3_milestone'] = bin_repo_to_milestone(repo)

                if repo_data['is_archived']:
                    continue

                print(repo_data)
                writer.writerow(repo_data)
