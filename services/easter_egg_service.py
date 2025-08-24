from datetime import datetime
from typing import Dict, Optional, Tuple
from loguru import logger

from models.user import User
from services.user_service import user_service


class EasterEggService:
    """Сервис для работы с пасхалками"""
    
    def __init__(self):
        # Конфигурация пасхалок: {код: (монеты, описание)}
        self.easter_eggs: Dict[str, Tuple[int, str]] = {
            "1488": (600, "Секретная награда за знание истории"),
            "52": (400, "Особая награда для избранных"),
            "1337": (250, "Награда для хакеров")
        }
    
    async def check_easter_egg(self, user: User, code: str) -> Tuple[bool, str, int]:
        """
        Проверяет пасхалку и возвращает результат
        
        Returns:
            Tuple[bool, str, int]: (успех, сообщение, количество монет)
        """
        try:
            # Проверяем, может ли пользователь попытаться
            if not user.can_attempt_easter_egg():
                remaining_attempts = 3 - user.easter_egg_attempts_today
                return False, f"❌ Превышен лимит попыток на сегодня! Осталось попыток: {remaining_attempts}", 0
            
            # Записываем попытку
            user.record_easter_egg_attempt()
            
            # Проверяем, существует ли такая пасхалка
            if code not in self.easter_eggs:
                return False, "❌ Неверный код! Попробуйте еще раз.", 0
            
            # Проверяем, не была ли уже активирована
            if user.has_activated_easter_egg(code):
                return False, "🎁 Эта пасхалка уже активирована!", 0
            
            # Активируем пасхалку
            coins, description = self.easter_eggs[code]
            user.activate_easter_egg(code)
            user.coins += coins
            
            # Сохраняем изменения
            await user_service.update_user(user)
            
            return True, f"🎉 **Пасхалка активирована!**\n\n💰 Получено: {coins} монет\n📝 {description}", coins
            
        except Exception as e:
            logger.error(f"Error checking easter egg for user {user.telegram_id}: {e}")
            return False, "❌ Произошла ошибка при проверке пасхалки", 0
    
    async def get_easter_egg_status(self, user: User) -> str:
        """Возвращает статус пасхалок для пользователя"""
        try:
            status_text = "🥚 **Пасхалки**\n\n"
            
            # Показываем активированные пасхалки
            if user.easter_eggs_activated:
                status_text += "✅ **Активированные пасхалки:**\n"
                for egg_id in user.easter_eggs_activated:
                    coins, description = self.easter_eggs.get(egg_id, (0, "Неизвестная пасхалка"))
                    status_text += f"• {egg_id} - {coins} монет ({description})\n"
                status_text += "\n"
            else:
                status_text += "🔍 Пока нет активированных пасхалок\n\n"
            
            # Показываем доступные попытки
            if user.can_attempt_easter_egg():
                remaining = 3 - user.easter_egg_attempts_today
                status_text += f"🎯 Осталось попыток сегодня: {remaining}/3"
            else:
                status_text += "⏰ Лимит попыток на сегодня исчерпан"
            
            return status_text
            
        except Exception as e:
            logger.error(f"Error getting easter egg status for user {user.telegram_id}: {e}")
            return "❌ Ошибка при получении статуса пасхалок"
    
    def get_easter_egg_hint(self) -> str:
        """Возвращает подсказку для пасхалок"""
        return (
            "🥚 **ПАСХАЛКА**\n\n"
            "🔍 Напишите в чат загадочный код и получите бонус!\n\n"
            "💡 **НАГРАДА ???** (3 вариации)\n"
            "• Секретный код 1 - 600 монет\n"
            "• Секретный код 2 - 400 монет\n"
            "• Секретный код 3 - 250 монет\n\n"
            "🎯 Каждый код можно активировать только один раз!\n"
            "⏰ Максимум 3 попытки в день\n\n"
            "🔐 Попробуйте угадать, что означают эти числа..."
        )


# Создаем экземпляр сервиса
easter_egg_service = EasterEggService()
