This repo contains a number of tools for working with GitHub repositories:

 * author_check.py: Check that AUTHORS is correct in our repos.
 * pull_age.py: Compute the age of pull requests.
 * wall.py: Run the wall-displayed Pull Request aging chart.
 * sync_labels.py: Sync labels across all GitHub repos to another.


## Setting up GitHub authentication

Most of these make GitHub API calls, and so will need GitHub credentials in
order to not be severely rate-limited.  Edit (or create) `~/.netrc` so that it
has an entry like this:

    machine api.github.com
      login your_user_name
      password ddf9079e12042ac022c101c61c0235965851e209
 
Change the login to your GitHub user name.  You'll get the password value from
<https://github.com/settings/applications>.  Visit that page, and in the
section called "Personal access tokens," click "Generate new token."  It will
prompt you for your password, then you'll see a scary list of scopes. Leave
them at their defaults, and click "Generate token." Copy the password that
appears. Paste it into your ~/.netrc.

## Installation

You'll need to have [virtualenv](http://www.virtualenv.org) installed already.
Then run:

    $ git clone https://github.com/edx/repo-tools.git
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt

`people.yaml` (in the private repo edx/repo-tools-data/) contains the mapping
between GitHub username and the canonical entry for AUTHORS files. It also has
information about whether the person has signed a contributor agreement or is
covered by the institution they work for.

# author_check

A commandline utility for checking for consistency between committers,
people who have signed a contributor agreement and people in the AUTHORS
file.

author_check needs a different authentication mechanism than `~/.netrc`.
Create an `auth.yaml` file of the form:

    user: "<your github username>"
    token: "<your personal access token>"

Various ways to invoke `author_check.py`:

    $ ./author_check.py <owner>/<repo>
    audits the given repo
    
    $ ./author_check.py <owner>/<repo> <pull-request-number>
    audits the given pull request
    
    $ ./author_check.py <user>
    status of given user
    
    $ ./author_check.py
    audits all repos in repos.yaml

# wall

Generates the JSON used to build the wall-displayed Pull Request age chart.

    $ python wall.py > age/age.json
    returns a JSON string of aging data

    $ python -m SimpleHTTPServer && python -m webbrowser age/age.html
    look at the awesome chart


# sync_labels

Syncs all github repos in `repos.yaml` to contain all the labels in `labels.yaml`

Deletes any labels that exist in a repo but not in `labels.yaml`

Both .yaml files are in the private edx/repo-tools-data repo.

## Feedback

Please send any feedback to <oscm@edx.org>.
