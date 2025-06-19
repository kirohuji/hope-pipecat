from typing import Any
import os
from src.bots.persistent_context import PersistentContext
from src.bots.rtvi import create_rtvi_processor
from src.bots.types import BotCallbacks, BotConfig, BotParams
from src.common.config import SERVICE_API_KEYS
from src.common.models import Conversation, Message
from loguru import logger
from openai._types import NOT_GIVEN
from deepgram import LiveOptions
# from sqlalchemy.ext.asyncio import AsyncSession
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.services.deepseek.llm import DeepSeekLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.processors.frameworks.rtvi import (
    # RTVIConfig,
    RTVIActionRun,
    RTVIMessage,
    # RTVIProcessor,
    # RTVIObserver,
)
from pipecat.processors.frame_processor import FrameDirection
# from pipecat.processors.frameworks.rtvi import (
#     # RTVIBotLLMProcessor,
#     RTVIBotTranscriptionProcessor,
#     RTVIBotTTSProcessor,
#     RTVISpeakingProcessor,
#     RTVIUserTranscriptionProcessor,
# )
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.gemini_multimodal_live.gemini import (
    GeminiMultimodalLiveLLMService,
)
# from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from fastapi import WebSocket

def flatten_content(content_list):
    # 如果是 [{"type": "text", "text": "你好"}] => "你好"
    if isinstance(content_list, list):
        return ''.join([item.get("text", "") for item in content_list])
    return content_list  # already a string

async def bot_pipeline(
    params: BotParams,
    config: BotConfig,
    callbacks: BotCallbacks,
    room_url: str,
    room_token: str,
    websocket: WebSocket,
    pipecat_connection: SmallWebRTCConnection,
) -> Pipeline:
    # transport = DailyTransport(
    #     room_url,
    #     room_token,
    #     "Gemini Bot",
    #     DailyParams(
    #         audio_in_sample_rate=16000,
    #         audio_out_enabled=True,
    #         audio_out_sample_rate=24000,
    #         transcription_enabled=False,
    #         vad_enabled=True,
    #         vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
    #         vad_audio_passthrough=True,
    #     ),
    # )

    # transport = FastAPIWebsocketTransport(
    #     websocket=websocket,
    #     params=FastAPIWebsocketParams(
    #         audio_in_sample_rate=16000,
    #         audio_out_sample_rate=24000,
    #         audio_in_enabled=True,
    #         audio_out_enabled=True,
    #         add_wav_header=False,
    #         vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
    #         serializer=ProtobufFrameSerializer(),
    #     ),
    # )
    transport_params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_out_10ms_chunks=2,
        video_in_enabled=True,
        video_out_enabled=True,
        video_out_is_live=True,
        vad_analyzer=SileroVADAnalyzer(),
    )
    transport = SmallWebRTCTransport(
        webrtc_connection=pipecat_connection, params=transport_params
    )

    conversation = await Conversation.get(params.conversation_id)
    if not conversation:
        raise Exception(f"Conversation {params.conversation_id} not found")
    # messages = [getattr(msg, "content") for msg in conversation.messages]
    messages = [msg.content for msg in await Message.find(Message.conversation_id == params.conversation_id).to_list()]

    #
    # RTVI
    #

    # stt = DeepgramSTTService(
    #     api_key=os.getenv("DEEPGRAM_API_KEY"),
    #     live_options=LiveOptions(
    #         vad_events=True,
    #     ),
    # )
    # llm_rt = DeepSeekLLMService(
    #     api_key=os.getenv("DEEPSEEK_API_KEY"),
    #         model="deepseek-chat",
    # )
    # tts = CartesiaTTSService(
    #     api_key=os.getenv("CARTESIA_API_KEY"),
    #         voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
    #         # language=Language.ZH,
    # )
    llm_rt = GeminiMultimodalLiveLLMService(
        api_key=str(SERVICE_API_KEYS["gemini"]),
        voice_id="Aoede",  # Puck, Charon, Kore, Fenrir, Aoede
        # system_instruction="Talk like a pirate."
        transcribe_user_audio=True,
        transcribe_model_audio=True,
        inference_on_context_initialization=False,
    )

    tools = NOT_GIVEN  # todo: implement tools in and set here
    context_rt = OpenAILLMContext(messages, tools)
    if isinstance(llm_rt, DeepSeekLLMService):
        for msg in messages:
            msg["content"] = flatten_content(msg["content"])
        context_rt = OpenAILLMContext(messages)
    else:
        context_rt = OpenAILLMContext(messages, tools)
    context_aggregator_rt = llm_rt.create_context_aggregator(context_rt)
    user_aggregator = context_aggregator_rt.user()
    assistant_aggregator = context_aggregator_rt.assistant()
    await llm_rt.set_context(context_rt)
    # storage = PersistentContext(context=context_rt)

    rtvi = await create_rtvi_processor(config, user_aggregator)

    processors = [
        transport.input(),
        # stt,
        user_aggregator,
        rtvi,
        llm_rt,
        # tts,
        transport.output(),
        assistant_aggregator,
        # storage.create_processor(exit_on_endframe=True),
    ]

    pipeline = Pipeline(processors)

    # @storage.on_context_message
    # async def on_context_message(messages: list[Any]):
    #     logger.debug(f"{len(messages)} message(s) received for storage")
    #     try:
    #         # await Message.create_messages(
    #         #     db_session=db, conversation_id=params.conversation_id, messages=messages
    #         # )
    #         max_msg = await Message.find(Message.conversation_id == params.conversation_id).sort(-Message.message_number).first_or_none()
    #         new_number = (max_msg.message_number if max_msg else 0) + 1

    #         for msg in messages:
    #             # msg 应该是 dict，且有 role 和 content 字段
    #             message_doc = Message(
    #                 conversation_id=params.conversation_id,
    #                 content=msg,  # 这里 msg 是 dict
    #                 message_number=new_number,
    #                 language_code=language_code or "unknown",  # 补全为字符串
    #             )
    #             await message_doc.insert()
    #             new_number += 1
    #     except Exception as e:
    #         logger.error(f"Error storing messages: {e}")
    #         raise e

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        # for message in params.actions:
        #     await rtvi.handle_message(message)

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        # Enable both camera and screenshare. From the client side
        # send just one.
        await transport.capture_participant_video(
            participant["id"], framerate=1, video_source="camera"
        )
        await transport.capture_participant_video(
            participant["id"], framerate=1, video_source="screenVideo"
        )
        await callbacks.on_first_participant_joined(participant)

    @transport.event_handler("on_participant_joined")
    async def on_participant_joined(transport, participant):
        await callbacks.on_participant_joined(participant)

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        await callbacks.on_participant_left(participant, reason)

    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        await callbacks.on_call_state_updated(state)

    return (pipeline , rtvi)

