import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from config import settings
from loguru import logger


class MongoDB:
    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls) -> None:
        """Подключение к MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(settings.mongodb_url)
            cls.database = cls.client[settings.database_name]
            
            # Проверяем соединение
            await cls.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB at {settings.mongodb_url}")
            
            # Создаем индексы
            await cls._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Отключение от MongoDB"""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")

    @classmethod
    async def _create_indexes(cls) -> None:
        """Создание индексов для оптимизации запросов"""
        try:
            # Индексы для пользователей
            await cls.database.users.create_index("telegram_id", unique=True)
            await cls.database.users.create_index("username")
            await cls.database.users.create_index("experience")
            await cls.database.users.create_index("level")
            await cls.database.users.create_index("last_activity")
            
            # Индексы для карточек
            await cls.database.cards.create_index("name", unique=True)
            await cls.database.cards.create_index("rarity")
            await cls.database.cards.create_index("is_active")
            await cls.database.cards.create_index("total_owned")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Failed to create some indexes: {e}")

    @classmethod
    def get_collection(cls, collection_name: str) -> AsyncIOMotorCollection:
        """Получение коллекции по имени"""
        if cls.database is None:
            raise RuntimeError("Database not connected")
        return cls.database[collection_name]

    @classmethod
    async def get_stats(cls) -> dict:
        """Получение статистики базы данных"""
        if cls.database is None:
            return {}
            
        try:
            stats = await cls.database.command("dbStats")
            collections_info = {
                "users": await cls.database.users.count_documents({}),
                "cards": await cls.database.cards.count_documents({}),
            }
            
            return {
                "database_name": stats.get("db"),
                "collections": collections_info,
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Глобальный экземпляр для удобства
db = MongoDB()
