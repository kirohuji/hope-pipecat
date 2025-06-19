import os
import sys
from contextlib import asynccontextmanager
from typing import Dict
import asyncio

from src.bots.webrtc.bot import bot_launch_websocket, bot_launch_webrtc
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from .api import router as api_router
from pipecat_ai_small_webrtc_prebuilt.frontend import SmallWebRTCPrebuiltUI
# 新增导入
from src.common.database import MongoDB
from src.common.models import Conversation, Message, Attachment
from pipecat.transports.network.webrtc_connection import IceServer, SmallWebRTCConnection

ice_servers = [
    IceServer(
        urls="stun:stun.l.google.com:19302",
    )
]

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level=os.getenv("WEBAPP_LOG_LEVEL", "DEBUG"))

# ========================
# FastAPI App
# ========================

pcs_map: Dict[str, SmallWebRTCConnection] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 初始化 MongoDB/Beanie
        await MongoDB.init([Conversation, Message, Attachment])
        coros = [pc.disconnect() for pc in pcs_map.values()]
        await asyncio.gather(*coros)
        pcs_map.clear()
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        os._exit(1)
    yield
    # MongoDB 不需要像 SQLAlchemy 那样关闭连接，通常直接 yield 即可

app = FastAPI(
    title="Open Sesame API",
    docs_url="/docs",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/prebuilt", SmallWebRTCPrebuiltUI)

app.include_router(api_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def home():
    return "Sesame is running"

@app.post("/api/bot")
async def offer(request: dict, background_tasks: BackgroundTasks):
    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for pc_id: {pc_id}")
        await pipecat_connection.renegotiate(
            sdp=request["sdp"], type=request["type"], restart_pc=request.get("restart_pc", False)
        )
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)

        background_tasks.add_task(bot_launch_webrtc, pipecat_connection)

    answer = pipecat_connection.get_answer()
    # Updating the peer connection inside the map
    pcs_map[answer["pc_id"]] = pipecat_connection

    return answer