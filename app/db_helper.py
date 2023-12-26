import logging

import sqlalchemy as sa
from aiogram import types
from sqlalchemy.ext.asyncio import AsyncSession

from models import Repository, User, UserRepository


# Common prebuilt queries
STMT_USER = sa.select(User)
STMT_REPOSITORY = sa.select(Repository)
STMT_USER_REPOSITORY = sa.select(UserRepository)
STMT_USER_SUBSCRIPTION = sa.select(Repository).join(UserRepository)
STMT_USER_WITH_REPOSITORIES = sa.select(User).join(UserRepository)


async def get_or_create_user(session: AsyncSession, message: types.Message) -> User:
    user_id = message.from_user.id
    user = (await session.scalars(STMT_USER.where(User.external_id == user_id))).one_or_none()
    if user is None:
        user = User()
        user.external_id = user_id
        await session.merge(user)
        await session.commit()
        logging.info("[%s] New user %s", user.id, user.external_id)

    return user


async def update_repository_latest_tag(session: AsyncSession, repository: Repository, latest_tag: str) -> None:
    session.add(repository)
    repository.latest_tag = latest_tag
    await session.merge(repository)
    await session.commit()
    logging.info("[%s] New tag %s", repository.id, latest_tag)


async def make_subscription(session: AsyncSession, user: User, repository_url: str) -> None:
    repository = (await session.scalars(STMT_REPOSITORY.where(Repository.url == repository_url))).one_or_none()
    if repository is None:
        repository = Repository()
        repository.url = repository_url
        session.add(repository)
        await session.flush()
        logging.info(
            "Repository `%s` doesn't exists: create new repository url",
            repository_url,
        )

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
        logging.info("Subscribe user %s to %s", user.id, repository_url)


async def make_unsubscription(session: AsyncSession, user: User, repository_url: str) -> None:
    repository = (await session.scalars(STMT_REPOSITORY.where(Repository.url == repository_url))).one_or_none()
    if repository is None:
        logging.info("Repository `%s` doesn't exists: skip", repository_url)
        return

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
        logging.info("Unsubscribe user %s from %s", user.id, repository_url)


async def remove_all_subscriptions(session: AsyncSession, user: User) -> None:
    user_repositories = await session.scalars(STMT_USER_REPOSITORY.where(UserRepository.user_id == user.id))
    for user_repository in user_repositories:
        await session.delete(user_repository)

    logging.info("Full unsubscribe for user %s", user.id)
