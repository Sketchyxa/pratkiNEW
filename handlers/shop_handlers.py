from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger
import random

from models.user import User
from services.user_service import user_service
from services.card_service import card_service
from services.game_service import game_service

router = Router()


async def safe_edit_message(callback, text: str, reply_markup=None, success_message: str = None):
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        if success_message:
            await callback.answer(success_message)
        else:
            await callback.answer()
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("📊 Данные актуальны")
        elif "there is no text in the message to edit" in str(e):
            # Если сообщение содержит медиа, отправляем новое
            await callback.message.answer(text, reply_markup=reply_markup)
            await callback.answer()
        else:
            await callback.answer("❌ Ошибка при обновлении")
            logger.error(f"Error editing message: {e}")


@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery):
    """Магазин карточек"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Проверяем кулдауны для отображения
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        
        pack_info = {
            "starter": {"name": "Стартер пак", "cost": 25, "desc": "1 гарантированная Common", "cooldown": 0.2},
            "basic": {"name": "Базовый пак", "cost": 50, "desc": "1 случайная карточка", "cooldown": 0.5},
            "premium": {"name": "Премиум пак", "cost": 100, "desc": "2 карточки + шанс Epic", "cooldown": 1},
            "elite": {"name": "Элитный пак", "cost": 200, "desc": "3 карточки + Rare", "cooldown": 2},
            "super": {"name": "Супер пак", "cost": 350, "desc": "5 карточек + Epic", "cooldown": 3},
            "mega": {"name": "Мега пак", "cost": 600, "desc": "8 карточек + Legendary", "cooldown": 5},
            "ultra": {"name": "Ультра пак", "cost": 1000, "desc": "12 карточек + 2 Legendary", "cooldown": 10},
            "legendary": {"name": "Легендарный пак", "cost": 1500, "desc": "15 карточек + Legendary", "cooldown": 15},
            "artifact": {"name": "Артефактный пак", "cost": 2500, "desc": "20 карточек + Artifact", "cooldown": 30},
            "divine": {"name": "Божественный пак", "cost": 5000, "desc": "30 карточек + Artifact", "cooldown": 60}
        }
        
        shop_text = f"🏪 **Магазин карточек**\n\n🪙 **Ваши монеты:** {user.coins} 💰\n\n🎁 **Доступные паки:**\n\n"
        
        for pack_type, info in pack_info.items():
            cooldown_text = ""
            if pack_type in user.pack_cooldowns:
                last_purchase = user.pack_cooldowns[pack_type]
                cooldown_end = last_purchase + timedelta(minutes=info["cooldown"])
                
                if now < cooldown_end:
                    time_left = cooldown_end - now
                    minutes_left = int(time_left.total_seconds() // 60)
                    seconds_left = int(time_left.total_seconds() % 60)
                    cooldown_text = f" ⏰ ({minutes_left}м {seconds_left}с)"
            
            shop_text += f"📦 **{info['name']}** - {info['cost']} 🪙{cooldown_text}\n"
            shop_text += f"• {info['desc']} • Кулдаун: {info['cooldown']}м\n\n"
        
        shop_text += "🎲 Шанс на Artifact: 0.1%"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Стартер (25 🪙)", callback_data="buy_pack_starter"),
                InlineKeyboardButton(text="📄 Базовый (50 🪙)", callback_data="buy_pack_basic")
            ],
            [
                InlineKeyboardButton(text="💎 Премиум (100 🪙)", callback_data="buy_pack_premium"),
                InlineKeyboardButton(text="⭐ Элитный (200 🪙)", callback_data="buy_pack_elite")
            ],
            [
                InlineKeyboardButton(text="🎰 Супер (350 🪙)", callback_data="buy_pack_super"),
                InlineKeyboardButton(text="🔥 Мега (600 🪙)", callback_data="buy_pack_mega")
            ],
            [
                InlineKeyboardButton(text="💫 Ультра (1000 🪙)", callback_data="buy_pack_ultra"),
                InlineKeyboardButton(text="👑 Легендарный (1500 🪙)", callback_data="buy_pack_legendary")
            ],
            [
                InlineKeyboardButton(text="🔴 Артефактный (2500 🪙)", callback_data="buy_pack_artifact"),
                InlineKeyboardButton(text="✨ Божественный (5000 🪙)", callback_data="buy_pack_divine")
            ],
            [
                InlineKeyboardButton(text="🎯 Выбрать редкость", callback_data="shop_rarity"),
                InlineKeyboardButton(text="💰 Продать карточки", callback_data="sell_cards_menu")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ])
        
        await safe_edit_message(callback, shop_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in shop menu: {e}")
        await callback.answer("❌ Ошибка при загрузке магазина", show_alert=True)


@router.callback_query(F.data.startswith("buy_pack_"))
async def buy_pack(callback: CallbackQuery):
    """Покупка пака карточек"""
    try:
        pack_type = callback.data.split("_")[-1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Настройки паков с кулдаунами (уменьшены для большей свободы)
        pack_configs = {
            "starter": {"cost": 25, "cards": 1, "guaranteed": "common", "boost": False, "cooldown_minutes": 0.2},
            "basic": {"cost": 50, "cards": 1, "guaranteed": None, "boost": False, "cooldown_minutes": 0.5},
            "premium": {"cost": 100, "cards": 2, "guaranteed": None, "boost": True, "cooldown_minutes": 1},
            "elite": {"cost": 200, "cards": 3, "guaranteed": "rare", "boost": True, "cooldown_minutes": 2},
            "super": {"cost": 350, "cards": 5, "guaranteed": "epic", "boost": True, "cooldown_minutes": 3},
            "mega": {"cost": 600, "cards": 8, "guaranteed": "legendary", "boost": True, "cooldown_minutes": 5},
            "ultra": {"cost": 1000, "cards": 12, "guaranteed": "legendary", "boost": True, "extra_legendary": True, "cooldown_minutes": 10},
            "legendary": {"cost": 1500, "cards": 15, "guaranteed": "legendary", "boost": True, "extra_legendary": True, "cooldown_minutes": 15},
            "artifact": {"cost": 2500, "cards": 20, "guaranteed": "artifact", "boost": True, "extra_legendary": True, "cooldown_minutes": 30},
            "divine": {"cost": 5000, "cards": 30, "guaranteed": "artifact", "boost": True, "extra_legendary": True, "cooldown_minutes": 60}
        }
        
        if pack_type not in pack_configs:
            await callback.answer("❌ Неизвестный тип пака", show_alert=True)
            return
        
        config = pack_configs[pack_type]
        
        # Проверяем кулдаун пака
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        
        if pack_type in user.pack_cooldowns:
            last_purchase = user.pack_cooldowns[pack_type]
            cooldown_end = last_purchase + timedelta(minutes=config["cooldown_minutes"])
            
            if now < cooldown_end:
                time_left = cooldown_end - now
                minutes_left = int(time_left.total_seconds() // 60)
                seconds_left = int(time_left.total_seconds() % 60)
                
                await callback.answer(
                    f"⏰ Пак на кулдауне! Осталось: {minutes_left}м {seconds_left}с",
                    show_alert=True
                )
                return
        
        # Проверяем достаточно ли монет
        if user.coins < config["cost"]:
            await callback.answer(
                f"❌ Недостаточно монет! Нужно: {config['cost']} 🪙, есть: {user.coins} 🪙",
                show_alert=True
            )
            return
        
        # Списываем монеты и устанавливаем кулдаун
        user.coins -= config["cost"]
        user.pack_cooldowns[pack_type] = now
        await user_service.update_user(user)
        
        # Открываем пак
        opened_cards = []
        
        # Добавляем гарантированную карточку
        if config["guaranteed"]:
            guaranteed_card = await card_service.get_random_card_by_rarity(config["guaranteed"])
            if guaranteed_card:
                opened_cards.append(guaranteed_card)
                await user_service.add_card_to_user(user, str(guaranteed_card.id))
                await card_service.update_card_stats(guaranteed_card.name, 1, 1)
        
        # Добавляем дополнительную legendary для ультра пака
        if config.get("extra_legendary"):
            extra_leg = await card_service.get_random_card_by_rarity("legendary")
            if extra_leg:
                opened_cards.append(extra_leg)
                await user_service.add_card_to_user(user, str(extra_leg.id))
                await card_service.update_card_stats(extra_leg.name, 1, 1)
        
        # Добавляем остальные карточки
        remaining_cards = config["cards"] - (1 if config["guaranteed"] else 0) - (1 if config.get("extra_legendary") else 0)
        
        for _ in range(remaining_cards):
            if config["boost"]:
                # Повышенный шанс на редкие карточки
                rand = random.uniform(0, 100)
                if pack_type == "ultra":
                    # Ультра пак - еще больше шансов на редкие
                    if rand <= 20:  # 20% Common
                        rarity = "common"
                    elif rand <= 45:  # 25% Rare
                        rarity = "rare"
                    elif rand <= 75:  # 30% Epic
                        rarity = "epic"
                    elif rand <= 98:  # 23% Legendary
                        rarity = "legendary"
                    else:  # 2% Artifact
                        rarity = "artifact"
                else:
                    # Обычные усиленные паки
                    if rand <= 40:  # 40% вместо 69.89%
                        rarity = "common"
                    elif rand <= 65:  # 25% вместо 20%
                        rarity = "rare"
                    elif rand <= 85:  # 20% вместо 8%
                        rarity = "epic"
                    elif rand <= 98:  # 13% вместо 2%
                        rarity = "legendary"
                    else:  # 2% вместо 0.1%
                        rarity = "artifact"
                
                card = await card_service.get_random_card_by_rarity(rarity)
            else:
                # Ограничиваем базовый пак только Common-Rare
                if pack_type == "basic":
                    rand = random.uniform(0, 100)
                    if rand <= 80:
                        rarity = "common"
                    else:
                        rarity = "rare"
                    card = await card_service.get_random_card_by_rarity(rarity)
                else:
                    card = await card_service.get_random_card()
            
            if card:
                opened_cards.append(card)
                await user_service.add_card_to_user(user, str(card.id))
                await card_service.update_card_stats(card.name, 1, 1)
        
        # Формируем сообщение о результатах
        result_text = f"🎉 **Пак '{pack_type.title()}' открыт!**\n\n"
        result_text += f"🪙 Потрачено: {config['cost']} монет\n"
        result_text += f"🎴 Получено карточек: {len(opened_cards)}\n\n"
        
        for i, card in enumerate(opened_cards, 1):
            result_text += f"{i}. {card.get_rarity_emoji()} **{card.name}**\n"
        
        # Бонусный опыт за покупку
        bonus_exp = config["cost"] // 10
        await user_service.add_experience(user, bonus_exp)
        result_text += f"\n✨ Бонус опыта: +{bonus_exp} XP"
        result_text += f"\n🪙 Осталось монет: {user.coins}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить еще", callback_data="shop"),
                InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_cards")
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await safe_edit_message(callback, result_text, reply_markup=keyboard, success_message=f"🎉 Пак открыт! Получено {len(opened_cards)} карточек!")
        
    except Exception as e:
        logger.error(f"Error buying pack: {e}")
        await callback.answer("❌ Ошибка при покупке пака", show_alert=True)


@router.callback_query(F.data == "shop_rarity")
async def shop_rarity_menu(callback: CallbackQuery):
    """Меню покупки карточек определенной редкости"""
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    
    rarity_text = (
        "🎯 **Выбор по редкости**\n\n"
        f"💰 Ваш опыт: {user.experience} XP\n\n"
        "⚪ **Common** - 25 XP\n"
        "🔵 **Rare** - 75 XP\n"
        "🟣 **Epic** - 200 XP\n"
        "🟡 **Legendary** - 500 XP\n"
        "🔴 **Artifact** - 1000 XP\n\n"
        "💡 Выберите желаемую редкость:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚪ Common (25)", callback_data="buy_rarity_common"),
            InlineKeyboardButton(text="🔵 Rare (75)", callback_data="buy_rarity_rare")
        ],
        [
            InlineKeyboardButton(text="🟣 Epic (200)", callback_data="buy_rarity_epic"),
            InlineKeyboardButton(text="🟡 Legendary (500)", callback_data="buy_rarity_legendary")
        ],
        [InlineKeyboardButton(text="🔴 Artifact (1000)", callback_data="buy_rarity_artifact")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
    ])
    
    await safe_edit_message(callback, rarity_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("buy_rarity_"))
async def buy_rarity_card(callback: CallbackQuery):
    """Покупка карточки определенной редкости"""
    try:
        rarity = callback.data.split("_")[-1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        costs = {
            "common": 25,
            "rare": 75,
            "epic": 200,
            "legendary": 500,
            "artifact": 1000
        }
        
        cost = costs.get(rarity, 0)
        
        if user.experience < cost:
            await callback.answer(
                f"❌ Недостаточно опыта! Нужно: {cost} XP, есть: {user.experience} XP",
                show_alert=True
            )
            return
        
        # Получаем карточку
        card = await card_service.get_random_card_by_rarity(rarity)
        
        if not card:
            await callback.answer("❌ Карточки этой редкости временно недоступны", show_alert=True)
            return
        
        # Списываем опыт и добавляем карточку
        user.experience -= cost
        await user_service.update_user(user)
        await user_service.add_card_to_user(user, str(card.id))
        await card_service.update_card_stats(card.name, 1, 1)
        
        result_text = (
            f"🎉 **Карточка куплена!**\n\n"
            f"{card.get_rarity_emoji()} **{card.name}**\n"
            f"📖 {card.description}\n\n"
            f"💰 Потрачено: {cost} XP\n"
            f"💰 Осталось: {user.experience} XP"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить еще", callback_data="shop_rarity"),
                InlineKeyboardButton(text="📚 Коллекция", callback_data="my_cards")
            ]
        ])
        
        await safe_edit_message(callback, result_text, reply_markup=keyboard, success_message=f"🎉 Получена {card.name}!")
        
    except Exception as e:
        logger.error(f"Error buying rarity card: {e}")
        await callback.answer("❌ Ошибка при покупке", show_alert=True)


@router.callback_query(F.data == "shop_exchange")
async def shop_exchange_menu(callback: CallbackQuery):
    """Меню обмена карточек"""
    exchange_text = (
        "🔄 **Обмен карточек**\n\n"
        "💱 **Доступные обмены:**\n\n"
        "📤 **Продать карточки:**\n"
        "• ⚪ Common → 5 XP\n"
        "• 🔵 Rare → 15 XP\n"
        "• 🟣 Epic → 40 XP\n"
        "• 🟡 Legendary → 100 XP\n\n"
        "🔄 **Обмен карточек:**\n"
        "• 5x Common → 1x Rare\n"
        "• 5x Rare → 1x Epic\n"
        "• 3x Epic → 1x Legendary\n\n"
        "💡 Используйте команды:\n"
        "/sell <название> - продать карточку\n"
        "/exchange <название> - обменять карточки"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
    ])
    
    await safe_edit_message(callback, exchange_text, reply_markup=keyboard)


@router.message(Command("sell"))
async def sell_card_command(message: Message):
    """Команда продажи карточки"""
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("❓ Использование: /sell <название_карточки>")
            return
        
        card_name = args[1].strip()
        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        # Находим карточку
        card = await card_service.get_card_by_name(card_name)
        if not card:
            await message.answer(f"❌ Карточка '{card_name}' не найдена")
            return
        
        # Проверяем наличие у пользователя
        if user.get_card_count(str(card.id)) == 0:
            await message.answer(f"❌ У вас нет карточки '{card_name}'")
            return
        
        # Определяем цену в монетах
        prices = {
            "common": 15,
            "rare": 45,
            "epic": 120,
            "legendary": 350,
            "artifact": 1000
        }
        
        price = prices.get(card.rarity, 1)
        
        # Продаем карточку
        success = await user_service.remove_card_from_user(user, str(card.id), 1)
        if success:
            user.coins += price
            await user_service.update_user(user)
            await card_service.update_card_stats(card.name, -1)
            
            await message.answer(
                f"💰 **Карточка продана!**\n\n"
                f"{card.get_rarity_emoji()} {card.name}\n"
                f"🪙 Получено: {price} монет\n"
                f"💰 Всего монет: {user.coins}"
            )
        else:
            await message.answer("❌ Ошибка при продаже карточки")
        
    except Exception as e:
        logger.error(f"Error selling card: {e}")
        await message.answer("❌ Ошибка при продаже карточки")


@router.callback_query(F.data.startswith("sell_cards_menu"))
async def sell_cards_menu(callback: CallbackQuery):
    """Меню продажи карточек с кнопками"""
    try:
        # Извлекаем страницу
        page = 1
        if ":" in callback.data:
            try:
                page = int(callback.data.split(":")[1])
            except (ValueError, IndexError):
                page = 1
        
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if not user.cards or len(user.cards) == 0:
            await safe_edit_message(
                callback,
                "💰 **Продажа карточек**\n\n"
                "❌ У вас нет карточек для продажи\n\n"
                "🎴 Получите карточки через /dailycard или магазин",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
                ])
            )
            return
        
        # Получаем карточки пользователя с информацией
        sellable_cards = []
        for user_card in user.cards:
            if user_card.quantity > 0:
                card = await card_service.get_card_by_id(user_card.card_id)
                if card:
                    # Цены продажи
                    prices = {
                        "common": 15, "rare": 45, "epic": 120,
                        "legendary": 350, "artifact": 1000
                    }
                    price = prices.get(card.rarity, 1)
                    sellable_cards.append((card, user_card.quantity, price))
        
        if not sellable_cards:
            await safe_edit_message(
                callback,
                "💰 **Продажа карточек**\n\n"
                "❌ Нет карточек для продажи",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
                ])
            )
            return
        
        # Сортируем по цене (дороже сначала)
        sellable_cards.sort(key=lambda x: x[2], reverse=True)
        
        # Пагинация
        page_size = 6
        total_pages = (len(sellable_cards) + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_cards = sellable_cards[start_idx:end_idx]
        
        text = f"💰 **Продажа карточек** (стр. {page}/{total_pages})\n\n"
        text += f"🪙 Ваши монеты: {user.coins}\n\n"
        
        keyboard_buttons = []
        
        for card, quantity, price in page_cards:
            text += f"{card.get_rarity_emoji()} **{card.name}** x{quantity}\n"
            text += f"   💰 Цена: {price} 🪙 за штуку\n\n"
            
            button_text = f"💰 {card.name[:15]}... ({price}🪙)"
            keyboard_buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"sell_card:{card.name}"
            )])
        
        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️", 
                callback_data=f"sell_cards_menu:{page-1}"
            ))
        
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}", 
            callback_data="ignore"
        ))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text="▶️", 
                callback_data=f"sell_cards_menu:{page+1}"
            ))
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="💰 Продать все Common", callback_data="sell_all_common"),
            InlineKeyboardButton(text="💰 Продать дубли", callback_data="sell_duplicates")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔥 ПРОДАТЬ ВСЁ", callback_data="sell_all_cards")
        ])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="shop")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await safe_edit_message(callback, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in sell cards menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню продажи", show_alert=True)


@router.callback_query(F.data.startswith("sell_card:"))
async def sell_card_callback(callback: CallbackQuery):
    """Продажа карточки через кнопку"""
    try:
        card_name = callback.data.split(":", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Находим карточку
        card = await card_service.get_card_by_name(card_name)
        if not card:
            await callback.answer("❌ Карточка не найдена", show_alert=True)
            return
        
        # Проверяем наличие
        quantity = user.get_card_count(str(card.id))
        if quantity == 0:
            await callback.answer("❌ У вас нет этой карточки", show_alert=True)
            return
        
        # Цены продажи
        prices = {
            "common": 2, "rare": 8, "epic": 25,
            "legendary": 75, "artifact": 200
        }
        price = prices.get(card.rarity, 1)
        
        # Подтверждение продажи
        confirm_text = (
            f"💰 **Подтверждение продажи**\n\n"
            f"Карточка: {card.get_rarity_emoji()} **{card.name}**\n"
            f"У вас: {quantity} шт.\n"
            f"Цена: {price} 🪙 за штуку\n\n"
            f"Продать 1 карточку?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Продать 1 шт", callback_data=f"confirm_sell:{card_name}:1"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="sell_cards_menu")
            ]
        ])
        
        if quantity > 1:
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton(text=f"💰 Продать все ({quantity} шт)", callback_data=f"confirm_sell:{card_name}:{quantity}")
            ])
        
        await safe_edit_message(callback, confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in sell card callback: {e}")
        await callback.answer("❌ Ошибка при продаже", show_alert=True)


@router.callback_query(F.data.startswith("confirm_sell:"))
async def confirm_sell_card(callback: CallbackQuery):
    """Подтверждение продажи карточки"""
    try:
        parts = callback.data.split(":")
        card_name = parts[1]
        quantity_to_sell = int(parts[2])
        
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        card = await card_service.get_card_by_name(card_name)
        
        if not user or not card:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        # Проверяем наличие
        available_quantity = user.get_card_count(str(card.id))
        if available_quantity < quantity_to_sell:
            await callback.answer("❌ Недостаточно карточек", show_alert=True)
            return
        
        # Цены продажи
        prices = {
            "common": 15, "rare": 45, "epic": 120,
            "legendary": 350, "artifact": 1000
        }
        price_per_card = prices.get(card.rarity, 1)
        total_price = price_per_card * quantity_to_sell
        
        # Продаем карточки
        success = await user_service.remove_card_from_user(user, str(card.id), quantity_to_sell)
        
        if success:
            user.coins += total_price
            await user_service.update_user(user)
            await card_service.update_card_stats(card.name, -quantity_to_sell)
            
            result_text = (
                f"✅ **Продажа завершена!**\n\n"
                f"{card.get_rarity_emoji()} **{card.name}** x{quantity_to_sell}\n"
                f"🪙 Получено: {total_price} монет\n"
                f"💰 Всего монет: {user.coins}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💰 Продать еще", callback_data="sell_cards_menu"),
                    InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")
                ]
            ])
            
            await safe_edit_message(callback, result_text, reply_markup=keyboard, success_message=f"✅ Продано за {total_price} монет!")
        else:
            await callback.answer("❌ Ошибка при продаже", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error confirming sell: {e}")
        await callback.answer("❌ Ошибка при продаже", show_alert=True)


# Массовая продажа карточек
@router.callback_query(F.data == "sell_all_cards")
async def sell_all_cards_confirm(callback: CallbackQuery):
    """Подтверждение продажи ВСЕХ карточек"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user or not user.cards:
            await callback.answer("❌ У вас нет карточек", show_alert=True)
            return
        
        # Подсчитываем общую стоимость
        total_value = 0
        total_cards = 0
        prices = {"common": 15, "rare": 45, "epic": 120, "legendary": 350, "artifact": 1000}
        
        for user_card in user.cards:
            if user_card.quantity > 0:
                card = await card_service.get_card_by_id(user_card.card_id)
                if card:
                    price = prices.get(card.rarity, 1)
                    total_value += price * user_card.quantity
                    total_cards += user_card.quantity
        
        if total_cards == 0:
            await callback.answer("❌ Нет карточек для продажи", show_alert=True)
            return
        
        confirm_text = (
            f"🔥 **ПРОДАЖА ВСЕХ КАРТОЧЕК**\n\n"
            f"⚠️ **ВНИМАНИЕ!** Это действие необратимо!\n\n"
            f"📊 **Будет продано:**\n"
            f"🎴 Карточек: {total_cards} шт.\n"
            f"🪙 Получите: {total_value} монет\n\n"
            f"💰 После продажи у вас будет: {user.coins + total_value} монет\n\n"
            f"❌ **ВСЯ КОЛЛЕКЦИЯ БУДЕТ УДАЛЕНА!**"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 ДА, ПРОДАТЬ ВСЁ", callback_data="confirm_sell_all")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="sell_cards_menu")]
        ])
        
        await safe_edit_message(callback, confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in sell all cards: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "confirm_sell_all")
