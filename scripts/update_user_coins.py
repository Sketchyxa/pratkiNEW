#!/usr/bin/env python3
"""
Скрипт для обновления монет у существующих пользователей
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.user_service import user_service
from loguru import logger

async def update_user_coins():
    """Обновляет монеты у существующих пользователей"""
    print("🔧 Обновление монет у пользователей...")
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        print("✅ Подключение к базе данных успешно")
        
        # Получаем всех пользователей
        all_users = await user_service.get_all_users()
        print(f"✅ Найдено {len(all_users)} пользователей")
        
        updated_count = 0
        for user in all_users:
            # Если у пользователя меньше 600 монет, устанавливаем 600
            if user.coins < 600:
                old_coins = user.coins
                user.coins = 600
                await user_service.update_user(user)
                updated_count += 1
                print(f"✅ Пользователь {user.telegram_id}: {old_coins} → 600 монет")
        
        print(f"\n✅ Обновление завершено! Обновлено {updated_count} пользователей из {len(all_users)}")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Отключаемся от базы данных
        await db.disconnect()
        print("🔌 Отключение от базы данных")


if __name__ == "__main__":
    asyncio.run(update_user_coins())
