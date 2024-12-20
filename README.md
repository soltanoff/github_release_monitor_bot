# GitHub Release Monitor bot

[![\[Telegram\] aiogram live](https://img.shields.io/badge/telegram-aiogram-blue.svg?style=flat-square)](https://t.me/aiogram_live)
[![Supported python versions](https://img.shields.io/pypi/pyversions/aiogram.svg?style=flat-square)](https://pypi.python.org/pypi/aiogram)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-8.0-blue.svg?style=flat-square&logo=telegram)](https://core.telegram.org/bots/api)
[![MIT License](https://img.shields.io/pypi/l/aiogram.svg?style=flat-square)](https://opensource.org/licenses/MIT)

Simple release monitor for GitHub repositories based on telegram bot.

You may try it on telegram - [here](http://t.me/github_release_monitor_bot) :)

## Command list

- `/help` - view all commands
- `/start` - base command for user registration
- `/my_subscriptions` - view all subscriptions
- `/subscribe` - \[github repo urls] subscribe to the new GitHub repository
- `/unsubscribe` - \[github repo urls] unsubscribe from the GitHub repository
- `/remove_all_subscriptions` - remove all exists subscriptions

<details><summary>Examples here</summary>
<code>/subscribe https://github.com/sqlalchemy/sqlalchemy</code>

FYI: bot will send you info about updates automatically.

![subscribe_example.jpg](assets%2Fsubscribe_example.jpg)

![fetch_example.jpg](assets%2Ffetch_example.jpg)

</details>

## Config and environments variable

Config based on `.env` creation or set env-variables as you like (example: [.env.default](.env.default))

### `TELEGRAM_API_KEY`

- Find [BotFather](https://t.me/BotFather) account
- Create a new bot
- Generate API token and put it to config

### `SURVEY_PERIOD`

This parameter is used to set the polling frequency for all url addresses. Default 1 hour.

### `FETCHING_STEP_PERIOD`

This setting is used to set a timeout between each API request to prevent the rate limit from failing. Default 1 minute.

## How to run

### Without Docker:

- Make virtual environment
- Install package requirements
- Create `.env` or set env-variables as you like (example: [.env.default](.env.default))
- Run it

### With Docker

- Create `.env` or set env-variables as you like (example: [.env.default](.env.default)
  and see [docker-compose.yml](docker-compose.yml))
- Run it!

## Development tools

### Bandit tool

[Bandit](https://github.com/PyCQA/bandit) is a tool designed to find common security issues in Python code. To do this
Bandit processes each file, builds an AST from it, and runs appropriate plugins against the AST nodes. Once Bandit has
finished scanning all the files it generates a report.

```shell
bandit -c pyproject.toml -r .
```

### Safety tool

[safety](https://pyup.io/safety/) is a tool designed to check installed dependencies for known security vulnerabilities.

```shell
# how to check all installed packages
safety check --policy-file .safety-policy.yml

# how to check all dependencies
safety check -r requirements_dev.txt --policy-file .safety-policy.yml

# json report 
mkdir -p reports/safety && safety check -r requirements_dev.txt --policy-file .safety-policy.yml --json --output reports/safety/result.json
```

### flake8

[flake8](https://github.com/PyCQA/flake8) is a python tool that glues together pycodestyle, pyflakes, mccabe, and
third-party plugins to check the style and quality of some python code.

```shell
flake8 .
```

### pylint

[pylint](https://github.com/pylint-dev/pylint) - static code analyzer for Python 2 or 3. It checks
presence of bugs, enforces the coding standard, tries to find problems in the code and can suggest suggestions
code refactoring.

```shell
pylint $(git ls-files '*.py')
```

## My subscriptions

- https://github.com/sqlalchemy/sqlalchemy
- https://github.com/soltanoff/github_release_monitor_bot
- https://github.com/python/cpython
- https://github.com/pylint-dev/pylint
- https://github.com/PyCQA/flake8
- https://github.com/john-hen/Flake8-pyproject
- https://github.com/pyupio/safety
- https://github.com/python-greenlet/greenlet
- https://github.com/aiogram/aiogram
- https://github.com/python-poetry/poetry
- https://github.com/sqlalchemy/alembic
- https://github.com/ultrajson/ultrajson
- https://github.com/MagicStack/uvloop
- https://github.com/encode/uvicorn
- https://github.com/tiangolo/fastapi
- https://github.com/aio-libs/aiohttp
- https://github.com/django/django
- https://github.com/encode/django-rest-framework
- https://github.com/pyca/cryptography
- https://github.com/pytest-dev/pytest
- https://github.com/nedbat/coveragepy
- https://github.com/redis/redis-py
- https://github.com/sparckles/robyn
- https://github.com/PyCQA/bandit
- https://github.com/litestar-org/litestar
- https://github.com/jd/tenacity
- https://github.com/aminalaee/sqladmin
- https://github.com/wagtail/wagtail
- https://github.com/zmievsa/cadwyn
- https://github.com/litestar-org/litestar-pg-redis-docker
- https://github.com/bigskysoftware/htmx
- https://github.com/Bogdanp/dramatiq
- https://github.com/jcrist/msgspec
- https://github.com/ijl/orjson
- https://github.com/PrefectHQ/prefect
