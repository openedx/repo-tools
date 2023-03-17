"""
Provides SQL queries used for interacting with BigQuery.
"""

# This query is mostly generated using the BigQuery Information Schema.
#
# select concat("_target.",column_name," = ","_source.",column_name)
# from `pull-request-reporting.open_edx_github.INFORMATION_SCHEMA.COLUMNS`
# where table_name = 'closed_pull_requests';
#
UPSERT_CLOSED_PULLS = """merge `pull-request-reporting.open_edx_github.closed_pull_requests` _target
using `pull-request-reporting.open_edx_github._TEMP_TABLE_NAME_` _source 
on _target.permalink = _source.permalink
when matched then
  update
  set
  _target.additions = _source.additions,
  _target.labels = _source.labels,
  _target.mergedAt = _source.mergedAt,
  _target.isDraft = _source.isDraft,
  _target.lastEditedAt = _source.lastEditedAt,
  _target.updatedAt = _source.updatedAt,
  _target.headRef = _source.headRef,
  _target.permalink = _source.permalink,
  _target.changedFiles = _source.changedFiles,
  _target.deletions = _source.deletions,
  _target.mergedBy = _source.mergedBy,
  _target.url = _source.url,
  _target.author = _source.author,
  _target.baseRef = _source.baseRef,
  _target.createdAt = _source.createdAt,
  _target.number = _source.number,
  _target.repository = _source.repository,
  _target.commits = _source.commits,
  _target.state = _source.state,
  _target.title = _source.title
when not matched then
  insert (additions, labels, mergedAt, isDraft, lastEditedAt, updatedAt, headRef, permalink, changedFiles, deletions, mergedBy, url, author, baseRef, createdAt, number, repository, commits, state, title)
  values (additions, labels, mergedAt, isDraft, lastEditedAt, updatedAt, headRef, permalink, changedFiles, deletions, mergedBy, url, author, baseRef, createdAt, number, repository, commits, state, title);
"""

