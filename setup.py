import glob
import os
import os.path
import re
import sys

import setuptools
from setuptools import setup

with open('README.rst') as readme:
    long_description = readme.read()


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.

    Requirements will include any constraints from files specified
    with -c in the requirements files.
    Returns a list of requirement strings.
    """
    # UPDATED VIA SEMGREP - if you need to remove/modify this method remove this line and add a comment specifying why.

    # e.g. {"django": "Django", "confluent-kafka": "confluent_kafka[avro]"}
    by_canonical_name = {}

    def check_name_consistent(package):
        """
        Raise exception if package is named different ways.

        This ensures that packages are named consistently so we can match
        constraints to packages. It also ensures that if we require a package
        with extras we don't constrain it without mentioning the extras (since
        that too would interfere with matching constraints.)
        """
        canonical = package.lower().replace('_', '-').split('[')[0]
        seen_spelling = by_canonical_name.get(canonical)
        if seen_spelling is None:
            by_canonical_name[canonical] = package
        elif seen_spelling != package:
            raise Exception(
                f'Encountered both "{seen_spelling}" and "{package}" in requirements '
                'and constraints files; please use just one or the other.'
            )

    requirements = {}
    constraint_files = set()

    # groups "pkg<=x.y.z,..." into ("pkg", "<=x.y.z,...")
    re_package_name_base_chars = r"a-zA-Z0-9\-_."  # chars allowed in base package name
    # Two groups: name[maybe,extras], and optionally a constraint
    requirement_line_regex = re.compile(
        r"([%s]+(?:\[[%s,\s]+\])?)([<>=][^#\s]+)?"
        % (re_package_name_base_chars, re_package_name_base_chars)
    )

    def add_version_constraint_or_raise(current_line, current_requirements, add_if_not_present):
        regex_match = requirement_line_regex.match(current_line)
        if regex_match:
            package = regex_match.group(1)
            version_constraints = regex_match.group(2)
            check_name_consistent(package)
            existing_version_constraints = current_requirements.get(package, None)
            # It's fine to add constraints to an unconstrained package,
            # but raise an error if there are already constraints in place.
            if existing_version_constraints and existing_version_constraints != version_constraints:
                raise BaseException(f'Multiple constraint definitions found for {package}:'
                                    f' "{existing_version_constraints}" and "{version_constraints}".'
                                    f'Combine constraints into one location with {package}'
                                    f'{existing_version_constraints},{version_constraints}.')
            if add_if_not_present or package in current_requirements:
                current_requirements[package] = version_constraints

    # Read requirements from .in files and store the path to any
    # constraint files that are pulled in.
    for path in requirements_paths:
        with open(path) as reqs:
            for line in reqs:
                if is_requirement(line):
                    add_version_constraint_or_raise(line, requirements, True)
                if line and line.startswith('-c') and not line.startswith('-c http'):
                    constraint_files.add(os.path.dirname(path) + '/' + line.split('#')[0].replace('-c', '').strip())

    # process constraint files: add constraints to existing requirements
    for constraint_file in constraint_files:
        with open(constraint_file) as reader:
            for line in reader:
                if is_requirement(line):
                    add_version_constraint_or_raise(line, requirements, False)

    # process back into list of pkg><=constraints strings
    constrained_requirements = [f'{pkg}{version or ""}' for (pkg, version) in sorted(requirements.items())]
    return constrained_requirements


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement.

    Returns:
        bool: True if the line is not blank, a comment,
        a URL, or an included file
    """
    # UPDATED VIA SEMGREP - if you need to remove/modify this method remove this line and add a comment specifying why

    return line and line.strip() and not line.startswith(('-r', '#', '-e', 'git+', '-c'))


VERSION = get_version('edx_repo_tools', '__init__.py')


# Find our extra requirements. A subdirectory of edx_repo_tools can have an
# extra.in file. It will be pip-compiled to extra.txt.  Here we find them all
# and register them as extras.
EXTRAS_REQUIRE = {}
for fextra in glob.glob("edx_repo_tools/*/extra.txt"):
    slug = fextra.split("/")[1]
    if sys.version_info >= (3, 12) and glob.glob(f'edx_repo_tools/{slug}/extra-py312.txt'):
        fextra = f'edx_repo_tools/{slug}/extra-py312.txt'

    EXTRAS_REQUIRE[slug] = load_requirements(fextra)

