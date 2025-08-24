import random
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from loguru import logger

from models.user import User, BattleDeck
from models.card import Mob
from database.connection import db


class BattleService:
    """Сервис для управления боями с мобами"""
    
    def __init__(self):
        self.mobs_data = self._generate_mobs()
    
    def _generate_mobs(self) -> List[Mob]:
        """Генерирует список мобов для всех 50 уровней"""
        mobs = []
        
        # Список имен мобов
        mob_names = [
            "Гоблин", "Орк", "Тролль", "Дракон", "Демон", "Вампир", "Оборотень", "Зомби",
            "Скелет", "Призрак", "Элементаль", "Гигант", "Циклоп", "Минотавр", "Химера",
            "Гарпия", "Кентавр", "Пегас", "Единорог", "Феникс", "Грифон", "Василиск",
            "Кракен", "Левиафан", "Бегемот", "Кракен", "Медуза", "Сирена", "Русалка",
            "Тритон", "Нереида", "Океанид", "Наяда", "Дриада", "Нимфа", "Фея", "Эльф",
            "Дварф", "Халфлинг", "Гном", "Кобольд", "Гнолл", "Бугай", "Огр", "Эттин",
            "Фомор", "Титан", "Бог", "Архидемон", "Древний", "Примитив"
        ]
        
        for level in range(1, 51):
            # Вычисляем силу моба на основе уровня (экспоненциальный рост)
            if level <= 30:
                base_power = int(level * 80 + (level ** 1.5) * 10) + random.randint(-30, 30)
            else:
                # Увеличиваем силу для уровней 30-50
                base_power = int(level * 120 + (level ** 2) * 15) + random.randint(-50, 50)
            
            # Определяем сложность
            if level <= 10:
                difficulty = "easy"
                power_multiplier = 0.7
            elif level <= 25:
                difficulty = "normal"
                power_multiplier = 1.0
            elif level <= 40:
                difficulty = "hard"
                power_multiplier = 1.6
            else:
                difficulty = "boss"
                power_multiplier = 2.5
            
            power = int(base_power * power_multiplier)
            health = power * 2
            
            # Награды
            exp_reward = level * 2 + random.randint(5, 15)
            coin_reward = level + random.randint(1, 5)
            
            mob = Mob(
                name=f"{mob_names[level-1]} Уровня {level}",
                description=f"Могучий {mob_names[level-1].lower()} {level} уровня",
                level=level,
                power=power,
                health=health,
                experience_reward=exp_reward,
                coin_reward=coin_reward,
                difficulty=difficulty
            )
            mobs.append(mob)
        
        return mobs
    
    async def get_mob_by_level(self, level: int) -> Optional[Mob]:
        """Получает моба по уровню"""
        if 1 <= level <= 50:
            return self.mobs_data[level - 1]
        return None
    
    def calculate_card_power(self, card_rarity: str) -> int:
        """Вычисляет силу карточки по её редкости"""
        power_map = {
            "common": random.randint(100, 300),
            "rare": random.randint(400, 800),
            "epic": random.randint(1000, 2000),
            "legendary": random.randint(2500, 5000),
            "artifact": random.randint(6000, 12000)
        }
        return power_map.get(card_rarity, 200)
    
    async def get_user_deck_power(self, user: User) -> int:
        """Вычисляет общую силу колоды пользователя"""
        total_power = 0
        
        for card_id in user.battle_deck.card_ids:
            # Находим карточку в коллекции пользователя
            user_card = next((c for c in user.cards if c.card_id == card_id), None)
            if user_card:
                # Получаем информацию о карточке из базы
                from bson import ObjectId
                try:
                    card_info = await db.cards.find_one({"_id": ObjectId(card_id)})
                    if card_info:
                        rarity = card_info.get("rarity", "common")
                        total_power += self.calculate_card_power(rarity)
                except:
                    # Если не удалось найти карточку, используем базовую силу
                    total_power += self.calculate_card_power("common")
        
        return total_power
    
    async def battle_mob(self, user: User, mob_level: int) -> Tuple[bool, str, dict]:
        """
        Проводит бой с мобом
        
        Returns:
            Tuple[bool, str, dict]: (победа, сообщение, награды)
        """
        # Проверяем возможность боя
        if not user.can_battle():
            time_left = 3600
            if user.battle_progress.last_battle_time:
                time_passed = (datetime.utcnow() - user.battle_progress.last_battle_time).total_seconds()
                time_left = max(0, 3600 - time_passed)
            
            if time_left > 0:
                minutes = int(time_left // 60)
                seconds = int(time_left % 60)
                return False, f"⏰ Подождите {minutes:02d}:{seconds:02d} перед следующим боем", {}
            
            return False, "❌ У вас должна быть колода из 5 карт для боя", {}
        
        # Получаем моба
        mob = await self.get_mob_by_level(mob_level)
        if not mob:
            return False, "❌ Моб не найден", {}
        
        # Вычисляем силу колоды
        deck_power = await self.get_user_deck_power(user)
        
        # Проводим бой
        battle_result = self._simulate_battle(deck_power, mob.power)
        
        # Обновляем прогресс пользователя
        user.battle_progress.total_battles += 1
        user.battle_progress.last_battle_time = datetime.utcnow()
        
        if battle_result:
            # Победа
            user.battle_progress.battles_won += 1
            if user.battle_progress.current_level == mob_level:
                user.battle_progress.current_level = min(50, mob_level + 1)
            
            # Награды
            rewards = {
                "experience": mob.experience_reward,
                "coins": mob.coin_reward
            }
            
            # Добавляем награды пользователю
            user.add_experience(mob.experience_reward)
            user.coins += mob.coin_reward
            
            message = (
                f"🎉 **Победа!**\n\n"
                f"⚔️ Вы победили {mob.name}\n"
                f"💪 Сила вашей колоды: {deck_power}\n"
                f"💀 Сила моба: {mob.power}\n\n"
                f"💰 Награды:\n"
                f"📈 Опыт: +{mob.experience_reward}\n"
                f"🪙 Монеты: +{mob.coin_reward}\n\n"
                f"🏆 Прогресс: {user.battle_progress.current_level}/50"
            )
            
            return True, message, rewards
        else:
            # Поражение
            message = (
                f"💀 **Поражение!**\n\n"
                f"⚔️ {mob.name} оказался сильнее\n"
                f"💪 Сила вашей колоды: {deck_power}\n"
                f"💀 Сила моба: {mob.power}\n\n"
                f"💡 Попробуйте улучшить свою колоду или собрать более сильные карты"
            )
            
            return False, message, {}
    
    def _simulate_battle(self, deck_power: int, mob_power: int) -> bool:
        """Симулирует бой между колодой и мобом"""
        # Добавляем элемент случайности
        deck_roll = random.randint(int(deck_power * 0.8), int(deck_power * 1.2))
        mob_roll = random.randint(int(mob_power * 0.8), int(mob_power * 1.2))
        
        return deck_roll >= mob_roll
    
    async def get_available_mobs(self, user: User) -> List[Mob]:
        """Получает список доступных мобов для пользователя"""
        available_mobs = []
        
        # Показываем текущий уровень и несколько следующих
        start_level = max(1, user.battle_progress.current_level - 2)
        end_level = min(50, user.battle_progress.current_level + 2)
        
        for level in range(start_level, end_level + 1):
            mob = await self.get_mob_by_level(level)
            if mob:
                available_mobs.append(mob)
        
        return available_mobs
    
    async def can_battle_mob(self, user: User, mob_level: int) -> bool:
        """Проверяет, может ли пользователь сражаться с мобом определенного уровня"""
        if not user.can_battle():
            return False
        
        # Пользователь может сражаться с мобами своего уровня и ниже
        return mob_level <= user.battle_progress.current_level


# Создаем экземпляр сервиса
battle_service = BattleService()
