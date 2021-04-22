import setuptools
from setuptools import setup


with open('README.rst') as readme:
    long_description = readme.read()

setup(
    name='edx-repo-tools',
    version='0.3.1',
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
            'sync_labels = edx_repo_tools.ospr.sync_labels:sync_labels',
            'no_yaml = edx_repo_tools.ospr.no_yaml:no_yaml',
            'tag_release = edx_repo_tools.release.tag_release:main',
            'drip = edx_repo_tools.drip_survey:cli',
            'get_org_repo_urls = edx_repo_tools.dev.get_org_repo_urls:main',
            'modernize_travis = edx_repo_tools.codemods.django3.travis_modernizer:main',
            'modernize_tox = edx_repo_tools.codemods.django3.tox_modernizer:main',
            'modernize_openedx_yaml = edx_repo_tools.modernize_openedx_yaml:main',
            'modernize_github_actions = edx_repo_tools.codemods.django3.github_actions_modernizer:main',
            'add_common_constraint = edx_repo_tools.add_common_constraint:main',
        ],
    },
    package_data={
        'edx_repo_tools.oep2.report': ['oep2-report.ini'],
    }
)
