from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger

from models.user import User
from services.user_service import user_service
from services.card_service import card_service
from services.game_service import game_service
from config import settings

router = Router()


@router.callback_query(F.data == "upgrade_menu")
async def upgrade_menu(callback: CallbackQuery):
    """Меню улучшения карточек"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Находим карточки доступные для улучшения
        upgradeable_cards = []
        
        for user_card in user.cards:
            if user_card.quantity >= settings.cards_for_upgrade:
                card = await card_service.get_card_by_id(user_card.card_id)
                if card and card.rarity != "artifact":  # Артефактные нельзя улучшить
                    target_rarity = await card_service.get_upgrade_result(card.rarity)
                    if target_rarity:
                        upgradeable_cards.append((card, user_card.quantity, target_rarity))
        
        if not upgradeable_cards:
            upgrade_text = (
                "🔧 **Улучшение карточек**\n\n"
                f"❌ Нет карточек для улучшения\n\n"
                f"💡 **Как улучшать:**\n"
                f"• Соберите {settings.cards_for_upgrade} одинаковые карточки\n"
                f"• Нажмите кнопку улучшения\n"
                f"• Получите случайную карточку следующей редкости\n\n"
                f"⚪ {settings.cards_for_upgrade}x Common → 🔵 1x Rare\n"
                f"🔵 {settings.cards_for_upgrade}x Rare → 🟣 1x Epic\n"
                f"🟣 {settings.cards_for_upgrade}x Epic → 🟡 1x Legendary\n"
                f"🟡 {settings.cards_for_upgrade}x Legendary → 🔴 1x Artifact"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎴 Получить карточки", callback_data="daily_card"),
                    InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_cards")
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
            ])
        else:
            upgrade_text = (
                "🔧 **Улучшение карточек**\n\n"
                "✅ Доступно для улучшения:\n\n"
            )
            
            keyboard_buttons = []
            
            for i, (card, quantity, target_rarity) in enumerate(upgradeable_cards[:10]):  # Показываем до 10
                target_emoji = settings.rarities.get(target_rarity, {}).get("emoji", "❓")
                upgrade_text += f"{card.get_rarity_emoji()} **{card.name}** x{quantity}\n"
                upgrade_text += f"   → {target_emoji} {target_rarity.title()}\n\n"
                
                # Добавляем кнопку для улучшения
                if i < 6:  # Максимум 6 кнопок
                    button_text = f"{card.get_rarity_emoji()} {card.name[:15]}..."
                    callback_data = f"upgrade_card:{card.name}"
                    keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
            
            if len(upgradeable_cards) > 6:
                upgrade_text += f"... и еще {len(upgradeable_cards) - 6} карточек\n"
                upgrade_text += "💡 Используйте /upgrade <название> для улучшения\n"
            
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(upgrade_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in upgrade menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню улучшений", show_alert=True)


@router.callback_query(F.data.startswith("upgrade_card:"))
async def upgrade_card_callback(callback: CallbackQuery):
    """Улучшение карточки через callback"""
    try:
        card_name = callback.data.split(":", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Подтверждение улучшения
        card = await card_service.get_card_by_name(card_name)
        if not card:
            await callback.answer("❌ Карточка не найдена", show_alert=True)
            return
        
        user_card_count = user.get_card_count(str(card.id))
        target_rarity = await card_service.get_upgrade_result(card.rarity)
        
        if user_card_count < settings.cards_for_upgrade:
            await callback.answer(
                f"❌ Недостаточно карточек! Нужно: {settings.cards_for_upgrade}, есть: {user_card_count}",
                show_alert=True
            )
            return
        
        target_emoji = settings.rarities.get(target_rarity, {}).get("emoji", "❓")
        
        confirm_text = (
            f"🔧 **Подтверждение улучшения**\n\n"
            f"📤 Отдаете: {settings.cards_for_upgrade}x {card.get_rarity_emoji()} {card.name}\n"
            f"📥 Получите: 1x {target_emoji} {target_rarity.title()} (случайная)\n\n"
            f"⚠️ Это действие нельзя отменить!\n"
            f"Продолжить?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, улучшить", callback_data=f"confirm_upgrade:{card_name}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="upgrade_menu")
            ]
        ])
        
        await callback.message.edit_text(confirm_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in upgrade callback: {e}")
        await callback.answer("❌ Ошибка при улучшении", show_alert=True)


@router.callback_query(F.data.startswith("confirm_upgrade:"))
async def confirm_upgrade(callback: CallbackQuery):
    """Подтверждение и выполнение улучшения"""
    try:
        card_name = callback.data.split(":", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Выполняем улучшение
        success, result_message = await game_service.upgrade_cards(user, card_name)
        
        if success:
            # Добавляем эффекты и анимацию
            result_message = "🎉 " + result_message
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔧 Улучшить еще", callback_data="upgrade_menu"),
                    InlineKeyboardButton(text="📚 Коллекция", callback_data="my_cards")
                ],
                [InlineKeyboardButton(text="🎴 Получить карточки", callback_data="daily_card")]
            ])
            
            await callback.answer("🎉 Улучшение успешно!", show_alert=True)
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="upgrade_menu")]
            ])
            
            await callback.answer("❌ Ошибка улучшения", show_alert=True)
        
        await callback.message.edit_text(result_message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error confirming upgrade: {e}")
        await callback.answer("❌ Ошибка при улучшении карточки", show_alert=True)


@router.message(Command("upgrade"))
async def upgrade_command(message: Message):
    """Улучшенная команда /upgrade"""
    try:
        args = message.text.split(maxsplit=1)
        
        if len(args) < 2:
            # Показываем доступные для улучшения карточки
            user = await user_service.get_user_by_telegram_id(message.from_user.id)
            if not user:
                await message.answer("❌ Пользователь не найден. Используйте /start")
                return
            
            upgradeable = []
            for user_card in user.cards:
                if user_card.quantity >= settings.cards_for_upgrade:
                    card = await card_service.get_card_by_id(user_card.card_id)
                    if card and card.rarity != "artifact":
                        target_rarity = await card_service.get_upgrade_result(card.rarity)
                        if target_rarity:
                            upgradeable.append(f"• {card.get_rarity_emoji()} {card.name} x{user_card.quantity}")
            
            if upgradeable:
                response = (
                    f"🔧 **Доступно для улучшения:**\n\n" + 
                    "\n".join(upgradeable[:10]) +
                    f"\n\n💡 Используйте: `/upgrade <название>`\n"
                    f"📱 Или воспользуйтесь кнопками в меню"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔧 Меню улучшений", callback_data="upgrade_menu")]
                ])
                
                await message.answer(response, reply_markup=keyboard)
            else:
                await message.answer(
                    f"❌ Нет карточек для улучшения\n\n"
                    f"💡 Соберите {settings.cards_for_upgrade} одинаковые карточки любой редкости (кроме Artifact)"
                )
            return
        
        card_name = args[1].strip()
        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        success, result_message = await game_service.upgrade_cards(user, card_name)
        await message.answer(result_message)
        
        if success:
            # Предлагаем дальнейшие действия
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔧 Улучшить еще", callback_data="upgrade_menu"),
                    InlineKeyboardButton(text="📚 Коллекция", callback_data="my_cards")
                ]
            ])
            await message.answer("🎯 Что делаем дальше?", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in upgrade command: {e}")
        await message.answer("❌ Ошибка при улучшении карточек")


@router.callback_query(F.data == "mass_upgrade")
async def mass_upgrade_menu(callback: CallbackQuery):
    """Меню массового улучшения"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Подсчитываем возможные массовые улучшения
        mass_upgrades = {}
        
        for user_card in user.cards:
            if user_card.quantity >= settings.cards_for_upgrade:
                card = await card_service.get_card_by_id(user_card.card_id)
                if card and card.rarity != "artifact":
                    possible_upgrades = user_card.quantity // settings.cards_for_upgrade
                    if possible_upgrades > 1:
                        mass_upgrades[card.name] = {
                            "card": card,
                            "count": possible_upgrades,
                            "total_cards": user_card.quantity
                        }
        
        if not mass_upgrades:
            mass_text = (
                "⚡ **Массовое улучшение**\n\n"
                "❌ Нет карточек для массового улучшения\n\n"
                "💡 Соберите много одинаковых карточек для\n"
                "массового улучшения (6+ карточек одного вида)"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="upgrade_menu")]
            ])
        else:
            mass_text = "⚡ **Массовое улучшение**\n\n"
            
            for card_name, info in mass_upgrades.items():
                card = info["card"]
                count = info["count"]
                mass_text += f"{card.get_rarity_emoji()} **{card_name}**\n"
                mass_text += f"   Можно улучшить: {count} раз\n\n"
            
            mass_text += "⚠️ При массовом улучшении все возможные\nкарточки будут улучшены сразу!"
            
            keyboard_buttons = []
            for card_name in list(mass_upgrades.keys())[:5]:  # Максимум 5 кнопок
                button_text = f"⚡ {card_name[:20]}..."
                callback_data = f"mass_upgrade_card:{card_name}"
                keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
            
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="upgrade_menu")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(mass_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in mass upgrade menu: {e}")
        await callback.answer("❌ Ошибка при загрузке массового улучшения", show_alert=True)
