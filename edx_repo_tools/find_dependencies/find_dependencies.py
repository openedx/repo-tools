"""
Spider and catalog dependencies.

$ export OLIVE_DIRS=$(gittreeif origin/open-release/olive.master -q pwd)
$ python find_deps.py $OLIVE_DIRS

"""

import concurrent.futures
import contextlib
import functools
import itertools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path
from typing import Iterable, Optional, Tuple

import requests
from rich.progress import Progress, MofNCompleteColumn

# pylint: disable=unspecified-encoding

cached = functools.lru_cache(maxsize=0)

@contextlib.contextmanager
def change_dir(new_dir):
    """
    Change to a new directory, and then change back.

    Will make the directory if needed.
    """
    old_dir = os.getcwd()
    new_dir = Path(new_dir)
    new_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(new_dir)
    try:
        yield new_dir
    finally:
        os.chdir(old_dir)


def run_command(cmd: str, outfile=None) -> Tuple[bool, str]:
    """
    Run a command line (with no shell).  Write the output to a file.

    Returns a tuple:
        bool: true if the command succeeded.
        str: the output of the command.

    """
    proc = subprocess.run(
        shlex.split(cmd, posix=False),
        shell=False,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = proc.stdout.decode("utf-8")
    if outfile:
        Path(outfile).write_text(output)

    return proc.returncode == 0, output.strip()


@cached
def npm_repo_url(npm_spec: str) -> Optional[str]:
    """Given 'jspkg@0.1.0', return a repo url."""
    pkg, _, ver = npm_spec.rpartition("@")
    url = f"https://registry.npmjs.org/{pkg}/{ver}"
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            print(f"{npm_spec}: {url} -> {resp.status_code}")
            return None
        jdata = resp.json()
    except requests.RequestException as exc:
        print(f"Couldn't fetch npm data for {npm_spec}: {exc}")
        return None
    repo = jdata.get("repository")
    if repo is None:
        return None
    if isinstance(repo, dict):
        repo = repo["url"]
    return repo

def canonical_url(url: str) -> str:
    """Canonicalize a repo URL, probably on GitHub."""
    for pat, repl in [
        (r"^git\+", ""),
        (r"#.$", ""),
        (r"\.git$", ""),
        (r"^git:", "https:"),
        (r"^ssh://git@", "https://"),
        (r"^git@github.com:", "https://github.com/"),
    ]:
        url = re.sub(pat, repl, url)
    if ":" not in url and url.count("/") == 1:
        url = f"https://github.com/{url}"
    return url

@cached
def find_real_url(url: str) -> Optional[str]:
    """Find the eventual real url for a redirected url."""
    while True:
        try:
            resp = requests.head(url, timeout=60)
        except requests.RequestException as exc:
            print(f"Couldn't fetch {url}: {exc}")
            return None
        if resp.status_code == 429:
            # I didn't know you could get 429 from https://github.com, but you can...
            wait = int(resp.headers.get("Retry-After", 10))
            time.sleep(wait + 1)
        else:
            break

    if resp.status_code == 200:
        return resp.url
    return None


WORK_DIR = Path("/tmp/unpack_reqs")

def parallel_map(func, data, description):
    """Run func over data using threads, with a progress bar."""
    data = list(data)
    n_workers = os.cpu_count() or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        with Progress(*Progress.get_default_columns(), MofNCompleteColumn()) as progress:
            pbar = progress.add_task(f"{description:20}", total=len(data))
            for result in executor.map(func, data):
                progress.update(pbar, advance=1)
                yield result

def write_list(path: str, lines: Iterable[str]):
    """Write a list of strings to a file."""
    with Path(path).open("w") as flist:
        for line in lines:
            print(line, file=flist)

def check_js_dependencies() -> Iterable[str]:
    """Check the JS dependencies in package-lock.json, returning a set of repo URLs."""
    print("Checking JavaScript dependencies")
    with Path("package-lock.json").open() as lockf:
        lock_data = json.load(lockf)

    deps = set()
    for name, pkg in lock_data["packages"].items():
        name = pkg.get("name") or name
        name = name.rpartition("node_modules/")[-1]
        version = pkg.get("version")
        if version is None:
            continue
        deps.add(f"{name}@{version}")
    write_list("deps.txt", sorted(deps))

    urls = set()
    for url in parallel_map(npm_repo_url, deps, "Getting npm URLs"):
        if url:
            urls.add(canonical_url(url))

    real_urls = set()
    for url in parallel_map(find_real_url, urls, "Getting real URLs"):
        if url:
            real_urls.add(url)

    print(f"{len(deps)} deps, {len(urls)} urls, {len(real_urls)} real urls")
    write_list("repo_urls.txt", sorted(real_urls))
    return real_urls

def check_py_dependencies() -> Iterable[str]:
    """Check the Python dependencies in base.txt, returning a set of repo URLs."""
    print("Checking Python dependencies")

    print("Creating venv")
    run_command("python3 -m venv .venv", "make_venv.log")
    run_command(".venv/bin/python3 -m pip install -U pip", "pip_upgrade.log")
    print("Downloading packages")
    run_command(".venv/bin/python3 -m pip download --dest files -r base.txt", "pip_download.log")

    urls = set()
    for url in parallel_map(repo_url_from_wheel, Path("files").glob("*.whl"), "Examining wheels"):
        if url:
            urls.add(canonical_url(url))

    for url in parallel_map(repo_url_from_tgz, Path("files").glob("*.tar.gz"), "Examining tar.gz"):
        if url:
            urls.add(canonical_url(url))

    with open("base.txt") as fbase:
        for line in fbase:
            if match := re.search(r"https://github.com[^@ #]*(\.git)?", line):
                urls.add(canonical_url(match[0]))

    real_urls = set()
    for url in parallel_map(find_real_url, urls, "Getting real URLs"):
        if url:
            real_urls.add(url)

    write_list("repo_urls.txt", sorted(real_urls))
    return real_urls

def matching_text(text, regexes):
    """Find a line in text matching a regex, and return the first regex group."""
    for regex in regexes:
        for line in text.splitlines():
            if match := re.search(regex, line):
                return match[1]
    return None

@cached
def repo_url_from_wheel(wheel_path: str) -> Optional[str]:
    """Read metadata from a .whl file, returning the repo URL."""
    with zipfile.ZipFile(wheel_path) as whl_file:
        fmetadata = next((f for f in whl_file.namelist() if f.endswith("/METADATA")), None)
        if fmetadata is None:
            print(f"No metadata in {wheel_path}")
            return None
        with whl_file.open(fmetadata) as inner_file:
            metadata = inner_file.read().decode("utf-8")
        return repo_url_from_metadata(wheel_path, metadata)

@cached
def repo_url_from_tgz(tgz_path: str) -> Optional[str]:
    """Read metadata from a .tar.gz file, returning the repo URL."""
    with tarfile.open(tgz_path) as tgz_file:
        fmetadata = next((f for f in tgz_file.getnames() if f.endswith("/PKG-INFO")), None)
        if fmetadata is None:
            print(f"No metadata in {tgz_path}")
            return None
        metadata = tgz_file.extractfile(fmetadata).read().decode("utf-8")
        return repo_url_from_metadata(tgz_path, metadata)


SOURCE_URL_REGEXES = [
    r"(?i)^Project-URL: Source.*,\s*(.*)$",
    r"(?i)^Home-page: (.*)$",
    r"(?i)^Project-URL: Home.*,\s*(.*)$",
]

def repo_url_from_metadata(filename, metadata):
    """Find the likely source repo URL from PyPI metadata."""
    repo_url = matching_text(metadata, SOURCE_URL_REGEXES)
    if repo_url is None:
        print(f"No repo URL in {filename}")
        return None
    if repo_url == "UNKNOWN":
        print(f"Repo URL is UNKNOWN in {filename}")
        return None
    return repo_url

# The first of these we find is the requirements file we'll examine:
PY_REQS = [
    "requirements/edx/base.txt",
    "requirements/base.txt",
    "requirements.txt",
]

# Files that indicate a repo is a Python project:
PY_INDICATORS = [
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
]

def find_py_reqs():
    """Find the Python requirements file to use."""
    for fname in PY_REQS:
        possible_req = Path(fname)
        if possible_req.exists():
            return possible_req
    if any(Path(ind).exists() for ind in PY_INDICATORS):
        print(f"WARNING: {repo_name} is likely a Python package, but we can't find its dependencies.")
    return None


def process_directory():
    """
    Find all the requirements in the current directory. Returns a set of repo URLs.

    Also copies the considered dependencies file into the temp work directory,
    for later analysis.
    """
    repo_name = Path.cwd().name
    repo_work = WORK_DIR / repo_name
    repo_work.mkdir(parents=True, exist_ok=True)
    repo_urls = set()
    if (js_reqs := Path("package-lock.json")).exists():
        shutil.copyfile(js_reqs, repo_work / "package-lock.json")
        with change_dir(repo_work):
            repo_urls.update(check_js_dependencies())
    if (py_reqs := find_py_reqs()):
        shutil.copyfile(py_reqs, repo_work / "base.txt")
        with change_dir(repo_work):
            repo_urls.update(check_py_dependencies())
    return repo_urls

SECOND_PARTY_ORGS = [
    "edx", "edx-unsupported", "edx-solutions",
    "mitodl",
    "overhangio",
    "open-craft", "eduNEXT", "raccoongang",
]

def main(dirs=None):
    """
    Analyze the requirements in all of the directories mentioned on the command line.
    If arguments have newlines, treat each line as a separate directory.
    """
    if dirs is None:
        dirs = sys.argv[1:]

    print(f"Creating new work directory: {WORK_DIR}")
    shutil.rmtree(WORK_DIR, ignore_errors=True)

    dirs = sorted(itertools.chain.from_iterable(d.splitlines() for d in dirs))
    repo_urls = set()

    for i_dir, repo_dir in enumerate(dirs, start=1):
        print(f"-- repo {repo_dir} ({i_dir}/{len(dirs)}) ----------")
        with change_dir(repo_dir):
            repo_urls.update(process_directory())

    write_list(WORK_DIR / "repo_urls.txt", sorted(repo_urls))

    seconds = sorted(
        url for url in repo_urls
        if any(f"/{org}/" in url for org in SECOND_PARTY_ORGS)
    )
    write_list(WORK_DIR / "second_party_urls.txt", sorted(seconds))

    print("== DONE ==============")
    print("Second-party:")
    print("\n".join(seconds))


if __name__ == "__main__":
    main()
