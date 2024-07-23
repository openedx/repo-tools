Repo Checks
###########

This is a tool & a lightweight framework for automating administrative tasks through GitHub's API.

These checks are generally written by Axim engineers to help us to help us establish some consistency across the plethora of repositories under the `openedx GitHub organization <https://github.com/openedx>`_, although they theoretically could be applied to any GitHub organization.

Concepts
********

A "repo check" is something that we want to ensure about a given repository. Each repo check defines the following:

* ``is_relevant``: Does this check even make sense on the given repo?
* ``check``: Does the repo satisfy the check's conditions?
* ``dry_run``: Based on the results of ``check``, display any problems.
* ``fix``: Based on the results of ``check``, actively fix the problems.

The ``repo_checks`` command line tool lets you execute these checks, either as dry runs or as active fixes.

Usage
*****

You will need a GH personal access token (classic, not "Fine-grained tokens") with the following scopes:

*  admin:org
*  repo
*  user
*  workflow

First, set up repo-tools as described in `the root README <../../README.rst>`_.
There are a few ways to do this; one way is::

  export GITHUB_TOKEN="$(pass github-token)"  # assumes you have passwordstore.org

  python3 -m venv venv
  . venv/bin/activate
  pip install -e .[repo_checks]

Then, dry-run the script (one of these)::

  repo_checks                                      # all repos & checks
  repo_checks -r edx-platform -r frontend-platform # limit repos
  repo_checks -c EnsureLabels -c RequiredCLACheck  # limit checks
  repo_checks -c EnsureLabels -r edx-platform      # single repo & check

Finally, when you're ready, you can actually apply the fixes to GitHub::

  repo_checks --no-dry-run <... same args you used above ...>

Note this will open pull requests in the relevant repos. Some repos intentionally don't have certain workflows (for example, ``docs.openedx.org`` does not use ``commitlint``), so please tag maintainers on the pull requests so they can decide whether or not to use the added or changed workflows.

When running over all repos in an organization, the script runs on the newest repos first as those are the most likely
to be out of compliance.

A note about rate-limiting, if your run is halted due to rate-limiting, note the last repo that the check was running on
in the output and restart the job from there once your rate limit has been reset::

    repo_checks ...                                      # original run
    ...                                                  # rate limiting or other error halts the run
    repo_checks ... --start-at "<last_repo_in_output>"   # Re run starting from where we halted.

Contributing
************

* Make changes on your branch.

* Consider adding `to the test suite <../../tests/test_repo_checks.py>`_ even though it is currently sparse.

* CI will run tests for you, but not linting, so ensure your changes don't break repo_checks' pylint: ``pylint edx_repo_tools/repo_checks``.

* Dry-run the script and save the output (non-Axim engineers: you should be able to do this with a read-only GH access token).

* Open a PR. Paste your dry-run output into the PR (https://gist.github.com is helpful for long outputs).

* Ping ``#ask-axim`` for review.

* Once approved, apply and merge (non-Axim engineers: ask your Axim reviewer to do this part for you).

  * Run the script with ``--no-dry-run``, saving the output. Paste the output into the PR for future reference.

  * If something went wrong, push fixes to the PR and try again. Repeat as necessary.

  * Once successfully applied, merge the PR.
