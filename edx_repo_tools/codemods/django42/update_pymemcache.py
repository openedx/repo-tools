import click
import subprocess


def main():
    """
    Function to call the bash script which is replacing all 
    django.core.cache.backends.memcached.MemcachedCache references with
    django.core.cache.backends.memcached.PyMemcacheCache in the whole
    project and adding pymemcache and removing python-memcached in requirements
    """
    subprocess.run(['./edx_repo_tools/codemods/django42/script_to_update_pymemcache.sh'])


if __name__ == '__main__':
    main()
