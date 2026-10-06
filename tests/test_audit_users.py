"""
Tests for audit_users.

These run the real command against a real (sync) GhApi client, faking only the
HTTP layer, so that a breaking change in ghapi's API surface (such as the move
to async-by-default in ghapi 2) fails here rather than at runtime.

Two HTTP clients are in play, so two mocking mechanisms are needed:

- GitHub REST calls go through ghapi, which uses httpx2 (via fasttransport).
  `responses` cannot intercept httpx2, so we patch httpx2.Client with a
  MockTransport. This relies on ghapi's internals: if ghapi changes its HTTP
  library, this patch needs updating. httpx2 is a dev dependency for this reason.
- The GraphQL call in audit_users uses `requests`, so we mock it with `responses`.
"""

import base64
import functools
import json

import httpx2
import responses
from click.testing import CliRunner

from edx_repo_tools.audit_gh_users.audit_users import main

CSV = "GitHub Username,Name\nin-salesforce,Someone\n"

# Teams for each org member who is not in the CSV.
TEAMS = {
    "only-other-team": ["some-team"],
    "triage-and-other": ["openedx-triage", "some-team"],
    "only-triage": ["openedx-triage"],
    "only-interest-performance": ["interest-performance"],
    "only-edunext-website": ["edunext-website"],
    "only-bot": ["bot-netlify"],
    "bot-and-other": ["bot-netlify", "some-team"],
    "only-product-managers": ["openedx-product-managers"],
    "only-wg": ["wg-marketing"],
    "wg-and-triage": ["wg-translations", "openedx-triage"],
    "wg-and-other": ["wg-marketing", "some-team"],
    "all-ignored": ["openedx-triage", "interest-performance"],
    "no-teams": [],
}


def _github_handler(request):
    """
    Fake the REST endpoints audit_users calls.
    """
    path = request.url.path
    page = request.url.params.get("page", "1")
    if path == "/orgs/openedx/members":
        logins = ["in-salesforce", *TEAMS]
        return httpx2.Response(200, json=[{"login": login} for login in logins] if page == "1" else [])
    if path == "/repos/openedx/openedx-webhooks-data/contents/salesforce-export.csv":
        return httpx2.Response(
            200, json={"content": base64.encodebytes(CSV.encode()).decode()}
        )
    return httpx2.Response(404, json={"message": f"unexpected request: {path}"})


def _graphql_callback(request):
    """
    Fake the GraphQL teams lookup, answering for whichever user was queried.
    """
    query = json.loads(request.body)["query"]
    user = next(login for login in TEAMS if f'userLogins:"{login}"' in query)
    teams = TEAMS[user]
    body = {
        "data": {
            "organization": {
                "teams": {"totalCount": len(teams), "nodes": [{"name": name} for name in teams]}
            }
        }
    }
    return (200, {}, json.dumps(body))


@responses.activate
def test_audit_users_flags_only_users_with_a_non_ignored_team(monkeypatch):
    monkeypatch.setattr(
        httpx2,
        "Client",
        functools.partial(httpx2.Client, transport=httpx2.MockTransport(_github_handler)),
    )
    responses.add_callback(responses.POST, "https://api.github.com/graphql", callback=_graphql_callback)

    result = CliRunner().invoke(main, ["--github-token", "fake-token"])

    assert result.exit_code == 0, result.output
    flagged = {line.split(" - ")[0] for line in result.output.splitlines() if " - teams: " in line}
    assert flagged == {"only-other-team", "triage-and-other", "wg-and-other", "bot-and-other"}
    # Only users missing from the CSV are looked up.
    assert len(responses.calls) == len(TEAMS)
