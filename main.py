import asyncio
import logging
import os
import re
import time
from asyncio import Task, CancelledError
from functools import partial
from typing import List

from aiogram import Bot, Dispatcher, executor, types
from aiohttp.web_runner import GracefulExit

from models import async_session, User, Repository, UserRepository
from release_monitor import run_release_monitor
from utils import (
    special_command_handler,
    COMMAND_LIST,
    STMT_USER,
    STMT_REPOSITORY,
    STMT_USER_REPOSITORY,
    STMT_USER_SUBSCRIPTION,
    GITHUB_PATTERN,
    SLEEP_AFTER_EXCEPTION,
)

# Telegram
bot = Bot(token=os.getenv('TELEGRAM_API_KEY'))
dp = Dispatcher(bot)
# Background task collection for graceful shutdown
BACKGROUND_TASKS: List[Task] = []


@special_command_handler(dp, command='start', description='base command for user registration')
@special_command_handler(dp, command='help', description='view all commands')
async def send_welcome(message: types.Message):
    chat_id: int = message.chat.id
    user_id: str = message.from_user.id
    username: str = message.from_user.username
    request_message: str = message.text

    await message.answer_chat_action('typing')
    logging.info('User[%s|%s:@%s]: %r', chat_id, user_id, username, request_message)

    async with async_session() as session:
        user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
        if user is None:
            user = User()
            user.external_id = user_id
            session.add(user)
            await session.commit()

    commands = '\n'.join(COMMAND_LIST)
    await message.reply(f'Well, hello! Check all commands below:\n{commands}')


@special_command_handler(dp, command='my_subscriptions', description='view all subscriptions')
async def my_subscriptions(message: types.Message):
    chat_id: int = message.chat.id
    user_id: str = message.from_user.id
    username: str = message.from_user.username
    request_message: str = message.text

    await message.answer_chat_action('typing')
    logging.info('User[%s|%s:@%s]: %r', chat_id, user_id, username, request_message)

    async with async_session() as session:
        user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
        if user is None:
            logging.info('User[%s|%s:@%s] doesn\'t exists: skip', chat_id, user_id, username)
            await message.reply('You were not subscribed before')
            return

        answer = ''
        repositories = await session.scalars(STMT_USER_SUBSCRIPTION.where(UserRepository.user_id == user.id))
        for repository in repositories:
            answer += f'\n{repository.latest_tag if repository.latest_tag else "<fetch in progress>"} - {repository.url}'

        await message.reply(
            text=f'Subscriptions: {answer if answer else "empty"}',
            disable_web_page_preview=True,
        )


@special_command_handler(
    dp,
    command='subscribe',
    description='[github repo urls] subscribe to the new GitHub repository',
    skip_empty_messages=True,
)
async def subscribe(message: types.Message):
    chat_id: int = message.chat.id
    user_id: str = message.from_user.id
    username: str = message.from_user.username
    request_message: str = message.text

    await message.answer_chat_action('typing')
    logging.info('User[%s|%s:@%s]: %r', chat_id, user_id, username, request_message)

    async with async_session() as session:
        user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
        if user is None:
            user = User()
            user.external_id = user_id
            session.add(user)
            await session.flush()
            logging.info('User[%s|%s:@%s] doesn\'t exists: create new user', chat_id, user_id, username)

        for repository_url in request_message.split():
            if not re.fullmatch(GITHUB_PATTERN, repository_url):
                logging.warning('Repository skipped by check: %s', repository_url)
                continue

            repository = (await session.scalars(STMT_REPOSITORY.where(Repository.url == repository_url))).one_or_none()
            if repository is None:
                repository = Repository()
                repository.url = repository_url
                session.add(repository)
                await session.flush()
                logging.info('Repository `%s` doesn\'t exists: create new repository url', repository_url)

            user_repository = (
                await session.scalars(
                    STMT_USER_REPOSITORY.where(
                        UserRepository.user_id == user.id,
                        UserRepository.repository_id == repository.id,
                    )
                )
            ).one_or_none()
            if user_repository is None:
                user_repository = UserRepository()
                user_repository.user = user
                user_repository.repository = repository
                session.add(user_repository)
                logging.info('Subscribe user[%s|%s:@%s] to %s', chat_id, user_id, username, repository_url)

        await session.commit()

    answer = 'Successfully subscribed!'
    logging.info('<<< User[%s|%s:@%s]: %r', chat_id, user_id, username, answer)
    await message.reply(answer)


