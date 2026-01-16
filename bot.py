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
from modules.notdefteri_bot import NotDefteriBott
from modules.proje_bot import ProjeBot

# Modül instance'ları oluştur
modules = {
    'asistan': AsistanBot(),
    'ders': DersBot(),
    'ingilizce': IngilizceBot(),
    'kitap': KitapBot(),
    'notdefteri': NotDefteriBott(),
    'proje': ProjeBot()
}


# ==================== ANA MENÜ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlatma komutu - Ana menü"""
    user = update.effective_user
    
    # Kullanıcıyı veritabanına kaydet
    database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_message = f"""
🌟 *Merhaba {user.first_name}!*

Ben senin kişisel asistan botunun! Farklı modüllerle sana yardımcı olabilirim.

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım komutu"""
    user = update.effective_user
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Kullanıcının aktif modülünü al
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
`/help` veya `/yardim` - Bu yardım mesajı
`/modul` - Aktif modülü göster

Her modülün kendi özel komutları ve özellikleri var. 
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


# ==================== HATA İŞLEYİCİ ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hataları işle"""
    print(f"Hata: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin."
        )


# ==================== ANA FONKSİYON ====================

def main():
    """Botu başlat"""
    print("🤖 Modüler Bot başlatılıyor...")
    
    # Veritabanını başlat
    database.init_database()
    print("📦 Veritabanı hazır")
    
    # Bot uygulamasını oluştur
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Zamanlayıcıya bot'u set et
    scheduler.set_bot_application(application)
    
    # Genel komut işleyicileri
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("yardim", help_command))
    application.add_handler(CommandHandler("modul", modul_command))
    
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
    
    # Hata işleyici ekle
    application.add_error_handler(error_handler)
    
    # Zamanlayıcıyı başlat
    scheduler.start_scheduler()
    
    # Botu başlat
    print("✅ Modüler Bot çalışıyor! Ctrl+C ile durdurun.")
    print(f"📱 Aktif Modüller: {', '.join(modules.keys())}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
