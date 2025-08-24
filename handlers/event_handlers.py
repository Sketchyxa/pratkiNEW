from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from loguru import logger

from services.user_service import user_service
from services.event_service import event_service
from config import settings

router = Router()


class EventStates(StatesGroup):
    waiting_for_event_name = State()
    waiting_for_event_description = State()
    waiting_for_event_duration = State()
    waiting_for_event_target = State()
    waiting_for_event_rewards = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in settings.admin_ids


@router.callback_query(F.data == "events")
async def events_menu(callback: CallbackQuery):
    """Меню ивентов для пользователей"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        try:
            active_events = await event_service.get_active_events()
        except Exception as e:
            logger.error(f"Error getting active events: {e}")
            active_events = []
        
        events_text = "🎪 **Активные ивенты**\n\n"
        
        if not active_events:
            events_text += "📭 Сейчас нет активных ивентов\n\nСледите за обновлениями!"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])
        else:
            for event in active_events:
                # Получаем прогресс пользователя
                progress = await event_service.get_user_event_progress(user.telegram_id, str(event.id))
                
                status_emoji = "🏃" if progress and not progress.is_completed else "✅" if progress and progress.is_completed else "🆕"
                
                time_left = event.end_date - datetime.utcnow()
                time_text = f"{time_left.days}д {time_left.seconds // 3600}ч" if time_left.total_seconds() > 0 else "Завершен"
                
                events_text += f"{status_emoji} {event.icon} **{event.name}**\n"
                events_text += f"📅 До окончания: {time_text}\n"
                
                if progress:
                    events_text += f"📊 Прогресс: {progress.current_progress}/{progress.target_progress}\n"
                    if progress.is_completed and not progress.rewards_claimed:
                        events_text += "🎁 **Награда готова к получению!**\n"
                
                events_text += "\n"
            
            # Создаем кнопки для ивентов
            keyboard_buttons = []
            for event in active_events[:10]:  # Ограничиваем до 10 ивентов
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"{event.icon} {event.name}", 
                        callback_data=f"event_detail_{event.id}"
                    )
                ])
            
            keyboard_buttons.extend([
                [InlineKeyboardButton(text="◀️ Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(events_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in events menu: {e}")
        await callback.answer("❌ Ошибка при загрузке ивентов", show_alert=True)


@router.callback_query(F.data.startswith("event_detail_"))
async def event_detail(callback: CallbackQuery):
    """Детальная информация об ивенте"""
    try:
        event_id = callback.data.split("_", 2)[2]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        event = await event_service.get_event_by_id(event_id)
        
        if not user or not event:
            await callback.answer("❌ Ивент не найден", show_alert=True)
            return
        
        # Получаем прогресс пользователя
        progress = await event_service.get_user_event_progress(user.telegram_id, event_id)
        
        # Проверяем и обновляем прогресс
        await event_service.check_user_event_progress(user)
        progress = await event_service.get_user_event_progress(user.telegram_id, event_id)
        
        time_left = event.end_date - datetime.utcnow()
        time_text = f"{time_left.days}д {time_left.seconds // 3600}ч" if time_left.total_seconds() > 0 else "Завершен"
        
        event_text = (
            f"{event.icon} **{event.name}**\n\n"
            f"📝 {event.description}\n\n"
            f"📅 **Время до окончания:** {time_text}\n"
            f"🎯 **Цель:** {event.target_value} {event.target_type.replace('_', ' ')}\n"
        )
        
        # Прогресс пользователя
        if progress:
            progress_percent = min(100, (progress.current_progress / progress.target_progress) * 100)
            progress_bar = "█" * int(progress_percent // 10) + "░" * (10 - int(progress_percent // 10))
            
            event_text += f"\n📊 **Ваш прогресс:**\n"
            event_text += f"{progress_bar} {progress.current_progress}/{progress.target_progress} ({progress_percent:.1f}%)\n"
            
            if progress.is_completed:
                if progress.rewards_claimed:
                    event_text += "\n✅ **Ивент завершен! Награда получена**"
                else:
                    event_text += "\n🎉 **Ивент завершен! Можете забрать награду**"
        else:
            event_text += "\n🆕 **Вы еще не участвуете в этом ивенте**"
        
        # Награды
        if event.rewards.coins > 0 or event.rewards.experience > 0 or event.rewards.cards:
            event_text += "\n\n🎁 **Награды:**\n"
            if event.rewards.coins > 0:
                event_text += f"🪙 {event.rewards.coins} монет\n"
            if event.rewards.experience > 0:
                event_text += f"✨ {event.rewards.experience} опыта\n"
            if event.rewards.cards:
                event_text += f"🎴 {len(event.rewards.cards)} специальных карточек\n"
        
        # Статистика ивента
        event_text += f"\n👥 **Участников:** {event.total_participants}\n"
        event_text += f"🏆 **Завершили:** {event.total_completed}"
        
        # Кнопки
        keyboard_buttons = []
        
        if progress and progress.is_completed and not progress.rewards_claimed:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🎁 Забрать награду", callback_data=f"claim_reward_{event_id}")
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="🏆 Топ игроков", callback_data=f"event_leaderboard_{event_id}")],
            [InlineKeyboardButton(text="◀️ К ивентам", callback_data="events")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(event_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in event detail: {e}")
        await callback.answer("❌ Ошибка при загрузке деталей ивента", show_alert=True)


@router.callback_query(F.data.startswith("claim_reward_"))
async def claim_event_reward(callback: CallbackQuery):
    """Получение награды за ивент"""
    try:
        event_id = callback.data.split("_", 2)[2]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        success = await event_service.claim_event_rewards(user, event_id)
        
        if success:
            await callback.answer("🎉 Награда получена!", show_alert=True)
            # Возвращаемся к деталям ивента
            await event_detail(callback)
        else:
            await callback.answer("❌ Не удалось получить награду", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error claiming event reward: {e}")
        await callback.answer("❌ Ошибка при получении награды", show_alert=True)


@router.callback_query(F.data.startswith("event_leaderboard_"))
async def event_leaderboard(callback: CallbackQuery):
    """Топ игроков по ивенту"""
    try:
        event_id = callback.data.split("_", 2)[2]
        event = await event_service.get_event_by_id(event_id)
        
        if not event:
            await callback.answer("❌ Ивент не найден", show_alert=True)
            return
        
        leaderboard = await event_service.get_event_leaderboard(event_id, 10)
        
        leaderboard_text = f"🏆 **Топ игроков - {event.name}**\n\n"
        
        if not leaderboard:
            leaderboard_text += "📭 Пока нет участников"
        else:
            for entry in leaderboard:
                status = "✅" if entry["is_completed"] else "🏃"
                medal = "🥇" if entry["position"] == 1 else "🥈" if entry["position"] == 2 else "🥉" if entry["position"] == 3 else f"{entry['position']}."
                
                leaderboard_text += f"{medal} {status} **{entry['user_name']}**\n"
                leaderboard_text += f"    📊 Прогресс: {entry['progress']}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К ивенту", callback_data=f"event_detail_{event_id}")]
        ])
        
        await callback.message.edit_text(leaderboard_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in event leaderboard: {e}")
        await callback.answer("❌ Ошибка при загрузке топа", show_alert=True)


# Админские функции для управления ивентами
@router.callback_query(F.data == "admin_events")
async def admin_events_menu(callback: CallbackQuery):
    """Админское меню ивентов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        all_events = await event_service.get_all_events()
        
        events_text = "🎪 **Управление ивентами**\n\n"
        events_text += f"📊 Всего ивентов: {len(all_events)}\n"
        
        active_count = len([e for e in all_events if e.is_active and e.start_date <= datetime.utcnow() <= e.end_date])
        events_text += f"🟢 Активных: {active_count}\n\n"
        
        # Показываем последние ивенты
        if all_events:
            events_text += "📋 **Последние ивенты:**\n"
            for event in all_events[:5]:
                status = "🟢" if event.is_active and event.start_date <= datetime.utcnow() <= event.end_date else "🔴"
                events_text += f"{status} {event.icon} {event.name}\n"
                events_text += f"    👥 {event.total_participants} участников, 🏆 {event.total_completed} завершили\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать ивент", callback_data="create_event"),
                InlineKeyboardButton(text="📋 Все ивенты", callback_data="admin_all_events")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_events_stats"),
                InlineKeyboardButton(text="🎯 Шаблоны", callback_data="event_templates")
            ],
            [InlineKeyboardButton(text="◀️ Админка", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(events_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin events menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню ивентов", show_alert=True)


# Функция для проверки ивентов после игровых действий
async def check_and_notify_events(user, bot=None):
    """Проверяет прогресс в ивентах и уведомляет о завершении"""
    try:
        completed_events = await event_service.check_user_event_progress(user)
        
        if completed_events and bot:
            for event in completed_events:
                notification_text = (
                    f"🎉 **ИВЕНТ ЗАВЕРШЕН!**\n\n"
                    f"{event.icon} **{event.name}**\n"
                    f"📝 {event.description}\n\n"
                    f"🎁 **Награды готовы к получению!**\n"
                )
                
                if event.rewards.coins > 0:
                    notification_text += f"🪙 +{event.rewards.coins} монет\n"
                if event.rewards.experience > 0:
                    notification_text += f"✨ +{event.rewards.experience} опыта\n"
                if event.rewards.cards:
                    notification_text += f"🎴 +{len(event.rewards.cards)} карточек\n"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎁 Забрать награду", callback_data=f"claim_reward_{event.id}")],
                    [InlineKeyboardButton(text="🎪 Все ивенты", callback_data="events")]
                ])
                
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_text,
                    reply_markup=keyboard
                )
        
        return completed_events
        
    except Exception as e:
        logger.error(f"Error checking events: {e}")
        return []


