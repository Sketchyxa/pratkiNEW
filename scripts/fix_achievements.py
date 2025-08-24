#!/usr/bin/env python3
"""
Скрипт для исправления достижений уровня у всех пользователей
Запускается один раз для проверки и выдачи всех пропущенных достижений
"""

import asyncio
import sys
import os

# Добавляем корневую папку в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.user_service import user_service
from services.achievement_service import achievement_service
from loguru import logger


async def fix_user_achievements():
    """Проверяет и исправляет достижения для всех пользователей"""
    try:
        logger.info("Starting achievement fix script...")
        
        # Получаем всех пользователей
        all_users = await user_service.get_all_users()
        logger.info(f"Found {len(all_users)} users to check")
        
        fixed_count = 0
        
        for user in all_users:
            logger.info(f"Checking user {user.telegram_id} (level {user.level})")
            
            # Проверяем достижения для пользователя
            new_achievements = await achievement_service.check_user_achievements(user)
            
            if new_achievements:
                logger.info(f"Fixed {len(new_achievements)} achievements for user {user.telegram_id}")
                for achievement in new_achievements:
                    logger.info(f"  - {achievement.name}")
                fixed_count += 1
            
        logger.info(f"Achievement fix completed. Fixed achievements for {fixed_count} users.")
        
    except Exception as e:
        logger.error(f"Error in achievement fix script: {e}")


if __name__ == "__main__":
    asyncio.run(fix_user_achievements())
