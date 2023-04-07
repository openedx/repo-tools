A CLI for querying GraphQL data from GitHub and persisiting it to BigQuery for
analysis and visualization.

### Getting Started
In order to run you will need a JSON credentials file for Google Cloud.

The file is expected to be named `google-service-credentials.json` and in the same directory as the script.  The credentials should be associated with a GCP service account added to a GCP project.  The current service account is: pull-request-reporter@pull-request-reporting.iam.gserviceaccount.com

Additionall you will need to set a GitHub bearer token as an environment variable.  That token must be associated with an account with the appropriate permsions to access the repositories you are querying.

`export GH_BEARER_TOKEN=ghp_V2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Related Resources

- [BigQuery Workspace](https://console.cloud.google.com/bigquery?project=pull-request-reporting&ws=!1m4!1m3!3m2!1spull-request-reporting!2sopen_edx_github)
- [GCP Project](https://console.cloud.google.com/home/dashboard?project=pull-request-reporting)
- [Datastudio Dashboard](https://datastudio.google.com/reporting/64382012-1c39-4af0-8fa2-84c32c5192f5/page/p_ermoo938zc)
- [Authoritative Repository Sheet](https://docs.google.com/spreadsheets/d/1tI5OPMjnhL6obzynuAUURLjOSN72QWCkHSXGGoFLMG8/edit#gid=819569654)

### Get Help
`python ./graphql_requests.py --help`

### Process Open Pull Requests
`python ./graphql_requests.py handle-open-pulls`

### Process Closed Pull Requests.
`python ./graphql_requests.py handle-closed-pulls`
