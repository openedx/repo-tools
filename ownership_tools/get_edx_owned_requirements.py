"""
Given a github repo, and a series of requirements files. Get a list of 
requirements that are owned by the edx org.
"""
import os


import json
import pip
import github
import requests

from requirements.requirement import Requirement
from cache_to_disk import cache_to_disk

REPO = 'edx/edx-platform'
REQUIREMENTS_FILES = [
        "requirements/edx/base.txt",
        "requirements/edx-sandbox/base.txt",
        ]

PYPI_PACKAGE_API_URL = "https://pypi.org/pypi/{package_name}/json"

@cache_to_disk(1)
def get_pypi_data(package_name):
    r = requests.get(PYPI_PACKAGE_API_URL.format(package_name=package_name))
    try:
        data = r.json()
        return data
    except json.decoder.JSONDecodeError as e:
        #print("Package Failed: {}".format(package_name))
        pass

    return {}


def get_edx_owned_requirements(repo, requirements_files):
    """
    Given a github repo object and a list of requirements files.
    Get all requirements that are owned by edX or dependencies not from
    PYPI.
    """

    for file_path in requirements_files:

        # Get the file.
        content = repo.get_contents(file_path)
        text = content.decoded_content.decode('utf-8')
    
        # Go line by line because the requirements library won't work
        # if any of the lines fail to parse.
        for line in text.splitlines():
            try:
                req = Requirement.parse(line)
            except ValueError as e:
                #msg = "ERROR: {line}, {exception}"
                #print(msg.format(line=line, exception=e))
                continue
    
            pypi_data = get_pypi_data(req.name)
    
            if not pypi_data:
                print(req.uri.lstrip("git+").rstrip(".git"))
            elif 'info' in pypi_data:
                author = pypi_data['info']['author']
                home_page = pypi_data['info']['home_page']
    
                if author.lower() == "edx":
                    if home_page.endswith('.git'):
                        print(home_page[:-4])
                    else:
                        print(home_page)

if __name__ == "__main__":
    g = github.Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(REPO)
    get_edx_owned_requirements(repo, REQUIREMENTS_FILES)
