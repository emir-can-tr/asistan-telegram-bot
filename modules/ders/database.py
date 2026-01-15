"""
Ders Modülü Database
Ayrı database: modules/ders/ders.db
"""
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import os


# Database path - modules/ders klasörü içinde
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DB_DIR, "ders.db")


def get_connection():
    """Ders veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_ders_database():
    """Ders modülü tablolarını oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Dersler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ders_kodu TEXT NOT NULL,
            ders_adi TEXT NOT NULL,
            ogretmen TEXT,
            haftalik_saat INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ders programı tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            gun TEXT NOT NULL,
            saat_no INTEGER NOT NULL,
            baslangic_saati TEXT NOT NULL,
            bitis_saati TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        )
    """)
    
    # Çalışma kayıtları tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            konu TEXT,
            sure_dakika INTEGER,
            tarih DATE NOT NULL,
            notlar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        )
    """)
    
    # Soru çözüm kayıtları tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS question_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            konu TEXT,
            soru_sayisi INTEGER NOT NULL,
            tarih DATE NOT NULL,
            notlar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        )
    """)
    
    # Ödevler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS homeworks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER,
            baslik TEXT NOT NULL,
            aciklama TEXT,
            baslangic_tarihi DATE,
            bitis_tarihi DATE NOT NULL,
            tamamlandi BOOLEAN DEFAULT 0,
            tamamlanma_tarihi TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        )
    """)
    
    conn.commit()
    conn.close()


# ==================== DERS İŞLEMLERİ ====================

def add_lesson(user_id: int, ders_kodu: str, ders_adi: str, ogretmen: str = None, haftalik_saat: int = None) -> Dict[str, Any]:
    """Yeni ders ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO lessons (user_id, ders_kodu, ders_adi, ogretmen, haftalik_saat)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, ders_kodu, ders_adi, ogretmen, haftalik_saat))
    
    conn.commit()
    lesson_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
    lesson = cursor.fetchone()
    conn.close()
    
    return dict(lesson)


def get_user_lessons(user_id: int) -> List[Dict[str, Any]]:
    """Kullanıcının derslerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM lessons WHERE user_id = ? ORDER BY ders_kodu", (user_id,))
    lessons = cursor.fetchall()
    conn.close()
    
    return [dict(l) for l in lessons]


def get_lesson_by_code_or_name(user_id: int, search: str) -> Optional[Dict[str, Any]]:
    """Ders kodu veya adına göre ders bul"""
    conn = get_connection()
    cursor = conn.cursor()
    
    search_upper = search.upper()
    
    cursor.execute("""
        SELECT * FROM lessons 
        WHERE user_id = ? AND (
            UPPER(ders_kodu) LIKE ? OR 
            UPPER(ders_adi) LIKE ?
        )
        LIMIT 1
    """, (user_id, f"%{search_upper}%", f"%{search_upper}%"))
    
    lesson = cursor.fetchone()
    conn.close()
    
    return dict(lesson) if lesson else None


# ==================== PROGRAM İŞLEMLERİ ====================

def add_schedule_entry(user_id: int, lesson_id: int, gun: str, saat_no: int, 
                       baslangic_saati: str, bitis_saati: str) -> Dict[str, Any]:
    """Program girişi ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO schedule (user_id, lesson_id, gun, saat_no, baslangic_saati, bitis_saati)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, lesson_id, gun, saat_no, baslangic_saati, bitis_saati))
    
    conn.commit()
    entry_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()
    conn.close()
    
    return dict(entry)


def get_schedule_for_day(user_id: int, gun: str) -> List[Dict[str, Any]]:
    """Belirli bir günün programını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, l.ders_kodu, l.ders_adi, l.ogretmen
        FROM schedule s
        JOIN lessons l ON s.lesson_id = l.id
        WHERE s.user_id = ? AND s.gun = ?
        ORDER BY s.saat_no
    """, (user_id, gun.lower()))
    
    schedule = cursor.fetchall()
    conn.close()
    
    return [dict(s) for s in schedule]


def get_schedule_by_hour(user_id: int, gun: str, saat_no: int) -> Optional[Dict[str, Any]]:
    """Belirli gün ve saatteki dersi getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, l.ders_kodu, l.ders_adi, l.ogretmen
        FROM schedule s
        JOIN lessons l ON s.lesson_id = l.id
        WHERE s.user_id = ? AND s.gun = ? AND s.saat_no = ?
    """, (user_id, gun.lower(), saat_no))
    
    entry = cursor.fetchone()
    conn.close()
    
    return dict(entry) if entry else None


# ==================== ÇALIŞMA KAYITLARI ====================

def add_study_record(user_id: int, lesson_id: int, konu: str = None, 
                     sure_dakika: int = None, tarih: date = None, notlar: str = None) -> Dict[str, Any]:
    """Çalışma kaydı ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if tarih is None:
        tarih = date.today()
    
    cursor.execute("""
        INSERT INTO study_records (user_id, lesson_id, konu, sure_dakika, tarih, notlar)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, lesson_id, konu, sure_dakika, tarih.isoformat(), notlar))
    
    conn.commit()
    record_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM study_records WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    conn.close()
    
    return dict(record)


def get_study_records(user_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """Çalışma kayıtlarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    from_date = (date.today() - timedelta(days=days-1)).isoformat()
    
    cursor.execute("""
        SELECT sr.*, l.ders_kodu, l.ders_adi
        FROM study_records sr
        JOIN lessons l ON sr.lesson_id = l.id
        WHERE sr.user_id = ? AND sr.tarih >= ?
        ORDER BY sr.tarih DESC, sr.created_at DESC
    """, (user_id, from_date))
    
    records = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in records]


