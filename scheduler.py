"""
Zamanlayıcı - Saatlik hatırlatmalar ve kullanıcı tanımlı hatırlatmalar için APScheduler
Tüm modüller için merkezi hatırlatma sistemi
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import timedelta
from config import REMINDER_START_HOUR, REMINDER_END_HOUR, REMINDER_ENABLED, TIMEZONE
import database
import time_utils
from ai_service import format_reminder_message, format_reminder_notification
import os
import logging
import pytz

# Logging
logger = logging.getLogger(__name__)

# Global scheduler - Timezone ayarlı
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# Bot instance (bot.py'den set edilecek)
bot_application = None


def set_bot_application(app):
    """Bot application'ı set et"""
    global bot_application
    bot_application = app


async def send_reminders():
    """Tüm kullanıcılara tamamlanmamış alışkanlıklar için hatırlatma gönder (Kullanıcı saatine göre)"""
    if not REMINDER_ENABLED:
        return
    
    if not bot_application:
        logger.warning("Bot application henüz set edilmedi")
        return
    
    users = database.get_all_users()
    
    for user in users:
        try:
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            # Kullanıcının saati hatırlatma aralığında mı?
            if user_now.hour < REMINDER_START_HOUR or user_now.hour >= REMINDER_END_HOUR:
                continue

            # Bu kullanıcının tamamlanmamış alışkanlıklarını kontrol et
            uncompleted = database.get_uncompleted_habits_for_user(user['id'])
            
            if uncompleted:
                message = format_reminder_message(uncompleted)
                if message:
                    await bot_application.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Hatırlatma gönderildi: {user['telegram_id']}")
        except Exception as e:
            logger.error(f"Hatırlatma gönderilemedi ({user.get('telegram_id')}): {e}")


async def check_user_reminders():
    """Kullanıcı tanımlı hatırlatmaları kontrol et ve gönder (Kullanıcı bazlı)"""
    if not bot_application:
        return
    
    users = database.get_all_users()
    
    for user in users:
        try:
            user_id = user['id']
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            user_time_str = user_now.strftime("%H:%M")
            user_date_str = user_now.date().isoformat()
            
            # Bu kullanıcı için o anki saatte gönderilmesi gereken hatırlatmaları bul
            pending_reminders = database.get_pending_reminders_for_user(user_id, user_time_str, user_date_str)
            
            for reminder in pending_reminders:
                try:
                    message = format_reminder_notification(reminder)
                    await bot_application.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Kullanıcı hatırlatması gönderildi: {user['telegram_id']} - {reminder['title']}")
                    
                    # Hatırlatmayı işaretle veya sil
                    database.mark_reminder_sent(reminder['id'], reminder.get('is_recurring', False))
                    
                except Exception as e:
                    logger.error(f"Kullanıcı hatırlatması gönderilemedi ({user['telegram_id']}): {e}")
                    
        except Exception as e:
            logger.error(f"Kullanıcı kontrol döngüsü hatası (user {user.get('id')}): {e}")


async def reset_recurring_reminders():
    """Gece yarısı tekrarlayan hatırlatmaları sıfırla"""
    database.reset_daily_reminders()
    logger.info("Tekrarlayan hatırlatmalar sıfırlandı")


# ==================== DERS MODÜLÜ HATIRLATMALARI ====================

