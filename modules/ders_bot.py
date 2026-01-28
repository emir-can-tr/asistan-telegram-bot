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
        
        # Yanıtı gönder
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(response.replace('*', '').replace('_', ''))
    
    # ==================== YARDIMCI METODLAR ====================
    
    async def _handle_query_schedule(self, result: dict, user_id: int) -> str:
        """Program sorgulama"""
        gun = result.get('gun', 'bugün')
        saat_no = result.get('saat_no')
        
        # Gün adını normalize et
        gun_map = {
            'bugün': datetime.now().strftime('%A').lower(),
            'yarın': (datetime.now().weekday() + 1) % 7,
            'pazartesi': 'pazartesi',
            'salı': 'sali',
            'sali': 'sali',
            'çarşamba': 'çarşamba',
            'carşamba': 'çarşamba',
            'perşembe': 'perşembe',
            'persembe': 'perşembe',
            'cuma': 'cuma',
        }
        
        # İngilizce gün adlarını Türkçe'ye çevir
        weekday_names = ['pazartesi', 'sali', 'çarşamba', 'perşembe', 'cuma', 'cumartesi', 'pazar']
        if gun == 'bugün':
            gun = weekday_names[datetime.now().weekday()]
        elif gun == 'yarın':
            gun = weekday_names[(datetime.now().weekday() + 1) % 7]
        else:
            gun = gun_map.get(gun, gun)
        
        # Saat numarasına göre sorgulama
        if saat_no:
            entry = db.get_schedule_by_hour(user_id, gun, saat_no)
            if entry:
                response = f"📚 *{gun.title()} {saat_no}. Saat:*\n\n"
                response += f"{entry['ders_kodu']} - {entry['ders_adi']}\n"
                response += f"⏰ {entry['baslangic_saati']}-{entry['bitis_saati']}\n"
                if entry.get('ogretmen'):
                    response += f"👨‍🏫 {entry['ogretmen']}"
            else:
                response = f"📅 {gun.title()} günü {saat_no}. saatte ders yok."
        else:
            # Günün tüm programı
            schedule = db.get_schedule_for_day(user_id, gun)
            response = ai.format_schedule(schedule)
        
        return response
    
    async def _handle_add_study(self, result: dict, user_id: int, user_lessons: list) -> str:
        """Çalışma kaydı ekleme"""
        lesson_search = result.get('lesson_search', '')
        konu = result.get('konu')
        sure_dakika = result.get('sure_dakika')
        
        if not lesson_search:
            return "❌ Hangi dersi çalıştığını belirtmelisin. Örnek: 'Matematik çalıştım'"
        
        # Dersi bul
        lesson = db.get_lesson_by_code_or_name(user_id, lesson_search)
        if not lesson:
            return f"❌ '{lesson_search}' dersi bulunamadı. `/derslerim` komutu ile derslerini görebilirsin."
        
        # Kaydı ekle
        db.add_study_record(
            user_id=user_id,
            lesson_id=lesson['id'],
            konu=konu,
            sure_dakika=sure_dakika
        )
        
        response = f"✅ *{lesson['ders_adi']}* çalışman kaydedildi!\n\n"
        if konu:
            response += f"📖 Konu: {konu}\n"
        if sure_dakika:
            saat = sure_dakika // 60
            dakika = sure_dakika % 60
            if saat > 0:
                response += f"⏱️ Süre: {saat} saat"
                if dakika > 0:
                    response += f" {dakika} dakika"
            elif dakika > 0:
                response += f"⏱️ Süre: {dakika} dakika"
        
        response += "\n\nBöyle devam! 💪"
        return response
    
    async def _handle_add_questions(self, result: dict, user_id: int, user_lessons: list) -> str:
        """Soru çözümü kaydı ekleme"""
        lesson_search = result.get('lesson_search', '')
        konu = result.get('konu')
        soru_sayisi = result.get('soru_sayisi')
        
        if not lesson_search:
            return "❌ Hangi dersten soru çözdüğünü belirtmelisin. Örnek: 'Matematik'ten 15 soru çözdüm'"
        
        if not soru_sayisi:
            return "❌ Kaç soru çöz düğünü belirtmelisin. Örnek: '15 soru'"
        
        # Dersi bul
        lesson = db.get_lesson_by_code_or_name(user_id, lesson_search)
        if not lesson:
            return f"❌ '{lesson_search}' dersi bulunamadı."
        
        # Kaydı ekle
        db.add_question_record(
            user_id=user_id,
            lesson_id=lesson['id'],
            soru_sayisi=soru_sayisi,
            konu=konu
        )
        
        response = f"✅ *{soru_sayisi} {lesson['ders_adi']} sorusu* kaydedildi!\n\n"
        if konu:
            response += f"📖 Konu: {konu}\n"
        
        response += "\nHarika gidiyorsun! 🎯"
        return response
    
    async def _handle_add_homework(self, result: dict, user_id: int, user_lessons: list) -> str:
        """Ödev ekleme"""
        lesson_search = result.get('lesson_search')
        homework_title = result.get('homework_title', '')
        homework_description = result.get('homework_description')
        homework_due_date = result.get('homework_due_date')
        
        if not homework_title:
            return "❌ Ödev başlığı belirtmelisin. Örnek: 'Matematik ödevi var cuma teslim'"
        
        if not homework_due_date:
            return "❌ Son tarihi belirtmelisin. Örnek: 'cuma', 'yarın', '2026-01-05'"
        
        # Dersi bul (opsiyonel)
        lesson_id = None
        if lesson_search:
            lesson = db.get_lesson_by_code_or_name(user_id, lesson_search)
            if lesson:
                lesson_id = lesson['id']
        
        # Tarihi parse et
        try:
            due_date = datetime.strptime(homework_due_date, '%Y-%m-%d').date()
        except:
            # Basit tarih parse
            if homework_due_date.lower() in ['bugün', 'bugun']:
                due_date = date.today()
            elif homework_due_date.lower() in ['yarın', 'yarin']:
                from datetime import timedelta
                due_date = date.today() + timedelta(days=1)
            else:
                return f"❌ Tarih formatı anlaşılamadı: {homework_due_date}"
        
        # Ödevi ekle
        db.add_homework(
            user_id=user_id,
            lesson_id=lesson_id,
            baslik=homework_title,
            aciklama=homework_description,
            bitis_tarihi=due_date
        )
        
        response = f"✅ *Ödev eklendi!*\n\n📝 {homework_title}\n"
        if homework_description:
            response += f"📄 {homework_description}\n"
        response += f"📅 Son tarih: {due_date.strftime('%d.%m.%Y')}"
        
        return response
    
    async def _handle_complete_homework(self, result: dict, user_id: int) -> str:
        """Ödev tamamlama"""
        homework_search = result.get('homework_search', '')
        
        if not homework_search:
            return "❌ Hangi ödevi tamamladığını belirtmelisin."
        
        # Ödevi bul
        homework = db.get_homework_by_title(user_id, homework_search)
        if not homework:
            return f"❌ '{homework_search}' ile eşleşen bir ödev bulunamadı."
        
        # Tamamla
        db.complete_homework(homework['id'])
        
        return f"🎉 *'{homework['baslik']}'* ödevi tamamlandı!\n\nTebrikler! 🎊"
    
    async def _handle_show_stats(self, result: dict, user_id: int) -> str:
        """İstatistikleri göster"""
        # Çalışma kayıtları
        study_records = db.get_study_records(user_id, days=7)
        study_text = ai.format_study_records(study_records)
        
        # Soru istatistikleri
        question_stats = db.get_question_stats(user_id, days=7)
        stats_text = ai.format_question_stats(question_stats)
        
        return f"{study_text}\n\n{stats_text}"
    
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
    
    async def load_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders programını yükle - varsayılan program veya CSV bilgisi"""
        user_id = update.effective_user.id
        
        # Zaten yüklü mü kontrol et
        lessons = db.get_user_lessons(user_id)
        if lessons:
            await update.message.reply_text(
                "⚠️ Ders programın zaten yüklü!\n\n"
                "Mevcut derslerini görmek için `/derslerim` kullan.\n"
                "Programı sıfırlamak için `/program_sifirla` kullan.",
                parse_mode='Markdown'
            )
            return
        
        # CSV yükleme bilgisi ver
        await update.message.reply_text(
            "📚 *Ders Programı Yükleme*\n\n"
            "Kendi ders programını yüklemek için bana bir CSV dosyası gönder.\n\n"
            "*CSV Formatı:*\n"
            "```\ngun,saat_no,baslangic,bitis,ders_kodu,ders_adi,ogretmen\n"
            "pazartesi,1,08:30,09:10,MAT,Matematik,Ali Hoca\n"
            "pazartesi,2,09:25,10:05,FIZ,Fizik,Veli Hoca\n```\n\n"
            "*Gün isimleri:* pazartesi, sali, carsamba, persembe, cuma\n\n"
            "💡 Not: Öğretmen sütunu opsiyoneldir.",
            parse_mode='Markdown'
        )
    
    async def reset_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ders programını sıfırla"""
        user_id = update.effective_user.id
        
        lessons = db.get_user_lessons(user_id)
        if not lessons:
            await update.message.reply_text(
                "❌ Zaten ders programın yok.\n\n"
                "Yeni program yüklemek için `/program_yukle` kullan.",
                parse_mode='Markdown'
            )
            return
        
        # Programı sil
        loader.clear_user_schedule(user_id)
        
        await update.message.reply_text(
            "✅ *Ders programın sıfırlandı!*\n\n"
            "Tüm dersler ve program verileri silindi.\n\n"
            "Yeni program yüklemek için `/program_yukle` kullan veya CSV dosyası gönder.",
            parse_mode='Markdown'
        )
    
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
                    f"✅ *Ders Programı Yüklendi!*\n\n"
                    f"📚 {result['ders_sayisi']} ders eklendi\n"
                    f"📅 {result['program_sayisi']} program girişi eklendi\n\n"
                    f"Artık 'Bugün hangi derslerim var?' diye sorabilirsin!",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ *Hata:* {result['message']}\n\n"
                    "CSV formatının doğru olduğundan emin ol.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Dosya işleme hatası: {str(e)}")
   
    async def list_lessons_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dersleri listele"""
        user_id = update.effective_user.id
        lessons = db.get_user_lessons(user_id)
        
        if not lessons:
            await update.message.reply_text(
                "❌ Henüz ders eklenmemiş!\n\n`/program_yukle` ile programını yükle.",
                parse_mode='Markdown'
            )
            return
        
        response = f"📚 *Derslerim ({len(lessons)} ders):*\n\n"
        for lesson in lessons:
            response += f"• *{lesson['ders_kodu']}* - {lesson['ders_adi']}\n"
            if lesson.get('ogretmen'):
                response += f"  👨‍🏫 {lesson['ogretmen']}\n"
            if lesson.get('haftalik_saat'):
                response += f"  ⏰ {lesson['haftalik_saat']} saat/hafta\n"
            response += "\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def list_homeworks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ödevleri listele"""
        user_id = update.effective_user.id
        homeworks = db.get_pending_homeworks(user_id)
        response = ai.format_homeworks(homeworks)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def show_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İstatistikleri göster (haftalık)"""
        user_id = update.effective_user.id
        
        # Çalışma kayıtları
        study_records = db.get_study_records(user_id, days=7)
        study_text = ai.format_study_records(study_records)
        
        # Soru istatistikleri
        question_stats = db.get_question_stats(user_id, days=7)
        stats_text = ai.format_question_stats(question_stats)
        
        response = f"{study_text}\n\n{stats_text}"
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def today_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bugünkü özet"""
        user_id = update.effective_user.id
        
        # Bugünkü çalışmalar
        today_studies = db.get_today_study_records(user_id)
        
        # Bugünkü sorular
        today_questions = db.get_today_question_stats(user_id)
        
        from datetime import date
        today_str = date.today().strftime("%d.%m.%Y")
        
        response = f"📅 *Bugünkü Özet ({today_str})*\n\n"
        
        # Çalışmalar
        if today_studies:
            response += "📚 *Çalışmalar:*\n"
            for study in today_studies:
                response += f"• {study['ders_adi']}"
                if study.get('konu'):
                    response += f" - {study['konu']}"
                if study.get('sure_dakika'):
                    sure = study['sure_dakika']
                    saat = sure // 60
                    dakika = sure % 60
                    if saat > 0:
                        response += f" ({saat}sa"
                        if dakika > 0:
                            response += f" {dakika}dk"
                        response += ")"
                    elif dakika > 0:
                        response += f" ({dakika}dk)"
                response += "\n"
            response += "\n"
        else:
            response += "📚 Bugün henüz çalışma kaydın yok.\n\n"
        
        # Sorular
        if today_questions['toplam'] > 0:
            response += f"✏️ *Sorular:* {today_questions['toplam']} soru\n"
            if today_questions['ders_bazinda']:
                for ders in today_questions['ders_bazinda']:
                    response += f"  • {ders['ders_adi']}: {ders['toplam']} soru"
                    if ders.get('konular'):
                        response += f" ({ders['konular']})"
                    response += "\n"
        else:
            response += "✏️ Bugün henüz soru çözmedin.\n"
        
        if not today_studies and today_questions['toplam'] == 0:
            response += "\n💪 Hadi, bugün biraz çalış!"
        elif today_questions['toplam'] > 0 or today_studies:
            response += "\n🎉 Harika gidiyorsun!"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def weekly_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Haftalık özet"""
        user_id = update.effective_user.id
        
        # Haftalık çalışmalar
        study_records = db.get_study_records(user_id, days=7)
        
        # Haftalık sorular
        question_stats = db.get_question_stats(user_id, days=7)
        
        response = "📊 *Bu Haftanın Özeti (Son 7 Gün)*\n\n"
        
        # Çalışma istatistikleri
        if study_records:
            response += f"📚 *Çalışmalar:* {len(study_records)} kayıt\n\n"
            # Ders bazında grupla
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
