from ownership_tools.get_repos import expanded_repos_list, orgs, has_python_code


def get_python_repos():
    python_repos = []
    for repo in expanded_repos_list(orgs):
        if repo.archived:
            continue
        if not has_python_code(repo):
            continue
        python_repos.append(repo)
    return python_repos


if __name__ == "__main__":
    repo_names = str.join(',', get_python_repos())
    print(repo_names)
