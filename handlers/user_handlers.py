from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, CommandStart
from loguru import logger

from models.user import User
from services.user_service import user_service
from services.card_service import card_service
from services.game_service import game_service
from config import settings

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

async def safe_edit_message_update(update, text: str, reply_markup=None):
    """Безопасное редактирование сообщения для update (CallbackQuery или Message)"""
    if isinstance(update, CallbackQuery):
        try:
            await update.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            if "message is not modified" in str(e):
                await update.answer("📊 Данные актуальны")
            elif "there is no text in the message to edit" in str(e):
                # Если сообщение содержит медиа, отправляем новое
                await update.message.answer(text, reply_markup=reply_markup)
                await update.answer()
            else:
                await update.answer("❌ Ошибка при обновлении")
                logger.error(f"Error editing message: {e}")
        else:
            await update.answer()
    else:
        await update.answer(text, reply_markup=reply_markup)


@router.message(CommandStart())
async def start_command(message: Message):
    """Команда /start"""
    try:
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        welcome_text = (
            "🎉 **Добро пожаловать в Pratki Card Bot!**\n\n"
            "🎴 Собирайте уникальные карточки\n"
            "⚡ Улучшайте свою коллекцию\n"
            "🏆 Соревнуйтесь с другими игроками\n\n"
            "ℹ️ Используйте кнопки ниже или команды:\n"
            "/help - список команд\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎴 Карточка дня", callback_data="daily_card"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
            ],
            [
                InlineKeyboardButton(text="📚 Мои карточки", callback_data="my_cards"),
                InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")
            ],
            [
                InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu"),
                InlineKeyboardButton(text="🔧 Улучшить карточки", callback_data="upgrade_menu")
            ],
            [
                InlineKeyboardButton(text="⚡ Лидерборд", callback_data="leaderboard"),
                InlineKeyboardButton(text="🎪 Ивенты", callback_data="events")
            ],
            [
                InlineKeyboardButton(text="💎 NFT Карточки", callback_data="nft_cards"),
                InlineKeyboardButton(text="🎁 Бонус", callback_data="bonus")
            ],
            [
                InlineKeyboardButton(text="🥚 ПАСХАЛКА", callback_data="easter_egg"),
                InlineKeyboardButton(text="🧩 Предложить карточку", callback_data="suggest_card")
            ],
            [
                InlineKeyboardButton(text="🔧 Поддержка", callback_data="support")
            ]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard)
        
        # Проверяем достижения при старте
        try:
            from handlers.achievement_handlers import check_and_notify_achievements
            await check_and_notify_achievements(user, message.bot)
        except Exception as achievement_error:
            logger.error(f"Error checking achievements on start: {achievement_error}")
        
    except Exception as e:
        logger.error(f"Error in start command for user {message.from_user.id}: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(Command("help"))
async def help_command(message: Message):
    """Команда /help"""
    help_text = (
        "📋 **Список команд:**\n\n"
        "🎯 **Основные команды:**\n"
        "/start - Начать игру\n"
        "/dailycard - Получить ежедневную карточку\n"
        "/mycards - Посмотреть свою коллекцию\n"
        "/profile - Посмотреть свой профиль\n"
        "/upgrade <название> - Улучшить карточки\n"
        "/leaderboard - Таблица лидеров\n"
        "/cardinfo <название> - Информация о карточке\n\n"
        "⭐ **Система редкости:**\n"
        "⚪ Common (69.89%)\n"
        "🔵 Rare (20%)\n"
        "🟣 Epic (8%)\n"
        "🟡 Legendary (2%)\n"
        "🔴 Artifact (0.1%)\n\n"
        "🔄 **Улучшение:**\n"
        "3 одинаковые карточки → 1 следующей редкости\n\n"
        "💎 **Артефактные карточки:**\n"
        "При получении: 50% шанс на бонус/штраф"
    )
    
    await message.answer(help_text)


@router.callback_query(F.data == "daily_card")
@router.message(Command("dailycard"))
async def daily_card_handler(update):
    """Получение ежедневной карточки"""
    try:
        if isinstance(update, CallbackQuery):
            message = update.message
            user_id = update.from_user.id
        else:
            message = update
            user_id = update.from_user.id
        
        user = await user_service.get_or_create_user(
            telegram_id=user_id,
            username=getattr(update.from_user, 'username', None),
            first_name=getattr(update.from_user, 'first_name', None),
            last_name=getattr(update.from_user, 'last_name', None)
        )
        
        card, bonus_card, message_text = await game_service.give_daily_card(user)
        
        if not card:
            if isinstance(update, CallbackQuery):
                await update.answer(message_text, show_alert=True)
            else:
                await message.answer(message_text)
            return
        
        # Отправляем карточку с медиафайлом
        media_url = card.get_media_url()
        
        if media_url and media_url.startswith('assets/'):
            try:
                if media_url.endswith('.mp4'):
                    await message.answer_video(FSInputFile(media_url), caption=message_text)
                elif media_url.endswith('.gif'):
                    await message.answer_animation(FSInputFile(media_url), caption=message_text)
                else:
                    await message.answer_photo(FSInputFile(media_url), caption=message_text)
            except:
                await message.answer(message_text)
        else:
            await message.answer(message_text)
        
        # Проверяем артефактный эффект
        if card.rarity == "artifact":
            effect_happened, effect_text = await game_service.handle_artifact_effect(user)
            if effect_happened:
                await message.answer(effect_text)
        
        # Проверяем достижения после получения карточки
        try:
            from handlers.achievement_handlers import check_and_notify_achievements
            await check_and_notify_achievements(user, message.bot)
        except Exception as achievement_error:
            logger.error(f"Error checking achievements after daily card: {achievement_error}")
        
        if isinstance(update, CallbackQuery):
            await update.answer()
            
    except Exception as e:
        logger.error(f"Error in daily card for user {user_id}: {e}")
        error_msg = "❌ Произошла ошибка при получении карточки"
        if isinstance(update, CallbackQuery):
            await update.answer(error_msg, show_alert=True)
        else:
            await message.answer(error_msg)


@router.callback_query(F.data == "profile")
@router.message(Command("profile"))
async def profile_handler(update):
    """Профиль пользователя"""
    try:
        if isinstance(update, CallbackQuery):
            message = update.message
            user_id = update.from_user.id
        else:
            message = update
            user_id = update.from_user.id
        
        user = await user_service.get_user_by_telegram_id(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        # Время до следующей карточки
        cooldown_text = ""
        if user.last_daily_card:
            next_card_time = user.last_daily_card + timedelta(hours=settings.daily_card_cooldown_hours)
            if datetime.utcnow() < next_card_time:
                remaining = next_card_time - datetime.utcnow()
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                cooldown_text = f"\n⏰ Следующая карточка через: {hours}ч {minutes}м"
        
        # Получаем информацию о любимых карточках
        favorite_cards_text = "💖 **Любимые карточки:**\n"
        if user.favorite_cards:
            from services.card_service import card_service
            for card_id in user.favorite_cards:
                card = await card_service.get_card_by_id(card_id)
                if card:
                    rarity_emoji = {
                        "common": "⚪",
                        "rare": "🔵", 
                        "epic": "🟣",
                        "legendary": "🟡",
                        "artifact": "🔴"
                    }.get(card.rarity.lower(), "⚪")
                    favorite_cards_text += f"{rarity_emoji} {card.name}\n"
                else:
                    favorite_cards_text += f"❓ Неизвестная карточка\n"
        else:
            favorite_cards_text += "Пока нет любимых карточек\n"
        
        profile_text = (
            f"👤 **Профиль игрока**\n\n"
            f"🆔 ID: {user.telegram_id}\n"
            f"👤 Имя: {user.first_name or 'Неизвестно'}\n"
            f"🎯 Уровень: {user.level}\n"
            f"✨ Опыт: {user.experience}\n"
            f"🪙 Монеты: {user.coins}\n"
            f"🃏 Всего карточек: {user.total_cards}\n"
            f"🎴 Уникальных карточек: {len(user.cards)}\n\n"
            f"{favorite_cards_text}\n"
            f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}"
            f"{cooldown_text}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Мои карточки", callback_data="my_cards"),
                InlineKeyboardButton(text="🎴 Карточка дня", callback_data="daily_card")
            ],
            [
                InlineKeyboardButton(text="🏪 Магазин", callback_data="shop"),
                InlineKeyboardButton(text="🏆 Рейтинг", callback_data="leaderboard")
            ],
            [
                InlineKeyboardButton(text="🏅 Достижения", callback_data="achievements"),
                InlineKeyboardButton(text="💖 Любимые", callback_data="manage_favorites")
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        if isinstance(update, CallbackQuery):
            await safe_edit_message(update, profile_text, reply_markup=keyboard)
        else:
            await message.answer(profile_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error in profile for user {user_id}: {e}")
        await message.answer("❌ Произошла ошибка при получении профиля")


@router.callback_query(F.data.startswith("my_cards"))
@router.message(Command("mycards"))
async def my_cards_handler(update):
    """Коллекция карточек пользователя"""
    try:
        if isinstance(update, CallbackQuery):
            message = update.message
            user_id = update.from_user.id
            # Извлекаем страницу из callback_data (my_cards:page)
            page = 1
            if ":" in update.data and len(update.data.split(":")) > 1:
                try:
                    page = int(update.data.split(":")[1])
                except (ValueError, IndexError):
                    page = 1
        else:
            message = update
            user_id = update.from_user.id
            page = 1
        
        user = await user_service.get_user_by_telegram_id(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        if not user.cards or len(user.cards) == 0 or user.total_cards == 0:
            text = "📚 **Ваша коллекция пуста**\n\nИспользуйте /dailycard чтобы получить первую карточку!"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎴 Получить карточку", callback_data="daily_card")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])
            
            if isinstance(update, CallbackQuery):
                await safe_edit_message(update, text, reply_markup=keyboard)
            else:
                await message.answer(text, reply_markup=keyboard)
            return
        
        # Получаем коллекцию с пагинацией
        try:
            collection, total_items, total_pages = await game_service.get_user_collection(user, page, 10)
        except Exception as e:
            logger.error(f"Error getting user collection: {e}")
            text = "❌ Ошибка при получении коллекции. Попробуйте позже."
            if isinstance(update, CallbackQuery):
                await safe_edit_message(update, text)
            else:
                await message.answer(text)
            return
        
        if not collection:
            text = "📚 **Ваша коллекция пуста**\n\nИспользуйте /dailycard чтобы получить первую карточку!"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎴 Получить карточку", callback_data="daily_card")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])
            
            if isinstance(update, CallbackQuery):
                await safe_edit_message(update, text, reply_markup=keyboard)
            else:
                await message.answer(text, reply_markup=keyboard)
            return
        
        # Формируем текст
        text = f"📚 **Ваша коллекция** (страница {page}/{total_pages})\n\n"
        
        keyboard_buttons = []
        for i, (card, quantity) in enumerate(collection):
            text += f"{card.get_rarity_emoji()} **{card.name}** x{quantity}\n"
            # Добавляем кнопку для просмотра карточки
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{card.get_rarity_emoji()} {card.name} x{quantity}",
                callback_data=f"view_card:{card.name}"
            )])
        
        # Кнопки навигации
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"my_cards:{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"my_cards:{page+1}"))
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔄 Улучшить", callback_data="upgrade_menu"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
        ])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if isinstance(update, CallbackQuery):
            await safe_edit_message(update, text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error in my_cards for user {user_id}: {e}")
        await message.answer("❌ Произошла ошибка при получении коллекции")


@router.callback_query(F.data.startswith("view_card:"))
async def view_card_detail(callback: CallbackQuery):
    """Детальный просмотр карточки"""
    try:
        card_name = callback.data.split(":", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Найти карточку
        card = await card_service.get_card_by_name(card_name)
        if not card:
            await callback.answer("❌ Карточка не найдена", show_alert=True)
            return
        
        # Получить количество у пользователя
        quantity = user.get_card_count(str(card.id))
        
        # Получить редкость на русском
        rarity_names = {
            "common": "Обычная",
            "rare": "Редкая", 
            "epic": "Эпическая",
            "legendary": "Легендарная",
            "artifact": "Артефакт"
        }
        rarity_name = rarity_names.get(card.rarity, card.rarity.title())
        
        # Формируем детальную информацию
        detail_text = (
            f"🎴 **Детали карточки**\n\n"
            f"{card.get_rarity_emoji()} **{card.name}**\n\n"
            f"📝 **Описание:**\n{card.description}\n\n"
            f"🔹 **Редкость:** {rarity_name}\n"
            f"📊 **У вас:** {quantity} шт.\n"
            f"👥 **Всего владельцев:** {card.unique_owners}\n"
            f"🎴 **Всего экземпляров:** {card.total_owned}\n"
            f"📅 **Добавлена:** {card.created_at.strftime('%d.%m.%Y')}"
        )
        
        # Добавляем информацию об эффекте артефакта
        if card.rarity == "artifact" and hasattr(card, 'effect') and card.effect:
            effect_text = "✨ **Особый эффект**" if card.effect.get('type') == 'bonus' else "⚠️ **Проклятие**"
            detail_text += f"\n\n{effect_text}\n{card.effect.get('description', 'Описание недоступно')}"
        
        # Проверяем, есть ли карточка в любимых
        card_id = str(card.id)
        is_favorite = card_id in user.favorite_cards
        favorite_button_text = "💔 Убрать из любимых" if is_favorite else "💖 В любимые"
        favorite_callback = f"remove_favorite:{card_id}" if is_favorite else f"add_favorite:{card_id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Продать", callback_data=f"sell_card:{card_name}"),
                InlineKeyboardButton(text="🔄 Улучшить", callback_data=f"upgrade_card:{card_name}")
            ],
            [
                InlineKeyboardButton(text=favorite_button_text, callback_data=favorite_callback)
            ],
            [InlineKeyboardButton(text="◀️ К коллекции", callback_data="my_cards")]
        ])
        
        # Проверяем, есть ли медиафайл для карточки
        media_url = card.get_media_url()
        
        # Добавляем отладочную информацию
        logger.info(f"Card {card_name} - Media URL: {media_url}")
        logger.info(f"Card {card_name} - GIF URL: {card.gif_url}")
        logger.info(f"Card {card_name} - Video URL: {card.video_url}")
        logger.info(f"Card {card_name} - Image URL: {card.image_url}")
        
        if media_url and media_url.startswith('assets/'):
            logger.info(f"Attempting to send media for card {card_name}: {media_url}")
            try:
                # Определяем тип медиафайла
                if media_url.endswith('.gif'):
                    from aiogram.types import InputMediaAnimation
                    media = InputMediaAnimation(
                        media=FSInputFile(media_url),
                        caption=detail_text,
                        parse_mode="Markdown"
                    )
                    await callback.message.edit_media(media, reply_markup=keyboard)
                    logger.info(f"Successfully sent GIF for card {card_name}")
                elif media_url.endswith('.mp4'):
                    from aiogram.types import InputMediaVideo
                    media = InputMediaVideo(
                        media=FSInputFile(media_url),
                        caption=detail_text,
                        parse_mode="Markdown"
                    )
                    await callback.message.edit_media(media, reply_markup=keyboard)
                    logger.info(f"Successfully sent video for card {card_name}")
                elif media_url.endswith(('.jpg', '.jpeg', '.png')):
                    from aiogram.types import InputMediaPhoto
                    media = InputMediaPhoto(
                        media=FSInputFile(media_url),
                        caption=detail_text,
                        parse_mode="Markdown"
                    )
                    await callback.message.edit_media(media, reply_markup=keyboard)
                    logger.info(f"Successfully sent image for card {card_name}")
                else:
                    # Неизвестный тип файла, отправляем только текст
                    await safe_edit_message(callback, detail_text, reply_markup=keyboard)
            except Exception as media_error:
                logger.error(f"Error sending media for card {card_name}: {media_error}")
                # Если не удалось отправить медиа, отправляем только текст
                await safe_edit_message(callback, detail_text, reply_markup=keyboard)
        else:
            logger.info(f"No media found for card {card_name}, sending text only")
            # Если нет медиафайла, отправляем только текст
            await safe_edit_message(callback, detail_text, reply_markup=keyboard)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error viewing card detail: {e}")
        await callback.answer("❌ Ошибка при загрузке карточки", show_alert=True)


