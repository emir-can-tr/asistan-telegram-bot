"""
Ders Bot Modülü - TAM FONKSİYONEL
Ders programı, çalışma takibi, soru çözümü, ödev yönetimi
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
from modules.ders import database as db
from modules.ders import ai_service as ai
from modules.ders import schedule_loader as loader
from datetime import datetime, date


class DersBot(BaseModule):
    """Ders yönetimi modülü"""
    
    def get_module_name(self) -> str:
        return "ders"
    
    def get_module_description(self) -> str:
        return "Ders programı oluştur, ödevlerini takip et, çalışma ve soru kayıtlarını yönet."
    
    def get_module_emoji(self) -> str:
        return "📚"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders modülü başlatma"""
        user = update.effective_user
        
        # Kullanıcının dersleri var mı kontrol et
        lessons = db.get_user_lessons(user.id)
        
        welcome_message = f"""
{self.module_emoji} *Ders Modülüne Hoş Geldin!*

Bu modülde:
• 📅 Ders program takibi
• 📚 Çalışma kaydı tutma
• ✏️ Soru çözümü takibi 
• 📝 Ödev yönetimi

*Komutlar:*
• `/program_yukle` - Ders programını yükle
• `/derslerim` - Derslerini listele
• `/odevlerim` - Ödevlerini göster
• `/bugun` - Bugünkü özet
• `/haftalik` - Haftalık özet
• `/istatistik` - Çalışma istatistiklerin

*Örnek Kullanımlar:*
• "Bugün hangi derslerim var?"
• "Matematik çalıştım türev konusu 2 saat"
• "Fizik'ten 15 soru çözdüm"
• "Matematik ödevi var cuma teslim"
• "Bugün ne kadar çalıştım?"
• "Bu hafta kaç soru çözdüm?"

Benimle doğal dilde konuşabilirsin! 💪
"""
        
        if not lessons:
            welcome_message += "\n\n⚠️ *Henüz ders programın yüklenmemiş!*\n`/program_yukle` komutu ile yükleyebilirsin."
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        """Ders modülü mesaj işleyici"""
        message_text = update.message.text
        user_id = db_user['telegram_id']
        
        # Kullanıcının derslerini al
        user_lessons = db.get_user_lessons(user_id)
        
        # AI'dan analiz al
        result = ai.analyze_ders_message(message_text, user_lessons)
        
        action = result.get('action', 'chat')
        response = result.get('response', 'Anladım!')
        
        # Aksiyona göre işlem yap
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
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def _handle_query_schedule(self, result: dict, user_id: int) -> str:
        """Ders programı sorgulama"""
        day = result.get('day', date.today().strftime('%Y-%m-%d'))
        
        # Gün ismini bul (Türkçe)
        tr_gunler = {
            'Monday': 'pazartesi', 'Tuesday': 'sali', 'Wednesday': 'çarşamba',
            'Thursday': 'perşembe', 'Friday': 'cuma', 'Saturday': 'cumartesi', 'Sunday': 'pazar'
        }
        
        if isinstance(day, str):
            try:
                dt = datetime.strptime(day, '%Y-%m-%d')
                gun_ismi = tr_gunler[dt.strftime('%A')]
            except:
                gun_ismi = date.today().strftime('%A')
                gun_ismi = tr_gunler.get(gun_ismi, 'pazartesi')
        else:
            gun_ismi = "pazartesi"
            
        schedule = db.get_schedule(user_id, gun_ismi)
        return ai.format_schedule(schedule, gun_ismi)

    async def _handle_add_study(self, result: dict, user_id: int, user_lessons: list) -> str:
        """Çalışma kaydı ekleme"""
        ders_adi = result.get('subject')
        sure = result.get('duration', 0)
        konu = result.get('topic')
        detay = result.get('details')
        
        # Ders ID bul
        lesson_id = self._find_lesson_id(ders_adi, user_lessons)
        
        if not lesson_id:
            return f"❌ '{ders_adi}' dersini bulamadım. Lütfen ders ismini doğru yazdığından emin ol."
        
        db.add_study_record(user_id, lesson_id, sure, konu, detay)
        
        return f"✅ *Çalışma Kaydedildi!*\n\n📚 Ders: {ders_adi}\n⏱️ Süre: {sure} dk\n📝 Konu: {konu}"

    async def _handle_add_questions(self, result: dict, user_id: int, user_lessons: list) -> str:
        """Soru çözümü ekleme"""
        ders_adi = result.get('subject')
        miktar = result.get('amount', 0)
        dogru = result.get('correct')
        yanlis = result.get('incorrect')
        konu = result.get('topic')
        
        lesson_id = self._find_lesson_id(ders_adi, user_lessons)
        
        if not lesson_id:
            return f"❌ '{ders_adi}' dersini bulamadım."
            
        db.add_question_record(user_id, lesson_id, miktar, dogru, yanlis, konu)
        
        msg = f"✅ *Soru Çözümü Kaydedildi!*\n\n📚 Ders: {ders_adi}\n✏️ Soru: {miktar}"
        if dogru is not None:
            msg += f"\n✅ Doğru: {dogru}"
        if yanlis is not None:
            msg += f"\n❌ Yanlış: {yanlis}"
            
        return msg

    async def _handle_add_homework(self, result: dict, user_id: int, user_lessons: list) -> str:
        """Ödev ekleme"""
        ders_adi = result.get('subject')
        aciklama = result.get('description')
        teslim_tarihi = result.get('due_date')
        
        lesson_id = self._find_lesson_id(ders_adi, user_lessons)
        
        if not lesson_id:
            return f"❌ '{ders_adi}' dersini bulamadım."
            
        db.add_homework(user_id, lesson_id, aciklama, teslim_tarihi)
        
        return f"✅ *Ödev Eklendi!*\n\n📚 Ders: {ders_adi}\n📝 {aciklama}\n📅 Teslim: {teslim_tarihi}"

    async def _handle_complete_homework(self, result: dict, user_id: int) -> str:
        """Ödev tamamlama"""
        homework_id = result.get('homework_id') # AI bunu tahmin edemeyebilir, bu yüzden basitleştirilmiş bir akış gerekebilir
        # Şimdilik sadece son ödevi tamamla veya listele
        pending = db.get_pending_homeworks(user_id)
        if not pending:
            return "Tamamlanacak ödevin yok! 🎉"
            
        # Eğer AI spesifik bir ödev ID bulamadıysa, kullanıcıya listeyi gösterelim
        return "Hangi ödevi tamamladın? `/odevlerim` yazarak ID'sini görebilirsin."

    async def _handle_show_stats(self, result: dict, user_id: int) -> str:
        """İstatistik gösterme"""
        period = result.get('period', 'today')
        
        if period == 'today':
            studies = db.get_today_study_records(user_id)
            questions = db.get_today_question_stats(user_id)
            title = "Bugünkü"
        else:
            studies = db.get_study_records(user_id, days=7)
            questions = db.get_question_stats(user_id, days=7)
            title = "Bu Haftaki"
            
        # Basit hesaplama
        total_time = sum(s['sure_dakika'] for s in studies)
        total_questions = questions['toplam']
        
        return f"📊 *{title} İstatistiklerin*\n\n⏱️ Çalışma: {total_time} dakika\n✏️ Soru: {total_questions} adet"

    def _find_lesson_id(self, match_name: str, lessons: list):
        """Ders isminden ID bul (Fuzzy matching basitleştirilmiş)"""
        if not match_name:
            return None
            
        match_name = match_name.lower().strip()
        
        for lesson in lessons:
            ders_adi = lesson['ders_adi'].lower()
            ders_kodu = lesson['ders_kodu'].lower()
            
            if match_name in ders_adi or match_name in ders_kodu:
                return lesson['id']
                
            # Kısa kod eşleştirme (MAT -> Matematik)
            if match_name in ['mat', 'matematik'] and ('mat' in ders_kodu or 'mat' in ders_adi):
                return lesson['id']
            if match_name in ['fiz', 'fizik'] and ('fiz' in ders_kodu or 'fiz' in ders_adi):
                return lesson['id']
                
        return None

    # --- Command Handlers ---
    
    async def load_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders programını yükle - varsayılan program veya CSV bilgisi"""
        user_id = update.effective_user.id
        
        # Zaten yüklü mü kontrol et
        lessons = db.get_user_lessons(user_id)
        if lessons:
            await update.message.reply_text(
                "⚠️ Ders programın zaten yüklü!\n\nMevcut derslerini görmek için `/derslerim` kullan.\nProgramı sıfırlamak için `/program_sifirla` kullan.",
                parse_mode='Markdown'
            )
            return
        
        # CSV yükleme bilgisi ver
        await update.message.reply_text(
            "📚 *Ders Programı Yükleme*\\n\\n"
            "Kendi ders programını yüklemek için bana bir CSV dosyası gönder.\\n\\n"
            "*CSV Formatı:*\\n"
            "```\\ngun,saat_no,baslangic,bitis,ders_kodu,ders_adi,ogretmen\\n"
            "pazartesi,1,08:30,09:10,MAT,Matematik,Ali Hoca\\n"
            "pazartesi,2,09:25,10:05,FIZ,Fizik,Veli Hoca\\n```\\n\\n"
            "*Gün isimleri:* pazartesi, sali, carsamba, persembe, cuma\\n\\n"
            "💡 Not: Öğretmen sütunu opsiyoneldir.",
            parse_mode='Markdown'
        )

    async def reset_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders programını sıfırla"""
        user_id = update.effective_user.id
        
        # Onay iste (Basit versiyon: direkt siler, gerçek uygulamada butonlu onay eklenebilir)
        # Şimdilik direkt silelim ama uyarı verelim
        success = loader.clear_user_schedule(user_id)
        
        if success:
            await update.message.reply_text("🗑️ Ders programın ve tüm ders verilerin silindi. Yeni program yüklemek için `/program_yukle` kullanabilirsin.")
        else:
            await update.message.reply_text("❌ Bir hata oluştu.")

    async def handle_csv_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """CSV dosyasından ders programı yükle"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("📄 CSV dosyası işleniyor...")
        
        try:
            # Dosyayı indir
            file = await context.bot.get_file(update.message.document.file_id)
            file_bytes = await file.download_as_bytearray()
            
            # UTF-8 ile decode et
            try:
                csv_content = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                csv_content = file_bytes.decode('utf-8-sig')  # BOM varsa
            
            # CSV'den program yükle
            result = loader.load_schedule_from_csv(user_id, csv_content)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ *Ders Programı Yüklendi!*\\n\\n"
                    f"📚 {result['ders_sayisi']} ders eklendi\\n"
                    f"📅 {result['program_sayisi']} program girişi eklendi\\n\\n"
                    f"Artık 'Bugün hangi derslerim var?' diye sorabilirsin!",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ *Hata:* {result['message']}\\n\\n"
                    "CSV formatının doğru olduğundan emin ol.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Dosya işleme hatası: {str(e)}")

    async def list_lessons_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lessons = db.get_user_lessons(user_id)
        
        if not lessons:
            await update.message.reply_text("Henüz kayıtlı dersin yok.")
            return
            
        response = "*📚 Derslerin:*\n\n"
        for lesson in lessons:
            response += f"• *{lesson['ders_kodu']}* - {lesson['ders_adi']}"
            if lesson['ogretmen']:
                response += f" ({lesson['ogretmen']})"
            response += "\n"
            
        await update.message.reply_text(response, parse_mode='Markdown')

    async def list_homeworks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        homeworks = db.get_pending_homeworks(user_id)
        
        response = ai.format_homeworks(homeworks)
        await update.message.reply_text(response, parse_mode='Markdown')

    async def show_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Son 7 günün istatistikleri
        study_records = db.get_study_records(user_id, days=7)
        question_stats = db.get_question_stats(user_id, days=7)
        
        response = "*📊 Haftalık İstatistikler*\n\n"
        
        if study_records:
            total_time = sum(s['sure_dakika'] for s in study_records)
            response += f"⏱️ *Toplam Çalışma:* {total_time} dakika\n"
        else:
            response += "⏱️ Henüz çalışma kaydı yok.\n"
            
        if question_stats['toplam'] > 0:
            response += f"✏️ *Toplam Soru:* {question_stats['toplam']} ({question_stats['dogru']} D / {question_stats['yanlis']} Y)\n"
        else:
            response += "✏️ Henüz soru çözümü yok.\n"
            
        await update.message.reply_text(response, parse_mode='Markdown')

    async def today_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        today_studies = db.get_today_study_records(user_id)
        today_questions = db.get_today_question_stats(user_id)
        
        response = f"*Bugünkü Özet ({date.today().strftime('%d.%m.%Y')})*\n\n"
        
        if today_studies:
            response += "*Çalışmalar:*\n"
            for study in today_studies:
                response += f"- {study['ders_adi']}\n"
            response += "\n"
        else:
            response += "Bugün henüz çalışma kaydın yok.\n\n"
        
        if today_questions['toplam'] > 0:
            response += f"*Sorular:* {today_questions['toplam']} soru\n"
        else:
            response += "Bugün henüz soru çözmedin.\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def weekly_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Haftalık detaylı özet"""
        user_id = update.effective_user.id
        
        # Son 7 günün verileri
        study_records = db.get_study_records(user_id, days=7)
        question_stats = db.get_question_stats(user_id, days=7)
        
        response = "*📅 Bu Haftanın Özeti*\n\n"
        
        # Çalışma istatistikleri
        if study_records:
            from collections import defaultdict
            ders_sayaci = defaultdict(int)
            toplam_sure = 0
            
            for study in study_records:
                ders_sayaci[study['ders_adi']] += 1
                if study.get('sure_dakika'):
                    toplam_sure += study['sure_dakika']
            
            response += "*Ders Bazında:*\n"
            for ders, sayi in sorted(ders_sayaci.items(), key=lambda x: x[1], reverse=True):
                response += f"• {ders}: {sayi} kez\n"
            
            if toplam_sure > 0:
                saat = toplam_sure // 60
                dakika = toplam_sure % 60
                response += f"\n⏱️ Toplam Süre: {saat}sa {dakika}dk\n"
            
            response += "\n"
        else:
            response += "📚 Bu hafta çalışma kaydın yok.\n\n"
        
        # Soru istatistikleri
        if question_stats['toplam'] > 0:
            response += f"✏️ *Sorular:* {question_stats['toplam']} soru\n\n"
            if question_stats['ders_bazinda']:
                response += "*Ders Bazında:*\n"
                for ders in question_stats['ders_bazinda']:
                    response += f"• {ders['ders_adi']}: {ders['toplam']} soru"
                    if ders.get('konular'):
                        response += f" ({ders['konular']})"
                    response += "\n"
        else:
            response += "✏️ Bu hafta soru çözmedin.\n"
        
        if not study_records and question_stats['toplam'] == 0:
            response += "\n💪 Hadi, bu hafta biraz çalış!"
        else:
            response += "\n🎉 Böyle devam et!"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    def register_handlers(self, application: Application):
        """Ders modülü özel handler'ları"""
        from telegram.ext import CommandHandler, MessageHandler, filters
        
        application.add_handler(CommandHandler("program_yukle", self.load_schedule_command))
        application.add_handler(CommandHandler("program_sifirla", self.reset_schedule_command))
        application.add_handler(CommandHandler("derslerim", self.list_lessons_command))
        application.add_handler(CommandHandler("odevlerim", self.list_homeworks_command))
        application.add_handler(CommandHandler("istatistik", self.show_stats_command))
        application.add_handler(CommandHandler("bugun", self.today_summary_command))
        application.add_handler(CommandHandler("gunluk", self.today_summary_command))
        application.add_handler(CommandHandler("haftalik", self.weekly_summary_command))
        application.add_handler(CommandHandler("bu_hafta", self.weekly_summary_command))
        
        # CSV dosya handler
        application.add_handler(MessageHandler(
            filters.Document.MimeType("text/csv") | filters.Document.FileExtension("csv"),
            self.handle_csv_document
        ))
