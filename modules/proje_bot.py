"""
Proje Bot - Proje yonetimi, milestone, task takibi
"""
from telegram import Update
from telegram.ext import Application, ContextTypes
from modules.base_module import BaseModule
from modules.proje import database as db
from modules.proje import ai_service as ai

class ProjeBot(BaseModule):
    
    def get_module_name(self) -> str:
        return "proje"
    
    def get_module_description(self) -> str:
        return "Proje yonetimi, milestone ve task takibi."
    
    def get_module_emoji(self) -> str:
        return "🚀"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        projects = db.get_user_projects(user_id)
        
        welcome = f"""
{self.module_emoji} *Proje Modulune Hos Geldin!*

*Durum:* {len(projects)} proje

*Ozellikler:*
- Proje olusturma
- Milestone takibi
- Task yonetimi
- Ilerleme raporlari

*Komutlar:*
/proje_ekle - Yeni proje
/projelerim - Tum projeler
/proje_durum - Ilerleme

*Ornekler:*
- "Web sitesi projesi olustur"
- "Backend milestone ekle"
- "API task tamamlandi"
"""
        
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        message_text = update.message.text
        user_id = db_user['telegram_id']
        
        result = ai.analyze_proje_message(message_text)
        action = result.get('action', 'chat')
        response = result.get('response', 'Anladim!')
        
        if action == "add_project":
            project_name = result.get('project_name', '')
            if project_name:
                db.add_project(user_id, project_name)
                response = f"*{project_name}* projesi olusturuldu!"
        
        elif action == "list_projects":
            projects = db.get_user_projects(user_id)
            response = ai.format_projects(projects)
        
        try:
            await update.message.reply_text(response, parse_mode='Markdown')
        except:
            await update.message.reply_text(response.replace('*', ''))
    
    def register_handlers(self, application: Application):
        from telegram.ext import CommandHandler
        application.add_handler(CommandHandler("proje_ekle", self.add_project_cmd))
        application.add_handler(CommandHandler("projelerim", self.list_projects_cmd))
    
    async def add_project_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Proje adini yaz:\nWeb Sitesi Projesi", parse_mode='Markdown')
    
    async def list_projects_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        projects = db.get_user_projects(user_id)
        response = ai.format_projects(projects)
        await update.message.reply_text(response, parse_mode='Markdown')
