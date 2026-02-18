###################
Open edX Repo Tools
###################

This repo contains a number of tools Open edX engineers use for working with
GitHub repositories.

The set of tools has grown over the years. Some are old and in current use,
some have fallen out of use, some are quite new.

Setting up GitHub authentication
================================

Most of these make GitHub API calls, and so will need GitHub credentials in
order to not be severely rate-limited.  Edit (or create) `~/.netrc` so that it
has an entry like this::

    machine api.github.com
      login your_user_name
      password ghp_XyzzyfGXFooBar8nBqQuuxY9brgXYz4Xyzzy

Change the login to your GitHub user name.  The password is a Personal Access
Token you get from https://github.com/settings/tokens.  Visit that page, click
"Generate new token." It will prompt you for your password, then you'll see a
scary list of scopes. Check the "repo" option and click "Generate token." Copy
the token that appears. Paste it into your ~/.netrc in the "password" entry.


Working in the repo
===================

This project uses `uv <https://docs.astral.sh/uv/>`_ for dependency management.
See details at `UV_QUICK_REFERENCE <UV_QUICK_REFERENCE.md>`_

To work on these tools:

1. Install uv if you haven't already::

    curl -LsSf https://astral.sh/uv/install.sh | sh

2. Install dependencies::

    make sync

   Or directly with uv::

    uv sync --all-extras --dev

3. Run tests::

    make test

4. Older tools were Python files run from the root of the repo.  Now we are
   being more disciplined and putting code into importable modules with entry
   points in pyproject.toml.

5. Simple tools can go into an existing subdirectory of edx_repo_tools.  Follow
   the structure of existing tools you find here.  More complex tools, or ones
   that need unusual third-party requirements, should go into a new
   subdirectory of edx_repo_tools.

6. Add a new entry point in pyproject.toml under ``[project.scripts]`` for your command:

   .. code::

        [project.scripts]
        new_tool = "edx_repo_tools.new_tool_dir.new_tool:main"

7. If your tool needs additional third-party requirements, add them to the
   ``[project.optional-dependencies]`` section in pyproject.toml with a name
   matching your tool. For example::

        [project.optional-dependencies]
        new_tool = [
            "some-package",
            "another-package",
        ]

   Users can then install your tool with::

        uv sync --extra new_tool

Updating Dependencies
=====================

To update all dependencies to their latest compatible versions::

    make upgrade

This command will:
1. Sync common constraints from edx-lint repository
2. Update the ``uv.lock`` file with the latest versions

Or you can run the steps manually::

    make sync-constraints  # Sync organization-wide constraints
    uv lock --upgrade      # Update lock file

Managing Constraints
====================

This repository uses organization-wide constraints from the edx-lint repository
to ensure consistency across all Open edX projects. These constraints (like
``Django<6.0``) are automatically downloaded and applied.

To manually sync constraints::

    make sync-constraints

Or directly::

    uv run python sync_constraints.py

**Important**: Do not manually edit the ``[tool.uv.constraint-dependencies]``
section in pyproject.toml. Use the ``sync_constraints.py`` script to update
constraints, which preserves local constraints while updating common ones.

Active Tools
============

check_requirements_failures
----------------------------

Check repositories in a GitHub organization for the status of their automated
Python requirements upgrade workflows. This tool tracks the failure rate of
the last 10 workflow runs, when requirements PRs were last merged, and release
information. This helps identify repositories where the upgrade workflow may be
failing or stalled.

See the `check_requirements_failures README <edx_repo_tools/check_requirements_failures/README.rst>`_ in its subfolder.

repo_checks
-----------

See the `repo_checks README <edx_repo_tools/repo_checks/README.rst>`_ in its subfolder.

Older Tools
===========

There are many programs in this repo in various stages of disrepair.  A few
of them are described in this repo's `older README.md`_ file.  Others are not
described at all, but may be useful, or have useful tidbits in the code.

.. _older README.md: https://github.com/openedx/repo-tools/blob/7aa8bda466d1925c56d4ad6e3b2bdd87b1f83148/README.md


Feedback
========

Please send any feedback to oscm@edx.org.
