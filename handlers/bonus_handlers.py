from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger

from models.user import User
from services.user_service import user_service
from services.card_service import card_service
from services.game_service import game_service

router = Router()


@router.callback_query(F.data == "bonus")
async def bonus_menu(callback: CallbackQuery):
    """Меню бонусов и специальных функций"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден. Используйте /start", show_alert=True)
            return
        
        # Проверяем доступные бонусы
        bonuses_text = "🎁 **Доступные бонусы:**\n\n"
        
        # Ежедневная карточка
        can_get_daily = await user_service.can_get_daily_card(user)
        if can_get_daily:
            bonuses_text += "🎴 Ежедневная карточка - **ДОСТУПНА**\n"
        else:
            if user.last_daily_card:
                next_time = user.last_daily_card + timedelta(hours=2)
                remaining = next_time - datetime.utcnow()
                if remaining.total_seconds() > 0:
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    bonuses_text += f"🎴 Ежедневная карточка - через {hours}ч {minutes}м\n"
                else:
                    bonuses_text += "🎴 Ежедневная карточка - **ДОСТУПНА**\n"
        
        # Бонус для новичков
        if not user.newbie_bonus_received:
            bonuses_text += "🆕 Бонус новичка - **ДОСТУПЕН**\n"
        
        # Статистика опыта
        exp_to_next = user.get_experience_to_next_level()
        bonuses_text += f"\n📈 **Прогресс:**\n"
        bonuses_text += f"🎯 Текущий уровень: {user.level}\n"
        bonuses_text += f"✨ Опыт: {user.experience}\n"
        bonuses_text += f"⬆️ До следующего уровня: {exp_to_next} опыта\n"
        
        # Рекомендации
        bonuses_text += f"\n💡 **Как получить опыт:**\n"
        bonuses_text += f"• Получение карточек: 10-250 опыта\n"
        bonuses_text += f"• Улучшение карточек: 50+ опыта\n"
        bonuses_text += f"• Артефактные карточки: 250 опыта\n"
        bonuses_text += f"• Покупка паков: 25-100 опыта\n"
        bonuses_text += f"• Участие в событиях: 100+ опыта\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎴 Получить карточку", callback_data="daily_card"),
                InlineKeyboardButton(text="🎁 Новичок бонус", callback_data="newbie_bonus")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="bonus_stats"),
                InlineKeyboardButton(text="🎯 Достижения", callback_data="achievements")
            ],
            [
                InlineKeyboardButton(text="🎪 События", callback_data="events"),
                InlineKeyboardButton(text="🎲 Случайная карточка", callback_data="random_card")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(bonuses_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in bonus menu: {e}")
        await callback.answer("❌ Ошибка при загрузке бонусов", show_alert=True)


@router.callback_query(F.data == "newbie_bonus")
async def newbie_bonus(callback: CallbackQuery):
    """Бонус для новичков"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if user.newbie_bonus_received:
            await callback.answer("❌ Вы уже получили бонус новичка!", show_alert=True)
            return
        
        # Выдаем бонусную карточку редкости rare или выше
        import random
        bonus_rarities = ["rare", "epic", "legendary"]
        chosen_rarity = random.choice(bonus_rarities)
        
        bonus_card = await card_service.get_random_card_by_rarity(chosen_rarity)
        
        if bonus_card:
            await user_service.add_card_to_user(user, str(bonus_card.id))
            await card_service.update_card_stats(bonus_card.name, 1, 1)
            
            # Помечаем бонус как полученный
            user.newbie_bonus_received = True
            
            # Добавляем монеты и опыт
            bonus_coins = 50
            user.coins += bonus_coins
            await user_service.update_user(user)
            await user_service.add_experience(user, 100)
            
            message_text = (
                f"🎉 **Бонус новичка получен!**\n\n"
                f"{bonus_card.get_rarity_emoji()} **{bonus_card.name}**\n"
                f"📖 {bonus_card.description}\n\n"
                f"✨ +100 опыта\n"
                f"🪙 +{bonus_coins} монет!"
            )
            
            await callback.message.edit_text(message_text)
            await callback.answer("🎁 Бонус новичка получен!")
        else:
            await callback.answer("❌ Ошибка при выдаче бонуса", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in newbie bonus: {e}")
        await callback.answer("❌ Ошибка при получении бонуса", show_alert=True)


@router.callback_query(F.data == "bonus_stats")
async def bonus_stats(callback: CallbackQuery):
    """Статистика бонусов и достижений"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Собираем статистику по редкостям
        rarity_stats = {}
        for user_card in user.cards:
            card = await card_service.get_card_by_id(user_card.card_id)
            if card:
                if card.rarity not in rarity_stats:
                    rarity_stats[card.rarity] = 0
                rarity_stats[card.rarity] += user_card.quantity
        
        stats_text = f"📊 **Статистика коллекции**\n\n"
        stats_text += f"👤 **{user.first_name or 'Игрок'}**\n"
        stats_text += f"🎯 Уровень: {user.level}\n"
        stats_text += f"✨ Опыт: {user.experience}\n"
        stats_text += f"🃏 Всего карточек: {user.total_cards}\n"
        stats_text += f"🎴 Уникальных: {len(user.cards)}\n\n"
        
        stats_text += "📈 **По редкостям:**\n"
        for rarity in ["common", "rare", "epic", "legendary", "artifact"]:
            count = rarity_stats.get(rarity, 0)
            emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", 
                    "legendary": "🟡", "artifact": "🔴"}.get(rarity, "❓")
            stats_text += f"{emoji} {rarity.title()}: {count}\n"
        
        # Достижения
        achievements = []
        if user.total_cards >= 10:
            achievements.append("🏆 Коллекционер (10+ карточек)")
        if user.level >= 5:
            achievements.append("⭐ Опытный игрок (5+ уровень)")
        if rarity_stats.get("artifact", 0) > 0:
            achievements.append("💎 Владелец артефакта")
        if len(user.cards) >= 5:
            achievements.append("🎯 Разнообразие (5+ видов)")
        
        if achievements:
            stats_text += f"\n🏅 **Достижения:**\n"
            for achievement in achievements:
                stats_text += f"• {achievement}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="bonus")]
        ])
        
        await callback.message.edit_text(stats_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in bonus stats: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики", show_alert=True)


@router.callback_query(F.data == "achievements")
async def achievements_menu(callback: CallbackQuery):
    """Меню достижений - первая страница"""
    await show_achievements_page(callback, page=0)


@router.callback_query(F.data.startswith("achievements_page_"))
async def achievements_page(callback: CallbackQuery):
    """Меню достижений - конкретная страница"""
    try:
        page = int(callback.data.replace("achievements_page_", ""))
        await show_achievements_page(callback, page)
    except ValueError:
        await callback.answer("❌ Ошибка пагинации", show_alert=True)


async def show_achievements_page(callback: CallbackQuery, page: int = 0):
    """Показать страницу достижений"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Получаем статистику достижений
        from services.achievement_service import achievement_service
        stats = await achievement_service.get_user_achievement_stats(user)
        
        # Получаем все достижения
        all_achievements = await achievement_service.get_all_achievements()
        
        # Настройки пагинации
        achievements_per_page = 8
        total_pages = (len(all_achievements) + achievements_per_page - 1) // achievements_per_page
        
        # Проверяем валидность страницы
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
        
        # Получаем достижения для текущей страницы
        start_idx = page * achievements_per_page
        end_idx = start_idx + achievements_per_page
        page_achievements = all_achievements[start_idx:end_idx]
        
        achievements_text = (
            f"🏆 **Достижения**\n\n"
            f"📊 **Прогресс:** {stats['completed']}/{stats['total_possible']} "
            f"({stats['completion_percentage']}%)\n"
            f"⭐ **Очки достижений:** {stats['total_points']}\n"
            f"📄 **Страница {page + 1} из {total_pages}**\n\n"
            f"🎯 **Доступные достижения:**\n"
        )
        
        # Показываем достижения текущей страницы
        for i, achievement in enumerate(page_achievements, start_idx + 1):
            # Проверяем, получено ли достижение
            is_completed = any(ua.achievement_id == str(achievement.id) and ua.is_completed 
                             for ua in user.achievements)
            
            status = "✅" if is_completed else "🔒"
            difficulty_emoji = achievement.get_difficulty_emoji()
            
            achievements_text += (
                f"{i}. {status} {difficulty_emoji} **{achievement.name}**\n"
                f"   📝 {achievement.description}\n"
                f"   🎁 {achievement.reward_coins} монет, {achievement.reward_experience} XP\n\n"
            )
        
        # Создаем кнопки пагинации
        keyboard_buttons = []
        
        if total_pages > 1:
            pagination_buttons = []
            
            # Кнопка "Назад"
            if page > 0:
                pagination_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"achievements_page_{page - 1}"))
            
            # Номер страницы
            pagination_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="achievements_page_info"))
            
            # Кнопка "Вперед"
            if page < total_pages - 1:
                pagination_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"achievements_page_{page + 1}"))
            
            keyboard_buttons.append(pagination_buttons)
        
        # Кнопка "Назад"
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bonus")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(achievements_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in achievements page: {e}")
        await callback.answer("❌ Ошибка при загрузке достижений", show_alert=True)


