from datetime import datetime
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger

from models.user import User
from models.card import Mob
from services.user_service import user_service
from services.card_service import card_service
from services.battle_service import battle_service

router = Router()


@router.callback_query(F.data == "battle_menu")
async def battle_menu(callback: CallbackQuery):
    """Главное меню боевой системы"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Проверяем возможность боя
        can_battle = user.can_battle()
        time_left = ""
        
        if not can_battle and user.battle_progress.last_battle_time:
            time_passed = (datetime.utcnow() - user.battle_progress.last_battle_time).total_seconds()
            time_left_seconds = max(0, 3600 - time_passed)
            if time_left_seconds > 0:
                minutes = int(time_left_seconds // 60)
                seconds = int(time_left_seconds % 60)
                time_left = f"\n⏰ Следующий бой через: {minutes:02d}:{seconds:02d}"
        
        # Получаем доступных мобов
        available_mobs = await battle_service.get_available_mobs(user)
        
        # Получаем силу колоды
        deck_power = await battle_service.get_user_deck_power(user)
        
        # Формируем текст
        text = (
            f"⚔️ **Боевая система**\n\n"
            f"🏆 Ваш уровень: {user.battle_progress.current_level}/50\n"
            f"💪 Побед: {user.battle_progress.battles_won}/{user.battle_progress.total_battles}\n"
            f"🎴 Карт в колоде: {len(user.battle_deck.card_ids)}/5\n"
            f"💪 Сила колоды: {deck_power}\n"
            f"{time_left}\n\n"
        )
        
        if not user.battle_deck.card_ids or len(user.battle_deck.card_ids) < 5:
            text += "❌ **Соберите колоду из 5 карт для участия в боях!**\n\n"
        elif not can_battle:
            text += "⏰ **Подождите перед следующим боем**\n\n"
        else:
            text += "✅ **Готов к бою!**\n\n"
        
        # Добавляем информацию о доступных мобах
        if available_mobs:
            text += "🎯 **Доступные мобы:**\n"
            for mob in available_mobs[:3]:
                can_fight = await battle_service.can_battle_mob(user, mob.level)
                status = "✅" if can_fight else "🔒"
                text += f"{status} {mob.name} (Сила: {mob.power})\n"
            text += "\n"
        
        # Создаем кнопки
        keyboard = []
        
        # Кнопка управления колодой
        keyboard.append([
            InlineKeyboardButton(
                text="🎴 Управление колодой", 
                callback_data="battle_deck_manage"
            )
        ])
        
        # Кнопки мобов (показываем только доступных)
        if available_mobs:
            mob_buttons = []
            for mob in available_mobs[:3]:  # Показываем максимум 3 моба
                can_fight = await battle_service.can_battle_mob(user, mob.level)
                button_text = f"{mob.get_difficulty_emoji()} {mob.name} ({mob.power})"
                if not can_fight:
                    button_text += " 🔒"
                
                mob_buttons.append(
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"battle_mob_{mob.level}"
                    )
                )
            
            # Разбиваем на ряды по 2 кнопки
            for i in range(0, len(mob_buttons), 2):
                row = mob_buttons[i:i+2]
                keyboard.append(row)
        
        # Кнопка статистики
        keyboard.append([
            InlineKeyboardButton(
                text="📊 Статистика боев", 
                callback_data="battle_stats"
            )
        ])
        
        # Кнопка возврата
        keyboard.append([
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(text, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in battle_menu: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data == "battle_deck_manage")
async def battle_deck_manage(callback: CallbackQuery):
    """Управление боевой колодой"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Получаем карты пользователя
        user_cards = []
        for user_card in user.cards:
            try:
                card_info = await card_service.get_card_by_id(user_card.card_id)
                if card_info:
                    user_cards.append({
                        "card": card_info,
                        "quantity": user_card.quantity
                    })
            except:
                continue
        
        # Сортируем по редкости (от сильных к слабым)
        rarity_order = {"artifact": 5, "legendary": 4, "epic": 3, "rare": 2, "common": 1}
        user_cards.sort(key=lambda x: rarity_order.get(x["card"].rarity, 0), reverse=True)
        
        text = "🎴 **Управление боевой колодой**\n\n"
        
        if user.battle_deck.card_ids:
            text += "**Текущая колода:**\n"
            for i, card_id in enumerate(user.battle_deck.card_ids, 1):
                try:
                    card_info = await card_service.get_card_by_id(card_id)
                    if card_info:
                        text += f"{i}. {card_info.get_rarity_emoji()} {card_info.name}\n"
                except:
                    text += f"{i}. ❓ Неизвестная карта\n"
            text += "\n"
        
        text += f"**Ваши карты:** ({len(user_cards)} шт.)\n"
        text += "Выберите карты для колоды (максимум 5):\n\n"
        
        # Создаем кнопки для карт
        keyboard = []
        
        # Показываем карты пользователя
        for user_card_data in user_cards[:10]:  # Показываем первые 10 карт
            card = user_card_data["card"]
            quantity = user_card_data["quantity"]
            
            # Проверяем, есть ли карта уже в колоде
            in_deck = str(card.id) in user.battle_deck.card_ids
            
            button_text = f"{card.get_rarity_emoji()} {card.name} ({quantity})"
            if in_deck:
                button_text += " ✅"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"deck_card_{card.id}"
                )
            ])
        
        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton(text="🗑️ Очистить колоду", callback_data="deck_clear"),
            InlineKeyboardButton(text="🎲 Автозаполнение", callback_data="deck_auto")
        ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")
        ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(text, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in battle_deck_manage: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("deck_card_"))
