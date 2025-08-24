import os
import aiofiles
from datetime import datetime
from typing import List, Optional
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from models.user import User
from models.card import Card
from services.user_service import user_service
from services.card_service import card_service
from services.migration_service import migration_service
from config import settings

router = Router()


async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None, success_message: str = None):
    """Безопасное редактирование сообщения с обработкой ошибки 'message is not modified'"""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        if success_message:
            await callback.answer(success_message)
        else:
            await callback.answer()
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("📊 Данные актуальны")
        else:
            await callback.answer("❌ Ошибка при обновлении")
            logger.error(f"Error editing message: {e}")


class AdminStates(StatesGroup):
    waiting_for_card_name = State()
    waiting_for_card_description = State()
    waiting_for_card_rarity = State()
    waiting_for_card_media = State()
    waiting_for_dump_file = State()
    waiting_for_json_file = State()
    waiting_for_announcement = State()
    waiting_for_user_id = State()
    waiting_for_gift_coins = State()
    waiting_for_gift_exp = State()
    waiting_for_gift_card = State()
    waiting_for_experience = State()
    waiting_for_give_card_user = State()
    waiting_for_give_card_name = State()
    waiting_for_mass_gift_count = State()
    waiting_for_mass_gift_card = State()
    waiting_for_notify_card_name = State()  # Для уведомлений о карточках


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id == settings.admin_user_id


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главная панель администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Карточки", callback_data="admin_cards"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🎪 Ивенты", callback_data="admin_events"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📈 Аналитика", callback_data="admin_analytics"),
            InlineKeyboardButton(text="💰 Скидки", callback_data="admin_discounts")
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin_notifications"),
            InlineKeyboardButton(text="⏰ Авто-раздачи", callback_data="admin_auto_giveaways")
        ],
        [
            InlineKeyboardButton(text="📢 Объявление", callback_data="admin_announce"),
            InlineKeyboardButton(text="🎁 Раздачи", callback_data="admin_gifts")
        ],
        [InlineKeyboardButton(text="📤 Импорт", callback_data="admin_import")]
    ])
    
    await message.answer("🔧 **Панель администратора**\nВыберите действие:", reply_markup=keyboard)


