import click
import gspread
import yaml


SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1qpWfbPYLSaE_deaumWSEZfz91CshWd3v3B7xhOk5M4U/edit"
REPO_OWNERSHIP_SHEET_NAME = "Individual Repo Ownership"
EDX_PLATFORM_SHEET_NAME = "edx-platform Apps Ownership"


@click.command()
@click.option(
    '--google-creds-file',
    type=click.Path(exists=True),
    help="JSON file containing Google API credentials"
)
@click.argument(
    'output',
    type=click.File('wb')
)
def main(google_creds_file, output):
    """CLI entry point."""

    spreadsheet = gspread.service_account(filename=google_creds_file).open_by_url(SPREADSHEET_URL)
    
    output.write(
        yaml.dump({'components': fetch_repos(spreadsheet)}).encode('utf8')
    )


def fetch_repos(spreadsheet):
    components = []
    for row in get_records_from_worksheet(spreadsheet.worksheet(REPO_OWNERSHIP_SHEET_NAME)):
        theme, squad = parse_owner_sqaud(row['owner.squad'])
        component = {
            'component_type': 'repository',
            'name': row['repo name'],
            'url': row['repo url'],
            'theme': theme,
            'squad': squad,
            'priority': row['owner.priority'],
            'description': row['Description'],
            'notes': row['Notes'],
            'children': [],
        }
        if component['url'] == 'https://github.com/edx/edx-platform':
            component['children'] = fetch_edx_platform_apps(spreadsheet)
        components.append(component)
    return components


def parse_owner_sqaud(squad):
    split_squad = squad.split('-', 1)
    if len(split_squad) > 1:
        return split_squad[0], split_squad[1]
    else:
        return '', split_squad[0]


def fetch_edx_platform_apps(spreadsheet):
    components = []
    for row in get_records_from_worksheet(spreadsheet.worksheet(EDX_PLATFORM_SHEET_NAME)):
        theme, squad = parse_owner_sqaud(row['owner.squad'])
        components.append({
            'component_type': 'subdirectory',
            'parent': 'edx-platform',
            'name': 'edx-platform:' + row['Path'][2:],
            'path': row['Path'],
            'url': row['Link'],
            'theme': theme,
            'squad': squad,
            'priority': row['owner.priority'],
            'description': row['Description'],
            'notes': row['Notes'],
        })
    return components


def get_records_from_worksheet(worksheet):
    # Start numbering at row 2; headers are spreadsheet row 1
    for _, row in enumerate(worksheet.get_all_records(), start=2):
        yield row


if __name__ == '__main__':
    main(auto_envvar_prefix='TOOLS')
