import os
import re
from datetime import timedelta


DB_NAME = "db.sqlite3"
# Main timing config to prevent GitHub API limits
SURVEY_PERIOD = int(os.getenv("SURVEY_PERIOD") or timedelta(hours=1).seconds)
FETCHING_STEP_PERIOD = int(os.getenv("FETCHING_STEP_PERIOD") or timedelta(minutes=1).seconds)
# RegExp pattern for checking user input
GITHUB_PATTERN = re.compile(r"^https:\/\/github\.com\/([\w-]+\/[\w-]+)$")  # noqa
