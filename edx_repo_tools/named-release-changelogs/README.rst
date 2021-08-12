CHANGELOGS FOR NAMED RELEASES
############

This directory has code to collect and sort commits which are the diff between a named edx-relase and the present.

#. Create a Python 3.8 virtualenv.

#. Install pygithub (https://github.com/PyGithub/PyGithub) into your virtualenv::

   $ pip install pygithub

#. Create html files of recent commit deltas with the following cli:

   $ python python create_changelog.py

#. required arguments. Note that an api token can be configured to give access to private and other repos.

 $ -a GitHub API token (acquired here: https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token)

#. Optional arguments (default is ):

   $ -i <branch>
   $ -o <organization name ex: edx>
   $ -r <repo to scrape commits from>

#. Now you will be able to open a  html file created in the folder  titled {repo_name} changelog.html with your favorite browser

Created for Hackathon XXVI: For the love of Docs