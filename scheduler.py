"""
Zamanlayici - Saatlik hatirlatmalar ve kullanici tanimli hatirlatmalar icin APScheduler
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
from config import REMINDER_START_HOUR, REMINDER_END_HOUR, REMINDER_ENABLED
import database
from ai_service import format_reminder_message, format_reminder_notification
import os

scheduler = AsyncIOScheduler()
bot_application = None


def set_bot_application(app):
    """Bot application'i set et"""
    global bot_application
    bot_application = app


async def send_reminders():
    """Tum kullanicilara tamamlanmamis aliskanliklar icin hatirlatma gonder"""
    if not REMINDER_ENABLED:
        return
    
    current_hour = datetime.now().hour
    if current_hour < REMINDER_START_HOUR or current_hour >= REMINDER_END_HOUR:
        return
    
    if not bot_application:
        print("Bot application henuz set edilmedi")
        return
    
    users = database.get_all_users_with_uncompleted_habits()
    
    for user in users:
        try:
            uncompleted = database.get_uncompleted_habits_for_user(user['id'])
            
            if uncompleted:
                message = format_reminder_message(uncompleted)
                if message:
                    await bot_application.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                    print(f"Hatirlatma gonderildi: {user['telegram_id']}")
        except Exception as e:
            print(f"Hatirlatma gonderilemedi ({user['telegram_id']}): {e}")


async def check_user_reminders():
    """Kullanici tanimli hatirlatmalari kontrol et ve gonder"""
    if not bot_application:
        return
    
    current_time = datetime.now().strftime("%H:%M")
    pending_reminders = database.get_pending_reminders(current_time)
    
    for reminder in pending_reminders:
        try:
            message = format_reminder_notification(reminder)
            await bot_application.bot.send_message(
                chat_id=reminder['telegram_id'],
                text=message,
                parse_mode='Markdown'
            )
            print(f"Kullanici hatirlatmasi gonderildi: {reminder['telegram_id']} - {reminder['title']}")
            
            database.mark_reminder_sent(reminder['id'], reminder.get('is_recurring', False))
            
        except Exception as e:
            print(f"Kullanici hatirlatmasi gonderilemedi ({reminder['telegram_id']}): {e}")


async def reset_recurring_reminders():
    """Gece yarisi tekrarlayan hatirlatmalari sifirla"""
    database.reset_daily_reminders()
    print("Tekrarlayan hatirlatmalar sifirlandi")


def start_scheduler():
    """Zamanlayiciyi baslat"""
    
    scheduler.add_job(
        send_reminders,
        CronTrigger(minute=0),
        id='hourly_reminder',
        replace_existing=True
    )
    
    scheduler.add_job(
        check_user_reminders,
        CronTrigger(second=0),
        id='user_reminders',
        replace_existing=True
    )
    
    scheduler.add_job(
        reset_recurring_reminders,
        CronTrigger(hour=0, minute=0),
        id='reset_reminders',
        replace_existing=True
    )
    
    scheduler.start()
    print("Hatirlatma zamanlayicisi baslatildi")


def stop_scheduler():
    """Zamanlayiciyi durdur"""
    scheduler.shutdown()
    print("Hatirlatma zamanlayicisi durduruldu")