@router.callback_query(F.data == "admin_cards")
async def admin_cards_menu(callback: CallbackQuery):
    """Меню управления карточками"""
    if not is_admin(callback.from_user.id):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить карточку", callback_data="add_card"),
            InlineKeyboardButton(text="📝 Редактировать", callback_data="edit_card_menu")
        ],
        [
            InlineKeyboardButton(text="📋 Список карточек", callback_data="list_cards"),
            InlineKeyboardButton(text="🗑 Удалить карточку", callback_data="delete_card_menu")
        ],
        [
            InlineKeyboardButton(text="🎨 Предложения", callback_data="admin_suggestions"),
            InlineKeyboardButton(text="🔍 Поиск карточек", callback_data="search_cards")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text("📋 **Управление карточками**\nВыберите действие:", reply_markup=keyboard)


@router.callback_query(F.data == "add_card")
async def add_card_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления карточки"""
    if not is_admin(callback.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_for_card_name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cards")]
    ])
    
    await callback.message.edit_text("📝 Введите название новой карточки:", reply_markup=keyboard)


@router.message(StateFilter(AdminStates.waiting_for_card_name))
async def add_card_name(message: Message, state: FSMContext):
    """Получение названия карточки"""
    if not is_admin(message.from_user.id):
        return
    
    card_name = message.text.strip()
    
    # Проверяем, существует ли карточка
    existing_card = await card_service.get_card_by_name(card_name)
    if existing_card:
        await message.answer("❌ Карточка с таким названием уже существует!")
        return
    
    await state.update_data(card_name=card_name)
    await state.set_state(AdminStates.waiting_for_card_description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cards")]
    ])
    
    await message.answer("📖 Введите описание карточки:", reply_markup=keyboard)


@router.message(StateFilter(AdminStates.waiting_for_card_description))
async def add_card_description(message: Message, state: FSMContext):
    """Получение описания карточки"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое описание карточки")
        return
    
    await state.update_data(card_description=message.text.strip())
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚪ Common", callback_data="rarity_common"),
            InlineKeyboardButton(text="🔵 Rare", callback_data="rarity_rare")
        ],
        [
            InlineKeyboardButton(text="🟣 Epic", callback_data="rarity_epic"),
            InlineKeyboardButton(text="🟡 Legendary", callback_data="rarity_legendary")
        ],
        [InlineKeyboardButton(text="🔴 Artifact", callback_data="rarity_artifact")]
    ])
    
    await state.set_state(AdminStates.waiting_for_card_rarity)
    await message.answer("⭐ Выберите редкость карточки:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("rarity_"))
async def add_card_rarity(callback: CallbackQuery, state: FSMContext):
    """Получение редкости карточки"""
    if not is_admin(callback.from_user.id):
        return
    
    rarity = callback.data.split("_")[1]
    await state.update_data(card_rarity=rarity)
    await state.set_state(AdminStates.waiting_for_card_media)
    
    await callback.message.edit_text(
        "🖼 Отправьте изображение, GIF или видео для карточки\n"
        "Или отправьте 'skip' чтобы пропустить:"
    )


@router.message(StateFilter(AdminStates.waiting_for_card_media))
async def add_card_media(message: Message, state: FSMContext):
    """Получение медиафайла карточки"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    
    image_url = gif_url = video_url = None
    
    if message.text and message.text.lower() == 'skip':
        pass  # Пропускаем медиафайл
    elif message.photo:
        # Сохраняем фото
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        file_name = f"card_{data['card_name']}_{photo.file_id}.jpg"
        file_path = f"assets/images/{file_name}"
        
        os.makedirs("assets/images", exist_ok=True)
        await message.bot.download_file(file_info.file_path, file_path)
        image_url = file_path
        
    elif message.animation:
        # Сохраняем GIF
        animation = message.animation
        file_info = await message.bot.get_file(animation.file_id)
        file_name = f"card_{data['card_name']}_{animation.file_id}.gif"
        file_path = f"assets/images/{file_name}"
        
        os.makedirs("assets/images", exist_ok=True)
        await message.bot.download_file(file_info.file_path, file_path)
        gif_url = file_path
        
    elif message.video:
        # Сохраняем видео
        video = message.video
        file_info = await message.bot.get_file(video.file_id)
        file_name = f"card_{data['card_name']}_{video.file_id}.mp4"
        file_path = f"assets/images/{file_name}"
        
        os.makedirs("assets/images", exist_ok=True)
        await message.bot.download_file(file_info.file_path, file_path)
        video_url = file_path
    
    # Создаем карточку
    card = await card_service.create_card(
        name=data['card_name'],
        description=data['card_description'],
        rarity=data['card_rarity'],
        image_url=image_url,
        gif_url=gif_url,
        video_url=video_url,
        created_by=message.from_user.id
    )
    
    await state.clear()
    
    if card:
        rarity_emoji = card.get_rarity_emoji()
        await message.answer(
            f"✅ Карточка успешно создана!\n\n"
            f"{rarity_emoji} **{card.name}**\n"
            f"📖 {card.description}\n"
            f"⭐ {card.rarity.title()}"
        )
    else:
        await message.answer("❌ Ошибка при создании карточки")


@router.callback_query(F.data == "list_cards")
async def list_all_cards(callback: CallbackQuery):
    """Список всех карточек"""
    if not is_admin(callback.from_user.id):
        return
    
    cards = await card_service.get_all_cards()
    
    if not cards:
        await callback.message.edit_text("📋 Карточки не найдены")
        return
    
    # Группируем по редкости
    cards_by_rarity = {}
    for card in cards:
        if card.rarity not in cards_by_rarity:
            cards_by_rarity[card.rarity] = []
        cards_by_rarity[card.rarity].append(card)
    
    text = "📋 **Все карточки:**\n\n"
    
    for rarity in ["common", "rare", "epic", "legendary", "artifact"]:
        if rarity in cards_by_rarity:
            rarity_info = settings.rarities.get(rarity, {})
            emoji = rarity_info.get("emoji", "❓")
            name = rarity_info.get("name", rarity.title())
            
            text += f"{emoji} **{name}** ({len(cards_by_rarity[rarity])})\n"
            for card in cards_by_rarity[rarity][:5]:  # Показываем только первые 5
                text += f"   • {card.name}\n"
            
            if len(cards_by_rarity[rarity]) > 5:
                text += f"   ... и еще {len(cards_by_rarity[rarity]) - 5}\n"
            text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_import")
async def admin_import_menu(callback: CallbackQuery):
    """Меню импорта данных"""
    if not is_admin(callback.from_user.id):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗄 MySQL дамп", callback_data="import_mysql"),
            InlineKeyboardButton(text="📄 JSON карточки", callback_data="import_json")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(
        "📤 **Импорт данных**\n\n"
        "🗄 **MySQL дамп** - импорт пользователей и карточек из SQL дампа\n"
        "📄 **JSON карточки** - импорт карточек из JSON файла\n\n"
        "Выберите тип импорта:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "import_mysql")
async def import_mysql_start(callback: CallbackQuery, state: FSMContext):
    """Начало импорта MySQL дампа"""
    if not is_admin(callback.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_for_dump_file)
    await callback.message.edit_text(
        "📤 **Импорт MySQL дампа**\n\n"
        "Отправьте .sql файл с дампом базы данных.\n"
        "⚠️ Убедитесь, что дамп содержит таблицы: users, cards, user_cards"
    )


@router.message(StateFilter(AdminStates.waiting_for_dump_file))
async def import_mysql_file(message: Message, state: FSMContext):
    """Обработка загруженного MySQL дампа"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте файл")
        return
    
    document = message.document
    if not document.file_name.endswith('.sql'):
        await message.answer("❌ Файл должен иметь расширение .sql")
        return
    
    try:
        # Скачиваем файл
        file_info = await message.bot.get_file(document.file_id)
        file_path = f"temp_dump_{document.file_id}.sql"
        
        await message.bot.download_file(file_info.file_path, file_path)
        
        await message.answer("⏳ Начинаю импорт данных...")
        
        # Импортируем данные
        stats = await migration_service.import_mysql_dump(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if "error" in stats:
            await message.answer(f"❌ Ошибка импорта: {stats['error']}")
        else:
            text = "✅ **Импорт завершен!**\n\n"
            text += f"👥 Пользователей: {stats['users_imported']}\n"
            text += f"🃏 Карточек: {stats['cards_imported']}\n"
            text += f"🎴 Коллекций: {stats['user_cards_imported']}\n"
            
            if stats['errors']:
                text += f"\n⚠️ Ошибок: {len(stats['errors'])}"
            
            await message.answer(text)
        
    except Exception as e:
        logger.error(f"Error importing MySQL dump: {e}")
        await message.answer(f"❌ Ошибка при импорте: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data == "import_json")
async def import_json_start(callback: CallbackQuery, state: FSMContext):
    """Начало импорта JSON карточек"""
    if not is_admin(callback.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_for_json_file)
    await callback.message.edit_text(
        "📄 **Импорт JSON карточек**\n\n"
        "Отправьте .json файл с карточками.\n"
        "Формат: [{'name': '...', 'description': '...', 'rarity': '...', ...}, ...]"
    )


@router.message(StateFilter(AdminStates.waiting_for_json_file))
async def import_json_file(message: Message, state: FSMContext):
    """Обработка загруженного JSON файла"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте файл")
        return
    
    document = message.document
    if not document.file_name.endswith('.json'):
        await message.answer("❌ Файл должен иметь расширение .json")
        return
    
    try:
        # Скачиваем файл
        file_info = await message.bot.get_file(document.file_id)
        file_path = f"temp_cards_{document.file_id}.json"
        
        await message.bot.download_file(file_info.file_path, file_path)
        
        await message.answer("⏳ Начинаю импорт карточек...")
        
        # Импортируем карточки
        stats = await migration_service.import_json_cards(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if "error" in stats:
            await message.answer(f"❌ Ошибка импорта: {stats['error']}")
        else:
            text = "✅ **Импорт карточек завершен!**\n\n"
            text += f"➕ Новых карточек: {stats['cards_imported']}\n"
            text += f"🔄 Обновлено карточек: {stats['cards_updated']}\n"
            
            if stats['errors']:
                text += f"\n⚠️ Ошибок: {len(stats['errors'])}"
            
            await message.answer(text)
        
    except Exception as e:
        logger.error(f"Error importing JSON cards: {e}")
        await message.answer(f"❌ Ошибка при импорте: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика системы"""
    if not is_admin(callback.from_user.id):
        return
    
    try:
        # Получаем статистику
        user_stats = await user_service.get_user_stats()
        card_stats = await card_service.get_card_stats()
        
        text = "📊 **Статистика системы**\n\n"
        
        # Пользователи
        text += "👥 **Пользователи:**\n"
        text += f"   Всего: {user_stats.get('total_users', 0)}\n"
        text += f"   Активных за неделю: {user_stats.get('active_users_week', 0)}\n"
        text += f"   Средний уровень: {user_stats.get('average_level', 0)}\n\n"
        
        # Карточки
        text += "🃏 **Карточки:**\n"
        text += f"   Всего: {card_stats.get('total_cards', 0)}\n"
        if card_stats.get('most_popular'):
            text += f"   Популярная: {card_stats['most_popular']}\n"
        if card_stats.get('rarest'):
            text += f"   Редкая: {card_stats['rarest']}\n\n"
        
        # Распределение по редкости
        if card_stats.get('rarity_distribution'):
            text += "⭐ **По редкости:**\n"
            for rarity, count in card_stats['rarity_distribution'].items():
                emoji = settings.rarities.get(rarity, {}).get('emoji', '❓')
                text += f"   {emoji} {rarity.title()}: {count}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        await callback.message.edit_text("❌ Ошибка при получении статистики")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат в главное меню админки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Карточки", callback_data="admin_cards"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🎪 Ивенты", callback_data="admin_events"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📈 Аналитика", callback_data="admin_analytics"),
            InlineKeyboardButton(text="💰 Скидки", callback_data="admin_discounts")
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin_notifications"),
            InlineKeyboardButton(text="⏰ Авто-раздачи", callback_data="admin_auto_giveaways")
        ],
        [
            InlineKeyboardButton(text="📢 Объявление", callback_data="admin_announce"),
            InlineKeyboardButton(text="🎁 Раздачи", callback_data="admin_gifts")
        ],
        [InlineKeyboardButton(text="📤 Импорт", callback_data="admin_import")]
    ])
    
    await callback.message.edit_text("🔧 **Панель администратора**\nВыберите действие:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_announce")