@router.callback_query(F.data == "achievements_page_info")
async def achievements_page_info(callback: CallbackQuery):
    """Информация о пагинации достижений"""
    await callback.answer("📄 Используйте стрелки для навигации по страницам достижений", show_alert=True)


@router.callback_query(F.data == "events")
async def events_menu(callback: CallbackQuery):
    """Меню событий"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        events_text = "🎪 **События**\n\n"
        events_text += "🎉 **Активные события:**\n"
        events_text += "• 🎊 День рождения бота - повышенные шансы на редкие карточки\n"
        events_text += "• 🌟 Звездная ночь - все карточки получают +50% опыта\n"
        events_text += "• 💎 Алмазная лихорадка - увеличенный шанс артефактов\n"
        events_text += "• 🎯 День коллекционера - бонус за уникальные карточки\n"
        
        events_text += "\n❓ **Загадочные события:**\n"
        events_text += "• ??? Тайное испытание\n"
        events_text += "• ??? Скрытый турнир\n"
        events_text += "• ??? Мистическая неделя\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="bonus")]
        ])
        
        await callback.message.edit_text(events_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in events menu: {e}")
        await callback.answer("❌ Ошибка при загрузке событий", show_alert=True)


@router.callback_query(F.data == "random_card")
async def random_card_bonus(callback: CallbackQuery):
    """Случайная карточка за монеты"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Стоимость случайной карточки
        cost = 25
        
        if user.coins < cost:
            await callback.answer(f"❌ Недостаточно монет! Нужно: {cost}, у вас: {user.coins}", show_alert=True)
            return
        
        # Получаем случайную карточку
        card = await card_service.get_random_card()
        if not card:
            await callback.answer("❌ Карточки временно недоступны", show_alert=True)
            return
        
        # Списываем монеты и выдаем карточку
        user.coins -= cost
        await user_service.add_card_to_user(user, str(card.id))
        await user_service.update_user(user)
        
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
        
        await user_service.add_experience(user, exp_gained)
        
        message_text = (
            f"🎲 **Случайная карточка получена!**\n\n"
            f"{card.get_rarity_emoji()} **{card.name}**\n"
            f"📖 {card.description}\n\n"
            f"✨ +{exp_gained} опыта\n"
            f"🪙 -{cost} монет"
        )
        
        await callback.message.edit_text(message_text)
        await callback.answer("🎲 Карточка получена!")
        
    except Exception as e:
        logger.error(f"Error in random card bonus: {e}")
        await callback.answer("❌ Ошибка при получении карточки", show_alert=True)


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    welcome_text = (
        "🎮 **Добро пожаловать в карточную игру!**\n\n"
        "🃏 Собирайте карточки разных редкостей\n"
        "🔧 Улучшайте карточки и повышайте уровень\n"
        "🏆 Соревнуйтесь с другими игроками\n\n"
        "Выберите действие:"
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
            InlineKeyboardButton(text="🔧 Улучшить карточки", callback_data="upgrade_menu"),
            InlineKeyboardButton(text="⚡ Лидерборд", callback_data="leaderboard")
        ],
        [InlineKeyboardButton(text="💎 NFT Карточки", callback_data="nft_cards")],
        [
            InlineKeyboardButton(text="🎁 Бонус", callback_data="bonus"),
            InlineKeyboardButton(text="🥚 ПАСХАЛКА", callback_data="easter_egg")
        ],
        [
            InlineKeyboardButton(text="🎁 Предложить гифку", callback_data="suggest_gif"),
            InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
        ]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard)
    await callback.answer()
