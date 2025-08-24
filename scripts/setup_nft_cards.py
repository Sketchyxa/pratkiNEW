#!/usr/bin/env python3
"""
Скрипт для настройки карточек как доступных для покупки NFT
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.card_service import card_service
from config import settings
from database.connection import db


async def setup_nft_cards():
    """Настройка карточек как доступных для NFT"""
    print("🔧 Настройка NFT карточек...")
    
    # Подключаемся к базе данных
    await db.connect()
    
    try:
        # Получаем все карточки
        all_cards = await card_service.get_all_cards()
        print(f"📊 Найдено карточек: {len(all_cards)}")
        
        # Цены для разных редкостей
        nft_prices = {
            "common": 1000,
            "rare": 2000,
            "epic": 3000,
            "legendary": 4000,
            "artifact": 5000
        }
        
        updated_count = 0
        
        for card in all_cards:
            # Делаем все карточки доступными для NFT
            if not card.is_nft_available:
                card.is_nft_available = True
                card.nft_price = nft_prices.get(card.rarity, 1000)
                
                # Обновляем карточку в базе
                success = await card_service.update_card(card)
                if success:
                    updated_count += 1
                    print(f"✅ {card.name} ({card.rarity}) - {card.nft_price} XP")
                else:
                    print(f"❌ Ошибка обновления {card.name}")
        
        print(f"\n🎉 Настройка завершена!")
        print(f"📈 Обновлено карточек: {updated_count}")
        print(f"💎 Все карточки теперь доступны для покупки как NFT!")
        
        # Показываем статистику
        rarity_stats = {}
        for card in all_cards:
            if card.is_nft_available:
                rarity_stats[card.rarity] = rarity_stats.get(card.rarity, 0) + 1
        
        print(f"\n📊 Статистика по редкостям:")
        for rarity, count in rarity_stats.items():
            price = nft_prices.get(rarity, 1000)
            print(f"• {rarity.title()}: {count} карточек - {price} XP")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await db.disconnect()


async def reset_nft_cards():
    """Сброс всех NFT карточек (удаление владельцев)"""
    print("🔄 Сброс NFT карточек...")
    
    # Подключаемся к базе данных
    await db.connect()
    
    try:
        all_cards = await card_service.get_all_cards()
        reset_count = 0
        
        for card in all_cards:
            if card.is_nft_owned():
                card.nft_owner_id = None
                card.nft_assigned_at = None
                card.nft_transfer_count = 0
                
                success = await card_service.update_card(card)
                if success:
                    reset_count += 1
                    print(f"🔄 Сброшена NFT: {card.name}")
        
        print(f"\n✅ Сброшено NFT карточек: {reset_count}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await db.disconnect()


async def show_nft_status():
    """Показать статус NFT карточек"""
    print("📊 Статус NFT карточек...")
    
    # Подключаемся к базе данных
    await db.connect()
    
    try:
        all_cards = await card_service.get_all_cards()
        
        available_count = 0
        owned_count = 0
        
        for card in all_cards:
            if card.is_nft_available:
                available_count += 1
                if card.is_nft_owned():
                    owned_count += 1
                    print(f"🔒 {card.name} - владелец: {card.nft_owner_id}")
                else:
                    print(f"🛒 {card.name} - {card.nft_price} XP")
        
        print(f"\n📈 Статистика:")
        print(f"• Всего карточек: {len(all_cards)}")
        print(f"• Доступно для NFT: {available_count}")
        print(f"• Присвоено как NFT: {owned_count}")
        print(f"• Свободно для покупки: {available_count - owned_count}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python setup_nft_cards.py setup    - Настроить карточки как NFT")
        print("  python setup_nft_cards.py reset    - Сбросить все NFT")
        print("  python setup_nft_cards.py status   - Показать статус")
        return
    
    command = sys.argv[1]
    
    if command == "setup":
        await setup_nft_cards()
    elif command == "reset":
        await reset_nft_cards()
    elif command == "status":
        await show_nft_status()
    else:
        print(f"❌ Неизвестная команда: {command}")


if __name__ == "__main__":
    asyncio.run(main())
