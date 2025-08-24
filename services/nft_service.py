from datetime import datetime
from typing import Optional, List, Tuple
from loguru import logger

from models.user import User, UserNFT
from models.card import Card
from services.user_service import user_service
from services.card_service import card_service


class NFTService:
    """Сервис для работы с NFT карточками"""
    
    async def get_available_nft_cards(self) -> List[Card]:
        """Получает список карточек, доступных для покупки как NFT"""
        try:
            all_cards = await card_service.get_all_cards()
            available_nfts = []
            
            for card in all_cards:
                # Карточка доступна для NFT если:
                # 1. Она помечена как доступная для NFT
                # 2. Еще не присвоена никому
                if card.is_nft_available and not card.is_nft_owned():
                    available_nfts.append(card)
            
            return available_nfts
            
        except Exception as e:
            logger.error(f"Error getting available NFT cards: {e}")
            return []
    
    async def get_user_nfts(self, user: User) -> List[Tuple[Card, UserNFT]]:
        """Получает NFT карточки пользователя"""
        try:
            user_nfts = []
            
            for user_nft in user.nfts:
                if user_nft.is_active:
                    card = await card_service.get_card_by_id(user_nft.card_id)
                    if card:
                        user_nfts.append((card, user_nft))
            
            return user_nfts
            
        except Exception as e:
            logger.error(f"Error getting user NFTs: {e}")
            return []
    
    async def buy_nft(self, user: User, card_name: str) -> Tuple[bool, str]:
        """
        Покупает карточку как NFT
        Возвращает: (успех, сообщение)
        """
        try:
            # Находим карточку
            card = await card_service.get_card_by_name(card_name)
            if not card:
                return False, f"❌ Карточка '{card_name}' не найдена"
            
            # Проверяем, доступна ли карточка для покупки как NFT
            if not card.is_nft_available:
                return False, f"❌ Карточка '{card_name}' недоступна для покупки как NFT"
            
            # Проверяем, не присвоена ли уже кому-то
            if card.is_nft_owned():
                return False, f"❌ Карточка '{card_name}' уже присвоена другому игроку"
            
            # Проверяем, есть ли у пользователя обычная версия карточки
            if user.get_card_count(str(card.id)) == 0:
                return False, f"❌ У вас нет карточки '{card_name}'. Сначала получите её!"
            
            # Проверяем, есть ли у пользователя достаточно опыта
            if user.experience < card.nft_price:
                return False, f"❌ Недостаточно опыта! Нужно: {card.nft_price} XP, есть: {user.experience} XP"
            
            # Проверяем, не имеет ли уже пользователь NFT версию этой карточки
            if user.has_nft(str(card.id)):
                return False, f"❌ У вас уже есть NFT версия карточки '{card_name}'"
            
            # Списываем опыт
            user.experience -= card.nft_price
            
            # Создаем NFT запись
            user_nft = UserNFT(
                card_id=str(card.id),
                assigned_at=datetime.utcnow()
            )
            user.nfts.append(user_nft)
            
            # Обновляем карточку
            card.nft_owner_id = user.telegram_id
            card.nft_assigned_at = datetime.utcnow()
            
            # Сохраняем изменения
            await user_service.update_user(user)
            await card_service.update_card(card)
            
            username = user.username if user.username else "Anonymous"
            
            message = (
                f"🎉 **NFT ПРИСВОЕНА!**\n\n"
                f"💎 @{username} купил карточку как NFT:\n"
                f"{card.get_rarity_emoji()} **{card.name}**\n"
                f"📝 {card.description}\n\n"
                f"💰 Потрачено: {card.nft_price} XP\n"
                f"🏆 Теперь вы единственный владелец этой NFT!\n"
                f"💎 Всего ваших NFT: {len([nft for nft in user.nfts if nft.is_active])}"
            )
            
            return True, message
            
        except Exception as e:
            logger.error(f"Error buying NFT for user {user.telegram_id}: {e}")
            return False, "❌ Произошла ошибка при покупке NFT"
    
    async def transfer_nft(self, from_user: User, to_user: User, card_name: str) -> Tuple[bool, str]:
        """
        Передает NFT карточку другому пользователю
        Возвращает: (успех, сообщение)
        """
        try:
            # Находим карточку
            card = await card_service.get_card_by_name(card_name)
            if not card:
                return False, f"❌ Карточка '{card_name}' не найдена"
            
            # Проверяем, что карточка присвоена отправителю
            if card.nft_owner_id != from_user.telegram_id:
                return False, f"❌ Карточка '{card_name}' не принадлежит вам"
            
            # Проверяем, что у получателя есть обычная версия карточки
            if to_user.get_card_count(str(card.id)) == 0:
                return False, f"❌ У получателя нет карточки '{card_name}'. Он должен сначала получить её!"
            
            # Проверяем, что получатель не имеет уже NFT версию
            if to_user.has_nft(str(card.id)):
                return False, f"❌ У получателя уже есть NFT версия карточки '{card_name}'"
            
            # Находим NFT у отправителя
            from_user_nft = from_user.get_nft(str(card.id))
            if not from_user_nft:
                return False, f"❌ NFT карточка '{card_name}' не найдена у отправителя"
            
            # Создаем NFT у получателя
            to_user_nft = UserNFT(
                card_id=str(card.id),
                assigned_at=datetime.utcnow(),
                transfer_count=from_user_nft.transfer_count + 1,
                last_transfer_date=datetime.utcnow()
            )
            to_user.nfts.append(to_user_nft)
            
            # Удаляем NFT у отправителя
            from_user.nfts = [nft for nft in from_user.nfts if nft.card_id != str(card.id)]
            
            # Обновляем карточку
            card.nft_owner_id = to_user.telegram_id
            card.nft_transfer_count += 1
            
            # Сохраняем изменения
            await user_service.update_user(from_user)
            await user_service.update_user(to_user)
            await card_service.update_card(card)
            
            from_username = from_user.username if from_user.username else "Anonymous"
            to_username = to_user.username if to_user.username else "Anonymous"
            
            message = (
                f"🔄 **NFT ПЕРЕДАНА!**\n\n"
                f"💎 {from_username} → {to_username}\n"
                f"{card.get_rarity_emoji()} **{card.name}**\n"
                f"📝 {card.description}\n\n"
                f"🔄 Количество передач: {card.nft_transfer_count}"
            )
            
            return True, message
            
        except Exception as e:
            logger.error(f"Error transferring NFT: {e}")
            return False, "❌ Произошла ошибка при передаче NFT"
    
    async def sell_nft(self, user: User, card_name: str) -> Tuple[bool, str]:
        """
        Продает NFT карточку обратно в систему
        Возвращает: (успех, сообщение)
        """
        try:
            # Находим карточку
            card = await card_service.get_card_by_name(card_name)
            if not card:
                return False, f"❌ Карточка '{card_name}' не найдена"
            
            # Проверяем, что карточка присвоена пользователю
            if card.nft_owner_id != user.telegram_id:
                return False, f"❌ Карточка '{card_name}' не принадлежит вам"
            
            # Находим NFT у пользователя
            user_nft = user.get_nft(str(card.id))
            if not user_nft:
                return False, f"❌ NFT карточка '{card_name}' не найдена"
            
            # Вычисляем компенсацию (50% от цены покупки)
            compensation = card.nft_price // 2
            
            # Возвращаем компенсацию
            user.experience += compensation
            
            # Удаляем NFT у пользователя
            user.nfts = [nft for nft in user.nfts if nft.card_id != str(card.id)]
            
            # Сбрасываем NFT статус карточки
            card.nft_owner_id = None
            card.nft_assigned_at = None
            
            # Сохраняем изменения
            await user_service.update_user(user)
            await card_service.update_card(card)
            
            username = user.username if user.username else "Anonymous"
            
            message = (
                f"💰 **NFT ПРОДАНА!**\n\n"
                f"💎 @{username} продал NFT карточку:\n"
                f"{card.get_rarity_emoji()} **{card.name}**\n"
                f"📝 {card.description}\n\n"
                f"💰 Получено: {compensation} XP\n"
                f"💎 Карточка снова доступна для покупки как NFT!"
            )
            
            return True, message
            
        except Exception as e:
            logger.error(f"Error selling NFT for user {user.telegram_id}: {e}")
            return False, "❌ Произошла ошибка при продаже NFT"
    
    async def get_nft_leaderboard(self) -> List[Tuple[User, int]]:
        """Получает рейтинг игроков по количеству NFT"""
        try:
            all_users = await user_service.get_all_users()
            nft_leaderboard = []
            
            for user in all_users:
                nft_count = len([nft for nft in user.nfts if nft.is_active])
                if nft_count > 0:
                    nft_leaderboard.append((user, nft_count))
            
            # Сортируем по количеству NFT (убывание)
            nft_leaderboard.sort(key=lambda x: x[1], reverse=True)
            
            return nft_leaderboard[:10]  # Топ-10
            
        except Exception as e:
            logger.error(f"Error getting NFT leaderboard: {e}")
            return []


# Глобальный экземпляр сервиса
nft_service = NFTService()
