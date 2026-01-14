"""
Asistan Bot Modulu
Aliskanlik takibi, hatirlatmalar, gorevler ve notlar
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
import database
import ai_service


class AsistanBot(BaseModule):
    """Kisisel asistan modulu"""
    
    def get_module_name(self) -> str:
        return "asistan"
    
    def get_module_description(self) -> str:
        return "Aliskanliklarini takip et, hatirlatmalar kur, gorevleri yonet, not al."
    
    def get_module_emoji(self) -> str:
        return "🤖"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Asistan modulu baslatma"""
        user = update.effective_user
        
        welcome_message = f"""
{self.module_emoji} *Asistan Modulune Hos Geldin {user.first_name}!*

Bu modulde:
- Aliskanlik ekle ve takip et
- Hatirlatma kur
- Gorev listesi olustur
- Not al ve yonet

*Ornek komutlar:*
- "Her gun 2 litre su icmek istiyorum"
- "Saat 15:00'da ilacimi hatir lat"
- "Goreve market alisverisi ekle"
- "Aliskanliklarimi goster"

Benimle dogal bir sekilde konusabilirsin!
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        """Asistan modulu mesaj isleyici"""
        message_text = update.message.text
        
        user_habits = database.get_user_habits(db_user['id'])
        conversation_history = database.get_conversation_history(db_user['id'], limit=10)
        
        result = await ai_service.analyze_message(message_text, user_habits, conversation_history)
        
        action = result.get('action', 'chat')
        response = result.get('response', 'Bir hata olustu.')
        
        if action == "add_habit":
            response = await self._handle_add_habit(result, db_user)
        elif action == "complete_habit":
            response = await self._handle_complete_habit(result, db_user)
        elif action == "list_habits":
            response = ai_service.format_habits_list(user_habits)
        elif action == "delete_habit":
            response = await self._handle_delete_habit(result, db_user)
        elif action == "show_history":
            response = await self._handle_show_history(result, db_user)
        elif action == "show_today":
            summary = database.get_daily_summary(db_user['id'])
            response = ai_service.format_today_summary(summary)
        elif action == "add_reminder":
            response = await self._handle_add_reminder(result, db_user)
        elif action == "list_reminders":
            reminders = database.get_user_reminders(db_user['id'])
            response = ai_service.format_reminders_list(reminders)
        elif action == "delete_reminder":
            response = await self._handle_delete_reminder(result, db_user)
        elif action == "add_task":
            response = await self._handle_add_task(result, db_user)
        elif action == "list_tasks":
            tasks = database.get_user_tasks(db_user['id'])
            response = ai_service.format_tasks_list(tasks)
        elif action == "complete_task":
            response = await self._handle_complete_task(result, db_user)
        elif action == "delete_task":
            response = await self._handle_delete_task(result, db_user)
        elif action == "add_note":
            response = await self._handle_add_note(result, db_user)
        elif action == "list_notes":
            notes = database.get_user_notes(db_user['id'])
            response = ai_service.format_notes_list(notes)
        elif action == "delete_note":
            response = await self._handle_delete_note(result, db_user)
        
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(response.replace('*', '').replace('_', ''))
        
        database.add_conversation_message(db_user['id'], 'user', message_text)
        database.add_conversation_message(db_user['id'], 'assistant', response[:500])
        database.clear_old_conversation_history(db_user['id'], keep_last=20)
    
    async def _handle_add_habit(self, result: dict, db_user: dict) -> str:
        habit_name = result.get('habit_name', '')
        frequency = result.get('frequency', 'daily')
        target = result.get('target', '')
        
        if habit_name:
            database.add_habit(
                user_id=db_user['id'],
                name=habit_name,
                frequency=frequency,
                target=target
            )
            response = f"*'{habit_name}'* aliskanligi basariyla eklendi!\n\n"
            if target:
                response += f"Hedef: {target}\n"
            freq_text = {"daily": "Gunluk", "weekly": "Haftalik", "monthly": "Aylik"}
            response += f"Siklik: {freq_text.get(frequency, frequency)}"
            return response
        return "Aliskanlik adi belirtilmedi."
    
    async def _handle_complete_habit(self, result: dict, db_user: dict) -> str:
        habit_name = result.get('habit_name', '')
        
        if habit_name:
            habit = database.get_habit_by_name(db_user['id'], habit_name)
            
            if habit:
                if database.is_habit_completed_today(habit['id']):
                    return f"*'{habit['name']}'* zaten bugun icin tamamlanmis."
                else:
                    database.complete_habit(habit['id'])
                    return f"Harika! *'{habit['name']}'* tamamlandi olarak isaretlendi!"
            else:
                return f"'{habit_name}' adinda bir aliskanlik bulunamadi."
        return "Aliskanlik adi belirtilmedi."
    
    async def _handle_delete_habit(self, result: dict, db_user: dict) -> str:
        habit_name = result.get('habit_name', '')
        
        if habit_name:
            habit = database.get_habit_by_name(db_user['id'], habit_name)
            
            if habit:
                database.delete_habit(habit['id'])
                return f"*'{habit['name']}'* aliskanligi silindi."
            else:
                return f"'{habit_name}' adinda bir aliskanlik bulunamadi."
        return "Silinecek aliskanlik belirtilmedi."
    
    async def _handle_show_history(self, result: dict, db_user: dict) -> str:
        days = result.get('days', 7)
        if isinstance(days, str):
            try:
                days = int(days)
            except:
                days = 7
        history = database.get_habit_history(db_user['id'], days)
        return ai_service.format_history(history, days)
    
    async def _handle_add_reminder(self, result: dict, db_user: dict) -> str:
        from datetime import date
        
        reminder_title = result.get('reminder_title', '')
        remind_at = result.get('remind_at', '')
        remind_date_str = result.get('remind_date', None)
        is_recurring = result.get('is_recurring', False)
        
        if reminder_title and remind_at:
            try:
                parts = remind_at.split(':')
                if len(parts) == 2:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        remind_at = f"{hour:02d}:{minute:02d}"
                        
                        remind_date = None
                        date_text = "Bugun"
                        if remind_date_str and remind_date_str != "null":
                            try:
                                remind_date = date.fromisoformat(remind_date_str)
                                date_text = remind_date.strftime("%d.%m.%Y")
                            except:
                                pass
                        
                        database.add_reminder(
                            user_id=db_user['id'],
                            title=reminder_title,
                            remind_at=remind_at,
                            remind_date=remind_date,
                            is_recurring=is_recurring
                        )
                        
                        if is_recurring:
                            return f"*Hatirlatma eklendi!*\n\n{reminder_title}\nHer gun saat {remind_at}"
                        else:
                            return f"*Hatirlatma eklendi!*\n\n{reminder_title}\n{date_text}\nSaat: {remind_at}"
            except:
                pass
        return "Hatirlatma icin baslik ve saat gerekli."
    
    async def _handle_delete_reminder(self, result: dict, db_user: dict) -> str:
        reminder_title = result.get('reminder_title', '')
        
        if reminder_title:
            reminder = database.get_reminder_by_title(db_user['id'], reminder_title)
            
            if reminder:
                database.delete_reminder(reminder['id'])
                return f"*'{reminder['title']}'* hatirlatmasi silindi."
            else:
                return f"'{reminder_title}' ile eslesen bir hatirlatma bulunamadi."
        return "Silinecek hatirlatma belirtilmedi."
    
    async def _handle_add_task(self, result: dict, db_user: dict) -> str:
        from datetime import date
        
        task_title = result.get('task_title', '')
        task_due_date_str = result.get('task_due_date', None)
        
        if task_title:
            due_date = None
            date_text = ""
            if task_due_date_str and task_due_date_str != "null":
                try:
                    due_date = date.fromisoformat(task_due_date_str)
                    date_text = f"\nSon tarih: {due_date.strftime('%d.%m.%Y')}"
                except:
                    pass
            
            database.add_task(
                user_id=db_user['id'],
                title=task_title,
                due_date=due_date
            )
            return f"*Gorev eklendi!*\n\n{task_title}{date_text}"
        return "Gorev icin baslik gerekli."
    
    async def _handle_complete_task(self, result: dict, db_user: dict) -> str:
        task_title = result.get('task_title', '')
        
        if task_title:
            task = database.get_task_by_title(db_user['id'], task_title)
            
            if task:
                database.complete_task(task['id'])
                return f"*'{task['title']}'* gorevi tamamlandi!"
            else:
                return f"'{task_title}' ile eslesen bir gorev bulunamadi."
        return "Tamamlanacak gorev belirtilmedi."
    
    async def _handle_delete_task(self, result: dict, db_user: dict) -> str:
        task_title = result.get('task_title', '')
        
        if task_title:
            task = database.get_task_by_title(db_user['id'], task_title)
            
            if task:
                database.delete_task(task['id'])
                return f"*'{task['title']}'* gorevi silindi."
            else:
                return f"'{task_title}' ile eslesen bir gorev bulunamadi."
        return "Silinecek gorev belirtilmedi."
    
    async def _handle_add_note(self, result: dict, db_user: dict) -> str:
        note_content = result.get('note_content', '')
        
        if note_content:
            database.add_note(
                user_id=db_user['id'],
                content=note_content
            )
            return f"*Not kaydedildi!*\n\n{note_content}"
        return "Not icerigi belirtilmedi."
    
    async def _handle_delete_note(self, result: dict, db_user: dict) -> str:
        note_content = result.get('note_content', '')
        
        if note_content:
            note = database.get_note_by_content(db_user['id'], note_content)
            
            if note:
                database.delete_note(note['id'])
                short_content = note['content'][:30] + "..." if len(note['content']) > 30 else note['content']
                return f"Not silindi: {short_content}"
            else:
                return f"'{note_content}' ile eslesen bir not bulunamadi."
        return "Silinecek not belirtilmedi."
    
    def register_handlers(self, application: Application):
        """Asistan modulu handler'larini kaydet"""
        pass
