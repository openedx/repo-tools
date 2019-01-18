#!/bin/bash
# 
# Count lines of code in Open edX.
# This certainly over-counts JavaScript code, since we have lots of non-authored
# JavaScript in our repos.
#
# Needs cloc (https://github.com/AlDanial/cloc)

REPORTDIR=/tmp/cloc-reports
mkdir -p $REPORTDIR
rm -rf $REPORTDIR/*

cat <<EOF > $REPORTDIR/exclude-files.txt
package-lock.json
EOF

cat <<EOF > $REPORTDIR/more-langs.txt
reStructured Text
    filter remove_matches xyzzy
    extension rst
    3rd_gen_scale 1.0
SVG Graphics
    filter remove_html_comments
    extension svg
    3rd_gen_scale 1.0
EOF

find . -name .git -type d -prune | while read d; do
    dd=$(dirname "$d")
    if [[ $dd == ./src/third-party/* ]]; then
        # Ignore repos in the "third-party" tree.
        continue;
    fi
    echo "==== $dd ========================================================================================================"
    cd $dd
    git remote -v

    REPORTHEAD=$REPORTDIR/${dd##*/}
    cloc \
        --report-file=$REPORTHEAD.txt \
        --read-lang-def=$REPORTDIR/more-langs.txt \
        --ignored=$REPORTHEAD.ignored \
        --vcs=git \
        --not-match-d='.*\.egg-info' \
        --exclude-dir=node_modules,vendor,locale \
        --exclude-ext=png,jpg,gif,ttf,eot,woff,mo,xcf \
        --exclude-list-file=$REPORTDIR/exclude-files.txt \
        .
    cd -
done

cloc \
    --sum-reports \
    --read-lang-def=$REPORTDIR/more-langs.txt \
    $REPORTDIR/*.txt