@router.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery):
    """Возврат в главное меню"""
    welcome_text = (
        "🎉 **Добро пожаловать в Pratki Card Bot!**\n\n"
        "🎴 Собирайте уникальные карточки\n"
        "⚡ Улучшайте свою коллекцию\n"
        "🏆 Соревнуйтесь с другими игроками\n\n"
        "ℹ️ Используйте кнопки ниже или команды:\n"
        "/help - список команд\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Карточка дня", callback_data="daily_card"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
        ],
        [
            InlineKeyboardButton(text="📚 Мои карточки", callback_data="my_cards"),
            InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")
        ],
        [
            InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu"),
            InlineKeyboardButton(text="🔧 Улучшить карточки", callback_data="upgrade_menu")
        ],
        [
            InlineKeyboardButton(text="⚡ Лидерборд", callback_data="leaderboard"),
            InlineKeyboardButton(text="🎪 Ивенты", callback_data="events")
        ],
        [
            InlineKeyboardButton(text="💎 NFT Карточки", callback_data="nft_cards"),
            InlineKeyboardButton(text="🎁 Бонус", callback_data="bonus")
        ],
        [
            InlineKeyboardButton(text="🥚 ПАСХАЛКА", callback_data="easter_egg"),
            InlineKeyboardButton(text="🧩 Предложить карточку", callback_data="suggest_card")
        ],
        [
            InlineKeyboardButton(text="🔧 Поддержка", callback_data="support")
        ]
    ])
    
    await safe_edit_message(callback, welcome_text, reply_markup=keyboard)


