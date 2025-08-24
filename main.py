import asyncio
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import settings
from database.connection import db
from handlers import (
    user_handlers, 
    admin_handlers, 
    bonus_handlers, 
    shop_handlers, 
    upgrade_handlers, 
    nft_handlers, 
    suggestion_handlers,
    achievement_handlers,
    event_handlers,
    notify_handlers,
    battle_handlers,
    easter_egg_handlers
)
from middleware.rate_limiter import rate_limiter


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Starting Pratki Card Bot...")
    
    # Подключаемся к MongoDB
    await db.connect()
    
    # Сбрасываем rate limits при запуске
    from middleware.rate_limiter import rate_limiter
    rate_limiter.reset_all_limits()
    logger.info("Rate limits reset on startup")
    
    # Создаем стандартные достижения
    from services.achievement_service import achievement_service
    await achievement_service.create_default_achievements()
    
    logger.info("Bot startup completed")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Shutting down Pratki Card Bot...")
    
    # Отключаемся от MongoDB
    await db.disconnect()
    logger.info("Bot shutdown completed")


async def main():
    """Главная функция запуска бота"""
    # Настраиваем логирование
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    if settings.debug:
        logger.add("logs/bot.log", rotation="1 day", retention="7 days", level="DEBUG")
    
    logger.info("Initializing bot...")
    
    # Создаем бота и диспетчер
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="Markdown"))
    
    dp = Dispatcher()
    
    # Инициализируем сервис уведомлений
    from services.notification_service import notification_service
    notification_service.set_bot(bot)
    logger.info("Notification service initialized")
    
    # Подключаем middleware
    dp.message.middleware(rate_limiter)
    dp.callback_query.middleware(rate_limiter)
    
    # Подключаем хэндлеры
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(bonus_handlers.router)
    dp.include_router(shop_handlers.router)
    dp.include_router(upgrade_handlers.router)
    dp.include_router(nft_handlers.router)
    dp.include_router(suggestion_handlers.router)
    dp.include_router(achievement_handlers.router)
    dp.include_router(event_handlers.router)
    dp.include_router(notify_handlers.router)
    dp.include_router(battle_handlers.router)
    dp.include_router(easter_egg_handlers.router)
    
    # Регистрируем события запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        # Запускаем бота
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