async def confirm_sell_all_cards(callback: CallbackQuery):
    """Выполнение продажи всех карточек"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user or not user.cards:
            await callback.answer("❌ У вас нет карточек", show_alert=True)
            return
        
        total_value = 0
        total_cards = 0
        prices = {"common": 15, "rare": 45, "epic": 120, "legendary": 350, "artifact": 1000}
        
        # Подсчитываем и продаем
        for user_card in user.cards[:]:  # Копия списка для безопасного удаления
            if user_card.quantity > 0:
                card = await card_service.get_card_by_id(user_card.card_id)
                if card:
                    price = prices.get(card.rarity, 1)
                    total_value += price * user_card.quantity
                    total_cards += user_card.quantity
                    
                    # Обновляем статистику карточки
                    await card_service.update_card_stats(card.name, -user_card.quantity)
        
        # Очищаем коллекцию и добавляем монеты
        user.cards = []
        user.total_cards = 0
        user.coins += total_value
        await user_service.update_user(user)
        
        result_text = (
            f"✅ **ВСЯ КОЛЛЕКЦИЯ ПРОДАНА!**\n\n"
            f"🎴 Продано карточек: {total_cards}\n"
            f"🪙 Получено монет: {total_value}\n"
            f"💰 Всего монет: {user.coins}\n\n"
            f"🎮 Начните собирать коллекцию заново!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎴 Получить карточку", callback_data="daily_card"),
                InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await safe_edit_message(callback, result_text, reply_markup=keyboard, success_message="💥 Вся коллекция продана!")
        
    except Exception as e:
        logger.error(f"Error confirming sell all: {e}")
        await callback.answer("❌ Ошибка при продаже", show_alert=True)


@router.callback_query(F.data == "sell_all_common")
async def sell_all_common_cards(callback: CallbackQuery):
    """Продажа всех Common карточек"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        common_cards = []
        total_value = 0
        total_count = 0
        
        # Находим все Common карточки
        for user_card in user.cards:
            if user_card.quantity > 0:
                card = await card_service.get_card_by_id(user_card.card_id)
                if card and card.rarity == "common":
                    common_cards.append((card, user_card.quantity))
                    total_value += 15 * user_card.quantity  # 15 монет за Common
                    total_count += user_card.quantity
        
        if total_count == 0:
            await callback.answer("❌ У вас нет Common карточек", show_alert=True)
            return
        
        # Продаем все Common карточки
        for card, quantity in common_cards:
            success = await user_service.remove_card_from_user(user, str(card.id), quantity)
            if success:
                await card_service.update_card_stats(card.name, -quantity)
        
        user.coins += total_value
        await user_service.update_user(user)
        
        result_text = (
            f"✅ **Common карточки проданы!**\n\n"
            f"⚪ Продано: {total_count} Common карточек\n"
            f"🪙 Получено: {total_value} монет\n"
            f"💰 Всего монет: {user.coins}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Продать еще", callback_data="sell_cards_menu"),
                InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")
            ]
        ])
        
        await safe_edit_message(callback, result_text, reply_markup=keyboard, success_message=f"✅ Продано {total_count} Common карточек!")
        
    except Exception as e:
        logger.error(f"Error selling common cards: {e}")
        await callback.answer("❌ Ошибка при продаже", show_alert=True)