@router.callback_query(F.data == "create_event")
async def create_event_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания ивента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ **Создание нового ивента**\n\n"
        "📝 Введите название ивента:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_events")]
        ])
    )
    
    await state.set_state(EventStates.waiting_for_event_name)
    await callback.answer()


@router.message(EventStates.waiting_for_event_name)
async def create_event_name(message: Message, state: FSMContext):
    """Получение названия ивента"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст")
        return
    
    await state.update_data(name=message.text.strip())
    
    await message.answer(
        f"✅ Название: **{message.text.strip()}**\n\n"
        "📝 Теперь введите описание ивента:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_events")]
        ])
    )
    
    await state.set_state(EventStates.waiting_for_event_description)


@router.message(EventStates.waiting_for_event_description)
async def create_event_description(message: Message, state: FSMContext):
    """Получение описания ивента"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Пожалуйста, введите текст")
        return
    
    await state.update_data(description=message.text.strip())
    
    await message.answer(
        f"✅ Описание сохранено\n\n"
        "⏰ Введите длительность ивента в днях (например: 7):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_events")]
        ])
    )
    
    await state.set_state(EventStates.waiting_for_event_duration)


@router.message(EventStates.waiting_for_event_duration)
async def create_event_duration(message: Message, state: FSMContext):
    """Получение длительности ивента"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Пожалуйста, введите число")
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError("Количество дней должно быть положительным")
        
        await state.update_data(duration_days=days)
        
        # Показываем типы целей
        await message.answer(
            f"✅ Длительность: {days} дней\n\n"
            "🎯 Выберите тип цели для ивента:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎴 Собрать карточки", callback_data="event_target_total_cards"),
                    InlineKeyboardButton(text="🔥 Карточки редкости", callback_data="event_target_card_rarity")
                ],
                [
                    InlineKeyboardButton(text="🎯 Определенные карточки", callback_data="event_target_specific_cards"),
                    InlineKeyboardButton(text="⭐ Достичь уровня", callback_data="event_target_level")
                ],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_events")]
            ])
        )
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число дней")


@router.callback_query(F.data.startswith("event_target_"))
async def create_event_target(callback: CallbackQuery, state: FSMContext):
    """Выбор типа цели ивента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    target_type = callback.data.split("_", 2)[2]
    await state.update_data(target_type=target_type)
    
    target_descriptions = {
        "total_cards": "Введите количество карточек, которое нужно собрать:",
        "card_rarity": "Введите количество и редкость через пробел (например: 10 rare):",
        "specific_cards": "Введите ID карточек через запятую:",
        "level": "Введите уровень, которого нужно достичь:"
    }
    
    description = target_descriptions.get(target_type, "Введите значение цели:")
    
    await callback.message.edit_text(
        f"🎯 **Тип цели:** {target_type.replace('_', ' ').title()}\n\n"
        f"📝 {description}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_events")]
        ])
    )
    
    await state.set_state(EventStates.waiting_for_event_target)
    await callback.answer()


