"""
Check repositories for Python requirements upgrade workflow failures.

This tool checks each repository in a GitHub organization for:
1. The presence of .github/workflows/upgrade-python-requirements.yml
2. The last time a PR titled "chore: Upgrade Python requirements" was merged
3. The date and version of the last release

This helps identify repositories where the automated requirements upgrade
workflow may be failing or stalled.
"""

import csv
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import click


class CheckFailedException(click.ClickException):
    """
    Exception raised when check mode finds repositories with stale requirements.

    This exception is raised instead of returning an exit code, following Click conventions.
    """

    def __init__(self, failed_repos, output_path):
        self.failed_repos = failed_repos
        self.output_path = output_path
        self.exit_code = 1

    def show(self, file=None):
        """Display the failure message with list of failed repositories."""
        click.echo("\n" + "!" * 80, err=True)
        click.echo("CHECK FAILED", err=True)
        click.echo("!" * 80, err=True)
        click.echo(
            f"\n{len(self.failed_repos)} repositories have not merged a requirements PR in 4+ weeks:",
            err=True,
        )
        for result in self.failed_repos:
            repo = result["repo"]
            pr = result["last_pr"]
            if pr:
                click.echo(f"  - {repo}: Last PR merged {pr['date']}", err=True)
            else:
                click.echo(f"  - {repo}: No PR ever merged", err=True)
        if self.output_path:
            click.echo("\nSee failed repos CSV for details.", err=True)


