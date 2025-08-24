# 🚀 Деплой Pratki Card Bot

## Варианты деплоя

### 1. Docker Compose (Рекомендуется)

#### Подготовка:
1. Установите Docker и Docker Compose
2. Скопируйте `env.example` в `.env` и заполните переменные:
```bash
cp env.example .env
```

3. Отредактируйте `.env`:
```env
BOT_TOKEN=ваш_токен_бота
ADMIN_USER_ID=ваш_telegram_id
```

#### Запуск:
```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down
```

### 2. VPS/Сервер

#### Требования:
- Ubuntu 20.04+ / CentOS 8+
- Python 3.11+
- MongoDB 7.0+
- 2GB RAM минимум

#### Установка:
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и зависимости
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Устанавливаем MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install mongodb-org -y
sudo systemctl start mongod
sudo systemctl enable mongod

# Клонируем проект
git clone <ваш_репозиторий>
cd pratkiNEW

# Создаем виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Настраиваем переменные окружения
cp env.example .env
nano .env  # Отредактируйте файл

# Запускаем бота
python main.py
```

### 3. Systemd Service (для VPS)

Создайте файл `/etc/systemd/system/pratki-bot.service`:
```ini
[Unit]
Description=Pratki Card Bot
After=network.target mongod.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/pratkiNEW
Environment=PATH=/path/to/pratkiNEW/venv/bin
ExecStart=/path/to/pratkiNEW/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pratki-bot
sudo systemctl start pratki-bot
sudo systemctl status pratki-bot
```

### 4. Облачные платформы

#### Railway:
1. Подключите GitHub репозиторий
2. Добавьте переменные окружения в настройках
3. Railway автоматически развернет приложение

#### Render:
1. Создайте новый Web Service
2. Подключите GitHub репозиторий
3. Укажите команду запуска: `python main.py`
4. Добавьте переменные окружения

#### Heroku:
1. Создайте `Procfile`:
```
worker: python main.py
```
2. Добавьте MongoDB addon
3. Настройте переменные окружения

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|---------|
| `BOT_TOKEN` | Токен вашего Telegram бота | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `ADMIN_USER_ID` | Ваш Telegram ID | `123456789` |
| `MONGODB_URL` | URL подключения к MongoDB | `mongodb://localhost:27017/pratki` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `DEBUG` | Режим отладки | `false` |

## Мониторинг и логи

### Docker:
```bash
# Логи бота
docker-compose logs -f bot

# Логи MongoDB
docker-compose logs -f mongo

# Статистика контейнеров
docker stats
```

### Systemd:
```bash
# Логи сервиса
sudo journalctl -u pratki-bot -f

# Статус сервиса
sudo systemctl status pratki-bot
```

## Резервное копирование

### MongoDB:
```bash
# Создание бэкапа
mongodump --db pratki --out /backup/$(date +%Y%m%d)

# Восстановление
mongorestore --db pratki /backup/20231201/pratki/
```

### Docker:
```bash
# Бэкап данных MongoDB
docker exec pratki_mongo mongodump --db pratki --out /data/backup

# Копирование бэкапа с контейнера
docker cp pratki_mongo:/data/backup ./backup
```

## Обновление бота

### Docker:
```bash
# Остановка
docker-compose down

# Обновление кода
git pull

# Пересборка и запуск
docker-compose up -d --build
```

### Systemd:
```bash
# Остановка сервиса
sudo systemctl stop pratki-bot

# Обновление кода
git pull

# Перезапуск
sudo systemctl start pratki-bot
```

## Устранение неполадок

### Бот не запускается:
1. Проверьте токен бота
2. Проверьте подключение к MongoDB
3. Просмотрите логи: `docker-compose logs bot`

### Проблемы с базой данных:
1. Проверьте статус MongoDB: `sudo systemctl status mongod`
2. Проверьте подключение: `mongo --eval "db.runCommand('ping')"`

### Высокое потребление ресурсов:
1. Проверьте логи на ошибки
2. Настройте rate limiting
3. Оптимизируйте запросы к базе данных