@router.message(EventStates.waiting_for_event_target)
async def create_event_target_value(message: Message, state: FSMContext):
    """Получение значения цели"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Пожалуйста, введите значение")
        return
    
    data = await state.get_data()
    target_type = data.get("target_type")
    
    try:
        target_value = None
        target_data = {}
        
        if target_type == "total_cards":
            target_value = int(message.text.strip())
        elif target_type == "card_rarity":
            parts = message.text.strip().split()
            if len(parts) != 2:
                raise ValueError("Введите количество и редкость через пробел")
            target_value = int(parts[0])
            target_data["rarity"] = parts[1].lower()
        elif target_type == "specific_cards":
            card_ids = [id.strip() for id in message.text.strip().split(",")]
            target_value = len(card_ids)
            target_data["card_ids"] = card_ids
        elif target_type == "level":
            target_value = int(message.text.strip())
        
        await state.update_data(target_value=target_value, target_data=target_data)
        
        await message.answer(
            f"✅ Цель настроена\n\n"
            "🎁 Теперь настройте награды.\n"
            "Введите награды в формате: монеты опыт (например: 100 50):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить награды", callback_data="skip_rewards")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_events")]
            ])
        )
        
        await state.set_state(EventStates.waiting_for_event_rewards)
        
    except ValueError as e:
        await message.answer(f"❌ Ошибка в формате: {str(e)}")


@router.message(EventStates.waiting_for_event_rewards)
async def create_event_rewards(message: Message, state: FSMContext):
    """Получение наград за ивент"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Пожалуйста, введите награды")
        return
    
    try:
        parts = message.text.strip().split()
        coins = int(parts[0]) if len(parts) > 0 else 0
        experience = int(parts[1]) if len(parts) > 1 else 0
        
        await state.update_data(reward_coins=coins, reward_experience=experience)
        await finalize_event_creation(message, state)
        
    except ValueError:
        await message.answer("❌ Введите корректные числа для наград")


