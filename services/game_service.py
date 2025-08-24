import random
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from loguru import logger

from models.user import User
from models.card import Card
from services.user_service import user_service
from services.card_service import card_service
from config import settings


class GameService:
    """Сервис игровой логики"""
    
    async def give_daily_card(self, user: User) -> Tuple[Optional[Card], bool, str]:
        """
        Выдача ежедневной карточки
        Возвращает: (карточка, бонусная_карточка_выдана, сообщение)
        """
        try:
            # Проверяем кулдаун
            if not await user_service.can_get_daily_card(user):
                cooldown_hours = settings.daily_card_cooldown_hours
                return None, False, f"❌ Следующую карточку можно получить через {cooldown_hours} часов!"
            
            # Получаем случайную карточку
            card = await card_service.get_random_card()
            if not card:
                return None, False, "❌ Карточки временно недоступны"
            
            # Добавляем карточку пользователю
            await user_service.add_card_to_user(user, str(card.id))
            await user_service.update_daily_card_time(user)
            
            # Обновляем счетчики для достижений
            user.update_daily_streak()
            user.increment_cards_today()
            user.record_card_received(card.rarity)
            user.reset_monthly_counters()
            
            # Обновляем статистику карточки
            await card_service.update_card_stats(card.name, 1, 
                                               1 if user.get_card_count(str(card.id)) == 1 else 0)
            
            # Бонус для новичков
            bonus_card = False
            if settings.newbie_bonus and not user.first_card_received:
                user.first_card_received = True
                await user_service.update_user(user)
                
                # Выдаем бонусную карточку
                bonus_card_obj = await card_service.get_random_card()
                if bonus_card_obj:
                    await user_service.add_card_to_user(user, str(bonus_card_obj.id))
                    await card_service.update_card_stats(bonus_card_obj.name, 1, 
                                                       1 if user.get_card_count(str(bonus_card_obj.id)) == 1 else 0)
                    bonus_card = True
            
            # Добавляем опыт
            exp_gained = 10
            if card.rarity == "rare":
                exp_gained = 25
            elif card.rarity == "epic":
                exp_gained = 50
            elif card.rarity == "legendary":
                exp_gained = 100
            elif card.rarity == "artifact":
                exp_gained = 250
            
            level_up = await user_service.add_experience(user, exp_gained)
            
            # Добавляем монеты за карточку
            coins_gained = 5
            if card.rarity == "rare":
                coins_gained = 10
            elif card.rarity == "epic":
                coins_gained = 20
            elif card.rarity == "legendary":
                coins_gained = 50
            elif card.rarity == "artifact":
                coins_gained = 100
            
            user.coins += coins_gained
            await user_service.update_user(user)
            
            # Проверяем достижения после получения карточки
            try:
                from handlers.achievement_handlers import check_and_notify_achievements
                await check_and_notify_achievements(user, None)  # bot будет передан позже
            except Exception as achievement_error:
                logger.error(f"Error checking achievements after daily card: {achievement_error}")
            
            # Проверяем ивенты после получения карточки
            try:
                from handlers.event_handlers import check_and_notify_events
                await check_and_notify_events(user)
            except Exception as event_error:
                logger.error(f"Error checking events after daily card: {event_error}")
            
            # Красивое сообщение в стиле оригинального бота
            username = user.username if user.username else "Anonymous"
            rarity_name = settings.rarities.get(card.rarity, {}).get("name", card.rarity.title())
            
            # Вычисляем время до следующей карточки
            if settings.daily_card_cooldown_hours > 0:
                next_card_time = user.last_daily_card + timedelta(hours=settings.daily_card_cooldown_hours)
                remaining = next_card_time - datetime.utcnow()
                if remaining.total_seconds() > 0:
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    cooldown_text = f"🔁 Следующая попытка: через {hours}ч {minutes}м"
                else:
                    cooldown_text = "🔁 Следующая карточка: доступна сейчас!"
            else:
                cooldown_text = "🔁 Следующая карточка: доступна сейчас!"
            
            message = (
                f"🎉 @{username} получил карточку:\n"
                f"{card.get_rarity_emoji()} **{card.name}**\n"
                f"🔹 Редкость: {rarity_name}\n"
                f"📝 {card.description}\n"
                f"🧠 +{exp_gained} опыта\n"
                f"🪙 +{coins_gained} монет\n\n"
                f"👑 Всего карточек у тебя: {user.total_cards + 1}\n"
                f"{cooldown_text}"
            )
            
            if level_up > 0:
                message += f"\n\n🆙 **НОВЫЙ УРОВЕНЬ: {user.level}!**"
            
            if bonus_card:
                message += f"\n\n🎁 **Бонусная карточка для новичка!**"
            
            return card, bonus_card, message
            
        except Exception as e:
            logger.error(f"Error giving daily card to user {user.telegram_id}: {e}")
            return None, False, "❌ Произошла ошибка при получении карточки"
    
    async def upgrade_cards(self, user: User, card_name: str) -> Tuple[bool, str]:
        """
        Улучшение карточек (3 одинаковые -> 1 следующей редкости)
        Возвращает: (успех, сообщение)
        """
        try:
            # Находим карточку
            card = await card_service.get_card_by_name(card_name)
            if not card:
                return False, f"❌ Карточка '{card_name}' не найдена"
            
            # Проверяем количество карточек у пользователя
            user_card_count = user.get_card_count(str(card.id))
            if user_card_count < settings.cards_for_upgrade:
                return False, f"❌ Недостаточно карточек. Нужно: {settings.cards_for_upgrade}, есть: {user_card_count}"
            
            # Проверяем возможность улучшения
            target_rarity = await card_service.get_upgrade_result(card.rarity)
            if not target_rarity:
                return False, f"❌ Карточки редкости '{card.rarity}' нельзя улучшить"
            
            # Удаляем исходные карточки
            success = await user_service.remove_card_from_user(user, str(card.id), settings.cards_for_upgrade)
            if not success:
                return False, "❌ Ошибка при удалении карточек"
            
            # Обновляем статистику исходной карточки
            await card_service.update_card_stats(card.name, -settings.cards_for_upgrade)
            
            # Получаем случайную карточку новой редкости
            new_card = await card_service.get_random_card_by_rarity(target_rarity)
            if not new_card:
                # Возвращаем карточки обратно в случае ошибки
                await user_service.add_card_to_user(user, str(card.id), settings.cards_for_upgrade)
                return False, f"❌ Нет доступных карточек редкости '{target_rarity}'"
            
            # Добавляем новую карточку
            await user_service.add_card_to_user(user, str(new_card.id))
            await card_service.update_card_stats(new_card.name, 1, 
                                               1 if user.get_card_count(str(new_card.id)) == 1 else 0)
            
            # Добавляем бонусный опыт
            bonus_exp = 50 + (len(settings.rarities) - list(settings.rarities.keys()).index(target_rarity)) * 25
            level_up = await user_service.add_experience(user, bonus_exp)
            
            username = user.username if user.username else "Anonymous"
            old_rarity = settings.rarities.get(card.rarity, {}).get("name", card.rarity.title())
            new_rarity = settings.rarities.get(new_card.rarity, {}).get("name", new_card.rarity.title())
            
            message = (
                f"🔄 @{username} улучшил карточки!\n\n"
                f"📤 **Отдал:** {settings.cards_for_upgrade}x {card.get_rarity_emoji()} {card.name}\n"
                f"📥 **Получил:** 1x {new_card.get_rarity_emoji()} **{new_card.name}**\n"
                f"🔹 Редкость: {old_rarity} → {new_rarity}\n"
                f"📝 {new_card.description}\n"
                f"🧠 +{bonus_exp} опыта\n\n"
                f"👑 Всего карточек: {user.total_cards}"
            )
            
            if level_up > 0:
                message += f"\n\n🆙 **НОВЫЙ УРОВЕНЬ: {user.level}!**"
            
            return True, message
            
        except Exception as e:
            logger.error(f"Error upgrading cards for user {user.telegram_id}: {e}")
            return False, "❌ Произошла ошибка при улучшении карточек"
    
    async def handle_artifact_effect(self, user: User) -> Tuple[bool, str]:
        """
        Обработка эффекта артефактной карточки
        Возвращает: (произошел_эффект, описание_эффекта)
        """
        try:
            if not user.cards:
                return False, ""
            
            # 50% шанс на бонус или штраф
            is_bonus = random.choice([True, False])
            
            if is_bonus:
                # Бонус: дополнительная случайная карточка
                bonus_card = await card_service.get_random_card()
                if bonus_card:
                    await user_service.add_card_to_user(user, str(bonus_card.id))
                    await card_service.update_card_stats(bonus_card.name, 1, 
                                                       1 if user.get_card_count(str(bonus_card.id)) == 1 else 0)
                    return True, (
                        f"🎁 **АРТЕФАКТНЫЙ БОНУС!**\n"
                        f"✨ Дополнительная карточка: {bonus_card.get_rarity_emoji()} **{bonus_card.name}**\n"
                        f"📝 {bonus_card.description}"
                    )
            else:
                # Штраф: потеря случайной карточки
                if user.cards:
                    random_user_card = random.choice(user.cards)
                    card = await card_service.get_card_by_id(random_user_card.card_id)
                    
                    if card and await user_service.remove_card_from_user(user, str(card.id), 1):
                        await card_service.update_card_stats(card.name, -1)
                        return True, (
                            f"💀 **АРТЕФАКТНОЕ ПРОКЛЯТИЕ!**\n"
                            f"❌ Потеряна карточка: {card.get_rarity_emoji()} **{card.name}**\n"
                            f"📝 {card.description}\n"
                            f"😱 Такова цена артефактной магии..."
                        )
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error handling artifact effect for user {user.telegram_id}: {e}")
            return False, ""
    
    async def get_user_collection(self, user: User, page: int = 1, 
                                 page_size: int = 10) -> Tuple[List[Tuple[Card, int]], int, int]:
        """
        Получение коллекции пользователя с пагинацией
        Возвращает: (список_(карточка, количество), общее_количество, всего_страниц)
        """
        try:
            logger.info(f"Getting collection for user with {len(user.cards) if user.cards else 0} cards")
            
            if not user.cards:
                logger.warning(f"User has no cards in user.cards list")
                return [], 0, 0
            
            # Получаем информацию о карточках (только с количеством > 0)
            collection = []
            for user_card in user.cards:
                logger.info(f"Processing user card: {user_card.card_id}, quantity: {user_card.quantity}")
                if user_card.quantity > 0:  # Только карточки с количеством больше 0
                    card = await card_service.get_card_by_id(user_card.card_id)
                    if card:
                        logger.info(f"Found card: {card.name}")
                        collection.append((card, user_card.quantity))
                    else:
                        logger.warning(f"Card not found for ID: {user_card.card_id}")
            
            # Сортируем по редкости и названию
            rarity_order = list(settings.rarities.keys())
            collection.sort(key=lambda x: (rarity_order.index(x[0].rarity), x[0].name))
            
            # Пагинация
            total_items = len(collection)
            total_pages = (total_items + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            return collection[start_idx:end_idx], total_items, total_pages
            
        except Exception as e:
            logger.error(f"Error getting user collection {user.telegram_id}: {e}")
            return [], 0, 0


# Глобальный экземпляр сервиса
game_service = GameService()
