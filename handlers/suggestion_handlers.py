from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from datetime import datetime

from models.user import User
from services.user_service import user_service
from services.card_service import card_service
from config import settings

router = Router()


class SuggestionStates(StatesGroup):
    waiting_for_card_name = State()
    waiting_for_card_description = State()
    waiting_for_card_media = State()


# Модель предложения карточки с медиа
class CardSuggestion:
    def __init__(self, user_id: int, username: str, card_name: str, description: str, media_file_id: str = None, media_type: str = None):
        self.user_id = user_id
        self.username = username
        self.card_name = card_name
        self.description = description
        self.media_file_id = media_file_id  # Telegram file_id для гифки/фото
        self.media_type = media_type  # 'animation', 'photo', 'video'
        self.created_at = datetime.utcnow()
        self.status = "pending"  # pending, approved, rejected


# Временное хранилище предложений (в реальном проекте - MongoDB)
suggestions_storage = []


@router.callback_query(F.data == "suggest_card")
async def suggest_card_start(callback: CallbackQuery, state: FSMContext):
    """Начало предложения карточки"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Проверяем бан на предложения
        if user.is_suggestion_banned:
            ban_text = (
                "🚫 **Вы заблокированы для предложений карточек**\n\n"
                f"**Причина:** {user.suggestion_ban_reason or 'Нарушение правил'}\n"
                f"**Дата бана:** {user.suggestion_ban_date.strftime('%d.%m.%Y %H:%M') if user.suggestion_ban_date else 'Неизвестно'}\n\n"
                "📞 **Для разбана обращайтесь:** @Siriusatop123"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])
            
            await callback.message.edit_text(ban_text, reply_markup=keyboard)
            await callback.answer()
            return
        
        # Проверяем лимит предложений (например, 3 в день)
        user_suggestions_today = [s for s in suggestions_storage 
                                if s.user_id == callback.from_user.id 
                                and s.created_at.date() == datetime.utcnow().date()]
        
        if len(user_suggestions_today) >= 3:
            await callback.answer("❌ Лимит предложений на сегодня исчерпан (3/3)", show_alert=True)
            return
        
        await state.set_state(SuggestionStates.waiting_for_card_name)
        
        suggestion_text = (
            "🧩 **Предложить карточку**\n\n"
            "💡 Поделитесь своей идеей карточки с гифкой!\n\n"
            "📝 **Шаг 1/3:** Введите название карточки\n\n"
            "ℹ️ **Требования:**\n"
            "• Максимум 50 символов\n"
            "• Уникальное название\n"
            "• Без оскорблений\n\n"
            f"📊 Ваши предложения сегодня: {len(user_suggestions_today)}/3"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(suggestion_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error starting suggestion: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(SuggestionStates.waiting_for_card_name))
async def process_card_name(message: Message, state: FSMContext):
    """Обработка названия карточки"""
    try:
        if not message.text:
            await message.answer("❌ Пожалуйста, отправьте текстовое название карточки")
            return
        
        card_name = message.text.strip()
        
        # Валидация названия
        if len(card_name) > 50:
            await message.answer("❌ Название слишком длинное (максимум 50 символов)")
            return
        
        if len(card_name) < 3:
            await message.answer("❌ Название слишком короткое (минимум 3 символа)")
            return
        
        # Проверяем, не существует ли уже такая карточка
        existing_card = await card_service.get_card_by_name(card_name)
        if existing_card:
            await message.answer(f"❌ Карточка с названием '{card_name}' уже существует")
            return
        
        # Проверяем, не предлагали ли уже такое название
        existing_suggestion = any(s.card_name.lower() == card_name.lower() 
                                for s in suggestions_storage 
                                if s.status == "pending")
        if existing_suggestion:
            await message.answer(f"❌ Карточка '{card_name}' уже предложена другим игроком")
            return
        
        await state.update_data(card_name=card_name)
        await state.set_state(SuggestionStates.waiting_for_card_description)
        
        description_text = (
            f"🧩 **Предложение карточки**\n\n"
            f"✅ **Название:** {card_name}\n\n"
            f"📝 **Шаг 2/3:** Введите описание карточки\n\n"
            f"ℹ️ **Требования:**\n"
            f"• Максимум 200 символов\n"
            f"• Интересное описание\n"
            f"• Без оскорблений"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        
        await message.answer(description_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error processing card name: {e}")
        await message.answer("❌ Ошибка при обработке названия")


@router.message(StateFilter(SuggestionStates.waiting_for_card_description))
async def process_card_description(message: Message, state: FSMContext):
    """Обработка описания карточки"""
    try:
        if not message.text:
            await message.answer("❌ Пожалуйста, отправьте текстовое описание карточки")
            return
        
        description = message.text.strip()
        
        # Валидация описания
        if len(description) > 200:
            await message.answer("❌ Описание слишком длинное (максимум 200 символов)")
            return
        
        if len(description) < 10:
            await message.answer("❌ Описание слишком короткое (минимум 10 символов)")
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        card_name = data.get("card_name")
        
        if not card_name:
            await message.answer("❌ Ошибка: название карточки не найдено. Начните заново.")
            await state.clear()
            return
        
        # Сохраняем описание и переходим к медиа
        await state.update_data(card_description=description)
        await state.set_state(SuggestionStates.waiting_for_card_media)
        
        media_text = (
            f"🧩 **Предложение карточки**\n\n"
            f"✅ **Название:** {card_name}\n"
            f"✅ **Описание:** {description[:50]}{'...' if len(description) > 50 else ''}\n\n"
            f"🎬 **Шаг 3/3:** Отправьте гифку или изображение\n\n"
            f"📎 **Поддерживаемые форматы:**\n"
            f"• GIF анимации 🎭\n"
            f"• Фотографии 📸\n"
            f"• Видео 🎥\n\n"
            f"⚠️ **Требования:**\n"
            f"• Размер до 50 МБ\n"
            f"• Подходящий контент\n"
            f"• Без авторских прав"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        
        await message.answer(media_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error processing card description: {e}")
        await message.answer("❌ Ошибка при обработке описания")


@router.message(StateFilter(SuggestionStates.waiting_for_card_media))
async def process_card_media(message: Message, state: FSMContext):
    """Обработка медиа-файла для карточки"""
    try:
        media_file_id = None
        media_type = None
        
        # Определяем тип медиа
        if message.animation:  # GIF
            media_file_id = message.animation.file_id
            media_type = "animation"
            
            # Проверяем размер (50 МБ = 50 * 1024 * 1024 байт)
            if message.animation.file_size and message.animation.file_size > 50 * 1024 * 1024:
                await message.answer("❌ Файл слишком большой (максимум 50 МБ)")
                return
                
        elif message.photo:  # Фото
            media_file_id = message.photo[-1].file_id  # Берем самое большое разрешение
            media_type = "photo"
            
        elif message.video:  # Видео
            media_file_id = message.video.file_id
            media_type = "video"
            
            # Проверяем размер
            if message.video.file_size and message.video.file_size > 50 * 1024 * 1024:
                await message.answer("❌ Файл слишком большой (максимум 50 МБ)")
                return
                
        else:
            await message.answer(
                "❌ Неподдерживаемый формат!\n\n"
                "📎 Отправьте:\n"
                "• GIF анимацию 🎭\n"
                "• Фотографию 📸\n"
                "• Видео 🎥"
            )
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        card_name = data.get("card_name")
        description = data.get("card_description")
        
        if not card_name or not description:
            await message.answer("❌ Ошибка: данные карточки потеряны. Начните заново.")
            await state.clear()
            return
        
        # Создаем предложение с медиа
        suggestion = CardSuggestion(
            user_id=message.from_user.id,
            username=message.from_user.username or message.from_user.first_name or f"User{message.from_user.id}",
            card_name=card_name,
            description=description,
            media_file_id=media_file_id,
            media_type=media_type
        )
        
        suggestions_storage.append(suggestion)
        await state.clear()
        
        # Отправляем уведомление админу с медиа
        admin_notification = (
            f"🧩 **НОВОЕ ПРЕДЛОЖЕНИЕ КАРТОЧКИ**\n\n"
            f"👤 От: @{suggestion.username} (ID: {suggestion.user_id})\n"
            f"🎴 Название: {suggestion.card_name}\n"
            f"📝 Описание: {suggestion.description}\n"
            f"🎬 Медиа: {media_type}\n"
            f"📅 Время: {suggestion.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Рассмотрите предложение в админке!"
        )
        
        try:
            # Отправляем админу медиа + текст
            if media_type == "animation":
                await message.bot.send_animation(
                    chat_id=settings.admin_user_id,
                    animation=media_file_id,
                    caption=admin_notification
                )
            elif media_type == "photo":
                await message.bot.send_photo(
                    chat_id=settings.admin_user_id,
                    photo=media_file_id,
                    caption=admin_notification
                )
            elif media_type == "video":
                await message.bot.send_video(
                    chat_id=settings.admin_user_id,
                    video=media_file_id,
                    caption=admin_notification
                )
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
        
        # Названия типов медиа
        media_type_names = {
            "animation": "GIF анимация 🎭",
            "photo": "Фотография 📸", 
            "video": "Видео 🎥"
        }
        
        # Подтверждение пользователю
        success_text = (
            f"✅ **Предложение отправлено!**\n\n"
            f"🎴 **Название:** {card_name}\n"
            f"📝 **Описание:** {description[:100]}{'...' if len(description) > 100 else ''}\n"
            f"🎬 **Медиа:** {media_type_names.get(media_type, media_type)}\n\n"
            f"🔔 Администратор получил уведомление\n"
            f"⏰ Ожидайте рассмотрения\n\n"
            f"🎁 **При принятии вы получите:**\n"
            f"• 🪙 100 монет\n"
            f"• ✨ 50 опыта\n"
            f"• 🎴 Эксклюзивную копию карточки"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🧩 Предложить еще", callback_data="suggest_card"),
                InlineKeyboardButton(text="📚 Мои карточки", callback_data="my_cards")
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(success_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error processing card media: {e}")
        await message.answer("❌ Ошибка при обработке медиа-файла")


@router.callback_query(F.data == "admin_suggestions")
async def admin_view_suggestions(callback: CallbackQuery):
    """Просмотр предложений для админа"""
    try:
        # Проверяем права админа
        if callback.from_user.id != settings.admin_user_id:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        
        pending_suggestions = [s for s in suggestions_storage if s.status == "pending"]
        
        if not pending_suggestions:
            suggestions_text = (
                "🧩 **Предложения карточек**\n\n"
                "📭 Нет новых предложений\n\n"
                "ℹ️ Когда пользователи предложат карточки,\n"
                "они появятся здесь для рассмотрения"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_suggestions")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
            ])
        else:
            suggestions_text = (
                f"🧩 **Предложения карточек**\n\n"
                f"📋 Новых предложений: {len(pending_suggestions)}\n\n"
            )
            
            keyboard_buttons = []
            for i, suggestion in enumerate(pending_suggestions[:5]):  # Показываем первые 5
                button_text = f"{i+1}. {suggestion.card_name[:20]}..."
                keyboard_buttons.append([InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"review_suggestion:{i}"
                )])
            
            if len(pending_suggestions) > 5:
                suggestions_text += f"... и еще {len(pending_suggestions) - 5} предложений"
            
            keyboard_buttons.extend([
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_suggestions")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(suggestions_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error viewing suggestions: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("review_suggestion:"))
async def review_suggestion(callback: CallbackQuery):
    """Рассмотрение конкретного предложения"""
    try:
        if callback.from_user.id != settings.admin_user_id:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        
        suggestion_index = int(callback.data.split(":")[1])
        pending_suggestions = [s for s in suggestions_storage if s.status == "pending"]
        
        if suggestion_index >= len(pending_suggestions):
            await callback.answer("❌ Предложение не найдено", show_alert=True)
            return
        
        suggestion = pending_suggestions[suggestion_index]
        
        media_info = ""
        if suggestion.media_type:
            media_type_names = {
                "animation": "GIF анимация 🎭",
                "photo": "Фотография 📸", 
                "video": "Видео 🎥"
            }
            media_info = f"🎬 **Медиа:** {media_type_names.get(suggestion.media_type, suggestion.media_type)}\n"
        
        review_text = (
            f"🧩 **Рассмотрение предложения**\n\n"
            f"👤 **Автор:** @{suggestion.username}\n"
            f"🆔 **ID:** {suggestion.user_id}\n"
            f"📅 **Дата:** {suggestion.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🎴 **Название:** {suggestion.card_name}\n\n"
            f"📝 **Описание:**\n{suggestion.description}\n\n"
            f"{media_info}"
            f"**Что делать с предложением?**"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_suggestion:{suggestion_index}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_suggestion:{suggestion_index}")
            ],
            [
                InlineKeyboardButton(text="🚫 Забанить автора", callback_data=f"ban_suggestion_user:{suggestion_index}")
            ],
            [InlineKeyboardButton(text="◀️ К списку", callback_data="admin_suggestions")]
        ])
        
        # Если есть медиа, отправляем его отдельно
        if suggestion.media_file_id and suggestion.media_type:
            try:
                if suggestion.media_type == "animation":
                    await callback.bot.send_animation(
                        chat_id=callback.from_user.id,
                        animation=suggestion.media_file_id,
                        caption=f"🎬 Медиа для карточки '{suggestion.card_name}'"
                    )
                elif suggestion.media_type == "photo":
                    await callback.bot.send_photo(
                        chat_id=callback.from_user.id,
                        photo=suggestion.media_file_id,
                        caption=f"🎬 Медиа для карточки '{suggestion.card_name}'"
                    )
                elif suggestion.media_type == "video":
                    await callback.bot.send_video(
                        chat_id=callback.from_user.id,
                        video=suggestion.media_file_id,
                        caption=f"🎬 Медиа для карточки '{suggestion.card_name}'"
                    )
            except Exception as e:
                logger.error(f"Failed to send media: {e}")
        
        await callback.message.edit_text(review_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error reviewing suggestion: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("approve_suggestion:"))
async def approve_suggestion(callback: CallbackQuery):
    """Принятие предложения"""
    try:
        if callback.from_user.id != settings.admin_user_id:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        
        suggestion_index = int(callback.data.split(":")[1])
        pending_suggestions = [s for s in suggestions_storage if s.status == "pending"]
        
        if suggestion_index >= len(pending_suggestions):
            await callback.answer("❌ Предложение не найдено", show_alert=True)
            return
        
        suggestion = pending_suggestions[suggestion_index]
        suggestion.status = "approved"
        
        # Награждаем пользователя
        user = await user_service.get_user_by_telegram_id(suggestion.user_id)
        if user:
            user.coins += 100
            await user_service.add_experience(user, 50)
            await user_service.update_user(user)
            
            # Уведомляем пользователя
            reward_message = (
                f"🎉 **Ваше предложение принято!**\n\n"
                f"🎴 Карточка: **{suggestion.card_name}**\n\n"
                f"🎁 **Награда получена:**\n"
                f"• 🪙 +100 монет\n"
                f"• ✨ +50 опыта\n\n"
                f"Спасибо за вклад в развитие игры!"
            )
            
            try:
                await callback.bot.send_message(
                    chat_id=suggestion.user_id,
                    text=reward_message
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
        
        result_text = (
            f"✅ **Предложение принято!**\n\n"
            f"🎴 Карточка: {suggestion.card_name}\n"
            f"👤 Автор: @{suggestion.username}\n"
            f"🎁 Награда выдана пользователю\n\n"
            f"💡 Теперь вы можете создать эту карточку\n"
            f"через админ-панель"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать карточку", callback_data="add_card"),
                InlineKeyboardButton(text="📋 К предложениям", callback_data="admin_suggestions")
            ]
        ])
        
        await callback.message.edit_text(result_text, reply_markup=keyboard)
        await callback.answer("✅ Предложение принято!")
        
    except Exception as e:
        logger.error(f"Error approving suggestion: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("reject_suggestion:"))
async def reject_suggestion(callback: CallbackQuery):
    """Отклонение предложения"""
    try:
        if callback.from_user.id != settings.admin_user_id:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        
        suggestion_index = int(callback.data.split(":")[1])
        pending_suggestions = [s for s in suggestions_storage if s.status == "pending"]
        
        if suggestion_index >= len(pending_suggestions):
            await callback.answer("❌ Предложение не найдено", show_alert=True)
            return
        
        suggestion = pending_suggestions[suggestion_index]
        suggestion.status = "rejected"
        
        # Уведомляем пользователя
        reject_message = (
            f"❌ **Ваше предложение отклонено**\n\n"
            f"🎴 Карточка: **{suggestion.card_name}**\n\n"
            f"📝 **Возможные причины:**\n"
            f"• Неподходящее содержание\n"
            f"• Слишком похоже на существующие\n"
            f"• Не соответствует тематике\n\n"
            f"💡 Попробуйте предложить что-то другое!"
        )
        
        try:
            await callback.bot.send_message(
                chat_id=suggestion.user_id,
                text=reject_message
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
        
        result_text = (
            f"❌ **Предложение отклонено**\n\n"
            f"🎴 Карточка: {suggestion.card_name}\n"
            f"👤 Автор: @{suggestion.username}\n"
            f"📨 Пользователь уведомлен об отклонении"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К предложениям", callback_data="admin_suggestions")]
        ])
        
        await callback.message.edit_text(result_text, reply_markup=keyboard)
        await callback.answer("❌ Предложение отклонено")
        
    except Exception as e:
        logger.error(f"Error rejecting suggestion: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("ban_suggestion_user:"))
async def ban_suggestion_user(callback: CallbackQuery):
    """Бан пользователя за плохое предложение"""
    try:
        # Проверяем права админа
        if callback.from_user.id != settings.admin_user_id:
            await callback.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        
        suggestion_index = int(callback.data.split(":")[-1])
        
        # Находим предложение
        pending_suggestions = [s for s in suggestions_storage if s.status == "pending"]
        if suggestion_index >= len(pending_suggestions):
            await callback.answer("❌ Предложение не найдено", show_alert=True)
            return
        
        suggestion = pending_suggestions[suggestion_index]
        
        # Получаем пользователя
        from services.user_service import user_service
        user = await user_service.get_user_by_telegram_id(suggestion.user_id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Баним пользователя
        user.is_suggestion_banned = True
        user.suggestion_ban_reason = f"Неподходящее предложение карточки '{suggestion.card_name}'"
        user.suggestion_ban_date = datetime.utcnow()
        
        await user_service.update_user(user)
        
        # Отклоняем предложение
        suggestion.status = "banned"
        
        # Уведомляем пользователя о бане
        try:
            ban_notification = (
                f"🚫 **Вы заблокированы для предложений карточек**\n\n"
                f"**Причина:** Неподходящее содержание\n"
                f"**Предложение:** '{suggestion.card_name}'\n"
                f"**Дата:** {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"❗ Соблюдайте правила сообщества!\n"
                f"📞 Для разбана обращайтесь: @Siriusatop123"
            )
            
            await callback.bot.send_message(
                chat_id=suggestion.user_id,
                text=ban_notification
            )
        except Exception as e:
            logger.error(f"Failed to send ban notification: {e}")
        
        # Подтверждение админу
        await callback.answer(
            f"🚫 Пользователь @{suggestion.username} забанен!\n"
            f"Предложение '{suggestion.card_name}' отклонено.",
            show_alert=True
        )
        
        # Возвращаемся к списку предложений
        await admin_view_suggestions(callback)
        
    except Exception as e:
        logger.error(f"Error banning suggestion user: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)