"""
CLI for importing GitHub data into BigQuery for further analysis and visualization.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import click
from google.cloud import bigquery
from google.oauth2 import service_account
from graphql_queries import CLOSED_ISSUE_QUERY, OPEN_ISSUE_QUERY
from graphql_util import retrieve_paginated_results
from sql_queries import UPSERT_CLOSED_PULLS

API_CREDENTIALS_FILE="google-service-credentials.json"
API_SCOPES = ["https://www.googleapis.com/auth/cloud-platform",
              "https://www.googleapis.com/auth/drive"]
OPEN_PULL_REQUEST_TABLE = "open_edx_github.open_pull_requests"

@click.group()
@click.option('--preserve-temp-files',
        default=False,
        help='Allows preserving temp files for debugging purposes, they are deleted by default.')
@click.pass_context
def cli(ctx, preserve_temp_files):
    """
    Click group representing the CLI.
    """
    click.echo("Starting up...")
    ctx.ensure_object(dict)
    ctx.obj["preserve_temp_files"] = preserve_temp_files


def get_bq_client():
    """
    Utility for returning a configured BigQuery client.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    credentials = service_account.Credentials.from_service_account_file(
        filename=dir_path + "/" + API_CREDENTIALS_FILE, scopes=API_SCOPES)

    return bigquery.Client(credentials=credentials, project=credentials.project_id)


def execute_dml_bigquery(query):
    """
    Executes DML queries and returns the query_job object.
    """
    client = get_bq_client()
    query_job = client.query(query)
    query_job.result()
    return query_job


def drop_bq_table(table_id):
    """
    Drops a BigQuery table by table_id.
    """
    client = get_bq_client()
    client.delete_table(table_id)
    click.echo(f"Dropped table {table_id}")


def jsonl_to_bq(filename):
    """
    Uploads a file to a table replacing the tables contents.  The operation 
    is effectively a drop and replace, so the schema will reflect the structure
    of the JSON documents in the file.  Alterations made to the table to add 
    additonal columns will be lost.
    """

    client = get_bq_client()

    dataset_id = " pull-request-reporting.open_edx_github "
    table_id = "pull-request-reporting.open_edx_github.open_pull_requests"

    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    job_config.autodetect = True
    job_config.write_disposition = "WRITE_TRUNCATE"

    with open(filename, "rb") as source_file:
        job = client.load_table_from_file(
            source_file,
            table_id,
            location="US",
            job_config=job_config,
        )

    job.result()

    click.echo(f"Loaded {job.output_rows} rows into {dataset_id}:{table_id}.")


def create_temp_table(jsonl_file, table_name):
    """
    Creates and populuates a temp table from that JSON Lines formated file.
    """

    client = get_bq_client()

    dataset_id = "pull-request-reporting.open_edx_github"
    table_id = "pull-request-reporting.open_edx_github." + table_name

    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    job_config.autodetect = True
    job_config.create_disposition = "CREATE_IF_NEEDED"
    job_config.write_disposition = "WRITE_TRUNCATE"

    with open(jsonl_file, "rb") as source_file:
        job = client.load_table_from_file(
            source_file,
            table_id,
            location="US",
            job_config=job_config,
        )

    job.result()

    click.echo(f"Loaded {job.output_rows} rows into {dataset_id}:{table_id}.")


def upsert_closed_pulls(table_name):
    """
    Merges records from a temporary table into a destination. Currently
    uses the permalink as a pseudo key.
    """

    query = UPSERT_CLOSED_PULLS.replace("_TEMP_TABLE_NAME_", table_name)
    query_job = execute_dml_bigquery(query)
    click.echo(f"Upserting closed pulls affected {query_job.num_dml_affected_rows} rows.")


