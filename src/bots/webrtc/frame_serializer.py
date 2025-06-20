import base64
import json

from loguru import logger
from pipecat.frames.frames import Frame, TransportMessageUrgentFrame
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType


def encode_response(data: str | dict) -> str:
    data = data if isinstance(data, str) else json.dumps(data)
    encoded = base64.b64encode(data.encode("utf-8")).decode("utf-8")
    return f"data: {encoded}\n\n"


class BotFrameSerializer(ProtobufFrameSerializer):
    def __init__(self):
        super().__init__()

    async def deserialize(self, data: str | bytes) -> Frame | None:
        return await super().deserialize(data)