async def admin_announce_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания объявления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_announcement)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(
        "📢 **Создание объявления**\n\n"
        "Напишите текст объявления, которое будет отправлено всем пользователям:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_announcement))
async def admin_announce_send(message: Message, state: FSMContext):
    """Отправка объявления всем пользователям"""
    if not is_admin(message.from_user.id):
        return
    
    announcement_text = message.text.strip()
    
    if not announcement_text:
        await message.answer("❌ Текст объявления не может быть пустым")
        return
    
    await state.clear()
    
    try:
        # Получаем всех пользователей
        users = await user_service.get_all_users()
        sent_count = 0
        failed_count = 0
        
        await message.answer(f"📢 Начинаю рассылку объявления {len(users)} пользователям...")
        
        for user in users:
            try:
                # Экранируем специальные символы для Markdown
                safe_announcement = announcement_text.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                full_text = f"📢 **Объявление от администрации:**\n\n{safe_announcement}"
                await message.bot.send_message(user.telegram_id, full_text, parse_mode="Markdown")
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send announcement to {user.telegram_id}: {e}")
        
        result_text = (
            f"✅ **Рассылка завершена!**\n\n"
            f"📤 Отправлено: {sent_count}\n"
            f"❌ Не доставлено: {failed_count}\n"
            f"👥 Всего пользователей: {len(users)}"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Error sending announcement: {e}")
        await message.answer("❌ Ошибка при отправке объявления")


@router.callback_query(F.data == "admin_gifts")
async def admin_gifts_menu(callback: CallbackQuery):
    """Меню раздач"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    gifts_text = (
        "🎁 **Раздачи игрокам**\n\n"
        "Выберите тип раздачи:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪙 Раздача монет", callback_data="gift_coins"),
            InlineKeyboardButton(text="🎴 Раздача карточек", callback_data="gift_cards")
        ],
        [
            InlineKeyboardButton(text="✨ Раздача опыта", callback_data="gift_exp"),
            InlineKeyboardButton(text="🔥 Раздача + Уведомления", callback_data="enhanced_giveaway")
        ],
        [
            InlineKeyboardButton(text="🎁 Особая раздача", callback_data="gift_special")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(gifts_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("gift_"))
async def admin_gift_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчики раздач"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    gift_type = callback.data.split("_")[1]
    
    if gift_type == "coins":
        await state.set_state(AdminStates.waiting_for_gift_coins)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_gifts")]
        ])
        
        await callback.message.edit_text(
            "🪙 **Раздача монет всем игрокам**\n\n"
            "Введите количество монет для раздачи:",
            reply_markup=keyboard
        )
        
    elif gift_type == "exp":
        await state.set_state(AdminStates.waiting_for_gift_exp)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_gifts")]
        ])
        
        await callback.message.edit_text(
            "✨ **Раздача опыта всем игрокам**\n\n"
            "Введите количество опыта для раздачи:",
            reply_markup=keyboard
        )
        
    elif gift_type == "cards":
        await state.set_state(AdminStates.waiting_for_gift_card)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_gifts")]
        ])
        
        await callback.message.edit_text(
            "🎴 **Раздача карточек всем игрокам**\n\n"
            "Введите название карточки для раздачи:",
            reply_markup=keyboard
        )
        
    elif gift_type == "special":
        special_text = (
            "🎁 **Особые раздачи**\n\n"
            "Выберите тип особой раздачи:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎰 Случайная карточка", callback_data="special_random_card"),
                InlineKeyboardButton(text="💰 Монеты + Опыт", callback_data="special_coins_exp")
            ],
            [
                InlineKeyboardButton(text="🔥 Редкая карточка", callback_data="special_rare_card"),
                InlineKeyboardButton(text="🎁 Mega бонус", callback_data="special_mega")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_gifts")]
        ])
        
        await callback.message.edit_text(special_text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    """Меню управления пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        stats = await user_service.get_user_stats()
        
        users_text = (
            "👥 **Управление пользователями**\n\n"
            f"📊 **Статистика:**\n"
            f"• Всего пользователей: {stats.get('total_users', 0)}\n"
            f"• Активных за неделю: {stats.get('active_users_week', 0)}\n"
            f"• Средний уровень: {stats.get('average_level', 0)}\n\n"
            "Выберите действие:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Список пользователей", callback_data="users_list"),
                InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="users_search")
            ],
            [
                InlineKeyboardButton(text="⚡ Топ игроки", callback_data="users_top"),
                InlineKeyboardButton(text="📊 Подробная статистика", callback_data="users_stats")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(users_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin users menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню пользователей", show_alert=True)


# Заглушки для остальных админских функций
@router.callback_query(F.data.in_(["users_list", "users_search", "users_top", "users_stats"]))
async def admin_users_placeholders(callback: CallbackQuery):
    """Заглушки для функций управления пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    placeholders = {
        "users_list": "👥 Список пользователей в разработке",
        "users_search": "🔍 Поиск пользователей в разработке",
        "users_top": "⚡ Топ игроки доступны в /leaderboard",
        "users_stats": "📊 Подробная статистика в разработке"
    }
    
    message_text = placeholders.get(callback.data, "Функция в разработке")
    await callback.answer(message_text, show_alert=True)


@router.message(StateFilter(AdminStates.waiting_for_gift_coins))
async def process_gift_coins(message: Message, state: FSMContext):
    """Обработка раздачи монет"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        coins_amount = int(message.text.strip())
        if coins_amount <= 0:
            await message.answer("❌ Количество монет должно быть положительным числом")
            return
        
        await state.clear()
        
        users = await user_service.get_all_users()
        success_count = 0
        
        await message.answer(f"🪙 Начинаю раздачу {coins_amount} монет {len(users)} игрокам...")
        
        for user in users:
            try:
                user.coins += coins_amount
                await user_service.update_user(user)
                success_count += 1
            except Exception as e:
                logger.error(f"Error giving coins to user {user.telegram_id}: {e}")
        
        result_text = (
            f"✅ **Раздача монет завершена!**\n\n"
            f"🪙 Роздано: {coins_amount} монет\n"
            f"👥 Получили: {success_count} игроков\n"
            f"📊 Всего игроков: {len(users)}"
        )
        
        await message.answer(result_text)
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        logger.error(f"Error processing gift coins: {e}")
        await message.answer("❌ Ошибка при раздаче монет")


@router.message(StateFilter(AdminStates.waiting_for_gift_exp))
async def process_gift_exp(message: Message, state: FSMContext):
    """Обработка раздачи опыта"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        exp_amount = int(message.text.strip())
        if exp_amount <= 0:
            await message.answer("❌ Количество опыта должно быть положительным числом")
            return
        
        await state.clear()
        
        users = await user_service.get_all_users()
        success_count = 0
        
        await message.answer(f"✨ Начинаю раздачу {exp_amount} опыта {len(users)} игрокам...")
        
        for user in users:
            try:
                old_level = user.level
                user.experience += exp_amount
                user.level = user.calculate_level()
                await user_service.update_user(user)
                success_count += 1
            except Exception as e:
                logger.error(f"Error giving exp to user {user.telegram_id}: {e}")
        
        result_text = (
            f"✅ **Раздача опыта завершена!**\n\n"
            f"✨ Роздано: {exp_amount} опыта\n"
            f"👥 Получили: {success_count} игроков\n"
            f"📊 Всего игроков: {len(users)}"
        )
        
        await message.answer(result_text)
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        logger.error(f"Error processing gift exp: {e}")
        await message.answer("❌ Ошибка при раздаче опыта")


@router.message(StateFilter(AdminStates.waiting_for_gift_card))
async def process_gift_card(message: Message, state: FSMContext):
    """Обработка раздачи карточек"""
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
        
        users = await user_service.get_all_users()
        success_count = 0
        
        await message.answer(f"🎴 Начинаю раздачу карточки '{card_name}' {len(users)} игрокам...")
        
        for user in users:
            try:
                await user_service.add_card_to_user(user, str(card.id))
                success_count += 1
                
                # Отправляем уведомление пользователю
                try:
                    username = user.username if user.username else "Anonymous"
                    notification_text = (
                        f"🎁 **Подарок от администрации!**\n\n"
                        f"🎴 Вы получили карточку:\n"
                        f"{card.get_rarity_emoji()} **{card.name}**\n"
                        f"📝 {card.description}\n\n"
                        f"💝 Спасибо за участие в игре!"
                    )
                    await message.bot.send_message(user.telegram_id, notification_text, parse_mode="Markdown")
                except Exception as notify_error:
                    logger.error(f"Failed to notify user {user.telegram_id} about gift: {notify_error}")
                    
            except Exception as e:
                logger.error(f"Error giving card to user {user.telegram_id}: {e}")
        
        # Обновляем статистику карточки
        await card_service.update_card_stats(card_name, success_count, success_count)
        
        result_text = (
            f"✅ **Раздача карточки завершена!**\n\n"
            f"🎴 Роздано: '{card_name}'\n"
            f"👥 Получили: {success_count} игроков\n"
            f"📊 Всего игроков: {len(users)}"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Error processing gift card: {e}")
        await message.answer("❌ Ошибка при раздаче карточки")


# Обработчики особых раздач
@router.callback_query(F.data.startswith("special_"))
async def handle_special_giveaways(callback: CallbackQuery):
    """Обработка особых раздач"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    special_type = callback.data.split("_", 1)[1]
    
    try:
        users = await user_service.get_all_users()
        if not users:
            await callback.answer("❌ Нет зарегистрированных пользователей", show_alert=True)
            return
        
        await callback.message.edit_text(f"🎁 Начинаю особую раздачу для {len(users)} игроков...")
        
        from services.card_service import card_service
        success_count = 0
        
        if special_type == "random_card":
            # Случайная карточка каждому игроку
            for user in users:
                try:
                    card = await card_service.get_random_card()
                    if card:
                        await user_service.add_card_to_user(user, str(card.id))
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error giving random card to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Раздача случайных карточек завершена!**\n\n"
                f"🎰 Роздано: случайные карточки\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
            
        elif special_type == "coins_exp":
            # Монеты + опыт
            coins_amount = 100
            exp_amount = 50
            
            for user in users:
                try:
                    user.coins += coins_amount
                    user.experience += exp_amount
                    user.level = user.calculate_level()
                    await user_service.update_user(user)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error giving coins+exp to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Комбо раздача завершена!**\n\n"
                f"🪙 Роздано: {coins_amount} монет\n"
                f"✨ Роздано: {exp_amount} опыта\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
            
        elif special_type == "rare_card":
            # Редкая карточка (Epic или выше)
            for user in users:
                try:
                    import random
                    rand = random.uniform(0, 100)
                    if rand <= 50:  # 50% Epic
                        rarity = "epic"
                    elif rand <= 85:  # 35% Legendary
                        rarity = "legendary"
                    else:  # 15% Artifact
                        rarity = "artifact"
                    
                    card = await card_service.get_random_card_by_rarity(rarity)
                    if card:
                        await user_service.add_card_to_user(user, str(card.id))
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error giving rare card to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Раздача редких карточек завершена!**\n\n"
                f"🔥 Роздано: Epic/Legendary/Artifact карточки\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
            
        elif special_type == "mega":
            # Мега бонус: 3 случайные карточки + 200 монет + 100 опыта
            coins_amount = 200
            exp_amount = 100
            cards_count = 3
            
            for user in users:
                try:
                    # Добавляем монеты и опыт
                    user.coins += coins_amount
                    user.experience += exp_amount
                    user.level = user.calculate_level()
                    await user_service.update_user(user)
                    
                    # Добавляем 3 случайные карточки
                    for _ in range(cards_count):
                        card = await card_service.get_random_card()
                        if card:
                            await user_service.add_card_to_user(user, str(card.id))
                    
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error giving mega bonus to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Мега раздача завершена!**\n\n"
                f"🎴 Роздано: {cards_count} случайные карточки\n"
                f"🪙 Роздано: {coins_amount} монет\n"
                f"✨ Роздано: {exp_amount} опыта\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
        
        else:
            await callback.answer("❌ Неизвестный тип особой раздачи", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 К раздачам", callback_data="admin_gifts")]
        ])
        
        await callback.message.edit_text(result_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error processing special giveaway: {e}")
        await callback.answer("❌ Ошибка при выполнении особой раздачи", show_alert=True)


@router.callback_query(F.data == "admin_analytics")
async def admin_analytics_menu(callback: CallbackQuery):
    """Меню продвинутой аналитики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    analytics_text = (
        "📈 **Продвинутая аналитика**\n\n"
        "Выберите тип аналитики:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="analytics_users"),
            InlineKeyboardButton(text="🎴 Карточки", callback_data="analytics_cards")
        ],
        [
            InlineKeyboardButton(text="📊 Активность", callback_data="analytics_activity"),
            InlineKeyboardButton(text="🏆 Достижения", callback_data="analytics_achievements")
        ],
        [
            InlineKeyboardButton(text="📈 Рост", callback_data="analytics_growth"),
            InlineKeyboardButton(text="💾 Снимок", callback_data="analytics_snapshot")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(analytics_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("analytics_"))
async def admin_analytics_handler(callback: CallbackQuery):
    """Обработчик аналитики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    analytics_type = callback.data.split("_", 1)[1]
    
    try:
        from services.analytics_service import analytics_service
        
        await callback.message.edit_text("⏳ Загружаю аналитику...")
        
        if analytics_type == "users":
            stats = await analytics_service.get_general_stats()
            users_stats = stats["users"]
            economy_stats = stats["economy"]
            
            text = (
                f"👥 **Статистика пользователей**\n\n"
                f"📊 **Общие данные:**\n"
                f"• Всего пользователей: {users_stats['total']}\n"
                f"• Активных за 7 дней: {users_stats['active_7d']} ({users_stats['active_percentage']}%)\n"
                f"• Новых за 7 дней: {users_stats['new_7d']}\n\n"
                f"💰 **Экономика:**\n"
                f"• Общие монеты: {economy_stats['total_coins']:,}\n"
                f"• Общий опыт: {economy_stats['total_experience']:,}\n"
                f"• Среднее монет: {economy_stats['avg_coins']}\n"
                f"• Средний опыт: {economy_stats['avg_experience']}\n\n"
                f"📈 **Распределение по уровням:**\n"
            )
            
            for level in sorted(users_stats['level_distribution'].keys(), reverse=True)[:10]:
                count = users_stats['level_distribution'][level]
                text += f"   Уровень {level}: {count} игроков\n"
            
            # Топ пользователи
            text += "\n🏆 **Топ по карточкам:**\n"
            for i, user in enumerate(stats["top_users"]["by_cards"][:5], 1):
                text += f"   {i}. {user['name']}: {user['value']} карточек\n"
        
        elif analytics_type == "cards":
            card_stats = await analytics_service.get_card_stats()
            
            text = (
                f"🎴 **Статистика карточек**\n\n"
                f"📊 **Общие данные:**\n"
                f"• Всего карточек в базе: {card_stats['total_cards']}\n\n"
                f"🎯 **По редкости:**\n"
            )
            
            for rarity, data in card_stats['by_rarity'].items():
                emoji = {
                    "common": "⚪", "rare": "🔵", "epic": "🟣", 
                    "legendary": "🟡", "artifact": "🔴"
                }.get(rarity, "❓")
                
                text += (
                    f"{emoji} **{rarity.title()}:**\n"
                    f"   • Карточек: {data['count']}\n"
                    f"   • Экземпляров: {data['total_owned']}\n"
                    f"   • Владельцев: {data['total_owners']}\n\n"
                )
            
            text += "🔥 **Самые популярные:**\n"
            for i, card in enumerate(card_stats['most_popular'][:5], 1):
                emoji = {
                    "common": "⚪", "rare": "🔵", "epic": "🟣", 
                    "legendary": "🟡", "artifact": "🔴"
                }.get(card['rarity'], "❓")
                text += f"   {i}. {emoji} {card['name']}: {card['owners']} владельцев\n"
        
        elif analytics_type == "activity":
            activity_stats = await analytics_service.get_activity_stats(7)
            
            text = (
                f"📊 **Статистика активности (7 дней)**\n\n"
                f"🔄 **Удержание пользователей:**\n"
                f"• 7 дней: {activity_stats['retention']['7d']} ({activity_stats['retention']['7d_percentage']}%)\n"
                f"• 30 дней: {activity_stats['retention']['30d']} ({activity_stats['retention']['30d_percentage']}%)\n\n"
                f"📈 **Активность по дням:**\n"
            )
            
            for day in activity_stats['daily_active'][-7:]:
                text += f"   {day['date']}: {day['count']} активных\n"
            
            text += "\n👥 **Регистрации по дням:**\n"
            for day in activity_stats['registrations'][-7:]:
                if day['count'] > 0:
                    text += f"   {day['date']}: {day['count']} новых\n"
        
        elif analytics_type == "achievements":
            achievement_stats = await analytics_service.get_achievement_stats()
            
            text = (
                f"🏆 **Статистика достижений**\n\n"
                f"📊 **Общие данные:**\n"
                f"• Всего достижений: {achievement_stats['total_achievements']}\n"
                f"• Общие очки: {achievement_stats['user_stats']['total_points']}\n"
                f"• Средние очки: {achievement_stats['user_stats']['avg_points']}\n\n"
                f"🎯 **Топ по очкам:**\n"
            )
            
            for i, user in enumerate(achievement_stats['user_stats']['top_achievers'][:5], 1):
                text += f"   {i}. {user['name']}: {user['points']} очков ({user['completed']} достижений)\n"
            
            text += "\n📈 **Популярные достижения:**\n"
            popular_achievements = sorted(
                achievement_stats['achievements'].items(),
                key=lambda x: x[1]['total_earned'],
                reverse=True
            )[:5]
            
            for name, data in popular_achievements:
                text += f"   • {name}: {data['total_earned']} ({data['completion_rate']}%)\n"
        
        elif analytics_type == "growth":
            growth_stats = await analytics_service.get_growth_stats(30)
            
            if growth_stats.get('data_points', 0) < 2:
                text = "📈 **Статистика роста**\n\n❌ Недостаточно исторических данных для анализа роста"
            else:
                text = (
                    f"📈 **Статистика роста (30 дней)**\n\n"
                    f"🔢 **Общий рост:**\n"
                    f"• Пользователи: +{growth_stats['growth']['users']}\n"
                    f"• Монеты: +{growth_stats['growth']['coins']:,}\n"
                    f"• Карточки: +{growth_stats['growth']['cards']:,}\n\n"
                    f"📊 **Средний рост в день:**\n"
                    f"• Пользователи: +{growth_stats['trends']['users_per_day']}\n"
                    f"• Монеты: +{growth_stats['trends']['coins_per_day']:,}\n"
                    f"• Карточки: +{growth_stats['trends']['cards_per_day']:,}\n\n"
                    f"📋 Данных за период: {growth_stats['data_points']} точек"
                )
        
        elif analytics_type == "snapshot":
            await analytics_service.save_daily_snapshot()
            text = (
                "💾 **Снимок статистики сохранен**\n\n"
                "✅ Ежедневный снимок статистики успешно сохранен в базу данных.\n\n"
                "📊 Снимок включает:\n"
                "• Статистику пользователей\n"
                "• Экономические данные\n"
                "• Данные по карточкам\n"
                "• Распределение редкости\n\n"
                f"🕐 Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        
        else:
            text = "❌ Неизвестный тип аналитики"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"analytics_{analytics_type}")],
            [InlineKeyboardButton(text="◀️ К аналитике", callback_data="admin_analytics")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in analytics handler: {e}")
        await callback.answer("❌ Ошибка при загрузке аналитики", show_alert=True)


# Новые обработчики для недостающих функций
@router.callback_query(F.data == "admin_discounts")
async def admin_discounts_menu(callback: CallbackQuery):
    """Меню управления скидками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    discounts_text = (
        "💰 **Управление скидками**\n\n"
        "📊 Здесь вы можете настроить скидки на паки в магазине:\n\n"
        "🎯 **Доступные действия:**\n"
        "• Создать новую скидку\n"
        "• Посмотреть активные скидки\n"
        "• Завершить скидку\n"
        "• Создать флеш-распродажу\n\n"
        "💡 Скидки помогают стимулировать покупки и создают динамику в экономике игры!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Создать скидку", callback_data="create_discount"),
            InlineKeyboardButton(text="📋 Активные скидки", callback_data="active_discounts")
        ],
        [
            InlineKeyboardButton(text="⚡ Флеш-распродажа", callback_data="flash_sale"),
            InlineKeyboardButton(text="📊 Статистика скидок", callback_data="discount_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(discounts_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_notifications")
async def admin_notifications_menu(callback: CallbackQuery):
    """Меню управления уведомлениями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    notifications_text = (
        "🔔 **Управление уведомлениями**\n\n"
        "📨 Здесь вы можете настроить автоматические уведомления:\n\n"
        "🎯 **Типы уведомлений:**\n"
        "• 🆕 Новые карточки\n"
        "• 🎪 Новые ивенты\n"
        "• 💰 Скидки и акции\n"
        "• 🏆 Достижения других игроков\n"
        "• 📢 Системные сообщения\n\n"
        "⚙️ **Настройки:**\n"
        "• Включить/выключить типы уведомлений\n"
        "• Настроить время отправки\n"
        "• Создать персонализированные сообщения"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆕 Уведомить о карточке", callback_data="notify_card"),
            InlineKeyboardButton(text="🎪 О новых ивентах", callback_data="notify_new_events")
        ],
        [
            InlineKeyboardButton(text="💰 О скидках", callback_data="notify_discounts"),
            InlineKeyboardButton(text="🏆 О достижениях", callback_data="notify_achievements")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="notification_settings"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="notification_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(notifications_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_auto_giveaways")
async def admin_auto_giveaways_menu(callback: CallbackQuery):
    """Меню управления авто-раздачами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    auto_giveaways_text = (
        "⏰ **Автоматические раздачи**\n\n"
        "🤖 Здесь настраиваются регулярные раздачи по расписанию:\n\n"
        "🎯 **Типы авто-раздач:**\n"
        "• 🎁 Ежедневные бонусы\n"
        "• 🎴 Еженедельные карточки\n"
        "• 💰 Ежемесячные монеты\n"
        "• 🎪 Сезонные награды\n"
        "• 🏆 Призы за активность\n\n"
        "⚙️ **Настройки:**\n"
        "• Время выдачи\n"
        "• Размер наград\n"
        "• Условия получения\n"
        "• Уведомления пользователей"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 Ежедневные бонусы", callback_data="auto_daily_bonus"),
            InlineKeyboardButton(text="🎴 Еженедельные карточки", callback_data="auto_weekly_cards")
        ],
        [
            InlineKeyboardButton(text="💰 Ежемесячные монеты", callback_data="auto_monthly_coins"),
            InlineKeyboardButton(text="🎪 Сезонные награды", callback_data="auto_seasonal_rewards")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки расписания", callback_data="auto_schedule_settings"),
            InlineKeyboardButton(text="📊 Статистика раздач", callback_data="auto_giveaway_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(auto_giveaways_text, reply_markup=keyboard)
    await callback.answer()


# Заглушки для новых функций (будут реализованы позже)
@router.callback_query(F.data.in_([
    "create_discount", "active_discounts", "flash_sale", "discount_stats",
    "notify_new_cards", "notify_new_events", "notify_discounts", "notify_achievements", 
    "notification_settings", "notification_stats",
    "auto_daily_bonus", "auto_weekly_cards", "auto_monthly_coins", "auto_seasonal_rewards",
    "auto_schedule_settings", "auto_giveaway_stats"
]))
async def admin_new_features_placeholders(callback: CallbackQuery):
    """Заглушки для новых функций"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    feature_names = {
        "create_discount": "Создание скидки",
        "active_discounts": "Просмотр активных скидок",
        "flash_sale": "Флеш-распродажа",
        "discount_stats": "Статистика скидок",
        "notify_new_cards": "Уведомления о новых карточках",
        "notify_new_events": "Уведомления о новых ивентах",
        "notify_discounts": "Уведомления о скидках",
        "notify_achievements": "Уведомления о достижениях",
        "notification_settings": "Настройки уведомлений",
        "notification_stats": "Статистика уведомлений",
        "auto_daily_bonus": "Ежедневные авто-бонусы",
        "auto_weekly_cards": "Еженедельные авто-карточки",
        "auto_monthly_coins": "Ежемесячные авто-монеты",
        "auto_seasonal_rewards": "Сезонные авто-награды",
        "auto_schedule_settings": "Настройки расписания",
        "auto_giveaway_stats": "Статистика авто-раздач"
    }
    
    feature_name = feature_names.get(callback.data, "Эта функция")
    
    await callback.answer(
        f"🚧 {feature_name} находится в разработке!\n\n"
        "Функция будет доступна в ближайших обновлениях.",
        show_alert=True
    )


@router.callback_query(F.data == "edit_card_menu")
async def edit_card_menu(callback: CallbackQuery):
    """Меню редактирования карточек"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        # Получаем первые 10 карточек для редактирования
        cards = await card_service.get_all_cards()
        
        if not cards:
            await callback.message.edit_text(
                "📝 **Редактирование карточек**\n\n❌ Карточки не найдены",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
                ])
            )
            return
        
        text = "📝 **Выберите карточку для редактирования:**\n\n"
        
        keyboard_buttons = []
        for i, card in enumerate(cards[:8]):  # Показываем первые 8
            text += f"{i+1}. {card.get_rarity_emoji()} {card.name}\n"
            button_text = f"{card.get_rarity_emoji()} {card.name[:20]}..."
            keyboard_buttons.append([InlineKeyboardButton(
                text=button_text, 
                callback_data=f"edit_card:{card.name}"
            )])
        
        if len(cards) > 8:
            text += f"\n... и еще {len(cards) - 8} карточек"
            keyboard_buttons.append([InlineKeyboardButton(
                text="📋 Показать все", 
                callback_data="edit_card_all"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in edit card menu: {e}")
        await callback.answer("❌ Ошибка при загрузке карточек", show_alert=True)


@router.callback_query(F.data == "delete_card_menu")
async def delete_card_menu(callback: CallbackQuery):
    """Меню удаления карточек"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        cards = await card_service.get_all_cards()
        
        if not cards:
            await callback.message.edit_text(
                "🗑 **Удаление карточек**\n\n❌ Карточки не найдены",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
                ])
            )
            return
        
        text = "🗑 **Выберите карточку для удаления:**\n\n⚠️ **ВНИМАНИЕ!** Удаление карточки необратимо!\n\n"
        
        keyboard_buttons = []
        for i, card in enumerate(cards[:8]):  # Показываем первые 8
            text += f"{i+1}. {card.get_rarity_emoji()} {card.name} (владельцев: {card.unique_owners})\n"
            button_text = f"🗑 {card.name[:20]}..."
            keyboard_buttons.append([InlineKeyboardButton(
                text=button_text, 
                callback_data=f"delete_card:{card.name}"
            )])
        
        if len(cards) > 8:
            text += f"\n... и еще {len(cards) - 8} карточек"
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in delete card menu: {e}")
        await callback.answer("❌ Ошибка при загрузке карточек", show_alert=True)


