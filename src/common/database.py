import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from loguru import logger

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://dev:dev@localhost:27017/dev")

class MongoDB:
    _client: AsyncIOMotorClient = None
    _initialized: bool = False

    @classmethod
    async def init(cls, document_models: list):
        if cls._initialized:
            return
        cls._client = AsyncIOMotorClient(MONGODB_URL)
        await init_beanie(database=cls._client.get_default_database(), document_models=document_models)
        cls._initialized = True
        logger.info("MongoDB (Beanie) initialized.")

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls._client is None:
            raise RuntimeError("MongoDB client not initialized")
        return cls._client
