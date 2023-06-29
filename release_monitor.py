import asyncio
import logging
import re
from asyncio import CancelledError
from http import HTTPStatus
from typing import Optional

import aiohttp
import ujson
from aiogram import Bot
from aiogram.types import ParseMode
from aiohttp.web_runner import GracefulExit

from models import async_session, Repository, UserRepository
from utils import (
    STMT_REPOSITORY,
    GITHUB_API_RELEASE_URL_MASK,
    GITHUB_REPO_URI_PATTERN,
    FETCHING_STEP_PERIOD,
    STMT_REPOSITORY_ID,
    STMT_USER_WITH_REPOSITORIES,
    SURVEY_PERIOD, GITHUB_API_TAGS_URL_MASK, GITHUB_API_RELEASE_TAG_MASK, GITHUB_TAG_URI_PATTERN,
)


async def check_last_blockchain_tag(
    http_session: aiohttp.ClientSession,
    bot: Bot,
    repository_id: int,
):
    async with async_session() as db_session:
        repository = (await db_session.scalars(STMT_REPOSITORY.where(Repository.id == repository_id))).one()

        origin_url = repository.url
        repo_uri = re.findall(GITHUB_REPO_URI_PATTERN, origin_url)[0]
        latest_tag: Optional[str] = None
        tag_url: Optional[str] = None

        # try to get latest release
        api_url = GITHUB_API_RELEASE_URL_MASK.format(repo_uri=repo_uri)
        async with http_session.get(api_url) as response:
            logging.info('Fetching data from %s', api_url)
            result: dict = await response.json(loads=ujson.loads)
            if response.status != HTTPStatus.OK:
                logging.warning('[%s] Failed to fetch data code=%s: %s', origin_url, response.status, await response.text())
            else:
                latest_tag: str = result['tag_name']
                tag_url: str = result['html_url']

        if latest_tag is None and tag_url is None:
            # try to get git refs with tags
            api_url = GITHUB_API_TAGS_URL_MASK.format(repo_uri=repo_uri)
            async with http_session.get(api_url) as response:
                logging.info('Fetching data from %s', api_url)
                result: dict = await response.json(loads=ujson.loads)
                if response.status != HTTPStatus.OK:
                    logging.warning('[%s] Failed to fetch data code=%s: %s', origin_url, response.status, await response.text())
                    return

                last_tag_info = result[-1]
                latest_tag: str = re.findall(GITHUB_TAG_URI_PATTERN, last_tag_info['ref'])[0]
                tag_url: str = GITHUB_API_RELEASE_TAG_MASK.format(repo_uri=repo_uri, tag=latest_tag)

        if repository.latest_tag == latest_tag:
            logging.info('[%s] Tag %s exists', origin_url, latest_tag)
            return

        logging.info('[%s] New tag %s', origin_url, latest_tag)
        repository.latest_tag = latest_tag
        await db_session.commit()

        answer = f'<b>Release tag</b>: {tag_url}'
        for user in await db_session.scalars(STMT_USER_WITH_REPOSITORIES.where(UserRepository.repository_id == repository.id)):
            await bot.send_message(user.external_id, answer, parse_mode=ParseMode.HTML)
            logging.info('[%s] Sending to %s', origin_url, user.external_id)
            # await asyncio.sleep(1)  # to prevent API limits


async def data_collector(bot: Bot):
    async with async_session() as db_session:
        all_repositories = (await db_session.scalars(STMT_REPOSITORY_ID)).all()

    async with aiohttp.ClientSession() as http_session:
        for repository_id in all_repositories:
            try:
                await check_last_blockchain_tag(http_session, bot, repository_id)
            except Exception as ex:
                logging.exception('[%s] Unexpected exception: %r', repository_id, ex, exc_info=ex)
            finally:
                await asyncio.sleep(FETCHING_STEP_PERIOD)


async def run_release_monitor(bot: Bot):
    while True:
        logging.info('Run data collector')
        try:
            await data_collector(bot)
        except (GracefulExit, KeyboardInterrupt, CancelledError):
            logging.info('Close release monitor...')
        except Exception as ex:
            logging.exception('Unexpected exception: %r', ex, exc_info=ex)
        except BaseException as ex:
            logging.critical('Critical exception: %r', ex, exc_info=ex)

        logging.info('Data collector is finished')
        await asyncio.sleep(SURVEY_PERIOD)
