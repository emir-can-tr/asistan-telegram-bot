"""
Ders Modülü AI Servisi
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


def analyze_ders_message(message: str, user_lessons: list, context: Dict = None) -> Dict[str, Any]:
    """
    Kullanıcının mesajını analiz et ve uygun aksiyonu belirle
    
    Actions:
    - query_schedule: Program sorgulama
    - add_study: Çalışma kaydı
    - add_questions: Soru çözümü kaydı
    - add_homework: Ödev ekleme
    - complete_homework: Ödev tamamlama
    - list_homeworks: Ödevleri listele
    - show_stats: İstatistikler
    - chat: Genel sohbet
    """
    
    # Kullanıcının derslerini formatla
    lessons_text = "\n".join([f"- {l['ders_kodu']}: {l['ders_adi']}" for l in user_lessons]) if user_lessons else "Henüz ders eklenmemiş"
    
    prompt = f"""Sen bir ders takip asistanısın. Kullanıcının mesajını analiz et ve ne yapmak istediğini belirle.

KULLANICININ DERSLERİ:
{lessons_text}

MESAJ: {message}

GÖREVIN:
1. Kullanıcının ne yapmak istediğini anla
2. Uygun aksiyonu belirle
3. JSON formatında yanıt ver

AKSİYONLAR:
- query_schedule: "Bugün hangi DERSLERİM var?", "4. saat ne dersi?" gibi PROGRAM sorguları (hangi ders olduğunu sormak)
- add_study: "Matematik çalıştım", "Fizik çalıştım türev konusu 2 saat" gibi çalışma kayıtları
- add_questions: "Matematik'ten 15 soru çözdüm", "Fizik limit konusundan 20 soru" gibi soru çözümleri
- add_homework: "Matematik ödevi var son tarih cuma", "Fizik raporu yaz 15 ocağa kadar" gibi ödev eklemeleri
- complete_homework: "Matematik ödevini bitirdim", "Fizik raporunu tamamladım" gibi ödev tamamlamaları
- list_homeworks: "Ödevlerimi göster", "Yaklaşan ödevler" gibi listeleme istekleri
- show_stats: "Bu hafta kaç soru çözdüm?", "Bugün NE KADAR çalıştım?", "Bugünkü durumum", "Bugün ne yaptım?" gibi GÜNDELİK/HAFTALIK istatistikler
- chat: Diğer her şey

ÖNEMLİ: "Bugün hangi derslerim var?" = query_schedule (program), "Bugün ne yaptım/çalıştım?" = show_stats (özet)

JSON FORMAT:
{{
    "action": "action_name",
    "response": "Kullanıcıya gösterilecek yanıt (Türkçe, samimi)",
    "lesson_search": "ders kodu veya adı (varsa)",
    "konu": "konu adı (varsa)",
    "sure_dakika": süre dakika cinsinden sayı (varsa),
    "soru_sayisi": soru sayısı (varsa),
    "gun": "gün adı (bugün, yarın, pazartesi vb. - varsa)",
    "saat_no": saat numarası 1-8 arası (varsa),
    "homework_title": "ödev başlığı (varsa)",
    "homework_description": "ödev açıklaması (varsa)",
    "homework_due_date": "son tarih YYYY-MM-DD formatında (varsa)",
    "homework_search": "tamamlanacak/silinecek ödev başlığı (varsa)"
}}

ÖRNEKLER:

Mesaj: "Bugün hangi derslerim var?"
{{
    "action": "query_schedule",
    "response": "Bugünkü programını göstereyim",
    "gun": "bugün"
}}

Mesaj: "Matematik çalıştım türev konusu 2 saat"
{{
    "action": "add_study",
    "response": "Matematik çalışman kaydedildi!",
    "lesson_search": "matematik",
    "konu": "türev",
    "sure_dakika": 120
}}

Mesaj: "Fizik'ten 15 soru çözdüm limit konusundan"
{{
    "action": "add_questions",
    "response": "15 Fizik sorusu kaydedildi!",
    "lesson_search": "fizik",
    "konu": "limit",
    "soru_sayisi": 15
}}

