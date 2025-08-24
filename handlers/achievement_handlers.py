from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from services.user_service import user_service
from services.achievement_service import achievement_service

router = Router()


@router.callback_query(F.data == "achievements")
async def achievements_menu(callback: CallbackQuery):
    """Меню достижений пользователя"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        stats = await achievement_service.get_user_achievement_stats(user)
        
        achievements_text = (
            f"🏆 **Ваши достижения**\n\n"
            f"📊 **Прогресс:** {stats['completed']}/{stats['total_possible']} "
            f"({stats['completion_percentage']}%)\n"
            f"⭐ **Очки достижений:** {stats['total_points']}\n\n"
            f"📂 **По категориям:**\n"
        )
        
        category_names = {
            "general": "🎯 Общие",
            "collection": "🎴 Коллекционирование", 
            "economy": "💰 Экономика",
            "social": "👥 Социальные",
            "special": "⭐ Особые"
        }
        
        for category, count in stats['categories'].items():
            category_name = category_names.get(category, category.title())
            achievements_text += f"{category_name}: {count}\n"
        
        if not stats['categories']:
            achievements_text += "Пока нет полученных достижений\n"
        
        achievements_text += "\n🎯 Выберите категорию для просмотра:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Общие", callback_data="achievements_general"),
                InlineKeyboardButton(text="🎴 Коллекции", callback_data="achievements_collection")
            ],
            [
                InlineKeyboardButton(text="💰 Экономика", callback_data="achievements_economy"),
                InlineKeyboardButton(text="👥 Социальные", callback_data="achievements_social")
            ],
            [
                InlineKeyboardButton(text="⭐ Особые", callback_data="achievements_special"),
                InlineKeyboardButton(text="🔍 Все", callback_data="achievements_all")
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(achievements_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing achievements menu: {e}")
        await callback.answer("❌ Ошибка при загрузке достижений", show_alert=True)


@router.callback_query(F.data.startswith("achievements_"))
async def achievements_category(callback: CallbackQuery):
    """Показ достижений по категории"""
    try:
        category = callback.data.split("_", 1)[1]
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        all_achievements = await achievement_service.get_all_achievements()
        user_achievement_ids = [ua.achievement_id for ua in user.achievements if ua.is_completed]
        
        # Фильтруем по категории
        if category != "all":
            filtered_achievements = [a for a in all_achievements if a.category == category]
        else:
            filtered_achievements = all_achievements
        
        if not filtered_achievements:
            await callback.answer("❌ В этой категории нет достижений", show_alert=True)
            return
        
        category_names = {
            "general": "🎯 Общие достижения",
            "collection": "🎴 Коллекционирование",
            "economy": "💰 Экономические",
            "social": "👥 Социальные",
            "special": "⭐ Особые",
            "all": "🏆 Все достижения"
        }
        
        achievements_text = f"{category_names.get(category, category.title())}\n\n"
        
        completed_count = 0
        for achievement in filtered_achievements:
            is_completed = str(achievement.id) in user_achievement_ids
            
            if is_completed:
                completed_count += 1
                status = "✅"
            else:
                # Для скрытых достижений не показываем детали
                if achievement.is_hidden:
                    continue
                status = "❌"
            
            # Прогресс для некоторых достижений
            progress_text = ""
            if not is_completed and not achievement.is_hidden:
                if achievement.condition_type == "cards_count":
                    current = min(user.total_cards, achievement.condition_value)
                    progress_text = f" ({current}/{achievement.condition_value})"
                elif achievement.condition_type == "level":
                    current = min(user.level, achievement.condition_value)
                    progress_text = f" ({current}/{achievement.condition_value})"
                elif achievement.condition_type == "coins_total":
                    current = min(user.coins, achievement.condition_value)
                    progress_text = f" ({current}/{achievement.condition_value})"
            
            achievements_text += (
                f"{status} {achievement.icon} **{achievement.name}**"
                f"{progress_text}\n"
                f"    {achievement.description}\n"
            )
            
            if is_completed:
                achievements_text += f"    🎁 +{achievement.points} очков"
                if achievement.reward_coins > 0:
                    achievements_text += f", +{achievement.reward_coins} монет"
                if achievement.reward_experience > 0:
                    achievements_text += f", +{achievement.reward_experience} опыта"
                achievements_text += "\n"
            
            achievements_text += "\n"
        
        achievements_text += f"📊 Выполнено: {completed_count}/{len(filtered_achievements)}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К достижениям", callback_data="achievements")]
        ])
        
        await callback.message.edit_text(achievements_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing achievements category: {e}")
        await callback.answer("❌ Ошибка при загрузке достижений", show_alert=True)


async def notify_new_achievements(user, new_achievements: list, bot):
    """Уведомляет пользователя о новых достижениях"""
    if not new_achievements:
        return
    
    try:
        for achievement in new_achievements:
            notification_text = (
                f"🎉 **НОВОЕ ДОСТИЖЕНИЕ!**\n\n"
                f"{achievement.icon} **{achievement.name}**\n"
                f"📝 {achievement.description}\n\n"
                f"🎁 **Награды:**\n"
            )
            
            if achievement.reward_coins > 0:
                notification_text += f"🪙 +{achievement.reward_coins} монет\n"
            if achievement.reward_experience > 0:
                notification_text += f"✨ +{achievement.reward_experience} опыта\n"
            
            notification_text += f"⭐ +{achievement.points} очков достижений"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏆 Мои достижения", callback_data="achievements")]
            ])
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=notification_text,
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Error notifying about new achievements: {e}")


# Функция для проверки достижений после игровых действий
async def check_and_notify_achievements(user, bot=None):
    """Проверяет и уведомляет о новых достижениях"""
    try:
        new_achievements = await achievement_service.check_user_achievements(user)
        if new_achievements and bot:
            await notify_new_achievements(user, new_achievements, bot)
        return new_achievements
    except Exception as e:
        logger.error(f"Error checking achievements: {e}")
        return []
