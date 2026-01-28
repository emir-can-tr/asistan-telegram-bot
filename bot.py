"""
Kişisel Asistan Telegram Botu - Modüler Versiyon
Gemini AI destekli çoklu modül botu
"""
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import database
from config import TELEGRAM_BOT_TOKEN
import scheduler
import voice_service
import logging

# Logging konfigürasyonu
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Modülleri import et
from modules.asistan_bot import AsistanBot
from modules.ders_bot import DersBot
from modules.ingilizce_bot import IngilizceBot
from modules.kitap_bot import KitapBot
from modules.notdefteri_bot import NotDefteriBot
from modules.proje_bot import ProjeBot

# Modül instance'ları oluştur
modules = {
    'asistan': AsistanBot(),
    'ders': DersBot(),
    'ingilizce': IngilizceBot(),
    'kitap': KitapBot(),
    'notdefteri': NotDefteriBot(),
    'proje': ProjeBot()
}


# ==================== ANA MENÜ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlatma komutu - Ana menü"""
    user = update.effective_user
    
    # Kullanıcıyı veritabanına kaydet
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Timezone bilgisini al
    user_tz = db_user.get('timezone', 'Europe/Istanbul')
    
    welcome_message = f"""
🌟 *Merhaba {user.first_name}!*

Ben senin kişisel asistan botunun! Farklı modüllerle sana yardımcı olabilirim.

🕒 *Zaman Dilimi:* `{user_tz}`
Eğer bu yanlışsa: `/timezone Europe/Istanbul` şeklinde değiştirebilirsin.

*📱 Modüller:*

🤖 `/asistan` - Alışkanlık, hatırlatma, görev ve not yönetimi
📚 `/ders` - Ders programı ve ödev takibi
🇬🇧 `/ingilizce` - Kelime öğrenme ve pratik
📖 `/kitap` - Okuma listesi ve kitap notları
📔 `/notdefteri` - Gelişmiş not yönetimi
🚀 `/proje` - Proje yönetimi ve takip

*Nasıl Kullanılır?*
1. Kullanmak istediğin modülün komutunu yaz (örn: `/asistan`)
2. Modül aktif olduğunda mesaj yazarak kullanabilirsin
3. Başka modüle geçmek için o modülün komutunu yaz

Hadi başlayalım! Hangi modülü kullanmak istersin? 💪
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı zaman dilimini ayarla"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Lütfen bir zaman dilimi belirtin.\n\n"
            "Örnek: `/timezone Europe/Istanbul`\n"
            "Dünya saatleri için IANA formatı kullanın.",
            parse_mode='Markdown'
        )
        return

    new_timezone = context.args[0]
    
    try:
        import pytz
        pytz.timezone(new_timezone)
    except Exception:
        await update.message.reply_text(
            "❌ Geçersiz zaman dilimi! `Europe/Istanbul`, `Europe/London` gibi geçerli bir bölge girin.",
            parse_mode='Markdown'
        )
        return

    db_user = database.get_or_create_user(user.id)
    database.update_user_timezone(db_user['id'], new_timezone)
    
    await update.message.reply_text(
        f"✅ Zaman dilimi güncellendi: `{new_timezone}`\n"
        f"Hatırlatmalar artık bu saate göre gönderilecek.",
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım komutu"""
    user = update.effective_user
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    current_module = database.get_user_current_module(db_user['id'])
    
    help_message = f"""
📖 *Yardım - Modüler Bot Sistemi*

*Aktif Modülün:* {modules[current_module].module_emoji} {current_module.title()}

*Modül Komutları:*
🤖 `/asistan` - Asistan modülü
📚 `/ders` - Ders modülü
🇬🇧 `/ingilizce` - İngilizce modülü
📖 `/kitap` - Kitap modülü
📔 `/notdefteri` - Not defteri modülü
🚀 `/proje` - Proje modülü

*Genel Komutlar:*
`/start` - Ana menü
`/help` - Yardım
`/timezone` - Saat ayarı
`/modul` - Aktif modül

Modül değiştirmek için yukarıdaki komutları kullan!
"""
    
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def modul_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktif modülü göster"""
    user = update.effective_user
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    current_module = database.get_user_current_module(db_user['id'])
    module_instance = modules[current_module]
    
    message = f"""
{module_instance.module_emoji} *Aktif Modül: {current_module.title()}*

{module_instance.module_description}

Modül değiştirmek için diğer modül komutlarını kullanabilirsin:
`/asistan` | `/ders` | `/ingilizce` | `/kitap` | `/notdefteri` | `/proje`
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


# ==================== MODÜL KOMUT İŞLEYİCİLERİ ====================

async def switch_to_asistan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asistan modülüne geç"""
    await switch_module(update, context, 'asistan')

async def switch_to_ders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ders modülüne geç"""
    await switch_module(update, context, 'ders')

async def switch_to_ingilizce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İngilizce modülüne geç"""
    await switch_module(update, context, 'ingilizce')

async def switch_to_kitap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kitap modülüne geç"""
    await switch_module(update, context, 'kitap')

async def switch_to_notdefteri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Not defteri modülüne geç"""
    await switch_module(update, context, 'notdefteri')

async def switch_to_proje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proje modülüne geç"""
    await switch_module(update, context, 'proje')


