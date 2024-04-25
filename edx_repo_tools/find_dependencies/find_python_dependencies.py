"""
Spider and catalog dependencies.
$ python find_python_dependencies.py $FILE_PATH
"""

import json
import os
import requirements
import sys
from pathlib import Path
import requests


# The first of these we find is the requirements file we'll examine:
PY_REQS = [
    "requirements/edx/base.txt",
    "requirements/base.txt",
    "requirements.txt",
]

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

def main(dirs=None, org=None):
    """
    Analyze the requirements in input directory mentioned on the command line.    
    """
    packages_url = [] 
    if dirs is None:
        repo_dir = sys.argv[1]

    with open(repo_dir) as fbase:
        # Read each line (package name) in the file
        for req in requirements.parse(fbase):
            print(req.name)
            home_page = request_package_info_url(req.name)
            if home_page is not None:
                if match := urls_in_orgs([home_page], SECOND_PARTY_ORGS):
                    packages_url.append(home_page)

    print("== DONE ==============")
    print("Second-party:")
    print("\n".join(packages_url))
    
    if packages_url:
        sys.exit(1)

if __name__ == "__main__":
    main()