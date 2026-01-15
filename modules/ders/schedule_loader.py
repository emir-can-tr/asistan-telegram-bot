"""
Ders programını otomatik yükle
Kullanıcının verdiği programı database'e kaydet
"""
from . import database as db


def load_schedule_data(user_id: int):
    """
    Kullanıcı programını database'e yükle
    Bu fonksiyon kullanıcı için özel olarak program yükler
    Kendi ders programınızı burada tanımlayabilirsiniz
    """
    
    # Örnek ders tanımları
    lessons_data = [
        # (ders_kodu, ders_adi, ogretmen, haftalik_saat)
        ("MAT", "MATEMATİK", "Öğretmen Adı", 5),
        ("FZ", "FİZİK", "Öğretmen Adı", 4),
        ("KM", "KİMYA", "Öğretmen Adı", 3),
        ("BY", "BİYOLOJİ", "Öğretmen Adı", 3),
        ("TDE", "EDEBİYAT", "Öğretmen Adı", 3),
        ("TH", "TARİH", "Öğretmen Adı", 2),
        ("CG", "COĞRAFYA", "Öğretmen Adı", 3),
        ("ING", "İNGİLİZCE", "Öğretmen Adı", 5),
    ]
    
    lesson_map = {}
    for ders_kodu, ders_adi, ogretmen, haftalik_saat in lessons_data:
        lesson = db.add_lesson(user_id, ders_kodu, ders_adi, ogretmen, haftalik_saat)
        lesson_map[ders_kodu] = lesson['id']
    
    # Örnek program verisi
    # (gun, saat_no, baslangic_saati, bitis_saati, ders_kodu)
    schedule = [
        # Pazartesi
        ("pazartesi", 1, "08:30", "09:10", "MAT"),
        ("pazartesi", 2, "09:25", "10:05", "MAT"),
        ("pazartesi", 3, "10:20", "11:00", "FZ"),
        ("pazartesi", 4, "11:10", "11:50", "FZ"),
        ("pazartesi", 5, "12:30", "13:10", "ING"),
        ("pazartesi", 6, "13:20", "14:00", "ING"),
        ("pazartesi", 7, "14:10", "14:50", "TDE"),
        ("pazartesi", 8, "15:00", "15:40", "TH"),
        
        # Salı
        ("sali", 1, "08:30", "09:10", "BY"),
        ("sali", 2, "09:25", "10:05", "KM"),
        ("sali", 3, "10:20", "11:00", "KM"),
        ("sali", 4, "11:10", "11:50", "CG"),
        ("sali", 5, "12:30", "13:10", "MAT"),
        ("sali", 6, "13:20", "14:00", "FZ"),
        ("sali", 7, "14:10", "14:50", "ING"),
        ("sali", 8, "15:00", "15:40", "TDE"),
        
        # Çarşamba - kendi programınıza göre düzenleyin
        # Perşembe - kendi programınıza göre düzenleyin
        # Cuma - kendi programınıza göre düzenleyin
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
