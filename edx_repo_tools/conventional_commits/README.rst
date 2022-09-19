Commit Stats
############

This directory has code to collect and report statistics about conventional commit compliance.  After cloning a number of repos, you use these tools to collect data into a commits.db database, then query and graph the data.

#. Create a Python 3.8 virtualenv, and a new directory into which to clone the repos.

#. Install repo-tools (https://github.com/openedx/repo-tools) into your virtualenv, including the "conventional_commits" extra requirements::

   $ python -m pip install '/path/to/repo-tools[conventional_commits]'

#. Change to your work directory.

#. Create a sub-directory called "edx", and cd into it.

#. Clone the edx org.  This will need more than 8Gb of disk space::

   $ clone_org --prune --forks edx

#. Update all the repos.  The "gittree" shell alias is in the gittools.sh file in repo-tools::

   $ gittree "git fetch --all; git checkout \$(git remote show origin | awk '/HEAD branch/ {print \$NF}'); git pull"

#. cd ..

#. Delete the existing commits.db file, if any.

#. Collect commit stats. Consider every edx repo, ignore the ones ending in
   "-private", and include all the ones that have an openedx.yaml file::

   $ conventional_commits collect --ignore='*-private' --require=openedx.yaml edx/*

#. Now commits.db is a SQLite database with a table called "commits".  You can query this directly with SQLite-compatible tools if you like.

#. Draw a chart::

   $ conventional_commits plot