Mesaj: "Matematik ödevi var cuma teslim"
{{
    "action": "add_homework",
    "response": "Matematik ödevi eklendi!",
    "lesson_search": "matematik",
    "homework_title": "Matematik ödevi",
    "homework_due_date": "2026-01-03"
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


def format_schedule(schedule_entries: list) -> str:
    """Program girişlerini formatla"""
    if not schedule_entries:
        return "📅 Bu gün için ders programın yok."
    
    formatted = "📅 *Ders Programı:*\n\n"
    
    for entry in schedule_entries:
        formatted += f"{entry['saat_no']}. Saat ({entry['baslangic_saati']}-{entry['bitis_saati']})\n"
        formatted += f"📚 {entry['ders_kodu']} - {entry['ders_adi']}\n"
        if entry.get('ogretmen'):
            formatted += f"👨‍🏫 {entry['ogretmen']}\n"
        formatted += "\n"
    
    return formatted.strip()


def format_study_records(records: list) -> str:
    """Çalışma kayıtlarını formatla"""
    if not records:
        return "📚 Henüz çalışma kaydın yok."
    
    formatted = "📚 *Çalışma Kayıtların:*\n\n"
    
    current_date = None
    for record in records:
        # Tarih başlığı
        if record['tarih'] != current_date:
            current_date = record['tarih']
            formatted += f"*{current_date}*\n"
        
        formatted += f"• {record['ders_adi']}"
        if record.get('konu'):
            formatted += f" - {record['konu']}"
        if record.get('sure_dakika'):
            saat = record['sure_dakika'] // 60
            dakika = record['sure_dakika'] % 60
            if saat > 0:
                formatted += f" ({saat}sa"
                if dakika > 0:
                    formatted += f" {dakika}dk"
                formatted += ")"
            elif dakika > 0:
                formatted += f" ({dakika}dk)"
        formatted += "\n"
    
    return formatted.strip()


def format_question_stats(stats: Dict) -> str:
    """Soru istatistiklerini formatla"""
    if stats['toplam'] == 0:
        return f"✏️ Son {stats['gun_sayisi']} günde hiç soru çözmedin."
    
    formatted = f"✏️ *Son {stats['gun_sayisi']} Gün Soru İstatistikleri:*\n\n"
    formatted += f"📊 Toplam: *{stats['toplam']} soru*\n\n"
    
    if stats['ders_bazinda']:
        formatted += "*Ders Bazında:*\n"
        for ders in stats['ders_bazinda']:
            formatted += f"• {ders['ders_adi']}: {ders['toplam']} soru\n"
    
    return formatted.strip()


def format_homeworks(homeworks: list) -> str:
    """Ödevleri formatla"""
    if not homeworks:
        return "📝 Tebrikler! Hiç bekleyen ödevin yok."
    
    from datetime import date, datetime
    
    formatted = "📝 *Bekleyen Ödevler:*\n\n"
    
    for hw in homeworks:
        formatted += f"• *{hw['baslik']}*\n"
        if hw.get('ders_adi'):
            formatted += f"  📚 {hw['ders_adi']}\n"
        if hw.get('aciklama'):
            formatted += f"  📄 {hw['aciklama']}\n"
        
        # Son tarih kontrolü
        bitis = datetime.strptime(hw['bitis_tarihi'], '%Y-%m-%d').date()
        bugun = date.today()
        kalan_gun = (bitis - bugun).days
        
        if kalan_gun < 0:
            formatted += f"  ⚠️ Son tarih: {hw['bitis_tarihi']} (GEÇTİ!)\n"
        elif kalan_gun == 0:
            formatted += f"  ⚠️ Son tarih: BUGÜN!\n"
        elif kalan_gun == 1:
            formatted += f"  📅 Son tarih: Yarın\n"
        else:
            formatted += f"  📅 Son tarih: {hw['bitis_tarihi']} ({kalan_gun} gün)\n"
        
        formatted += "\n"
    
    return formatted.strip()
