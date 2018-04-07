from setuptools import setup

setup(
    name='edx-repo-tools',
    version='0.1',
    packages=[
        'edx_repo_tools',
        'edx_repo_tools.oep2',
        'edx_repo_tools.oep2.checks',
        'edx_repo_tools.oep2.report',
        'edx_repo_tools.ospr',
        'edx_repo_tools.release',
        'edx_repo_tools.drip_survey',
    ],
    install_requires=[
        'appdirs',
        'click',
        'lazy',
        'github3.py',
        'pytest',
        'pytest-xdist',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'oep2 = edx_repo_tools.oep2:_cli',
            'sync_labels = edx_repo_tools.ospr.sync_labels:sync_labels',
            'no_yaml = edx_repo_tools.ospr.no_yaml:no_yaml',
            'tag_release = edx_repo_tools.release.tag_release:main',
            'drip = edx_repo_tools.drip_survey:cli',
        ],
    },
    package_data={
        'edx_repo_tools.oep2.report': ['oep2-report.ini'],
    }
)