async def homework_deadline_reminder():
    """DERS MODÜLÜ: Ödev teslim hatırlatması - Her gün 18:00 (Kullanıcı saatine göre)"""
    if not bot_application:
        return

    import sqlite3
    ders_db = os.path.join(os.path.dirname(__file__), 'modules', 'ders', 'ders.db')

    try:
        conn = sqlite3.connect(ders_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        users = database.get_all_users()

        for user in users:
            # Kullanıcı saati kontrolü
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            # Sadece saat 18'de gönder
            if user_now.hour != 18 or user_now.minute != 0:
                continue

            user_tg_id = user['telegram_id']
            today = user_now.date()
            tomorrow = today + timedelta(days=1)
            next_3_days = today + timedelta(days=3)

            # Yarın ve 3 gün içinde teslim edilecek ödevleri al
            cursor.execute("""
                SELECT h.*, l.ders_adi
                FROM homeworks h
                LEFT JOIN lessons l ON h.lesson_id = l.id
                WHERE h.user_id = ?
                AND h.tamamlandi = 0
                AND h.bitis_tarihi BETWEEN ? AND ?
                ORDER BY h.bitis_tarihi ASC
            """, (user_tg_id, today.isoformat(), next_3_days.isoformat()))

            homeworks = cursor.fetchall()

            if homeworks:
                urgent_hw = []
                upcoming_hw = []

                for hw in homeworks:

                    # sqlite'dan gelen tarih string formatında (YYYY-MM-DD)
                    try:
                        y, m, d = map(int, hw['bitis_tarihi'].split('-'))
                        hw_date = today.replace(year=y, month=m, day=d)
                    except:
                        continue
                        
                    ders_adi = hw['ders_adi'] or "Genel"

                    if hw_date == today:
                        urgent_hw.append(f"🔴 **{hw['baslik']}** ({ders_adi}) - BUGÜN!")
                    elif hw_date == tomorrow:
                        urgent_hw.append(f"🟠 **{hw['baslik']}** ({ders_adi}) - Yarın")
                    else:
                        days_left = (hw_date - today).days
                        upcoming_hw.append(f"🟡 **{hw['baslik']}** ({ders_adi}) - {days_left} gün kaldı")

                message_parts = ["📚 *DERS MODÜLÜ: Ödev Hatırlatması*\n"]

                if urgent_hw:
                    message_parts.append("⚠️ *ACİL ÖDEVLER:*")
                    message_parts.extend(urgent_hw)
                    message_parts.append("")

                if upcoming_hw:
                    message_parts.append("📋 *Yaklaşan Ödevler:*")
                    message_parts.extend(upcoming_hw)

                message_parts.append("\n💪 Ödevleri tamamlamak için `/ders` modülüne geç!")

                try:
                    await bot_application.bot.send_message(
                        chat_id=user_tg_id,
                        text="\n".join(message_parts),
                        parse_mode='Markdown'
                    )
                    logger.info(f"Ödev hatırlatma gönderildi: {user_tg_id}")
                except Exception as e:
                    logger.error(f"Ödev hatırlatma hatası (user {user_tg_id}): {e}")

        conn.close()
    except Exception as e:
        logger.error(f"Ödev hatırlatma genel hata: {e}")


async def lesson_start_reminder():
    """DERS MODÜLÜ: Ders başlangıç hatırlatması - Her 15 dakikada bir kontrol"""
    if not bot_application:
        return

    import sqlite3
    ders_db = os.path.join(os.path.dirname(__file__), 'modules', 'ders', 'ders.db')
    
    gun_map = {
        0: 'pazartesi', 1: 'sali', 2: 'carsamba',
        3: 'persembe', 4: 'cuma', 5: 'cumartesi', 6: 'pazar'
    }

    try:
        conn = sqlite3.connect(ders_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        users = database.get_all_users()

        for user in users:
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            # Saati kontrol et: Sadece 7-22 arası
            if not (7 <= user_now.hour <= 22):
                continue
                
            current_day = gun_map[user_now.weekday()]
            
            # 15 dakika sonrası
            check_time = (user_now + timedelta(minutes=15)).strftime("%H:%M")

            user_tg_id = user['telegram_id']

            # Bu saatte dersi var mı kontrol et
            cursor.execute("""
                SELECT s.*, l.ders_adi, l.ogretmen
                FROM schedule s
                JOIN lessons l ON s.lesson_id = l.id
                WHERE s.user_id = ? AND s.gun = ? AND s.baslangic_saati = ?
            """, (user_tg_id, current_day, check_time))

            lesson = cursor.fetchone()

            if lesson:
                try:
                    await bot_application.bot.send_message(
                        chat_id=user_tg_id,
                        text=f"📚 *DERS HATIRLATMA*\n\n"
                             f"⏰ 15 dakika sonra dersin başlıyor!\n\n"
                             f"📖 **{lesson['ders_adi']}**\n"
                             f"🕐 Saat: {lesson['baslangic_saati']} - {lesson['bitis_saati']}\n"
                             f"👨‍🏫 Öğretmen: {lesson['ogretmen'] or '-'}\n\n"
                             f"Hazırlan! 💪",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Ders hatırlatma gönderildi: {user_tg_id} - {lesson['ders_adi']}")
                except Exception as e:
                    logger.error(f"Ders hatırlatma hatası: {e}")

        conn.close()
    except Exception as e:
        logger.error(f"Ders hatırlatma genel hata: {e}")


# ==================== İNGİLİZCE MODÜLÜ HATIRLATMALARI ====================

async def vocabulary_review_reminder():
    """İNGİLİZCE MODÜLÜ: Kelime tekrar hatırlatması - Her gün 10:00 (Kullanıcı saati)"""
    if not bot_application:
        return

    import sqlite3
    ingilizce_db = os.path.join(os.path.dirname(__file__), 'modules', 'ingilizce', 'ingilizce.db')

    try:
        conn = sqlite3.connect(ingilizce_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        users = database.get_all_users()

        for user in users:
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            if user_now.hour != 10 or user_now.minute != 0:
                continue

            user_tg_id = user['telegram_id']
            today_str = user_now.date().isoformat()

            # Bugün tekrar edilmesi gereken kelimeleri al
            cursor.execute("""
                SELECT COUNT(*) as count FROM words
                WHERE user_id = ?
                AND durum = 'ogreniyor'
                AND next_review <= ?
            """, (user_tg_id, today_str))

            result = cursor.fetchone()
            review_count = result['count'] if result else 0

            if review_count > 0:
                # Günlük hedefi kontrol et
                cursor.execute("""
                    SELECT gunluk_kelime_sayisi FROM daily_goals
                    WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (user_tg_id,))

                goal_result = cursor.fetchone()
                goal_text = ""
                if goal_result:
                    goal_text = f"\n🎯 Günlük Hedefin: {goal_result['gunluk_kelime_sayisi']} kelime"

                try:
                    await bot_application.bot.send_message(
                        chat_id=user_tg_id,
                        text=f"🇬🇧 *İNGİLİZCE: Tekrar Zamanı!*\n\n"
                             f"📚 Bugün **{review_count} kelime** tekrar bekliyor!\n"
                             f"{goal_text}\n\n"
                             f"Tekrar için `/ingilizce` modülüne geç ve:\n"
                             f"• 'Tekrar edilecek kelimeleri göster'\n\n"
                             f"🧠 Spaced Repetition ile öğrenme kalıcı olur!",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Kelime tekrar hatırlatma gönderildi: {user_tg_id}")
                except Exception as e:
                    logger.error(f"Kelime tekrar hatırlatma hatası (user {user_tg_id}): {e}")

        conn.close()
    except Exception as e:
        logger.error(f"Kelime tekrar hatırlatma genel hata: {e}")


async def daily_word_goal_reminder():
    """İNGİLİZCE MODÜLÜ: Günlük kelime hedefi hatırlatması - Her gün 20:00"""
    if not bot_application:
        return

    import sqlite3
    ingilizce_db = os.path.join(os.path.dirname(__file__), 'modules', 'ingilizce', 'ingilizce.db')

    try:
        conn = sqlite3.connect(ingilizce_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        users = database.get_all_users()

        for user in users:
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            if user_now.hour != 20 or user_now.minute != 0:
                continue

            user_tg_id = user['telegram_id']
            today_str = user_now.date().isoformat()

            cursor.execute("""
                SELECT gunluk_kelime_sayisi FROM daily_goals
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_tg_id,))

            goal_result = cursor.fetchone()

            if goal_result:
                goal = goal_result['gunluk_kelime_sayisi']

                # Bugün öğrenilen kelime sayısı
                cursor.execute("""
                    SELECT COUNT(*) as count FROM words
                    WHERE user_id = ? AND DATE(learn_date) = ?
                """, (user_tg_id, today_str))

                learned = cursor.fetchone()['count']

                if learned < goal:
                    remaining = goal - learned
                    try:
                        await bot_application.bot.send_message(
                            chat_id=user_tg_id,
                            text=f"🇬🇧 *İNGİLİZCE: Günlük Hedef Hatırlatması*\n\n"
                                 f"🎯 Günlük Hedef: {goal} kelime\n"
                                 f"✅ Öğrenilen: {learned} kelime\n"
                                 f"⏳ Kalan: **{remaining} kelime**\n\n"
                                 f"Gün bitmeden hedefini tamamla! 💪\n"
                                 f"`/ingilizce` modülüne geç!",
                            parse_mode='Markdown'
                        )
                        logger.info(f"Günlük hedef hatırlatma gönderildi: {user_tg_id}")
                    except Exception as e:
                        logger.error(f"Günlük hedef hatırlatma hatası: {e}")

        conn.close()
    except Exception as e:
        logger.error(f"Günlük hedef hatırlatma genel hata: {e}")


# ==================== NOT DEFTERİ MODÜLÜ HATIRLATMALARI ====================

async def daily_journal_reminder():
    """NOT DEFTERİ HATIRLATMA: Günlük yazma - Her gün 21:30 (sadece yazmayanlar)"""
    if not bot_application:
        return
    
    import sqlite3
    notdefteri_db = os.path.join(os.path.dirname(__file__), 'modules', 'notdefteri', 'notdefteri.db')
    
    try:
        conn = sqlite3.connect(notdefteri_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        users = database.get_all_users()
        
        for user in users:
            user_tz = user.get('timezone', TIMEZONE)
            user_now = time_utils.get_user_now(user_tz)
            
            if user_now.hour != 21 or user_now.minute != 30:
                continue

            user_tg_id = user['telegram_id']
            today_str = user_now.date().isoformat()
            
            # Bugün günlük yazdı mı kontrol et
            cursor.execute("""
                SELECT COUNT(*) as count FROM notes
                WHERE user_id = ? 
                AND kategori_path LIKE '%Günlük%'
                AND DATE(created_at) = ?
            """, (user_tg_id, today_str))
            
            result = cursor.fetchone()
            
            # Eğer bugün günlük yazmadıysa hatırlat
            if result and result['count'] == 0:
                try:
                    await bot_application.bot.send_message(
                        chat_id=user_tg_id,
                        text=f"📔 *NOT DEFTERİ HATIRLATMA: Günlük Zamanı!*\n\n"
                             f"🌙 Bugün henüz günlük yazmadın.\n\n"
                             f"Günlüğünü yazmak için `/notdefteri` modülüne geç:\n"
                             f"• 'Günlük kategorisinde not: Bugün...'\n\n"
                             f"💭 Bugünü değerlendir, düşüncelerini paylaş!",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Günlük hatırlatma gönderildi: {user_tg_id}")
                except Exception as e:
                    logger.error(f"Günlük hatırlatma hatası (user {user_tg_id}): {e}")
        
        conn.close()
    except Exception as e:
        logger.error(f"Günlük hatırlatma genel hata: {e}")


def start_scheduler():
    """Zamanlayıcıyı başlat - Tüm modüller için merkezi hatırlatma sistemi"""
    
    logger.info(f"Zamanlayıcı başlatılıyor. Server Timezone: {TIMEZONE}")

    # Not: CronTrigger'ları "her dakika" çalışacak şekilde ayarlıyoruz.
    # Çünkü her kullanıcının saati farklı olabilir, bu yüzden dakikada bir kontrol edip
    # "Kullanıcının saati X mi?" diye bakmamız lazım.
    
    # 1. Her Dakika Kontrol Edilecekler
    # - Alışkanlıklar (Saat başı mı kontrol edeceğiz? Evet, kullanıcının saat başıysa)
    # - Dersler (15 dk bir) -> Dakikalık kontrolde (dk % 15 == 0) bakılabilir
    # - Kullanıcı hatırlatmaları (Tam saatinde)
    # - Diğer günlük hatırlatmalar (Belirli saatlerde)

    # Performans için: Tek bir "master" job her dakika çalışıp hepsini tetikleyebilir.
    # Ama APScheduler ile ayrı joblar daha temiz.
    
    # Her dakika çalışıp, kullanıcının saatine göre işlem yapacak ana döngüler
    
    scheduler.add_job(
        check_user_reminders,
        CronTrigger(minute='*'), # Her dakika
        id='user_reminders',
        replace_existing=True
    )
    
    scheduler.add_job(
        send_reminders,
        CronTrigger(minute='0'), # Her saat başı
        id='hourly_habit_check',
        replace_existing=True
    )

    scheduler.add_job(
        lesson_start_reminder,
        args=[],
        trigger=CronTrigger(minute='0,15,30,45'),
        id='lesson_start',
        replace_existing=True
    )

    # Günlük modül hatırlatmaları için dakikalık kontrol (sadece saati gelenlere atacak)
    scheduler.add_job(homework_deadline_reminder, CronTrigger(minute='*'), id='hw_deadline', replace_existing=True)
    scheduler.add_job(vocabulary_review_reminder, CronTrigger(minute='*'), id='vocab_review', replace_existing=True)
    scheduler.add_job(daily_word_goal_reminder, CronTrigger(minute='*'), id='word_goal', replace_existing=True)
    scheduler.add_job(daily_journal_reminder, CronTrigger(minute='*'), id='journal_rem', replace_existing=True)

    # Gece yarısı reset (UTC 00:00'da çalışsa da olur, ama user bazlı değil global reset. Sorun olmaz)
    scheduler.add_job(
        reset_recurring_reminders,
        CronTrigger(hour=0, minute=0),
        id='reset_reminders',
        replace_existing=True
    )

    scheduler.start()
    logger.info("⏰ Hatırlatma zamanlayıcısı başlatıldı (User-Aware Loop)")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("⏰ Hatırlatma zamanlayıcısı durduruldu")
