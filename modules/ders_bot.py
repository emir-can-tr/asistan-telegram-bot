"""
Ders Bot Modulu
Ders programi, calisma takibi, soru cozumu, odev yonetimi
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
from modules.ders import database as db
from modules.ders import ai_service as ai
from modules.ders import schedule_loader as loader
from datetime import datetime, date


class DersBot(BaseModule):
    """Ders yonetimi modulu"""
    
    def get_module_name(self) -> str:
        return "ders"
    
    def get_module_description(self) -> str:
        return "Ders programi olustur, odevlerini takip et, calisma ve soru kayitlarini yonet."
    
    def get_module_emoji(self) -> str:
        return "📚"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders modulu baslatma"""
        user = update.effective_user
        lessons = db.get_user_lessons(user.id)
        
        welcome_message = f"""
{self.module_emoji} *Ders Modulune Hos Geldin!*

Bu modulde:
- Ders program takibi
- Calisma kaydi tutma
- Soru cozumu takibi
- Odev yonetimi

*Komutlar:*
/program_yukle - Ders programini yukle
/derslerim - Derslerini listele
/odevlerim - Odevlerini goster
/bugun - Bugunku ozet
/haftalik - Haftalik ozet
/istatistik - Calisma istatistiklerin

*Ornek Kullanimlar:*
- "Bugun hangi derslerim var?"
- "Matematik calistim turev konusu 2 saat"
- "Fizik'ten 15 soru cozdum"
- "Matematik odevi var cuma teslim"
"""
        
        if not lessons:
            welcome_message += "\n\n*Henuz ders programin yuklenmemis!*\n/program_yukle komutu ile yukleyebilirsin."
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        """Ders modulu mesaj isleyici"""
        message_text = update.message.text
        user_id = db_user['telegram_id']
        
        user_lessons = db.get_user_lessons(user_id)
        result = ai.analyze_ders_message(message_text, user_lessons)
        
        action = result.get('action', 'chat')
        response = result.get('response', 'Anladim!')
        
        if action == "query_schedule":
            response = await self._handle_query_schedule(result, user_id)
        elif action == "add_study":
            response = await self._handle_add_study(result, user_id, user_lessons)
        elif action == "add_questions":
            response = await self._handle_add_questions(result, user_id, user_lessons)
        elif action == "add_homework":
            response = await self._handle_add_homework(result, user_id, user_lessons)
        elif action == "complete_homework":
            response = await self._handle_complete_homework(result, user_id)
        elif action == "list_homeworks":
            homeworks = db.get_pending_homeworks(user_id)
            response = ai.format_homeworks(homeworks)
        elif action == "show_stats":
            response = await self._handle_show_stats(result, user_id)
        
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(response.replace('*', '').replace('_', ''))
    
    async def _handle_query_schedule(self, result: dict, user_id: int) -> str:
        gun = result.get('gun', 'bugun')
        saat_no = result.get('saat_no')
        
        weekday_names = ['pazartesi', 'sali', 'carsamba', 'persembe', 'cuma', 'cumartesi', 'pazar']
        if gun == 'bugun':
            gun = weekday_names[datetime.now().weekday()]
        elif gun == 'yarin':
            gun = weekday_names[(datetime.now().weekday() + 1) % 7]
        
        if saat_no:
            entry = db.get_schedule_by_hour(user_id, gun, saat_no)
            if entry:
                response = f"*{gun.title()} {saat_no}. Saat:*\n\n"
                response += f"{entry['ders_kodu']} - {entry['ders_adi']}\n"
                response += f"{entry['baslangic_saati']}-{entry['bitis_saati']}\n"
                if entry.get('ogretmen'):
                    response += f"{entry['ogretmen']}"
            else:
                response = f"{gun.title()} gunu {saat_no}. saatte ders yok."
        else:
            schedule = db.get_schedule_for_day(user_id, gun)
            response = ai.format_schedule(schedule)
        
        return response
    
    async def _handle_add_study(self, result: dict, user_id: int, user_lessons: list) -> str:
        lesson_search = result.get('lesson_search', '')
        konu = result.get('konu')
        sure_dakika = result.get('sure_dakika')
        
        if not lesson_search:
            return "Hangi dersi calistigini belirtmelisin."
        
        lesson = db.get_lesson_by_code_or_name(user_id, lesson_search)
        if not lesson:
            return f"'{lesson_search}' dersi bulunamadi."
        
        db.add_study_record(
            user_id=user_id,
            lesson_id=lesson['id'],
            konu=konu,
            sure_dakika=sure_dakika
        )
        
        response = f"*{lesson['ders_adi']}* calisman kaydedildi!\n\n"
        if konu:
            response += f"Konu: {konu}\n"
        if sure_dakika:
            saat = sure_dakika // 60
            dakika = sure_dakika % 60
            if saat > 0:
                response += f"Sure: {saat} saat"
                if dakika > 0:
                    response += f" {dakika} dakika"
            elif dakika > 0:
                response += f"Sure: {dakika} dakika"
        
        return response
    
    async def _handle_add_questions(self, result: dict, user_id: int, user_lessons: list) -> str:
        lesson_search = result.get('lesson_search', '')
        konu = result.get('konu')
        soru_sayisi = result.get('soru_sayisi')
        
        if not lesson_search or not soru_sayisi:
            return "Ders adi ve soru sayisi belirtmelisin."
        
        lesson = db.get_lesson_by_code_or_name(user_id, lesson_search)
        if not lesson:
            return f"'{lesson_search}' dersi bulunamadi."
        
        db.add_question_record(
            user_id=user_id,
            lesson_id=lesson['id'],
            soru_sayisi=soru_sayisi,
            konu=konu
        )
        
        response = f"*{soru_sayisi} {lesson['ders_adi']} sorusu* kaydedildi!\n\n"
        if konu:
            response += f"Konu: {konu}\n"
        
        return response
    
    async def _handle_add_homework(self, result: dict, user_id: int, user_lessons: list) -> str:
        lesson_search = result.get('lesson_search')
        homework_title = result.get('homework_title', '')
        homework_description = result.get('homework_description')
        homework_due_date = result.get('homework_due_date')
        
        if not homework_title or not homework_due_date:
            return "Odev basligi ve son tarih gerekli."
        
        lesson_id = None
        if lesson_search:
            lesson = db.get_lesson_by_code_or_name(user_id, lesson_search)
            if lesson:
                lesson_id = lesson['id']
        
        try:
            due_date = datetime.strptime(homework_due_date, '%Y-%m-%d').date()
        except:
            if homework_due_date.lower() in ['bugun']:
                due_date = date.today()
            elif homework_due_date.lower() in ['yarin']:
                from datetime import timedelta
                due_date = date.today() + timedelta(days=1)
            else:
                return f"Tarih formati anlasilamadi: {homework_due_date}"
        
        db.add_homework(
            user_id=user_id,
            lesson_id=lesson_id,
            baslik=homework_title,
            aciklama=homework_description,
            bitis_tarihi=due_date
        )
        
        response = f"*Odev eklendi!*\n\n{homework_title}\n"
        if homework_description:
            response += f"{homework_description}\n"
        response += f"Son tarih: {due_date.strftime('%d.%m.%Y')}"
        
        return response
    
    async def _handle_complete_homework(self, result: dict, user_id: int) -> str:
        homework_search = result.get('homework_search', '')
        
        if not homework_search:
            return "Hangi odevi tamamladigini belirtmelisin."
        
        homework = db.get_homework_by_title(user_id, homework_search)
        if not homework:
            return f"'{homework_search}' ile eslesen bir odev bulunamadi."
        
        db.complete_homework(homework['id'])
        return f"*'{homework['baslik']}'* odevi tamamlandi!"
    
    async def _handle_show_stats(self, result: dict, user_id: int) -> str:
        study_records = db.get_study_records(user_id, days=7)
        study_text = ai.format_study_records(study_records)
        
        question_stats = db.get_question_stats(user_id, days=7)
        stats_text = ai.format_question_stats(question_stats)
        
        return f"{study_text}\n\n{stats_text}"
    
    def register_handlers(self, application: Application):
        """Ders modulu ozel handler'lari"""
        from telegram.ext import CommandHandler
        
        application.add_handler(CommandHandler("program_yukle", self.load_schedule_command))
        application.add_handler(CommandHandler("derslerim", self.list_lessons_command))
        application.add_handler(CommandHandler("odevlerim", self.list_homeworks_command))
        application.add_handler(CommandHandler("istatistik", self.show_stats_command))
        application.add_handler(CommandHandler("bugun", self.today_summary_command))
        application.add_handler(CommandHandler("haftalik", self.weekly_summary_command))
    
    async def load_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lessons = db.get_user_lessons(user_id)
        if lessons:
            await update.message.reply_text("Ders programin zaten yuklu!", parse_mode='Markdown')
            return
        
        try:
            loader.load_schedule_data(user_id)
            await update.message.reply_text("*Ders programin basariyla yuklendi!*", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"Hata: {str(e)}")
    
    async def list_lessons_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lessons = db.get_user_lessons(user_id)
        
        if not lessons:
            await update.message.reply_text("Henuz ders eklenmemis!", parse_mode='Markdown')
            return
        
        response = f"*Derslerim ({len(lessons)} ders):*\n\n"
        for lesson in lessons:
            response += f"- *{lesson['ders_kodu']}* - {lesson['ders_adi']}\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def list_homeworks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        homeworks = db.get_pending_homeworks(user_id)
        response = ai.format_homeworks(homeworks)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def show_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        study_records = db.get_study_records(user_id, days=7)
        study_text = ai.format_study_records(study_records)
        question_stats = db.get_question_stats(user_id, days=7)
        stats_text = ai.format_question_stats(question_stats)
        response = f"{study_text}\n\n{stats_text}"
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def today_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        today_studies = db.get_today_study_records(user_id)
        today_questions = db.get_today_question_stats(user_id)
        
        response = f"*Bugunku Ozet ({date.today().strftime('%d.%m.%Y')})*\n\n"
        
        if today_studies:
            response += "*Calismalar:*\n"
            for study in today_studies:
                response += f"- {study['ders_adi']}\n"
            response += "\n"
        else:
            response += "Bugun henuz calisma kaydin yok.\n\n"
        
        if today_questions['toplam'] > 0:
            response += f"*Sorular:* {today_questions['toplam']} soru\n"
        else:
            response += "Bugun henuz soru cozmedin.\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def weekly_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        study_records = db.get_study_records(user_id, days=7)
        question_stats = db.get_question_stats(user_id, days=7)
        
        response = "*Bu Haftanin Ozeti (Son 7 Gun)*\n\n"
        
        if study_records:
            response += f"*Calismalar:* {len(study_records)} kayit\n\n"
        else:
            response += "Bu hafta calisma kaydin yok.\n\n"
        
        if question_stats['toplam'] > 0:
            response += f"*Sorular:* {question_stats['toplam']} soru\n"
        else:
            response += "Bu hafta soru cozmedin.\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
