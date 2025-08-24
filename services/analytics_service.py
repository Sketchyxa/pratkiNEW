from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from loguru import logger

from database.connection import db
from services.user_service import user_service
from services.card_service import card_service


class AnalyticsService:
    """Сервис для аналитики и статистики"""
    
    def __init__(self):
        self.stats_collection: AsyncIOMotorCollection = None
    
    async def get_stats_collection(self) -> AsyncIOMotorCollection:
        if self.stats_collection is None:
            self.stats_collection = db.get_collection("analytics_stats")
        return self.stats_collection
    
    async def get_general_stats(self) -> Dict[str, Any]:
        """Получает общую статистику бота"""
        try:
            # Получаем всех пользователей
            all_users = await user_service.get_all_users()
            total_users = len(all_users)
            
            if total_users == 0:
                return self._empty_stats()
            
            # Активные пользователи (заходили за последние 7 дней)
            week_ago = datetime.utcnow() - timedelta(days=7)
            active_users = [u for u in all_users if u.last_activity and u.last_activity > week_ago]
            active_count = len(active_users)
            
            # Новые пользователи (зарегистрированы за последние 7 дней)
            new_users = [u for u in all_users if u.created_at > week_ago]
            new_count = len(new_users)
            
            # Статистика по уровням
            level_stats = {}
            for user in all_users:
                level = user.level
                level_stats[level] = level_stats.get(level, 0) + 1
            
            # Экономическая статистика
            total_coins = sum(u.coins for u in all_users)
            total_experience = sum(u.experience for u in all_users)
            avg_coins = total_coins / total_users if total_users > 0 else 0
            avg_experience = total_experience / total_users if total_users > 0 else 0
            
            # Статистика карточек
            total_cards_owned = sum(u.total_cards for u in all_users)
            avg_cards = total_cards_owned / total_users if total_users > 0 else 0
            
            # Топ пользователи
            top_by_cards = sorted(all_users, key=lambda x: x.total_cards, reverse=True)[:5]
            top_by_level = sorted(all_users, key=lambda x: x.level, reverse=True)[:5]
            top_by_coins = sorted(all_users, key=lambda x: x.coins, reverse=True)[:5]
            
            return {
                "users": {
                    "total": total_users,
                    "active_7d": active_count,
                    "new_7d": new_count,
                    "active_percentage": round((active_count / total_users) * 100, 1),
                    "level_distribution": level_stats
                },
                "economy": {
                    "total_coins": total_coins,
                    "total_experience": total_experience,
                    "avg_coins": round(avg_coins, 1),
                    "avg_experience": round(avg_experience, 1)
                },
                "cards": {
                    "total_owned": total_cards_owned,
                    "avg_per_user": round(avg_cards, 1)
                },
                "top_users": {
                    "by_cards": [{"name": u.first_name or f"User{u.telegram_id}", "value": u.total_cards} for u in top_by_cards],
                    "by_level": [{"name": u.first_name or f"User{u.telegram_id}", "value": u.level} for u in top_by_level],
                    "by_coins": [{"name": u.first_name or f"User{u.telegram_id}", "value": u.coins} for u in top_by_coins]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting general stats: {e}")
            return self._empty_stats()
    
    async def get_card_stats(self) -> Dict[str, Any]:
        """Получает статистику по карточкам"""
        try:
            all_cards = await card_service.get_all_cards()
            
            if not all_cards:
                return {"total_cards": 0, "by_rarity": {}, "most_popular": [], "least_popular": []}
            
            # Статистика по редкости
            rarity_stats = {}
            for card in all_cards:
                rarity = card.rarity
                if rarity not in rarity_stats:
                    rarity_stats[rarity] = {"count": 0, "total_owned": 0, "total_owners": 0}
                
                rarity_stats[rarity]["count"] += 1
                rarity_stats[rarity]["total_owned"] += card.total_owned
                rarity_stats[rarity]["total_owners"] += card.unique_owners
            
            # Самые популярные карточки
            popular_cards = sorted(all_cards, key=lambda x: x.unique_owners, reverse=True)[:10]
            unpopular_cards = sorted(all_cards, key=lambda x: x.unique_owners)[:5]
            
            return {
                "total_cards": len(all_cards),
                "by_rarity": rarity_stats,
                "most_popular": [
                    {
                        "name": card.name,
                        "rarity": card.rarity,
                        "owners": card.unique_owners,
                        "total_owned": card.total_owned
                    } for card in popular_cards
                ],
                "least_popular": [
                    {
                        "name": card.name,
                        "rarity": card.rarity,
                        "owners": card.unique_owners,
                        "total_owned": card.total_owned
                    } for card in unpopular_cards
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting card stats: {e}")
            return {"total_cards": 0, "by_rarity": {}, "most_popular": [], "least_popular": []}
    
    async def get_activity_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает статистику активности за период"""
        try:
            all_users = await user_service.get_all_users()
            
            if not all_users:
                return {"daily_active": [], "registrations": [], "retention": {}}
            
            # Статистика по дням за последние N дней
            daily_stats = {}
            registration_stats = {}
            
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                date_key = date.strftime("%Y-%m-%d")
                daily_stats[date_key] = 0
                registration_stats[date_key] = 0
            
            # Считаем активных пользователей по дням
            for user in all_users:
                if user.last_activity:
                    activity_date = user.last_activity.strftime("%Y-%m-%d")
                    if activity_date in daily_stats:
                        daily_stats[activity_date] += 1
                
                reg_date = user.created_at.strftime("%Y-%m-%d")
                if reg_date in registration_stats:
                    registration_stats[reg_date] += 1
            
            # Retention анализ
            retention_7d = len([u for u in all_users if u.last_activity and 
                               u.last_activity > datetime.utcnow() - timedelta(days=7)])
            retention_30d = len([u for u in all_users if u.last_activity and 
                                u.last_activity > datetime.utcnow() - timedelta(days=30)])
            
            return {
                "daily_active": [{"date": date, "count": count} for date, count in daily_stats.items()],
                "registrations": [{"date": date, "count": count} for date, count in registration_stats.items()],
                "retention": {
                    "7d": retention_7d,
                    "30d": retention_30d,
                    "7d_percentage": round((retention_7d / len(all_users)) * 100, 1) if all_users else 0,
                    "30d_percentage": round((retention_30d / len(all_users)) * 100, 1) if all_users else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting activity stats: {e}")
            return {"daily_active": [], "registrations": [], "retention": {}}
    
    async def get_achievement_stats(self) -> Dict[str, Any]:
        """Получает статистику по достижениям"""
        try:
            from services.achievement_service import achievement_service
            
            all_achievements = await achievement_service.get_all_achievements()
            all_users = await user_service.get_all_users()
            
            if not all_achievements or not all_users:
                return {"total_achievements": 0, "completion_stats": {}}
            
            # Статистика по достижениям
            achievement_stats = {}
            for achievement in all_achievements:
                achievement_stats[achievement.name] = {
                    "total_earned": achievement.total_earned,
                    "completion_rate": round((achievement.total_earned / len(all_users)) * 100, 1),
                    "category": achievement.category,
                    "difficulty": achievement.difficulty,
                    "points": achievement.points
                }
            
            # Статистика по пользователям
            total_points = sum(u.achievement_points for u in all_users)
            avg_points = total_points / len(all_users) if all_users else 0
            
            # Топ по очкам достижений
            top_achievers = sorted(all_users, key=lambda x: x.achievement_points, reverse=True)[:10]
            
            return {
                "total_achievements": len(all_achievements),
                "achievements": achievement_stats,
                "user_stats": {
                    "total_points": total_points,
                    "avg_points": round(avg_points, 1),
                    "top_achievers": [
                        {
                            "name": u.first_name or f"User{u.telegram_id}",
                            "points": u.achievement_points,
                            "completed": len([a for a in u.achievements if a.is_completed])
                        } for u in top_achievers
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting achievement stats: {e}")
            return {"total_achievements": 0, "completion_stats": {}}
    
    async def save_daily_snapshot(self):
        """Сохраняет ежедневный снимок статистики"""
        try:
            stats = await self.get_general_stats()
            card_stats = await self.get_card_stats()
            
            snapshot = {
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "timestamp": datetime.utcnow(),
                "users": stats["users"],
                "economy": stats["economy"],
                "cards": stats["cards"],
                "total_cards_in_db": card_stats["total_cards"],
                "rarity_distribution": card_stats["by_rarity"]
            }
            
            collection = await self.get_stats_collection()
            
            # Удаляем старую запись за сегодня если есть
            await collection.delete_one({"date": snapshot["date"]})
            
            # Сохраняем новую
            await collection.insert_one(snapshot)
            
            logger.info(f"Daily snapshot saved for {snapshot['date']}")
            
        except Exception as e:
            logger.error(f"Error saving daily snapshot: {e}")
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Возвращает пустую статистику"""
        return {
            "users": {"total": 0, "active_7d": 0, "new_7d": 0, "active_percentage": 0, "level_distribution": {}},
            "economy": {"total_coins": 0, "total_experience": 0, "avg_coins": 0, "avg_experience": 0},
            "cards": {"total_owned": 0, "avg_per_user": 0},
            "top_users": {"by_cards": [], "by_level": [], "by_coins": []}
        }
    
    async def get_growth_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает статистику роста"""
        try:
            collection = await self.get_stats_collection()
            
            # Получаем исторические данные
            start_date = datetime.utcnow() - timedelta(days=days)
            historical_data = await collection.find({
                "timestamp": {"$gte": start_date}
            }).sort("timestamp", 1).to_list(length=None)
            
            if len(historical_data) < 2:
                return {"growth": {}, "trends": {}}
            
            # Сравниваем первую и последнюю точки
            first = historical_data[0]
            last = historical_data[-1]
            
            user_growth = last["users"]["total"] - first["users"]["total"]
            coins_growth = last["economy"]["total_coins"] - first["economy"]["total_coins"]
            cards_growth = last["cards"]["total_owned"] - first["cards"]["total_owned"]
            
            return {
                "period_days": days,
                "growth": {
                    "users": user_growth,
                    "coins": coins_growth,
                    "cards": cards_growth
                },
                "trends": {
                    "users_per_day": round(user_growth / days, 2),
                    "coins_per_day": round(coins_growth / days, 2),
                    "cards_per_day": round(cards_growth / days, 2)
                },
                "data_points": len(historical_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting growth stats: {e}")
            return {"growth": {}, "trends": {}}


# Глобальный экземпляр сервиса
analytics_service = AnalyticsService()
