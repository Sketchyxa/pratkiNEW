#!/usr/bin/env python3
"""
Скрипт для инициализации всех достижений в базе данных
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

from services.achievement_service import achievement_service
from database.connection import db
from loguru import logger


async def init_achievements():
    """Инициализация всех достижений"""
    try:
        # Подключаемся к базе данных
        await db.connect()
        logger.info("Подключение к базе данных установлено")
        
        # Создаем стандартные достижения
        logger.info("Создание стандартных достижений...")
        await achievement_service.create_default_achievements()
        
        # Получаем все достижения для проверки
        all_achievements = await achievement_service.get_all_achievements()
        logger.info(f"✅ Создано достижений: {len(all_achievements)}")
        
        # Показываем статистику по категориям
        categories = {}
        difficulties = {}
        
        for achievement in all_achievements:
            # По категориям
            category = achievement.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
            
            # По сложности
            difficulty = achievement.difficulty
            if difficulty not in difficulties:
                difficulties[difficulty] = 0
            difficulties[difficulty] += 1
        
        logger.info("\n📊 Статистика по категориям:")
        category_names = {
            "general": "🎯 Общие",
            "collection": "🎴 Коллекционирование", 
            "economy": "💰 Экономика",
            "social": "👥 Социальные",
            "special": "⭐ Особые"
        }
        
        for category, count in categories.items():
            category_name = category_names.get(category, category.title())
            logger.info(f"  {category_name}: {count}")
        
        logger.info("\n📊 Статистика по сложности:")
        difficulty_names = {
            "easy": "🟢 Легкие",
            "normal": "🟡 Обычные", 
            "hard": "🟠 Сложные",
            "legendary": "🔴 Легендарные",
            "special": "🟣 Особые"
        }
        
        for difficulty, count in difficulties.items():
            difficulty_name = difficulty_names.get(difficulty, difficulty.title())
            logger.info(f"  {difficulty_name}: {count}")
        
        # Показываем несколько примеров
        logger.info("\n🎯 Примеры достижений:")
        for i, achievement in enumerate(all_achievements[:5], 1):
            difficulty_emoji = achievement.get_difficulty_emoji()
            logger.info(f"  {i}. {difficulty_emoji} {achievement.name} - {achievement.description}")
        
        if len(all_achievements) > 5:
            logger.info(f"  ... и еще {len(all_achievements) - 5} достижений")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации: {e}")
    finally:
        logger.info("Инициализация завершена")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    logger.info("🚀 Инициализация достижений...")
    asyncio.run(init_achievements())
