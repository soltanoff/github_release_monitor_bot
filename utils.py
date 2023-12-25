import logging
import os
import re
from datetime import timedelta

import sqlalchemy as sa
from aiogram import types

from models import Repository, User, UserRepository, async_session


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
