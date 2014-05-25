import collections

from pulls import get_pulls


def show_wall():
    issues = get_pulls("edx/edx-platform", state="open")
    blocked_by = collections.defaultdict(list)
    for issue in issues:
        issue.finish_loading()
        for label in issue['labels']:
            if label == "osc":
                continue
            blocked_by[label].append(issue)

    shame = sorted(blocked_by.items(), key=lambda li: len(li[1]), reverse=True)
    print("team,external,internal,extlines,intlines")
    for label, issues in shame:
        internal, external = [0, 0], [0, 0]
        for iss in issues:
            lines = iss['pull.additions'] + iss['pull.deletions']
            stats = external if "osc" in iss['labels'] else internal
            stats[0] += 1
            stats[1] += lines
        print("{}\t{}\t{}\t{}\t{}".format(
            label, external[0], internal[0], external[1], internal[1]
        ))


if __name__ == "__main__":
    show_wall()
