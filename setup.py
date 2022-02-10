import os
import re

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


VERSION = get_version('edx_repo_tools', '__init__.py')


setup(
    name='edx-repo-tools',
    version=VERSION,
    description="This repo contains a number of tools Open edX uses for working with GitHub repositories.",
    long_description=long_description,
    license='Apache',
    keywords='edx repo tools',
    url='https://github.com/edx/repo-tools',
    author='edX',
    author_email='oscm@edx.org',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License'
    ],
    packages=setuptools.find_packages(),
    install_requires=[
        'appdirs',
        'click',
        'lazy',
        'github3.py',
        'pytest',
        'pytest-xdist',
        'pyyaml',
        'ruamel.yaml'
    ],
    entry_points={
        'console_scripts': [
            'clone_org = edx_repo_tools.dev.clone_org:main',
            'show_hooks = edx_repo_tools.dev.show_hooks:main',
            'oep2 = edx_repo_tools.oep2:_cli',
            'no_yaml = edx_repo_tools.ospr.no_yaml:no_yaml',
            'tag_release = edx_repo_tools.release.tag_release:main',
            'drip = edx_repo_tools.drip_survey:cli',
            'get_org_repo_urls = edx_repo_tools.dev.get_org_repo_urls:main',
            'modernize_travis = edx_repo_tools.codemods.django3.travis_modernizer:main',
            'modernize_tox = edx_repo_tools.codemods.django3.tox_modernizer:main',
            'modernize_openedx_yaml = edx_repo_tools.modernize_openedx_yaml:main',
            'modernize_github_actions = edx_repo_tools.codemods.django3.github_actions_modernizer:main',
            'modernize_github_actions_django = edx_repo_tools.codemods.django3.github_actions_modernizer_django:main',
            'modernize_setup_file = edx_repo_tools.codemods.django3.setup_file_modernizer:main',
            'modernize_node_workflow = edx_repo_tools.codemods.node16.gha_ci_modernizer:main',
            'add_common_constraint = edx_repo_tools.add_common_constraint:main',
            'remove_python2_unicode_compatible = edx_repo_tools.codemods.django3.remove_python2_unicode_compatible:main',
            'replace_unicode_with_str = edx_repo_tools.codemods.django3.replace_unicode_with_str:main',
            'replace_static = edx_repo_tools.codemods.django3.replace_static:main',
            'conventional_commits = edx_repo_tools.conventional_commits.commitstats:main',
            'replace_render_to_response = edx_repo_tools.codemods.django3.replace_render_to_response:main',
            'add_django32_settings = edx_repo_tools.codemods.django3.add_new_django32_settings:main',
        ],
    },
    package_data={
        'edx_repo_tools.oep2.report': ['oep2-report.ini'],
    }
)