@router.callback_query(F.data.startswith("delete_card:"))
async def delete_card_confirm(callback: CallbackQuery):
    """Подтверждение удаления карточки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    card_name = callback.data.split(":", 1)[1]
    card = await card_service.get_card_by_name(card_name)
    
    if not card:
        await callback.answer("❌ Карточка не найдена", show_alert=True)
        return
    
    confirm_text = (
        f"🗑 **Подтверждение удаления**\n\n"
        f"Карточка: {card.get_rarity_emoji()} **{card.name}**\n"
        f"Описание: {card.description}\n"
        f"Владельцев: {card.unique_owners}\n"
        f"Всего экземпляров: {card.total_owned}\n\n"
        f"⚠️ **ЭТО ДЕЙСТВИЕ НЕОБРАТИМО!**\n"
        f"Карточка будет удалена у всех игроков!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ УДАЛИТЬ", callback_data=f"confirm_delete:{card_name}"),
            InlineKeyboardButton(text="🚫 Отмена", callback_data="delete_card_menu")
        ]
    ])
    
    await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_card(callback: CallbackQuery):
    """Окончательное удаление карточки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    card_name = callback.data.split(":", 1)[1]
    
    success = await card_service.delete_card(card_name)
    
    if success:
        await callback.message.edit_text(
            f"✅ **Карточка удалена!**\n\n"
            f"🗑 Карточка '{card_name}' была успешно удалена",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
            ])
        )
        await callback.answer("✅ Карточка удалена!")
    else:
        await callback.answer("❌ Ошибка при удалении карточки", show_alert=True)


