#!/bin/bash

# Pass the Directory you want to replace the occurences in, as first argument.
# e.g bash script_to_replace_static.sh Workspace/credentials
DIR="$1"
# Type of files to repalce in
SEARCH="*.html"

for f in $(find $DIR -name "$SEARCH" -type f); do
	echo "Replacing in $f"
	# Creating backup file because sed creates empty file when output is in same file as input.
	cp $f $f.bak
	sed 's/{% load staticfiles %}/{% load static %}/g' $f.bak > $f
	cp $f $f.bak
	sed 's/{% load admin_static %}/{% load static %}/g' $f.bak > $f
	# Deleting bakup file
	rm -f $f.bak
done
