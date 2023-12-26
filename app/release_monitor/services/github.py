import logging
import re
from http import HTTPStatus
from operator import itemgetter
from typing import List, Optional, Tuple

import aiohttp
import ujson


GITHUB_TAG_URI_PATTERN = re.compile(r"refs\/tags\/([\w\d\-\.]+)")  # noqa
GITHUB_API_RELEASE_URL_MASK = "https://api.github.com/repos/{repo_uri}/releases/latest"
GITHUB_API_TAGS_URL_MASK = "https://api.github.com/repos/{repo_uri}/git/refs/tags"
GITHUB_API_RELEASE_TAG_MASK = "https://github.com/{repo_uri}/releases/tag/{tag}"


async def get_latest_tag_from_release_uri(http_session: aiohttp.ClientSession, repo_uri: str) -> Tuple[Optional[str], Optional[str]]:
    latest_tag: Optional[str] = None
    tag_url: Optional[str] = None
    # try to get the latest release
    api_url = GITHUB_API_RELEASE_URL_MASK.format(repo_uri=repo_uri)
    async with http_session.get(api_url) as response:
        logging.info("Fetching data from %s", api_url)
        result: dict = await response.json(loads=ujson.loads)
        if response.status != HTTPStatus.OK:
            logging.warning(
                "[%s] Failed to fetch data code=%s: %s",
                repo_uri,
                response.status,
                await response.text(),
            )
            return latest_tag, tag_url

        latest_tag: str = result["tag_name"]
        tag_url: str = result["html_url"]

    return latest_tag, tag_url


async def get_latest_tag_from_tag_uri(http_session: aiohttp.ClientSession, repo_uri: str) -> Tuple[Optional[str], Optional[str]]:
    latest_tag: Optional[str] = None
    tag_url: Optional[str] = None
    # try to get git refs with tags
    api_url = GITHUB_API_TAGS_URL_MASK.format(repo_uri=repo_uri)
    async with http_session.get(api_url) as response:
        logging.info("Fetching data from %s", api_url)
        result: List = await response.json(loads=ujson.loads)
        if response.status != HTTPStatus.OK:
            logging.warning(
                "[%s] Failed to fetch data code=%s: %s",
                repo_uri,
                response.status,
                await response.text(),
            )
            return latest_tag, tag_url

        result.sort(key=itemgetter("ref"))
        last_tag_info = result[-1]
        latest_tag = re.findall(GITHUB_TAG_URI_PATTERN, last_tag_info["ref"])[0]
        tag_url = GITHUB_API_RELEASE_TAG_MASK.format(repo_uri=repo_uri, tag=latest_tag)

    return latest_tag, tag_url
