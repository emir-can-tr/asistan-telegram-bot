"""
Kitap Bot Modulu
Okuma listesi, notlar, hedefler, ilerleme takibi
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
from modules.kitap import database as db
from modules.kitap import ai_service as ai
from datetime import datetime, date


class KitapBot(BaseModule):
    """Kitap okuma takip modulu"""
    
    def get_module_name(self) -> str:
        return "kitap"
    
    def get_module_description(self) -> str:
        return "Okuma listesi olustur, notlar al, hedef belirle, ilerlemeni takip et."
    
    def get_module_emoji(self) -> str:
        return "📚"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        books = db.get_user_books(user.id)
        
        welcome_message = f"""
{self.module_emoji} *Kitap Modulune Hos Geldin!*

Bu modulde:
- Okuma listesi yonetimi
- Kitap notlari
- Okuma hedefleri
- Ilerleme takibi

*Komutlar:*
/kitap_ekle - Yeni kitap ekle
/kitaplarim - Kitaplari listele
/okuma_kaydet - Okunan sayfa kaydet
/hedef_belirle - Okuma hedefi
/istatistik - Okuma istatistikleri

*Ornek Kullanimlar:*
- "1984 kitabini ekle, George Orwell, 328 sayfa"
- "Bugun 50 sayfa okudum"
- "Gunde 30 sayfa okumak istiyorum"
"""
        
        if not books:
            welcome_message += "\n\n*Henuz kitap eklenmemis!*"
        else:
            welcome_message += f"\n\nListenizde {len(books)} kitap var!"
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        message_text = update.message.text
        user_id = db_user['telegram_id']
        
        user_books = db.get_user_books(user_id)
        result = ai.analyze_kitap_message(message_text, user_books)
        
        action = result.get('action', 'chat')
        response = result.get('response', 'Anladim!')
        
        if action == "add_book":
            response = await self._handle_add_book(result, user_id)
        elif action == "add_note":
            response = await self._handle_add_note(result, user_id, user_books)
        elif action == "add_progress":
            response = await self._handle_add_progress(result, user_id, user_books)
        elif action == "set_goal":
            response = await self._handle_set_goal(result, user_id)
        elif action == "show_stats":
            response = await self._handle_show_stats(user_id)
        elif action == "list_books":
            filter_status = result.get('filter_status')
            books = db.get_user_books(user_id, durum=filter_status)
            response = ai.format_books_list(books, filter_status)
        elif action == "update_status":
            response = await self._handle_update_status(result, user_id, user_books)
        
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(response.replace('*', '').replace('_', ''))
    
    async def _handle_add_book(self, result: dict, user_id: int) -> str:
        baslik = result.get('book_title', '')
        yazar = result.get('book_author', '')
        toplam_sayfa = result.get('total_pages', 0)
        kategori = result.get('category')
        
        if not baslik or not yazar or not toplam_sayfa:
            return "Kitap eklemek icin baslik, yazar ve sayfa sayisi gerekli."
        
        db.add_book(user_id, baslik, yazar, toplam_sayfa, kategori)
        
        response = f"*{baslik}* eklendi!\n\n"
        response += f"Yazar: {yazar}\n"
        response += f"{toplam_sayfa} sayfa\n"
        if kategori:
            response += f"Kategori: {kategori}\n"
        
        return response
    
    async def _handle_add_note(self, result: dict, user_id: int, user_books: list) -> str:
        book_title = result.get('book_title', '')
        note_text = result.get('note_text', '')
        
        if not book_title:
            if user_books:
                current_books = db.get_user_books(user_id, durum='okunuyor')
                if current_books:
                    book = current_books[0]
                    book_title = book['baslik']
                else:
                    return "Hangi kitap icin not eklemek istiyorsun?"
            else:
                return "Once kitap eklemelisin!"
        
        if not note_text:
            return "Not metni bos olamaz!"
        
        book = db.get_book_by_title(user_id, book_title)
        if not book:
            return f"'{book_title}' kitabi bulunamadi."
        
        db.add_book_note(user_id, book['id'], note_text)
        
        return f"*{book['baslik']}* icin not kaydedildi!\n\n{note_text}"
    
    async def _handle_add_progress(self, result: dict, user_id: int, user_books: list) -> str:
        pages_read = result.get('pages_read', 0)
        book_title = result.get('book_title')
        
        if not pages_read:
            return "Kac sayfa okudugun belirtmelisin."
        
        if not book_title:
            current_books = db.get_user_books(user_id, durum='okunuyor')
            if not current_books:
                return "Su an okudugun kitap yok."
            book = current_books[0]
        else:
            book = db.get_book_by_title(user_id, book_title)
            if not book:
                return f"'{book_title}' kitabi bulunamadi."
        
        db.add_reading_progress(user_id, book['id'], pages_read)
        progress = db.get_book_progress(book['id'])
        
        response = f"*{book['baslik']}* - {pages_read} sayfa kaydedildi!\n\n"
        response += f"Ilerleme: %{progress['yuzde']}\n"
        response += f"{progress['toplam_okunan']}/{progress['toplam_sayfa']} sayfa\n"
        
        if progress['yuzde'] >= 100:
            response += "\nTebrikler! Kitabi bitirdin!"
            db.update_book_status(book['id'], 'okundu')
        
        return response
    
    async def _handle_set_goal(self, result: dict, user_id: int) -> str:
        goal_type = result.get('goal_type', 'gunluk')
        goal_value = result.get('goal_value', 0)
        
        if not goal_value:
            return "Hedef degeri belirtmelisin."
        
        db.set_reading_goal(user_id, goal_type, goal_value)
        
        type_text = {
            'gunluk': 'Gunluk',
            'haftalik': 'Haftalik',
            'aylik': 'Aylik',
            'yillik': 'Yillik'
        }.get(goal_type, goal_type.title())
        
        return f"*{type_text} hedef belirlendi!*\n\n{goal_value} sayfa"
    
    async def _handle_show_stats(self, user_id: int) -> str:
        stats = db.get_reading_stats(user_id, days=30)
        return ai.format_reading_stats(stats, "Son 30 Gun")
    
    async def _handle_update_status(self, result: dict, user_id: int, user_books: list) -> str:
        book_title = result.get('book_title', '')
        status = result.get('status', '')
        
        if not book_title:
            return "Hangi kitabin durumunu guncellemek istiyorsun?"
        
        if status not in ['okunacak', 'okunuyor', 'okundu']:
            if 'basla' in book_title.lower():
                status = 'okunuyor'
            elif 'bitir' in book_title.lower():
                status = 'okundu'
            else:
                return "Durum belirtmelisin: okunacak/okunuyor/okundu"
        
        book = db.get_book_by_title(user_id, book_title)
        if not book:
            return f"'{book_title}' kitabi bulunamadi."
        
        db.update_book_status(book['id'], status)
        
        status_text = {
            'okunacak': 'okunacaklar listesine eklendi',
            'okunuyor': 'okumaya baslandi',
            'okundu': 'tamamlandi olarak isaretlendi'
        }
        
        return f"*{book['baslik']}* {status_text.get(status)}!"
    
    def register_handlers(self, application: Application):
        from telegram.ext import CommandHandler
        
        application.add_handler(CommandHandler("kitap_ekle", self.add_book_command))
        application.add_handler(CommandHandler("kitaplarim", self.list_books_command))
        application.add_handler(CommandHandler("okuma_kaydet", self.add_progress_command))
        application.add_handler(CommandHandler("hedef_belirle", self.set_goal_command))
    
    async def add_book_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Kitap Ekle*\n\nFormat:\nBaslik, Yazar, Sayfa Sayisi\n\nOrnek:\n1984, George Orwell, 328",
            parse_mode='Markdown'
        )
    
    async def list_books_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        books = db.get_user_books(user_id)
        response = ai.format_books_list(books)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def add_progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Okuma Kaydi*\n\nKac sayfa okudugun yaz:\n50 sayfa okudum",
            parse_mode='Markdown'
        )
    
    async def set_goal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        goals = db.get_user_goals(user_id)
        
        response = "*Okuma Hedefleri*\n\n"
        if goals:
            response += "*Mevcut Hedefler:*\n"
            for goal in goals:
                response += f"- {goal['hedef_tipi'].title()}: {goal['hedef_deger']} sayfa\n"
        
        response += "\n*Yeni Hedef:*\nGunde 30 sayfa okumak istiyorum"
        
        await update.message.reply_text(response, parse_mode='Markdown')
