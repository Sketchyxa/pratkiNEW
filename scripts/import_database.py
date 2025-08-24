#!/usr/bin/env python3
"""
Скрипт для импорта базы данных
Импортирует данные из экспортированных JSON файлов
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
from models.user import User, UserCard, UserNFT, UserAchievement, BattleDeck, BattleProgress
from loguru import logger


async def import_database(import_dir: str = "database_export"):
    """Импорт базы данных из экспортированных файлов"""
    try:
        logger.info(f"Starting database import from {import_dir}...")
        
        import_path = Path(import_dir)
        if not import_path.exists():
            raise FileNotFoundError(f"Directory {import_dir} not found")
        
        # Подключаемся к базе данных
        await db.connect()
        
        # Импортируем карточки
        cards_file = import_path / "cards.json"
        if cards_file.exists():
            logger.info("Importing cards...")
            with open(cards_file, 'r', encoding='utf-8') as f:
                cards_data = json.load(f)
            
            imported_cards = 0
            skipped_cards = 0
            
            for card_data in cards_data:
                # Проверяем, существует ли карточка
                existing_card = await card_service.get_card_by_name(card_data["name"])
                
                if existing_card:
                    logger.info(f"Card '{card_data['name']}' already exists, skipping")
                    skipped_cards += 1
                    continue
                
                # Создаем карточку
                card = await card_service.create_card(
                    name=card_data["name"],
                    description=card_data["description"],
                    rarity=card_data["rarity"],
                    tags=card_data.get("tags", []),
                    image_url=card_data.get("image_url"),
                    gif_url=card_data.get("gif_url"),
                    video_url=card_data.get("video_url"),
                    is_active=card_data.get("is_active", True)
                )
                
                if card:
                    logger.info(f"Created card: {card.name} ({card.rarity})")
                    imported_cards += 1
                else:
                    logger.error(f"Failed to create card: {card_data['name']}")
            
            logger.info(f"Cards import completed! Created: {imported_cards}, Skipped: {skipped_cards}")
        else:
            logger.warning("cards.json not found, skipping cards import")
        
        # Импортируем достижения
        achievements_file = import_path / "achievements.json"
        if achievements_file.exists():
            logger.info("Importing achievements...")
            with open(achievements_file, 'r', encoding='utf-8') as f:
                achievements_data = json.load(f)
            
            imported_achievements = 0
            skipped_achievements = 0
            
            for achievement_data in achievements_data:
                # Проверяем, существует ли достижение
                existing_achievement = await achievement_service.get_achievement_by_id(achievement_data["achievement_id"])
                
                if existing_achievement:
                    logger.info(f"Achievement '{achievement_data['achievement_id']}' already exists, skipping")
                    skipped_achievements += 1
                    continue
                
                # Создаем достижение
                achievement = await achievement_service.create_achievement(
                    achievement_id=achievement_data["achievement_id"],
                    name=achievement_data["name"],
                    description=achievement_data["description"],
                    category=achievement_data["category"],
                    points=achievement_data["points"],
                    is_active=achievement_data.get("is_active", True)
                )
                
                if achievement:
                    logger.info(f"Created achievement: {achievement.name}")
                    imported_achievements += 1
                else:
                    logger.error(f"Failed to create achievement: {achievement_data['achievement_id']}")
            
            logger.info(f"Achievements import completed! Created: {imported_achievements}, Skipped: {skipped_achievements}")
        else:
            logger.warning("achievements.json not found, skipping achievements import")
        
        # Импортируем пользователей
        users_file = import_path / "users.json"
        if users_file.exists():
            logger.info("Importing users...")
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            imported_users = 0
            skipped_users = 0
            
            for user_data in users_data:
                # Проверяем, существует ли пользователь
                existing_user = await user_service.get_user_by_telegram_id(user_data["telegram_id"])
                
                if existing_user:
                    logger.info(f"User {user_data['telegram_id']} already exists, skipping")
                    skipped_users += 1
                    continue
                
                # Создаем пользователя
                user = User(
                    telegram_id=user_data["telegram_id"],
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name"),
                    experience=user_data.get("experience", 0),
                    level=user_data.get("level", 1),
                    coins=user_data.get("coins", 600),
                    total_cards=user_data.get("total_cards", 0),
                    favorite_cards=user_data.get("favorite_cards", []),
                    achievement_points=user_data.get("achievement_points", 0),
                    first_card_received=user_data.get("first_card_received", False),
                    newbie_bonus_received=user_data.get("newbie_bonus_received", False),
                    daily_streak=user_data.get("daily_streak", 0),
                    max_daily_streak=user_data.get("max_daily_streak", 0),
                    shop_purchases_count=user_data.get("shop_purchases_count", 0),
                    total_coins_spent=user_data.get("total_coins_spent", 0),
                    cards_sold_count=user_data.get("cards_sold_count", 0),
                    selling_profit=user_data.get("selling_profit", 0),
                    suggestions_made=user_data.get("suggestions_made", 0),
                    accepted_suggestions=user_data.get("accepted_suggestions", 0),
                    giveaway_participation=user_data.get("giveaway_participation", 0),
                    giveaway_wins=user_data.get("giveaway_wins", 0),
                    artifact_cards_received=user_data.get("artifact_cards_received", 0),
                    legendary_streak=user_data.get("legendary_streak", 0),
                    max_legendary_streak=user_data.get("max_legendary_streak", 0),
                    artifacts_this_month=user_data.get("artifacts_this_month", 0),
                    cards_received_today=user_data.get("cards_received_today", 0),
                    cards_received_at_hours=user_data.get("cards_received_at_hours", []),
                    night_cards_count=user_data.get("night_cards_count", 0),
                    morning_cards_count=user_data.get("morning_cards_count", 0),
                    card_streak=user_data.get("card_streak", 0),
                    max_card_streak=user_data.get("max_card_streak", 0),
                    events_completed=user_data.get("events_completed", 0),
                    total_days_played=user_data.get("total_days_played", 0),
                    is_suggestion_banned=user_data.get("is_suggestion_banned", False),
                    suggestion_ban_reason=user_data.get("suggestion_ban_reason"),
                    notifications_enabled=user_data.get("notifications_enabled", True),
                    easter_eggs_activated=user_data.get("easter_eggs_activated", []),
                    easter_egg_attempts_today=user_data.get("easter_egg_attempts_today", 0)
                )
                
                # Восстанавливаем карточки пользователя
                for card_data in user_data.get("cards", []):
                    user.add_card(card_data["card_id"], card_data["quantity"])
                
                # Восстанавливаем NFT карточки
                for nft_data in user_data.get("nfts", []):
                    user.nfts.append(UserNFT(
                        card_id=nft_data["card_id"],
                        is_active=nft_data.get("is_active", True)
                    ))
                
                # Восстанавливаем достижения пользователя
                for achievement_data in user_data.get("achievements", []):
                    user.achievements.append(UserAchievement(
                        achievement_id=achievement_data["achievement_id"],
                        progress=achievement_data.get("progress", 0),
                        is_completed=achievement_data.get("is_completed", False)
                    ))
                
                # Восстанавливаем боевую колоду
                battle_deck_data = user_data.get("battle_deck", {})
                user.battle_deck = BattleDeck(
                    card_ids=battle_deck_data.get("card_ids", [])
                )
                
                # Восстанавливаем боевой прогресс
                battle_progress_data = user_data.get("battle_progress", {})
                user.battle_progress = BattleProgress(
                    current_level=battle_progress_data.get("current_level", 1),
                    max_level=battle_progress_data.get("max_level", 50),
                    battles_won=battle_progress_data.get("battles_won", 0),
                    total_battles=battle_progress_data.get("total_battles", 0)
                )
                
                # Сохраняем пользователя
                saved_user = await user_service.create_user(user)
                if saved_user:
                    logger.info(f"Created user: {saved_user.telegram_id} ({saved_user.username or 'No username'})")
                    imported_users += 1
                else:
                    logger.error(f"Failed to create user: {user_data['telegram_id']}")
            
            logger.info(f"Users import completed! Created: {imported_users}, Skipped: {skipped_users}")
        else:
            logger.warning("users.json not found, skipping users import")
        
        # Показываем метаданные
        metadata_file = import_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info("Import completed!")
            logger.info(f"Original export date: {metadata.get('export_date', 'Unknown')}")
            logger.info(f"Original data: {metadata.get('total_cards', 0)} cards, {metadata.get('total_achievements', 0)} achievements, {metadata.get('total_users', 0)} users")
        
        # Отключаемся от базы данных
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"Error importing database: {e}")
        raise


async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        import_dir = sys.argv[1]
    else:
        import_dir = "database_export"
    
    await import_database(import_dir)


if __name__ == "__main__":
    asyncio.run(main())
