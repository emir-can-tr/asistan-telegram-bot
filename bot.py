"""
Kisisel Asistan Telegram Botu - Moduler Versiyon
Gemini AI destekli coklu modul botu
"""
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import database
from config import TELEGRAM_BOT_TOKEN
import scheduler

# Modulleri import et
from modules.asistan_bot import AsistanBot
from modules.ders_bot import DersBot
from modules.ingilizce_bot import IngilizceBot
from modules.kitap_bot import KitapBot
from modules.notdefteri_bot import NotDefteriBott
from modules.proje_bot import ProjeBot

# Modul instance'lari olustur
modules = {
    'asistan': AsistanBot(),
    'ders': DersBot(),
    'ingilizce': IngilizceBot(),
    'kitap': KitapBot(),
    'notdefteri': NotDefteriBott(),
    'proje': ProjeBot()
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot baslatma komutu - Ana menu"""
    user = update.effective_user
    
    database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_message = f"""
*Merhaba {user.first_name}!*

Ben senin kisisel asistan botunun! Farkli modullerle sana yardimci olabilirim.

*Moduller:*

/asistan - Aliskanlik, hatirlatma, gorev ve not yonetimi
/ders - Ders programi ve odev takibi
/ingilizce - Kelime ogrenme ve pratik
/kitap - Okuma listesi ve kitap notlari
/notdefteri - Gelismis not yonetimi
/proje - Proje yonetimi ve takip

*Nasil Kullanilir?*
1. Kullanmak istedigin modulun komutunu yaz
2. Modul aktif oldugunda mesaj yazarak kullanabilirsin
3. Baska module gecmek icin o modulun komutunu yaz
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardim komutu"""
    user = update.effective_user
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    current_module = database.get_user_current_module(db_user['id'])
    
    help_message = f"""
*Yardim - Moduler Bot Sistemi*

*Aktif Modulun:* {modules[current_module].module_emoji} {current_module.title()}

*Modul Komutlari:*
/asistan - Asistan modulu
/ders - Ders modulu
/ingilizce - Ingilizce modulu
/kitap - Kitap modulu
/notdefteri - Not defteri modulu
/proje - Proje modulu

*Genel Komutlar:*
/start - Ana menu
/help veya /yardim - Bu yardim mesaji
/modul - Aktif modulu goster
"""
    
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def modul_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktif modulu goster"""
    user = update.effective_user
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    current_module = database.get_user_current_module(db_user['id'])
    module_instance = modules[current_module]
    
    message = f"""
{module_instance.module_emoji} *Aktif Modul: {current_module.title()}*

{module_instance.module_description}

Modul degistirmek icin diger modul komutlarini kullanabilirsin:
/asistan | /ders | /ingilizce | /kitap | /notdefteri | /proje
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def switch_to_asistan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await switch_module(update, context, 'asistan')

async def switch_to_ders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await switch_module(update, context, 'ders')

async def switch_to_ingilizce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await switch_module(update, context, 'ingilizce')

async def switch_to_kitap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await switch_module(update, context, 'kitap')

async def switch_to_notdefteri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await switch_module(update, context, 'notdefteri')

async def switch_to_proje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await switch_module(update, context, 'proje')


async def switch_module(update: Update, context: ContextTypes.DEFAULT_TYPE, module_name: str):
    """Modul degistirme yardimci fonksiyonu"""
    user = update.effective_user
    
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    database.set_user_current_module(db_user['id'], module_name)
    
    module_instance = modules[module_name]
    await module_instance.start_command(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen mesajlari aktif module yonlendir"""
    user = update.effective_user
    
    db_user = database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    current_module = database.get_user_current_module(db_user['id'])
    
    module_instance = modules[current_module]
    await module_instance.handle_message(update, context, db_user)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hatalari isle"""
    print(f"Hata: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "Bir hata olustu. Lutfen tekrar deneyin."
        )


def main():
    """Botu baslat"""
    print("Moduler Bot baslatiliyor...")
    
    database.init_database()
    print("Veritabani hazir")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    scheduler.set_bot_application(application)
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("yardim", help_command))
    application.add_handler(CommandHandler("modul", modul_command))
    
    application.add_handler(CommandHandler("asistan", switch_to_asistan))
    application.add_handler(CommandHandler("ders", switch_to_ders))
    application.add_handler(CommandHandler("ingilizce", switch_to_ingilizce))
    application.add_handler(CommandHandler("kitap", switch_to_kitap))
    application.add_handler(CommandHandler("notdefteri", switch_to_notdefteri))
    application.add_handler(CommandHandler("proje", switch_to_proje))
    
    for module_name, module_instance in modules.items():
        module_instance.register_handlers(application)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error_handler)
    
    scheduler.start_scheduler()
    
    print("Moduler Bot calisiyor! Ctrl+C ile durdurun.")
    print(f"Aktif Moduller: {', '.join(modules.keys())}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
