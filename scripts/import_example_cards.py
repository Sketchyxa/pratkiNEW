#!/usr/bin/env python3
"""
Скрипт для импорта примерных карточек в базу данных
Используется для первоначального заполнения БД
"""

import asyncio
import json
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.card_service import card_service
from loguru import logger

# Примерные карточки для демонстрации
EXAMPLE_CARDS = [
    {
        "name": "Обычный Пратк",
        "description": "Самый простой пратк, встречается повсеместно",
        "rarity": "common",
        "tags": ["базовый", "стартовый"]
    },
    {
        "name": "Редкий Пратк",
        "description": "Пратк с особыми способностями",
        "rarity": "rare",
        "tags": ["способности", "улучшенный"]
    },
    {
        "name": "Эпический Боевой Пратк",
        "description": "Пратк, закаленный в боях",
        "rarity": "epic",
        "tags": ["боевой", "опытный", "сильный"]
    },
    {
        "name": "Легендарный Мастер Пратк",
        "description": "Мастер своего дела, один из немногих",
        "rarity": "legendary",
        "tags": ["мастер", "уникальный", "мудрый"]
    },
    {
        "name": "Артефактный Древний Пратк",
        "description": "Древний пратк, обладающий невероятной силой",
        "rarity": "artifact",
        "tags": ["древний", "артефакт", "могущественный"]
    },
    # Еще несколько карточек для разнообразия
    {
        "name": "Веселый Пратк",
        "description": "Всегда поднимет настроение",
        "rarity": "common",
        "tags": ["веселый", "позитивный"]
    },
    {
        "name": "Умный Пратк",
        "description": "Знает ответы на все вопросы",
        "rarity": "rare",
        "tags": ["умный", "знания"]
    },
    {
        "name": "Быстрый Пратк",
        "description": "Молниеносно выполняет любые задачи",
        "rarity": "epic",
        "tags": ["быстрый", "эффективный"]
    },
    {
        "name": "Золотой Пратк",
        "description": "Сияет как настоящее золото",
        "rarity": "legendary",
        "tags": ["золотой", "ценный", "блестящий"]
    },
    {
        "name": "Космический Пратк",
        "description": "Прибыл из далеких галактик",
        "rarity": "artifact",
        "tags": ["космический", "инопланетный", "редчайший"]
    },
    # Добавим еще common карточек для баланса
    {
        "name": "Простой Пратк",
        "description": "Обычный пратк без особых примет",
        "rarity": "common",
        "tags": ["простой", "обычный"]
    },
    {
        "name": "Маленький Пратк",
        "description": "Компактный и милый пратк",
        "rarity": "common",
        "tags": ["маленький", "милый"]
    },
    {
        "name": "Большой Пратк",
        "description": "Внушительных размеров пратк",
        "rarity": "rare",
        "tags": ["большой", "внушительный"]
    },
    {
        "name": "Хитрый Пратк",
        "description": "Всегда найдет нестандартное решение",
        "rarity": "rare",
        "tags": ["хитрый", "изобретательный"]
    },
    {
        "name": "Магический Пратк",
        "description": "Владеет древней магией",
        "rarity": "epic",
        "tags": ["магический", "заклинания"]
    }
]


async def import_cards():
    """Импорт примерных карточек"""
    try:
        logger.info("Starting example cards import...")
        
        # Подключаемся к базе данных
        await db.connect()
        
        imported_count = 0
        skipped_count = 0
        
        for card_data in EXAMPLE_CARDS:
            # Проверяем, существует ли карточка
            existing_card = await card_service.get_card_by_name(card_data["name"])
            
            if existing_card:
                logger.info(f"Card '{card_data['name']}' already exists, skipping")
                skipped_count += 1
                continue
            
            # Создаем карточку
            card = await card_service.create_card(
                name=card_data["name"],
                description=card_data["description"],
                rarity=card_data["rarity"],
                tags=card_data.get("tags", [])
            )
            
            if card:
                logger.info(f"Created card: {card.name} ({card.rarity})")
                imported_count += 1
            else:
                logger.error(f"Failed to create card: {card_data['name']}")
        
        logger.info(f"Import completed! Created: {imported_count}, Skipped: {skipped_count}")
        
        # Отключаемся от базы данных
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"Error importing cards: {e}")
        raise


async def export_cards_to_json(filename: str = "exported_cards.json"):
    """Экспорт всех карточек в JSON файл"""
    try:
        logger.info(f"Exporting cards to {filename}...")
        
        await db.connect()
        
        # Получаем все карточки
        cards = await card_service.get_all_cards(include_inactive=True)
        
        # Конвертируем в JSON формат
        cards_data = []
        for card in cards:
            card_dict = {
                "name": card.name,
                "description": card.description,
                "rarity": card.rarity,
                "tags": card.tags,
                "image_url": card.image_url,
                "gif_url": card.gif_url,
                "video_url": card.video_url,
                "is_active": card.is_active
            }
            cards_data.append(card_dict)
        
        # Сохраняем в файл
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(cards_data)} cards to {filename}")
        
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"Error exporting cards: {e}")
        raise


async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "export":
            filename = sys.argv[2] if len(sys.argv) > 2 else "exported_cards.json"
            await export_cards_to_json(filename)
        elif sys.argv[1] == "import":
            await import_cards()
        else:
            print("Usage: python import_example_cards.py [import|export] [filename]")
    else:
        await import_cards()


if __name__ == "__main__":
    asyncio.run(main())
