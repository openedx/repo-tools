cd ../repo-tools-data
git pull
cd ../repo-tools
source venv/bin/activate
python monthly_pr_stats.py --start=6/1/2015
python pull_quarters.py --monthly --start=6/1/2015
python transitions_kpi.py --all --since=30
python pull_orgs.py --since=31 --short

