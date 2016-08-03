from setuptools import setup

setup(
    name='edx-repo-tools',
    version='0.1',
    packages=[
        'edx_repo_tools',
        'edx_repo_tools.oep2',
    ],
    install_requires=[
        'click',
    ],
    entry_points={
        'console_scripts': [
            'oep2=edx_repo_tools.oep2:cli',
        ]
    },
)
