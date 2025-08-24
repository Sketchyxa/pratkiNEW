from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from models.user import PyObjectId


class Achievement(BaseModel):
    """Модель достижения"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Основная информация
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    icon: str = Field(default="🏆")
    category: str = Field(default="general")  # general, collection, economy, social, special
    
    # Условия получения
    condition_type: str = Field(...)  # cards_count, specific_card, level, coins, experience, days_active, etc.
    condition_value: int = Field(default=1)
    condition_data: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Дополнительные параметры
    
    # Награды
    reward_coins: int = Field(default=0)
    reward_experience: int = Field(default=0)
    reward_card_id: Optional[str] = None  # ID специальной карточки
    
    # Метаданные
    is_hidden: bool = Field(default=False)  # Скрытое достижение
    is_active: bool = Field(default=True)
    difficulty: str = Field(default="normal")  # easy, normal, hard, legendary
    points: int = Field(default=10)  # Очки достижений
    
    # Статистика
    total_earned: int = Field(default=0)  # Сколько раз получено
    first_earned_by: Optional[int] = None  # ID первого получившего
    first_earned_at: Optional[datetime] = None
    
    # Временные метки
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str}
    
    def get_difficulty_emoji(self) -> str:
        """Возвращает эмодзи сложности"""
        emoji_map = {
            "easy": "🟢",
            "normal": "🟡", 
            "hard": "🟠",
            "legendary": "🔴"
        }
        return emoji_map.get(self.difficulty, "🟡")
    
    def get_category_emoji(self) -> str:
        """Возвращает эмодзи категории"""
        emoji_map = {
            "general": "🏆",
            "collection": "🎴",
            "economy": "💰",
            "social": "👥",
            "special": "⭐"
        }
        return emoji_map.get(self.category, "🏆")



