from src.bots.http.bot import http_bot_pipeline
from src.bots.types import BotParams
from src.bots.webrtc.bot import bot_create, bot_launch, bot_launch_websocket
from src.common.config import DEFAULT_BOT_CONFIG, SERVICE_API_KEYS
from src.common.models import Attachment, Conversation, Message
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from bson import ObjectId
import json
import urllib.parse

router = APIRouter(prefix="/bot")

@router.post("/action", response_class=StreamingResponse)
async def stream_action(params: BotParams) -> StreamingResponse:
    if not params.conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing conversation_id in params"
        )
        
    config = DEFAULT_BOT_CONFIG
    
    attachments = []
    if params.attachments:
        attachments = await Attachment.find(Attachment.attachment_id.in_(params.attachments)).to_list()

    async def generate():
        messages = await Message.find(Message.conversation_id == params.conversation_id).to_list()
        gen, task = await http_bot_pipeline(params, config, messages, attachments, None)
        async for chunk in gen:
            yield chunk
        await task

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/connect", response_class=JSONResponse)
async def connect(params: BotParams):
    config = DEFAULT_BOT_CONFIG

    # Check which bot profile is requested and return a valid auth bundle to the RTVI client.
    if params.bot_profile == "voice-to-voice":
        return JSONResponse({"success": True})

    if not params.conversation_id:
        logger.error("No conversation ID passed to connect")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing conversation_id in params",
        )

    logger.debug(f"Starting voice bot for conversation {params.conversation_id}")

    # Check that we have a valid daily API key
    transport_api_key = SERVICE_API_KEYS["daily"]

    if not transport_api_key:
        logger.error("Missing API key for transport service")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing API key for transport service",
        )
    
    # 将 BotParams 编码为查询参数
    params_dict = params.dict()
    params_json = json.dumps(params_dict)
    encoded_params = urllib.parse.quote(params_json)
    
    ws_url = f"ws://localhost:7860/api/bot/ws?params={encoded_params}"
    return JSONResponse({"ws_url": ws_url})

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, params: str = Query(None)):
    print(f"params: {params}")
    await websocket.accept()
    print("WebSocket connection accepted")
    
    try:
        # 解码并解析 BotParams
        if params:
            decoded_params = urllib.parse.unquote(params)
            params_dict = json.loads(decoded_params)
            bot_params = BotParams(**params_dict)
            print(f"Received BotParams: {bot_params}")
        else:
            print("No params received in WebSocket connection")
            return
        
        config = DEFAULT_BOT_CONFIG
        await bot_launch_websocket(bot_params, config, websocket)
        
        # 保持 WebSocket 连接活跃
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                print(f"Received message: {data}")
                
                # 这里可以添加消息处理逻辑
                # 例如：将消息转发给 bot pipeline
                
        except Exception as e:
            print(f"WebSocket error: {e}")
            
    except Exception as e:
        print(f"Exception in websocket_endpoint: {e}")
        try:
            await websocket.close()
        except:
            pass


