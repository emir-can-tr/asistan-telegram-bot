"""
Ders programını otomatik yükle
Kullanıcının verdiği programı database'e kaydet
"""
from . import database as db
import csv
import io


def clear_user_schedule(user_id: int) -> bool:
    """Kullanıcının tüm ders ve program verilerini sil"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Önce kullanıcının ders ID'lerini al
    cursor.execute("SELECT id FROM lessons WHERE user_id = ?", (user_id,))
    lesson_ids = [row['id'] for row in cursor.fetchall()]
    
    if lesson_ids:
        # İlişkili kayıtları sil
        for lesson_id in lesson_ids:
            cursor.execute("DELETE FROM schedule WHERE lesson_id = ?", (lesson_id,))
            cursor.execute("DELETE FROM study_records WHERE lesson_id = ?", (lesson_id,))
            cursor.execute("DELETE FROM question_records WHERE lesson_id = ?", (lesson_id,))
        
        # Dersleri sil
        cursor.execute("DELETE FROM lessons WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    return True


def load_schedule_from_csv(user_id: int, csv_content: str) -> dict:
    """
    CSV içeriğinden ders programı yükle
    
    CSV Formatı:
    gun,saat_no,baslangic,bitis,ders_kodu,ders_adi,ogretmen
    pazartesi,1,08:30,09:10,MAT,Matematik,Ali Hoca
    
    Returns:
        dict: {'success': bool, 'message': str, 'ders_sayisi': int, 'program_sayisi': int}
    """
    try:
        # CSV'yi parse et
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Gerekli sütunları kontrol et
        required_columns = {'gun', 'saat_no', 'baslangic', 'bitis', 'ders_kodu', 'ders_adi'}
        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            return {
                'success': False,
                'message': f"Eksik sütunlar: {', '.join(missing)}",
                'ders_sayisi': 0,
                'program_sayisi': 0
            }
        
        # Mevcut programı sil
        clear_user_schedule(user_id)
        
        # Dersleri ve programı topla
        lessons_map = {}  # ders_kodu -> lesson dict
        schedule_entries = []
        
        for row in reader:
            ders_kodu = row['ders_kodu'].strip().upper()
            ders_adi = row['ders_adi'].strip()
            ogretmen = row.get('ogretmen', '').strip() or None
            
            # Dersi ekle (yoksa)
            if ders_kodu not in lessons_map:
                lesson = db.add_lesson(
                    user_id=user_id,
                    ders_kodu=ders_kodu,
                    ders_adi=ders_adi,
                    ogretmen=ogretmen
                )
                lessons_map[ders_kodu] = lesson
            
            # Program girişini kaydet
            schedule_entries.append({
                'ders_kodu': ders_kodu,
                'gun': row['gun'].strip().lower(),
                'saat_no': int(row['saat_no']),
                'baslangic': row['baslangic'].strip(),
                'bitis': row['bitis'].strip()
            })
        
        # Program girişlerini ekle
        for entry in schedule_entries:
            lesson = lessons_map.get(entry['ders_kodu'])
            if lesson:
                db.add_schedule_entry(
                    user_id=user_id,
                    lesson_id=lesson['id'],
                    gun=entry['gun'],
                    saat_no=entry['saat_no'],
                    baslangic_saati=entry['baslangic'],
                    bitis_saati=entry['bitis']
                )
        
        return {
            'success': True,
            'message': 'Program başarıyla yüklendi!',
            'ders_sayisi': len(lessons_map),
            'program_sayisi': len(schedule_entries)
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'CSV işleme hatası: {str(e)}',
            'ders_sayisi': 0,
            'program_sayisi': 0
        }


def load_schedule_data(user_id: int):
    """
    Kullan programını database'e yükle
    Bu fonksiyon kullanıcı için özel olarak hardcoded program yükler
    """
    
    # Önce dersleri ekle (sadece gerçek dersler)
    lessons_data = [
        ("A/F", "ALMANCA / FRANSIZCA", "NİLGÜN PIŞKIN ÖZIŞİK,ÖZGE ÖZDEMİR", 2),
        ("BDNSP", "BEDEN EĞİTİMİ ve SPOR", "EGE KAAN AKTAŞ,ONUR TUTKUN", 1),
        ("BY-10", "BİYOLOJİ", "NURCAN BELER", 3),
        ("CG-10", "COĞRAFYA", "BELGİN DELER", 3),
        ("DİN", "DİN KÜLTÜRÜ ve AHLAK BİLGİSİ", "HÜSNÜ TARIK KARAGÖZ", 1),
        ("FL-10", "FELSEFE", "MELDA GÜVERCİN", 2),
        ("FZ-10", "FİZİK", "BÜŞRA AVCI MERTADAM", 4),
        ("İNG10M", "İNGİLİZCE MAIN", "BEHTİYE UÇER", 5),
        ("İNG10S", "İNGİLİZCE SKILLS", "FUNDA YOLDAŞ", 2),
        ("KM-10", "KİMYA", "SEDA POŞLUK", 3),
        ("KULÜP1", "KULÜP 1", "", 1),
        ("KULÜP2", "KULÜP 2", "", 1),
        ("MT-10", "MATEMATİK", "BEDİA BEGÜM SÜLE", 5),
        ("TDE-10", "EDEBİYAT", "AYKUT İNCE", 3),
        ("TH-10", "TARİH", "FADİME AVCI", 2),
        ("TH-L10", "LIFE SCHOOL", "FADİME AVCI", 1),
        ("TR-P10", "PARAGRAF", "AYKUT İNCE", 1),
    ]
    
    lesson_map = {}
    for ders_kodu, ders_adi, ogretmen, haftalik_saat in lessons_data:
        lesson = db.add_lesson(user_id, ders_kodu, ders_adi, ogretmen, haftalik_saat)
        lesson_map[ders_kodu] = lesson['id']
    
    # Program verisini ekle (sadece gerçek dersler)
    schedule = [
        # Pazartesi
        ("pazartesi", 1, "08:30", "09:10", "FZ-10"),
        ("pazartesi", 2, "09:25", "10:05", "FZ-10"),
        ("pazartesi", 3, "10:20", "11:00", "İNG10M"),
        ("pazartesi", 4, "11:10", "11:50", "İNG10M"),
        ("pazartesi", 5, "12:30", "13:10", "İNG10M"),
        ("pazartesi", 6, "13:20", "14:00", "TH-L10"),
        ("pazartesi", 7, "14:10", "14:50", "CG-10"),
        ("pazartesi", 8, "15:00", "15:40", "CG-10"),
        
        # Salı
        ("sali", 1, "08:30", "09:10", "BY-10"),
        ("sali", 2, "09:25", "10:05", "TDE-10"),
        ("sali", 3, "10:20", "11:00", "TDE-10"),
        ("sali", 4, "11:10", "11:50", "TH-10"),
        ("sali", 5, "12:30", "13:10", "TH-10"),
        ("sali", 6, "13:20", "14:00", "İNG10M"),
        ("sali", 7, "14:10", "14:50", "İNG10M"),
        ("sali", 8, "15:00", "15:40", "CG-10"),
        
        # Çarşamba
        ("çarşamba", 1, "08:30", "09:10", "BY-10"),
        ("çarşamba", 2, "09:25", "10:05", "BY-10"),
        ("çarşamba", 3, "10:20", "11:00", "MT-10"),
        ("çarşamba", 4, "11:10", "11:50", "MT-10"),
        ("çarşamba", 5, "12:30", "13:10", "A/F"),
        ("çarşamba", 6, "13:20", "14:00", "A/F"),
        ("çarşamba", 7, "14:10", "14:50", "MT-10"),
        ("çarşamba", 8, "15:00", "15:40", "TDE-10"),
        
        # Perşembe
        ("perşembe", 1, "08:30", "09:10", "FZ-10"),
        ("perşembe", 2, "09:25", "10:05", "FZ-10"),
        ("perşembe", 3, "10:20", "11:00", "İNG10S"),
        ("perşembe", 4, "11:10", "11:50", "İNG10S"),
        ("perşembe", 5, "12:30", "13:10", "MT-10"),
        ("perşembe", 6, "13:20", "14:00", "MT-10"),
        ("perşembe", 7, "14:10", "14:50", "DİN"),
        ("perşembe", 8, "15:00", "15:40", "TR-P10"),
        
        # Cuma
        ("cuma", 1, "08:30", "09:10", "BDNSP"),
        ("cuma", 2, "09:25", "10:05", "KM-10"),
        ("cuma", 3, "10:20", "11:00", "KULÜP1"),
        ("cuma", 4, "11:10", "11:50", "KULÜP2"),
        ("cuma", 5, "12:30", "13:10", "FL-10"),
        ("cuma", 6, "13:20", "14:00", "FL-10"),
        ("cuma", 7, "14:10", "14:50", "KM-10"),
        ("cuma", 8, "15:00", "15:40", "KM-10"),
    ]
    
    for gun, saat_no, baslangic, bitis, ders_kodu in schedule:
        if ders_kodu in lesson_map:
            db.add_schedule_entry(
                user_id=user_id,
                lesson_id=lesson_map[ders_kodu],
                gun=gun,
                saat_no=saat_no,
                baslangic_saati=baslangic,
                bitis_saati=bitis
            )
    
    return True
