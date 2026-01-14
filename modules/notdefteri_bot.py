"""
Not Defteri Bot - Kategorili notlar, arama, favoriler
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
from modules.notdefteri import database as db
from modules.notdefteri import ai_service as ai

class NotDefteriBott(BaseModule):
    
    def get_module_name(self) -> str:
        return "notdefteri"
    
    def get_module_description(self) -> str:
        return "Kategorili not sistemi, gelismis arama ve favori notlar."
    
    def get_module_emoji(self) -> str:
        return "📔"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        notes = db.get_user_notes(user_id)
        categories = db.get_categories(user_id)
        
        welcome = f"""
{self.module_emoji} *Not Defteri Modulune Hos Geldin!*

*Durum:* {len(notes)} not, {len(categories)} kategori

*Komutlar:*
/not_ekle - Yeni not
/notlarim - Tum notlar
/favorilerim - Favori notlar
/not_ara - Not ara
/kategoriler - Kategori listesi

*Kategoriler:*
Genel, Is, Kisisel, Okul, Fikir

*Ornekler:*
- "Is kategorisinde not: Toplanti 15:00"
- "Python ogrenme notlari"
- "Python iceren notlari bul"
"""
        
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        message_text = update.message.text
        user_id = db_user['telegram_id']
        
        result = ai.analyze_note_message(message_text)
        action = result.get('action', 'chat')
        response = result.get('response', 'Anladim!')
        
        if action == "add_note":
            response = await self._handle_add_note(result, user_id)
        elif action == "search_note":
            response = await self._handle_search(result, user_id)
        elif action == "list_notes":
            notes = db.get_user_notes(user_id)
            response = ai.format_notes_list(notes)
        elif action == "list_favorites":
            notes = db.get_user_notes(user_id, favorites_only=True)
            response = ai.format_notes_list(notes) if notes else "Favori not yok."
        elif action == "show_categories":
            categories = db.get_categories(user_id)
            response = ai.format_categories(categories)
        
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except:
            await update.message.reply_text(response.replace('*', '').replace('_', ''))
    
    async def _handle_add_note(self, result: dict, user_id: int) -> str:
        baslik = result.get('baslik', '')
        icerik = result.get('icerik', '')
        kategori = result.get('kategori', 'Genel')
        
        if not baslik or not icerik:
            return "Baslik ve icerik gerekli."
        
        db.add_note(user_id, baslik, icerik, kategori)
        
        return f"*Not eklendi!*\n\n*{baslik}*\n{kategori}\n\n{icerik}"
    
    async def _handle_search(self, result: dict, user_id: int) -> str:
        keyword = result.get('search_keyword', '')
        kategori = result.get('kategori')
        
        if not keyword and not kategori:
            return "Arama kelimesi veya kategori belirt."
        
        if keyword:
            notes = db.search_notes(user_id, keyword, kategori)
        else:
            notes = db.get_user_notes(user_id, kategori=kategori)
        
        if not notes:
            return f"'{keyword}' icin sonuc yok."
        
        return ai.format_notes_list(notes)
    
    def register_handlers(self, application: Application):
        from telegram.ext import CommandHandler
        
        application.add_handler(CommandHandler("not_ekle", self.add_note_cmd))
        application.add_handler(CommandHandler("notlarim", self.list_notes_cmd))
        application.add_handler(CommandHandler("favorilerim", self.favorites_cmd))
        application.add_handler(CommandHandler("not_ara", self.search_cmd))
        application.add_handler(CommandHandler("kategoriler", self.categories_cmd))
    
    async def add_note_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Not Ekle*\n\nFormat:\nKategori: Baslik - Icerik\n\nOrnek:\nIs: Toplanti - Yarin 15:00",
            parse_mode='Markdown'
        )
    
    async def list_notes_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        notes = db.get_user_notes(user_id)
        response = ai.format_notes_list(notes)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def favorites_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        notes = db.get_user_notes(user_id, favorites_only=True)
        response = ai.format_notes_list(notes) if notes else "Favori not yok."
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def search_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Not Ara*\n\nArama yap:\nPython iceren notlari bul\nIs kategorisindeki notlar",
            parse_mode='Markdown'
        )
    
    async def categories_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        categories = db.get_categories(user_id)
        response = ai.format_categories(categories)
        await update.message.reply_text(response, parse_mode='Markdown')
