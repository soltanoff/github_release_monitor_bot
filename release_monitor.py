import asyncio
import logging
import re
from asyncio import CancelledError
from http import HTTPStatus
from operator import itemgetter
from typing import List, Optional, Tuple

import aiohttp
import ujson
from aiogram.enums import ParseMode
from aiohttp.web_runner import GracefulExit

from bot_controller import BotController
from models import Repository, UserRepository, async_session
from utils import (
    FETCHING_STEP_PERIOD,
    GITHUB_API_RELEASE_TAG_MASK,
    GITHUB_API_RELEASE_URL_MASK,
    GITHUB_API_TAGS_URL_MASK,
    GITHUB_REPO_URI_PATTERN,
    GITHUB_TAG_URI_PATTERN,
    STMT_REPOSITORY,
    STMT_USER_WITH_REPOSITORIES,
    SURVEY_PERIOD,
)


async def get_latest_tag_from_release_uri(http_session: aiohttp.ClientSession, repo_uri: str) -> Tuple[Optional[str], Optional[str]]:
    latest_tag: Optional[str] = None
    tag_url: Optional[str] = None
    # try to get the latest release
    api_url = GITHUB_API_RELEASE_URL_MASK.format(repo_uri=repo_uri)
    async with http_session.get(api_url) as response:
        logging.info('Fetching data from %s', api_url)
        result: dict = await response.json(loads=ujson.loads)
        if response.status != HTTPStatus.OK:
            logging.warning('[%s] Failed to fetch data code=%s: %s', repo_uri, response.status, await response.text())
            return latest_tag, tag_url

        latest_tag: str = result['tag_name']
        tag_url: str = result['html_url']

    return latest_tag, tag_url


async def get_latest_tag_from_tag_uri(http_session: aiohttp.ClientSession, repo_uri: str) -> Tuple[Optional[str], Optional[str]]:
    latest_tag: Optional[str] = None
    tag_url: Optional[str] = None
    # try to get git refs with tags
    api_url = GITHUB_API_TAGS_URL_MASK.format(repo_uri=repo_uri)
    async with http_session.get(api_url) as response:
        logging.info('Fetching data from %s', api_url)
        result: List = await response.json(loads=ujson.loads)
        if response.status != HTTPStatus.OK:
            logging.warning('[%s] Failed to fetch data code=%s: %s', repo_uri, response.status, await response.text())
            return latest_tag, tag_url

        result.sort(key=itemgetter('ref'))
        last_tag_info = result[-1]
        latest_tag: str = re.findall(GITHUB_TAG_URI_PATTERN, last_tag_info['ref'])[0]
        tag_url: str = GITHUB_API_RELEASE_TAG_MASK.format(repo_uri=repo_uri, tag=latest_tag)

    return latest_tag, tag_url


async def update_repository_latest_tag(repository: Repository, latest_tag: str):
    async with async_session() as db_session:
        db_session.add(repository)
        repository.latest_tag = latest_tag
        await db_session.merge(repository)
        await db_session.commit()
        logging.info('[%s] New tag %s', repository.id, latest_tag)


async def send_tag_update_to_all_subscribers(bot_controller: BotController, repository: Repository, tag_url: str):
    answer = f'<b>Release tag</b>: {tag_url}'
    async with async_session() as db_session:
        for user in await db_session.scalars(STMT_USER_WITH_REPOSITORIES.where(UserRepository.repository_id == repository.id)):
            await bot_controller.send_message(user.external_id, answer, parse_mode=ParseMode.HTML)
            logging.info('[%s] Sending to %s', repository.id, user.external_id)


async def check_last_repository_tag(
    http_session: aiohttp.ClientSession,
    bot_controller: BotController,
    repository: Repository,
):
    repo_uri = re.findall(GITHUB_REPO_URI_PATTERN, repository.url)[0]

    latest_tag, tag_url = await get_latest_tag_from_release_uri(http_session, repo_uri)
    if latest_tag is None and tag_url is None:
        latest_tag, tag_url = await get_latest_tag_from_tag_uri(http_session, repo_uri)

    if repository.latest_tag == latest_tag:
        logging.info('[%s] Tag %s exists', repository.id, latest_tag)
        return

    await update_repository_latest_tag(repository, latest_tag)
    await send_tag_update_to_all_subscribers(bot_controller, repository, tag_url)


async def data_collector(bot_controller: BotController):
    async with async_session() as db_session:
        all_repositories = (await db_session.scalars(STMT_REPOSITORY)).all()

    async with aiohttp.ClientSession() as http_session:
        for repository in all_repositories:
            try:
                await check_last_repository_tag(http_session, bot_controller, repository)
            except Exception as ex:
                logging.exception('[%s] Unexpected exception: %r', repository.id, ex, exc_info=ex)
            finally:
                await asyncio.sleep(FETCHING_STEP_PERIOD)


async def run_release_monitor(bot_controller: BotController):
    while True:
        logging.info('Run data collector')
        try:
            await data_collector(bot_controller)
        except (GracefulExit, KeyboardInterrupt, CancelledError):
            logging.info('Close release monitor...')
            return
        except Exception as ex:
            logging.exception('Unexpected exception: %r', ex, exc_info=ex)
        except BaseException as ex:
            logging.critical('Critical exception: %r', ex, exc_info=ex)

        logging.info('Data collector is finished')
        await asyncio.sleep(SURVEY_PERIOD)
