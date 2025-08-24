import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger
import mysql.connector
import pandas as pd

from database.connection import db
from models.user import User, UserCard
from models.card import Card
from services.user_service import user_service
from services.card_service import card_service
from config import settings


class MigrationService:
    """Сервис для миграции данных из MySQL в MongoDB"""
    
    def __init__(self):
        self.mysql_connection = None
    
    async def connect_mysql(self) -> bool:
        """Подключение к MySQL"""
        try:
            self.mysql_connection = mysql.connector.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset='utf8mb4'
            )
            logger.info("Connected to MySQL successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False
    
    def disconnect_mysql(self):
        """Отключение от MySQL"""
        if self.mysql_connection:
            self.mysql_connection.close()
            self.mysql_connection = None
            logger.info("Disconnected from MySQL")
    
    async def import_mysql_dump(self, dump_file_path: str) -> Dict[str, Any]:
        """
        Импорт MySQL дампа в MongoDB
        Возвращает статистику импорта
        """
        try:
            logger.info(f"Starting MySQL dump import from {dump_file_path}")
            
            # Читаем дамп файл
            with open(dump_file_path, 'r', encoding='utf-8') as file:
                dump_content = file.read()
            
            # Парсим SQL команды
            sql_commands = self._parse_sql_dump(dump_content)
            
            stats = {
                "users_imported": 0,
                "cards_imported": 0,
                "user_cards_imported": 0,
                "errors": []
            }
            
            # Импортируем данные
            for command in sql_commands:
                if command['type'] == 'INSERT':
                    await self._process_insert_command(command, stats)
            
            logger.info(f"Import completed. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error importing MySQL dump: {e}")
            return {"error": str(e)}
    
    def _parse_sql_dump(self, dump_content: str) -> List[Dict[str, Any]]:
        """Парсинг SQL дампа"""
        commands = []
        
        # Регулярные выражения для поиска INSERT команд
        insert_pattern = r"INSERT INTO\s+`?(\w+)`?\s*\(([^)]+)\)\s*VALUES\s*(.+?);"
        
        matches = re.findall(insert_pattern, dump_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            table_name = match[0]
            columns = [col.strip().strip('`') for col in match[1].split(',')]
            values_part = match[2]
            
            # Парсим значения (упрощенный парсер)
            values_rows = self._parse_values(values_part)
            
            commands.append({
                'type': 'INSERT',
                'table': table_name,
                'columns': columns,
                'values': values_rows
            })
        
        return commands
    
    def _parse_values(self, values_part: str) -> List[List[str]]:
        """Парсинг VALUES части SQL команды"""
        rows = []
        
        # Простой парсер для VALUES
        # Убираем лишние пробелы и переносы строк
        values_part = re.sub(r'\s+', ' ', values_part.strip())
        
        # Находим все группы значений в скобках
        value_groups = re.findall(r'\(([^)]+)\)', values_part)
        
        for group in value_groups:
            # Разбиваем значения по запятым
            values = []
            current_value = ""
            in_quotes = False
            quote_char = None
            
            for char in group:
                if char in ['"', "'"] and not in_quotes:
                    in_quotes = True
                    quote_char = char
                    current_value += char
                elif char == quote_char and in_quotes:
                    in_quotes = False
                    quote_char = None
                    current_value += char
                elif char == ',' and not in_quotes:
                    values.append(current_value.strip())
                    current_value = ""
                else:
                    current_value += char
            
            if current_value:
                values.append(current_value.strip())
            
            rows.append(values)
        
        return rows
    
    async def _process_insert_command(self, command: Dict[str, Any], stats: Dict[str, Any]):
        """Обработка INSERT команды"""
        try:
            table_name = command['table'].lower()
            
            if table_name == 'users':
                await self._import_users(command, stats)
            elif table_name == 'cards':
                await self._import_cards(command, stats)
            elif table_name in ['user_cards', 'user_collection']:
                await self._import_user_cards(command, stats)
            else:
                logger.warning(f"Unknown table: {table_name}")
                
        except Exception as e:
            error_msg = f"Error processing INSERT for table {command['table']}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
    
    async def _import_users(self, command: Dict[str, Any], stats: Dict[str, Any]):
        """Импорт пользователей"""
        columns = command['columns']
        
        for row in command['values']:
            try:
                user_data = dict(zip(columns, row))
                
                # Очищаем данные
                telegram_id = int(self._clean_value(user_data.get('telegram_id', '0')))
                username = self._clean_value(user_data.get('username', ''))
                first_name = self._clean_value(user_data.get('first_name', ''))
                last_name = self._clean_value(user_data.get('last_name', ''))
                experience = int(self._clean_value(user_data.get('experience', '0')))
                level = int(self._clean_value(user_data.get('level', '1')))
                
                # Проверяем, существует ли пользователь
                existing_user = await user_service.get_user_by_telegram_id(telegram_id)
                if existing_user:
                    logger.info(f"User {telegram_id} already exists, skipping")
                    continue
                
                # Создаем пользователя
                user = await user_service.create_user(
                    telegram_id=telegram_id,
                    username=username if username else None,
                    first_name=first_name if first_name else None,
                    last_name=last_name if last_name else None
                )
                
                # Обновляем опыт и уровень
                if experience > 0:
                    user.experience = experience
                    user.level = level
                    await user_service.update_user(user)
                
                stats['users_imported'] += 1
                
            except Exception as e:
                error_msg = f"Error importing user: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
    
    async def _import_cards(self, command: Dict[str, Any], stats: Dict[str, Any]):
        """Импорт карточек"""
        columns = command['columns']
        
        for row in command['values']:
            try:
                card_data = dict(zip(columns, row))
                
                # Очищаем данные
                name = self._clean_value(card_data.get('name', ''))
                description = self._clean_value(card_data.get('description', ''))
                rarity = self._clean_value(card_data.get('rarity', 'common'))
                image_url = self._clean_value(card_data.get('image_url', ''))
                gif_url = self._clean_value(card_data.get('gif_url', ''))
                video_url = self._clean_value(card_data.get('video_url', ''))
                
                if not name:
                    continue
                
                # Проверяем, существует ли карточка
                existing_card = await card_service.get_card_by_name(name)
                if existing_card:
                    logger.info(f"Card {name} already exists, skipping")
                    continue
                
                # Создаем карточку
                card = await card_service.create_card(
                    name=name,
                    description=description,
                    rarity=rarity,
                    image_url=image_url if image_url else None,
                    gif_url=gif_url if gif_url else None,
                    video_url=video_url if video_url else None
                )
                
                if card:
                    stats['cards_imported'] += 1
                
            except Exception as e:
                error_msg = f"Error importing card: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
    
    async def _import_user_cards(self, command: Dict[str, Any], stats: Dict[str, Any]):
        """Импорт коллекций пользователей"""
        columns = command['columns']
        
        for row in command['values']:
            try:
                user_card_data = dict(zip(columns, row))
                
                telegram_id = int(self._clean_value(user_card_data.get('telegram_id', '0')))
                card_name = self._clean_value(user_card_data.get('card_name', ''))
                quantity = int(self._clean_value(user_card_data.get('quantity', '1')))
                
                if not card_name or telegram_id == 0:
                    continue
                
                # Находим пользователя и карточку
                user = await user_service.get_user_by_telegram_id(telegram_id)
                card = await card_service.get_card_by_name(card_name)
                
                if not user or not card:
                    logger.warning(f"User {telegram_id} or card {card_name} not found")
                    continue
                
                # Добавляем карточку пользователю
                await user_service.add_card_to_user(user, str(card.id), quantity)
                await card_service.update_card_stats(card.name, quantity, 1)
                
                stats['user_cards_imported'] += 1
                
            except Exception as e:
                error_msg = f"Error importing user card: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
    
    def _clean_value(self, value: str) -> str:
        """Очистка значения от кавычек и NULL"""
        if not value or value.upper() == 'NULL':
            return ''
        
        # Убираем кавычки
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        
        # Убираем экранирование
        value = value.replace('\\"', '"').replace("\\'", "'")
        
        return value.strip()
    
    async def import_json_cards(self, json_file_path: str) -> Dict[str, Any]:
        """
        Импорт карточек из JSON файла (как в оригинальном боте)
        """
        try:
            logger.info(f"Starting JSON cards import from {json_file_path}")
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                cards_data = json.load(file)
            
            stats = {
                "cards_imported": 0,
                "cards_updated": 0,
                "errors": []
            }
            
            for card_data in cards_data:
                try:
                    name = card_data.get('name', '')
                    description = card_data.get('description', '')
                    rarity = card_data.get('rarity', 'common')
                    image_url = card_data.get('image_url', '')
                    gif_url = card_data.get('gif_url', '')
                    video_url = card_data.get('video_url', '')
                    tags = card_data.get('tags', [])
                    
                    if not name:
                        continue
                    
                    # Проверяем, существует ли карточка
                    existing_card = await card_service.get_card_by_name(name)
                    
                    if existing_card:
                        # Обновляем существующую карточку
                        existing_card.description = description
                        existing_card.rarity = rarity
                        existing_card.image_url = image_url if image_url else None
                        existing_card.gif_url = gif_url if gif_url else None
                        existing_card.video_url = video_url if video_url else None
                        existing_card.tags = tags
                        
                        if await card_service.update_card(existing_card):
                            stats['cards_updated'] += 1
                    else:
                        # Создаем новую карточку
                        card = await card_service.create_card(
                            name=name,
                            description=description,
                            rarity=rarity,
                            image_url=image_url if image_url else None,
                            gif_url=gif_url if gif_url else None,
                            video_url=video_url if video_url else None,
                            tags=tags
                        )
                        
                        if card:
                            stats['cards_imported'] += 1
                
                except Exception as e:
                    error_msg = f"Error processing card {card_data.get('name', 'unknown')}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            logger.info(f"JSON import completed. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error importing JSON cards: {e}")
            return {"error": str(e)}


# Глобальный экземпляр сервиса
migration_service = MigrationService()
