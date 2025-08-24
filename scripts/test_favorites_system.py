#!/usr/bin/env python3
"""
Скрипт для тестирования системы любимых карточек
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.user_service import user_service
from services.card_service import card_service
from loguru import logger

async def test_favorites_system():
    """Тестирует систему любимых карточек"""
    print("🔧 Тестирование системы любимых карточек...")
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        print("✅ Подключение к базе данных успешно")
        
        # Получаем тестового пользователя
        test_user = await user_service.get_user_by_telegram_id(123456789)
        if not test_user:
            print("❌ Тестовый пользователь не найден")
            return
        
        print(f"✅ Найден пользователь: {test_user.telegram_id}")
        print(f"📊 Всего карточек: {test_user.total_cards}")
        print(f"🎴 Уникальных карточек: {len(test_user.cards)}")
        print(f"💖 Любимых карточек: {len(test_user.favorite_cards)}")
        
        # Показываем текущие любимые
        if test_user.favorite_cards:
            print("\n💖 Текущие любимые карточки:")
            for card_id in test_user.favorite_cards:
                card = await card_service.get_card_by_id(card_id)
                if card:
                    print(f"  - {card.name} ({card.rarity})")
                else:
                    print(f"  - ❓ Неизвестная карточка (ID: {card_id})")
        
        # Получаем коллекцию пользователя
        from services.game_service import game_service
        collection, total_pages, current_page = await game_service.get_user_collection(test_user, 1, 100)
        print(f"\n📚 Всего карточек в коллекции: {len(collection)}")
        
        # Показываем первые 10 карточек
        print("\n🎴 Первые 10 карточек в коллекции:")
        for i, (card, quantity) in enumerate(collection[:10]):
            is_favorite = str(card.id) in test_user.favorite_cards
            status = "💖" if is_favorite else "⚪"
            print(f"  {i+1:2d}. {status} {card.name} ({card.rarity}) x{quantity}")
        
        # Тестируем добавление в любимые
        if collection:
            test_card, _ = collection[0]
            test_card_id = str(test_card.id)
            
            print(f"\n🧪 Тестирование добавления в любимые:")
            print(f"  Карточка: {test_card.name}")
            
            # Проверяем, можно ли добавить
            can_add = test_user.add_to_favorites(test_card_id)
            print(f"  Можно добавить: {can_add}")
            
            if can_add:
                # Добавляем
                test_user.add_to_favorites(test_card_id)
                await user_service.update_user(test_user)
                print(f"  ✅ Добавлена в любимые")
                
                # Проверяем, что добавилась
                updated_user = await user_service.get_user_by_telegram_id(123456789)
                is_now_favorite = test_card_id in updated_user.favorite_cards
                print(f"  В любимых после добавления: {is_now_favorite}")
                
                # Удаляем обратно
                updated_user.remove_from_favorites(test_card_id)
                await user_service.update_user(updated_user)
                print(f"  ✅ Удалена из любимых")
        
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
    asyncio.run(test_favorites_system())
