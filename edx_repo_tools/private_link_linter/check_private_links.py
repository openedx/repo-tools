"""
Check commits and pull requests for private links.

This implements the OEP-51 changes from this pull request:
https://github.com/openedx/open-edx-proposals/pull/348

"""

import re
import sys
import textwrap

import lxml.html
import markdown2
import requests

# from https://github.com/trentm/python-markdown2/wiki/link-patterns
URL_PATTERN = re.compile(
    r"""
        \b
        (
            (?:https?://|(?<!//)www\.)    # prefix - https:// or www.
            \w[\w_\-]*(?:\.\w[\w_\-]*)*   # host
            [^<>\s"']*                    # rest of url
            (?<![?!.,:*_~);])             # exclude trailing punctuation
            (?=[?!.,:*_~);]?(?:[<\s]|$))  # make sure that we're not followed by " or ', i.e. we're outside of href="...".
        )
    """,
    re.X
)
markdown = markdown2.Markdown(
    extras=["link-patterns"],
    link_patterns=[(URL_PATTERN, r"\1")]
)

def stdin_commits():
    """Read rev-list output on stdin, yield (hash, commit-message) pairs."""
    commits = sys.stdin.read().split("\0")
    for commit in commits:
        if commit:
            meta, message = commit.split("\n\n", maxsplit=1)
            hash = meta.split("\n", maxsplit=1)[0]
            yield (hash, textwrap.dedent(message))

def things_to_check():
    """What are all of the things we should check?"""
    yield "PR title", sys.argv[1]
    yield "PR description", sys.argv[2]
    for hash, message in stdin_commits():
        yield f"Commit {hash}", message

def markdown_urls(text):
    """Yield the URLs in the markdown `text`."""
    html = markdown.convert(text)
    doc = lxml.html.document_fromstring(html)
    for link in doc.xpath('//a'):
        yield link.get('href')

def remove_private_refs(text):
    """Remove lines marked `Private-ref:`."""
    return re.sub(r"(?mi)^private-ref:.*$", "", text)

# If you end up at one of these, the URL might not be public.
BAD_URL_SNIPPETS = [
    "https://id.atlassian.com/login",
    "https://trello.com/",
]

def text_errors(text):
    """Yield error messages for problems in `text`, maybe none."""
    text = remove_private_refs(text)
    for url in markdown_urls(text):
        try:
            resp = requests.get(url)
        except requests.RequestException as exc:
            yield f"URL {url} failed: {exc}"
        else:
            status = resp.status_code
            ok = (200 <= status < 300)
            if not ok:
                yield f"BAD: URL {url} status is {status}"
                continue
            for bad_snip in BAD_URL_SNIPPETS:
                if bad_snip in resp.url:
                    yield f"URL {url} went to a URL containing {bad_snip!r}"
                    continue

def main():
    for name, text in things_to_check():
        for error_msg in text_errors(text):
            print(f"{name}: {error_msg}")

if __name__ == "__main__":
    main()
