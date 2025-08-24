#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы достижений
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.achievement_service import achievement_service
from services.user_service import user_service
from models.user import User


async def test_achievements():
    """Тестирует систему достижений"""
    print("🔧 Тестирование системы достижений...")
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        print("✅ Подключение к базе данных успешно")
        
        # Создаем тестового пользователя
        test_user = await user_service.get_or_create_user(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Тестовый пользователь создан: {test_user.telegram_id}")
        
        # Создаем стандартные достижения
        await achievement_service.create_default_achievements()
        print("✅ Стандартные достижения созданы")
        
        # Получаем все достижения
        all_achievements = await achievement_service.get_all_achievements()
        print(f"✅ Найдено {len(all_achievements)} достижений")
        
        # Показываем статистику по категориям
        categories = {}
        for achievement in all_achievements:
            category = achievement.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        print("\n📊 Статистика по категориям:")
        for category, count in categories.items():
            print(f"  {category}: {count} достижений")
        
        # Проверяем достижения пользователя
        print(f"\n👤 Проверяем достижения пользователя {test_user.telegram_id}...")
        
        # Симулируем получение карточки
        test_user.total_cards = 1
        await user_service.update_user(test_user)
        
        # Проверяем достижения
        new_achievements = await achievement_service.check_user_achievements(test_user)
        print(f"✅ Получено {len(new_achievements)} новых достижений")
        
        for achievement in new_achievements:
            print(f"  🏆 {achievement.name}: {achievement.description}")
        
        # Получаем статистику достижений пользователя
        stats = await achievement_service.get_user_achievement_stats(test_user)
        print(f"\n📈 Статистика пользователя:")
        print(f"  Выполнено: {stats['completed']}/{stats['total_possible']} ({stats['completion_percentage']}%)")
        print(f"  Очки достижений: {stats['total_points']}")
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Отключаемся от базы данных
        await db.disconnect()
        print("🔌 Отключение от базы данных")


if __name__ == "__main__":
    asyncio.run(test_achievements())
