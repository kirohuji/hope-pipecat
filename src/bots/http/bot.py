import asyncio
from typing import Any, AsyncGenerator, List, Tuple
import os
from src.bots.http.frame_serializer import BotFrameSerializer
from src.bots.persistent_context import PersistentContext
from src.bots.rtvi import create_rtvi_processor
from src.bots.types import BotConfig, BotParams
from src.common.config import SERVICE_API_KEYS
from src.common.models import Attachment, Message
from fastapi import HTTPException, status
from loguru import logger
from openai._types import NOT_GIVEN

import uuid

from base64 import b64decode
from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.async_generator import AsyncGeneratorProcessor
from pipecat.processors.frameworks.rtvi import (
    RTVIConfig,
    RTVIActionRun,
    RTVIMessage,
    RTVIProcessor,
    RTVIObserver,
)
from pipecat.services.deepseek.llm import DeepSeekLLMService
# from pipecat.services.ai_services import OpenAILLMContext
# from pipecat.services.google import GoogleLLMContext, GoogleLLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.google.llm import GoogleLLMContext, GoogleLLMService

def flatten_content(content_list):
    # 如果是 [{"type": "text", "text": "你好"}] => "你好"
    if isinstance(content_list, list):
        return ''.join([item.get("text", "") for item in content_list])
    return content_list  # already a string

def is_valid_base64(s: str) -> bool:
    """检查字符串是否为有效的base64编码"""
    try:
        # 检查是否只包含base64字符
        import re
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', s):
            return False
        # 尝试解码
        b64decode(s)
        return True
    except Exception:
        return False

def decrypt_cryptojs(ciphertext_b64: str, password: str) -> str:
    # 如果不是有效的base64，直接返回原字符串
    if not is_valid_base64(ciphertext_b64):
        return ciphertext_b64
    
    try:
        # Base64 解码
        encrypted = b64decode(ciphertext_b64)

        # 提取 salt
        assert encrypted[:8] == b"Salted__", "不是 CryptoJS 默认加密格式"
        salt = encrypted[8:16]
        ciphertext = encrypted[16:]

        # 兼容 CryptoJS/OpenSSL 的 EVP_BytesToKey 方式，生成 key 和 iv
        key_iv = b''
        prev = b''
        while len(key_iv) < 48:  # 32字节key + 16字节IV = 48
            prev = md5(prev + password.encode('utf-8') + salt).digest()
            key_iv += prev
        key = key_iv[:32]
        iv = key_iv[32:48]

        # AES 解密
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)

        # 去除 PKCS7 Padding
        return unpad(decrypted, AES.block_size).decode('utf-8')
    except Exception as e:
        # 如果解密失败，返回原字符串
        logger.warning(f"解密失败，返回原字符串: {e}")
        return ciphertext_b64

async def http_bot_pipeline(
    params: BotParams,
    config: BotConfig,
    messages,
    attachments: List[Attachment],
    language_code: str = "english",
) -> Tuple[AsyncGenerator[Any, None], Any]:
    llm_api_key = SERVICE_API_KEYS.get("gemini")
    if llm_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service `llm` not available in SERVICE_API_KEYS. Please check your environment variables.",
        )

    # llm = GoogleLLMService(
    #     api_key=str(SERVICE_API_KEYS["gemini"]),
    #     model="gemini-2.0-flash-exp",
    # )
    llm = DeepSeekLLMService(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
            model="deepseek-chat",
    )

    tools = NOT_GIVEN
    if isinstance(llm, DeepSeekLLMService):
        converted_messages = []
        for msg in messages:
            converted_msg = {
                "role": "user" if msg.userId == params.user_id else "assistant",
                "content": decrypt_cryptojs(msg.body, "future")
            }
            converted_messages.append(converted_msg)
        context = OpenAILLMContext(converted_messages)
    else:
        context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)
    # Terrible hack. Fix this by making create_context_aggregator downcast the context
    # automatically. But think through that code first to make sure there won't be
    # any unintended consequences.
    # if isinstance(llm, GoogleLLMService):
    #     GoogleLLMContext.upgrade_to_google(context)
    user_aggregator = context_aggregator.user()
    assistant_aggregator = context_aggregator.assistant()

    storage = PersistentContext(context=context)

    async_generator = AsyncGeneratorProcessor(serializer=BotFrameSerializer())

    #
    # RTVI
    #

    rtvi = await create_rtvi_processor(config, user_aggregator)

    processors = [
        rtvi,
        user_aggregator,
        storage.create_processor(),
        llm,
        async_generator,
        assistant_aggregator,
        storage.create_processor(exit_on_endframe=True),
    ]

    pipeline = Pipeline(processors)

    runner = PipelineRunner(handle_sigint=False)

    task = PipelineTask(pipeline,  observers=[RTVIObserver(rtvi)])

    runner_task = asyncio.create_task(runner.run(task))

    @storage.on_context_message
    async def on_context_message(messages: list[Any]):
        try:
            for msg in messages:
                # 根据消息角色决定用户ID
                if msg.get('role') == 'user':
                    user_id = str(params.user_id)  # 确保转换为字符串
                else:
                    user_id = str(params.participant_id)  # 将ObjectId转换为字符串

                message_id = str(uuid.uuid4())
                
                message_doc = Message(
                    id=message_id,  # 明确设置字符串ID
                    conversation_id=str(params.conversation_id),  # 确保转换为字符串
                    body=msg['content'],
                    userId=user_id,  # 使用正确的字段名
                    contentType="text",
                )
                await message_doc.insert()
        except Exception as e:
            logger.error(f"Error storing messages: {e}")
            # 添加更详细的错误信息
            logger.error(f"Error details: {type(e)} - {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise e

    @rtvi.event_handler("on_bot_started")
    async def on_bot_started(rtvi: RTVIProcessor):
        for action in params.actions:
            logger.debug(f"Processing action: {action}")

            # If this is an append_to_messages action, we need to append any
            # attachments. The rule we'll follow is that we should append
            # attachments to the first "user" message in the actions list.
            if action.data.get("action") == "append_to_messages" and attachments:
                for msg in action.data["arguments"][0]["value"]:
                    if msg.get("role") == "user":
                        # Append attachments to this message
                        logger.debug(
                            f"Appending {len(attachments)} attachment(s) to 'user' message"
                        )
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            content = [{"type": "text", "text": content}]
                        for attachment in attachments:
                            # Assume for the moment that all attachments are images
                            content.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{attachment.file_type};base64,{attachment.file_data}"
                                    },
                                }
                            )
                            await attachment.delete()
                        break

            await rtvi.handle_message(action)

        # This is a single turn, so we just push an action to stop the running
        # pipeline task.
        action = RTVIActionRun(service="system", action="end")
        message = RTVIMessage(type="action", id="END", data=action.model_dump())
        await rtvi.handle_message(message)

    return (async_generator.generator(), runner_task)
