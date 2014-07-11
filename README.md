This repo contains a number of tools for working with GitHub repositories:

 * author-check.py: Check that AUTHORS is correct in our repos.
 * pull-age.py: Compute the age of pull requests.
 * wall.py: Run the wall-displayed Pull Request aging chart.
 * copy-labels.py: Copy labels from one GitHub repo to another.

Most of these make GitHub api calls, and so will need GitHub credentials in
order to not be severely rate-limited.  Edit (or create) ~/.netrc so that it
has an entry like this:

    machine api.github.com
      login nedbat
      password ddf9079e12042ac022c101c61c0235965851e209
 
The login is your GitHub user name, the password is the personal access token
you get from <https://github.com/settings/applications>.


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

## Installation

You'll need to have [virtualenv](http://www.virtualenv.org) installed already.
Then run:

    git clone https://github.com/edx/author-check.git
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

You'll also need to grab a personal access token from Github (go to
<https://github.com/settings/applications> to create one) and create an
`auth.yaml` file of the form:

    user: "<your github username>"
    token: "<your personal access token>"

`people.yaml` contains the mapping between Github username and the canonical
entry for AUTHORS files. It also has information about whether the person has
signed a contributor agreement or is covered by the institution they work for.

## Feedback

Please send any feedback to <jtauber@edx.org>.
