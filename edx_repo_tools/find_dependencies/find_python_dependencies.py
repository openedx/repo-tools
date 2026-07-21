"""
Spider and catalog dependencies.
$ python find_python_dependencies.py --req-file $FILE_PATH
"""

import click
import json
import os
import requirements
import sys
import tomllib
from pathlib import Path
from packaging.requirements import Requirement
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


def _dependency_group_names(group, all_groups, seen=None):
    """
    Yield package names from a [dependency-groups] entry, resolving any
    {include-group = "..."} references to the group they point at.
    """
    if seen is None:
        seen = set()
    for item in group:
        if isinstance(item, str):
            yield Requirement(item).name
        elif isinstance(item, dict) and "include-group" in item:
            included = item["include-group"]
            if included in seen:
                continue
            seen.add(included)
            yield from _dependency_group_names(all_groups.get(included, []), all_groups, seen)


def _names_from_pyproject_toml(data):
    """
    Yield package names declared in a pyproject.toml's [project.dependencies],
    [project.optional-dependencies], and [dependency-groups].
    """
    project = data.get("project", {})
    for dep in project.get("dependencies", []):
        yield Requirement(dep).name
    for extra_deps in project.get("optional-dependencies", {}).values():
        for dep in extra_deps:
            yield Requirement(dep).name
    all_groups = data.get("dependency-groups", {})
    for group in all_groups.values():
        yield from _dependency_group_names(group, all_groups)


def _names_from_uv_lock(data):
    """
    Yield package names from a uv.lock's fully-resolved [[package]] list.
    This covers the same direct+transitive dependency closure that a
    pip-compile'd requirements.txt used to represent.
    """
    for package in data.get("package", []):
        name = package.get("name")
        if name:
            yield name


def iter_requirement_names(path):
    """
    Yield package names declared in `path`, which may be a pip-compile style
    requirements.txt, a pyproject.toml, or a uv.lock.
    """
    path = Path(path)
    if path.name == "uv.lock":
        yield from _names_from_uv_lock(tomllib.loads(path.read_text()))
    elif path.name == "pyproject.toml":
        yield from _names_from_pyproject_toml(tomllib.loads(path.read_text()))
    else:
        with open(path) as freq:
            for req in requirements.parse(freq):
                yield req.name


@click.command()
@click.option(
    '--req-file', 'directories',
    multiple=True,
    required=True,
    help="The absolute file paths to locate Python dependencies "
        "within a particular repository. Accepts pip-compile style "
        "requirements.txt files, pyproject.toml, or uv.lock. You can "
        "provide this option multiple times to include multiple files.",
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
        for name in set(iter_requirement_names(directory)):
            url = request_package_info_url(name)
            if url is not None:
                home_page.add(url)

    packages_urls = set(urls_in_orgs(home_page, SECOND_PARTY_ORGS))

    if diff := packages_urls - set(ignore_paths):
            print("The following packages are from 2nd party orgs and should not be added as a core dependency, they can be added as an optional dependency operationally or they can be transferred to the openedx org before they are included:")
            print("\n".join(diff))
            exit(1)

if __name__ == "__main__":
    main()
