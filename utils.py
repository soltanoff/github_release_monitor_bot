import logging
import os
import re
from datetime import timedelta
from functools import wraps
from typing import Callable, List

import sqlalchemy as sa
from aiogram import Dispatcher, types
from aiogram.filters import Command

from models import Repository, User, UserRepository, async_session


COMMAND_LIST: List[str] = []
# Special timeout to prevent Telegram API timeouts and limits
SLEEP_AFTER_EXCEPTION = timedelta(minutes=1).seconds
# Main timing config to prevent GitHub API limits
SURVEY_PERIOD = int(os.getenv('SURVEY_PERIOD') or timedelta(hours=1).seconds)
FETCHING_STEP_PERIOD = int(os.getenv('FETCHING_STEP_PERIOD') or timedelta(minutes=1).seconds)

# RegExp pattern for checking user input
GITHUB_PATTERN = re.compile(r'^https:\/\/github\.com\/[\w-]+\/[\w-]+$')  # noqa
# For example: https://api.github.com/repos/algorand/go-algorand/releases/latest
GITHUB_REPO_URI_PATTERN = re.compile(r'^https:\/\/github\.com\/([\w-]+\/[\w-]+)$')  # noqa
GITHUB_TAG_URI_PATTERN = re.compile(r'refs\/tags\/([\w\d\-\.]+)')  # noqa
GITHUB_API_RELEASE_URL_MASK = 'https://api.github.com/repos/{repo_uri}/releases/latest'
GITHUB_API_TAGS_URL_MASK = 'https://api.github.com/repos/{repo_uri}/git/refs/tags'
GITHUB_API_RELEASE_TAG_MASK = 'https://github.com/{repo_uri}/releases/tag/{tag}'

# Common prebuilt queries
STMT_USER = sa.select(User)
STMT_REPOSITORY = sa.select(Repository)
STMT_USER_REPOSITORY = sa.select(UserRepository)
STMT_USER_SUBSCRIPTION = sa.select(Repository).join(UserRepository)
STMT_USER_WITH_REPOSITORIES = sa.select(User).join(UserRepository)


def special_command_handler(
    dispatcher: Dispatcher,
    command: str,
    description: str,
    skip_empty_messages: bool = False,
    disable_web_page_preview: bool = False,
) -> Callable:
    def decorator(callback: Callable) -> Callable:
        @wraps(callback)
        async def wrapper(message: types.Message) -> None:
            await message.bot.send_chat_action(message.chat.id, 'typing')

            if skip_empty_messages:
                request_message: str = message.text[len(command) + 1:].strip()
                if not request_message:
                    await message.reply('Empty message?')
                    return

            log_bot_incomming_message(message)
            user = await get_or_create_user(message)
            answer = await callback(message, user)
            log_bot_outgoing_message(message, answer)

            await message.reply(
                text=answer,
                disable_web_page_preview=disable_web_page_preview,
            )

        dispatcher.message(Command(command))(wrapper)
        COMMAND_LIST.append(f'/{command} - {description}')
        return callback

    return decorator


async def get_or_create_user(message: types.Message) -> User:
    async with async_session() as session:
        user_id = message.from_user.id
        user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
        if user is None:
            user = User()
            user.external_id = user_id
            await session.merge(user)
            await session.commit()

        return user


def log_bot_incomming_message(message: types.Message):
    logging.info(
        'User[%s|%s:@%s]: %r',
        message.chat.id,
        message.from_user.id,
        message.from_user.username,
        message.text,
    )


def log_bot_outgoing_message(message: types.Message, answer: str):
    logging.info(
        '<<< User[%s|%s:@%s]: %r',
        message.chat.id,
        message.from_user.id,
        message.from_user.username,
        answer,
    )