def get_today_study_records(user_id: int) -> List[Dict[str, Any]]:
    """Bugünkü çalışma kayıtlarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute("""
        SELECT sr.*, l.ders_kodu, l.ders_adi
        FROM study_records sr
        JOIN lessons l ON sr.lesson_id = l.id
        WHERE sr.user_id = ? AND sr.tarih = ?
        ORDER BY sr.created_at DESC
    """, (user_id, today))
    
    records = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in records]


# ==================== SORU ÇÖZÜM KAYITLARI ====================

def add_question_record(user_id: int, lesson_id: int, soru_sayisi: int,
                        konu: str = None, tarih: date = None, notlar: str = None) -> Dict[str, Any]:
    """Soru çözüm kaydı ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if tarih is None:
        tarih = date.today()
    
    cursor.execute("""
        INSERT INTO question_records (user_id, lesson_id, konu, soru_sayisi, tarih, notlar)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, lesson_id, konu, soru_sayisi, tarih.isoformat(), notlar))
    
    conn.commit()
    record_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM question_records WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    conn.close()
    
    return dict(record)


def get_question_stats(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Soru çözüm istatistiklerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    from_date = (date.today() - timedelta(days=days-1)).isoformat()
    
    # Toplam soru sayısı
    cursor.execute("""
        SELECT SUM(soru_sayisi) as toplam
        FROM question_records
        WHERE user_id = ? AND tarih >= ?
    """, (user_id, from_date))
    
    toplam_result = cursor.fetchone()
    toplam = toplam_result['toplam'] if toplam_result['toplam'] else 0
    
    # Ders bazında (konularla birlikte)
    cursor.execute("""
        SELECT l.ders_adi, SUM(qr.soru_sayisi) as toplam,
               GROUP_CONCAT(CASE WHEN qr.konu IS NOT NULL THEN qr.konu END, ', ') as konular
        FROM question_records qr
        JOIN lessons l ON qr.lesson_id = l.id
        WHERE qr.user_id = ? AND qr.tarih >= ?
        GROUP BY l.id
        ORDER BY toplam DESC
    """, (user_id, from_date))
    
    ders_bazinda = cursor.fetchall()
    conn.close()
    
    return {
        'toplam': toplam,
        'ders_bazinda': [dict(d) for d in ders_bazinda],
        'gun_sayisi': days
    }


def get_today_question_stats(user_id: int) -> Dict[str, Any]:
    """Bugünkü soru istatistiklerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    # Toplam soru sayısı
    cursor.execute("""
        SELECT SUM(soru_sayisi) as toplam
        FROM question_records
        WHERE user_id = ? AND tarih = ?
    """, (user_id, today))
    
    toplam_result = cursor.fetchone()
    toplam = toplam_result['toplam'] if toplam_result['toplam'] else 0
    
    # Ders bazında (konularla birlikte)
    cursor.execute("""
        SELECT l.ders_adi, SUM(qr.soru_sayisi) as toplam,
               GROUP_CONCAT(CASE WHEN qr.konu IS NOT NULL THEN qr.konu END, ', ') as konular
        FROM question_records qr
        JOIN lessons l ON qr.lesson_id = l.id
        WHERE qr.user_id = ? AND qr.tarih = ?
        GROUP BY l.id
        ORDER BY toplam DESC
    """, (user_id, today))
    
    ders_bazinda = cursor.fetchall()
    conn.close()
    
    return {
        'toplam': toplam,
        'ders_bazinda': [dict(d) for d in ders_bazinda],
        'gun_sayisi': 1
    }


# ==================== ÖDEV İŞLEMLERİ ====================

def add_homework(user_id: int, baslik: str, bitis_tarihi: date, lesson_id: int = None,
                 aciklama: str = None, baslangic_tarihi: date = None) -> Dict[str, Any]:
    """Ödev ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if baslangic_tarihi is None:
        baslangic_tarihi = date.today()
    
    cursor.execute("""
        INSERT INTO homeworks (user_id, lesson_id, baslik, aciklama, baslangic_tarihi, bitis_tarihi)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, lesson_id, baslik, aciklama, baslangic_tarihi.isoformat(), bitis_tarihi.isoformat()))
    
    conn.commit()
    hw_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM homeworks WHERE id = ?", (hw_id,))
    hw = cursor.fetchone()
    conn.close()
    
    return dict(hw)


