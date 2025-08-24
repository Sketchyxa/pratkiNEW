from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field, BeforeValidator
from bson import ObjectId


def validate_object_id(v):
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[ObjectId, BeforeValidator(validate_object_id)]


class EventReward(BaseModel):
    """Награда за ивент"""
    coins: int = 0
    experience: int = 0
    cards: List[str] = []  # ID карточек
    special_title: Optional[str] = None  # Особое звание


class Event(BaseModel):
    """Сезонный ивент"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., description="Название ивента")
    description: str = Field(..., description="Описание ивента")
    icon: str = Field(default="🎪", description="Иконка ивента")
    
    # Временные рамки
    start_date: datetime = Field(..., description="Дата начала")
    end_date: datetime = Field(..., description="Дата окончания")
    
    # Тип ивента
    event_type: str = Field(default="collection", description="Тип ивента: collection, cards, level")
    
    # Условия
    target_type: str = Field(..., description="Тип цели: card_rarity, total_cards, specific_cards")
    target_value: Any = Field(..., description="Значение цели")
    target_data: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные")
    
    # Награды
    rewards: EventReward = Field(default_factory=EventReward)
    
    # Статистика
    total_participants: int = Field(default=0)
    total_completed: int = Field(default=0)
    
    # Настройки
    is_active: bool = Field(default=True)
    is_hidden: bool = Field(default=False, description="Скрытый ивент до старта")
    max_participants: Optional[int] = Field(default=None, description="Максимум участников")
    
    # Системные поля
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(..., description="ID админа создавшего ивент")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserEventProgress(BaseModel):
    """Прогресс пользователя в ивенте"""
    event_id: str
    user_id: int
    current_progress: int = Field(default=0)
    target_progress: int = Field(...)
    is_completed: bool = Field(default=False)
    completed_at: Optional[datetime] = None
    rewards_claimed: bool = Field(default=False)
    
    # Дополнительные данные прогресса
    progress_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Системные поля
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
