import json
import logging
from dataclasses import dataclass

import click
from github3 import GitHubError
from github3.exceptions import NotFoundError
from tqdm import tqdm

import yaml
from edx_repo_tools.auth import pass_github
from edx_repo_tools.utils import dry_echo, dry, change_dir

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DEFAULT_ORGS = ["openedx"]

@dataclass
class CommitInfo:
    sha: str
    original_ref: str

@click.command()
@click.argument("ref")
@click.option("--org", multiple=True, default=DEFAULT_ORGS, help="GitHub org to scan")
@click.option("--search-branches", multiple=True, help="Branches to search for metadata")
@click.option("--dry/--doit", default=True, help="Dry run mode (default is dry run)")
@click.option("--create-tag/--create-branch", "use_tag", default=True, help="Create tags (default) or branches")
@click.option("--reverse", is_flag=True, help="Undo: delete the tags/branches instead of creating them")
@click.option("--skip-invalid", is_flag=True, default=False, help="Skip repos with invalid metadata")
@click.option("--input-plan", type=click.Path(), help="Load repo plan from JSON instead of scanning repos")
@click.option("--output-plan", type=click.Path(), help="Save discovered repo plan to JSON")
@click.option("--repos", multiple=True, help="Explicit list of repos (full names)")
@click.option("--skip-repo", multiple=True, help="Skip repos matching these full names")
@pass_github
def main(hub, ref, org, search_branches, dry, use_tag, reverse, skip_invalid, input_plan, output_plan, repos, skip_repo):
    """Create or delete release tags or branches for Open edX repositories."""
    repos = load_repos(hub, org, search_branches, input_plan, output_plan, repos, skip_repo)

    commits = {}
    for repo, ref_name in tqdm(repos, desc="Finding commits"):
        try:
            sha = find_commit(repo, ref_name or repo.default_branch)
            commits[repo] = CommitInfo(sha=sha, original_ref=ref_name or repo.default_branch)
        except Exception as e:
            log.error(f"Error finding commit for {repo.full_name}: {e}")
            if not skip_invalid:
                raise

    if not commits:
        click.secho("No repositories found to tag.", fg="red")
        return

    if reverse:
        show_reverse_plan(commits, ref, use_tag, dry)
    else:
        show_plan(commits, ref, use_tag, dry)

    if click.confirm("Proceed?"):
        try:
            create_or_delete_refs(commits, ref, use_tag, dry, reverse)
            click.secho("Done!", fg="green")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            raise

def load_repos(hub, org, search_branches, input_plan, output_plan, repos, skip_repo):
    """Load repositories based on input options."""
    if repos:
        repos = [(hub.repository(*repo.split("/")), search_branches[0] if search_branches else None) for repo in repos]
    elif input_plan:
        with open(input_plan) as f:
            repos = [(hub.repository(item["owner"], item["name"]), item["ref"]) for item in json.load(f)]
    else:
        repos = find_repos(hub, org, search_branches)
        if output_plan:
            with open(output_plan, "w") as f:
                json.dump([
                    {"owner": repo.owner.login, "name": repo.name, "ref": ref_name}
                    for repo, ref_name in repos
                ], f, indent=2)

    if skip_repo:
        repos = [(repo, ref_name) for repo, ref_name in repos if repo.full_name not in skip_repo]

    return repos


def find_repos(hub, orgs, branches):
    """Find all repos to process, prioritizing catalog-info.yaml over openedx.yaml."""
    found = {}

    for org in orgs:
        repos = list(hub.organization(org).repositories())
        for repo in tqdm(repos, desc=f"Scanning repos in {org}"):
            if repo.fork or repo.private:
                continue

            ref = None
            for filename in ["catalog-info.yaml", "openedx.yaml"]:
                for branch in (branches or [repo.default_branch]):
                    try:
                        contents = repo.file_contents(filename, ref=branch)
                        data = yaml.safe_load(contents.decoded)
                        if filename == "catalog-info.yaml":
                            ref = data.get("metadata", {}).get("annotations", {}).get("openedx.org/release")
                        else:
                            ref = data.get("openedx-release", {}).get("ref")
                        if ref:
                            break  # Found a valid reference in this branch, no need to check other branches for this file
                    except (NotFoundError, Exception):
                        continue  # Couldn't find the file in this branch, keep trying other branches
                if ref:
                    break  # Found a valid reference from one of the files, no need to check other files

            if ref:
                found[repo.full_name] = (repo, ref)
            else:
                log.info(f"No release reference found for {repo.full_name}, skipping.")

    return list(found.values())


def find_commit(repo, ref):
    """Find the commit SHA for a given ref."""
    try:
        branch = repo.branch(ref)
        return branch.commit.sha
    except NotFoundError:
        try:
            tag = repo.ref(f"tags/{ref}")
            return tag.object.sha
        except (NotFoundError, GitHubError):
            commit = repo.git_commit(ref)
            return commit.sha

def show_plan(commits, new_ref, use_tag, dry):
    """Print a summary of work to be done."""
    for repo, commit_info in commits.items():
        dry_echo(dry, f"Will create {'tag' if use_tag else 'branch'} {new_ref} at {commit_info.sha[:7]} (from {commit_info.original_ref}) in {repo.full_name}")

def show_reverse_plan(commits, new_ref, use_tag, dry):
    for repo, commit_info in commits.items():
        dry_echo(dry, f"Will delete {'tag' if use_tag else 'branch'} {new_ref} (original: {commit_info.original_ref}) in {repo.full_name}")

def create_or_delete_refs(commits, new_ref, use_tag, dry, reverse):
    ref_type = "tags" if use_tag else "heads"
    create_ref_path = f"refs/{ref_type}/{new_ref}"  # for creation
    lookup_ref_path = f"{ref_type}/{new_ref}"       # for lookup/delete

    completed = []
    errors = []

    for repo, commit_info in tqdm(commits.items(), desc="Deleting refs" if reverse else "Creating refs"):
        dry_echo(dry, f"{'Deleting' if reverse else 'Creating'} {create_ref_path} (from {commit_info.original_ref}) in {repo.full_name}")
        if dry:
            continue

        try:
            if reverse:
                repo.ref(lookup_ref_path).delete()
            else:
                repo.create_ref(ref=create_ref_path, sha=commit_info.sha)
                completed.append((repo, create_ref_path))
        except Exception as e:
            log.error(f"Error {'deleting' if reverse else 'creating'} {create_ref_path} in {repo.full_name}: {e}")
            if not reverse:
                rollback_refs(completed)
                raise
            else:
                errors.append((repo.full_name, str(e)))

    if errors and reverse:
        click.secho(f"Some deletions failed:", fg="red")
        for repo_name, error in errors:
            click.secho(f"  {repo_name}: {error}", fg="red")

def rollback_refs(completed_refs):
    click.secho("Rolling back...", fg="yellow")
    for repo, ref_path in tqdm(reversed(completed_refs), desc="Rolling back refs"):
        try:
            repo.ref(ref_path).delete()
            click.secho(f"Rolled back {ref_path} in {repo.full_name}", fg="yellow")
        except Exception as e:
            log.error(f"Error rolling back {ref_path} in {repo.full_name}: {e}")

if __name__ == "__main__":
    main()
