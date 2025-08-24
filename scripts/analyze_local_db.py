#!/usr/bin/env python3
"""
Скрипт для анализа локальной базы данных MongoDB
Запускайте этот скрипт на вашем ПК для просмотра содержимого базы
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger


async def analyze_database():
    """Анализ содержимого локальной базы данных"""
    try:
        logger.info("Starting database analysis...")
        
        # Подключение к локальной базе данных
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        
        # Получаем список всех баз данных
        databases = await client.list_database_names()
        logger.info(f"Available databases: {databases}")
        
        # Анализируем каждую базу данных
        for db_name in databases:
            if 'pratki' in db_name.lower():
                logger.info(f"\n=== Analyzing database: {db_name} ===")
                db = client[db_name]
                
                # Получаем список коллекций
                collections = await db.list_collection_names()
                logger.info(f"Collections in {db_name}: {collections}")
                
                # Анализируем каждую коллекцию
                for collection_name in collections:
                    collection = db[collection_name]
                    count = await collection.count_documents({})
                    logger.info(f"  {collection_name}: {count} documents")
                    
                    # Показываем пример документа
                    if count > 0:
                        sample = await collection.find_one()
                        if sample:
                            logger.info(f"    Sample document keys: {list(sample.keys())}")
                            
                            # Если это карточки, показываем несколько примеров
                            if collection_name == 'cards' and count > 0:
                                logger.info("    Sample cards:")
                                cards = await collection.find().limit(3).to_list(length=3)
                                for i, card in enumerate(cards, 1):
                                    name = card.get('name', 'Unknown')
                                    rarity = card.get('rarity', 'Unknown')
                                    logger.info(f"      {i}. {name} ({rarity})")
                            
                            # Если это пользователи, показываем статистику
                            elif collection_name == 'users' and count > 0:
                                logger.info("    User statistics:")
                                total_exp = await collection.aggregate([
                                    {"$group": {"_id": None, "total_exp": {"$sum": "$experience"}}}
                                ]).to_list(length=1)
                                if total_exp:
                                    logger.info(f"      Total experience: {total_exp[0]['total_exp']}")
                                
                                avg_level = await collection.aggregate([
                                    {"$group": {"_id": None, "avg_level": {"$avg": "$level"}}}
                                ]).to_list(length=1)
                                if avg_level:
                                    logger.info(f"      Average level: {avg_level[0]['avg_level']:.2f}")
        
        # Закрываем соединение
        client.close()
        
        logger.info("\n=== Database analysis completed ===")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


async def export_database_summary():
    """Экспорт краткой сводки базы данных"""
    try:
        logger.info("Exporting database summary...")
        
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        
        summary = {
            "exported_at": datetime.now().isoformat(),
            "databases": {}
        }
        
        databases = await client.list_database_names()
        
        for db_name in databases:
            if 'pratki' in db_name.lower():
                db = client[db_name]
                collections = await db.list_collection_names()
                
                summary["databases"][db_name] = {
                    "collections": {}
                }
                
                for collection_name in collections:
                    collection = db[collection_name]
                    count = await collection.count_documents({})
                    
                    summary["databases"][db_name]["collections"][collection_name] = {
                        "document_count": count
                    }
                    
                    # Добавляем пример документа
                    if count > 0:
                        sample = await collection.find_one()
                        if sample:
                            # Убираем _id и большие поля
                            sample.pop('_id', None)
                            if 'image_url' in sample:
                                sample['image_url'] = '...'
                            if 'gif_url' in sample:
                                sample['gif_url'] = '...'
                            if 'video_url' in sample:
                                sample['video_url'] = '...'
                            
                            summary["databases"][db_name]["collections"][collection_name]["sample_document"] = sample
        
        # Сохраняем сводку
        with open('database_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info("Database summary exported to database_summary.json")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise


async def main():
    """Главная функция"""
    try:
        await analyze_database()
        await export_database_summary()
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