@router.callback_query(F.data == "leaderboard")
@router.message(Command("leaderboard"))
async def leaderboard_handler(update):
    """Таблица лидеров - главное меню"""
    try:
        if isinstance(update, CallbackQuery):
            message = update.message
        else:
            message = update
        
        text = "🏆 **Таблица лидеров**\n\n"
        text += "Выберите категорию для просмотра:\n\n"
        text += "📊 **Доступные рейтинги:**\n"
        text += "• 🎯 По уровню и опыту\n"
        text += "• 💰 По количеству монет\n"
        text += "• 🃏 По количеству карточек\n"
        text += "• ⚔️ По прогрессу в боях\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 По уровню", callback_data="leaderboard_experience"),
                InlineKeyboardButton(text="💰 По монетам", callback_data="leaderboard_coins")
            ],
            [
                InlineKeyboardButton(text="🃏 По карточкам", callback_data="leaderboard_cards"),
                InlineKeyboardButton(text="⚔️ По боям", callback_data="leaderboard_battles")
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        if isinstance(update, CallbackQuery):
            try:
                await update.message.edit_text(text, reply_markup=keyboard)
            except Exception as e:
                if "message is not modified" in str(e):
                    await update.answer("📊 Меню лидерборда")
                else:
                    await update.message.answer(text, reply_markup=keyboard)
            await update.answer()
        else:
            await message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error in leaderboard menu: {e}")
        await message.answer("❌ Произошла ошибка при загрузке меню лидерборда")


@router.callback_query(F.data == "leaderboard_experience")
async def leaderboard_experience(callback: CallbackQuery):
    """Лидерборд по уровню и опыту"""
    try:
        # Получаем топ игроков по опыту
        top_users = await user_service.get_leaderboard(limit=10, sort_by="experience")
        
        if not top_users:
            await callback.message.edit_text("📊 Пока нет данных для таблицы лидеров")
            return
        
        text = "🏆 **Топ по уровню и опыту**\n\n"
        
        for i, user in enumerate(top_users, 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            name = user.first_name or user.username or f"User{user.telegram_id}"
            text += f"{medal} **{name}**\n"
            text += f"   🎯 Уровень: {user.level} | ✨ Опыт: {user.experience:,}\n"
            text += f"   🃏 Карточек: {user.total_cards} | 💰 Монет: {user.coins:,}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="leaderboard_experience")],
            [InlineKeyboardButton(text="◀️ К лидерборду", callback_data="leaderboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in experience leaderboard: {e}")
        await callback.answer("❌ Ошибка при загрузке топа по опыту", show_alert=True)


@router.callback_query(F.data == "leaderboard_coins")
async def leaderboard_coins(callback: CallbackQuery):
    """Лидерборд по монетам"""
    try:
        # Получаем топ игроков по монетам
        top_users = await user_service.get_leaderboard(limit=10, sort_by="coins")
        
        if not top_users:
            await callback.message.edit_text("📊 Пока нет данных для таблицы лидеров")
            return
        
        text = "💰 **Топ по монетам**\n\n"
        
        for i, user in enumerate(top_users, 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            name = user.first_name or user.username or f"User{user.telegram_id}"
            text += f"{medal} **{name}**\n"
            text += f"   💰 Монет: {user.coins:,} | 🎯 Уровень: {user.level}\n"
            text += f"   ✨ Опыт: {user.experience:,} | 🃏 Карточек: {user.total_cards}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="leaderboard_coins")],
            [InlineKeyboardButton(text="◀️ К лидерборду", callback_data="leaderboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in coins leaderboard: {e}")
        await callback.answer("❌ Ошибка при загрузке топа по монетам", show_alert=True)


@router.callback_query(F.data == "leaderboard_cards")
async def leaderboard_cards(callback: CallbackQuery):
    """Лидерборд по карточкам"""
    try:
        # Получаем топ игроков по карточкам
        top_users = await user_service.get_leaderboard(limit=10, sort_by="total_cards")
        
        if not top_users:
            await callback.message.edit_text("📊 Пока нет данных для таблицы лидеров")
            return
        
        text = "🃏 **Топ по карточкам**\n\n"
        
        for i, user in enumerate(top_users, 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            name = user.first_name or user.username or f"User{user.telegram_id}"
            text += f"{medal} **{name}**\n"
            text += f"   🃏 Карточек: {user.total_cards} | 🎯 Уровень: {user.level}\n"
            text += f"   ✨ Опыт: {user.experience:,} | 💰 Монет: {user.coins:,}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="leaderboard_cards")],
            [InlineKeyboardButton(text="◀️ К лидерборду", callback_data="leaderboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in cards leaderboard: {e}")
        await callback.answer("❌ Ошибка при загрузке топа по карточкам", show_alert=True)


@router.callback_query(F.data == "leaderboard_battles")
async def leaderboard_battles(callback: CallbackQuery):
    """Лидерборд по боям"""
    try:
        # Получаем топ игроков по боям
        top_users = await user_service.get_battle_leaderboard(limit=10)
        
        if not top_users:
            await callback.message.edit_text("⚔️ Пока нет данных о боях")
            return
        
        text = "⚔️ **Топ по боям**\n\n"
        
        for i, user in enumerate(top_users, 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            name = user.first_name or user.username or f"User{user.telegram_id}"
            battle_progress = user.battle_progress
            
            # Определяем стадию в боях
            stage_text = "🔰 Новичок"
            if battle_progress.total_battles >= 100:
                stage_text = "🏆 Чемпион"
            elif battle_progress.total_battles >= 50:
                stage_text = "⚔️ Воин"
            elif battle_progress.total_battles >= 20:
                stage_text = "🛡️ Защитник"
            elif battle_progress.total_battles >= 10:
                stage_text = "⚡ Боец"
            elif battle_progress.total_battles >= 5:
                stage_text = "🎯 Стрелок"
            
            text += f"{medal} **{name}**\n"
            text += f"   ⚔️ Боев: {battle_progress.total_battles} | {stage_text}\n"
            text += f"   🎯 Уровень: {user.level} | 🃏 Карточек: {user.total_cards}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="leaderboard_battles")],
            [InlineKeyboardButton(text="◀️ К лидерборду", callback_data="leaderboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in battles leaderboard: {e}")
        await callback.answer("❌ Ошибка при загрузке топа по боям", show_alert=True)


@router.message(Command("cardinfo"))
async def card_info_command(message: Message):
    """Информация о карточке"""
    try:
        # Извлекаем название карточки из команды
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("❓ Использование: /cardinfo <название_карточки>")
            return
        
        card_name = args[1].strip()
        card = await card_service.get_card_by_name(card_name)
        
        if not card:
            await message.answer(f"❌ Карточка '{card_name}' не найдена")
            return
        
        rarity_info = settings.rarities.get(card.rarity, {})
        probability = rarity_info.get('probability', 0)
        
        card_text = (
            f"{card.get_rarity_emoji()} **{card.name}**\n\n"
            f"📖 {card.description}\n"
            f"⭐ Редкость: {card.rarity.title()}\n"
            f"🎲 Вероятность: {probability}%\n"
            f"👥 Владельцев: {card.unique_owners}\n"
            f"🔢 Всего экземпляров: {card.total_owned}"
        )
        
        if card.tags:
            card_text += f"\n🏷 Теги: {', '.join(card.tags)}"
        
        # Отправляем с медиафайлом если есть
        media_url = card.get_media_url()
        
        if media_url and media_url.startswith('assets/'):
            try:
                if media_url.endswith('.mp4'):
                    await message.answer_video(FSInputFile(media_url), caption=card_text)
                elif media_url.endswith('.gif'):
                    await message.answer_animation(FSInputFile(media_url), caption=card_text)
                else:
                    await message.answer_photo(FSInputFile(media_url), caption=card_text)
            except:
                await message.answer(card_text)
        else:
            await message.answer(card_text)
            
    except Exception as e:
        logger.error(f"Error in card_info: {e}")
        await message.answer("❌ Произошла ошибка при получении информации о карточке")


@router.message(Command("upgrade"))
async def upgrade_command(message: Message):
    """Улучшение карточек"""
    try:
        # Извлекаем название карточки из команды
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "❓ Использование: /upgrade <название_карточки>\n\n"
                f"Для улучшения нужно {settings.cards_for_upgrade} одинаковые карточки"
            )
            return
        
        card_name = args[1].strip()
        
        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        success, result_message = await game_service.upgrade_cards(user, card_name)
        await message.answer(result_message)
        
    except Exception as e:
        logger.error(f"Error in upgrade command: {e}")
        await message.answer("❌ Произошла ошибка при улучшении карточек")


# Заглушки для остальных кнопок
@router.callback_query(F.data.in_(["support", "ignore"]))
async def placeholder_handlers(callback: CallbackQuery):
    """Заглушки для нереализованных функций"""
        
    if callback.data == "support":
        support_text = (
            "🔧 **Поддержка**\n\n"
            "❓ **Нужна помощь?**\n"
            "Свяжитесь с разработчиком!\n\n"
            "📞 **Контакты:**\n"
            "• Telegram: @Siriusatop123\n\n"
            "🐛 **Нашли баг?**\n"
            "Сообщите для быстрого исправления!\n\n"
            "⚡ **Предложения:**\n"
            "Делитесь идеями по улучшению бота!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await safe_edit_message(callback, support_text, reply_markup=keyboard)
        
    elif callback.data == "ignore":
        await callback.answer()
    else:
        # Остальные функции в разработке
        await callback.answer("Функция в разработке", show_alert=True)


@router.callback_query(F.data.startswith("manage_favorites"))
async def manage_favorites_handler(callback: CallbackQuery):
    """Управление любимыми карточками"""
    try:
        # Извлекаем страницу из callback_data (manage_favorites:page)
        page = 1
        if ":" in callback.data and len(callback.data.split(":")) > 1:
            try:
                page = int(callback.data.split(":")[1])
            except (ValueError, IndexError):
                page = 1
        
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Получаем коллекцию пользователя с пагинацией
        from services.game_service import game_service
        cards_per_page = 12  # 6 рядов по 2 карточки
        collection, total_pages, current_page = await game_service.get_user_collection(user, page, cards_per_page)
        
        if not collection:
            await safe_edit_message(
                callback,
                "💖 **Управление любимыми карточками**\n\n"
                "❌ У вас пока нет карточек для добавления в любимые!\n"
                "Получите карточки с помощью /dailycard",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Профиль", callback_data="profile")]
                ])
            )
            return
        
        favorites_text = (
            f"💖 **Управление любимыми карточками**\n\n"
            f"📊 **Текущие любимые ({len(user.favorite_cards)}/3):**\n"
        )
        
        # Показываем текущие любимые
        if user.favorite_cards:
            from services.card_service import card_service
            for card_id in user.favorite_cards:
                card = await card_service.get_card_by_id(card_id)
                if card:
                    rarity_emoji = {
                        "common": "⚪",
                        "rare": "🔵", 
                        "epic": "🟣",
                        "legendary": "🟡",
                        "artifact": "🔴"
                    }.get(card.rarity.lower(), "⚪")
                    favorites_text += f"{rarity_emoji} {card.name}\n"
        else:
            favorites_text += "Пока нет любимых карточек\n"
        
        favorites_text += f"\n🎴 **Доступные карточки (стр. {page}/{total_pages}):**\n"
        favorites_text += "Нажмите на карточку чтобы добавить/убрать из любимых"
        
        # Создаем кнопки с карточками (по 2 в ряд)
        keyboard_buttons = []
        for i in range(0, len(collection), 2):
            row = []
            for j in range(2):
                if i + j < len(collection):
                    card, quantity = collection[i + j]
                    card_id = str(card.id)
                    is_favorite = card_id in user.favorite_cards
                    emoji = "💖" if is_favorite else card.get_rarity_emoji()
                    button_text = f"{emoji} {card.name[:15]}"
                    if is_favorite:
                        callback_data = f"remove_favorite:{card_id}"
                    else:
                        callback_data = f"add_favorite:{card_id}"
                    row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))
            keyboard_buttons.append(row)
        
        # Добавляем навигацию по страницам
        navigation_buttons = []
        if total_pages > 1:
            nav_row = []
            if page > 1:
                nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"manage_favorites:{page-1}"))
            nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="no_action"))
            if page < total_pages:
                nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"manage_favorites:{page+1}"))
            navigation_buttons.append(nav_row)
        
        # Добавляем кнопку возврата
        keyboard_buttons.extend(navigation_buttons)
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Профиль", callback_data="profile")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await safe_edit_message(callback, favorites_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error managing favorites: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("add_favorite:"))
async def add_favorite_handler(callback: CallbackQuery):
    """Добавление карточки в любимые"""
    try:
        card_id = callback.data.split(":", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        success = user.add_to_favorites(card_id)
        
        if success:
            await user_service.update_user(user)
            # Получаем название карточки
            from services.card_service import card_service
            card = await card_service.get_card_by_id(card_id)
            card_name = card.name if card else "карточка"
            await callback.answer(f"💖 {card_name} добавлена в любимые!")
            
            # Обновляем интерфейс (возвращаемся на первую страницу)
            callback.data = "manage_favorites:1"
            await manage_favorites_handler(callback)
        else:
            if len(user.favorite_cards) >= 3:
                await callback.answer("❌ Максимум 3 любимые карточки!", show_alert=True)
            elif user.get_card_count(card_id) == 0:
                await callback.answer("❌ У вас нет этой карточки!", show_alert=True)
            else:
                await callback.answer("❌ Карточка уже в любимых!", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "no_action")
async def no_action_handler(callback: CallbackQuery):
    """Обработчик для кнопок без действия"""
    await callback.answer()


@router.callback_query(F.data.startswith("remove_favorite:"))
async def remove_favorite_handler(callback: CallbackQuery):
    """Удаление карточки из любимых"""
    try:
        card_id = callback.data.split(":", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        success = user.remove_from_favorites(card_id)
        
        if success:
            await user_service.update_user(user)
            # Получаем название карточки
            from services.card_service import card_service
            card = await card_service.get_card_by_id(card_id)
            card_name = card.name if card else "карточка"
            await callback.answer(f"💔 {card_name} убрана из любимых!")
            
            # Обновляем интерфейс
            if callback.data.startswith("remove_favorite:") and ":from_detail" not in callback.data:
                await manage_favorites_handler(callback)
            else:
                # Если вызвано из детального просмотра, обновляем его
                await view_card_detail_by_id(callback, card_id)
        else:
            await callback.answer("❌ Карточки нет в любимых!", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


async def view_card_detail_by_id(callback: CallbackQuery, card_id: str):
    """Вспомогательная функция для обновления детального просмотра карточки по ID"""
    try:
        from services.card_service import card_service
        card = await card_service.get_card_by_id(card_id)
        if card:
            # Имитируем callback с названием карточки для переиспользования существующей функции
            new_callback_data = f"card_detail:{card.name}"
            original_data = callback.data
            callback.data = new_callback_data
            await view_card_detail(callback)
            callback.data = original_data
    except Exception as e:
        logger.error(f"Error updating card detail: {e}")
