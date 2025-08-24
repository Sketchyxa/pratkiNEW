from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from loguru import logger

from database.connection import db
from models.achievement import Achievement
from models.user import User, UserAchievement


class AchievementService:
    """Сервис для работы с достижениями"""
    
    def __init__(self):
        self.collection: AsyncIOMotorCollection = None
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        if self.collection is None:
            self.collection = db.get_collection("achievements")
        return self.collection
    
    async def create_default_achievements(self):
        """Создает стандартные достижения для бота"""
        default_achievements = [
            # Коллекционирование
            {
                "name": "Первая карточка",
                "description": "Получите свою первую карточку",
                "icon": "🎴",
                "category": "collection",
                "condition_type": "cards_count",
                "condition_value": 1,
                "reward_coins": 25,
                "reward_experience": 10,
                "difficulty": "easy",
                "points": 5
            },
            {
                "name": "Коллекционер",
                "description": "Соберите 10 карточек",
                "icon": "📚",
                "category": "collection", 
                "condition_type": "cards_count",
                "condition_value": 10,
                "reward_coins": 100,
                "reward_experience": 50,
                "difficulty": "normal",
                "points": 15
            },
            {
                "name": "Мастер коллекционер",
                "description": "Соберите 50 карточек",
                "icon": "🏆",
                "category": "collection",
                "condition_type": "cards_count", 
                "condition_value": 50,
                "reward_coins": 500,
                "reward_experience": 200,
                "difficulty": "hard",
                "points": 30
            },
            {
                "name": "Легенда коллекций",
                "description": "Соберите 100 карточек",
                "icon": "👑",
                "category": "collection",
                "condition_type": "cards_count",
                "condition_value": 100,
                "reward_coins": 1000,
                "reward_experience": 500,
                "difficulty": "legendary",
                "points": 50
            },
            
            # Редкости
            {
                "name": "Редкий экземпляр",
                "description": "Получите первую Rare карточку",
                "icon": "🔵",
                "category": "collection",
                "condition_type": "rarity_card",
                "condition_value": 1,
                "condition_data": {"rarity": "rare"},
                "reward_coins": 50,
                "reward_experience": 25,
                "difficulty": "normal",
                "points": 10
            },
            {
                "name": "Эпический коллекционер",
                "description": "Получите первую Epic карточку",
                "icon": "🟣",
                "category": "collection",
                "condition_type": "rarity_card",
                "condition_value": 1,
                "condition_data": {"rarity": "epic"},
                "reward_coins": 150,
                "reward_experience": 75,
                "difficulty": "hard",
                "points": 20
            },
            {
                "name": "Легендарный охотник",
                "description": "Получите первую Legendary карточку",
                "icon": "🟡",
                "category": "collection",
                "condition_type": "rarity_card",
                "condition_value": 1,
                "condition_data": {"rarity": "legendary"},
                "reward_coins": 300,
                "reward_experience": 150,
                "difficulty": "hard",
                "points": 35
            },
            {
                "name": "Артефактный мастер",
                "description": "Получите первую Artifact карточку",
                "icon": "🔴",
                "category": "collection",
                "condition_type": "rarity_card",
                "condition_value": 1,
                "condition_data": {"rarity": "artifact"},
                "reward_coins": 1000,
                "reward_experience": 500,
                "difficulty": "legendary",
                "points": 100
            },
            
            # Экономика
            {
                "name": "Богач",
                "description": "Накопите 1000 монет",
                "icon": "💰",
                "category": "economy",
                "condition_type": "coins_total",
                "condition_value": 1000,
                "reward_experience": 100,
                "difficulty": "normal",
                "points": 15
            },
            {
                "name": "Миллионер",
                "description": "Накопите 10000 монет",
                "icon": "💎",
                "category": "economy",
                "condition_type": "coins_total",
                "condition_value": 10000,
                "reward_experience": 500,
                "difficulty": "hard",
                "points": 40
            },
            {
                "name": "Первая покупка",
                "description": "Купите свой первый пак в магазине",
                "icon": "🛒",
                "category": "economy",
                "condition_type": "shop_purchase",
                "condition_value": 1,
                "reward_coins": 50,
                "difficulty": "easy",
                "points": 5
            },
            
            # Уровни и опыт
            {
                "name": "Новичок",
                "description": "Достигните 2-го уровня",
                "icon": "⭐",
                "category": "general",
                "condition_type": "level",
                "condition_value": 2,
                "reward_coins": 50,
                "difficulty": "easy",
                "points": 5
            },
            {
                "name": "Опытный игрок",
                "description": "Достигните 5-го уровня",
                "icon": "⭐⭐",
                "category": "general",
                "condition_type": "level",
                "condition_value": 5,
                "reward_coins": 200,
                "reward_experience": 100,
                "difficulty": "normal",
                "points": 15
            },
            {
                "name": "Мастер",
                "description": "Достигните 10-го уровня",
                "icon": "⭐⭐⭐",
                "category": "general", 
                "condition_type": "level",
                "condition_value": 10,
                "reward_coins": 500,
                "reward_experience": 250,
                "difficulty": "hard",
                "points": 30
            },
            {
                "name": "Гуру карточек",
                "description": "Достигните 20-го уровня",
                "icon": "🌟",
                "category": "general",
                "condition_type": "level",
                "condition_value": 20,
                "reward_coins": 1000,
                "reward_experience": 500,
                "difficulty": "legendary",
                "points": 50
            },
            
            # Активность
            {
                "name": "Постоянный игрок",
                "description": "Играйте 7 дней подряд",
                "icon": "📅",
                "category": "general",
                "condition_type": "days_streak",
                "condition_value": 7,
                "reward_coins": 300,
                "reward_experience": 150,
                "difficulty": "normal",
                "points": 20
            },
            {
                "name": "Преданный фан",
                "description": "Играйте 30 дней подряд",
                "icon": "🗓️",
                "category": "general",
                "condition_type": "days_streak", 
                "condition_value": 30,
                "reward_coins": 1000,
                "reward_experience": 500,
                "difficulty": "hard",
                "points": 40
            },
            
            # Социальные
            {
                "name": "Первое предложение",
                "description": "Предложите свою первую карточку",
                "icon": "💡",
                "category": "social",
                "condition_type": "suggestions_made",
                "condition_value": 1,
                "reward_coins": 100,
                "reward_experience": 50,
                "difficulty": "normal",
                "points": 10
            },
            {
                "name": "Креативный автор",
                "description": "Создайте 5 предложений карточек",
                "icon": "🎨",
                "category": "social", 
                "condition_type": "suggestions_made",
                "condition_value": 5,
                "reward_coins": 500,
                "reward_experience": 250,
                "difficulty": "hard",
                "points": 25
            },
            
            # Специальные
            {
                "name": "Счастливчик",
                "description": "Получите карточку Artifact случайно",
                "icon": "🍀",
                "category": "special",
                "condition_type": "artifact_random",
                "condition_value": 1,
                "reward_coins": 777,
                "reward_experience": 333,
                "difficulty": "legendary",
                "points": 77,
                "is_hidden": True
            },
            {
                "name": "Ранняя пташка",
                "description": "Получите ежедневную карточку в 6 утра",
                "icon": "🌅",
                "category": "special",
                "condition_type": "early_bird",
                "condition_value": 1,
                "reward_coins": 100,
                "difficulty": "normal",
                "points": 15,
                "is_hidden": True
            },
            
            # ДОПОЛНИТЕЛЬНЫЕ КОЛЛЕКЦИОННЫЕ ДОСТИЖЕНИЯ
            {
                "name": "Коллекционер-маньяк",
                "description": "Соберите 500 карточек",
                "icon": "🔥",
                "category": "collection",
                "condition_type": "cards_count",
                "condition_value": 500,
                "reward_coins": 2000,
                "reward_experience": 1000,
                "difficulty": "legendary",
                "points": 100
            },
            {
                "name": "Хранитель дубликатов",
                "description": "Накопите 10 копий одной карточки",
                "icon": "👥",
                "category": "collection",
                "condition_type": "duplicate_cards",
                "condition_value": 10,
                "reward_coins": 500,
                "reward_experience": 200,
                "difficulty": "normal",
                "points": 25
            },
            {
                "name": "Армия клонов",
                "description": "Накопите 50 копий одной карточки",
                "icon": "🔄",
                "category": "collection",
                "condition_type": "duplicate_cards",
                "condition_value": 50,
                "reward_coins": 2000,
                "reward_experience": 800,
                "difficulty": "hard",
                "points": 75
            },
            {
                "name": "Покоритель редкости",
                "description": "Соберите по 20 карточек каждой редкости",
                "icon": "🌈",
                "category": "collection",
                "condition_type": "all_rarities",
                "condition_value": 20,
                "reward_coins": 1500,
                "reward_experience": 800,
                "difficulty": "hard",
                "points": 80
            },
            {
                "name": "Полная коллекция",
                "description": "Соберите все доступные карточки",
                "icon": "📚",
                "category": "collection",
                "condition_type": "complete_collection",
                "condition_value": 1,
                "reward_coins": 5000,
                "reward_experience": 2000,
                "difficulty": "legendary",
                "points": 200
            },
            
            # ДОПОЛНИТЕЛЬНЫЕ ЭКОНОМИЧЕСКИЕ ДОСТИЖЕНИЯ
            {
                "name": "Экономный покупатель",
                "description": "Купите 25 паков в магазине",
                "icon": "🛒",
                "category": "economy",
                "condition_type": "shop_purchases",
                "condition_value": 25,
                "reward_coins": 800,
                "reward_experience": 300,
                "difficulty": "normal",
                "points": 30
            },
            {
                "name": "Шопоголик",
                "description": "Купите 100 паков в магазине",
                "icon": "🛍️",
                "category": "economy",
                "condition_type": "shop_purchases",
                "condition_value": 100,
                "reward_coins": 3000,
                "reward_experience": 1000,
                "difficulty": "hard",
                "points": 60
            },
            {
                "name": "Кэш мастер",
                "description": "Накопите 50,000 монет",
                "icon": "💎",
                "category": "economy",
                "condition_type": "coins_total",
                "condition_value": 50000,
                "reward_coins": 5000,
                "reward_experience": 1500,
                "difficulty": "hard",
                "points": 80
            },
            {
                "name": "Монетный магнат",
                "description": "Накопите 200,000 монет",
                "icon": "👑",
                "category": "economy",
                "condition_type": "coins_total",
                "condition_value": 200000,
                "reward_coins": 20000,
                "reward_experience": 5000,
                "difficulty": "legendary",
                "points": 150
            },
            {
                "name": "Продавец года",
                "description": "Продайте 200 карточек",
                "icon": "💰",
                "category": "economy",
                "condition_type": "cards_sold",
                "condition_value": 200,
                "reward_coins": 1000,
                "reward_experience": 400,
                "difficulty": "normal",
                "points": 35
            },
            {
                "name": "Торговый магнат",
                "description": "Заработайте 100,000 монет продажей карточек",
                "icon": "🏦",
                "category": "economy",
                "condition_type": "selling_profit",
                "condition_value": 100000,
                "reward_coins": 10000,
                "reward_experience": 3000,
                "difficulty": "legendary",
                "points": 120
            },
            
            # ДОПОЛНИТЕЛЬНЫЕ ОБЩИЕ ДОСТИЖЕНИЯ
            {
                "name": "Гуру карточек PRO",
                "description": "Достигните 25-го уровня",
                "icon": "🚀",
                "category": "general",
                "condition_type": "level",
                "condition_value": 25,
                "reward_coins": 2500,
                "reward_experience": 1000,
                "difficulty": "hard",
                "points": 60
            },
            {
                "name": "Легенда уровней",
                "description": "Достигните 50-го уровня",
                "icon": "⭐",
                "category": "general",
                "condition_type": "level",
                "condition_value": 50,
                "reward_coins": 10000,
                "reward_experience": 5000,
                "difficulty": "legendary",
                "points": 200
            },
            {
                "name": "Ветеран игры",
                "description": "Играйте 60 дней подряд",
                "icon": "🎖️",
                "category": "general",
                "condition_type": "daily_streak",
                "condition_value": 60,
                "reward_coins": 3000,
                "reward_experience": 1500,
                "difficulty": "hard",
                "points": 80
            },
            {
                "name": "Железная воля",
                "description": "Играйте 365 дней подряд",
                "icon": "⚔️",
                "category": "general",
                "condition_type": "daily_streak",
                "condition_value": 365,
                "reward_coins": 20000,
                "reward_experience": 10000,
                "difficulty": "legendary",
                "points": 500
            },
            {
                "name": "Скоростной коллекционер",
                "description": "Соберите 100 карточек за один день",
                "icon": "⚡",
                "category": "general",
                "condition_type": "cards_per_day",
                "condition_value": 100,
                "reward_coins": 2000,
                "reward_experience": 800,
                "difficulty": "hard",
                "points": 60
            },
            
            # ДОПОЛНИТЕЛЬНЫЕ СОЦИАЛЬНЫЕ ДОСТИЖЕНИЯ
            {
                "name": "Мастер идей",
                "description": "Предложите 25 карточек",
                "icon": "🧠",
                "category": "social",
                "condition_type": "suggestions_made",
                "condition_value": 25,
                "reward_coins": 2000,
                "reward_experience": 800,
                "difficulty": "hard",
                "points": 50
            },
            {
                "name": "Популярный автор",
                "description": "Получите 10 принятых предложений",
                "icon": "⭐",
                "category": "social",
                "condition_type": "accepted_suggestions",
                "condition_value": 10,
                "reward_coins": 3000,
                "reward_experience": 1200,
                "difficulty": "hard",
                "points": 75
            },
            {
                "name": "Виртуоз творчества",
                "description": "Получите 50 принятых предложений",
                "icon": "🎭",
                "category": "social",
                "condition_type": "accepted_suggestions",
                "condition_value": 50,
                "reward_coins": 10000,
                "reward_experience": 5000,
                "difficulty": "legendary",
                "points": 200
            },
            
            # МНОЖЕСТВО ОСОБЫХ ДОСТИЖЕНИЙ
            {
                "name": "Полуночник",
                "description": "Получите карточку ровно в 00:00",
                "icon": "🌙",
                "category": "special",
                "condition_type": "midnight_card",
                "condition_value": 1,
                "reward_coins": 1000,
                "reward_experience": 400,
                "difficulty": "special",
                "points": 50,
                "is_hidden": True
            },
            {
                "name": "Золотая лихорадка",
                "description": "Получите 5 легендарных карточек подряд",
                "icon": "🥇",
                "category": "special",
                "condition_type": "legendary_streak",
                "condition_value": 5,
                "reward_coins": 5000,
                "reward_experience": 2000,
                "difficulty": "legendary",
                "points": 150,
                "is_hidden": True
            },
            {
                "name": "Магнит артефактов",
                "description": "Получите 10 артефактов за месяц",
                "icon": "🧲",
                "category": "special",
                "condition_type": "artifacts_per_month",
                "condition_value": 10,
                "reward_coins": 10000,
                "reward_experience": 5000,
                "difficulty": "legendary",
                "points": 300,
                "is_hidden": True
            },
            {
                "name": "Отличник",
                "description": "Завершите свой первый ивент",
                "icon": "🎓",
                "category": "special",
                "condition_type": "complete_event",
                "condition_value": 1,
                "reward_coins": 1000,
                "reward_experience": 500,
                "difficulty": "normal",
                "points": 40
            },
            {
                "name": "Чемпион ивентов",
                "description": "Завершите 10 ивентов",
                "icon": "🏆",
                "category": "special",
                "condition_type": "complete_events",
                "condition_value": 10,
                "reward_coins": 5000,
                "reward_experience": 2500,
                "difficulty": "hard",
                "points": 100
            },
            {
                "name": "Легенда ивентов",
                "description": "Завершите 50 ивентов",
                "icon": "👑",
                "category": "special",
                "condition_type": "complete_events",
                "condition_value": 50,
                "reward_coins": 25000,
                "reward_experience": 10000,
                "difficulty": "legendary",
                "points": 300
            },
            {
                "name": "Перфекционист",
                "description": "Получите 100% достижений в одной категории",
                "icon": "💯",
                "category": "special",
                "condition_type": "perfect_category",
                "condition_value": 1,
                "reward_coins": 3000,
                "reward_experience": 1500,
                "difficulty": "hard",
                "points": 80,
                "is_hidden": True
            },
            {
                "name": "Коллекционер достижений",
                "description": "Получите 75 достижений",
                "icon": "🏅",
                "category": "special",
                "condition_type": "achievements_count",
                "condition_value": 75,
                "reward_coins": 8000,
                "reward_experience": 4000,
                "difficulty": "legendary",
                "points": 200
            },
            {
                "name": "Мастер всего",
                "description": "Получите все доступные достижения",
                "icon": "🌟",
                "category": "special",
                "condition_type": "all_achievements",
                "condition_value": 1,
                "reward_coins": 50000,
                "reward_experience": 25000,
                "difficulty": "legendary",
                "points": 1000,
                "is_hidden": True
            },
            {
                "name": "Везунчик дня",
                "description": "Получите артефакт в праздничный день",
                "icon": "🎂",
                "category": "special",
                "condition_type": "holiday_artifact",
                "condition_value": 1,
                "reward_coins": 2000,
                "reward_experience": 1000,
                "difficulty": "special",
                "points": 100,
                "is_hidden": True
            },
            {
                "name": "Первопроходец",
                "description": "Получите карточку первым из всех игроков",
                "icon": "🚩",
                "category": "special",
                "condition_type": "first_card_ever",
                "condition_value": 1,
                "reward_coins": 3000,
                "reward_experience": 1500,
                "difficulty": "special",
                "points": 150,
                "is_hidden": True
            },
            {
                "name": "Супер коллекционер",
                "description": "Соберите 1500 карточек",
                "icon": "💥",
                "category": "special",
                "condition_type": "cards_count",
                "condition_value": 1500,
                "reward_coins": 15000,
                "reward_experience": 8000,
                "difficulty": "legendary",
                "points": 400
            },
            {
                "name": "Щедрый благотворитель",
                "description": "Участвуйте в 20 раздачах от админа",
                "icon": "🎁",
                "category": "special",
                "condition_type": "giveaway_participation",
                "condition_value": 20,
                "reward_coins": 3000,
                "reward_experience": 1200,
                "difficulty": "normal",
                "points": 60
            },
            {
                "name": "Любимец удачи",
                "description": "Выиграйте в 10 раздачах от админа",
                "icon": "🎰",
                "category": "special",
                "condition_type": "giveaway_wins",
                "condition_value": 10,
                "reward_coins": 8000,
                "reward_experience": 3000,
                "difficulty": "hard",
                "points": 120,
                "is_hidden": True
            },
            {
                "name": "Экстремальный коллекционер",
                "description": "Соберите 500 карточек за день",
                "icon": "🌪️",
                "category": "special",
                "condition_type": "cards_per_day",
                "condition_value": 500,
                "reward_coins": 10000,
                "reward_experience": 5000,
                "difficulty": "legendary",
                "points": 250,
                "is_hidden": True
            },
            {
                "name": "Тайный агент",
                "description": "Найдите и получите скрытую карточку",
                "icon": "🕵️",
                "category": "special",
                "condition_type": "secret_card",
                "condition_value": 1,
                "reward_coins": 5000,
                "reward_experience": 2500,
                "difficulty": "legendary",
                "points": 200,
                "is_hidden": True
            },
            {
                "name": "Миллиардер",
                "description": "Накопите 1,000,000 монет",
                "icon": "💸",
                "category": "special",
                "condition_type": "coins_total",
                "condition_value": 1000000,
                "reward_coins": 500000,
                "reward_experience": 50000,
                "difficulty": "legendary",
                "points": 2000,
                "is_hidden": True
            },
            {
                "name": "Машина времени",
                "description": "Играйте непрерывно в течение 1000 дней",
                "icon": "⏰",
                "category": "special",
                "condition_type": "total_days_played",
                "condition_value": 1000,
                "reward_coins": 100000,
                "reward_experience": 50000,
                "difficulty": "legendary",
                "points": 1000,
                "is_hidden": True
            },
            {
                "name": "Король артефактов",
                "description": "Соберите 100 артефактов",
                "icon": "👑",
                "category": "special",
                "condition_type": "artifact_collection",
                "condition_value": 100,
                "reward_coins": 50000,
                "reward_experience": 25000,
                "difficulty": "legendary",
                "points": 500,
                "is_hidden": True
            },
            {
                "name": "Безумный коллекционер",
                "description": "Соберите 10,000 карточек общего",
                "icon": "🤯",
                "category": "special",
                "condition_type": "cards_count",
                "condition_value": 10000,
                "reward_coins": 100000,
                "reward_experience": 50000,
                "difficulty": "legendary",
                "points": 1500,
                "is_hidden": True
            },
            {
                "name": "Император монет",
                "description": "Потратьте 1,000,000 монет в магазине",
                "icon": "👑",
                "category": "special",
                "condition_type": "coins_spent",
                "condition_value": 1000000,
                "reward_coins": 200000,
                "reward_experience": 75000,
                "difficulty": "legendary",
                "points": 800,
                "is_hidden": True
            },
            {
                "name": "Дневной рыцарь",
                "description": "Получите карточку ровно в 12:00",
                "icon": "☀️",
                "category": "special",
                "condition_type": "noon_card",
                "condition_value": 1,
                "reward_coins": 500,
                "reward_experience": 200,
                "difficulty": "special",
                "points": 30,
                "is_hidden": True
            },
            {
                "name": "Ночная сова",
                "description": "Получите 100 карточек после 22:00",
                "icon": "🦉",
                "category": "special",
                "condition_type": "night_cards",
                "condition_value": 100,
                "reward_coins": 2000,
                "reward_experience": 800,
                "difficulty": "hard",
                "points": 60,
                "is_hidden": True
            },
            {
                "name": "Утренняя птичка",
                "description": "Получите 100 карточек до 06:00",
                "icon": "🐦",
                "category": "special",
                "condition_type": "morning_cards",
                "condition_value": 100,
                "reward_coins": 2000,
                "reward_experience": 800,
                "difficulty": "hard",
                "points": 60,
                "is_hidden": True
            },
            {
                "name": "Мастер времени",
                "description": "Получите карточки во все 24 часа дня",
                "icon": "🕐",
                "category": "special",
                "condition_type": "all_hours_cards",
                "condition_value": 24,
                "reward_coins": 5000,
                "reward_experience": 2000,
                "difficulty": "legendary",
                "points": 150,
                "is_hidden": True
            },
            {
                "name": "Неудержимый",
                "description": "Получите 1000 карточек не прерываясь",
                "icon": "🔥",
                "category": "special",
                "condition_type": "card_streak",
                "condition_value": 1000,
                "reward_coins": 25000,
                "reward_experience": 10000,
                "difficulty": "legendary",
                "points": 400,
                "is_hidden": True
            },
            {
                "name": "Бог коллекционирования",
                "description": "Достигните максимального уровня 100",
                "icon": "🔱",
                "category": "special",
                "condition_type": "level",
                "condition_value": 100,
                "reward_coins": 1000000,
                "reward_experience": 100000,
                "difficulty": "legendary",
                "points": 5000,
                "is_hidden": True
            }
        ]
        
        collection = await self.get_collection()
        
        for achievement_data in default_achievements:
            # Проверяем, существует ли уже такое достижение
            existing = await collection.find_one({"name": achievement_data["name"]})
            if not existing:
                achievement = Achievement(**achievement_data)
                await collection.insert_one(achievement.dict(by_alias=True, exclude={"id"}))
                logger.info(f"Created achievement: {achievement_data['name']}")
    
    async def check_user_achievements(self, user: User) -> List[Achievement]:
        """Проверяет и выдает новые достижения пользователю"""
        from services.user_service import user_service
        
        new_achievements = []
        all_achievements = await self.get_all_achievements()
        user_achievement_ids = [ua.achievement_id for ua in user.achievements if ua.is_completed]
        
        for achievement in all_achievements:
            if str(achievement.id) in user_achievement_ids:
                continue  # Уже получено
            
            if await self._check_achievement_condition(user, achievement):
                # Выдаем достижение
                user_achievement = UserAchievement(
                    achievement_id=str(achievement.id),
                    is_completed=True,
                    progress=achievement.condition_value
                )
                user.achievements.append(user_achievement)
                user.achievement_points += achievement.points
                user.coins += achievement.reward_coins
                user.experience += achievement.reward_experience
                
                # Обновляем статистику достижения
                achievement.total_earned += 1
                if achievement.first_earned_by is None:
                    achievement.first_earned_by = user.telegram_id
                    achievement.first_earned_at = datetime.utcnow()
                
                await self.update_achievement(achievement)
                new_achievements.append(achievement)
        
        if new_achievements:
            await user_service.update_user(user)
        
        return new_achievements
    
    async def _check_achievement_condition(self, user: User, achievement: Achievement) -> bool:
        """Проверяет условие получения достижения"""
        condition_type = achievement.condition_type
        condition_value = achievement.condition_value
        condition_data = achievement.condition_data or {}
        
        if condition_type == "cards_count":
            return user.total_cards >= condition_value
        
        elif condition_type == "level":
            return user.level >= condition_value
        
        elif condition_type == "coins_total":
            return user.coins >= condition_value
        
        elif condition_type == "rarity_card":
            rarity = condition_data.get("rarity", "common")
            from services.card_service import card_service
            
            count = 0
            for user_card in user.cards:
                if user_card.quantity > 0:
                    card = await card_service.get_card_by_id(user_card.card_id)
                    if card and card.rarity.lower() == rarity.lower():
                        count += user_card.quantity
            return count >= condition_value
        
        elif condition_type == "shop_purchase":
            return user.shop_purchases_count >= condition_value
        
        elif condition_type == "shop_purchases":
            return user.shop_purchases_count >= condition_value
        
        elif condition_type == "days_streak":
            return user.daily_streak >= condition_value
        
        elif condition_type == "daily_streak":
            return user.daily_streak >= condition_value
        
        elif condition_type == "suggestions_made":
            return user.suggestions_made >= condition_value
        
        elif condition_type == "accepted_suggestions":
            return user.accepted_suggestions >= condition_value
        
        elif condition_type == "artifact_random":
            return user.artifact_cards_received >= condition_value
        
        elif condition_type == "early_bird":
            return user.morning_cards_count >= condition_value
        
        elif condition_type == "midnight_card":
            return user.has_received_card_at_hour(0)
        
        elif condition_type == "noon_card":
            return user.has_received_card_at_hour(12)
        
        elif condition_type == "legendary_streak":
            return user.legendary_streak >= condition_value
        
        elif condition_type == "artifacts_per_month":
            return user.artifacts_this_month >= condition_value
        
        elif condition_type == "complete_event":
            return user.events_completed >= condition_value
        
        elif condition_type == "complete_events":
            return user.events_completed >= condition_value
        
        elif condition_type == "perfect_category":
            # Проверяем 100% достижений в категории
            category = condition_data.get("category", "general")
            all_achievements = await self.get_all_achievements()
            category_achievements = [a for a in all_achievements if a.category == category]
            user_completed_in_category = len([ua for ua in user.achievements if ua.is_completed])
            return user_completed_in_category >= len(category_achievements)
        
        elif condition_type == "achievements_count":
            completed_count = len([ua for ua in user.achievements if ua.is_completed])
            return completed_count >= condition_value
        
        elif condition_type == "all_achievements":
            all_achievements = await self.get_all_achievements()
            completed_count = len([ua for ua in user.achievements if ua.is_completed])
            return completed_count >= len(all_achievements)
        
        elif condition_type == "holiday_artifact":
            # Проверяем получение артефакта в праздничный день
            from datetime import datetime
            now = datetime.utcnow()
            # Простая проверка на праздники (1 января, 8 марта, 9 мая и т.д.)
            holidays = [(1, 1), (3, 8), (5, 9), (12, 31)]
            is_holiday = (now.month, now.day) in holidays
            return is_holiday and user.artifact_cards_received >= condition_value
        
        elif condition_type == "first_card_ever":
            # Проверяем, получил ли пользователь первую карточку в системе
            from services.user_service import user_service
            all_users = await user_service.get_all_users()
            # Сортируем по дате создания и проверяем, был ли этот пользователь первым
            sorted_users = sorted(all_users, key=lambda u: u.created_at)
            return sorted_users[0].telegram_id == user.telegram_id
        
        elif condition_type == "cards_per_day":
            return user.cards_received_today >= condition_value
        
        elif condition_type == "night_cards":
            return user.night_cards_count >= condition_value
        
        elif condition_type == "morning_cards":
            return user.morning_cards_count >= condition_value
        
        elif condition_type == "all_hours_cards":
            return user.get_unique_hours_count() >= condition_value
        
        elif condition_type == "card_streak":
            return user.card_streak >= condition_value
        
        elif condition_type == "total_days_played":
            return user.total_days_played >= condition_value
        
        elif condition_type == "artifact_collection":
            return user.artifact_cards_received >= condition_value
        
        elif condition_type == "coins_spent":
            return user.total_coins_spent >= condition_value
        
        elif condition_type == "cards_sold":
            return user.cards_sold_count >= condition_value
        
        elif condition_type == "selling_profit":
            return user.selling_profit >= condition_value
        
        elif condition_type == "duplicate_cards":
            # Проверяем максимальное количество дубликатов одной карточки
            max_duplicates = max([card.quantity for card in user.cards], default=0)
            return max_duplicates >= condition_value
        
        elif condition_type == "all_rarities":
            # Проверяем наличие карточек всех редкостей
            from services.card_service import card_service
            rarities = ["common", "rare", "epic", "legendary", "artifact"]
            user_rarities = set()
            
            for user_card in user.cards:
                if user_card.quantity > 0:
                    card = await card_service.get_card_by_id(user_card.card_id)
                    if card:
                        user_rarities.add(card.rarity.lower())
            
            return len(user_rarities) >= len(rarities)
        
        elif condition_type == "complete_collection":
            # Проверяем полную коллекцию
            from services.card_service import card_service
            all_cards = await card_service.get_all_cards()
            user_card_ids = {card.card_id for card in user.cards if card.quantity > 0}
            return len(user_card_ids) >= len(all_cards)
        
        elif condition_type == "giveaway_participation":
            return user.giveaway_participation >= condition_value
        
        elif condition_type == "giveaway_wins":
            return user.giveaway_wins >= condition_value
        
        elif condition_type == "secret_card":
            # Проверяем получение скрытой карточки (пока заглушка)
            return False
        
        # Дополнительные условия можно добавить здесь
        return False
    
    async def get_all_achievements(self) -> List[Achievement]:
        """Получает все активные достижения"""
        collection = await self.get_collection()
        achievements_data = await collection.find({"is_active": True}).to_list(length=None)
        return [Achievement(**data) for data in achievements_data]
    
    async def get_achievement_by_id(self, achievement_id: str) -> Optional[Achievement]:
        """Получает достижение по ID"""
        from bson import ObjectId
        collection = await self.get_collection()
        
        if ObjectId.is_valid(achievement_id):
            data = await collection.find_one({"_id": ObjectId(achievement_id)})
            if data:
                return Achievement(**data)
        return None
    
    async def update_achievement(self, achievement: Achievement) -> bool:
        """Обновляет достижение"""
        try:
            collection = await self.get_collection()
            achievement.updated_at = datetime.utcnow()
            
            result = await collection.update_one(
                {"_id": achievement.id},
                {"$set": achievement.dict(by_alias=True, exclude={"id"})}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating achievement: {e}")
            return False
    
    async def get_user_achievement_stats(self, user: User) -> Dict[str, Any]:
        """Возвращает статистику достижений пользователя"""
        total_achievements = len(await self.get_all_achievements())
        user_completed = len([ua for ua in user.achievements if ua.is_completed])
        
        categories = {}
        for ua in user.achievements:
            if ua.is_completed:
                achievement = await self.get_achievement_by_id(ua.achievement_id)
                if achievement:
                    category = achievement.category
                    if category not in categories:
                        categories[category] = 0
                    categories[category] += 1
        
        return {
            "total_possible": total_achievements,
            "completed": user_completed,
            "completion_percentage": round((user_completed / total_achievements) * 100, 1) if total_achievements > 0 else 0,
            "total_points": user.achievement_points,
            "categories": categories
        }


# Глобальный экземпляр сервиса
achievement_service = AchievementService()
