from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from models.user import PyObjectId


class Card(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., unique=True)
    description: str = ""
    rarity: str  # common, rare, epic, legendary, artifact
    
    # Media files
    image_url: Optional[str] = None
    gif_url: Optional[str] = None
    video_url: Optional[str] = None
    
    # Metadata
    tags: List[str] = []
    is_active: bool = True
    
    # Stats
    total_owned: int = 0  # Общее количество у всех игроков
    unique_owners: int = 0  # Количество уникальных владельцев
    
    # NFT System
    is_nft_available: bool = False  # Можно ли купить как NFT
    nft_price: int = 1000  # Цена в XP для покупки как NFT
    nft_owner_id: Optional[int] = None  # Telegram ID владельца NFT (если присвоена)
    nft_assigned_at: Optional[datetime] = None  # Когда была присвоена как NFT
    nft_transfer_count: int = 0  # Количество передач NFT
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = None  # Telegram ID админа
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
    
    def get_rarity_emoji(self) -> str:
        """Возвращает эмодзи для редкости карточки"""
        rarity_emojis = {
            "common": "⚪",
            "rare": "🔵", 
            "epic": "🟣",
            "legendary": "🟡",
            "artifact": "🔴"
        }
        return rarity_emojis.get(self.rarity, "❓")
    
    def get_media_url(self) -> Optional[str]:
        """Возвращает URL медиафайла (приоритет: video > gif > image)"""
        if self.video_url:
            return self.video_url
        if self.gif_url:
            return self.gif_url
        return self.image_url
    
    def is_nft_owned(self) -> bool:
        """Проверяет, присвоена ли карточка как NFT"""
        return self.nft_owner_id is not None
    
    def get_nft_status_text(self) -> str:
        """Возвращает текст статуса NFT"""
        if self.is_nft_owned():
            return f"💎 NFT присвоена (владелец: {self.nft_owner_id})"
        elif self.is_nft_available:
            return f"💎 Доступна для покупки как NFT за {self.nft_price} XP"
        else:
            return "📄 Обычная карточка"


class Mob(BaseModel):
    """Моб для системы боя"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., unique=True)
    description: str = ""
    level: int = Field(..., ge=1, le=50)
    
    # Battle stats
    power: int = Field(..., ge=1)  # Сила моба
    health: int = Field(..., ge=1)  # Здоровье моба
    
    # Rewards
    experience_reward: int = Field(default=10)
    coin_reward: int = Field(default=5)
    
    # Metadata
    is_active: bool = True
    difficulty: str = "normal"  # easy, normal, hard, boss
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
    
    def get_difficulty_emoji(self) -> str:
        """Возвращает эмодзи для сложности моба"""
        difficulty_emojis = {
            "easy": "🟢",
            "normal": "🟡",
            "hard": "🟠",
            "boss": "🔴"
        }
        return difficulty_emojis.get(self.difficulty, "❓")


class CardStats(BaseModel):
    """Статистика карточек"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    total_cards: int = 0
    total_unique_cards: int = 0
    cards_by_rarity: Dict[str, int] = {}
    most_popular_card: Optional[str] = None
    rarest_card: Optional[str] = None
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
