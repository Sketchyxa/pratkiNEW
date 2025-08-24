#!/usr/bin/env python3
"""
Простой скрипт для миграции карточек в БД 'pratki'
"""

import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

# Добавляем корневую папку в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

from config import settings


async def migrate_cards():
    """Миграция карточек в новую БД"""
    try:
        # Подключение к БД
        client = AsyncIOMotorClient(settings.mongodb_url)
        old_db = client[settings.database_name]
        new_db = client["pratki"]
        
        logger.info(f"📁 Старая БД: {settings.database_name}")
        logger.info(f"📁 Новая БД: pratki")
        
        # Получаем карточки из старой БД
        old_cards = await old_db["cards"].find({"is_active": True}).to_list(length=None)
        logger.info(f"🎴 Найдено карточек: {len(old_cards)}")
        
        if not old_cards:
            logger.warning("❌ Нет карточек для миграции!")
            return
        
        # Мигрируем в новую БД
        migrated = 0
        for card in old_cards:
            card.pop('_id', None)  # Убираем старый ID
            await new_db["cards"].insert_one(card)
            migrated += 1
        
        logger.info(f"✅ Мигрировано карточек: {migrated}")
        
        # Проверяем результат
        total_new = await new_db["cards"].count_documents({})
        logger.info(f"🎴 Всего в новой БД: {total_new}")
        
        client.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    logger.info("🚀 Миграция карточек в БД 'pratki'...")
    asyncio.run(migrate_cards())
    logger.info("✅ Готово!")
