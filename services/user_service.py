from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from loguru import logger

from database.connection import db
from models.user import User, UserCard
from config import settings


class UserService:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = None
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        if self.collection is None:
            self.collection = db.get_collection("users")
        return self.collection
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        try:
            collection = await self.get_collection()
            user_data = await collection.find_one({"telegram_id": telegram_id})
            
            if user_data:
                user = User(**user_data)
                logger.info(f"Loaded user {telegram_id} with {len(user.cards)} cards, total_cards: {user.total_cards}")
                return user
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None
    
    async def create_user(self, telegram_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None) -> User:
        """Создание нового пользователя"""
        try:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            
            collection = await self.get_collection()
            result = await collection.insert_one(user.dict(by_alias=True, exclude={"id"}))
            user.id = result.inserted_id
            
            logger.info(f"Created new user: {telegram_id} ({username})")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            raise
    
    async def update_user(self, user: User) -> bool:
        """Обновление пользователя"""
        try:
            user.updated_at = datetime.utcnow()
            collection = await self.get_collection()
            
            # Логируем данные перед сохранением - используем model_dump для Pydantic v2
            try:
                user_dict = user.model_dump(by_alias=True, exclude={"id"})
            except AttributeError:
                # Fallback для Pydantic v1
                user_dict = user.dict(by_alias=True, exclude={"id"})
                
            logger.info(f"Saving user {user.telegram_id} with cards: {user_dict.get('cards', [])}")
            
            result = await collection.update_one(
                {"telegram_id": user.telegram_id},
                {"$set": user_dict}
            )
            
            logger.info(f"Update result - modified_count: {result.modified_count}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user {user.telegram_id}: {e}")
            return False
    
    async def get_or_create_user(self, telegram_id: int, username: str = None,
                                first_name: str = None, last_name: str = None) -> User:
        """Получение или создание пользователя"""
        user = await self.get_user_by_telegram_id(telegram_id)
        
        if not user:
            user = await self.create_user(telegram_id, username, first_name, last_name)
        else:
            # Обновляем информацию о пользователе
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            
            if updated:
                await self.update_user(user)
        
        return user
    
    async def can_get_daily_card(self, user: User) -> bool:
        """Проверка, может ли пользователь получить ежедневную карточку"""
        if not user.last_daily_card:
            return True
        
        cooldown = timedelta(hours=settings.daily_card_cooldown_hours)
        return datetime.utcnow() - user.last_daily_card >= cooldown
    
    async def update_daily_card_time(self, user: User) -> bool:
        """Обновление времени последней ежедневной карточки"""
        user.last_daily_card = datetime.utcnow()
        return await self.update_user(user)
    
    async def add_card_to_user(self, user: User, card_id: str, quantity: int = 1) -> bool:
        """Добавление карточки пользователю"""
        logger.info(f"Adding card {card_id} (quantity: {quantity}) to user {user.telegram_id}")
        user.add_card(card_id, quantity)
        result = await self.update_user(user)
        logger.info(f"User now has {len(user.cards)} cards, total_cards: {user.total_cards}")
        return result
    
    async def remove_card_from_user(self, user: User, card_id: str, quantity: int = 1) -> bool:
        """Удаление карточки у пользователя"""
        if user.remove_card(card_id, quantity):
            return await self.update_user(user)
        return False
    
    async def add_experience(self, user: User, amount: int) -> int:
        """Добавление опыта пользователю. Возвращает количество новых уровней"""
        level_up = user.add_experience(amount)
        await self.update_user(user)
        return level_up
    
    async def get_leaderboard(self, limit: int = 10, sort_by: str = "experience") -> List[User]:
        """Получение таблицы лидеров"""
        try:
            collection = await self.get_collection()
            
            sort_field = sort_by
            if sort_by not in ["experience", "level", "total_cards", "coins"]:
                sort_field = "experience"
            
            cursor = collection.find({}).sort(sort_field, -1).limit(limit)
            users = []
            
            async for user_data in cursor:
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_battle_leaderboard(self, limit: int = 10) -> List[User]:
        """Получение таблицы лидеров по боям"""
        try:
            collection = await self.get_collection()
            
            # Сортируем по количеству боев
            cursor = collection.find({}).sort("battle_progress.total_battles", -1).limit(limit)
            users = []
            
            async for user_data in cursor:
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting battle leaderboard: {e}")
            return []
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Получение статистики пользователей"""
        try:
            collection = await self.get_collection()
            
            total_users = await collection.count_documents({})
            active_users = await collection.count_documents({
                "last_activity": {"$gte": datetime.utcnow() - timedelta(days=7)}
            })
            
            # Средний уровень
            pipeline = [
                {"$group": {"_id": None, "avg_level": {"$avg": "$level"}}}
            ]
            avg_result = await collection.aggregate(pipeline).to_list(1)
            avg_level = avg_result[0]["avg_level"] if avg_result else 0
            
            return {
                "total_users": total_users,
                "active_users_week": active_users,
                "average_level": round(avg_level, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    async def get_all_users(self) -> List[User]:
        """Получение всех пользователей"""
        try:
            collection = await self.get_collection()
            cursor = collection.find({})
            
            users = []
            async for user_data in cursor:
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def get_users_by_ids(self, telegram_ids: List[int]) -> List[User]:
        """Получение пользователей по списку Telegram ID"""
        try:
            collection = await self.get_collection()
            cursor = collection.find({"telegram_id": {"$in": telegram_ids}})
            
            users = []
            async for user_data in cursor:
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users by IDs: {e}")
            return []


# Глобальный экземпляр сервиса
user_service = UserService()
