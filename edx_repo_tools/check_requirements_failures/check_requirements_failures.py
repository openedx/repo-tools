"""
Check repositories for Python requirements upgrade workflow failures.

This tool checks each repository in a GitHub organization for:
1. The presence of .github/workflows/upgrade-python-requirements.yml
2. The last time a PR titled "chore: Upgrade Python requirements" was merged
3. The date and version of the last release

This helps identify repositories where the automated requirements upgrade
workflow may be failing or stalled.
"""

import json
import subprocess
from datetime import datetime

import click


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


def check_workflow_exists(org, repo):
    """
    Check if the upgrade-python-requirements.yml workflow exists in the repo.

    Args:
        org: GitHub organization name
        repo: Repository name

    Returns:
        bool: True if the workflow file exists, False otherwise
    """
    result = run_gh_command(
        [
            "workflow",
            "list",
            "--repo",
            f"{org}/{repo}",
            "--json",
            "name",
        ]
    )
    if not result:
        return False
    for r in result:
        if r["name"] == "Upgrade Requirements":
            return True
    return False


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
        dict: Dictionary with 'date', 'version', and 'url' keys, or None if no releases
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
            "tagName,publishedAt,url",
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
                "url": release.get("url"),
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


@click.command()
@click.option("--org", required=True, help="GitHub organization name to check")
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
    "--csv",
    "output_csv",
    is_flag=True,
    default=False,
    help="Output results in CSV format",
)
def main(org, include_archived, repos, output_csv):
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

        # Check if workflow exists
        has_workflow = check_workflow_exists(org, repo)

        if not has_workflow:
            click.echo("  No upgrade workflow found, skipping\n", err=True)
            continue

        # Get last requirements PR
        last_pr = get_last_requirements_pr(org, repo)

        # Get last release
        last_release = get_last_release(org, repo)

        results.append({"repo": repo, "last_pr": last_pr, "last_release": last_release})

    # Output results
    if not results:
        click.echo(
            "\nNo repositories found with the upgrade-python-requirements.yml workflow."
        )
        return 0

    if output_csv:
        # CSV output
        click.echo(
            "Repository,Last PR Date,PR Number,PR URL,Last Release Date,Release Version,Release URL"
        )
        for result in results:
            repo = result["repo"]
            pr = result["last_pr"]
            release = result["last_release"]

            pr_date = pr["date"] if pr else "N/A"
            pr_number = pr["pr_number"] if pr else "N/A"
            pr_url = pr["url"] if pr else "N/A"

            release_date = release["date"] if release else "N/A"
            release_version = release["version"] if release else "N/A"
            release_url = release["url"] if release else "N/A"

            click.echo(
                f"{repo},{pr_date},{pr_number},{pr_url},{release_date},{release_version},{release_url}"
            )
    else:
        # Human-readable output
        click.echo("\n" + "=" * 80)
        click.echo("RESULTS")
        click.echo("=" * 80 + "\n")

        for result in results:
            repo = result["repo"]
            pr = result["last_pr"]
            release = result["last_release"]

            click.echo(f"Repository: {org}/{repo}")
            click.echo("-" * 80)

            if pr:
                click.echo("  Last Requirements PR:")
                click.echo(f"    Date: {pr['date']}")
                click.echo(f"    PR #: {pr['pr_number']}")
                click.echo(f"    URL:  {pr['url']}")
            else:
                click.echo("  Last Requirements PR: None found")

            if release:
                click.echo("  Last Release:")
                click.echo(f"    Date:    {release['date']}")
                click.echo(f"    Version: {release['version']}")
                click.echo(f"    URL:     {release['url']}")
            else:
                click.echo("  Last Release: None found")

            click.echo()

    return 0


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
