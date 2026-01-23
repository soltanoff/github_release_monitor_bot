import logging
import re

from aiogram import types
from sqlalchemy.ext.asyncio import AsyncSession

import db_helper
import settings
from bot_controller.router import Router
from db_helper import STMT_USER_SUBSCRIPTION
from models import User, UserRepository

router = Router(name=__name__)


@router.register(
    command="start",
    description="base command for user registration",
)
@router.register(
    command="help",
    description="view all commands",
)
async def send_welcome(*_) -> str:
    return "\n".join(router.command_list)


@router.register(
    command="my_subscriptions",
    description="view all subscriptions",
)
async def my_subscriptions(message: types.Message, session: AsyncSession, user: User) -> None:
    answer = ""
    repositories = await session.scalars(STMT_USER_SUBSCRIPTION.where(UserRepository.user_id == user.id))
    for repository in repositories:
        answer += f'\n{repository.latest_tag if repository.latest_tag else "<fetch in progress>"} - {repository.url}'

    answer = f'Subscriptions: {answer if answer else "empty"}'
    await message.reply(text=answer, disable_web_page_preview=True)


@router.register(
    command="subscribe",
    description="[github repo urls] subscribe to the new GitHub repository",
    skip_empty_messages=True,
)
async def subscribe(message: types.Message, session: AsyncSession, user: User) -> str:
    for repository_url in message.text.split():
        matches = re.findall(settings.GITHUB_PATTERN, repository_url)
        if not matches:
            logging.warning("Repository skipped by check: %s", repository_url)
            continue

        await db_helper.make_subscription(session, user, repository_url, short_name=matches[0])

    await session.commit()
    return "Successfully subscribed!"


@router.register(
    command="unsubscribe",
    description="[github repo urls] unsubscribe from the GitHub repository",
    skip_empty_messages=True,
)
async def unsubscribe(message: types.Message, session: AsyncSession, user: User) -> str:
    for repository_url in message.text.split():
        if not re.fullmatch(settings.GITHUB_PATTERN, repository_url):
            logging.warning("Repository skipped by check: %s", repository_url)
            continue

        await db_helper.make_unsubscription(session, user, repository_url)

    await session.commit()
    return "Successfully unsubscribed!"


@router.register(
    command="remove_all_subscriptions",
    description="remove all exists subscriptions",
)
async def remove_all_subscriptions(_: types.Message, session: AsyncSession, user: User) -> str:
    await db_helper.remove_all_subscriptions(session, user)
    await session.commit()
    return "Successfully unsubscribed!"


@router.register()
async def no_hello(*_) -> str:
    return "Say /help"