@router.callback_query(F.data == "skip_rewards")
async def skip_event_rewards(callback: CallbackQuery, state: FSMContext):
    """Пропуск наград"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await state.update_data(reward_coins=0, reward_experience=0)
    await finalize_event_creation(callback.message, state)
    await callback.answer()


async def finalize_event_creation(message: Message, state: FSMContext):
    """Завершение создания ивента"""
    try:
        data = await state.get_data()
        
        # Создаем ивент
        now = datetime.utcnow()
        event_data = {
            "name": data["name"],
            "description": data["description"],
            "start_date": now,
            "end_date": now + timedelta(days=data["duration_days"]),
            "target_type": data["target_type"],
            "target_value": data["target_value"],
            "target_data": data.get("target_data", {}),
            "rewards": {
                "coins": data.get("reward_coins", 0),
                "experience": data.get("reward_experience", 0),
                "cards": []
            },
            "created_by": message.from_user.id
        }
        
        event = await event_service.create_event(event_data)
        
        success_text = (
            f"✅ **Ивент создан успешно!**\n\n"
            f"🎪 **{event.name}**\n"
            f"📝 {event.description}\n\n"
            f"📅 Длительность: {data['duration_days']} дней\n"
            f"🎯 Цель: {event.target_value} {event.target_type.replace('_', ' ')}\n"
        )
        
        if data.get("reward_coins", 0) > 0 or data.get("reward_experience", 0) > 0:
            success_text += f"\n🎁 Награды:\n"
            if data.get("reward_coins", 0) > 0:
                success_text += f"🪙 {data['reward_coins']} монет\n"
            if data.get("reward_experience", 0) > 0:
                success_text += f"✨ {data['reward_experience']} опыта\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎪 Управление ивентами", callback_data="admin_events")]
        ])
        
        await message.answer(success_text, reply_markup=keyboard)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error finalizing event creation: {e}")
        await message.answer("❌ Ошибка при создании ивента")
        await state.clear()


@router.callback_query(F.data == "event_templates")
async def event_templates_menu(callback: CallbackQuery):
    """Меню шаблонов ивентов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    templates_text = (
        "🎯 **Шаблоны ивентов**\n\n"
        "Выберите готовый шаблон для быстрого создания:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Коллекционер", callback_data="template_collector"),
            InlineKeyboardButton(text="🔥 Охотник за редкими", callback_data="template_rare_hunter")
        ],
        [
            InlineKeyboardButton(text="⭐ Покоритель уровней", callback_data="template_level_master"),
            InlineKeyboardButton(text="🏆 Чемпион недели", callback_data="template_weekly_champion")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_events")]
    ])
    
    await callback.message.edit_text(templates_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("template_"))