@router.callback_query(F.data == "view_suggestions")
async def view_suggestions(callback: CallbackQuery):
    """Просмотр предложений карточек"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    # Пока заглушка - в будущем здесь будет список предложений из БД
    suggestions_text = (
        "🎨 **Предложения карточек**\n\n"
        "📋 Здесь будут отображаться предложения от пользователей\n\n"
        "🔧 **Функции:**\n"
        "• Просмотр предложений\n"
        "• Принятие/отклонение\n"
        "• Автоматическая награда игрокам\n\n"
        "⚠️ Пока в разработке"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="view_suggestions")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cards")]
    ])
    
    await safe_edit_message(callback, suggestions_text, keyboard)


# Заглушки для новых функций
@router.callback_query(F.data.in_(["edit_card_all", "search_cards"]))
async def admin_card_placeholders(callback: CallbackQuery):
    """Заглушки для функций карточек"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    placeholders = {
        "edit_card_all": "📝 Полный список для редактирования в разработке",
        "search_cards": "🔍 Поиск карточек в разработке"
    }
    
    message_text = placeholders.get(callback.data, "Функция в разработке")
    await callback.answer(message_text, show_alert=True)


@router.message(StateFilter(AdminStates.waiting_for_gift_coins))
async def process_gift_coins(message: Message, state: FSMContext):
    """Обработка раздачи монет"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        coins_amount = int(message.text.strip())
        if coins_amount <= 0:
            await message.answer("❌ Количество монет должно быть положительным числом")
            return
        
        await state.clear()
        
        users = await user_service.get_all_users()
        success_count = 0
        
        await message.answer(f"🪙 Начинаю раздачу {coins_amount} монет {len(users)} игрокам...")
        
        for user in users:
            try:
                user.coins += coins_amount
                await user_service.update_user(user)
                success_count += 1
            except Exception as e:
                logger.error(f"Error giving coins to user {user.telegram_id}: {e}")
        
        result_text = (
            f"✅ **Раздача монет завершена!**\n\n"
            f"🪙 Роздано: {coins_amount} монет\n"
            f"👥 Получили: {success_count} игроков\n"
            f"📊 Всего игроков: {len(users)}"
        )
        
        await message.answer(result_text)
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        logger.error(f"Error processing gift coins: {e}")
        await message.answer("❌ Ошибка при раздаче монет")


@router.message(StateFilter(AdminStates.waiting_for_gift_exp))
async def process_gift_exp(message: Message, state: FSMContext):
    """Обработка раздачи опыта"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        exp_amount = int(message.text.strip())
        if exp_amount <= 0:
            await message.answer("❌ Количество опыта должно быть положительным числом")
            return
        
        await state.clear()
        
        users = await user_service.get_all_users()
        success_count = 0
        
        await message.answer(f"✨ Начинаю раздачу {exp_amount} опыта {len(users)} игрокам...")
        
        for user in users:
            try:
                old_level = user.level
                user.experience += exp_amount
                user.level = user.calculate_level()
                await user_service.update_user(user)
                success_count += 1
            except Exception as e:
                logger.error(f"Error giving exp to user {user.telegram_id}: {e}")
        
        result_text = (
            f"✅ **Раздача опыта завершена!**\n\n"
            f"✨ Роздано: {exp_amount} опыта\n"
            f"👥 Получили: {success_count} игроков\n"
            f"📊 Всего игроков: {len(users)}"
        )
        
        await message.answer(result_text)
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        logger.error(f"Error processing gift exp: {e}")
        await message.answer("❌ Ошибка при раздаче опыта")


