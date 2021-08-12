from github import Github, GithubException
import requests
import re
import json
import argparse


# Initialize parser
parser = argparse.ArgumentParser()

# Adding optional argument
parser.add_argument("-o", "--org", type=str,help = "Relevant Organization")
parser.add_argument("-b", "--branch", type=str,help = "Relevant Named Release Branch")
parser.add_argument("-r", "--repo", help = "edx REPO to parse")
parser.add_argument("-a", "--api", help = "GITHUB API TOKEN")
# Read arguments from command line
args = parser.parse_args()

ORGANIZATION = args.org or "edx"
TOKEN = args.api

g = Github(TOKEN, per_page =100)
repo_name = (args.repo or "blockstore")
repo = g.get_repo( ORGANIZATION+ "/"+ repo_name)

def get_named_release_branches():

    branch_names=list(repo.get_branches())
    return list(filter(lambda branch: "open-release/" in branch.name, branch_names))

def get_most_recent_named_release():
    branches = get_named_release_branches()
    return sorted(branches, reverse=True,key =lambda branch: repo.get_branch(branch.name).commit.commit.author.date)[0]

def get_delta_commits():
    print("Generating Commit Deltas")
    most_recent= args.branch or get_most_recent_named_release().name
    date = repo.get_branch(most_recent).commit.commit.author.date
    commits = repo.get_commits(since=date)
    return commits


LAX= r"""(?xi) # case-insensitive
    ^
    # some labels can be pluralized, since it's hard to remember.
    (?P<label>build|chores?|docs?|feat|fix|perf|refactor|revert|style|tests?|temp)
    # an optional scope is allowed
    (?:\(\w+\))?
    (?P<breaking>!?):\s
    (?P<subjtext>.+)
    $
    |
    # GitHub revert PR commit syntax
    ^Revert\s+"(?P<subjtext2>.+)"(?:\s+\(\#\d+\))?$
    """

def analyze_commit(title):
    commit={}
    commit["lax"] = False
    m = re.search(LAX,title)
    if m:
        commit["lax"] = True
        commit["label"]= m["label"]
        commit["subjtext"]= m["subjtext"] or m["subjtext2"] or ""
        if m["breaking"]:
            commit["breaking"]= "YES"
        else:
            commit["breaking"]= ""
    else:
        commit["label"]= "other"
        commit["subjtext"]= title
        commit["breaking"]= ""
    return commit

def get_pr_url(commit):

    request_dict = requests.get(
        f'https://api.github.com/repos/{ORGANIZATION}/{repo_name}/commits/{commit.sha}/pulls',
        headers= {
            'Authorization': 'token %s' % TOKEN,
            "Accept": "application/vnd.github.groot-preview+json"
            }
        ).text
    try:
        url =json.loads(request_dict)[0]["url"]
    except:
        try:
            url= json.loads(request_dict)["url"]
        except:
            url= ""
    return url

def html_table(lol):
  yield '<table id="myTable">'
  yield'<tr><th onclick="sortTable(0)">Breaking</th> <th onclick="sortTable(1)">Label</th><th onclick="sortTable(2)">Title</th><th onclick="sortTable(3)">Date</th><th onclick="sortTable(4)">Author</th></tr>'
  for sublist in lol:
    yield '  <tr><td>'
    yield '    </td><td>'.join(sublist)
    yield '  </td></tr>'
  yield '</table>'

def create_changelog_html():
    commits = get_delta_commits()
    #TODO: ADD REAL COMMIT NAMES AND ORDER
    filtered_commits=[]
    print("Aquiring associated PRs")
    for commit in commits:
        title = commit.commit.message
        #remove messaging for squashed merges
        if title.split()[0]=="Merge":
            title= " ".join(title.split()[8:])
        title_info = analyze_commit(title[0:70])
        pr_url= get_pr_url(commit)
        filtered_commits.append(
            [
            title_info["breaking"],
            title_info["label"],
            title_info["subjtext"],
            str(commit.commit.author.date),
            f'<a href ="{commit.commit.author.email}">{commit.commit.author.name}</a>',
            f'<a href ="{pr_url}">PR</a>',
            ]
        )

    table_html = '\n'.join(html_table(filtered_commits))

    with open('changelog_scripts.html', 'r') as file:
        script_and_input = file.read().replace('\n', '')

    msg = f'<!DOCTYPE html><html>{script_and_input}<body>{table_html}</body></html>'
    text_file = open(f"{repo_name}changelog.html", "w")
    text_file.write(msg)
    text_file.close()

create_changelog_html()