async def create_event_from_template(callback: CallbackQuery):
    """Создание ивента из шаблона"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    template_type = callback.data.split("_", 1)[1]
    
    templates = {
        "collector": {
            "name": "Великий коллекционер",
            "description": "Соберите 50 карточек любого типа",
            "icon": "🎴",
            "duration_days": 7,
            "target_type": "total_cards",
            "target_value": 50,
            "target_data": {},
            "rewards": {"coins": 200, "experience": 150, "cards": []}
        },
        "rare_hunter": {
            "name": "Охотник за редкими",
            "description": "Соберите 10 редких карточек или выше",
            "icon": "🔥",
            "duration_days": 10,
            "target_type": "card_rarity",
            "target_value": 10,
            "target_data": {"rarity": "rare"},
            "rewards": {"coins": 300, "experience": 200, "cards": []}
        },
        "level_master": {
            "name": "Покоритель уровней",
            "description": "Достигните 15-го уровня",
            "icon": "⭐",
            "duration_days": 14,
            "target_type": "level",
            "target_value": 15,
            "target_data": {},
            "rewards": {"coins": 500, "experience": 300, "cards": []}
        },
        "weekly_champion": {
            "name": "Чемпион недели",
            "description": "Соберите 30 карточек за неделю",
            "icon": "🏆",
            "duration_days": 7,
            "target_type": "total_cards",
            "target_value": 30,
            "target_data": {},
            "rewards": {"coins": 150, "experience": 100, "cards": []}
        }
    }
    
    template = templates.get(template_type)
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    try:
        # Создаем ивент из шаблона
        now = datetime.utcnow()
        event_data = {
            **template,
            "start_date": now,
            "end_date": now + timedelta(days=template["duration_days"]),
            "created_by": callback.from_user.id
        }
        
        event = await event_service.create_event(event_data)
        
        success_text = (
            f"✅ **Ивент создан из шаблона!**\n\n"
            f"{event.icon} **{event.name}**\n"
            f"📝 {event.description}\n\n"
            f"📅 Длительность: {template['duration_days']} дней\n"
            f"🎯 Цель: {event.target_value} {event.target_type.replace('_', ' ')}\n\n"
            f"🎁 **Награды:**\n"
            f"🪙 {template['rewards']['coins']} монет\n"
            f"✨ {template['rewards']['experience']} опыта"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎪 Управление ивентами", callback_data="admin_events")]
        ])
        
        await callback.message.edit_text(success_text, reply_markup=keyboard)
        await callback.answer("🎉 Ивент создан из шаблона!")
        
    except Exception as e:
        logger.error(f"Error creating event from template: {e}")
        await callback.answer("❌ Ошибка при создании ивента", show_alert=True)
