import asyncio
import os
import sys
from multiprocessing import Process
from typing import Awaitable, Callable

import aiohttp
from src.bots.types import BotCallbacks, BotConfig, BotParams
from src.bots.webrtc.bot_error_pipeline import bot_error_pipeline_task
from src.bots.webrtc.bot_pipeline import bot_pipeline, bot_pipeline_webrtc
from src.bots.webrtc.bot_pipeline_runner import BotPipelineRunner
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection
from src.common.config import SERVICE_API_KEYS
from pipecat.processors.frameworks.rtvi import (
    RTVIObserver,
)
# from src.common.database import DatabaseSessionFactory
from fastapi import HTTPException, status, WebSocket, BackgroundTasks
from loguru import logger
# from sqlalchemy.ext.asyncio import AsyncSession

from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
)
from src.common.config import DEFAULT_BOT_CONFIG, SERVICE_API_KEYS

MAX_SESSION_TIME = int(os.getenv("BOT_MAX_VOICE_SESSION_TIME", 15 * 60)) or 15 * 60


async def _cleanup(room_url: str, config: BotConfig):
    async with aiohttp.ClientSession() as session:
        debug_room = os.getenv("USE_DEBUG_ROOM", None)
        if debug_room:
            return

        transport_api_key = SERVICE_API_KEYS["daily"]

        helper = DailyRESTHelper(
            daily_api_key=str(transport_api_key),
            aiohttp_session=session,
        )

        try:
            logger.info(f"Deleting room {room_url}")
            await helper.delete_room_by_url(room_url)
        except Exception as e:
            logger.error(f"Bot failed to delete room: {e}")


async def _pipeline_task(
    params: BotParams,
    config: BotConfig,
    room_url: str,
    room_token: str,
    websocket: WebSocket,
    pipecat_connection: SmallWebRTCConnection,
    # db: AsyncSession,
) -> Callable[[BotCallbacks], Awaitable[PipelineTask]]:
    async def create_task(callbacks: BotCallbacks) -> PipelineTask:
        pipeline, rtvi = await bot_pipeline(params, config, callbacks, room_url, room_token, websocket, pipecat_connection)

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=False,
                enable_metrics=True,
                send_initial_empty_metrics=False,
            ),
            observers=[RTVIObserver(rtvi)]
        )

        return task

    return create_task


async def _bot_main(
    params: BotParams,
    config: BotConfig,
    room_url: str,
    room_token: str,
    websocket: WebSocket,
):
    # subprocess_session_factory = DatabaseSessionFactory()
    # async with subprocess_session_factory() as db:
        bot_runner = BotPipelineRunner()
        try:
            task_creator = await _pipeline_task(params, config, room_url, room_token, websocket)
            await bot_runner.start(task_creator)
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            task_creator = await bot_error_pipeline_task(
                room_url, room_token, f"Error running bot: {e}"
            )
            await bot_runner.start(task_creator)

        await _cleanup(room_url, config)

        logger.info("Bot has finished. Bye!")
    # await subprocess_session_factory.engine.dispose()


def _bot_process(
    params: BotParams,
    config: BotConfig,
    room_url: str,
    room_token: str,
    websocket: WebSocket,
):
    # This is a different process so we need to make sure we have the right log level.
    logger.remove()
    logger.add(sys.stderr, level=os.getenv("BOT_LOG_LEVEL", "INFO"))

    asyncio.run(_bot_main(params, config, room_url, room_token, websocket))


async def bot_create(daily_api_key: str):
    async with aiohttp.ClientSession() as session:
        daily_rest_helper = DailyRESTHelper(
            daily_api_key=daily_api_key,
            aiohttp_session=session,
        )

        try:
            room = await daily_rest_helper.create_room(params=DailyRoomParams())
            bot_token = await daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)
            user_token = await daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unable to run bot: {e}"
            )

        return room, user_token, bot_token


async def bot_launch(
    params: BotParams,
    config: BotConfig,
    room_url: str,
    room_token: str,
):
    process = Process(target=_bot_process, args=(params, config, room_url, room_token))
    process.start()

async def bot_launch_websocket(
    params: BotParams,
    config: BotConfig,
    websocket: WebSocket,
):
    # process = Process(target=_bot_process, args=(params, config, None, None, websocket))
    # process.start()
    bot_runner = BotPipelineRunner()
    try:
        task_creator = await _pipeline_task(params, config, None, None, websocket)
        await bot_runner.start(task_creator)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        task_creator = await bot_error_pipeline_task(
            room_url, room_token, f"Error running bot: {e}"
        )
        await bot_runner.start(task_creator)

        await _cleanup(room_url, config)
        logger.info("Bot has finished. Bye!")


async def _pipeline_task_webrtc(
    params: BotParams,
    config: BotConfig,
    pipecat_connection: SmallWebRTCConnection,
) -> Callable[[BotCallbacks], Awaitable[PipelineTask]]:
    async def create_task(callbacks: BotCallbacks) -> PipelineTask:
        pipeline, rtvi = await bot_pipeline_webrtc(params, config, callbacks, pipecat_connection)

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                send_initial_empty_metrics=False,
            ),
            observers=[RTVIObserver(rtvi)]
        )

        return task

    return create_task

async def bot_launch_webrtc(
    pipecat_connection: SmallWebRTCConnection,
):
    bot_runner = BotPipelineRunner()
    params = BotParams(
        conversation_id="684fcc587556fc7d2f2a1e66",
        actions=[],
        bot_profile="vision",
        attachments=[],
    )
    config = DEFAULT_BOT_CONFIG
    try:
        task_creator = await _pipeline_task_webrtc(params, config, pipecat_connection)
        await bot_runner.start(task_creator)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        logger.info("Bot has finished. Bye!")
