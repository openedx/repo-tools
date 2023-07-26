"""
Summarize who has write access to repos.

Writes a .md report, and captures screenshots of the GitHub permissions pages.
"""

import datetime
import itertools
import os
import re
import shutil
import sys

import requests
from playwright.sync_api import sync_playwright

IMAGES_DIR = "/tmp/repo_perms_images"
REPORT_FILE = "./report.md"


def goto(page, url):
    """
    Visit a GitHub URL in a Playwright page.

    If the page looks like it needs authentication, pause Playwright so the
    user can log in.
    """
    print(f"Visiting {url}")
    page.goto(url)
    if page.is_visible("text='Sign in'"):
        # When not logged in, this happens.
        print("Log in to GitHub, then press Resume in the Playwright Inspector window.")
        page.pause()
    if page.is_visible("text='Confirm access'"):
        # When logged in, but you have to finish MFA, this happens.
        print("Finish authenticating, then press Resume in the Playwright Inspector window.")
        page.pause()


TOKEN = os.environ['GITHUB_TOKEN']
HEADERS = {"Authorization": f"token {TOKEN}"}

def file_slug(s):
    return re.sub(r"[/]", "-", s)

def screenshot_pages(page, url, image_prefix):
    """
    Capture screenshots of pages starting with `url`.

    Follow links classed with `next_page` to capture follow-on pages.

    """
    goto(page, url)
    for imgnum in itertools.count():
        page.screenshot(path=f"{IMAGES_DIR}/{image_prefix}-{imgnum}.png", full_page=True)

        # If there's a next page, visit it.
        next_page = page.locator("a.next_page")
        if next_page.count():
            with page.expect_navigation():
                next_page.click()
        else:
            # No next page, we're done here.
            break


def request_list(url):
    """
    Get list data from a GitHub URL.

    This follows "next" links to get all of the pages in paginated data.
    """
    data = []
    while url:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        data.extend(resp.json())
        url = None
        if "link" in resp.headers:
            match = re.search(r'<(?P<url>[^>]+)>; rel="next"', resp.headers["link"])
            if match:
                url = match.group('url')
    return data


def request_dict(url):
    """Get dict data from a GitHub URL."""
    return requests.get(url, headers=HEADERS, timeout=60).json()

def counted(things: list, thing_name: str) -> str:
    """
    Make a phrase counting the things in a list.

    Uses a simplistic English pluralization.

    >>> counted([1, 2, 3], "number")
    "3 numbers"
    >>> counted(["apple"], "fruit")
    "1 fruit"
    >>> counted([], "monster")
    "0 monsters"

    """
    num = len(things)
    words = f"{num} {thing_name}"
    if num != 1:
        words += "s"
    return words


# Not sure what happened: GitHub used to report "push" for write access, but
# now it reports "write"? We can have both, since PERMS is just used to order
# access levels.
PERMS = ["pull", "read", "triage", "push", "write", "maintain", "admin"]
PUSH = PERMS.index("push")
ACCESS_NAMES = ["Read", "Read", "Triage", "Write", "Write", "Maintain", "Admin"]

def run(repos, playwright, report_print):
    context = playwright.chromium.launch(headless=False)
    page = context.new_page()
    goto(page, "https://github.com")

    report_print(f"# Access report as of {datetime.datetime.now():%Y-%m-%d}\n")

    team_data = {}
    users = {}

    for repo in repos:
        url = f"https://github.com/{repo}/settings/access"
        report_print(f"\n## Repo: [{repo}]({url})\n")
        screenshot_pages(page, url, f"access-{file_slug(repo)}")

        # Get the team memberships
        url = f"https://api.github.com/repos/{repo}/teams?per_page=100"
        teams = request_list(url)
        for team in teams:
            perm = PERMS.index(team["permission"])
            if perm < PUSH:
                # We don't care about triage or pull access.
                continue

            name = team["name"]
            team_page = team["html_url"]
            access = ACCESS_NAMES[perm]
            if name not in team_data:
                team_data[name] = team
                # Get the child teams.
                url = team["url"] + "/teams?per_page=100"
                team_teams = request_list(url)
                teams.extend(team_teams)    # Play fast and loose with extending while iterating.
                team["child_teams"] = team_teams

                # Get the people in the team.
                url = team["url"] + "/members?per_page=100"
                team_members = request_list(url)
                team["members"] = team_members

            members = team_data[name]["members"]
            census = counted(members, "member")
            child_teams = team_data[name]["child_teams"]
            if child_teams:
                census += ", " + counted(child_teams, "child team")
            report_print(f"- team: [{name}]({team_page}), {access} access: {census}")

            for child_team in child_teams:
                team_name = child_team["name"]
                team_page = child_team["html_url"]
                report_print(f"  - team: [{team_name}]({team_page}), {access}")

            for member in members:
                login = member["login"]
                if login not in users:
                    user_info = request_dict(member["url"])
                    users[login] = user_info
                user_page = users[login]["html_url"]
                user_name = users[login]["name"]
                if user_name is None:
                    user_name = ""
                else:
                    user_name += " "
                report_print(f"  - {user_name}[@{login}]({user_page})")

    # Get all the teams
    for team_name, team in team_data.items():
        screenshot_pages(page, team["html_url"] + "/members", f"team-{file_slug(team_name)}")

    page.close()
    context.close()

def main():
    if os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)

    repos = sys.argv[1:]
    if not repos or repos[0].startswith("-"):
        print("repo_access_scraper has no options. Just list repos as arguments:")
        print("  $ repo_access_scraper openedx/ecommerce openedx/xblock")
        return

    with sync_playwright() as playwright:
        with open(REPORT_FILE, "w") as report_md:
            def report_print(*args, **kwargs):
                print(*args, **kwargs, file=report_md)
            run(repos, playwright, report_print)

    shutil.make_archive("images", "zip", root_dir=IMAGES_DIR)
    shutil.rmtree(IMAGES_DIR)


if __name__ == "__main__":
    main()
