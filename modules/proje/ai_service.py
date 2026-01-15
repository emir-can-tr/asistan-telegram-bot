"""
Proje AI Service
"""
import google.generativeai as genai
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import GEMINI_API_KEY
import json

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_proje_message(message: str):
    prompt = f"""Proje yönetim asistanısın. Analiz et.

MESAJ: {message}

AKSİYONLAR:
- add_project: "Web sitesi projesi oluştur" gibi
- add_milestone: "Backend milestone ekle" gibi
- add_task: "API task ekle" gibi
- complete_task: "API tamamlandı" gibi
- show_progress: "Proje durumu", "İlerleme" gibi
- list_projects: "Projelerim" gibi

JSON:
{{
    "action": "action_name",
    "response": "Yanıt",
    "project_name": "proje adı (varsa)",
    "milestone_name": "milestone adı (varsa)",
    "task_name": "task adı (varsa)"
}}

SADECE JSON:"""
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        result = json.loads(result_text)
        if 'response' not in result:
            result['response'] = "Anladım!"
        return result
    except:
        return {'action': 'chat', 'response': 'Anlayamadım?'}

def format_projects(projects: list):
    if not projects:
        return "🚀 Proje yok."
    
    response = f"🚀 *Projelerim ({len(projects)}):*\n\n"
    for p in projects:
        response += f"• *{p['name']}*\n"
        if p.get('description'):
            response += f"  📝 {p['description']}\n"
        response += f"  📊 {p['status']}\n\n"
    return response.strip()
