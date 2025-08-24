#!/usr/bin/env python3
"""
Простой скрипт для переключения на БД 'pratki'
"""

import os
import sys
from pathlib import Path
from loguru import logger


def switch_db():
    """Переключение на БД pratki"""
    try:
        # Путь к .env файлу
        env_file = Path(__file__).parent.parent / ".env"
        
        if not env_file.exists():
            logger.error("❌ Файл .env не найден!")
            return False
        
        # Читаем файл
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Заменяем DATABASE_NAME
        if 'DATABASE_NAME=' in content:
            content = content.replace('DATABASE_NAME=pratki_bot_new', 'DATABASE_NAME=pratki')
            content = content.replace('DATABASE_NAME=pratki_bot', 'DATABASE_NAME=pratki')
        else:
            content += '\nDATABASE_NAME=pratki'
        
        # Записываем обратно
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ БД переключена на 'pratki'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    logger.info("🔄 Переключение на БД 'pratki'...")
    if switch_db():
        logger.info("✅ Готово! Теперь запускайте бота")
    else:
        logger.error("❌ Не удалось переключить БД")
