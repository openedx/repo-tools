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

To work on these tools:

1. Use a virtualenv.

2. Install dependencies::

    make dev-install

3. Run tests::

    make test

4. Older tools were Python files run from the root of the repo.  Now we are
   being more disciplined and putting code into importable modules with entry
   points in setup.py.

5. Simple tools can go into an existing subdirectory of edx_repo_tools.  Follow
   the structure of existing tools you find here.  More complex tools, or ones
   that need unusual third-party requirements, should go into a new
   subdirectory of edx_repo_tools.

6. Add a new `entry_point` in setup.py for your command:

   .. code::

        entry_points={
            'console_scripts': [
                ...
                'new_tool = edx_repo_tools.new_tool_dir.new_tool:main',
                ...

7. If your tool is in its own directory, you can create an `extra.in` file
   there with third-party requirements intended just for your tool.  This will
   automatically create an installable "extra" for your requirements.

Active Tools
============

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
