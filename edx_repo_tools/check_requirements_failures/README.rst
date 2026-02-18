Check Requirements Failures
============================

This tool checks repositories in a GitHub organization (openedx by default)for
the status of their automated Python requirements upgrade workflows.

Purpose
-------

Many repositories use automated workflows to upgrade Python dependencies on a
regular schedule. This tool helps identify repositories where these workflows
may be failing or stalled by checking:

1. The failure rate of the last 10 workflow runs
2. When the last "chore: Upgrade Python requirements" PR was merged
3. The date and version of the last release

This information helps maintainers identify repositories that may need attention.

Prerequisites
-------------

This tool requires the GitHub CLI (``gh``) to be installed and authenticated:

- Install from: https://cli.github.com/
- Authenticate with: ``gh auth login``

Installation
------------

This tool is installed as part of the ``edx-repo-tools`` package::

    pip install edx-repo-tools

Usage
-----

Basic usage to get the status of all repositories in an organization::

    check_requirements_failures --org openedx

Check specific repositories::

    check_requirements_failures --org openedx --repo repo1 --repo repo2

Output results to CSV file::

    check_requirements_failures --org openedx --output-path ./reports

Include archived repositories::

    check_requirements_failures --org openedx --include-archived

Check mode (return non-0 if any repos haven't merged requirements PR in X+ weeks, see more below)::

    check_requirements_failures --org openedx --output-path ./reports --check --weeks 4

Options
-------

``--org TEXT``
    **Required.** The GitHub organization name to check.

``--repo TEXT``
    Specific repository name(s) to check. Can be specified multiple times.
    If not provided, checks all repositories in the organization.

``--include-archived``
    Include archived repositories in the check. By default, archived
    repositories are skipped.

``--output-path PATH``
    Directory path to write CSV output file. If provided, results will be
    written to a timestamped CSV file in the specified directory
    (e.g., ``requirements_check_openedx_20240115_143022.csv``).
    If not provided, outputs to stdout in human-readable format.
    The directory will be created if it doesn't exist.

``--check``
    Check mode: Identify repositories that have not merged a requirements PR
    in 4 or more weeks. When enabled and --output-path is passed in, it also
    creates an additional CSV file with "_FAILED" suffix containing only the
    failed repositories. The script will exit with code -1 if any failures
    are found, or 0 if all repositories are up to date. Useful for
    CI/CD pipelines.

``--weeks``
    The threshold of weeks that check mode will fail on. If set to 4, for
    instance, --check will fail if any eligible repositories have not merged
    a requirements PR in 4 weeks.


Output
------

Human-readable format
~~~~~~~~~~~~~~~~~~~~~

By default, the tool outputs results in a human-readable format::

    Repository: openedx/repo-name
    --------------------------------------------------------------------------------
      Workflow Runs (last 10):
        Failed:  2
        Success: 8
      Last Requirements PR:
        Date: 2024-01-15
        PR #: 123
        URL:  https://github.com/openedx/repo-name/pull/123
      Last Release:
        Date:     2024-01-20
        Version:  v3.0.3
        Name:     Release v3.0.3
        isLatest: True

CSV format
~~~~~~~~~~

When using ``--output-path``, a CSV file is created with these columns:

- Repository
- Total Runs (last 10)
- Failed Runs
- Success Runs
- Last PR Date
- PR Number
- PR URL
- Last Release Date
- Release Version
- Release Name
- Release Is Latest

Example Analysis
----------------

This tool can help answer questions like:

- Which repositories have high failure rates in their requirements upgrade workflows?
- Which repositories haven't had a requirements PR merged recently?
- Are there repositories where requirements PRs are being created but not merged?
- Is there a correlation between requirements updates and releases?
- Which repositories might have broken requirements upgrade workflows?

Example workflow::

    # Create a reports directory and generate CSV
    mkdir -p reports
    check_requirements_failures --org openedx --output-path ./reports

    # The tool will create a file like:
    # reports/requirements_check_openedx_20240115_143022.csv

    # Open in a spreadsheet tool for analysis
    # Sort by "Last PR Date" to find repositories with stale requirements
    # Compare PR dates with release dates to identify potential issues

CI/CD Integration
-----------------

Use check mode in CI/CD pipelines to automatically fail if repositories
haven't updated their requirements in 4+ weeks::

    # In your CI script or GitHub Actions workflow
    check_requirements_failures --org openedx --output-path ./reports --check

    # This will:
    # 1. Create requirements_check_openedx_TIMESTAMP.csv with all repos
    # 2. Create requirements_check_openedx_TIMESTAMP_FAILED.csv with failed repos (if any)
    # 3. Exit with code -1 if failures found, 0 if all up to date

Example GitHub Actions workflow::

    - name: Check requirements status
      run: |
        check_requirements_failures --org openedx --output-path ./reports --check
      continue-on-error: false  # Fail the workflow if check fails

    - name: Upload reports
      if: always()  # Upload even if previous step fails
      uses: actions/upload-artifact@v3
      with:
        name: requirements-reports
        path: ./reports/*.csv