@special_command_handler(
    dp,
    command='unsubscribe',
    description='[github repo urls] unsubscribe from the GitHub repository',
    skip_empty_messages=True,
)
async def unsubscribe(message: types.Message):
    chat_id: int = message.chat.id
    user_id: str = message.from_user.id
    username: str = message.from_user.username
    request_message: str = message.text

    await message.answer_chat_action('typing')
    logging.info('User[%s|%s:@%s]: %r', chat_id, user_id, username, request_message)

    async with async_session() as session:
        user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
        if user is None:
            logging.info('User[%s|%s:@%s] doesn\'t exists: skip', chat_id, user_id, username)
            await message.reply('You were not subscribed before')
            return

        for repository_url in request_message.split():
            if not re.fullmatch(GITHUB_PATTERN, repository_url):
                logging.warning('Repository skipped by check: %s', repository_url)
                continue

            repository = (await session.scalars(STMT_REPOSITORY.where(Repository.url == repository_url))).one_or_none()
            if repository is None:
                logging.info('Repository `%s` doesn\'t exists: skip', repository_url)
                continue

            user_repository = (
                await session.scalars(
                    STMT_USER_REPOSITORY.where(
                        UserRepository.user_id == user.id,
                        UserRepository.repository_id == repository.id,
                    )
                )
            ).one_or_none()
            if user_repository:
                await session.delete(user_repository)
                logging.info('Unsubscribe user[%s|%s:@%s] from %s', chat_id, user_id, username, repository_url)

        await session.commit()

    answer = 'Successfully unsubscribed!'
    logging.info('<<< User[%s|%s:@%s]: %r', chat_id, user_id, username, answer)
    await message.reply(answer)


@special_command_handler(dp, command='remove_all_subscriptions', description='remove all exists subscriptions')
async def remove_all_subscriptions(message: types.Message):
    chat_id: int = message.chat.id
    user_id: str = message.from_user.id
    username: str = message.from_user.username
    request_message: str = message.text

    await message.answer_chat_action('typing')
    logging.info('User[%s|%s:@%s]: %r', chat_id, user_id, username, request_message)

    async with async_session() as session:
        user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
        if user is None:
            logging.info('User[%s|%s:@%s] doesn\'t exists: skip', chat_id, user_id, username)
            await message.reply('You were not subscribed before')
            return

        user_repositories = await session.scalars(STMT_USER_REPOSITORY.where(UserRepository.user_id == user.id))
        for user_repository in user_repositories:
            await session.delete(user_repository)

        logging.info('Full unsubscribe for user[%s|%s:@%s]', chat_id, user_id, username)

        await session.commit()

    answer = 'Successfully unsubscribed!'
    logging.info('<<< User[%s|%s:@%s]: %r', chat_id, user_id, username, answer)
    await message.reply(answer)


async def on_startup(background_task: List[Task], bot_instance: Bot, _: Dispatcher):
    background_task.append(asyncio.create_task(run_release_monitor(bot_instance)))


async def on_shutdown(background_task: List[Task], _: Dispatcher):
    for task in background_task:
        try:
            task.cancel()
        except BaseException as task_error:
            logging.warning('%r: %r', task, task_error, exc_info=task_error)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)9s | %(asctime)s | %(name)30s | %(filename)20s | %(lineno)6s | %(message)s',
        force=True,
    )

    while True:
        try:
            executor.start_polling(
                dp,
                skip_updates=False,
                on_startup=partial(on_startup, BACKGROUND_TASKS, bot),
                on_shutdown=partial(on_shutdown, BACKGROUND_TASKS),
            )
        except Exception as error:
            logging.exception('Error found: %r. Restarting...', error, exc_info=error)
            time.sleep(SLEEP_AFTER_EXCEPTION)
        except (GracefulExit, KeyboardInterrupt, CancelledError):
            logging.info('Exit...')
