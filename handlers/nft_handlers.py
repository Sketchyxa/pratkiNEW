from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
import random

from models.user import User
from services.user_service import user_service
from services.card_service import card_service
from services.nft_service import nft_service

router = Router()


@router.callback_query(F.data == "nft_cards")
async def nft_menu(callback: CallbackQuery):
    """Меню NFT карточек"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Получаем NFT карточки пользователя
        user_nfts = await nft_service.get_user_nfts(user)
        
        # Получаем доступные для покупки NFT
        available_nfts = await nft_service.get_available_nft_cards()
        
        nft_text = (
            "💎 **NFT Система**\n\n"
            f"🏆 Ваших NFT: {len(user_nfts)}\n"
            f"🛒 Доступно для покупки: {len(available_nfts)}\n\n"
        )
        
        if user_nfts:
            nft_text += "🔴 **Ваши NFT карточки:**\n\n"
            for card, user_nft in user_nfts:
                nft_text += f"🔴 **{card.name}**\n"
                nft_text += f"   📅 Присвоена: {user_nft.assigned_at.strftime('%d.%m.%Y')}\n"
                nft_text += f"   🔄 Передач: {user_nft.transfer_count}\n\n"
        else:
            nft_text += (
                "❌ У вас пока нет NFT карточек\n\n"
                "💡 **Как получить NFT:**\n"
                "• Получите карточку обычным способом\n"
                "• Купите её как NFT за опыт\n"
                "• Станьте единственным владельцем!\n\n"
                "💰 Цены: 1000-5000 XP в зависимости от редкости"
            )
        
        if available_nfts:
            nft_text += f"\n🛒 **Доступные для покупки NFT:**\n"
            for i, card in enumerate(available_nfts[:5], 1):  # Показываем первые 5
                nft_text += f"{i}. {card.get_rarity_emoji()} **{card.name}** - {card.nft_price} XP\n"
            if len(available_nfts) > 5:
                nft_text += f"... и еще {len(available_nfts) - 5} карточек\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить NFT", callback_data="nft_shop"),
                InlineKeyboardButton(text="📊 Мои NFT", callback_data="my_nfts")
            ],
            [
                InlineKeyboardButton(text="🔄 Передать NFT", callback_data="nft_transfer"),
                InlineKeyboardButton(text="💰 Продать NFT", callback_data="nft_sell")
            ],
            [
                InlineKeyboardButton(text="🏆 Рейтинг NFT", callback_data="nft_leaderboard"),
                InlineKeyboardButton(text="📈 Статистика", callback_data="nft_stats")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(nft_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in NFT menu: {e}")
        await callback.answer("❌ Ошибка при загрузке NFT меню", show_alert=True)


@router.callback_query(F.data == "nft_shop")
async def nft_shop(callback: CallbackQuery):
    """Магазин NFT карточек - первая страница"""
    await show_nft_shop_page(callback, page=0)


@router.callback_query(F.data.startswith("nft_shop_page_"))
async def nft_shop_page(callback: CallbackQuery):
    """Магазин NFT карточек - конкретная страница"""
    try:
        page = int(callback.data.replace("nft_shop_page_", ""))
        await show_nft_shop_page(callback, page)
    except ValueError:
        await callback.answer("❌ Ошибка пагинации", show_alert=True)


async def show_nft_shop_page(callback: CallbackQuery, page: int = 0):
    """Показать страницу NFT магазина"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Получаем доступные NFT
        available_nfts = await nft_service.get_available_nft_cards()
        
        if not available_nfts:
            shop_text = (
                "🛒 **NFT Магазин**\n\n"
                "❌ Сейчас нет доступных карточек для покупки как NFT\n\n"
                "💡 Попробуйте позже или получите карточки обычным способом!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")]
            ])
        else:
            # Настройки пагинации
            cards_per_page = 8
            total_pages = (len(available_nfts) + cards_per_page - 1) // cards_per_page
            
            # Проверяем валидность страницы
            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0
            
            # Получаем карточки для текущей страницы
            start_idx = page * cards_per_page
            end_idx = start_idx + cards_per_page
            page_cards = available_nfts[start_idx:end_idx]
            
            shop_text = (
                "🛒 **NFT Магазин**\n\n"
                f"💰 Ваш опыт: {user.experience} XP\n"
                f"🛒 Доступно карточек: {len(available_nfts)}\n"
                f"📄 Страница {page + 1} из {total_pages}\n\n"
                "💡 **Как купить NFT:**\n"
                "1. Получите карточку обычным способом\n"
                "2. Купите её как NFT за опыт\n"
                "3. Станьте единственным владельцем!\n\n"
                "🔴 **Доступные NFT:**\n"
            )
            
            # Показываем карточки текущей страницы
            for i, card in enumerate(page_cards, start_idx + 1):
                has_card = user.get_card_count(str(card.id)) > 0
                status = "✅ Есть" if has_card else "❌ Нет"
                shop_text += f"{i}. {card.get_rarity_emoji()} **{card.name}** - {card.nft_price} XP ({status})\n"
            
            # Создаем кнопки для покупки (все карточки на странице)
            keyboard_buttons = []
            for card in page_cards:
                has_card = user.get_card_count(str(card.id)) > 0
                can_afford = user.experience >= card.nft_price
                
                if has_card and can_afford:
                    button_text = f"💎 {card.name[:15]}... ({card.nft_price} XP)"
                    callback_data = f"buy_nft_{card.name}"
                elif has_card:
                    button_text = f"❌ {card.name[:15]}... (недостаточно XP)"
                    callback_data = "nft_insufficient_xp"
                else:
                    button_text = f"🔒 {card.name[:15]}... (нет карточки)"
                    callback_data = "nft_no_card"
                
                keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
            
            # Кнопки пагинации
            pagination_buttons = []
            
            if total_pages > 1:
                # Кнопка "Назад"
                if page > 0:
                    pagination_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"nft_shop_page_{page - 1}"))
                
                # Номер страницы
                pagination_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="nft_page_info"))
                
                # Кнопка "Вперед"
                if page < total_pages - 1:
                    pagination_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"nft_shop_page_{page + 1}"))
                
                keyboard_buttons.append(pagination_buttons)
            
            # Кнопка "Назад"
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(shop_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in NFT shop page: {e}")
        await callback.answer("❌ Ошибка при загрузке магазина", show_alert=True)


@router.callback_query(F.data == "nft_page_info")
async def nft_page_info(callback: CallbackQuery):
    """Информация о пагинации"""
    await callback.answer("📄 Используйте стрелки для навигации по страницам", show_alert=True)


@router.callback_query(F.data.startswith("buy_nft_"))
async def buy_nft(callback: CallbackQuery):
    """Покупка NFT карточки"""
    try:
        card_name = callback.data.replace("buy_nft_", "")
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        success, message = await nft_service.buy_nft(user, card_name)
        
        if success:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🛒 Купить еще", callback_data="nft_shop"),
                    InlineKeyboardButton(text="💎 Мои NFT", callback_data="my_nfts")
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Попробовать еще", callback_data="nft_shop")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")]
            ])
        
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error buying NFT: {e}")
        await callback.answer("❌ Ошибка при покупке NFT", show_alert=True)


