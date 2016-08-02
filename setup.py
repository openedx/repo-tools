from setuptools import setup

setup(
    name='edx-repo-tools',
    version='0.1',
    packages=['oep2'],
    install_requires=[
        'click',
    ],
    entry_points={
        'console_scripts': [
            'explode-repos-yaml=oep2.explode_repos_yaml:cli',
        ]
    },
)
