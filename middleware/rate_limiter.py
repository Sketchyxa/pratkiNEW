import time
from collections import defaultdict
from typing import Dict, Tuple
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
from loguru import logger


class RateLimiterMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self):
        # Словарь для хранения времени последних запросов
        # user_id -> (last_request_time, request_count_in_window)
        self.user_requests: Dict[int, Tuple[float, int]] = defaultdict(lambda: (0.0, 0))
        
        # Настройки лимитов (увеличены для большей свободы)
        self.rate_limits = {
            'default': {'requests': 30, 'window': 10},      # 30 запросов за 10 секунд (было 10)
            'callback': {'requests': 50, 'window': 10},     # 50 коллбэков за 10 секунд (было 20)
            'shop': {'requests': 10, 'window': 30},         # 10 покупок за 30 секунд (было 5)
            'daily_card': {'requests': 5, 'window': 10},    # 5 попыток за 10 секунд (было 2)
            'suggestion': {'requests': 5, 'window': 60},    # 5 предложений в минуту (было 3)
        }
    
    async def __call__(self, handler, event: TelegramObject, data: dict):
        """Основная логика middleware"""
        user_id = None
        request_type = 'default'
        
        # Определяем тип запроса и ID пользователя
        if isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            if event.data.startswith('buy_pack_'):
                request_type = 'shop'
            elif event.data == 'daily_card':
                request_type = 'daily_card'
            elif event.data.startswith('suggest_'):
                request_type = 'suggestion'
            else:
                request_type = 'callback'
        elif isinstance(event, Message):
            user_id = event.from_user.id
            if event.text and event.text.startswith('/dailycard'):
                request_type = 'daily_card'
        
        # Проверяем лимиты только для обычных пользователей
        if user_id and not self.is_admin(user_id):
            if not self.check_rate_limit(user_id, request_type):
                # Превышен лимит - блокируем запрос
                if isinstance(event, CallbackQuery):
                    await event.answer("⏰ Слишком много запросов! Подождите немного.", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("⏰ Слишком много запросов! Подождите немного.")
                
                logger.warning(f"Rate limit exceeded for user {user_id}, type: {request_type}")
                return
        
        # Пропускаем запрос дальше
        return await handler(event, data)
    
    def check_rate_limit(self, user_id: int, request_type: str) -> bool:
        """Проверяет, не превышен ли лимит запросов"""
        current_time = time.time()
        limits = self.rate_limits.get(request_type, self.rate_limits['default'])
        
        last_time, count = self.user_requests[user_id]
        
        # Если прошло больше времени чем окно - сбрасываем счетчик
        if current_time - last_time > limits['window']:
            self.user_requests[user_id] = (current_time, 1)
            return True
        
        # Если в пределах окна - проверяем лимит
        if count >= limits['requests']:
            return False
        
        # Увеличиваем счетчик
        self.user_requests[user_id] = (last_time, count + 1)
        return True
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        from config import settings
        return user_id == settings.admin_user_id
    
    def reset_user_limits(self, user_id: int):
        """Сбрасывает лимиты для пользователя (для админских команд)"""
        if user_id in self.user_requests:
            del self.user_requests[user_id]
            logger.info(f"Reset rate limits for user {user_id}")
    
    def reset_all_limits(self):
        """Сбрасывает все лимиты (для перезапуска бота)"""
        self.user_requests.clear()
        logger.info("Reset all rate limits")
    
    def get_user_stats(self, user_id: int) -> dict:
        """Возвращает статистику запросов пользователя"""
        if user_id not in self.user_requests:
            return {'requests': 0, 'last_request': 0}
        
        last_time, count = self.user_requests[user_id]
        return {
            'requests': count,
            'last_request': last_time,
            'time_since_last': time.time() - last_time
        }


# Глобальный экземпляр middleware
rate_limiter = RateLimiterMiddleware()