def get_pending_homeworks(user_id: int) -> List[Dict[str, Any]]:
    """Tamamlanmamış ödevleri getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.*, l.ders_adi
        FROM homeworks h
        LEFT JOIN lessons l ON h.lesson_id = l.id
        WHERE h.user_id = ? AND h.tamamlandi = 0
        ORDER BY h.bitis_tarihi ASC
    """, (user_id,))
    
    homeworks = cursor.fetchall()
    conn.close()
    
    return [dict(h) for h in homeworks]


def complete_homework(homework_id: int) -> bool:
    """Ödevi tamamla"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE homeworks 
        SET tamamlandi = 1, tamamlanma_tarihi = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), homework_id))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def get_homework_by_title(user_id: int, title_search: str) -> Optional[Dict[str, Any]]:
    """Başlığa göre ödev bul"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.*, l.ders_adi
        FROM homeworks h
        LEFT JOIN lessons l ON h.lesson_id = l.id
        WHERE h.user_id = ? AND UPPER(h.baslik) LIKE ?
        AND h.tamamlandi = 0
        ORDER BY h.bitis_tarihi ASC
        LIMIT 1
    """, (user_id, f"%{title_search.upper()}%"))
    
    hw = cursor.fetchone()
    conn.close()
    
    return dict(hw) if hw else None


# Veritabanını başlat
init_ders_database()


# ==================== EKSİK FONKSİYONLAR ====================

def get_lesson_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """İsme göre ders bul (get_lesson_by_code_or_name alias)"""
    return get_lesson_by_code_or_name(user_id, name)


def get_study_stats(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Çalışma istatistiklerini getir"""
    conn = get_connection()
    cursor = conn.cursor()

    from_date = (date.today() - timedelta(days=days-1)).isoformat()

    # Toplam süre
    cursor.execute("""
        SELECT SUM(sure_dakika) as toplam_dakika
        FROM study_records
        WHERE user_id = ? AND tarih >= ?
    """, (user_id, from_date))

    toplam_result = cursor.fetchone()
    toplam_dakika = toplam_result['toplam_dakika'] if toplam_result['toplam_dakika'] else 0

    # Ders bazında
    cursor.execute("""
        SELECT l.ders_adi, SUM(sr.sure_dakika) as toplam_dakika,
               GROUP_CONCAT(CASE WHEN sr.konu IS NOT NULL THEN sr.konu END, ', ') as konular
        FROM study_records sr
        JOIN lessons l ON sr.lesson_id = l.id
        WHERE sr.user_id = ? AND sr.tarih >= ?
        GROUP BY l.id
        ORDER BY toplam_dakika DESC
    """, (user_id, from_date))

    ders_bazinda = cursor.fetchall()
    conn.close()

    return {
        'toplam_dakika': toplam_dakika,
        'ders_bazinda': [dict(d) for d in ders_bazinda],
        'gun_sayisi': days
    }


def delete_lesson(lesson_id: int) -> bool:
    """Dersi ve ilişkili tüm kayıtları sil"""
    conn = get_connection()
    cursor = conn.cursor()

    # İlişkili kayıtları sil
    cursor.execute("DELETE FROM schedule WHERE lesson_id = ?", (lesson_id,))
    cursor.execute("DELETE FROM study_records WHERE lesson_id = ?", (lesson_id,))
    cursor.execute("DELETE FROM question_records WHERE lesson_id = ?", (lesson_id,))
    cursor.execute("UPDATE homeworks SET lesson_id = NULL WHERE lesson_id = ?", (lesson_id,))

    # Dersi sil
    cursor.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0
