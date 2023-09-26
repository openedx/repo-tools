Audit GitHub Users
##################

This script will compare the list of users in a github org against a list of
users in a CSV and tell you which github users are not listed in the CSV.

CSV Location and Format
***********************

The CSV is expected to be in a GitHub repo and it should contain a column name
"GitHub Username" that contains a GitHub username.

Usage
*****

You will need a GH pesonal access token with the following scopes:

* read:org
* repo

First, set up repo-tools as described in `the root README <../../README.rst>`_.
There are a few ways to do this; one way is::

  export GITHUB_TOKEN="$(pass github-token)"  # assumes you have passwordstore.org

  python3 -m venv venv
  . venv/bin/activate
  pip install -e .[audit_gh_users]

Then, run the script::

  audit_users

Contributing
************

* Make changes on your branch.

* CI will run tests for you, but not linting, so ensure your changes don't break pylint: ``pylint edx_repo_tools/audit_users``.

* Ping `#ask-axim`__ on Slack for review.

__ https://openedx.slack.com/archives/C0497NQCLBT

* Once approved, apply and merge (non-Axim engineers: ask your Axim reviewer to do this part for you).