@router.callback_query(F.data == "sell_duplicates")
async def sell_duplicate_cards(callback: CallbackQuery):
    """Продажа дублей (оставляем по 1 экземпляру)"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        duplicates_sold = 0
        total_value = 0
        prices = {"common": 15, "rare": 45, "epic": 120, "legendary": 350, "artifact": 1000}
        
        # Находим и продаем дубли
        for user_card in user.cards:
            if user_card.quantity > 1:  # Есть дубли
                card = await card_service.get_card_by_id(user_card.card_id)
                if card:
                    duplicates_count = user_card.quantity - 1  # Оставляем 1
                    price = prices.get(card.rarity, 1)
                    total_value += price * duplicates_count
                    duplicates_sold += duplicates_count
                    
                    # Продаем дубли
                    success = await user_service.remove_card_from_user(user, str(card.id), duplicates_count)
                    if success:
                        await card_service.update_card_stats(card.name, -duplicates_count)
        
        if duplicates_sold == 0:
            await callback.answer("❌ У вас нет дублей для продажи", show_alert=True)
            return
        
        user.coins += total_value
        await user_service.update_user(user)
        
        result_text = (
            f"✅ **Дубли проданы!**\n\n"
            f"🔄 Продано дублей: {duplicates_sold}\n"
            f"🪙 Получено: {total_value} монет\n"
            f"💰 Всего монет: {user.coins}\n\n"
            f"📚 В коллекции остались уникальные карточки"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_cards"),
                InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")
            ]
        ])
        
        await safe_edit_message(callback, result_text, reply_markup=keyboard, success_message=f"✅ Продано {duplicates_sold} дублей!")
        
    except Exception as e:
        logger.error(f"Error selling duplicates: {e}")
        await callback.answer("❌ Ошибка при продаже", show_alert=True)


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорируем нажатие на кнопку-индикатор страницы"""
    await callback.answer()
