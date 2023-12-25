import logging
import re
from asyncio import CancelledError
from typing import Callable, List

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiohttp.web_runner import GracefulExit

import utils
from models import Repository, User, UserRepository, async_session
from utils import GITHUB_PATTERN, STMT_REPOSITORY, STMT_USER_REPOSITORY, STMT_USER_SUBSCRIPTION


class BotController:
    def __init__(self, telegram_api_key: str):
        self._bot = Bot(token=telegram_api_key)
        self._dispatcher = Dispatcher()
        self._command_list: List[str] = []

        self._register_handler(
            command='start',
            description='base command for user registration',
            command_handler=self.send_welcome,
        )
        self._register_handler(
            command='help',
            description='view all commands',
            command_handler=self.send_welcome,
        )
        self._register_handler(
            command='my_subscriptions',
            description='view all subscriptions',
            disable_web_page_preview=True,
            command_handler=self.my_subscriptions,
        )
        self._register_handler(
            command='subscribe',
            description='[github repo urls] subscribe to the new GitHub repository',
            skip_empty_messages=True,
            command_handler=self.subscribe,
        )
        self._register_handler(
            command='unsubscribe',
            description='[github repo urls] unsubscribe from the GitHub repository',
            skip_empty_messages=True,
            command_handler=self.unsubscribe,
        )
        self._register_handler(
            command='remove_all_subscriptions',
            description='remove all exists subscriptions',
            command_handler=self.remove_all_subscriptions,
        )

    async def start(self):
        try:
            await self._dispatcher.start_polling(self._bot)
        except Exception as error:
            logging.exception('Unexpected error: %r', error, exc_info=error)
        except (GracefulExit, KeyboardInterrupt, CancelledError):
            logging.info('Bot graceful shutdown...')

    async def send_message(self, user_external_id: int, answer: str, parse_mode=ParseMode.HTML):
        await self._bot.send_message(user_external_id, answer, parse_mode=parse_mode)

    async def send_welcome(self, _: types.Message, __: User) -> str:
        return '\n'.join(self._command_list)

    @staticmethod
    async def my_subscriptions(_: types.Message, user: User) -> str:
        async with async_session() as session:
            answer = ''
            repositories = await session.scalars(STMT_USER_SUBSCRIPTION.where(UserRepository.user_id == user.id))
            for repository in repositories:
                answer += f'\n{repository.latest_tag if repository.latest_tag else "<fetch in progress>"} - {repository.url}'

            return f'Subscriptions: {answer if answer else "empty"}'

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    async def remove_all_subscriptions(_: types.Message, user: User) -> str:
        async with async_session() as session:
            user_repositories = await session.scalars(STMT_USER_REPOSITORY.where(UserRepository.user_id == user.id))
            for user_repository in user_repositories:
                await session.delete(user_repository)

            logging.info('Full unsubscribe for user %s', user.id)
            await session.commit()

        return 'Successfully unsubscribed!'

    def _register_handler(
        self,
        command: str,
        description: str,
        command_handler: Callable,
        skip_empty_messages: bool = False,
        disable_web_page_preview: bool = False,
    ):
        async def wrapper(message: types.Message) -> None:
            await message.bot.send_chat_action(message.chat.id, 'typing')

            if skip_empty_messages:
                request_message: str = message.text[len(command) + 1:].strip()
                if not request_message:
                    await message.reply('Empty message?')
                    return

            utils.log_bot_incomming_message(message)
            user = await utils.get_or_create_user(message)
            answer = await command_handler(message, user)
            utils.log_bot_outgoing_message(message, answer)

            await message.reply(
                text=answer,
                disable_web_page_preview=disable_web_page_preview,
            )

        self._dispatcher.message(Command(command))(wrapper)
        self._command_list.append(f'/{command} - {description}')
