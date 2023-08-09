Find Dependencies
#################

This tool spiders through requirements/base.txt and package-lock.json files to find dependencies of a repo.  In particular, we wanted it to find the source repos for dependencies, to see which might need to be moved to the openedx GitHub organization.

Installation
************

#. Create a Python 3.8 virtualenv.

#. Install repo-tools (https://github.com/openedx/repo-tools) into your virtualenv, including the "find_dependencies" extra requirements::

   $ python -m pip install '/path/to/repo-tools[find_dependencies]'


Running
*******

Run it with a list of local repo directories.  It will traverse into each directory you named, spidering dependencies.  It writes work files into /tmp/unpack_reqs:

- A subdirectory for each repo, named for the repo.  These have copies of the base.txt and package-lock.json files that were examined.

- repo_urls.txt is a list of the best-guess repo URL for every dependency.

- second_party_urls.txt is the subset of repo_urls.txt that come from organizations close enough to the Open edX project, that the repos might need to be moved into the openedx organization.

I run it in a tree of all repos, with these commands to examine all the repos branched for Olive::

    $ export OLIVE_DIRS=$(gittreeif origin/open-release/olive.master -q pwd)
    $ find_dependencies $OLIVE_DIRS

(gittreeif is from https://github.com/openedx/repo-tools/gittools.sh)

It reports on its progress and failures, like this:

```
% find_dependencies $OLIVE_DIRS
Creating new work directory: /tmp/unpack_reqs
-- /src/ghorg/openedx/DoneXBlock ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 12/12
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 12/12
-- /src/ghorg/openedx/blockstore ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 47/47
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 3/3
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 50/50
-- /src/ghorg/openedx/configuration ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 32/32
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 7/7
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 38/38
-- /src/ghorg/openedx/course-discovery ----------
Checking JavaScript dependencies
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 391/391
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 317/317
391 deps, 317 urls, 282 real urls
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
-- /src/ghorg/openedx/credentials ----------
Checking JavaScript dependencies
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1000/1000
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 647/647
1000 deps, 647 urls, 589 real urls
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 85/85
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 8/8
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 93/93
-- /src/ghorg/openedx/cs_comments_service ----------
-- /src/ghorg/openedx/devstack ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 25/25
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 2/2
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 27/27
-- /src/ghorg/openedx/docs.openedx.org ----------
Checking Python dependencies
Creating venv
Downloading packages
No repo URL in files/sphinx_book_theme-0.3.3-py3-none-any.whl
No repo URL in files/pydata_sphinx_theme-0.8.1-py3-none-any.whl
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 34/34
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1/1
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 28/28
-- /src/ghorg/openedx/ecommerce ----------
Checking JavaScript dependencies
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 713/713
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 612/612
713 deps, 612 urls, 519 real urls
Checking Python dependencies
Creating venv
Downloading packages
Repo URL is UNKNOWN in files/python_toolbox-1.0.11-py2.py3-none-any.whl
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 151/151
Repo URL is UNKNOWN in files/logger-1.4.tar.gz
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Repo URL is UNKNOWN in files/cybersource-rest-client-python-0.0.21.tar.gz
Repo URL is UNKNOWN in files/pycountry-17.1.8.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 24/24
ConnectTimeoutError(<urllib3.connection.HTTPConnection object at 0x107ea7be0>, 'Connection to naked-py.com timed out. (connect timeout=60)'))
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 169/169
-- /src/ghorg/openedx/ecommerce-worker ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 25/25
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 2/2
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 27/27
-- /src/ghorg/openedx/edx-analytics-configuration ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 19/19
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1/1
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 19/19
-- /src/ghorg/openedx/edx-analytics-dashboard ----------
Checking JavaScript dependencies
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1611/1611
Couldn't fetch https://github.com:mafintosh/tar-fs: Failed to parse: https://github.com:mafintosh/tar-fs
Couldn't fetch https://github.com:mafintosh/tar-stream: Failed to parse: https://github.com:mafintosh/tar-stream
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1173/1173
1611 deps, 1173 urls, 931 real urls
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 62/62
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 8/8
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 68/68
-- /src/ghorg/openedx/edx-analytics-data-api ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 68/68
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 9/9
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 76/76
-- /src/ghorg/openedx/edx-analytics-pipeline ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
-- /src/ghorg/openedx/edx-app-android ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 9/9
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 10/10
-- /src/ghorg/openedx/edx-app-ios ----------
-- /src/ghorg/openedx/edx-developer-docs ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:-- 0/0
-- /src/ghorg/openedx/edx-documentation ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 29/29
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1/1
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 25/25
-- /src/ghorg/openedx/edx-notes-api ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 52/52
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 5/5
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 56/56
-- /src/ghorg/openedx/edx-platform ----------
Checking JavaScript dependencies
edx-proctoring-proctortrack@1.1.1: https://registry.npmjs.org/edx-proctoring-proctortrack/1.1.1 -> 404
edx@0.1.0: https://registry.npmjs.org/edx/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 2045/2045
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1393/1393
2045 deps, 1393 urls, 1127 real urls
Checking Python dependencies
Creating venv
Downloading packages
Repo URL is UNKNOWN in files/pynliner-0.8.0-py2.py3-none-any.whl
Repo URL is UNKNOWN in files/openedx_django_wiki-1.1.4-py3-none-any.whl
No repo URL in files/click_didyoumean-0.3.0-py3-none-any.whl
Repo URL is UNKNOWN in files/xblock_google_drive-0.3.0-py2.py3-none-any.whl
Repo URL is UNKNOWN in files/xblock_drag_and_drop_v2-3.0.0-py3-none-any.whl
Repo URL is UNKNOWN in files/edx_user_state_client-1.3.2-py3-none-any.whl
Repo URL is UNKNOWN in files/done_xblock-2.0.4-py3-none-any.whl
No repo URL in files/staff_graded_xblock-2.0.1-py3-none-any.whl
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 250/250
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 24/24
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 270/270
-- /src/ghorg/openedx/enterprise-access ----------
Checking Python dependencies
Creating venv
Downloading packages
No repo URL in files/click_didyoumean-0.3.0-py3-none-any.whl
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 88/88
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 8/8
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 94/94
-- /src/ghorg/openedx/enterprise-catalog ----------
Checking Python dependencies
Creating venv
Downloading packages
No repo URL in files/click_didyoumean-0.3.0-py3-none-any.whl
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 86/86
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 7/7
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 91/91
-- /src/ghorg/openedx/frontend-app-account ----------
Checking JavaScript dependencies
@edx/frontend-app-account@1.0.0-semantically-released: https://registry.npmjs.org/@edx/frontend-app-account/1.0.0-semantically-released -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1430/1430
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 911/911
1430 deps, 911 urls, 824 real urls
-- /src/ghorg/openedx/frontend-app-authn ----------
Checking JavaScript dependencies
@edx/frontend-app-authn@0.1.0: https://registry.npmjs.org/@edx/frontend-app-authn/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1646/1646
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1044/1044
1646 deps, 1044 urls, 934 real urls
-- /src/ghorg/openedx/frontend-app-communications ----------
Checking JavaScript dependencies
@edx/frontend-app-communications@0.1.0: https://registry.npmjs.org/@edx/frontend-app-communications/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1555/1555
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 967/967
1555 deps, 967 urls, 868 real urls
-- /src/ghorg/openedx/frontend-app-course-authoring ----------
Checking JavaScript dependencies
@edx/frontend-app-course-authoring@0.1.0: https://registry.npmjs.org/@edx/frontend-app-course-authoring/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1629/1629
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1072/1072
1629 deps, 1072 urls, 968 real urls
-- /src/ghorg/openedx/frontend-app-discussions ----------
Checking JavaScript dependencies
@edx/frontend-app-discussions@0.1.0: https://registry.npmjs.org/@edx/frontend-app-discussions/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1597/1597
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1010/1010
1597 deps, 1010 urls, 912 real urls
-- /src/ghorg/openedx/frontend-app-ecommerce ----------
Checking JavaScript dependencies
@edx/frontend-app-ecommerce@0.1.0: https://registry.npmjs.org/@edx/frontend-app-ecommerce/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1695/1695
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1122/1122
1695 deps, 1122 urls, 1006 real urls
-- /src/ghorg/openedx/frontend-app-gradebook ----------
Checking JavaScript dependencies
@edx/frontend-app-gradebook@1.6.0: https://registry.npmjs.org/@edx/frontend-app-gradebook/1.6.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1980/1980
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1273/1273
1980 deps, 1273 urls, 1118 real urls
-- /src/ghorg/openedx/frontend-app-learner-dashboard ----------
Checking JavaScript dependencies
@edx/frontend-component-footer@1.0.0-semantically-released: https://registry.npmjs.org/@edx/frontend-component-footer/1.0.0-semantically-released -> 404
@edx/frontend-app-learner-dashboard@0.0.1: https://registry.npmjs.org/@edx/frontend-app-learner-dashboard/0.0.1 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1917/1917
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1279/1279
1917 deps, 1279 urls, 1148 real urls
-- /src/ghorg/openedx/frontend-app-learner-record ----------
Checking JavaScript dependencies
@edx/frontend-app-learner-record@0.1.0: https://registry.npmjs.org/@edx/frontend-app-learner-record/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1527/1527
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 952/952
1527 deps, 952 urls, 866 real urls
-- /src/ghorg/openedx/frontend-app-learning ----------
Checking JavaScript dependencies
@edx/frontend-app-learning@1.0.0-semantically-released: https://registry.npmjs.org/@edx/frontend-app-learning/1.0.0-semantically-released -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1712/1712
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1073/1073
1712 deps, 1073 urls, 861 real urls
-- /src/ghorg/openedx/frontend-app-ora-grading ----------
Checking JavaScript dependencies
@edx/frontend-app-ora-grading@0.0.1: https://registry.npmjs.org/@edx/frontend-app-ora-grading/0.0.1 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1902/1902
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1234/1234
1902 deps, 1234 urls, 1115 real urls
-- /src/ghorg/openedx/frontend-app-payment ----------
Checking JavaScript dependencies
@edx/frontend-app-payment@0.1.0: https://registry.npmjs.org/@edx/frontend-app-payment/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1518/1518
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 989/989
1518 deps, 989 urls, 904 real urls
-- /src/ghorg/openedx/frontend-app-profile ----------
Checking JavaScript dependencies
@edx/frontend-app-profile@1.0.0-semantically-released: https://registry.npmjs.org/@edx/frontend-app-profile/1.0.0-semantically-released -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1575/1575
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1013/1013
1575 deps, 1013 urls, 923 real urls
-- /src/ghorg/openedx/frontend-app-publisher ----------
Checking JavaScript dependencies
edx-frontend-app-publisher@0.1.0: https://registry.npmjs.org/edx-frontend-app-publisher/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1616/1616
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1071/1071
1616 deps, 1071 urls, 952 real urls
-- /src/ghorg/openedx/frontend-app-support-tools ----------
Checking JavaScript dependencies
@edx/frontend-app-support@0.1.0: https://registry.npmjs.org/@edx/frontend-app-support/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1683/1683
Couldn't fetch github.com:samccone/chrome-trace-event: No connection adapters were found for 'github.com:samccone/chrome-trace-event'
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1150/1150
1683 deps, 1150 urls, 994 real urls
-- /src/ghorg/openedx/frontend-template-application ----------
Checking JavaScript dependencies
@edx/frontend-template-application@0.1.0: https://registry.npmjs.org/@edx/frontend-template-application/0.1.0 -> 404
Getting npm URLs     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1378/1378
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 851/851
1378 deps, 851 urls, 782 real urls
-- /src/ghorg/openedx/license-manager ----------
Checking Python dependencies
Creating venv
Downloading packages
No repo URL in files/click_didyoumean-0.3.0-py3-none-any.whl
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 89/89
Repo URL is UNKNOWN in files/pyjwkest-1.4.2.tar.gz
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 9/9
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 96/96
-- /src/ghorg/openedx/openedx-demo-course ----------
-- /src/ghorg/openedx/openedx-test-course ----------
-- /src/ghorg/openedx/repo-tools ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 82/82
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 6/6
Couldn't fetch http://trevp.net/tlslite/: ('Connection aborted.', ConnectionResetError(54, 'Connection reset by peer'))
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 87/87
-- /src/ghorg/openedx/testeng-ci ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 20/20
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 1/1
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 21/21
-- /src/ghorg/openedx/tubular ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 62/62
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 13/13
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 75/75
-- /src/ghorg/openedx/xqueue ----------
Checking Python dependencies
Creating venv
Downloading packages
Examining wheels     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 34/34
Examining tar.gz     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 2/2
Getting real URLs    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 36/36
== DONE ==============
Second-party:
https://github.com/edx/brand-edx.org
https://github.com/edx/braze-client
https://github.com/edx/edx-name-affirmation
https://github.com/edx/frontend-component-footer-edx
https://github.com/edx/getsmarter-api-clients
https://github.com/edx/learner-pathway-progress
https://github.com/edx/new-relic-source-map-webpack-plugin
https://github.com/edx/outcome-surveys
https://github.com/edx/ux-pattern-library
https://github.com/mitodl/edx-sga
https://github.com/open-craft/xblock-poll
```