# To run tests & linting across the entire repo, we need to install the union
# of *all* extra requirements lists *plus* the dev-specific requirements.
# If this list contains conflicting pins, then installing it will fail;
# that is intentional.
EXTRAS_REQUIRE["dev"] = sorted({
    *load_requirements("requirements/development.txt"),
    *(extra_pin for extra_reqs in EXTRAS_REQUIRE.values() for extra_pin in extra_reqs),
})

setup(
    name='edx-repo-tools',
    version=VERSION,
    description="This repo contains a number of tools Open edX uses for working with GitHub repositories.",
    long_description=long_description,
    license='Apache',
    keywords='edx repo tools',
    url='https://github.com/openedx/repo-tools',
    author='edX',
    author_email='oscm@edx.org',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License'
    ],
    packages=setuptools.find_packages(),
    install_requires=load_requirements("requirements/base.txt"),
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        'console_scripts': [
            'add_common_constraint = edx_repo_tools.add_common_constraint:main',
            'add_dependabot_ecosystem = edx_repo_tools.dependabot_yml:main',
            'add_django32_settings = edx_repo_tools.codemods.django3.add_new_django32_settings:main',
            'audit_users = edx_repo_tools.audit_gh_users.audit_users:main',
            'clone_org = edx_repo_tools.dev.clone_org:main',
            'conventional_commits = edx_repo_tools.conventional_commits.commitstats:main',
            'find_dependencies = edx_repo_tools.find_dependencies.find_dependencies:main',
            'find_python_dependencies = edx_repo_tools.find_dependencies.find_python_dependencies:main',
            'get_org_repo_urls = edx_repo_tools.dev.get_org_repo_urls:main',
            'modernize_github_actions = edx_repo_tools.codemods.django3.github_actions_modernizer:main',
            'modernize_github_actions_django = edx_repo_tools.codemods.django3.github_actions_modernizer_django:main',
            'modernize_node_release_workflow = edx_repo_tools.codemods.node16.gha_release_workflow_modernizer:main',
            'modernize_node_workflow = edx_repo_tools.codemods.node16.gha_ci_modernizer:main',
            'modernize_openedx_yaml = edx_repo_tools.modernize_openedx_yaml:main',
            'modernize_setup_file = edx_repo_tools.codemods.django3.setup_file_modernizer:main',
            'modernize_tox = edx_repo_tools.codemods.django3.tox_modernizer:main',
            'modernize_travis = edx_repo_tools.codemods.django3.travis_modernizer:main',
            'no_yaml = edx_repo_tools.ospr.no_yaml:no_yaml',
            'oep2 = edx_repo_tools.oep2:_cli',
            'pull_request_creator = edx_repo_tools.pull_request_creator:main',
            'remove_python2_unicode_compatible = edx_repo_tools.codemods.django3.remove_python2_unicode_compatible:main',
            'replace_render_to_response = edx_repo_tools.codemods.django3.replace_render_to_response:main',
            'replace_static = edx_repo_tools.codemods.django3.replace_static:main',
            'replace_unicode_with_str = edx_repo_tools.codemods.django3.replace_unicode_with_str:main',
            'repo_access_scraper = edx_repo_tools.repo_access_scraper.repo_access_scraper:main',
            'repo_checks = edx_repo_tools.repo_checks.repo_checks:main',
            'show_hooks = edx_repo_tools.dev.show_hooks:main',
            'tag_release = edx_repo_tools.release.tag_release:main',
            'modernize_tox_django42 = edx_repo_tools.codemods.django42.tox_moderniser_django42:main',
            'modernize_github_actions_django42 = edx_repo_tools.codemods.django42.github_actions_modernizer_django42:main',
            'remove_providing_args = edx_repo_tools.codemods.django42.remove_providing_args_arg:main',
            'python312_gh_actions_modernizer = edx_repo_tools.codemods.python312.gh_actions_modernizer:main',
            'python312_tox_modernizer = edx_repo_tools.codemods.python312.tox_modernizer:main',
        ],
    },
    package_data={
        'edx_repo_tools.oep2.report': ['oep2-report.ini'],
        'edx_repo_tools.repo_checks': ['labels.yaml'],
    },
)