async def bot_pipeline_webrtc(
    params: BotParams,
    config: BotConfig,
    callbacks: BotCallbacks,
    pipecat_connection: SmallWebRTCConnection,
) -> Pipeline:
    transport_params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
        # audio_in_enabled=True,
        # audio_out_enabled=True,
        # audio_out_10ms_chunks=2,
        # video_in_enabled=True,
        # video_out_enabled=True,
        # video_out_is_live=True,
        # vad_analyzer=SileroVADAnalyzer(),
    )
    transport = SmallWebRTCTransport(
        webrtc_connection=pipecat_connection, params=transport_params
    )

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options=LiveOptions(
            vad_events=True,
        ),
    )
    llm_rt = DeepSeekLLMService(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
            model="deepseek-chat",
    )
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
            # language=Language.ZH,
    )

    context_rt = OpenAILLMContext(
        [
            {
                "role": "user",
                "content": "Start by greeting the user warmly and introducing yourself.",
            }
        ],
    )

    context_aggregator_rt = llm_rt.create_context_aggregator(context_rt)
    user_aggregator = context_aggregator_rt.user()
    assistant_aggregator = context_aggregator_rt.assistant()

    rtvi = await create_rtvi_processor(config, user_aggregator)

    processors = [
        transport.input(),
        rtvi,
        stt,
        user_aggregator,
        llm_rt,
        tts,
        transport.output(),
        assistant_aggregator,
        # storage.create_processor(exit_on_endframe=True),
    ]

    pipeline = Pipeline(processors)

    # @rtvi.event_handler("on_bot_started")
    # async def on_bot_started(rtvi):
    #     for action in params.actions:
    #         logger.debug(f"Processing action: {action}")
    #         await rtvi.handle_message(action)
    #     action = RTVIActionRun(service="system", action="end")
    #     message = RTVIMessage(type="action", id="END", data=action.model_dump())
    #     await rtvi.handle_message(message)

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        # await rtvi.queue_frames([context_aggregator_rt.user().get_context_frame()])
        # for message in params.actions:
        #     await rtvi.handle_message(message)

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        # Enable both camera and screenshare. From the client side
        # send just one.
        await transport.capture_participant_video(
            participant["id"], framerate=1, video_source="camera"
        )
        await transport.capture_participant_video(
            participant["id"], framerate=1, video_source="screenVideo"
        )
        await callbacks.on_first_participant_joined(participant)

    @transport.event_handler("on_participant_joined")
    async def on_participant_joined(transport, participant):
        await callbacks.on_participant_joined(participant)

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        await callbacks.on_participant_left(participant, reason)

    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        await callbacks.on_call_state_updated(state)

    return (pipeline , rtvi)
