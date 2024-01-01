import asyncio
import logging
from asyncio import CancelledError

import aiohttp
from aiogram.enums import ParseMode
from aiohttp.web_runner import GracefulExit

import db_helper
import settings
from bot_controller import BotController
from models import Repository, UserRepository, async_session
from release_monitor.services import github


async def check_last_repository_tag(
    http_session: aiohttp.ClientSession,
    bot_controller: BotController,
    repository: Repository,
):
    latest_tag, tag_url = await github.get_latest_tag_from_release_uri(http_session, repository.short_name)
    if latest_tag is None and tag_url is None:
        latest_tag, tag_url = await github.get_latest_tag_from_tag_uri(http_session, repository.short_name)

    if latest_tag is None:
        logging.error("[%s] Tag is NONE?", repository.short_name)
        return

    if repository.latest_tag == latest_tag:
        logging.info("[%s] Tag %s exists", repository.short_name, latest_tag)
        return

    async with async_session() as db_session:
        await db_helper.update_repository_latest_tag(db_session, repository, latest_tag)
        answer = f"<b>Release tag</b>: {tag_url}"
        for user in await db_session.scalars(db_helper.STMT_USER_WITH_REPOSITORIES.where(UserRepository.repository_id == repository.id)):
            await bot_controller.send_message(user.external_id, answer, parse_mode=ParseMode.HTML)
            logging.info("[%s] Sending to %s", repository.short_name, user.external_id)


async def data_collector(bot_controller: BotController):
    async with async_session() as db_session:
        all_repositories = (await db_session.scalars(db_helper.STMT_REPOSITORY)).all()

    async with aiohttp.ClientSession() as http_session:
        for repository in all_repositories:
            try:
                await check_last_repository_tag(http_session, bot_controller, repository)
            except Exception as ex:
                logging.exception("[%s] Unexpected exception: %r", repository.short_name, ex, exc_info=ex)
            finally:
                await asyncio.sleep(settings.FETCHING_STEP_PERIOD)


async def run_release_monitor(bot_controller: BotController):
    while True:
        logging.info("Run data collector")
        try:
            await data_collector(bot_controller)
        except (GracefulExit, KeyboardInterrupt, CancelledError):
            logging.info("Close release monitor...")
            return
        except Exception as ex:
            logging.exception("Unexpected exception: %r", ex, exc_info=ex)
        except BaseException as ex:
            logging.critical("Critical exception: %r", ex, exc_info=ex)

        logging.info("Data collector is finished")
        await asyncio.sleep(settings.SURVEY_PERIOD)
