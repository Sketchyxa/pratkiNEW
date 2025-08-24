from datetime import datetime, timedelta
from typing import List, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from models.user import User
from models.card import Card
from services.user_service import user_service


class NotificationService:
    """Сервис для отправки уведомлений пользователям"""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
    
    def set_bot(self, bot: Bot):
        """Устанавливает экземпляр бота"""
        self.bot = bot
    
    async def notify_new_card(self, card: Card) -> int:
        """
        Уведомляет всех пользователей о новой карточке
        Возвращает количество отправленных уведомлений
        """
        if not self.bot:
            logger.error("Bot instance not set for notifications")
            return 0
        
        try:
            # Получаем всех пользователей с включенными уведомлениями
            users = await user_service.get_all_users()
            active_users = [user for user in users if user.notifications_enabled]
            
            notification_text = (
                f"🆕 **Новая карточка добавлена!**\n\n"
                f"{card.get_rarity_emoji()} **{card.name}**\n\n"
                f"📝 {card.description}\n\n"
                f"⭐ **Редкость:** {card.rarity.title()}\n"
                f"🎲 **Шанс получения:** {self._get_rarity_probability(card.rarity)}%\n\n"
                f"🎴 Попробуйте получить её в ежедневной карточке или магазине!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎴 Карточка дня", callback_data="daily_card"),
                    InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")
                ],
                [InlineKeyboardButton(text="📚 Все карточки", callback_data="my_cards")]
            ])
            
            sent_count = 0
            
            for user in active_users:
                try:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=notification_text,
                        reply_markup=keyboard
                    )
                    
                    # Обновляем время последнего уведомления
                    user.last_card_notification = datetime.utcnow()
                    await user_service.update_user(user)
                    
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")
                    # Если пользователь заблокировал бота, отключаем уведомления
                    if "bot was blocked" in str(e).lower():
                        user.notifications_enabled = False
                        await user_service.update_user(user)
            
            logger.info(f"Sent new card notification to {sent_count} users")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending new card notifications: {e}")
            return 0
    
    async def notify_event_completion(self, user: User, event_name: str, reward_text: str):
        """Уведомляет пользователя о завершении ивента"""
        if not self.bot or not user.notifications_enabled:
            return
        
        try:
            notification_text = (
                f"🎉 **Поздравляем!**\n\n"
                f"Вы завершили ивент: **{event_name}**\n\n"
                f"🎁 **Награды:**\n{reward_text}\n\n"
                f"Заберите их в разделе ивентов!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎪 К ивентам", callback_data="events")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=notification_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Failed to send event completion notification: {e}")
    
    async def notify_achievement(self, user: User, achievement_name: str, points: int, coins: int):
        """Уведомляет пользователя о получении достижения"""
        if not self.bot or not user.notifications_enabled:
            return
        
        try:
            reward_parts = []
            if points > 0:
                reward_parts.append(f"⭐ {points} очков")
            if coins > 0:
                reward_parts.append(f"🪙 {coins} монет")
            
            reward_text = " + ".join(reward_parts) if reward_parts else "Престиж!"
            
            notification_text = (
                f"🏆 **Новое достижение!**\n\n"
                f"**{achievement_name}**\n\n"
                f"🎁 **Награда:** {reward_text}\n\n"
                f"Продолжайте в том же духе!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏅 Мои достижения", callback_data="achievements")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=notification_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Failed to send achievement notification: {e}")
    
    async def broadcast_message(self, message: str, admin_only: bool = False) -> int:
        """
        Рассылает сообщение всем пользователям
        Возвращает количество отправленных сообщений
        """
        if not self.bot:
            logger.error("Bot instance not set for broadcast")
            return 0
        
        try:
            if admin_only:
                from config import settings
                users = await user_service.get_users_by_ids(settings.admin_ids)
            else:
                users = await user_service.get_all_users()
                users = [user for user in users if user.notifications_enabled]
            
            sent_count = 0
            
            for user in users:
                try:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message
                    )
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to broadcast to user {user.telegram_id}: {e}")
                    if "bot was blocked" in str(e).lower():
                        user.notifications_enabled = False
                        await user_service.update_user(user)
            
            logger.info(f"Broadcast sent to {sent_count} users")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            return 0
    
    def _get_rarity_probability(self, rarity: str) -> float:
        """Получает вероятность редкости карточки"""
        from config import settings
        return settings.rarities.get(rarity, {}).get("probability", 0)


# Глобальный экземпляр сервиса
notification_service = NotificationService()
