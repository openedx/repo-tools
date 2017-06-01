# gitgraft.py

## Overview
Python script to assist migrating commits between otherwise disconnected github repositories. Specifically designed for repos created by breaking out subtrees via commands like ```git filter-branch```.

The script works from a simple configuration file and should allow for repeated pulls of changes without duplicating commits. It will create a new branch on the target repo and generate a series of commits on that branch that match commits made to relevant files on the original branch.

## How does it work?
gitgraft looks takes a list of "tracked paths" (directories of files) that are configured to map two locations in different repos together. It then looks back a configurable number of days to find commits that are in common between them by comparing commit metadata such as committer, author, timestamps, and message. If ```git filter-branch``` was used to separate out the repo while keeping history those things should stay the same.

It will then:
* Create a new local branch in the branched repository
* Look at any commits made to tracked paths in the original repo that do not exist in the branched repo for any tracked files changed as part of the commit
* If any files were found a new commit is crafted for the branched repo with a commit message that looks like this:
 
 ```
Graft d1f2561
                
Grafting commit >>d1f256124cf4a304afed64e02be528a55126f7c2<<
Original commit by Jeremy Bowman on 2017-03-27T15:51:37 with this message:
----------------------------------------------------------------
PLAT-1198 Reduce risk of losing navigation events
```

If the new branch and commits look good and get integrated to the branched repo you can re-run gitgraft to search for additional changes at any time. Subsequent runs will look in the commit messages for the SHA1 located between the >><< in commit messages and use that to mark those commits as "moved", effectively ignoring them and allowing only the on grafted changes to be considered.

## Setup
Make sure you've got all of the requirements:
```
pip install -r requirements.txt
```

Create a configuration file, which should look something like this:

```
# "original" means the repo with the commits you would like to take
# "branched" means the repo that you will be copying those commits into

[repositories]
# Since we can't rely on git to reliably give us repo names, specify what we should call
# the original repo here.
original_repository_name = edx-platform

# Local path to the top level repo directories. Must not be dirty!
original_repository = /Users/brianmesick/Dev/edx-platform/edx-platform-head/edx-platform
branched_repository = /Users/brianmesick/Dev/platform-core/platform-core

# Branches to checkout to diff against 
original_branch = master
branched_branch = bmedx/dogstats-and-markup

[tracked_paths]
# Maps paths which are relevant to this grafting, left is the original repo, right is the branched repo. 
tracked =
    openedx/core/lib/api/plugins.py > platform_core/lib/api/plugins.py
    common/lib/dogstats/dogstats_wrapper > platform_core/lib/dogstats_wrapper
    openedx/core/lib/cache_utils.py > platform_core/lib/cache_utils.py
    openedx/core/lib/course_tabs.py > platform_core/lib/course_tabs.py
    openedx/core/lib/tempdir.py > platform_core/lib/tempdir.py

# Any paths under the tracked paths that you would like to *not* be considered. Useful 
# for large or frequently updated paths that are irrelevant and slow things down. These 
# are optional.
original_ignored =

branched_ignored =
    common/lib/dogstats/dogstats_wrapper/huge/directory/with/many/changes/
```

Looking at all of the commits of large repositories can be slow, and can cause some false file matches. Having more, and specific, ```tracked``` and ```ignored``` options can save a lot of time and confusion.

## Usage

```
Usage: gitgraft.py [OPTIONS] CONF

  Creates a "best-guess" copy of commits across two unrelated (no consistent
  history) github repositories

Options:
  --dry_run  Do a test run without creating a branch or commits
  --verbose  Verbose output
  --help     Show this message and exit.
```

The output will show commits as they happen, including the impacted files. When run with ```--verbose``` extensive debugging information will be printed, which can assist with narrowing down issues with tracked or ignored paths.
