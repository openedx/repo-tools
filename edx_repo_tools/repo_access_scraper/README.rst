Repo Access Scraper
###################

This tool records who is granted write (or admin) access to a repo.  It writes a .md file with teams and people who have write access to each repo. It also captures screenshots of the GitHub access settings pages for each involved repo and team.

#. Install repo-tools (https://github.com/openedx/repo-tools) dependencies, including the "repo_access_scraper" extra::

   $ cd /path/to/repo-tools
   $ uv sync --extra repo_access_scraper

#. You may need to install the playwright headless browsers::

   $ uv run playwright install

#. Generate a GitHub personal access token, and define it in the environment::

   $ export GITHUB_TOKEN=ghp_w3IJJ8YvqW4MJ....DGDpP8iOhko472RmIlP

#. Run the tool, naming the repos you want to audit:

   .. code::

       $ uv run repo_access_scraper \
           openedx/course-discovery \
           openedx/frontend-app-publisher \
           openedx/ecommerce \
           openedx/ecommerce-worker \
           openedx/frontend-app-payment \
           openedx/frontend-app-ecommerce

#. A report.md file will be created.

#. An images.zip file will be created, with screenshots of the GitHub access settings and team members pages.
