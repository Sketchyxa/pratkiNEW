#!/usr/bin/env python3
"""
Скрипт для миграции пользователей с новыми полями достижений
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.user_service import user_service
from loguru import logger

async def migrate_user_achievements():
    """Мигрирует пользователей с новыми полями достижений"""
    print("🔧 Миграция пользователей с новыми полями достижений...")
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        print("✅ Подключение к базе данных успешно")
        
        # Получаем всех пользователей
        all_users = await user_service.get_all_users()
        print(f"✅ Найдено {len(all_users)} пользователей")
        
        migrated_count = 0
        for user in all_users:
            needs_update = False
            
            # Проверяем и добавляем недостающие поля
            if not hasattr(user, 'daily_streak'):
                user.daily_streak = 0
                needs_update = True
            
            if not hasattr(user, 'max_daily_streak'):
                user.max_daily_streak = 0
                needs_update = True
            
            if not hasattr(user, 'last_daily_streak_date'):
                user.last_daily_streak_date = None
                needs_update = True
            
            if not hasattr(user, 'shop_purchases_count'):
                user.shop_purchases_count = 0
                needs_update = True
            
            if not hasattr(user, 'total_coins_spent'):
                user.total_coins_spent = 0
                needs_update = True
            
            if not hasattr(user, 'cards_sold_count'):
                user.cards_sold_count = 0
                needs_update = True
            
            if not hasattr(user, 'selling_profit'):
                user.selling_profit = 0
                needs_update = True
            
            if not hasattr(user, 'suggestions_made'):
                user.suggestions_made = 0
                needs_update = True
            
            if not hasattr(user, 'accepted_suggestions'):
                user.accepted_suggestions = 0
                needs_update = True
            
            if not hasattr(user, 'giveaway_participation'):
                user.giveaway_participation = 0
                needs_update = True
            
            if not hasattr(user, 'giveaway_wins'):
                user.giveaway_wins = 0
                needs_update = True
            
            if not hasattr(user, 'artifact_cards_received'):
                user.artifact_cards_received = 0
                needs_update = True
            
            if not hasattr(user, 'legendary_streak'):
                user.legendary_streak = 0
                needs_update = True
            
            if not hasattr(user, 'max_legendary_streak'):
                user.max_legendary_streak = 0
                needs_update = True
            
            if not hasattr(user, 'artifacts_this_month'):
                user.artifacts_this_month = 0
                needs_update = True
            
            if not hasattr(user, 'last_month_reset'):
                user.last_month_reset = None
                needs_update = True
            
            if not hasattr(user, 'cards_received_today'):
                user.cards_received_today = 0
                needs_update = True
            
            if not hasattr(user, 'last_day_reset'):
                user.last_day_reset = None
                needs_update = True
            
            if not hasattr(user, 'cards_received_at_hours'):
                user.cards_received_at_hours = []
                needs_update = True
            
            if not hasattr(user, 'night_cards_count'):
                user.night_cards_count = 0
                needs_update = True
            
            if not hasattr(user, 'morning_cards_count'):
                user.morning_cards_count = 0
                needs_update = True
            
            if not hasattr(user, 'card_streak'):
                user.card_streak = 0
                needs_update = True
            
            if not hasattr(user, 'max_card_streak'):
                user.max_card_streak = 0
                needs_update = True
            
            if not hasattr(user, 'events_completed'):
                user.events_completed = 0
                needs_update = True
            
            if not hasattr(user, 'total_days_played'):
                user.total_days_played = 0
                needs_update = True
            
            # Обновляем пользователя если нужно
            if needs_update:
                await user_service.update_user(user)
                migrated_count += 1
                print(f"✅ Мигрирован пользователь: {user.telegram_id}")
        
        print(f"\n✅ Миграция завершена! Обновлено {migrated_count} пользователей из {len(all_users)}")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Отключаемся от базы данных
        await db.disconnect()
        print("🔌 Отключение от базы данных")


if __name__ == "__main__":
    asyncio.run(migrate_user_achievements())
