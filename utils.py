import os
import re
from datetime import timedelta
from functools import wraps
from typing import Callable, List

import sqlalchemy as sa
from aiogram import Dispatcher, types

from models import User, Repository, UserRepository

COMMAND_LIST: List[str] = []
# Special timeout for prevent to Telegram API timeouts and limits
SLEEP_AFTER_EXCEPTION = timedelta(minutes=1).seconds
# Main timing config for prevent to GitHub API limits
SURVEY_PERIOD = int(os.getenv('SURVEY_PERIOD') or timedelta(hours=1).seconds)
FETCHING_STEP_PERIOD = int(os.getenv('FETCHING_STEP_PERIOD') or timedelta(minutes=1).seconds)

# RegExp pattern for checking user input
GITHUB_PATTERN = re.compile(r'^https:\/\/github\.com\/\w+\/\w+$')  # noqa
# For example: https://api.github.com/repos/algorand/go-algorand/releases/latest
GITHUB_REPO_URI_PATTERN = re.compile(r'^https:\/\/github\.com\/(\w+\/\w+)$')  # noqa
GITHUB_API_URL_MASK = 'https://api.github.com/repos/{repo_uri}/releases/latest'

# Common prebuilt queries
STMT_USER = sa.select(User)
STMT_REPOSITORY = sa.select(Repository)
STMT_USER_REPOSITORY = sa.select(UserRepository)
STMT_USER_SUBSCRIPTION = sa.select(Repository).join(UserRepository)
STMT_REPOSITORY_ID = sa.select(Repository.id).join(UserRepository)
STMT_USER_WITH_REPOSITORIES = sa.select(User).join(UserRepository)


def special_command_handler(
    dispatcher: Dispatcher,
    command: str,
    description: str,
    skip_empty_messages: bool = False,
) -> Callable:
    def decorator(callback: Callable) -> Callable:
        @wraps(callback)
        async def wrapper(message: types.Message) -> None:
            if skip_empty_messages:
                request_message: str = message.text[len(command) + 1:].strip()
                if not request_message:
                    await message.reply('Empty message?')
                    return

            await callback(message)

        dispatcher.message_handler(commands=[command])(wrapper)
        COMMAND_LIST.append(f'/{command} - {description}')
        return callback

    return decorator
