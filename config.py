import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Telegram Bot
    bot_token: str = Field(..., env="BOT_TOKEN")
    admin_user_id: int = Field(..., env="ADMIN_USER_ID")
    
    # Admin IDs (список ID администраторов)
    @property
    def admin_ids(self) -> List[int]:
        """Возвращает список ID администраторов"""
        return [self.admin_user_id]
    
    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    database_name: str = Field(default="pratki_bot", env="DATABASE_NAME")
    
    # MySQL (for migration)
    mysql_host: str = Field(default="localhost", env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT")
    mysql_user: str = Field(default="root", env="MYSQL_USER")
    mysql_password: str = Field(default="", env="MYSQL_PASSWORD")
    mysql_database: str = Field(default="pratki_old", env="MYSQL_DATABASE")
    
    # Bot Configuration
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    rate_limit_messages: int = Field(default=5, env="RATE_LIMIT_MESSAGES")
    rate_limit_callbacks: int = Field(default=10, env="RATE_LIMIT_CALLBACKS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Game Configuration
    daily_card_cooldown_hours: int = 2  # Кулдаун 2 часа
    cards_for_upgrade: int = 3
    newbie_bonus: bool = True
    
    # Card Rarities and Probabilities
    rarities: dict = {
        "common": {"probability": 69.89, "emoji": "⚪", "name": "Common"},
        "rare": {"probability": 20.0, "emoji": "🔵", "name": "Rare"},
        "epic": {"probability": 8.0, "emoji": "🟣", "name": "Epic"},
        "legendary": {"probability": 2.0, "emoji": "🟡", "name": "Legendary"},
        "artifact": {"probability": 0.1, "emoji": "🔴", "name": "Artifact"}
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
