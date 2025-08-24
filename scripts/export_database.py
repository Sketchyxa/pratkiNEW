#!/usr/bin/env python3
"""
Скрипт для экспорта всей базы данных
Экспортирует все коллекции в JSON файлы
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.card_service import card_service
from services.achievement_service import achievement_service
from services.user_service import user_service
from loguru import logger


async def export_database(export_dir: str = "database_export"):
    """Экспорт всей базы данных"""
    try:
        logger.info(f"Starting database export to {export_dir}...")
        
        # Создаем директорию для экспорта
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)
        
        # Подключаемся к базе данных
        await db.connect()
        
        # Экспортируем карточки
        logger.info("Exporting cards...")
        cards = await card_service.get_all_cards(include_inactive=True)
        cards_data = []
        for card in cards:
            card_dict = {
                "name": card.name,
                "description": card.description,
                "rarity": card.rarity,
                "tags": card.tags,
                "image_url": card.image_url,
                "gif_url": card.gif_url,
                "video_url": card.video_url,
                "is_active": card.is_active,
                "created_at": str(card.created_at) if card.created_at else None,
                "updated_at": str(card.updated_at) if card.updated_at else None
            }
            cards_data.append(card_dict)
        
        with open(export_path / "cards.json", 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        
        # Экспортируем достижения
        logger.info("Exporting achievements...")
        achievements = await achievement_service.get_all_achievements()
        achievements_data = []
        for achievement in achievements:
            achievement_dict = {
                "achievement_id": achievement.achievement_id,
                "name": achievement.name,
                "description": achievement.description,
                "category": achievement.category,
                "points": achievement.points,
                "is_active": achievement.is_active,
                "created_at": str(achievement.created_at) if achievement.created_at else None
            }
            achievements_data.append(achievement_dict)
        
        with open(export_path / "achievements.json", 'w', encoding='utf-8') as f:
            json.dump(achievements_data, f, ensure_ascii=False, indent=2)
        
        # Экспортируем пользователей
        logger.info("Exporting users...")
        users = await user_service.get_all_users()
        users_data = []
        for user in users:
            user_dict = {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "experience": user.experience,
                "level": user.level,
                "coins": user.coins,
                "total_cards": user.total_cards,
                "cards": [{"card_id": card.card_id, "quantity": card.quantity, "obtained_at": str(card.obtained_at)} for card in user.cards],
                "nfts": [{"card_id": nft.card_id, "assigned_at": str(nft.assigned_at), "is_active": nft.is_active} for nft in user.nfts],
                "favorite_cards": user.favorite_cards,
                "achievements": [{"achievement_id": ach.achievement_id, "earned_at": str(ach.earned_at), "progress": ach.progress, "is_completed": ach.is_completed} for ach in user.achievements],
                "achievement_points": user.achievement_points,
                "battle_deck": {"card_ids": user.battle_deck.card_ids, "last_used": str(user.battle_deck.last_used) if user.battle_deck.last_used else None},
                "battle_progress": {
                    "current_level": user.battle_progress.current_level,
                    "max_level": user.battle_progress.max_level,
                    "last_battle_time": str(user.battle_progress.last_battle_time) if user.battle_progress.last_battle_time else None,
                    "battles_won": user.battle_progress.battles_won,
                    "total_battles": user.battle_progress.total_battles
                },
                "last_daily_card": str(user.last_daily_card) if user.last_daily_card else None,
                "first_card_received": user.first_card_received,
                "newbie_bonus_received": user.newbie_bonus_received,
                "daily_streak": user.daily_streak,
                "max_daily_streak": user.max_daily_streak,
                "last_daily_streak_date": str(user.last_daily_streak_date) if user.last_daily_streak_date else None,
                "pack_cooldowns": {k: str(v) for k, v in user.pack_cooldowns.items()},
                "shop_purchases_count": user.shop_purchases_count,
                "total_coins_spent": user.total_coins_spent,
                "cards_sold_count": user.cards_sold_count,
                "selling_profit": user.selling_profit,
                "suggestions_made": user.suggestions_made,
                "accepted_suggestions": user.accepted_suggestions,
                "giveaway_participation": user.giveaway_participation,
                "giveaway_wins": user.giveaway_wins,
                "artifact_cards_received": user.artifact_cards_received,
                "legendary_streak": user.legendary_streak,
                "max_legendary_streak": user.max_legendary_streak,
                "artifacts_this_month": user.artifacts_this_month,
                "last_month_reset": str(user.last_month_reset) if user.last_month_reset else None,
                "cards_received_today": user.cards_received_today,
                "last_day_reset": str(user.last_day_reset) if user.last_day_reset else None,
                "cards_received_at_hours": user.cards_received_at_hours,
                "night_cards_count": user.night_cards_count,
                "morning_cards_count": user.morning_cards_count,
                "card_streak": user.card_streak,
                "max_card_streak": user.max_card_streak,
                "events_completed": user.events_completed,
                "total_days_played": user.total_days_played,
                "is_suggestion_banned": user.is_suggestion_banned,
                "suggestion_ban_reason": user.suggestion_ban_reason,
                "suggestion_ban_date": str(user.suggestion_ban_date) if user.suggestion_ban_date else None,
                "easter_eggs_activated": user.easter_eggs_activated,
                "easter_egg_attempts_today": user.easter_egg_attempts_today,
                "last_easter_egg_attempt": str(user.last_easter_egg_attempt) if user.last_easter_egg_attempt else None,
                "notifications_enabled": user.notifications_enabled,
                "last_card_notification": str(user.last_card_notification) if user.last_card_notification else None,
                "created_at": str(user.created_at) if user.created_at else None,
                "updated_at": str(user.updated_at) if user.updated_at else None,
                "last_activity": str(user.last_activity) if user.last_activity else None
            }
            users_data.append(user_dict)
        
        with open(export_path / "users.json", 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        
        # Создаем файл с метаданными
        metadata = {
            "export_date": datetime.now().isoformat(),
            "total_cards": len(cards_data),
            "total_achievements": len(achievements_data),
            "total_users": len(users_data),
            "cards_by_rarity": {},
            "achievements_by_category": {}
        }
        
        # Подсчитываем статистику по карточкам
        for card in cards_data:
            rarity = card["rarity"]
            if rarity not in metadata["cards_by_rarity"]:
                metadata["cards_by_rarity"][rarity] = 0
            metadata["cards_by_rarity"][rarity] += 1
        
        # Подсчитываем статистику по достижениям
        for achievement in achievements_data:
            category = achievement["category"]
            if category not in metadata["achievements_by_category"]:
                metadata["achievements_by_category"][category] = 0
            metadata["achievements_by_category"][category] += 1
        
        with open(export_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Создаем README для экспорта
        readme_content = f"""# Экспорт базы данных Pratki Bot