# Обработчики особых раздач
@router.callback_query(F.data.startswith("special_"))
async def handle_special_giveaways(callback: CallbackQuery):
    """Обработка особых раздач"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    special_type = callback.data.split("_", 1)[1]
    
    try:
        users = await user_service.get_all_users()
        if not users:
            await callback.answer("❌ Нет зарегистрированных пользователей", show_alert=True)
            return
        
        await callback.message.edit_text(f"🎁 Начинаю особую раздачу для {len(users)} игроков...")
        
        from services.card_service import card_service
        success_count = 0
        
        if special_type == "random_card":
            # Случайная карточка каждому игроку
            for user in users:
                try:
                    card = await card_service.get_random_card()
                    if card:
                        await user_service.add_card_to_user(user, str(card.id))
                        success_count += 1
                        
                        # Отправляем уведомление пользователю
                        try:
                            notification_text = (
                                f"🎁 **Подарок от администрации!**\n\n"
                                f"🎴 Вы получили случайную карточку:\n"
                                f"{card.get_rarity_emoji()} **{card.name}**\n"
                                f"📝 {card.description}\n\n"
                                f"💝 Спасибо за участие в игре!"
                            )
                            await callback.message.bot.send_message(user.telegram_id, notification_text, parse_mode="Markdown")
                        except Exception as notify_error:
                            logger.error(f"Failed to notify user {user.telegram_id} about random gift: {notify_error}")
                            
                except Exception as e:
                    logger.error(f"Error giving random card to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Раздача случайных карточек завершена!**\n\n"
                f"🎰 Роздано: случайные карточки\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
            
        elif special_type == "coins_exp":
            # Монеты + опыт
            coins_amount = 100
            exp_amount = 50
            
            for user in users:
                try:
                    user.coins += coins_amount
                    user.experience += exp_amount
                    user.level = user.calculate_level()
                    await user_service.update_user(user)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error giving coins+exp to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Комбо раздача завершена!**\n\n"
                f"🪙 Роздано: {coins_amount} монет\n"
                f"✨ Роздано: {exp_amount} опыта\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
            
        elif special_type == "rare_card":
            # Редкая карточка (Epic или выше)
            for user in users:
                try:
                    import random
                    rand = random.uniform(0, 100)
                    if rand <= 50:  # 50% Epic
                        rarity = "epic"
                    elif rand <= 85:  # 35% Legendary
                        rarity = "legendary"
                    else:  # 15% Artifact
                        rarity = "artifact"
                    
                    card = await card_service.get_random_card_by_rarity(rarity)
                    if card:
                        await user_service.add_card_to_user(user, str(card.id))
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error giving rare card to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Раздача редких карточек завершена!**\n\n"
                f"🔥 Роздано: Epic/Legendary/Artifact карточки\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
            
        elif special_type == "mega":
            # Мега бонус: 3 случайные карточки + 200 монет + 100 опыта
            coins_amount = 200
            exp_amount = 100
            cards_count = 3
            
            for user in users:
                try:
                    # Добавляем монеты и опыт
                    user.coins += coins_amount
                    user.experience += exp_amount
                    user.level = user.calculate_level()
                    await user_service.update_user(user)
                    
                    # Добавляем 3 случайные карточки
                    for _ in range(cards_count):
                        card = await card_service.get_random_card()
                        if card:
                            await user_service.add_card_to_user(user, str(card.id))
                    
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error giving mega bonus to user {user.telegram_id}: {e}")
            
            result_text = (
                f"✅ **Мега раздача завершена!**\n\n"
                f"🎴 Роздано: {cards_count} случайные карточки\n"
                f"🪙 Роздано: {coins_amount} монет\n"
                f"✨ Роздано: {exp_amount} опыта\n"
                f"👥 Получили: {success_count} игроков\n"
                f"📊 Всего игроков: {len(users)}"
            )
        
        else:
            await callback.answer("❌ Неизвестный тип особой раздачи", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 К раздачам", callback_data="admin_gifts")]
        ])
        
        await callback.message.edit_text(result_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error processing special giveaway: {e}")
        await callback.answer("❌ Ошибка при выполнении особой раздачи", show_alert=True)


@router.callback_query(F.data == "admin_analytics")
async def admin_analytics_menu(callback: CallbackQuery):
    """Меню продвинутой аналитики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    analytics_text = (
        "📈 **Продвинутая аналитика**\n\n"
        "Выберите тип аналитики:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="analytics_users"),
            InlineKeyboardButton(text="🎴 Карточки", callback_data="analytics_cards")
        ],
        [
            InlineKeyboardButton(text="📊 Активность", callback_data="analytics_activity"),
            InlineKeyboardButton(text="🏆 Достижения", callback_data="analytics_achievements")
        ],
        [
            InlineKeyboardButton(text="📈 Рост", callback_data="analytics_growth"),
            InlineKeyboardButton(text="💾 Снимок", callback_data="analytics_snapshot")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(analytics_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("analytics_"))
async def admin_analytics_handler(callback: CallbackQuery):
    """Обработчик аналитики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    analytics_type = callback.data.split("_", 1)[1]
    
    try:
        from services.analytics_service import analytics_service
        
        await callback.message.edit_text("⏳ Загружаю аналитику...")
        
        if analytics_type == "users":
            stats = await analytics_service.get_general_stats()
            users_stats = stats["users"]
            economy_stats = stats["economy"]
            
            text = (
                f"👥 **Статистика пользователей**\n\n"
                f"📊 **Общие данные:**\n"
                f"• Всего пользователей: {users_stats['total']}\n"
                f"• Активных за 7 дней: {users_stats['active_7d']} ({users_stats['active_percentage']}%)\n"
                f"• Новых за 7 дней: {users_stats['new_7d']}\n\n"
                f"💰 **Экономика:**\n"
                f"• Общие монеты: {economy_stats['total_coins']:,}\n"
                f"• Общий опыт: {economy_stats['total_experience']:,}\n"
                f"• Среднее монет: {economy_stats['avg_coins']}\n"
                f"• Средний опыт: {economy_stats['avg_experience']}\n\n"
                f"📈 **Распределение по уровням:**\n"
            )
            
            for level in sorted(users_stats['level_distribution'].keys(), reverse=True)[:10]:
                count = users_stats['level_distribution'][level]
                text += f"   Уровень {level}: {count} игроков\n"
            
            # Топ пользователи
            text += "\n🏆 **Топ по карточкам:**\n"
            for i, user in enumerate(stats["top_users"]["by_cards"][:5], 1):
                text += f"   {i}. {user['name']}: {user['value']} карточек\n"
        
        elif analytics_type == "cards":
            card_stats = await analytics_service.get_card_stats()
            
            text = (
                f"🎴 **Статистика карточек**\n\n"
                f"📊 **Общие данные:**\n"
                f"• Всего карточек в базе: {card_stats['total_cards']}\n\n"
                f"🎯 **По редкости:**\n"
            )
            
            for rarity, data in card_stats['by_rarity'].items():
                emoji = {
                    "common": "⚪", "rare": "🔵", "epic": "🟣", 
                    "legendary": "🟡", "artifact": "🔴"
                }.get(rarity, "❓")
                
                text += (
                    f"{emoji} **{rarity.title()}:**\n"
                    f"   • Карточек: {data['count']}\n"
                    f"   • Экземпляров: {data['total_owned']}\n"
                    f"   • Владельцев: {data['total_owners']}\n\n"
                )
            
            text += "🔥 **Самые популярные:**\n"
            for i, card in enumerate(card_stats['most_popular'][:5], 1):
                emoji = {
                    "common": "⚪", "rare": "🔵", "epic": "🟣", 
                    "legendary": "🟡", "artifact": "🔴"
                }.get(card['rarity'], "❓")
                text += f"   {i}. {emoji} {card['name']}: {card['owners']} владельцев\n"
        
        elif analytics_type == "activity":
            activity_stats = await analytics_service.get_activity_stats(7)
            
            text = (
                f"📊 **Статистика активности (7 дней)**\n\n"
                f"🔄 **Удержание пользователей:**\n"
                f"• 7 дней: {activity_stats['retention']['7d']} ({activity_stats['retention']['7d_percentage']}%)\n"
                f"• 30 дней: {activity_stats['retention']['30d']} ({activity_stats['retention']['30d_percentage']}%)\n\n"
                f"📈 **Активность по дням:**\n"
            )
            
            for day in activity_stats['daily_active'][-7:]:
                text += f"   {day['date']}: {day['count']} активных\n"
            
            text += "\n👥 **Регистрации по дням:**\n"
            for day in activity_stats['registrations'][-7:]:
                if day['count'] > 0:
                    text += f"   {day['date']}: {day['count']} новых\n"
        
        elif analytics_type == "achievements":
            achievement_stats = await analytics_service.get_achievement_stats()
            
            text = (
                f"🏆 **Статистика достижений**\n\n"
                f"📊 **Общие данные:**\n"
                f"• Всего достижений: {achievement_stats['total_achievements']}\n"
                f"• Общие очки: {achievement_stats['user_stats']['total_points']}\n"
                f"• Средние очки: {achievement_stats['user_stats']['avg_points']}\n\n"
                f"🎯 **Топ по очкам:**\n"
            )
            
            for i, user in enumerate(achievement_stats['user_stats']['top_achievers'][:5], 1):
                text += f"   {i}. {user['name']}: {user['points']} очков ({user['completed']} достижений)\n"
            
            text += "\n📈 **Популярные достижения:**\n"
            popular_achievements = sorted(
                achievement_stats['achievements'].items(),
                key=lambda x: x[1]['total_earned'],
                reverse=True
            )[:5]
            
            for name, data in popular_achievements:
                text += f"   • {name}: {data['total_earned']} ({data['completion_rate']}%)\n"
        
        elif analytics_type == "growth":
            growth_stats = await analytics_service.get_growth_stats(30)
            
            if growth_stats.get('data_points', 0) < 2:
                text = "📈 **Статистика роста**\n\n❌ Недостаточно исторических данных для анализа роста"
            else:
                text = (
                    f"📈 **Статистика роста (30 дней)**\n\n"
                    f"🔢 **Общий рост:**\n"
                    f"• Пользователи: +{growth_stats['growth']['users']}\n"
                    f"• Монеты: +{growth_stats['growth']['coins']:,}\n"
                    f"• Карточки: +{growth_stats['growth']['cards']:,}\n\n"
                    f"📊 **Средний рост в день:**\n"
                    f"• Пользователи: +{growth_stats['trends']['users_per_day']}\n"
                    f"• Монеты: +{growth_stats['trends']['coins_per_day']:,}\n"
                    f"• Карточки: +{growth_stats['trends']['cards_per_day']:,}\n\n"
                    f"📋 Данных за период: {growth_stats['data_points']} точек"
                )
        
        elif analytics_type == "snapshot":
            await analytics_service.save_daily_snapshot()
            text = (
                "💾 **Снимок статистики сохранен**\n\n"
                "✅ Ежедневный снимок статистики успешно сохранен в базу данных.\n\n"
                "📊 Снимок включает:\n"
                "• Статистику пользователей\n"
                "• Экономические данные\n"
                "• Данные по карточкам\n"
                "• Распределение редкости\n\n"
                f"🕐 Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        
        else:
            text = "❌ Неизвестный тип аналитики"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"analytics_{analytics_type}")],
            [InlineKeyboardButton(text="◀️ К аналитике", callback_data="admin_analytics")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in analytics handler: {e}")
        await callback.answer("❌ Ошибка при загрузке аналитики", show_alert=True)


# Новые обработчики для недостающих функций
@router.callback_query(F.data == "admin_discounts")
async def admin_discounts_menu(callback: CallbackQuery):
    """Меню управления скидками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    discounts_text = (
        "💰 **Управление скидками**\n\n"
        "📊 Здесь вы можете настроить скидки на паки в магазине:\n\n"
        "🎯 **Доступные действия:**\n"
        "• Создать новую скидку\n"
        "• Посмотреть активные скидки\n"
        "• Завершить скидку\n"
        "• Создать флеш-распродажу\n\n"
        "💡 Скидки помогают стимулировать покупки и создают динамику в экономике игры!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Создать скидку", callback_data="create_discount"),
            InlineKeyboardButton(text="📋 Активные скидки", callback_data="active_discounts")
        ],
        [
            InlineKeyboardButton(text="⚡ Флеш-распродажа", callback_data="flash_sale"),
            InlineKeyboardButton(text="📊 Статистика скидок", callback_data="discount_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(discounts_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_notifications")
async def admin_notifications_menu(callback: CallbackQuery):
    """Меню управления уведомлениями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    notifications_text = (
        "🔔 **Управление уведомлениями**\n\n"
        "📨 Здесь вы можете настроить автоматические уведомления:\n\n"
        "🎯 **Типы уведомлений:**\n"
        "• 🆕 Новые карточки\n"
        "• 🎪 Новые ивенты\n"
        "• 💰 Скидки и акции\n"
        "• 🏆 Достижения других игроков\n"
        "• 📢 Системные сообщения\n\n"
        "⚙️ **Настройки:**\n"
        "• Включить/выключить типы уведомлений\n"
        "• Настроить время отправки\n"
        "• Создать персонализированные сообщения"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆕 Уведомить о карточке", callback_data="notify_card"),
            InlineKeyboardButton(text="🎪 О новых ивентах", callback_data="notify_new_events")
        ],
        [
            InlineKeyboardButton(text="💰 О скидках", callback_data="notify_discounts"),
            InlineKeyboardButton(text="🏆 О достижениях", callback_data="notify_achievements")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="notification_settings"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="notification_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(notifications_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_auto_giveaways")
async def admin_auto_giveaways_menu(callback: CallbackQuery):
    """Меню управления авто-раздачами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    auto_giveaways_text = (
        "⏰ **Автоматические раздачи**\n\n"
        "🤖 Здесь настраиваются регулярные раздачи по расписанию:\n\n"
        "🎯 **Типы авто-раздач:**\n"
        "• 🎁 Ежедневные бонусы\n"
        "• 🎴 Еженедельные карточки\n"
        "• 💰 Ежемесячные монеты\n"
        "• 🎪 Сезонные награды\n"
        "• 🏆 Призы за активность\n\n"
        "⚙️ **Настройки:**\n"
        "• Время выдачи\n"
        "• Размер наград\n"
        "• Условия получения\n"
        "• Уведомления пользователей"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 Ежедневные бонусы", callback_data="auto_daily_bonus"),
            InlineKeyboardButton(text="🎴 Еженедельные карточки", callback_data="auto_weekly_cards")
        ],
        [
            InlineKeyboardButton(text="💰 Ежемесячные монеты", callback_data="auto_monthly_coins"),
            InlineKeyboardButton(text="🎪 Сезонные награды", callback_data="auto_seasonal_rewards")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки расписания", callback_data="auto_schedule_settings"),
            InlineKeyboardButton(text="📊 Статистика раздач", callback_data="auto_giveaway_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(auto_giveaways_text, reply_markup=keyboard)
    await callback.answer()


# Заглушки для новых функций (будут реализованы позже)
@router.callback_query(F.data.in_([
    "create_discount", "active_discounts", "flash_sale", "discount_stats",
    "notify_new_cards", "notify_new_events", "notify_discounts", "notify_achievements", 
    "notification_settings", "notification_stats",
    "auto_daily_bonus", "auto_weekly_cards", "auto_monthly_coins", "auto_seasonal_rewards",
    "auto_schedule_settings", "auto_giveaway_stats"
]))
async def admin_new_features_placeholders(callback: CallbackQuery):
    """Заглушки для новых функций"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    feature_names = {
        "create_discount": "Создание скидки",
        "active_discounts": "Просмотр активных скидок",
        "flash_sale": "Флеш-распродажа",
        "discount_stats": "Статистика скидок",
        "notify_new_cards": "Уведомления о новых карточках",
        "notify_new_events": "Уведомления о новых ивентах",
        "notify_discounts": "Уведомления о скидках",
        "notify_achievements": "Уведомления о достижениях",
        "notification_settings": "Настройки уведомлений",
        "notification_stats": "Статистика уведомлений",
        "auto_daily_bonus": "Ежедневные авто-бонусы",
        "auto_weekly_cards": "Еженедельные авто-карточки",
        "auto_monthly_coins": "Ежемесячные авто-монеты",
        "auto_seasonal_rewards": "Сезонные авто-награды",
        "auto_schedule_settings": "Настройки расписания",
        "auto_giveaway_stats": "Статистика авто-раздач"
    }
    
    feature_name = feature_names.get(callback.data, "Эта функция")
    
    await callback.answer(
        f"🚧 {feature_name} находится в разработке!\n\n"
        "Функция будет доступна в ближайших обновлениях.",
        show_alert=True
    )
