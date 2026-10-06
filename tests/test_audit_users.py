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


def _github_handler(request):
    """
    Fake the REST endpoints audit_users calls.
    """
    path = request.url.path
    page = request.url.params.get("page", "1")
    if path == "/orgs/openedx/members":
        members = [{"login": "in-salesforce"}, {"login": "extra-user"}] if page == "1" else []
        return httpx2.Response(200, json=members)
    if path == "/repos/openedx/openedx-webhooks-data/contents/salesforce-export.csv":
        return httpx2.Response(
            200, json={"content": base64.encodebytes(CSV.encode()).decode()}
        )
    return httpx2.Response(404, json={"message": f"unexpected request: {path}"})


@responses.activate
def test_audit_users_reports_extra_user_in_non_triage_team(monkeypatch):
    monkeypatch.setattr(
        httpx2,
        "Client",
        functools.partial(httpx2.Client, transport=httpx2.MockTransport(_github_handler)),
    )
    responses.post(
        "https://api.github.com/graphql",
        json={
            "data": {
                "organization": {
                    "teams": {"totalCount": 1, "nodes": [{"name": "some-team"}]}
                }
            }
        },
    )

    result = CliRunner().invoke(main, ["--github-token", "fake-token"])

    assert result.exit_code == 0, result.output
    assert "extra-user - teams: ['some-team']" in result.output
    assert "in-salesforce" not in result.output
    # Only the user missing from the CSV is looked up.
    assert [json.loads(c.request.body)["query"].count("extra-user") for c in responses.calls] == [1]
