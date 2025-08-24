#!/usr/bin/env python3
"""
Скрипт для полного экспорта локальной базы данных MongoDB
Запускайте этот скрипт на вашем ПК для экспорта всех данных
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


async def export_database():
    """Полный экспорт базы данных"""
    try:
        logger.info("Starting full database export...")
        
        # Создаем директорию для экспорта
        export_dir = Path("local_db_export")
        export_dir.mkdir(exist_ok=True)
        
        # Подключение к локальной базе данных
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        
        # Получаем список всех баз данных
        databases = await client.list_database_names()
        logger.info(f"Available databases: {databases}")
        
        # Экспортируем каждую базу данных с 'pratki' в названии
        for db_name in databases:
            if 'pratki' in db_name.lower():
                logger.info(f"\n=== Exporting database: {db_name} ===")
                db = client[db_name]
                
                # Создаем поддиректорию для базы данных
                db_dir = export_dir / db_name
                db_dir.mkdir(exist_ok=True)
                
                # Получаем список коллекций
                collections = await db.list_collection_names()
                logger.info(f"Collections in {db_name}: {collections}")
                
                # Экспортируем каждую коллекцию
                for collection_name in collections:
                    collection = db[collection_name]
                    count = await collection.count_documents({})
                    logger.info(f"  Exporting {collection_name}: {count} documents")
                    
                    if count > 0:
                        # Получаем все документы
                        documents = await collection.find({}).to_list(length=None)
                        
                        # Подготавливаем данные для экспорта
                        export_data = []
                        for doc in documents:
                            # Конвертируем ObjectId в строку
                            if '_id' in doc:
                                doc['_id'] = str(doc['_id'])
                            
                            # Конвертируем datetime в строку
                            for key, value in doc.items():
                                if isinstance(value, datetime):
                                    doc[key] = value.isoformat()
                            
                            export_data.append(doc)
                        
                        # Сохраняем в JSON файл
                        output_file = db_dir / f"{collection_name}.json"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
                        
                        logger.info(f"    Exported to {output_file}")
                    else:
                        logger.info(f"    Collection {collection_name} is empty, skipping")
        
        # Создаем файл с информацией об экспорте
        export_info = {
            "exported_at": datetime.now().isoformat(),
            "databases_exported": [db for db in databases if 'pratki' in db.lower()],
            "total_databases": len([db for db in databases if 'pratki' in db.lower()])
        }
        
        with open(export_dir / "export_info.json", 'w', encoding='utf-8') as f:
            json.dump(export_info, f, ensure_ascii=False, indent=2, default=str)
        
        # Закрываем соединение
        client.close()
        
        logger.info(f"\n=== Database export completed! ===")
        logger.info(f"Export directory: {export_dir.absolute()}")
        logger.info(f"Files created:")
        for file_path in export_dir.rglob("*.json"):
            logger.info(f"  {file_path}")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise


async def main():
    """Главная функция"""
    try:
        await export_database()
    except KeyboardInterrupt:
        logger.info("Export interrupted by user")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
