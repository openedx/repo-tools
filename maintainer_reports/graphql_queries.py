_REPOS_ = "repo:openedx/DoneXBlock repo:openedx/RateXBlock repo:openedx/XBlock repo:openedx/blockstore repo:openedx/brand-openedx repo:openedx/codejail repo:openedx/configuration repo:openedx/course-discovery repo:openedx/credentials repo:openedx/cs_comments_service repo:openedx/devstack repo:openedx/docs.openedx.org repo:openedx/ecommerce repo:openedx/ecommerce-worker repo:openedx/edx-ace repo:openedx/edx-analytics-dashboard repo:openedx/edx-analytics-data-api repo:openedx/edx-analytics-pipeline repo:openedx/edx-app-android repo:openedx/edx-cookiecutters repo:openedx/edx-developer-docs repo:openedx/edx-documentation repo:openedx/edx-notes-api repo:openedx/edx-ora2 repo:openedx/edx-platform repo:openedx/edx-proctoring repo:openedx/edx-rest-api-client repo:openedx/edx-search repo:openedx/edx-toggles repo:openedx/enterprise-catalog repo:openedx/event-routing-backends repo:openedx/frontend-app-account repo:openedx/frontend-app-admin-portal repo:openedx/frontend-app-authn repo:openedx/frontend-app-course-authoring repo:openedx/frontend-app-discussions repo:openedx/frontend-app-ecommerce repo:openedx/frontend-app-gradebook repo:openedx/frontend-app-learning repo:openedx/frontend-app-payment repo:openedx/frontend-app-profile repo:openedx/frontend-app-program-console repo:openedx/frontend-app-publisher repo:openedx/frontend-app-support-tools repo:openedx/frontend-build repo:openedx/frontend-component-footer repo:openedx/frontend-component-header repo:openedx/frontend-platform repo:openedx/frontend-template-application repo:openedx/license-manager repo:openedx/mdrst repo:openedx/open-edx-proposals repo:openedx/openedx-conference-website repo:openedx/openedx-demo-course repo:openedx/openedx-events repo:openedx/openedx-filters repo:openedx/openedx-i18n repo:openedx/paragon repo:openedx/taxonomy-connector repo:openedx/xblock-drag-and-drop-v2 repo:openedx/xblock-lti-consumer repo:openedx/xqueue repo:openedx/frontend-app-library-authoring repo:openedx/frontend-app-learner-record repo:openedx/frontend-app-authn  repo:openedx/django-config-models repo:openedx/edx-bulk-grades repo:openedx/edx-django-utils repo:openedx/edx-val repo:openedx/frontend-app-discussions  repo:openedx/frontend-app-ora-grading repo:openedx/xblock-sdk repo:openedx/xblock-utils"

_TYPE_="pr"
_STATE_="closed"
_QUERY_= f"{_REPOS_} is:{_TYPE_} is:{_STATE_} closed:_RANGE_"

CLOSED_ISSUE_QUERY="""
{
  search(first: 75, after: _END_CURSOR_, query: "_QUERY_", type: ISSUE) {
    pageInfo {
        startCursor
        hasNextPage
        endCursor
        }
        nodes {
      ... on PullRequest {
        title
        repository {
          name
          nameWithOwner
        }
        number
        url
        author {
          login
        }
        mergedBy {
         login 
        }
        permalink
        createdAt
        lastEditedAt
        mergedAt
        updatedAt
        state
        additions
        deletions
        changedFiles
        commits {
          totalCount
        }
        baseRef {
          id
        }
        headRef {
          id
        }
        isDraft
        labels (first:100) {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
""".replace("_QUERY_",_QUERY_)



_TYPE_="pr"
_STATE_="open"
_OPEN_QUERY_= f"{_REPOS_} is:{_TYPE_} is:{_STATE_}"

OPEN_ISSUE_QUERY="""
{
  search(first: 75, after: _END_CURSOR_, query: "_OPEN_QUERY_", type: ISSUE) {
    pageInfo {
        startCursor
        hasNextPage
        endCursor
        }
        nodes {
      ... on PullRequest {
        title
        repository {
          name
          nameWithOwner
        }
        number
        url
        author {
          login
        }
        mergedBy {
         login 
        }
        permalink
        createdAt
        lastEditedAt
        mergedAt
        updatedAt
        state
        additions
        deletions
        changedFiles
        commits {
          totalCount
        }
        baseRef {
          id
        }
        headRef {
          id
        }
        isDraft
        labels (first:100) {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
""".replace("_OPEN_QUERY_",_OPEN_QUERY_)


ISSUES_ONLY_QUERY = """
{
  search(first: 75, query: "repo:openedx/credentials is:issue is:open", type: ISSUE) {
    issueCount
    nodes {
      ... on Issue {
        title
        repository {
          name
          nameWithOwner
        }
        number
        url
        author {
          login
        }
        createdAt
        lastEditedAt
        updatedAt
        state
        projectItems(first:10) {
          edges {
            node {
              id
            }
          }
        }
        labels (first:100) {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""


REPOSITORY_QUERY = """
{
  search(first: 75, after: _END_CURSOR_, query: "org:openedx", type: REPOSITORY) {
    repositoryCount
        pageInfo {
          startCursor
          hasNextPage
          endCursor
      } 
      nodes {
        ... on Repository {
          name
          isPrivate
          homepageUrl
          # assignableUsers(first:10) {
          #   edges {
          #     node {
          #       id
          #       login
          #     }
          #   }
          # }
          # labels(first: 20) {
          #   edges {
          #     node {
          #       id
          #     }
          #   }
          # }
          # languages(first: 5) {
          #   edges {
          #     node {
          #       id
          #     }
          #   }
          # }
          updatedAt
          nameWithOwner
          primaryLanguage {
            id
            name
          }
          mergeCommitAllowed
          autoMergeAllowed
          rebaseMergeAllowed
          squashMergeAllowed
          allowUpdateBranch
          milestones {
            edges {
              node {
                id
                description
              }
            }
          }
        }
      }
    }
  }
"""

