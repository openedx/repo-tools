"""
Collect and report on conventional commit statistics.
"""

import csv
import datetime
import fnmatch
import os
import os.path
import re
import sqlite3
import sys

import click
try:
    import dataset
    import matplotlib.pyplot as plt
    import matplotlib.dates
    import pandas as pd
except ImportError as err:
    sys.exit(f"Did you install requirements/conventional_commits.txt? {err}")

from edx_repo_tools.utils import change_dir, get_cmd_output


@click.group(help=__doc__)
def main():
    pass

def load_commits(db, repo_name):
    """Load the commits from the current directory repo."""

    SEP = "-=:=-=:=-=:=-=:=-=:=-=:=-=:=-"
    GITLOG = f"git log --no-merges --format='format:date: %aI%nhash: %H%nauth: %aE%nname: %aN%nsubj: %s%n%b%n{SEP}'"
    SHORT_LINES = 5

    # -=:=-=:=-=:=-=:=-=:=-=:=-=:=-
    # date: 2021-07-06T15:51:32-04:00
    # hash: ecd257ae297277ef4e544e44f4e803dfd48f238c
    # auth: JHynes@edx.org
    # name: Justin Hynes
    # subj: feat!: Remove temp certificates mgmt cmd
    # [MICROBA-1311]
    # - Remove temporary management command used to fix records incorrectly created with a default `mode` of "honor".
    #
    # -=:=-=:=-=:=-=:=-=:=-=:=-=:=-
    # date: 2021-07-06T12:48:21-04:00
    # hash: 384bc6b5147423f9c3208ce5c4afa79e5e0cd040
    # auth: 8483753+crice100@users.noreply.github.com
    # name: Christie Rice
    # subj: fix: Fix cert status (#28097)
    # MICROBA-1372
    # -=:=-=:=-=:=-=:=-=:=-=:=-=:=-

    with db:
        commit_table = db["commits"]

        log = get_cmd_output(GITLOG)
        for i, commit in enumerate(log.split(SEP + "\n")):
            if commit:
                lines = commit.split("\n", maxsplit=SHORT_LINES)
                row = {"repo": repo_name}
                for line in lines[:SHORT_LINES]:
                    key, val = line.split(": ", maxsplit=1)
                    row[key] = val
                row["body"] = lines[SHORT_LINES].strip()
                analyze_commit(row)
                commit_table.insert(row)

# Strict conformance to OEP-51.
STRICT = r"""(?x)
    ^
    (?P<label>build|chore|docs|feat|fix|perf|refactor|revert|style|test|temp)
    (?P<breaking>!?):\s
    (?P<subjtext>.+)
    $
    """

# Looser checking of conformance to conventional commits.
LAX = r"""(?xi)
    ^
    (?P<label>\w+)
    (?:\(\w+\))?
    (?P<breaking>!?):\s
    (?P<subjtext>.+)
    $
    """

def analyze_commit(row):
    row["conventional"] = row["lax"] = False
    m = re.search(STRICT, row["subj"])
    if m:
        row["conventional"] = True
    else:
        m = re.search(LAX, row["subj"])
        if m:
            row["lax"] = True
    if m:
        row["label"] = m["label"]
        row["breaking"] = bool(m["breaking"])
        row["subjtext"] = m["subjtext"]
    row["bodylines"] = len(row["body"].splitlines())


@main.command(help="Collect stats about commits in local git repos")
@click.option("--db", "dbfile", default="commits.db", help="SQLite database file to write to")
@click.option("--ignore", multiple=True, help="Repos to ignore")
@click.option("--require", help="A file that must exist to process the repo")
@click.argument("repos", nargs=-1)
def collect(dbfile, ignore, require, repos):
    db = dataset.connect("sqlite:///" + dbfile)
    for repo in repos:
        if any(fnmatch.fnmatch(repo, pat) for pat in ignore):
            print(f"Ignoring {repo}")
            continue
        if require is not None:
            if not os.path.exists(os.path.join(repo, require)):
                print(f"Skipping {repo}")
                continue
        print(repo)
        with change_dir(repo) as repo_dir:
            repo_name = "/".join(repo_dir.split("/")[-2:])
            load_commits(db, repo_name)

QUERY = """\
    select
    weekend, total, con, cast((con*100.0)/total as integer) pctcon, bod, cast((bod*100.0)/total as integer) pctbod
    from (
        select
        strftime("%Y%m%d", date, "weekday 0") as weekend,
        count(*) total,
        sum(conventional) as con, sum(bodylines > 0) as bod
        from commits group by weekend
    )
    where weekend > '202009';
    """

@main.command(help="Plot the collected statistics")
def plot():
    # Read sqlite query results into a pandas DataFrame
    with sqlite3.connect("commits.db") as con:
        df = pd.read_sql_query(QUERY, con)

    # Make the date nice
    df["when"] = pd.to_datetime(df["weekend"], format="%Y%m%d")
    # Drop the last row, because it's probably incomplete
    df = df[:-1]
    df.tail()

    fig, ax = plt.subplots()
    fig.set_size_inches(12, 8)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b'))

    line1 = ax.plot(df.when, df.total, "*-", label="# Commits", color="gray", linewidth=1)[0]

    ax2 = ax.twinx()
    ax2.set_ylim(-5, 105)
    line2 = ax2.plot(df.when, df.pctcon, label="% Conventional", color="green", linewidth=4)[0]

    ax3 = ax.twinx()
    ax3.set_ylim(-5, 105)
    line3 = ax3.plot(df.when, df.pctbod, label="% with bodies", color="blue", linewidth=2)[0]

    lines = [line1, line2, line3]
    plt.legend(lines, [l.get_label() for l in lines])
    plt.show()


if __name__ == "__main__":
    main()
