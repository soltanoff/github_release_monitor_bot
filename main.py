import asyncio
import logging
import os

from bot_controller import BotController
from release_monitor import run_release_monitor


async def main():
    bot_controller = BotController(os.getenv('TELEGRAM_API_KEY'))
    asyncio.create_task(run_release_monitor(bot_controller))
    await bot_controller.start()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)9s | %(asctime)s | %(name)30s | %(filename)20s | %(lineno)6s | %(message)s',
        force=True,
    )
    asyncio.run(main())
