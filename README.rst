###################
Open EdX Repo Tools
###################

This repo contains a number of tools Open edX uses for working with GitHub
repositories.

* oep2: Report on `OEP-2`_ compliance across repositories.
* tag_release: Tags multiple repos as part of the release process.

.. _OEP-2: http://open-edx-proposals.readthedocs.io/en/latest/oeps/oep-0002.html

Setting up GitHub authentication
================================

Most of these make GitHub API calls, and so will need GitHub credentials in
order to not be severely rate-limited.  Edit (or create) `~/.netrc` so that it
has an entry like this::

    machine api.github.com
      login your_user_name
      password ddf9079e12042ac022c101c61c0235965851e209

Change the login to your GitHub user name.  You'll get the password value from
https://github.com/settings/applications.  Visit that page, click on Developer
Settings and in the section called "Personal access tokens," click "Generate new token."  
It will prompt you for your password, then you'll see a scary list of scopes. Check 
the "repo" option and click "Generate token." Copy the password that
appears. Paste it into your ~/.netrc.


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


Older Tools
===========

There are many programs in this repo in various stages of disrepair.  A few
of them are described in this repo's `older README.md`_ file.  Others are not
described at all, but may be useful, or have useful tidbits in the code.

.. _older README.md: https://github.com/edx/repo-tools/blob/7aa8bda466d1925c56d4ad6e3b2bdd87b1f83148/README.md


Feedback
========

Please send any feedback to oscm@edx.org.