def update_cols_bq(target_table_id):
    """
    When the table is recreated via the write disposition WRITE_TRUNCATE
    the schema is discerned from the JSONL document.  Two columns to track
    maintainers are added after the fact.
    """
    client = get_bq_client()

    table = client.get_table(target_table_id)

    original_schema = table.schema
    new_schema = original_schema[:]  
    new_schema.append(bigquery.SchemaField("maintainer", "STRING"))
    new_schema.append(bigquery.SchemaField("maintainer_organization", "STRING"))

    table.schema = new_schema
    table = client.update_table(table, ["schema"])


def update_maintainers_bq(target_table):
    """
    Populated the maintainer related columns by joining against
    an external table which is a Google Sheet.
    """

    query_text = f"""
    update `{target_table}` open
    set open.maintainer = repos.maintainer,
        open.maintainer_organization = repos.Maintainer_Org
    FROM `open_edx_github.connected_repository_sheet` repos
    where repos.Repository_Name = open.repository.name;
    """
    query_job = execute_dml_bigquery(query_text)

    click.echo(f"Updating Maintainers, modified {query_job.num_dml_affected_rows} rows.")


def get_closed_pulls(days_ago):
    """
    Retrieves closed pulls from n days_ago
    """
    now = datetime.now()
    ago = timedelta(days=days_ago)
    start = now - ago
    date_range = start.strftime("%Y-%m-%d") + ".." + now.strftime("%Y-%m-%d")
    return retrieve_paginated_results(CLOSED_ISSUE_QUERY.replace("_RANGE_",date_range))


def save_json_lines(results, filename):
    """
    BigQuery accepts JSON in the JSON Lines format where each object, where
    that object will correspond to a row in a table once uploaded.
    """
    with open(filename, "w", encoding='utf-8') as output:
        for pull in results:
            output.write(json.dumps(pull) + os.linesep)


@cli.command()
@click.pass_context
def handle_open_pulls(ctx):
    """
    CLI command that runs the open pulls workflow.
    """
    open_file_name = f"{tempfile.gettempdir()}/open_pulls.json"
    file_path = Path(open_file_name)

    open_pulls = retrieve_paginated_results(OPEN_ISSUE_QUERY)

    save_json_lines(open_pulls,open_file_name)    
    # Overwrite the Open Pull data in BigQuery
    jsonl_to_bq(open_file_name)
    # Add columns for maintainer data not detected from the JSON schema
    update_cols_bq(OPEN_PULL_REQUEST_TABLE)
    # Update the maintainer data in the newly created columns
    update_maintainers_bq(OPEN_PULL_REQUEST_TABLE)

    if not ctx.obj["preserve_temp_files"]:
        file_path.unlink(missing_ok=True)
        click.echo(f"Removed temp file {open_file_name}.")
    else:
        click.echo(f"Preserved temp file {open_file_name}.")


@cli.command()
@click.pass_context
@click.option('--days-ago', default=2, help='Retrieve closed pulls from n days ago and merge them into the BigQuery dataset.')
def handle_closed_pulls(ctx, days_ago):
    """
    CLI command that runs the closed pulls workflow.
    """
    # Closed issue processing flow:
    # - Query last period.
    # - Insert into temp table
    # - Run merge from temp table -> closed table
    # - Run queries to update maintainers
    # - Optinally drop temp table

    temp_table = datetime.now().strftime("%Y-%m-%d") + "_" + str(os.getpid())
    closed_file_name = f"{tempfile.gettempdir()}/closed_pulls.json"
    file_path = Path(closed_file_name)

    results = get_closed_pulls(days_ago)
    save_json_lines(results, closed_file_name)
    create_temp_table(closed_file_name, temp_table)
    upsert_closed_pulls(temp_table)
    drop_bq_table(f"open_edx_github.{temp_table}")

    if not ctx.obj["preserve_temp_files"]:
        file_path.unlink(missing_ok=True)
        click.echo(f"Removed temp file {closed_file_name}.")
    else:
        click.echo(f"Preserved temp file {closed_file_name}.")


if __name__ == '__main__':

    # pylint: disable=no-value-for-parameter
    cli(obj={})
