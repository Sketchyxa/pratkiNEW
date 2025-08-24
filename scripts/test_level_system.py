#!/usr/bin/env python3
"""
Скрипт для тестирования новой системы уровней
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User

def test_level_system():
    """Тестирует новую систему уровней"""
    print("🔧 Тестирование новой системы уровней...\n")
    
    # Создаем тестового пользователя
    test_user = User(telegram_id=123456789)
    
    print("📊 Таблица уровней:")
    print("Уровень | Опыт для уровня | Опыт до следующего")
    print("-" * 50)
    
    for level in range(1, 21):  # Показываем первые 20 уровней
        exp_for_level = test_user.get_experience_for_level(level)
        exp_to_next = test_user.get_experience_for_level(level + 1) - exp_for_level if level < 20 else 0
        
        print(f"{level:7d} | {exp_for_level:14d} | {exp_to_next:16d}")
    
    print("\n" + "="*50)
    print("🧪 Тестирование расчета уровней:")
    
    test_experiences = [0, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    
    for exp in test_experiences:
        test_user.experience = exp
        level = test_user.calculate_level()
        exp_to_next = test_user.get_experience_to_next_level()
        
        print(f"Опыт: {exp:6d} → Уровень: {level:2d} (до следующего: {exp_to_next:5d})")
    
    print("\n" + "="*50)
    print("📈 Сравнение со старой системой:")
    print("Опыт | Старая система | Новая система | Разница")
    print("-" * 55)
    
    for exp in [100, 500, 1000, 2000, 5000, 10000]:
        # Старая система: каждые 100 опыта = новый уровень
        old_level = max(1, exp // 100 + 1)
        
        # Новая система
        test_user.experience = exp
        new_level = test_user.calculate_level()
        
        diff = old_level - new_level
        print(f"{exp:5d} | {old_level:13d} | {new_level:13d} | {diff:+6d}")

if __name__ == "__main__":
    test_level_system()