Дата экспорта: {metadata['export_date']}

## Статистика:
- 🎴 Карточек: {metadata['total_cards']}
- 🏆 Достижений: {metadata['total_achievements']}
- 👥 Пользователей: {metadata['total_users']}

## Карточки по редкости:
"""
        for rarity, count in metadata["cards_by_rarity"].items():
            readme_content += f"- {rarity.capitalize()}: {count}\n"
        
        readme_content += f"""
## Достижения по категориям:
"""
        for category, count in metadata["achievements_by_category"].items():
            readme_content += f"- {category.capitalize()}: {count}\n"
        
        readme_content += """
## Файлы:
- `cards.json` - все карточки
- `achievements.json` - все достижения  
- `users.json` - все пользователи
- `metadata.json` - метаданные экспорта

## Импорт:
Для импорта используйте: `python scripts/import_database.py`
"""
        
        with open(export_path / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"Database export completed!")
        logger.info(f"Exported to: {export_path.absolute()}")
        logger.info(f"Cards: {len(cards_data)}")
        logger.info(f"Achievements: {len(achievements_data)}")
        logger.info(f"Users: {len(users_data)}")
        
        # Отключаемся от базы данных
        await db.disconnect()
        
        return export_path
        
    except Exception as e:
        logger.error(f"Error exporting database: {e}")
        raise


async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        export_dir = sys.argv[1]
    else:
        export_dir = f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    await export_database(export_dir)


if __name__ == "__main__":
    asyncio.run(main())
