"""
İngilizce Modülü AI Servisi
Gemini AI ile kelime anlamı ve örnek cümle getirme
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


def get_word_meaning_and_examples(word: str) -> Dict[str, Any]:
    """
    Kelimenin Türkçe anlamını ve 3 örnek cümle getir
    """
    
    prompt = f"""İngilizce kelime: "{word}"

Bu kelime için şunları ver:
1. Türkçe anlamı (kısa ve öz)
2. 3 farklı örnek cümle (İngilizce)

JSON formatında yanıt ver:
{{
    "meaning": "Türkçe anlamı",
    "example1": "İngilizce örnek cümle 1",
    "example2": "İngilizce örnek cümle 2",
    "example3": "İngilizce örnek cümle 3"
}}

SADECE JSON yanıt ver, başka hiçbir şey yazma."""
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # JSON'u parse et
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        return result
        
    except Exception as e:
        print(f"AI kelime hatası: {e}")
        return {
            'meaning': f"{word} (anlamı alınamadı)",
            'example1': None,
            'example2': None,
            'example3': None
        }


def analyze_ingilizce_message(message: str, context: Dict = None) -> Dict[str, Any]:
    """
    Kullanıcının mesajını analiz et
    
    Actions:
    - add_word: Kelime ekleme
    - word_detail: Kelime detayı göster (anlamı + örnekler)
    - set_goal: Günlük hedef
    - show_daily: Günlük kelimeleri göster
    - show_stats: İstatistikler
    - start_review: Tekrar başlat
    - list_words: Kelimeleri listele
    - chat: Genel sohbet
    """
    
    prompt = f"""Sen bir İngilizce kelime öğrenme asistanısın. Kullanıcının mesajını analiz et.

MESAJ: {message}

AKSİYONLAR:
- add_word: "serendipity kelimesini ekle", "ephemeral ekle" gibi kelime eklemeleri
- word_detail: "serendipity nedir?", "ephemeral ne demek?" gibi kelime detay sorguları
- set_goal: "Günde 10 kelime öğrenmek istiyorum" gibi hedef belirlemeleri
- show_daily: "Bugün öğrenecek", "Günlük kelimeleri göster" gibi
- show_stats: "İstatistiklerim", "Kaç kelime öğrendim" gibi
- start_review: "Tekrar et", "Hatırlatma", "Review" gibi
- list_words: "Kelimelerim", "Tüm kelimeler" gibi
- chat: Diğer her şey

JSON FORMAT:
{{
    "action": "action_name",
    "response": "Yanıt (Türkçe)",
    "word": "kelime (varsa, küçük harf)",
    "goal_count": hedef sayısı (varsa)
}}

Şimdi analiz et ve SADECE JSON yanıt ver:"""
    
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
        
    except Exception as e:
        print(f"AI analiz hatası: {e}")
        return {
            'action': 'chat',
            'response': 'Mesajını anlayamadım, tekrar anlat?'
        }


def format_word_info(word_data: Dict) -> str:
    """Kelime bilgisini formatla"""
    response = f"🇬🇧 *{word_data['word'].title()}*\n\n"
    response += f"🇹🇷 Anlamı: {word_data['meaning']}\n\n"
    
    if word_data.get('example1'):
        response += "*Örnek Cümleler:*\n"
        response += f"1. {word_data['example1']}\n"
        if word_data.get('example2'):
            response += f"2. {word_data['example2']}\n"
        if word_data.get('example3'):
            response += f"3. {word_data['example3']}\n"
    
    return response.strip()


def format_words_list(words: list) -> str:
    """Kelime listesini formatla (minimal - sadece kelime + durum)"""
    if not words:
        return "📚 Henüz kelime eklenmemiş."
    
    response = f"📚 *Kelimelerim ({len(words)} kelime):*\n\n"
    
    # Durum emoji'leri
    status_emoji = {
        'ogrenilmedi': '⬜',
        'ogreniyor': '🟨',
        'ogrenildi': '✅'
    }
    
    for word in words[:50]:  # İlk 50 kelime
        emoji = status_emoji.get(word['durum'], '⬜')
        review_info = f" (#{word['review_count']})" if word['review_count'] > 0 else ""
        
        response += f"{emoji} `{word['word']}`{review_info}\n"
    
    if len(words) > 50:
        response += f"\n... ve {len(words)-50} kelime daha"
    
    response += "\n\n💡 Kelime detayı için: `kelime nedir?`"
    
    return response.strip()


def format_stats(stats: Dict) -> str:
    """İstatistikleri formatla"""
    response = "📊 *İngilizce İstatistiklerim:*\n\n"
    response += f"📚 Toplam Kelime: {stats['toplam']}\n"
    response += f"✅ Öğrenildi: {stats['ogrenildi']}\n"
    response += f"🟨 Öğreniliyor: {stats['ogreniyor']}\n"
    response += f"⬜ Öğrenilmedi: {stats['ogrenilmedi']}\n\n"
    
    if stats['toplam_ogrenilen'] > 0:
        response += f"📈 Son {stats['son_gun']} Gün:\n"
        response += f"• {stats['toplam_ogrenilen']} kelime öğrenildi\n"
        response += f"• Günlük ortalama: {stats['gunluk_ortalama']} kelime\n"
    
    return response.strip()
