from get_repos import expanded_repos_list, orgs, total_language_bytes

all_repos = expanded_repos_list(orgs)

repo_size_map = {}

for repo in all_repos:
    if not repo.archived:
        print(",".join([repo.name, repo.html_url, str(repo.fork), total_language_bytes(repo)]))
