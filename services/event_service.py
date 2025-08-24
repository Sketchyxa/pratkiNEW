from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from loguru import logger

from database.connection import db
from models.event import Event, UserEventProgress, EventReward
from models.user import User


class EventService:
    """Сервис для работы с ивентами"""
    
    def __init__(self):
        self.events_collection: AsyncIOMotorCollection = None
        self.progress_collection: AsyncIOMotorCollection = None
    
    async def get_events_collection(self) -> AsyncIOMotorCollection:
        if self.events_collection is None:
            self.events_collection = db.get_collection("events")
        return self.events_collection
    
    async def get_progress_collection(self) -> AsyncIOMotorCollection:
        if self.progress_collection is None:
            self.progress_collection = db.get_collection("user_event_progress")
        return self.progress_collection
    
    async def create_event(self, event_data: Dict[str, Any]) -> Event:
        """Создает новый ивент"""
        try:
            event = Event(**event_data)
            collection = await self.get_events_collection()
            
            result = await collection.insert_one(event.model_dump(by_alias=True))
            event.id = result.inserted_id
            
            logger.info(f"Created event: {event.name}")
            return event
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise
    
    async def get_active_events(self) -> List[Event]:
        """Получает все активные ивенты"""
        try:
            collection = await self.get_events_collection()
            now = datetime.utcnow()
            
            events_data = await collection.find({
                "is_active": True,
                "start_date": {"$lte": now},
                "end_date": {"$gte": now}
            }).to_list(length=None)
            
            return [Event(**data) for data in events_data]
            
        except Exception as e:
            logger.error(f"Error getting active events: {e}")
            return []
    
    async def get_all_events(self) -> List[Event]:
        """Получает все ивенты"""
        try:
            collection = await self.get_events_collection()
            events_data = await collection.find({}).sort("created_at", -1).to_list(length=None)
            return [Event(**data) for data in events_data]
            
        except Exception as e:
            logger.error(f"Error getting all events: {e}")
            return []
    
    async def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Получает ивент по ID"""
        try:
            from bson import ObjectId
            collection = await self.get_events_collection()
            
            if ObjectId.is_valid(event_id):
                data = await collection.find_one({"_id": ObjectId(event_id)})
                if data:
                    return Event(**data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting event by id {event_id}: {e}")
            return None
    
    async def update_event(self, event: Event) -> bool:
        """Обновляет ивент"""
        try:
            collection = await self.get_events_collection()
            
            result = await collection.update_one(
                {"_id": event.id},
                {"$set": event.model_dump(by_alias=True, exclude={"id"})}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return False
    
    async def delete_event(self, event_id: str) -> bool:
        """Удаляет ивент"""
        try:
            from bson import ObjectId
            collection = await self.get_events_collection()
            
            if ObjectId.is_valid(event_id):
                result = await collection.delete_one({"_id": ObjectId(event_id)})
                return result.deleted_count > 0
            return False
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False
    
    async def get_user_event_progress(self, user_id: int, event_id: str) -> Optional[UserEventProgress]:
        """Получает прогресс пользователя в ивенте"""
        try:
            collection = await self.get_progress_collection()
            data = await collection.find_one({
                "user_id": user_id,
                "event_id": event_id
            })
            
            if data:
                return UserEventProgress(**data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user event progress: {e}")
            return None
    
    async def update_user_progress(self, progress: UserEventProgress) -> bool:
        """Обновляет прогресс пользователя"""
        try:
            collection = await self.get_progress_collection()
            progress.last_updated = datetime.utcnow()
            
            result = await collection.update_one(
                {"user_id": progress.user_id, "event_id": progress.event_id},
                {"$set": progress.model_dump()},
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user progress: {e}")
            return False
    
    async def check_user_event_progress(self, user: User) -> List[Event]:
        """Проверяет прогресс пользователя во всех активных ивентах"""
        try:
            active_events = await self.get_active_events()
            completed_events = []
            
            for event in active_events:
                # Получаем текущий прогресс
                progress = await self.get_user_event_progress(user.telegram_id, str(event.id))
                
                if progress and progress.is_completed:
                    continue  # Уже завершен
                
                # Вычисляем новый прогресс
                new_progress = await self._calculate_event_progress(user, event)
                
                if progress is None:
                    # Создаем новый прогресс
                    progress = UserEventProgress(
                        event_id=str(event.id),
                        user_id=user.telegram_id,
                        current_progress=new_progress,
                        target_progress=event.target_value
                    )
                else:
                    progress.current_progress = new_progress
                
                # Проверяем завершение
                if new_progress >= event.target_value and not progress.is_completed:
                    progress.is_completed = True
                    progress.completed_at = datetime.utcnow()
                    completed_events.append(event)
                    
                    # Обновляем статистику ивента
                    event.total_completed += 1
                    await self.update_event(event)
                
                # Сохраняем прогресс
                await self.update_user_progress(progress)
            
            return completed_events
            
        except Exception as e:
            logger.error(f"Error checking user event progress: {e}")
            return []
    
    async def _calculate_event_progress(self, user: User, event: Event) -> int:
        """Вычисляет прогресс пользователя в ивенте"""
        try:
            if event.target_type == "total_cards":
                return user.total_cards
            
            elif event.target_type == "card_rarity":
                from services.card_service import card_service
                target_rarity = event.target_data.get("rarity", "common").lower()
                
                count = 0
                for user_card in user.cards:
                    if user_card.quantity > 0:
                        card = await card_service.get_card_by_id(user_card.card_id)
                        if card and card.rarity.lower() == target_rarity:
                            count += user_card.quantity
                return count
            
            elif event.target_type == "specific_cards":
                target_card_ids = event.target_data.get("card_ids", [])
                
                count = 0
                for user_card in user.cards:
                    if user_card.card_id in target_card_ids and user_card.quantity > 0:
                        count += user_card.quantity
                return count
            
            elif event.target_type == "level":
                return user.level
            
            elif event.target_type == "coins":
                return user.coins
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating event progress: {e}")
            return 0
    
    async def claim_event_rewards(self, user: User, event_id: str) -> bool:
        """Выдает награды за завершенный ивент"""
        try:
            progress = await self.get_user_event_progress(user.telegram_id, event_id)
            event = await self.get_event_by_id(event_id)
            
            if not progress or not progress.is_completed or progress.rewards_claimed:
                return False
            
            if not event:
                return False
            
            # Выдаем награды
            from services.user_service import user_service
            
            user.coins += event.rewards.coins
            user.experience += event.rewards.experience
            
            # Добавляем карточки
            for card_id in event.rewards.cards:
                from services.card_service import card_service
                card = await card_service.get_card_by_id(card_id)
                if card:
                    await user_service.add_card_to_user(user, card_id)
            
            # Отмечаем награды как полученные
            progress.rewards_claimed = True
            await self.update_user_progress(progress)
            
            # Обновляем пользователя
            await user_service.update_user(user)
            
            logger.info(f"Claimed event rewards for user {user.telegram_id}, event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error claiming event rewards: {e}")
            return False
    
    async def get_event_leaderboard(self, event_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает топ игроков по ивенту"""
        try:
            collection = await self.get_progress_collection()
            
            pipeline = [
                {"$match": {"event_id": event_id}},
                {"$sort": {"current_progress": -1, "last_updated": 1}},
                {"$limit": limit}
            ]
            
            results = await collection.aggregate(pipeline).to_list(length=None)
            
            # Добавляем информацию о пользователях
            from services.user_service import user_service
            leaderboard = []
            
            for i, result in enumerate(results, 1):
                user = await user_service.get_user_by_telegram_id(result["user_id"])
                if user:
                    leaderboard.append({
                        "position": i,
                        "user_name": user.first_name or f"User{user.telegram_id}",
                        "user_id": user.telegram_id,
                        "progress": result["current_progress"],
                        "is_completed": result["is_completed"],
                        "completed_at": result.get("completed_at")
                    })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting event leaderboard: {e}")
            return []


# Глобальный экземпляр сервиса
event_service = EventService()