async def switch_module(update: Update, context: ContextTypes.DEFAULT_TYPE, module_name: str):
    """Modül değiştirme yardımcı fonksiyonu"""
    user = update.effective_user
    
    # Kullanıcıyı al veya oluştur
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Modülü değiştir
    database.set_user_current_module(db_user['id'], module_name)
    
    # Modülün start komutunu çağır
    module_instance = modules[module_name]
    await module_instance.start_command(update, context)


# ==================== MESAJ İŞLEYİCİ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen mesajları aktif modüle yönlendir"""
    user = update.effective_user
    
    # Kullanıcıyı al veya oluştur
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Kullanıcının aktif modülünü al
    current_module = database.get_user_current_module(db_user['id'])
    
    # İlgili modülün mesaj işleyicisini çağır
    module_instance = modules[current_module]
    await module_instance.handle_message(update, context, db_user)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sesli mesajları text'e çevir ve aktif modüle yönlendir"""
    user = update.effective_user
    
    # Kullanıcıyı al
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # İşleniyor mesajı
    processing_msg = await update.message.reply_text("🎤 Sesli mesaj işleniyor...")
    
    try:
        # Voice veya audio file ID'sini al
        if update.message.voice:
            file_id = update.message.voice.file_id
        elif update.message.audio:
            file_id = update.message.audio.file_id
        else:
            await processing_msg.edit_text("❌ Ses dosyası bulunamadı.")
            return
        
        # Transcribe et
        result = await voice_service.transcribe_telegram_voice(context.bot, file_id)
        
        if not result['success']:
            await processing_msg.edit_text(f"❌ Ses çevirme hatası: {result['error']}")
            return
        
        transcribed_text = result['text']
        
        if not transcribed_text:
            await processing_msg.edit_text("❌ Ses anlaşılamadı. Lütfen tekrar dene.")
            return
        
        # Transcription'u göster
        await processing_msg.edit_text(f"📝 *Anladığım:*\n{transcribed_text}", parse_mode='Markdown')
        
        # Aktif modüle yönlendir
        current_module = database.get_user_current_module(db_user['id'])
        module_instance = modules[current_module]
        
        # Fake message objesi oluştur
        # Not: Bu basit bir yaklaşım, daha ileri seviye için message kopyalanabilir
        class FakeMessage:
            def __init__(self, text, original_message):
                self.text = text
                self.reply_text = original_message.reply_text
                self.chat = original_message.chat
                self.from_user = original_message.from_user
        
        class FakeUpdate:
            def __init__(self, message, original_update):
                self.message = message
                self.effective_user = original_update.effective_user
        
        fake_message = FakeMessage(transcribed_text, update.message)
        fake_update = FakeUpdate(fake_message, update)
        
        await module_instance.handle_message(fake_update, context, db_user)
        
    except Exception as e:
        logger.error(f"Voice message error: {e}")
        await processing_msg.edit_text(f"❌ Hata: {str(e)}")


# ==================== HATA İŞLEYİCİ ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hataları işle"""
    print(f"Hata: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin."
        )



async def test_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manuel hatırlatma tetikleyici (Debug)"""
    await update.message.reply_text("🔄 Hatırlatmalar manuel olarak tetikleniyor...", parse_mode='Markdown')
    
    # Trigger functions
    try:
        # Global ve kullanıcı bazlı kontrolleri tetikle
        await scheduler.send_reminders()
        await scheduler.check_user_reminders()
        await update.message.reply_text("✅ Tetikleme tamamlandı. Koşullar sağlanıyorsa mesaj gelmesi lazım.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}", parse_mode='Markdown')


async def post_init(application: Application):
    """Bot başlatıldıktan sonra çalışacak"""
    # Zamanlayıcıya bot'u set et
    scheduler.set_bot_application(application)
    
    # Zamanlayıcıyı başlat
    scheduler.start_scheduler()
    print("⏰ Zamanlayıcı post_init içinde başlatıldı")


# ==================== ANA FONKSİYON ====================

def main():
    """Botu başlat"""
    print("🤖 Modüler Bot başlatılıyor...")
    
    # Veritabanını başlat
    database.init_database()
    print("📦 Veritabanı hazır")
    
    # Bot uygulamamasını oluştur (post_init ile)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Genel komut işleyicileri
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("yardim", help_command))
    application.add_handler(CommandHandler("modul", modul_command))
    application.add_handler(CommandHandler("timezone", timezone_command))
    
    # Debug komutu
    application.add_handler(CommandHandler("test_reminders", test_reminders_command))
    
    # Modül komut işleyicileri
    application.add_handler(CommandHandler("asistan", switch_to_asistan))
    application.add_handler(CommandHandler("ders", switch_to_ders))
    application.add_handler(CommandHandler("ingilizce", switch_to_ingilizce))
    application.add_handler(CommandHandler("kitap", switch_to_kitap))
    application.add_handler(CommandHandler("notdefteri", switch_to_notdefteri))
    application.add_handler(CommandHandler("proje", switch_to_proje))
    
    # Her modülün özel handler'larını kaydet
    for module_name, module_instance in modules.items():
        module_instance.register_handlers(application)
    
    # Mesaj işleyici ekle (tüm text mesajları)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Sesli mesaj işleyici
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))
    
    # Hata işleyici ekle
    application.add_error_handler(error_handler)
    
    # Zamanlayıcı burada başlatılmaz, post_init içinde başlatılır
    
    # Botu başlat
    print("✅ Modüler Bot çalışıyor! Ctrl+C ile durdurun.")
    print(f"📱 Aktif Modüller: {', '.join(modules.keys())}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
