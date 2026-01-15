"""
Kitap Modülü AI Servisi
Gemini AI ile mesaj analizi
"""
import google.generativeai as genai
import sys
import os
# Config'i root'tan import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import GEMINI_API_KEY
import json
from typing import Dict, Any

# Gemini API'yi yapılandır
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')


def analyze_kitap_message(message: str, user_books: list, context: Dict = None) -> Dict[str, Any]:
    """
    Kullanıcının mesajını analiz et ve uygun aksiyonu belirle
    
    Actions:
    - add_book: Kitap ekleme
    - add_note: Not ekleme
    - add_progress: İlerleme kaydı
    - set_goal: Hedef belirleme
    - show_stats: İstatistikler
    - list_books: Kitapları listele
    - update_status: Durum güncelleme
    - chat: Genel sohbet
    """
    
    # Kullanıcının kitaplarını formatla
    books_text = "\n".join([f"- {b['baslik']} ({b['yazar']}) - {b['durum']}" for b in user_books]) if user_books else "Henüz kitap eklenmemiş"
    
    prompt = f"""Sen bir kitap takip asistanısın. Kullanıcının mesajını analiz et ve ne yapmak istediğini belirle.

KULLANICININ KİTAPLARI:
{books_text}

MESAJ: {message}

GÖREVIN:
1. Kullanıcının ne yapmak istediğini anla
2. Uygun aksiyonu belirle
3. JSON formatında yanıt ver

AKSİYONLAR:
- add_book: "1984 kitabını ekle", "Suç ve Ceza, Dostoyevski, 600 sayfa" gibi yeni kitap eklemeleri
- add_note: "Not ekle", "Bu kitap hakkında not" gibi not eklemeleri
- add_progress: "Bugün 50 sayfa okudum", "100 sayfa okudum" gibi ilerleme kayıtları
- set_goal: "Günde 30 sayfa okumak istiyorum", "Ayda 2 kitap okuma hedefi" gibi hedef belirlemeleri
- show_stats: "Bu ay kaç sayfa okudum?", "İstatistiklerimi göster" gibi istatistik sorguları
- list_books: "Kitaplarımı göster", "Okunacak kitaplar" gibi listeleme istekleri
- update_status: "1984'ü okumaya başladım", "Suç ve Ceza'yı bitirdim" gibi durum güncellemeleri
- chat: Diğer her şey

JSON FORMAT:
{{
    "action": "action_name",
    "response": "Kullanıcıya gösterilecek yanıt (Türkçe, samimi)",
    "book_title": "kitap başlığı (varsa)",
    "book_author": "yazar adı (varsa)",
    "total_pages": toplam sayfa sayısı (varsa),
    "category": "kategori (varsa)",
    "note_text": "not metni (varsa)",
    "pages_read": okunan sayfa sayısı (varsa),
    "goal_type": "gunluk/haftalik/aylik/yillik (varsa)",
    "goal_value": hedef değeri sayı (varsa),
    "status": "okunacak/okunuyor/okundu (varsa)",
    "filter_status": "listele için durum filtresi (varsa)"
}}

ÖRNEKLER:

Mesaj: "1984 kitabını ekle, George Orwell, 328 sayfa"
{{
    "action": "add_book",
    "response": "1984 kitabı eklendi!",
    "book_title": "1984",
    "book_author": "George Orwell",
    "total_pages": 328
}}

Mesaj: "Bugün 50 sayfa okudum"
{{
    "action": "add_progress",
    "response": "50 sayfa kaydedildi!",
    "pages_read": 50
}}

Mesaj: "Günde 30 sayfa okumak istiyorum"
{{
    "action": "set_goal",
    "response": "Günlük 30 sayfa hedefi belirlendi!",
    "goal_type": "gunluk",
    "goal_value": 30
}}

Mesaj: "Bu ay kaç sayfa okudum?"
{{
    "action": "show_stats",
    "response": "İstatistiklerini göstereyim"
}}

Şimdi analiz et ve SADECE JSON yanıt ver:"""
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # JSON'u parse et
        # Markdown code block varsa temizle
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Varsayılan response ekle
        if 'response' not in result:
            result['response'] = "Anladım!"
        
        return result
        
    except Exception as e:
        print(f"AI analiz hatası: {e}")
        return {
            'action': 'chat',
            'response': 'Mesajını anlayamadım, biraz daha detaylı anlatabilir misin?'
        }


def format_books_list(books: list, durum: str = None) -> str:
    """Kitap listesini formatla"""
    if not books:
        durum_text = f" ({durum})" if durum else ""
        return f"📚 Henüz kitap{durum_text} yok."
    
    durum_emoji = {
        "okunacak": "📖",
        "okunuyor": "📗",
        "okundu": "📕"
    }
    
    response = f"📚 *Kitaplarım ({len(books)} kitap):*\n\n"
    
    for book in books:
        emoji = durum_emoji.get(book['durum'], '📘')
        response += f"{emoji} *{book['baslik']}*\n"
        response += f"  ✍️ {book['yazar']}\n"
        response += f"  📄 {book['toplam_sayfa']} sayfa\n"
        if book.get('kategori'):
            response += f"  🏷️ {book['kategori']}\n"
        response += f"  📊 Durum: {book['durum'].title()}\n"
        response += "\n"
    
    return response.strip()


def format_reading_stats(stats: Dict, period_text: str = "Son 7 Gün") -> str:
    """Okuma istatistiklerini formatla"""
    if stats['toplam_sayfa'] == 0:
        return f"📊 {period_text} içinde okuma kaydın yok."
    
    response = f"📊 *{period_text} Okuma İstatistikleri:*\n\n"
    response += f"📖 Toplam: *{stats['toplam_sayfa']} sayfa*\n"
    response += f"📅 Günlük Ortalama: *{stats['ortalama']} sayfa*\n\n"
    
    if stats['kitap_bazinda']:
        response += "*Kitap Bazında:*\n"
        for kitap in stats['kitap_bazinda']:
            response += f"• {kitap['baslik']}: {kitap['okunan']} sayfa\n"
    
    return response.strip()
