"""
Not Defteri AI Servisi
"""
import google.generativeai as genai
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import GEMINI_API_KEY
import json
from typing import Dict, Any

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_note_message(message: str) -> Dict[str, Any]:
    prompt = f"""Not defteri asistanısın. Mesajı analiz et.

MESAJ: {message}

AKSİYONLAR:
- add_note: "Not ekle: ...", "İş kategorisinde not: ..." gibi
- search_note: "Python notları", "İş kategorisindeki notlar" gibi
- list_notes: "Notlarım", "Tüm notlar" gibi
- list_favorites: "Favoriler", "Favori notlar" gibi
- show_categories: "Kategoriler", "Kategori listesi" gibi

JSON:
{{
    "action": "action_name",
    "response": "Yanıt",
    "baslik": "not başlığı (varsa)",
    "icerik": "not içeriği (varsa)",
    "kategori": "Genel/İş/Kişisel/Okul/Fikir (varsa)",
    "search_keyword": "arama kelimesi (varsa)"
}}

SADECE JSON ver:"""
    
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

def format_notes_list(notes: list) -> str:
    if not notes:
        return "📝 Not yok."
    
    response = f"📝 *Notlarım ({len(notes)}):*\n\n"
    
    for note in notes[:20]:
        fav = "⭐ " if note['is_favorite'] else ""
        response += f"{fav}*{note['baslik']}*\n"
        response += f"📁 {note['kategori_path']}\n"
        if len(note['icerik']) > 100:
            response += f"{note['icerik'][:100]}...\n"
        else:
            response += f"{note['icerik']}\n"
        response += "\n"
    
    if len(notes) > 20:
        response += f"... ve {len(notes)-20} not daha"
    
    return response.strip()

def format_categories(categories: list) -> str:
    if not categories:
        return "📁 Kategori yok."
    
    response = "📁 *Kategoriler:*\n\n"
    
    for cat in categories:
        response += f"• {cat['kategori_path']}: {cat['sayi']} not\n"
    
    return response.strip()
