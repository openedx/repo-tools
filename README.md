# author-check

A commandline utility for checking for consistency between committers,
people who have signed a contributor agreement and people in the AUTHORS
file.

    ./author_check.py <owner>/<repo>
    audits the given repo
    
    ./author_check.py <owner>/<repo> <pull-request-number>
    audits the given pull request
    
    ./author_check.py <user>
    status of given user
    
    ./author_check.py
    audits all repos in repos.yaml

You'll need to run this in a virtual environment with the `requirements.txt`
installed.

You'll also need to grab a personal access token from Github (go to
<https://github.com/settings/applications> to create one) and create an
`auth.yaml` file of the form:

    user: "<your github username>"
    token: "<your personal access token>"

`mapping.yaml` contains the mapping between Github username and the canonical
entry for AUTHORS files. It also has information about whether the person has
signed a contributor agreement or is covered by the institution they work for.

Please send any feedback to <jtauber@edx.org>.
