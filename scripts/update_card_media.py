#!/usr/bin/env python3
"""
Скрипт для обновления карточек с ссылками на медиафайлы
"""

import asyncio
import sys
import os
import glob

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from services.card_service import card_service
from loguru import logger

async def update_card_media():
    """Обновляет карточки с ссылками на медиафайлы"""
    print("🔧 Обновление карточек с медиафайлами...")
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        print("✅ Подключение к базе данных успешно")
        
        # Получаем все карточки
        all_cards = await card_service.get_all_cards()
        print(f"✅ Найдено {len(all_cards)} карточек")
        
        # Получаем список всех медиафайлов
        media_files = glob.glob("assets/images/*.mp4")
        media_files.extend(glob.glob("assets/images/*.gif"))
        media_files.extend(glob.glob("assets/images/*.jpg"))
        media_files.extend(glob.glob("assets/images/*.jpeg"))
        media_files.extend(glob.glob("assets/images/*.png"))
        
        print(f"✅ Найдено {len(media_files)} медиафайлов")
        
        # Создаем словарь соответствия имен карточек и файлов
        card_media_map = {}
        
        # Обрабатываем файлы с именами карточек (card24.mp4, card25.mp4 и т.д.)
        for file_path in media_files:
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            # Если файл начинается с "card" и содержит число
            if name_without_ext.startswith("card") and name_without_ext[4:].isdigit():
                card_number = int(name_without_ext[4:])
                # Найдем карточку по номеру (если есть)
                if card_number <= len(all_cards):
                    card = all_cards[card_number - 1]  # Индексация с 0
                    card_media_map[card.name] = f"assets/images/{filename}"
        
        # Обрабатываем файлы с названиями карточек
        special_cards = [
            "ancient_sage", "crystal_phoenix", "mechanical_titan", "wind_shaman",
            "sea_leviathan", "mountain_dwarf", "poison_basilisk", "fire_dragon",
            "ghost_knight", "sand_scorpion", "desert_djinn", "snow_wolf",
            "ice_golem", "forest_bear", "sky_whale", "forest_fairy",
            "star_drake", "sacred_unicorn", "forest_elf", "vampire_queen",
            "dark_mage", "goblin_mechanic", "wisdom_tree"
        ]
        
        for card_name in special_cards:
            for file_path in media_files:
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                
                if name_without_ext == card_name:
                    # Найдем карточку по имени
                    for card in all_cards:
                        if card_name.lower() in card.name.lower():
                            card_media_map[card.name] = f"assets/images/{filename}"
                            break
        
        print(f"✅ Создано {len(card_media_map)} соответствий карточек и медиафайлов")
        
        # Обновляем карточки
        updated_count = 0
        for card_name, media_path in card_media_map.items():
            card = await card_service.get_card_by_name(card_name)
            if card:
                # Определяем тип медиафайла
                if media_path.endswith('.mp4'):
                    card.video_url = media_path
                elif media_path.endswith('.gif'):
                    card.gif_url = media_path
                elif media_path.endswith(('.jpg', '.jpeg', '.png')):
                    card.image_url = media_path
                
                # Обновляем карточку
                success = await card_service.update_card(card)
                if success:
                    updated_count += 1
                    print(f"✅ Обновлена карточка: {card_name} -> {media_path}")
        
        print(f"\n✅ Обновлено {updated_count} карточек из {len(card_media_map)}")
        
        # Показываем примеры обновленных карточек
        print("\n📋 Примеры обновленных карточек:")
        for i, (card_name, media_path) in enumerate(list(card_media_map.items())[:5]):
            print(f"  {i+1}. {card_name} -> {media_path}")
        
        print("\n✅ Обновление завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Отключаемся от базы данных
        await db.disconnect()
        print("🔌 Отключение от базы данных")


if __name__ == "__main__":
    asyncio.run(update_card_media())