async def deck_card_toggle(callback: CallbackQuery):
    """Добавление/удаление карты из колоды"""
    try:
        card_id = callback.data.replace("deck_card_", "")
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Проверяем, есть ли карта у пользователя
        if not user.get_card_count(card_id):
            await callback.answer("❌ У вас нет этой карты")
            return
        
        # Добавляем или удаляем карту из колоды
        if card_id in user.battle_deck.card_ids:
            user.battle_deck.card_ids.remove(card_id)
            await callback.answer("🗑️ Карта удалена из колоды")
        else:
            if len(user.battle_deck.card_ids) >= 5:
                await callback.answer("❌ Колода уже полная (максимум 5 карт)")
                return
            user.battle_deck.card_ids.append(card_id)
            await callback.answer("✅ Карта добавлена в колоду")
        
        # Сохраняем изменения
        await user_service.update_user(user)
        
        # Обновляем меню
        await battle_deck_manage(callback)
        
    except Exception as e:
        logger.error(f"Error in deck_card_toggle: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data == "deck_clear")
async def deck_clear(callback: CallbackQuery):
    """Очистка колоды"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        user.battle_deck.card_ids.clear()
        await user_service.update_user(user)
        
        await callback.answer("🗑️ Колода очищена")
        await battle_deck_manage(callback)
        
    except Exception as e:
        logger.error(f"Error in deck_clear: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data == "deck_auto")
async def deck_auto_fill(callback: CallbackQuery):
    """Автозаполнение колоды лучшими картами"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Получаем все карты пользователя
        user_cards = []
        for user_card in user.cards:
            try:
                card_info = await card_service.get_card_by_id(user_card.card_id)
                if card_info:
                    user_cards.append({
                        "card": card_info,
                        "quantity": user_card.quantity
                    })
            except:
                continue
        
        # Сортируем по редкости и выбираем лучшие
        rarity_order = {"artifact": 5, "legendary": 4, "epic": 3, "rare": 2, "common": 1}
        user_cards.sort(key=lambda x: rarity_order.get(x["card"].rarity, 0), reverse=True)
        
        # Заполняем колоду лучшими картами
        user.battle_deck.card_ids = [str(card_data["card"].id) for card_data in user_cards[:5]]
        
        await user_service.update_user(user)
        
        await callback.answer("🎲 Колода автозаполнена лучшими картами")
        await battle_deck_manage(callback)
        
    except Exception as e:
        logger.error(f"Error in deck_auto_fill: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("battle_mob_"))
async def battle_mob(callback: CallbackQuery):
    """Бой с мобом"""
    try:
        mob_level = int(callback.data.replace("battle_mob_", ""))
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Проверяем возможность боя
        if not await battle_service.can_battle_mob(user, mob_level):
            await callback.answer("❌ Вы не можете сражаться с этим мобом")
            return
        
        # Проводим бой
        victory, message, rewards = await battle_service.battle_mob(user, mob_level)
        
        # Сохраняем изменения пользователя
        await user_service.update_user(user)
        
        # Создаем кнопки
        keyboard = []
        if victory:
            keyboard.append([
                InlineKeyboardButton(text="🎉 Продолжить", callback_data="battle_menu")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(text="💪 Попробовать снова", callback_data=f"battle_mob_{mob_level}"),
                InlineKeyboardButton(text="🔙 К мобам", callback_data="battle_menu")
            ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(message, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in battle_mob: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data == "battle_stats")
async def battle_stats(callback: CallbackQuery):
    """Статистика боев"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Вычисляем статистику
        win_rate = 0
        if user.battle_progress.total_battles > 0:
            win_rate = (user.battle_progress.battles_won / user.battle_progress.total_battles) * 100
        
        # Получаем силу колоды
        deck_power = await battle_service.get_user_deck_power(user)
        
        text = (
            f"📊 **Статистика боев**\n\n"
            f"🏆 Уровень: {user.battle_progress.current_level}/50\n"
            f"⚔️ Всего боев: {user.battle_progress.total_battles}\n"
            f"🎉 Побед: {user.battle_progress.battles_won}\n"
            f"💀 Поражений: {user.battle_progress.total_battles - user.battle_progress.battles_won}\n"
            f"📈 Процент побед: {win_rate:.1f}%\n\n"
            f"💪 Сила колоды: {deck_power}\n"
            f"🎴 Карт в колоде: {len(user.battle_deck.card_ids)}/5\n\n"
        )
        
        if user.battle_deck.card_ids:
            text += "**Текущая колода:**\n"
            for i, card_id in enumerate(user.battle_deck.card_ids, 1):
                try:
                    card_info = await card_service.get_card_by_id(card_id)
                    if card_info:
                        text += f"{i}. {card_info.get_rarity_emoji()} {card_info.name}\n"
                except:
                    text += f"{i}. ❓ Неизвестная карта\n"
        
        keyboard = [
            [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
        ]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(text, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in battle_stats: {e}")
        await callback.answer("❌ Произошла ошибка")
