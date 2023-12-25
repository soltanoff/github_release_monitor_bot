import asyncio
import logging
import os
import re
from asyncio import CancelledError

from aiogram import Bot, Dispatcher, types
from aiohttp.web_runner import GracefulExit

from models import Repository, User, UserRepository, async_session
from release_monitor import run_release_monitor
from utils import (
    COMMAND_LIST,
    GITHUB_PATTERN,
    STMT_REPOSITORY,
    STMT_USER_REPOSITORY,
    STMT_USER_SUBSCRIPTION,
    special_command_handler,
)


dp = Dispatcher()


@special_command_handler(dp, command='start', description='base command for user registration')
@special_command_handler(dp, command='help', description='view all commands')
async def send_welcome(_: types.Message, __: User) -> str:
    return '\n'.join(COMMAND_LIST)


@special_command_handler(dp, command='my_subscriptions', description='view all subscriptions', disable_web_page_preview=True)
async def my_subscriptions(_: types.Message, user: User) -> str:
    async with async_session() as session:
        answer = ''
        repositories = await session.scalars(STMT_USER_SUBSCRIPTION.where(UserRepository.user_id == user.id))
        for repository in repositories:
            answer += f'\n{repository.latest_tag if repository.latest_tag else "<fetch in progress>"} - {repository.url}'

        return f'Subscriptions: {answer if answer else "empty"}'


@special_command_handler(
    dp,
    command='subscribe',
    description='[github repo urls] subscribe to the new GitHub repository',
    skip_empty_messages=True,
)
async def subscribe(message: types.Message, user: User) -> str:
    async with async_session() as session:
        for repository_url in message.text.split():
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
                logging.info('Subscribe user %s to %s', user.id, repository_url)

        await session.commit()

    return 'Successfully subscribed!'


@special_command_handler(
    dp,
    command='unsubscribe',
    description='[github repo urls] unsubscribe from the GitHub repository',
    skip_empty_messages=True,
)
async def unsubscribe(message: types.Message, user: User) -> str:
    async with async_session() as session:
        for repository_url in message.text.split():
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
                logging.info('Unsubscribe user %s from %s', user.id, repository_url)

        await session.commit()

    return 'Successfully unsubscribed!'


@special_command_handler(dp, command='remove_all_subscriptions', description='remove all exists subscriptions')
async def remove_all_subscriptions(_: types.Message, user: User) -> str:
    async with async_session() as session:
        user_repositories = await session.scalars(STMT_USER_REPOSITORY.where(UserRepository.user_id == user.id))
        for user_repository in user_repositories:
            await session.delete(user_repository)

        logging.info('Full unsubscribe for user %s', user.id)
        await session.commit()

    return 'Successfully unsubscribed!'


async def main():
    bot = Bot(token=os.getenv('TELEGRAM_API_KEY'))
    asyncio.create_task(run_release_monitor(bot))

    try:
        await dp.start_polling(bot)
    except Exception as error:
        logging.exception('Unexpected error: %r', error, exc_info=error)
    except (GracefulExit, KeyboardInterrupt, CancelledError):
        logging.info('Exit...')


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)9s | %(asctime)s | %(name)30s | %(filename)20s | %(lineno)6s | %(message)s',
        force=True,
    )
    asyncio.run(main())
