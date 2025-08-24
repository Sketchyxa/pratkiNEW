from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger

from models.user import User
from services.user_service import user_service
from services.easter_egg_service import easter_egg_service

router = Router()


@router.callback_query(F.data == "easter_egg")
async def easter_egg_menu(callback: CallbackQuery):
    """Меню пасхалок"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден. Используйте /start", show_alert=True)
            return
        
        # Получаем статус пасхалок
        status_text = await easter_egg_service.get_easter_egg_status(user)
        
        # Добавляем подсказку
        hint_text = easter_egg_service.get_easter_egg_hint()
        
        full_text = f"{status_text}\n\n{hint_text}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(full_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in easter egg menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню пасхалок", show_alert=True)


@router.message(lambda message: message.text and message.text.strip().isdigit())
async def check_easter_egg_code(message: Message):
    """Проверяет введенный код пасхалки"""
    try:
        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            return  # Игнорируем если пользователь не зарегистрирован
        
        code = message.text.strip()
        
        # Проверяем пасхалку
        success, response_text, coins = await easter_egg_service.check_easter_egg(user, code)
        
        # Отправляем ответ пользователю
        await message.answer(response_text)
        
    except Exception as e:
        logger.error(f"Error checking easter egg code: {e}")
        # Не отправляем сообщение об ошибке пользователю, чтобы не раскрывать систему


@router.message(Command("easter"))
async def easter_egg_command(message: Message):
    """Команда для просмотра пасхалок"""
    try:
        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        # Получаем статус пасхалок
        status_text = await easter_egg_service.get_easter_egg_status(user)
        
        # Добавляем подсказку
        hint_text = easter_egg_service.get_easter_egg_hint()
        
        full_text = f"{status_text}\n\n{hint_text}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(full_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in easter egg command: {e}")
        await message.answer("❌ Ошибка при загрузке пасхалок")
