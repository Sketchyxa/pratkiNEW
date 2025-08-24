from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated, Union
from pydantic import BaseModel, Field, BeforeValidator
from bson import ObjectId


def validate_object_id(v):
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


def validate_datetime(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            try:
                return datetime.strptime(v, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                try:
                    return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    raise ValueError(f"Invalid datetime format: {v}")
    raise ValueError(f"Invalid datetime: {v}")


PyObjectId = Annotated[ObjectId, BeforeValidator(validate_object_id)]
PyDateTime = Annotated[datetime, BeforeValidator(validate_datetime)]


class UserCard(BaseModel):
    card_id: str
    quantity: int = 1
    obtained_at: PyDateTime = Field(default_factory=datetime.utcnow)


class UserNFT(BaseModel):
    """NFT карточка пользователя - эксклюзивная присвоенная карточка"""
    card_id: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True  # Может быть продана/передана
    transfer_count: int = 0  # Количество передач между пользователями
    last_transfer_date: Optional[datetime] = None


class UserAchievement(BaseModel):
    """Достижение пользователя"""
    achievement_id: str
    earned_at: datetime = Field(default_factory=datetime.utcnow)
    progress: int = Field(default=0)  # Прогресс к получению (если многоэтапное)
    is_completed: bool = Field(default=False)
    notified: bool = Field(default=False)  # Уведомлен ли пользователь


class BattleDeck(BaseModel):
    """Боевая колода пользователя"""
    card_ids: List[str] = Field(default_factory=list, max_length=5)
    last_used: Optional[datetime] = None


class BattleProgress(BaseModel):
    """Прогресс в боях с мобами"""
    current_level: int = 1
    max_level: int = 50
    last_battle_time: Optional[datetime] = None
    battles_won: int = 0
    total_battles: int = 0


class User(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    telegram_id: int = Field(..., unique=True)
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Game stats
    experience: int = 0
    level: int = 1
    coins: int = 600  # Стартовые монеты
    total_cards: int = 0
    cards: List[UserCard] = []
    nfts: List[UserNFT] = []  # Эксклюзивные NFT карточки
    favorite_cards: List[str] = []  # ID любимых карточек (максимум 3)
    
    # Достижения
    achievements: List[UserAchievement] = []
    achievement_points: int = 0  # Общие очки достижений
    
    # Battle system
    battle_deck: BattleDeck = Field(default_factory=BattleDeck)
    battle_progress: BattleProgress = Field(default_factory=BattleProgress)
    
    # Activity tracking
    last_daily_card: Optional[datetime] = None
    first_card_received: bool = False
    newbie_bonus_received: bool = False
    
    # Daily streak tracking
    daily_streak: int = 0  # Текущая серия дней
    max_daily_streak: int = 0  # Максимальная серия дней
    last_daily_streak_date: Optional[datetime] = None  # Последний день серии
    
    # Shop and economy tracking
    pack_cooldowns: Dict[str, datetime] = Field(default_factory=dict)
    shop_purchases_count: int = 0  # Общее количество покупок в магазине
    total_coins_spent: int = 0  # Общее количество потраченных монет
    cards_sold_count: int = 0  # Количество проданных карточек
    selling_profit: int = 0  # Общая прибыль от продажи карточек
    
    # Social and suggestions
    suggestions_made: int = 0  # Количество предложенных карточек
    accepted_suggestions: int = 0  # Количество принятых предложений
    giveaway_participation: int = 0  # Участие в раздачах
    giveaway_wins: int = 0  # Победы в раздачах
    
    # Special achievements tracking
    artifact_cards_received: int = 0  # Количество полученных артефактов
    legendary_streak: int = 0  # Текущая серия легендарных карточек
    max_legendary_streak: int = 0  # Максимальная серия легендарных
    artifacts_this_month: int = 0  # Артефакты за текущий месяц
    last_month_reset: Optional[datetime] = None  # Сброс счетчика артефактов
    
    # Time-based achievements
    cards_received_today: int = 0  # Карточки полученные сегодня
    last_day_reset: Optional[datetime] = None  # Сброс дневного счетчика
    cards_received_at_hours: List[int] = Field(default_factory=list)  # Часы получения карточек
    night_cards_count: int = 0  # Карточки полученные после 22:00
    morning_cards_count: int = 0  # Карточки полученные до 06:00
    card_streak: int = 0  # Текущая серия получения карточек
    max_card_streak: int = 0  # Максимальная серия получения карточек
    
    # Event tracking
    events_completed: int = 0  # Завершенные ивенты
    total_days_played: int = 0  # Общее количество дней игры
    
    # Bans and restrictions
    is_suggestion_banned: bool = False  # Заблокирован ли для предложений карточек
    suggestion_ban_reason: Optional[str] = None
    suggestion_ban_date: Optional[datetime] = None
    
    # Easter egg system
    easter_eggs_activated: List[str] = Field(default_factory=list)  # Активированные пасхалки
    easter_egg_attempts_today: int = 0  # Попытки ввода пасхалки сегодня
    last_easter_egg_attempt: Optional[datetime] = None  # Последняя попытка ввода пасхалки
    
    # Настройки уведомлений
    notifications_enabled: bool = True  # Включены ли уведомления
    last_card_notification: Optional[datetime] = None  # Последнее уведомление о новой карточке
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        
    def calculate_level(self) -> int:
        """Вычисляет уровень пользователя на основе опыта"""
        # Прогрессивная формула: каждый уровень требует больше опыта
        if self.experience <= 0:
            return 1
        
        # Формула: уровень = 1 + корень(опыт / 50)
        # Это дает более медленный рост уровней
        level = 1 + int((self.experience / 50) ** 0.5)
        return max(1, level)
    
    def get_experience_for_level(self, level: int) -> int:
        """Возвращает количество опыта, необходимое для достижения уровня"""
        if level <= 1:
            return 0
        # Обратная формула: опыт = 50 * (уровень - 1)²
        return int(50 * (level - 1) ** 2)
    
    def get_experience_to_next_level(self) -> int:
        """Возвращает количество опыта до следующего уровня"""
        current_level = self.calculate_level()
        next_level_exp = self.get_experience_for_level(current_level + 1)
        return max(0, next_level_exp - self.experience)
    
    def get_card_count(self, card_id: str) -> int:
        """Получает количество определенной карточки у пользователя"""
        for card in self.cards:
            if card.card_id == card_id:
                return card.quantity
        return 0
    
    def has_nft(self, card_id: str) -> bool:
        """Проверяет, есть ли у пользователя NFT версия карточки"""
        return any(nft.card_id == card_id and nft.is_active for nft in self.nfts)
    
    def get_nft(self, card_id: str) -> Optional[UserNFT]:
        """Получает NFT карточку пользователя"""
        for nft in self.nfts:
            if nft.card_id == card_id and nft.is_active:
                return nft
        return None
    
    def add_card(self, card_id: str, quantity: int = 1) -> None:
        """Добавляет карточку пользователю"""
        for card in self.cards:
            if card.card_id == card_id:
                card.quantity += quantity
                self.total_cards += quantity
                return
        
        self.cards.append(UserCard(card_id=card_id, quantity=quantity))
        self.total_cards += quantity
    
    def remove_card(self, card_id: str, quantity: int = 1) -> bool:
        """Удаляет карточку у пользователя. Возвращает True если успешно"""
        for i, card in enumerate(self.cards):
            if card.card_id == card_id:
                if card.quantity >= quantity:
                    card.quantity -= quantity
                    self.total_cards -= quantity
                    if card.quantity == 0:
                        self.cards.pop(i)
                        # Также удаляем из любимых если была там
                        if card_id in self.favorite_cards:
                            self.favorite_cards.remove(card_id)
                    return True
                return False
        return False
    
    def add_experience(self, amount: int) -> int:
        """Добавляет опыт и возвращает новый уровень"""
        old_level = self.level
        self.experience += amount
        self.level = self.calculate_level()
        return self.level - old_level
    
    def add_to_favorites(self, card_id: str) -> bool:
        """Добавляет карточку в любимые (максимум 3). Возвращает True если успешно"""
        if card_id in self.favorite_cards:
            return False  # Уже в любимых
        if len(self.favorite_cards) >= 3:
            return False  # Превышен лимит
        if self.get_card_count(card_id) == 0:
            return False  # У пользователя нет этой карточки
        
        self.favorite_cards.append(card_id)
        return True
    
    def remove_from_favorites(self, card_id: str) -> bool:
        """Удаляет карточку из любимых. Возвращает True если успешно"""
        if card_id in self.favorite_cards:
            self.favorite_cards.remove(card_id)
            return True
        return False
    
    def can_battle(self) -> bool:
        """Проверяет, может ли пользователь участвовать в бою"""
        if not self.battle_deck.card_ids or len(self.battle_deck.card_ids) < 5:
            return False
        
        if self.battle_progress.last_battle_time:
            time_since_last_battle = datetime.utcnow() - self.battle_progress.last_battle_time
            return time_since_last_battle.total_seconds() >= 3600  # 1 час
        
        return True
    
    def get_deck_power(self) -> int:
        """Вычисляет общую силу боевой колоды"""
        total_power = 0
        for card_id in self.battle_deck.card_ids:
            # Получаем силу карточки по её редкости
            card = next((c for c in self.cards if c.card_id == card_id), None)
            if card:
                # Временная логика силы по редкости (будет заменена на реальную)
                power_map = {
                    "common": 200,
                    "rare": 600,
                    "epic": 1500,
                    "legendary": 3750,
                    "artifact": 9000
                }
                # Пока используем базовую силу, позже добавим реальную логику
                total_power += power_map.get("common", 200)
        return total_power
    
    def update_daily_streak(self) -> bool:
        """Обновляет серию дней. Возвращает True если серия продолжается"""
        today = datetime.utcnow().date()
        
        if self.last_daily_streak_date:
            last_date = self.last_daily_streak_date.date()
            if today == last_date:
                return True  # Уже обновлено сегодня
            elif (today - last_date).days == 1:
                # Продолжаем серию
                self.daily_streak += 1
                self.max_daily_streak = max(self.max_daily_streak, self.daily_streak)
                self.last_daily_streak_date = datetime.utcnow()
                return True
            else:
                # Сбрасываем серию
                self.daily_streak = 1
                self.last_daily_streak_date = datetime.utcnow()
                return False
        else:
            # Первый день
            self.daily_streak = 1
            self.last_daily_streak_date = datetime.utcnow()
            return True
    
    def record_card_received(self, card_rarity: str, hour: int = None) -> None:
        """Записывает получение карточки для достижений"""
        if hour is None:
            hour = datetime.utcnow().hour
        
        # Обновляем счетчики по времени
        if hour not in self.cards_received_at_hours:
            self.cards_received_at_hours.append(hour)
        
        if 22 <= hour or hour <= 6:
            self.night_cards_count += 1
        
        if 0 <= hour <= 6:
            self.morning_cards_count += 1
        
        # Обновляем счетчик артефактов
        if card_rarity == "artifact":
            self.artifact_cards_received += 1
            self.artifacts_this_month += 1
        
        # Обновляем серию легендарных карточек
        if card_rarity == "legendary":
            self.legendary_streak += 1
            self.max_legendary_streak = max(self.max_legendary_streak, self.legendary_streak)
        else:
            self.legendary_streak = 0
        
        # Обновляем общую серию карточек
        self.card_streak += 1
        self.max_card_streak = max(self.max_card_streak, self.card_streak)
    
    def reset_daily_counters(self) -> None:
        """Сбрасывает дневные счетчики"""
        today = datetime.utcnow().date()
        
        if self.last_day_reset is None or self.last_day_reset.date() != today:
            self.cards_received_today = 0
            self.last_day_reset = datetime.utcnow()
    
    def reset_monthly_counters(self) -> None:
        """Сбрасывает месячные счетчики"""
        now = datetime.utcnow()
        current_month = (now.year, now.month)
        
        if self.last_month_reset is None:
            self.last_month_reset = now
            return
        
        last_month = (self.last_month_reset.year, self.last_month_reset.month)
        if current_month != last_month:
            self.artifacts_this_month = 0
            self.last_month_reset = now
    
    def increment_cards_today(self) -> None:
        """Увеличивает счетчик карточек за сегодня"""
        self.reset_daily_counters()
        self.cards_received_today += 1
    
    def get_unique_hours_count(self) -> int:
        """Возвращает количество уникальных часов получения карточек"""
        return len(set(self.cards_received_at_hours))
    
    def has_received_card_at_hour(self, hour: int) -> bool:
        """Проверяет, получал ли пользователь карточку в определенный час"""
        return hour in self.cards_received_at_hours
    
    def has_activated_easter_egg(self, easter_egg_id: str) -> bool:
        """Проверяет, активирована ли пасхалка"""
        return easter_egg_id in self.easter_eggs_activated
    
    def activate_easter_egg(self, easter_egg_id: str) -> bool:
        """Активирует пасхалку. Возвращает True если успешно (не была активирована ранее)"""
        if easter_egg_id not in self.easter_eggs_activated:
            self.easter_eggs_activated.append(easter_egg_id)
            return True
        return False
    
    def can_attempt_easter_egg(self) -> bool:
        """Проверяет, может ли пользователь попытаться ввести пасхалку"""
        today = datetime.utcnow().date()
        
        # Сбрасываем счетчик попыток если новый день
        if self.last_easter_egg_attempt:
            last_attempt_date = self.last_easter_egg_attempt.date()
            if today != last_attempt_date:
                self.easter_egg_attempts_today = 0
        
        return self.easter_egg_attempts_today < 3
    
    def record_easter_egg_attempt(self) -> None:
        """Записывает попытку ввода пасхалки"""
        self.easter_egg_attempts_today += 1
        self.last_easter_egg_attempt = datetime.utcnow()
