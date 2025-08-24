from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from config import settings

router = Router()


class NotifyStates(StatesGroup):
    waiting_for_notify_card_name = State()
    waiting_for_giveaway_card_name = State()
    waiting_for_broadcast_message = State()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id in settings.admin_ids


# Обработчик уведомлений о карточках
@router.callback_query(F.data == "notify_card")
async def notify_card_start(callback: CallbackQuery, state: FSMContext):
    """Начало отправки уведомления о карточке"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🆕 **Уведомление о новой карточке**\n\n"
        "📝 Введите название карточки для уведомления всех игроков:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_notifications")]
        ])
    )
    
    await state.set_state(NotifyStates.waiting_for_notify_card_name)
    await callback.answer()


@router.message(StateFilter(NotifyStates.waiting_for_notify_card_name))
async def notify_card_process(message: Message, state: FSMContext):
    """Обработка уведомления о карточке"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        card_name = message.text.strip()
        if not card_name:
            await message.answer("❌ Введите название карточки")
            return
        
        # Проверяем существование карточки
        from services.card_service import card_service
        card = await card_service.get_card_by_name(card_name)
        if not card:
            await message.answer(f"❌ Карточка '{card_name}' не найдена")
            return
        
        await state.clear()
        
        # Отправляем уведомления
        from services.notification_service import notification_service
        
        await message.answer(f"📢 Отправляю уведомления о карточке '{card_name}'...")
        
        notification_count = await notification_service.notify_new_card(card)
        
        result_text = (
            f"✅ **Уведомления отправлены!**\n\n"
            f"🎴 Карточка: '{card_name}'\n"
            f"📨 Уведомлений отправлено: {notification_count}\n"
            f"👥 Всего пользователей с включенными уведомлениями"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Error processing card notification: {e}")
        await message.answer("❌ Ошибка при отправке уведомлений")
        await state.clear()


# Улучшенная раздача карточек с уведомлениями
@router.callback_query(F.data == "enhanced_giveaway")
async def enhanced_giveaway_start(callback: CallbackQuery, state: FSMContext):
    """Начало улучшенной раздачи карточки с уведомлениями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎁 **Раздача + Уведомления**\n\n"
        "📝 Введите название карточки для раздачи всем игрокам.\n"
        "Карточка будет выдана + отправлены уведомления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_gifts")]
        ])
    )
    
    await state.set_state(NotifyStates.waiting_for_giveaway_card_name)
    await callback.answer()


@router.message(StateFilter(NotifyStates.waiting_for_giveaway_card_name))
async def enhanced_giveaway_process(message: Message, state: FSMContext):
    """Обработка улучшенной раздачи карточки"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        card_name = message.text.strip()
        if not card_name:
            await message.answer("❌ Введите название карточки")
            return
        
        # Проверяем существование карточки
        from services.card_service import card_service
        from services.user_service import user_service
        
        card = await card_service.get_card_by_name(card_name)
        if not card:
            await message.answer(f"❌ Карточка '{card_name}' не найдена")
            return
        
        await state.clear()
        
        await message.answer(f"🎁 Начинаю раздачу карточки '{card_name}' + уведомления...")
        
        # Получаем всех пользователей
        users = await user_service.get_all_users()
        success_count = 0
        
        # Раздаем карточки
        for user in users:
            try:
                await user_service.add_card_to_user(user, str(card.id))
                success_count += 1
            except Exception as e:
                logger.error(f"Error giving card to user {user.telegram_id}: {e}")
        
        # Обновляем статистику карточки
        await card_service.update_card_stats(card_name, success_count, success_count)
        
        # Отправляем уведомления
        from services.notification_service import notification_service
        notification_count = await notification_service.notify_new_card(card)
        
        result_text = (
            f"✅ **Раздача + уведомления завершены!**\n\n"
            f"🎴 Карточка: '{card_name}'\n"
            f"👥 Получили карточку: {success_count} игроков\n"
            f"📨 Получили уведомление: {notification_count} игроков\n"
            f"📊 Всего игроков: {len(users)}\n\n"
            f"🎉 Карточка успешно добавлена в коллекции и все уведомлены!"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Error processing enhanced giveaway: {e}")
        await message.answer("❌ Ошибка при раздаче карточки")
        await state.clear()


# Массовая рассылка сообщений
@router.callback_query(F.data == "broadcast_message")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало массовой рассылки сообщения"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 **Массовая рассылка**\n\n"
        "✍️ Введите сообщение для отправки всем пользователям с включенными уведомлениями:\n\n"
        "💡 Поддерживается Markdown форматирование",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_notifications")]
        ])
    )
    
    await state.set_state(NotifyStates.waiting_for_broadcast_message)
    await callback.answer()


@router.message(StateFilter(NotifyStates.waiting_for_broadcast_message))
async def broadcast_process(message: Message, state: FSMContext):
    """Обработка массовой рассылки"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        broadcast_text = message.text.strip()
        if not broadcast_text:
            await message.answer("❌ Введите текст сообщения")
            return
        
        await state.clear()
        
        # Отправляем рассылку
        from services.notification_service import notification_service
        
        await message.answer(f"📢 Отправляю рассылку...")
        
        sent_count = await notification_service.broadcast_message(broadcast_text)
        
        result_text = (
            f"✅ **Рассылка завершена!**\n\n"
            f"📨 Сообщений отправлено: {sent_count}\n"
            f"👥 Пользователям с включенными уведомлениями\n\n"
            f"📝 **Отправленное сообщение:**\n{broadcast_text[:100]}{'...' if len(broadcast_text) > 100 else ''}"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Error processing broadcast: {e}")
        await message.answer("❌ Ошибка при отправке рассылки")
        await state.clear()


# Сброс rate limits
@router.callback_query(F.data == "admin_reset_limits")
async def reset_limits_handler(callback: CallbackQuery):
    """Сброс rate limits для всех пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        from middleware.rate_limiter import rate_limiter
        rate_limiter.reset_all_limits()
        
        await callback.answer("✅ Все rate limits сброшены!", show_alert=True)
        logger.info(f"Admin {callback.from_user.id} reset all rate limits")
        
    except Exception as e:
        logger.error(f"Error resetting rate limits: {e}")
        await callback.answer("❌ Ошибка при сбросе лимитов", show_alert=True)
