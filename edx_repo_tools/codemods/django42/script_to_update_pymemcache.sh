#!/bin/bash

# Function to recursively find and replace the cache backend in files
function update_cache_backend() {
    local root_dir=$1
    find "$root_dir" -type f -exec perl -i -pe 's/django\.core\.cache\.backends\.memcached\.MemcachedCache/django.core.cache.backends.memcached.PyMemcacheCache/g' {} +
}

# Get the current directory
current_dir=$(pwd)

# Update cache backend in the project
echo "Updating cache backend in project: $current_dir"
update_cache_backend "$current_dir"
echo "Cache backend update completed in project: $current_dir"