@router.callback_query(F.data == "my_nfts")
async def my_nfts(callback: CallbackQuery):
    """Показать NFT пользователя - первая страница"""
    await show_my_nfts_page(callback, page=0)


@router.callback_query(F.data.startswith("my_nfts_page_"))
async def my_nfts_page(callback: CallbackQuery):
    """Показать NFT пользователя - конкретная страница"""
    try:
        page = int(callback.data.replace("my_nfts_page_", ""))
        await show_my_nfts_page(callback, page)
    except ValueError:
        await callback.answer("❌ Ошибка пагинации", show_alert=True)


async def show_my_nfts_page(callback: CallbackQuery, page: int = 0):
    """Показать страницу NFT пользователя"""
    try:
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        user_nfts = await nft_service.get_user_nfts(user)
        
        if not user_nfts:
            nft_text = (
                "💎 **Мои NFT**\n\n"
                "❌ У вас пока нет NFT карточек\n\n"
                "💡 Отправляйтесь в магазин, чтобы купить свою первую NFT!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 NFT Магазин", callback_data="nft_shop")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")]
            ])
        else:
            # Настройки пагинации
            nfts_per_page = 8
            total_pages = (len(user_nfts) + nfts_per_page - 1) // nfts_per_page
            
            # Проверяем валидность страницы
            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0
            
            # Получаем NFT для текущей страницы
            start_idx = page * nfts_per_page
            end_idx = start_idx + nfts_per_page
            page_nfts = user_nfts[start_idx:end_idx]
            
            nft_text = f"💎 **Мои NFT карточки** ({len(user_nfts)})\n"
            nft_text += f"📄 Страница {page + 1} из {total_pages}\n\n"
            
            for i, (card, user_nft) in enumerate(page_nfts, start_idx + 1):
                nft_text += f"{i}. {card.get_rarity_emoji()} **{card.name}**\n"
                nft_text += f"   📅 Присвоена: {user_nft.assigned_at.strftime('%d.%m.%Y %H:%M')}\n"
                nft_text += f"   🔄 Передач: {user_nft.transfer_count}\n"
                nft_text += f"   💰 Цена покупки: {card.nft_price} XP\n\n"
            
            # Создаем кнопки для управления NFT (все NFT на странице)
            keyboard_buttons = []
            for card, user_nft in page_nfts:
                keyboard_buttons.append([
                    InlineKeyboardButton(text=f"👁️ {card.name[:15]}...", callback_data=f"view_card:{card.name}"),
                    InlineKeyboardButton(text=f"🔄 Передать", callback_data=f"transfer_nft_{card.name}")
                ])
                keyboard_buttons.append([
                    InlineKeyboardButton(text=f"💰 Продать", callback_data=f"sell_nft_{card.name}")
                ])
            
            # Кнопки пагинации
            if total_pages > 1:
                pagination_buttons = []
                
                # Кнопка "Назад"
                if page > 0:
                    pagination_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"my_nfts_page_{page - 1}"))
                
                # Номер страницы
                pagination_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="nft_page_info"))
                
                # Кнопка "Вперед"
                if page < total_pages - 1:
                    pagination_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"my_nfts_page_{page + 1}"))
                
                keyboard_buttons.append(pagination_buttons)
            
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(nft_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing user NFTs page: {e}")
        await callback.answer("❌ Ошибка при загрузке NFT", show_alert=True)


@router.callback_query(F.data == "nft_leaderboard")
async def nft_leaderboard(callback: CallbackQuery):
    """Рейтинг NFT владельцев"""
    try:
        leaderboard = await nft_service.get_nft_leaderboard()
        
        if not leaderboard:
            leaderboard_text = (
                "🏆 **Рейтинг NFT владельцев**\n\n"
                "❌ Пока нет игроков с NFT карточками\n\n"
                "💡 Будьте первым, кто купит NFT!"
            )
        else:
            leaderboard_text = "🏆 **Рейтинг NFT владельцев**\n\n"
            
            for i, (user, nft_count) in enumerate(leaderboard, 1):
                username = user.username if user.username else f"User{user.telegram_id}"
                leaderboard_text += f"{i}. 👤 @{username} - {nft_count} NFT\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")]
        ])
        
        await callback.message.edit_text(leaderboard_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing NFT leaderboard: {e}")
        await callback.answer("❌ Ошибка при загрузке рейтинга", show_alert=True)


@router.callback_query(F.data == "nft_stats")
async def nft_stats(callback: CallbackQuery):
    """Статистика NFT системы"""
    try:
        # Получаем статистику
        available_nfts = await nft_service.get_available_nft_cards()
        all_users = await user_service.get_all_users()
        
        total_nfts_owned = 0
        for user in all_users:
            total_nfts_owned += len([nft for nft in user.nfts if nft.is_active])
        
        stats_text = (
            "📊 **Статистика NFT системы**\n\n"
            f"🛒 Доступно для покупки: {len(available_nfts)}\n"
            f"💎 Всего присвоено NFT: {total_nfts_owned}\n"
            f"👥 Игроков с NFT: {len([u for u in all_users if any(nft.is_active for nft in u.nfts)])}\n\n"
        )
        
        if available_nfts:
            # Статистика по редкостям
            rarity_stats = {}
            for card in available_nfts:
                rarity_stats[card.rarity] = rarity_stats.get(card.rarity, 0) + 1
            
            stats_text += "📈 **По редкостям:**\n"
            for rarity, count in rarity_stats.items():
                stats_text += f"• {rarity.title()}: {count} карточек\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="nft_cards")]
        ])
        
        await callback.message.edit_text(stats_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing NFT stats: {e}")
        await callback.answer("❌ Ошибка при загрузке статистики", show_alert=True)


# Заглушки для остальных функций
@router.callback_query(F.data.in_(["nft_transfer", "nft_sell", "nft_insufficient_xp", "nft_no_card"]))
async def nft_placeholders(callback: CallbackQuery):
    """Заглушки для NFT функций"""
    placeholders = {
        "nft_transfer": "🔄 Передача NFT карточек в разработке",
        "nft_sell": "💰 Продажа NFT карточек в разработке",
        "nft_insufficient_xp": "❌ Недостаточно опыта для покупки NFT",
        "nft_no_card": "🔒 Сначала получите карточку обычным способом"
    }
    
    message_text = placeholders.get(callback.data, "Функция в разработке")
    await callback.answer(message_text, show_alert=True)
