// Инициализация базы данных для Pratki Bot
db = db.getSiblingDB('pratki');

// Создаем коллекции
db.createCollection('users');
db.createCollection('cards');
db.createCollection('achievements');
db.createCollection('events');

// Создаем индексы для оптимизации
db.users.createIndex({ "telegram_id": 1 }, { unique: true });
db.users.createIndex({ "username": 1 });
db.users.createIndex({ "level": -1 });
db.users.createIndex({ "experience": -1 });

db.cards.createIndex({ "card_id": 1 }, { unique: true });
db.cards.createIndex({ "rarity": 1 });
db.cards.createIndex({ "name": 1 });

db.achievements.createIndex({ "achievement_id": 1 }, { unique: true });
db.achievements.createIndex({ "category": 1 });

db.events.createIndex({ "event_id": 1 }, { unique: true });
db.events.createIndex({ "is_active": 1 });
db.events.createIndex({ "start_date": 1 });

print('База данных Pratki Bot инициализирована успешно!');
