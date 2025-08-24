#!/usr/bin/env python3
"""
Скрипт для миграции данных из старой базы MongoDB в новую
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger


async def migrate_database():
    """Миграция данных из старой базы в новую"""
    try:
        logger.info("Starting database migration...")
        
        # Подключение к старой базе данных
        old_client = AsyncIOMotorClient("mongodb://localhost:27017")
        old_db = old_client.pratki  # или как называется ваша старая база
        
        # Подключение к новой базе данных
        new_client = AsyncIOMotorClient("mongodb://localhost:27017")
        new_db = new_client.pratki_bot  # новая база из config.py
        
        # Мигрируем карточки
        logger.info("Migrating cards...")
        old_cards = old_db.cards.find({})
        cards_count = 0
        async for card in old_cards:
            # Удаляем _id чтобы MongoDB создал новый
            card.pop('_id', None)
            await new_db.cards.insert_one(card)
            cards_count += 1
        logger.info(f"Migrated {cards_count} cards")
        
        # Мигрируем пользователей
        logger.info("Migrating users...")
        old_users = old_db.users.find({})
        users_count = 0
        async for user in old_users:
            # Удаляем _id чтобы MongoDB создал новый
            user.pop('_id', None)
            await new_db.users.insert_one(user)
            users_count += 1
        logger.info(f"Migrated {users_count} users")
        
        # Мигрируем достижения
        logger.info("Migrating achievements...")
        old_achievements = old_db.achievements.find({})
        achievements_count = 0
        async for achievement in old_achievements:
            # Удаляем _id чтобы MongoDB создал новый
            achievement.pop('_id', None)
            await new_db.achievements.insert_one(achievement)
            achievements_count += 1
        logger.info(f"Migrated {achievements_count} achievements")
        
        # Мигрируем события
        logger.info("Migrating events...")
        old_events = old_db.events.find({})
        events_count = 0
        async for event in old_events:
            # Удаляем _id чтобы MongoDB создал новый
            event.pop('_id', None)
            await new_db.events.insert_one(event)
            events_count += 1
        logger.info(f"Migrated {events_count} events")
        
        # Мигрируем другие коллекции если есть
        collections_to_migrate = ['battles', 'shop_items', 'notifications', 'suggestions']
        for collection_name in collections_to_migrate:
            if collection_name in await old_db.list_collection_names():
                logger.info(f"Migrating {collection_name}...")
                old_items = old_db[collection_name].find({})
                items_count = 0
                async for item in old_items:
                    # Удаляем _id чтобы MongoDB создал новый
                    item.pop('_id', None)
                    await new_db[collection_name].insert_one(item)
                    items_count += 1
                logger.info(f"Migrated {items_count} {collection_name}")
        
        # Закрываем соединения
        old_client.close()
        new_client.close()
        
        logger.info("Database migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


async def main():
    """Главная функция"""
    try:
        await migrate_database()
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
