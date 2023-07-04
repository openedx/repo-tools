#!/bin/bash

# Function to recursively find and replace the cache backend in files
function update_cache_backend() {
    local root_dir=$1
    find "$root_dir" -type f -exec perl -i -pe 's/django\.core\.cache\.backends\.memcached\.MemcachedCache/django.core.cache.backends.memcached.PyMemcacheCache/g' {} +
}

# Function to find and append "pymemcache" to base.in files
function append_pymemcache() {
    local root_dir=$1
    find "$root_dir" -type f -name "base.in" -exec sh -c 'echo "pymemcache" >> "$0"' {} \;
}

# Function to find and remove the line containing "python-memcached==<version>"
function remove_python_memcached() {
    local root_dir=$1
    find "$root_dir" -type f -exec perl -i -ne 'print unless /^python-memcached==.*$/' {} +
}

# Get the current directory
current_dir=$(pwd)

# Update cache backend in the project
echo "Updating cache backend in project: $current_dir"
update_cache_backend "$current_dir"
echo "Cache backend update completed in project: $current_dir"

# Append "pymemcache" to base.in files
echo "Appending 'pymemcache' to base.in files in project: $current_dir"
append_pymemcache "$current_dir"
echo "Appending 'pymemcache' completed in project: $current_dir"

# Remove lines containing "python-memcached==<version>"
echo "Removing 'python-memcached' lines in project: $current_dir"
remove_python_memcached "$current_dir"
echo "Removal of 'python-memcached' lines completed in project: $current_dir"
