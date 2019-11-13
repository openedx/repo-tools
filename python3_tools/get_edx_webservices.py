import github
from get_repos import orgs, expanded_repos_list, get_remote_yaml


webservices = []

for repo in expanded_repos_list(orgs):
    try:
        metadata = get_remote_yaml(repo, 'openedx.yaml')
    except github.GithubException:
        continue
    if 'tags' in metadata and 'webservice' in metadata['tags']:
        print("{}".format(repo.html_url))
        webservices.append(repo)

