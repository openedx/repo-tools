"""
Spider and catalog dependencies.
$ python find_python_dependencies.py --req-file $FILE_PATH
"""

import click
import json
import os
import requirements
import sys
from pathlib import Path
import requests


# The first of these we find is the requirements file we'll examine:
def request_package_info_url(package):
        base_url = "https://pypi.org/pypi/"
        url = f"{base_url}{package}/json"
        response = requests.get(url)
        if response.status_code == 200:
            data_dict = response.json()
            info = data_dict["info"]
            return info["home_page"]            
        else:
            print(f"Failed to retrieve data for package {package}. Status code:", response.status_code)    

FIRST_PARTY_ORGS = ["openedx"]

SECOND_PARTY_ORGS = [
    "edx", "edx-unsupported", "edx-solutions",
    "mitodl",
    "overhangio",
    "open-craft", "eduNEXT", "raccoongang",
]

def urls_in_orgs(urls, orgs):
    """
    Find urls that are in any of the `orgs`.
    """
    return sorted(
        url for url in urls
        if any(f"/{org}/" in url for org in orgs)
    )

@click.command()
@click.option(
    '--req-file', 'directories',
    multiple=True,
    required=True,
    help="The absolute file paths to locate Python dependencies" 
        "within a particular repository. You can provide this "
        "option multiple times to include multiple requirement files.",
)
@click.option(
    '--ignore', 'ignore_paths',
    multiple=True,
    help="Dependency Repo URL to ignore even if it's"
            "outside of your organization's approved list",
)

def main(directories=None, ignore_paths=None):
    """
    Analyze the requirements in input directory mentioned on the command line.    
    """

    home_page = set()
    for directory in directories:
        with open(directory) as fbase:
            for req in requirements.parse(fbase):
                url = request_package_info_url(req.name)
                if url is not None:
                    home_page.add(url)
                    
    packages_urls = set(urls_in_orgs(home_page, SECOND_PARTY_ORGS))
    
    if diff:= packages_urls.symmetric_difference(set(ignore_paths)):
            print("The following packages are from 2nd party orgs and should not be added as a core dependency, they can be added as an optional dependency operationally or they can be transferred to the openedx org before they are included:")
            print("\n".join(diff))
            exit(1)

if __name__ == "__main__":
    main()