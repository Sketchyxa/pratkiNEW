import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from loguru import logger

from database.connection import db
from models.card import Card, CardStats
from config import settings


class CardService:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = None
        self.stats_collection: AsyncIOMotorCollection = None
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        if self.collection is None:
            self.collection = db.get_collection("cards")
        return self.collection
    
    async def get_stats_collection(self) -> AsyncIOMotorCollection:
        if self.stats_collection is None:
            self.stats_collection = db.get_collection("card_stats")
        return self.stats_collection
    
    async def create_card(self, name: str, description: str, rarity: str,
                         image_url: str = None, gif_url: str = None, 
                         video_url: str = None, tags: List[str] = None,
                         created_by: int = None) -> Optional[Card]:
        """Создание новой карточки"""
        try:
            card = Card(
                name=name,
                description=description,
                rarity=rarity,
                image_url=image_url,
                gif_url=gif_url,
                video_url=video_url,
                tags=tags or [],
                created_by=created_by
            )
            
            collection = await self.get_collection()
            result = await collection.insert_one(card.dict(by_alias=True, exclude={"id"}))
            card.id = result.inserted_id
            
            logger.info(f"Created new card: {name} ({rarity})")
            return card
            
        except Exception as e:
            logger.error(f"Error creating card {name}: {e}")
            return None
    
    async def get_card_by_name(self, name: str) -> Optional[Card]:
        """Получение карточки по имени"""
        try:
            collection = await self.get_collection()
            card_data = await collection.find_one({"name": name, "is_active": True})
            
            if card_data:
                return Card(**card_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting card {name}: {e}")
            return None
    
    async def get_card_by_id(self, card_id: str) -> Optional[Card]:
        """Получение карточки по ID"""
        try:
            from bson import ObjectId
            collection = await self.get_collection()
            
            # Конвертируем строку в ObjectId
            if ObjectId.is_valid(card_id):
                object_id = ObjectId(card_id)
            else:
                logger.warning(f"Invalid ObjectId format: {card_id}")
                return None
                
            card_data = await collection.find_one({"_id": object_id, "is_active": True})
            
            if card_data:
                logger.info(f"Found card by ID {card_id}: {card_data.get('name', 'Unknown')}")
                return Card(**card_data)
            else:
                logger.warning(f"Card not found in DB for ID: {card_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting card by ID {card_id}: {e}")
            return None
    
    async def get_all_cards(self, include_inactive: bool = False) -> List[Card]:
        """Получение всех карточек"""
        try:
            collection = await self.get_collection()
            
            filter_query = {} if include_inactive else {"is_active": True}
            cursor = collection.find(filter_query).sort("name", 1)
            
            cards = []
            async for card_data in cursor:
                cards.append(Card(**card_data))
            
            return cards
            
        except Exception as e:
            logger.error(f"Error getting all cards: {e}")
            return []
    
    async def get_cards_by_rarity(self, rarity: str) -> List[Card]:
        """Получение карточек по редкости"""
        try:
            collection = await self.get_collection()
            cursor = collection.find({"rarity": rarity, "is_active": True})
            
            cards = []
            async for card_data in cursor:
                cards.append(Card(**card_data))
            
            return cards
            
        except Exception as e:
            logger.error(f"Error getting cards by rarity {rarity}: {e}")
            return []
    
    async def update_card(self, card: Card) -> bool:
        """Обновление карточки"""
        try:
            card.updated_at = datetime.utcnow()
            collection = await self.get_collection()
            
            result = await collection.update_one(
                {"_id": card.id},
                {"$set": card.dict(by_alias=True, exclude={"id"})}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating card {card.name}: {e}")
            return False
    
    async def delete_card(self, card_name: str) -> bool:
        """Мягкое удаление карточки (деактивация)"""
        try:
            collection = await self.get_collection()
            result = await collection.update_one(
                {"name": card_name},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting card {card_name}: {e}")
            return False
    
    async def get_random_card_by_rarity(self, rarity: str) -> Optional[Card]:
        """Получение случайной карточки определенной редкости"""
        cards = await self.get_cards_by_rarity(rarity)
        if cards:
            return random.choice(cards)
        return None
    
    async def get_random_card(self) -> Optional[Card]:
        """Получение случайной карточки с учетом вероятностей"""
        try:
            # Генерируем случайное число
            rand = random.uniform(0, 100)
            cumulative_prob = 0
            
            # Проходим по редкостям в порядке увеличения редкости
            for rarity, info in settings.rarities.items():
                cumulative_prob += info["probability"]
                if rand <= cumulative_prob:
                    card = await self.get_random_card_by_rarity(rarity)
                    if card:
                        return card
            
            # Fallback на common карточку
            return await self.get_random_card_by_rarity("common")
            
        except Exception as e:
            logger.error(f"Error getting random card: {e}")
            return None
    
    async def update_card_stats(self, card_name: str, user_count_change: int = 0,
                               owner_count_change: int = 0) -> None:
        """Обновление статистики карточки"""
        try:
            collection = await self.get_collection()
            update_operations = {"$set": {"updated_at": datetime.utcnow()}}
            
            if user_count_change != 0 or owner_count_change != 0:
                update_operations["$inc"] = {}
                
                if user_count_change != 0:
                    update_operations["$inc"]["total_owned"] = user_count_change
                
                if owner_count_change != 0:
                    update_operations["$inc"]["unique_owners"] = owner_count_change
            
            await collection.update_one({"name": card_name}, update_operations)
            
        except Exception as e:
            logger.error(f"Error updating card stats for {card_name}: {e}")
    
    async def update_card(self, card: Card) -> bool:
        """Обновление карточки в базе данных"""
        try:
            collection = await self.get_collection()
            
            # Обновляем карточку, исключая id
            card_data = card.dict(by_alias=True, exclude={"id"})
            card_data["updated_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"_id": card.id},
                {"$set": card_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Card '{card.name}' updated successfully")
                return True
            else:
                logger.warning(f"Card '{card.name}' not found for update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating card {card.name}: {e}")
            return False
    
    async def get_upgrade_result(self, source_rarity: str) -> Optional[str]:
        """Получение редкости после улучшения"""
        upgrade_map = {
            "common": "rare",
            "rare": "epic", 
            "epic": "legendary",
            "legendary": "artifact"
        }
        
        return upgrade_map.get(source_rarity)
    
    async def search_cards(self, query: str, limit: int = 10) -> List[Card]:
        """Поиск карточек по названию или описанию"""
        try:
            collection = await self.get_collection()
            
            # Создаем regex для поиска
            regex_pattern = {"$regex": query, "$options": "i"}
            
            cursor = collection.find({
                "$and": [
                    {"is_active": True},
                    {"$or": [
                        {"name": regex_pattern},
                        {"description": regex_pattern},
                        {"tags": {"$in": [regex_pattern]}}
                    ]}
                ]
            }).limit(limit)
            
            cards = []
            async for card_data in cursor:
                cards.append(Card(**card_data))
            
            return cards
            
        except Exception as e:
            logger.error(f"Error searching cards with query '{query}': {e}")
            return []
    
    async def get_card_stats(self) -> Dict[str, Any]:
        """Получение общей статистики карточек"""
        try:
            collection = await self.get_collection()
            
            # Общее количество карточек
            total_cards = await collection.count_documents({"is_active": True})
            
            # Статистика по редкостям
            pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {"_id": "$rarity", "count": {"$sum": 1}}}
            ]
            
            rarity_stats = {}
            async for item in collection.aggregate(pipeline):
                rarity_stats[item["_id"]] = item["count"]
            
            # Самая популярная карточка
            most_popular = await collection.find(
                {"is_active": True}
            ).sort("total_owned", -1).limit(1).to_list(1)
            
            # Самая редкая карточка (по количеству владельцев)
            rarest = await collection.find(
                {"is_active": True, "unique_owners": {"$gt": 0}}
            ).sort("unique_owners", 1).limit(1).to_list(1)
            
            return {
                "total_cards": total_cards,
                "rarity_distribution": rarity_stats,
                "most_popular": most_popular[0]["name"] if most_popular else None,
                "rarest": rarest[0]["name"] if rarest else None
            }
            
        except Exception as e:
            logger.error(f"Error getting card stats: {e}")
            return {}
    
    async def delete_card(self, card_name: str) -> bool:
        """Полное удаление карточки из системы"""
        try:
            # Найдем карточку для получения её ID
            card = await self.get_card_by_name(card_name)
            if not card:
                return False
            
            collection = await self.get_collection()
            
            # Удаляем карточку у всех пользователей
            from services.user_service import user_service
            users = await user_service.get_all_users()
            
            for user in users:
                # Удаляем карточку из коллекции пользователя
                user.cards = [user_card for user_card in user.cards 
                             if user_card.card_id != str(card.id)]
                await user_service.update_user(user)
            
            # Удаляем саму карточку из БД
            result = await collection.delete_one({"name": card_name})
            
            if result.deleted_count > 0:
                logger.info(f"Card '{card_name}' deleted successfully")
                return True
            else:
                logger.warning(f"Card '{card_name}' not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting card {card_name}: {e}")
            return False


# Глобальный экземпляр сервиса
card_service = CardService()
