from setuptools import setup

setup(
    name='edx-repo-tools',
    version='0.1',
    packages=[
        'edx_repo_tools',
        'edx_repo_tools.oep2',
        'edx_repo_tools.oep2.checks',
        'edx_repo_tools.oep2.report',
    ],
    install_requires=[
        'click',
        'appdirs',
        'github3.py',
        'pytest',
        'pytest-xdist',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'oep2=edx_repo_tools.oep2:cli',
        ],
    },
    package_data={
        'edx_repo_tools.oep2.report': ['oep2-report.ini'],
    }
)
