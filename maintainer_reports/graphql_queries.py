_REPOS_ = "repo:openedx/edx-platform repo:openedx/xblock-lti-consumer repo:openedx/blockstore repo:openedx/course-discovery repo:openedx/credentials repo:openedx/DoneXBlock repo:openedx/ecommerce repo:openedx/ecommerce-worker repo:openedx/edx-ace repo:openedx/edx-rest-api-client repo:openedx/frontend-app-ecommerce repo:openedx/frontend-app-payment repo:openedx/frontend-app-publisher repo:openedx/openedx-events repo:openedx/RateXBlock"

_TYPE_="pr"
_STATE_="closed"
_QUERY_= f"{_REPOS_} is:{_TYPE_} is:{_STATE_} closed:_RANGE_"

CLOSED_ISSUE_QUERY="""
{
  search(first: 100, after: _END_CURSOR_, query: "_QUERY_", type: ISSUE) {
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
  search(first: 100, after: _END_CURSOR_, query: "_OPEN_QUERY_", type: ISSUE) {
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
  search(first: 100, query: "repo:openedx/credentials is:issue is:open", type: ISSUE) {
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
  search(first: 100, after: _END_CURSOR_, query: "org:openedx", type: REPOSITORY) {
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