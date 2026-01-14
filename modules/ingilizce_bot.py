"""
Ingilizce Bot Modulu
Kelime defteri, gunluk hedef, spaced repetition
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
from modules.ingilizce import database as db
from modules.ingilizce import ai_service as ai
from datetime import datetime, date


class IngilizceBot(BaseModule):
    """Ingilizce kelime ogrenme modulu"""
    
    def get_module_name(self) -> str:
        return "ingilizce"
    
    def get_module_description(self) -> str:
        return "Kelime ogren, gunluk hedef belirle, tekrar sistemi ile ezberle."
    
    def get_module_emoji(self) -> str:
        return "🇬🇧"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        stats = db.get_learning_stats(user.id, days=7)
        goal = db.get_user_daily_goal(user.id)
        
        welcome_message = f"""
{self.module_emoji} *Ingilizce Modulune Hos Geldin!*

Bu modulde:
- Kelime defteri (AI destekli)
- Gunluk hedef belirleme
- Akilli tekrar sistemi
- Ilerleme takibi

*Komutlar:*
/kelime_ekle - Yeni kelime
/kelimelerim - Kelime listesi
/gunluk_hedef - Gunluk hedef belirle
/bugun_ogren - Bugunku kelimelerinizi alin
/istatistik - Ilerleme durumu

*Ornek Kullanimlar:*
- "serendipity kelimesini ekle"
- "Gunde 10 kelime ogrenmek istiyorum"
- "Bugunku kelimeleri goster"

*Durum:* {stats['toplam']} kelime
"""
        
        if goal:
            welcome_message += f"\n*Gunluk Hedef:* {goal['gunluk_kelime_sayisi']} kelime"
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        message_text = update.message.text
        user_id = db_user['telegram_id']
        
        result = ai.analyze_ingilizce_message(message_text)
        action = result.get('action', 'chat')
        response = result.get('response', 'Anladim!')
        
        if action == "add_word":
            response = await self._handle_add_word(result, user_id)
        elif action == "word_detail":
            response = await self._handle_word_detail(result, user_id)
        elif action == "set_goal":
            response = await self._handle_set_goal(result, user_id)
        elif action == "show_daily":
            response = await self._handle_show_daily(user_id)
        elif action == "show_stats":
            stats = db.get_learning_stats(user_id, days=30)
            response = ai.format_stats(stats)
        elif action == "start_review":
            response = await self._handle_review(user_id)
        elif action == "list_words":
            words = db.get_user_words(user_id)
            response = ai.format_words_list(words)
        
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(response.replace('*', '').replace('_', ''))
    
    async def _handle_add_word(self, result: dict, user_id: int) -> str:
        word = result.get('word', '')
        
        if not word:
            return "Hangi kelimeyi eklemek istiyorsun?"
        
        existing = db.get_word_by_word(user_id, word)
        if existing:
            return f"*{word}* zaten kelime defterinde!"
        
        word_info = ai.get_word_meaning_and_examples(word)
        
        db.add_word(
            user_id, word, 
            word_info['meaning'],
            word_info.get('example1'),
            word_info.get('example2'),
            word_info.get('example3')
        )
        
        response = f"*{word.title()}* defterine eklendi!\n\n"
        response += ai.format_word_info({'word': word, **word_info})
        
        return response
    
    async def _handle_word_detail(self, result: dict, user_id: int) -> str:
        word = result.get('word', '')
        
        if not word:
            return "Hangi kelimenin detayini gormek istiyorsun?"
        
        word_data = db.get_word_by_word(user_id, word)
        
        if not word_data:
            return f"*{word}* kelime defterinde bulunamadi."
        
        return ai.format_word_info(word_data)
    
    async def _handle_set_goal(self, result: dict, user_id: int) -> str:
        goal_count = result.get('goal_count', 0)
        
        if not goal_count:
            return "Gunluk kac kelime ogrenmek istiyorsun?"
        
        db.set_daily_goal(user_id, goal_count)
        
        return f"Gunluk hedef belirlendi: *{goal_count} kelime*"
    
    async def _handle_show_daily(self, user_id: int) -> str:
        goal = db.get_user_daily_goal(user_id)
        
        if not goal:
            return "Once gunluk hedef belirle!"
        
        count = goal['gunluk_kelime_sayisi']
        daily_words = db.get_daily_words(user_id, count)
        
        if not daily_words:
            return "Tum kelimeler ogrenme asamasinda! Yeni kelime ekle veya tekrar yap."
        
        response = f"*Bugunun Kelimeleri ({len(daily_words)} kelime):*\n\n"
        
        for word in daily_words:
            response += f"*{word['word'].title()}*\n"
            response += f"{word['meaning']}\n"
            if word.get('example1'):
                response += f"{word['example1']}\n"
            response += "\n"
            
            db.mark_word_learned(word['id'])
        
        db.add_learning_session(user_id, len(daily_words))
        
        response += "Kelimeler 'ogreniyor' olarak isaretlendi!"
        
        return response
    
    async def _handle_review(self, user_id: int) -> str:
        review_words = db.get_words_for_review(user_id)
        
        if not review_words:
            return "Bugun tekrar edilecek kelime yok!"
        
        response = f"*{len(review_words)} Kelime Tekrari*\n\n"
        
        for word in review_words:
            response += f"*{word['word'].title()}* - {word['meaning']}\n"
            
            update_info = db.update_word_review(word['id'])
            response += f"   Tekrar #{update_info['review_count']}\n\n"
        
        response += "Tekrarlar tamamlandi!"
        
        return response
    
    def register_handlers(self, application: Application):
        from telegram.ext import CommandHandler
        
        application.add_handler(CommandHandler("kelime_ekle", self.add_word_command))
        application.add_handler(CommandHandler("kelimelerim", self.list_words_command))
        application.add_handler(CommandHandler("gunluk_hedef", self.set_goal_command))
        application.add_handler(CommandHandler("bugun_ogren", self.show_daily_command))
    
    async def add_word_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Kelime Ekle*\n\nEklemek istedigin kelimeyi yaz:\nserendipity ekle",
            parse_mode='Markdown'
        )
    
    async def list_words_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        words = db.get_user_words(user_id)
        response = ai.format_words_list(words)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def set_goal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        goal = db.get_user_daily_goal(user_id)
        
        response = "*Gunluk Hedef*\n\n"
        if goal:
            response += f"Mevcut hedef: {goal['gunluk_kelime_sayisi']} kelime/gun\n\n"
        response += "Yeni hedef belirle: Gunde 10 kelime ogrenmek istiyorum"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def show_daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        response = await self._handle_show_daily(user_id)
        await update.message.reply_text(response, parse_mode='Markdown')