def run_gh_command(command):
    """
    Run a GitHub CLI command and return the output.

    Args:
        command: List of command arguments to pass to gh

    Returns:
        dict or list: Parsed JSON output from the gh command
        None: If the command fails or returns no data
    """
    try:
        result = subprocess.run(
            ["gh"] + command, capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.CalledProcessError:
        # Command failed, return None
        return None
    except json.JSONDecodeError:
        # Output wasn't valid JSON
        return None


def get_workflow_run_stats(org, repo):
    """
    Get statistics about the last 10 runs of the upgrade-python-requirements.yml workflow.

    Args:
        org: GitHub organization name
        repo: Repository name

    Returns:
        dict: Dictionary with 'total_runs', 'failed_runs', 'success_runs', 'other_runs' keys
        None: If the workflow doesn't exist or no runs found
    """
    # Use gh run list with the workflow file name
    # This will return 404/empty if the workflow doesn't exist
    result = run_gh_command(
        [
            "run",
            "list",
            "--repo",
            f"{org}/{repo}",
            "--workflow",
            "upgrade-python-requirements.yml",
            "--limit",
            "10",
            "--json",
            "conclusion,status",
        ]
    )

    if not result or len(result) == 0:
        return None

    # Count the different outcomes
    failed_runs = 0
    success_runs = 0
    other_runs = 0

    for run in result:
        conclusion = run.get("conclusion")
        if conclusion == "failure":
            failed_runs += 1
        elif conclusion == "success":
            success_runs += 1
        else:
            # Could be: cancelled, skipped, timed_out, action_required, neutral, etc.
            other_runs += 1

    return {
        "total_runs": len(result),
        "failed_runs": failed_runs,
        "success_runs": success_runs,
        "other_runs": other_runs,
    }


def get_last_requirements_pr(org, repo):
    """
    Get the last merged PR with title "chore: Upgrade Python requirements".

    Args:
        org: GitHub organization name
        repo: Repository name

    Returns:
        dict: Dictionary with 'date', 'pr_number', and 'url' keys, or None if not found
    """
    # Search for merged PRs with the specific title
    result = run_gh_command(
        [
            "pr",
            "list",
            "--repo",
            f"{org}/{repo}",
            "--state",
            "merged",
            "--search",
            "chore: Upgrade Python requirements in:title",
            "--limit",
            "1",
            "--json",
            "number,title,mergedAt,url",
        ]
    )

    if result and len(result) > 0:
        pr = result[0]
        # Parse the merged date
        merged_at = pr.get("mergedAt")
        if merged_at:
            # Parse ISO 8601 date and format it
            dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d")

            return {
                "date": formatted_date,
                "pr_number": pr.get("number"),
                "url": pr.get("url"),
            }

    return None


def get_last_release(org, repo):
    """
    Get the date and version of the last release.

    Args:
        org: GitHub organization name
        repo: Repository name

    Returns:
        dict: Dictionary with 'date', 'version', 'name', and 'isLatest' keys, or None if no releases
    """
    result = run_gh_command(
        [
            "release",
            "list",
            "--repo",
            f"{org}/{repo}",
            "--limit",
            "1",
            "--json",
            "tagName,publishedAt,name,isLatest",
        ]
    )

    if result and len(result) > 0:
        release = result[0]
        published_at = release.get("publishedAt")
        if published_at:
            # Parse ISO 8601 date and format it
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d")

            return {
                "date": formatted_date,
                "version": release.get("tagName"),
                "name": release.get("name"),
                "isLatest": release.get("isLatest"),
            }

    return None


def get_org_repositories(org, include_archived=False):
    """
    Get all repositories in an organization.

    Args:
        org: GitHub organization name
        include_archived: Whether to include archived repositories

    Returns:
        list: List of repository names
    """
    try:
        # Use gh api with --paginate to get all repos
        # The --jq filter extracts name and archived status
        if include_archived:
            jq_filter = ".[].name"
        else:
            jq_filter = ".[] | select(.archived == false) | .name"

        result = subprocess.run(
            [
                "gh",
                "api",
                f"/orgs/{org}/repos",
                "--paginate",
                "--jq",
                jq_filter,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            # gh api with --paginate and --jq returns one item per line
            repos = [r.strip() for r in result.stdout.strip().split("\n") if r.strip()]
            return repos
        return []
    except subprocess.CalledProcessError:
        return []


def write_csv_report(output_dir, org, timestamp, results, suffix=""):
    """
    Write CSV report with repository results.

    Args:
        output_dir: Path object for output directory
        org: Organization name
        timestamp: Timestamp string for filename
        results: List of result dictionaries
        suffix: Optional suffix to add to filename (e.g., "_FAILED")

    Returns:
        Path to the created CSV file
    """
    filename = f"requirements_check_{org}_{timestamp}{suffix}.csv"
    filepath = output_dir / filename
    # Define CSV fieldnames (defined here to match write_csv_report)
    fieldnames = [
        "Repository",
        "Total Runs",
        "Failed Runs",
        "Success Runs",
        "Last PR Date",
        "PR Number",
        "PR URL",
        "Last Release Date",
        "Release Version",
        "Release Name",
        "Release Is Latest",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            repo = result["repo"]
            stats = result["workflow_stats"]
            pr = result["last_pr"]
            release = result["last_release"]

            writer.writerow(
                {
                    "Repository": repo,
                    "Total Runs": stats["total_runs"],
                    "Failed Runs": stats["failed_runs"],
                    "Success Runs": stats["success_runs"],
                    "Last PR Date": pr["date"] if pr else "N/A",
                    "PR Number": pr["pr_number"] if pr else "N/A",
                    "PR URL": pr["url"] if pr else "N/A",
                    "Last Release Date": release["date"] if release else "N/A",
                    "Release Version": release["version"] if release else "N/A",
                    "Release Name": release["name"] if release else "N/A",
                    "Release Is Latest": release["isLatest"] if release else "N/A",
                }
            )

    return filepath


def display_human_readable_results(org, results):
    """
    Display results in human-readable format to stdout.

    Args:
        org: Organization name
        results: List of result dictionaries
    """
    click.echo("\n" + "=" * 80)
    click.echo("RESULTS")
    click.echo("=" * 80 + "\n")

    for result in results:
        repo = result["repo"]
        stats = result["workflow_stats"]
        pr = result["last_pr"]
        release = result["last_release"]

        click.echo(f"Repository: {org}/{repo}")
        click.echo("-" * 80)

        # Show workflow run statistics
        click.echo(f"  Workflow Runs (last {stats['total_runs']}):")
        click.echo(f"    Failed:  {stats['failed_runs']}")
        click.echo(f"    Success: {stats['success_runs']}")
        if stats["other_runs"] > 0:
            click.echo(f"    Other:   {stats['other_runs']}")

        if pr:
            click.echo("  Last Requirements PR:")
            click.echo(f"    Date: {pr['date']}")
            click.echo(f"    PR #: {pr['pr_number']}")
            click.echo(f"    URL:  {pr['url']}")
        else:
            click.echo("  Last Requirements PR: None found")

        if release:
            click.echo("  Last Release:")
            click.echo(f"    Date:     {release['date']}")
            click.echo(f"    Version:  {release['version']}")
            click.echo(f"    Name:     {release['name']}")
            click.echo(f"    isLatest: {release['isLatest']}")
        else:
            click.echo("  Last Release: None found")

        click.echo()


def display_check_mode_summary(failed_repos, output_path):
    """
    Display check mode pass/fail summary and raise exception if failures found.

    Args:
        failed_repos: List of failed result dictionaries (empty list if all passed)
        output_path: Output path for CSV files (or None)

    Raises:
        CheckFailedException: If any repositories have failed the check
    """
    if failed_repos:
        raise CheckFailedException(failed_repos, output_path)
    else:
        click.echo("\n" + "=" * 80, err=True)
        click.echo("CHECK PASSED", err=True)
        click.echo("=" * 80, err=True)
        click.echo(
            "\nAll repositories have merged a requirements PR within the last 4 weeks.",
            err=True,
        )


@click.command()
@click.option("--org", default="openedx", help="GitHub organization name to check")
@click.option(
    "--include-archived",
    is_flag=True,
    default=False,
    help="Include archived repositories in the check",
)
@click.option(
    "--repo",
    "repos",
    multiple=True,
    help="Specific repository name(s) to check. If not provided, checks all repos in the org.",
)
@click.option(
    "--output-path",
    "output_path",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    default=None,
    help="Directory path to write CSV output file. If not provided, outputs to stdout in human-readable format.",
)
@click.option(
    "--check",
    "check_mode",
    is_flag=True,
    default=False,
    help="Check mode: Identify repos with no requirements PR merged in 4+ weeks and write to separate failed CSV. Exit with -1 if any failures found.",
)
def main(org, include_archived, repos, output_path, check_mode):
    """
    Check repositories for Python requirements upgrade workflow status.

    This tool examines repositories in a GitHub organization to find:
    - Repositories with the upgrade-python-requirements.yml workflow
    - When the last "chore: Upgrade Python requirements" PR was merged
    - The latest release information

    Requires the GitHub CLI (gh) to be installed and authenticated.
    """
    # Check if gh is installed
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("Error: GitHub CLI (gh) is not installed or not in PATH.", err=True)
        click.echo("Please install it from: https://cli.github.com/", err=True)
        return 1

    # Get list of repositories
    if repos:
        repo_list = list(repos)
    else:
        archived_msg = " (including archived)" if include_archived else ""
        click.echo(f"Fetching repositories from {org}{archived_msg}...", err=True)
        repo_list = get_org_repositories(org, include_archived)
        if not repo_list:
            click.echo(f"Error: Could not fetch repositories from {org}", err=True)
            return 1
        click.echo(f"Found {len(repo_list)} repositories\n", err=True)

    # Results storage
    results = []

    # Check each repository
    for repo in repo_list:
        click.echo(f"Checking {repo}...", err=True)

        # Get workflow run statistics (also checks if workflow exists)
        workflow_stats = get_workflow_run_stats(org, repo)

        if not workflow_stats:
            click.echo("  No upgrade workflow found or no runs, skipping\n", err=True)
            continue

        # Get last merged requirements PR
        last_pr = get_last_requirements_pr(org, repo)

        # Get last release
        last_release = get_last_release(org, repo)

        results.append(
            {
                "repo": repo,
                "workflow_stats": workflow_stats,
                "last_pr": last_pr,
                "last_release": last_release,
            }
        )

    # Output results
    if not results:
        click.echo(
            "\nNo repositories found with the upgrade-python-requirements.yml workflow."
        )
        return

    # In check mode, identify failed repositories (no PR merged in 4+ weeks)
    failed_repos = []
    if check_mode:
        four_weeks_ago = datetime.now() - timedelta(weeks=4)

        for result in results:
            pr = result["last_pr"]
            if pr is None:
                # No PR ever merged - this is a failure
                failed_repos.append(result)
            else:
                # Check if PR is older than 4 weeks
                pr_date = datetime.strptime(pr["date"], "%Y-%m-%d")
                if pr_date < four_weeks_ago:
                    failed_repos.append(result)

    if output_path:
        # CSV output to file
        # Create output directory if it doesn't exist
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Write main CSV report
        filepath = write_csv_report(output_dir, org, timestamp, results)
        click.echo(f"\nCSV report written to: {filepath}")

        # In check mode, also write failed repos CSV
        if check_mode and failed_repos:
            failed_filepath = write_csv_report(
                output_dir, org, timestamp, failed_repos, suffix="_FAILED"
            )
            click.echo(f"FAILED repos CSV written to: {failed_filepath}", err=True)
            click.echo(
                f"Found {len(failed_repos)} repositories with no requirements PR merged in 4+ weeks",
                err=True,
            )
    else:
        # Human-readable output to stdout
        display_human_readable_results(org, results)

    # In check mode, show summary and raise exception if any failures
    if check_mode:
        display_check_mode_summary(failed_repos, output_path)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
