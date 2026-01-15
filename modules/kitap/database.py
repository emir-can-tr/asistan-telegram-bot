"""
Kitap Modülü Database
Ayrı database: modules/kitap/kitap.db
"""
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import os


# Database path - modules/kitap klasörü içinde
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DB_DIR, "kitap.db")


def get_connection():
    """Kitap veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_kitap_database():
    """Kitap modülü tablolarını oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kitaplar tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            baslik TEXT NOT NULL,
            yazar TEXT NOT NULL,
            toplam_sayfa INTEGER NOT NULL,
            kategori TEXT,
            durum TEXT DEFAULT 'okunacak',
            baslangic_tarihi DATE,
            bitis_tarihi DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Kitap notları tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            not_metni TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)
    
    # Okuma hedefleri tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hedef_tipi TEXT NOT NULL,
            hedef_deger INTEGER NOT NULL,
            baslangic_tarihi DATE NOT NULL,
            bitis_tarihi DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Okuma ilerleme tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            okunan_sayfa INTEGER NOT NULL,
            tarih DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)
    
    conn.commit()
    conn.close()


# ==================== KİTAP İŞLEMLERİ ====================

def add_book(user_id: int, baslik: str, yazar: str, toplam_sayfa: int, 
             kategori: str = None) -> Dict[str, Any]:
    """Yeni kitap ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO books (user_id, baslik, yazar, toplam_sayfa, kategori, durum)
        VALUES (?, ?, ?, ?, ?, 'okunacak')
    """, (user_id, baslik, yazar, toplam_sayfa, kategori))
    
    conn.commit()
    book_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    conn.close()
    
    return dict(book)


def get_user_books(user_id: int, durum: str = None) -> List[Dict[str, Any]]:
    """Kullanıcının kitaplarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if durum:
        cursor.execute("""
            SELECT * FROM books 
            WHERE user_id = ? AND durum = ?
            ORDER BY created_at DESC
        """, (user_id, durum))
    else:
        cursor.execute("""
            SELECT * FROM books 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    
    books = cursor.fetchall()
    conn.close()
    
    return [dict(b) for b in books]


def normalize_turkish(text: str) -> str:
    """Türkçe karakterleri normalize et ve küçük harfe çevir"""
    if not text:
        return ""
    # Önce büyük Türkçe karakterleri dönüştür
    replacements = {
        'I': 'i', 'İ': 'i', 'ı': 'i',
        'Ğ': 'g', 'ğ': 'g',
        'Ü': 'u', 'ü': 'u',
        'Ş': 's', 'ş': 's',
        'Ö': 'o', 'ö': 'o',
        'Ç': 'c', 'ç': 'c'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.lower()


def get_book_by_title(user_id: int, title_search: str) -> Optional[Dict[str, Any]]:
    """Başlığa göre kitap bul (Türkçe karakter destekli)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Tüm kitapları al
    cursor.execute("""
        SELECT * FROM books
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    books = cursor.fetchall()
    conn.close()

    if not books:
        return None

    # Aranan ismi normalize et
    search_normalized = normalize_turkish(title_search)

    # Önce tam eşleşme dene
    for book in books:
        book_normalized = normalize_turkish(book['baslik'])
        if book_normalized == search_normalized:
            return dict(book)

    # Sonra kısmi eşleşme dene
    for book in books:
        book_normalized = normalize_turkish(book['baslik'])
        if search_normalized in book_normalized or book_normalized in search_normalized:
            return dict(book)

    return None


def update_book_status(book_id: int, durum: str, tarih: date = None) -> bool:
    """Kitap durumunu güncelle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if tarih is None:
        tarih = date.today()
    
    if durum == 'okunuyor' and not cursor.execute(
        "SELECT baslangic_tarihi FROM books WHERE id = ?", (book_id,)
    ).fetchone()['baslangic_tarihi']:
        cursor.execute("""
            UPDATE books 
            SET durum = ?, baslangic_tarihi = ?
            WHERE id = ?
        """, (durum, tarih.isoformat(), book_id))
    elif durum == 'okundu':
        cursor.execute("""
            UPDATE books 
            SET durum = ?, bitis_tarihi = ?
            WHERE id = ?
        """, (durum, tarih.isoformat(), book_id))
    else:
        cursor.execute("""
            UPDATE books 
            SET durum = ?
            WHERE id = ?
        """, (durum, book_id))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


# ==================== NOT İŞLEMLERİ ====================

def add_book_note(user_id: int, book_id: int, not_metni: str) -> Dict[str, Any]:
    """Kitaba not ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO book_notes (user_id, book_id, not_metni)
        VALUES (?, ?, ?)
    """, (user_id, book_id, not_metni))
    
    conn.commit()
    note_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM book_notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    conn.close()
    
    return dict(note)


def get_book_notes(book_id: int) -> List[Dict[str, Any]]:
    """Kitabın notlarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM book_notes
        WHERE book_id = ?
        ORDER BY created_at DESC
    """, (book_id,))
    
    notes = cursor.fetchall()
    conn.close()
    
    return [dict(n) for n in notes]


# ==================== HEDEF İŞLEMLERİ ====================

def set_reading_goal(user_id: int, hedef_tipi: str, hedef_deger: int,
                     baslangic_tarihi: date = None, bitis_tarihi: date = None) -> Dict[str, Any]:
    """Okuma hedefi belirle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if baslangic_tarihi is None:
        baslangic_tarihi = date.today()
    
    # Eğer aynı tip hedef varsa güncelle
    cursor.execute("""
        SELECT id FROM reading_goals
        WHERE user_id = ? AND hedef_tipi = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, hedef_tipi))
    
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE reading_goals
            SET hedef_deger = ?, baslangic_tarihi = ?, bitis_tarihi = ?
            WHERE id = ?
        """, (hedef_deger, baslangic_tarihi.isoformat(), 
              bitis_tarihi.isoformat() if bitis_tarihi else None, existing['id']))
        goal_id = existing['id']
    else:
        cursor.execute("""
            INSERT INTO reading_goals (user_id, hedef_tipi, hedef_deger, baslangic_tarihi, bitis_tarihi)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, hedef_tipi, hedef_deger, baslangic_tarihi.isoformat(),
              bitis_tarihi.isoformat() if bitis_tarihi else None))
        goal_id = cursor.lastrowid
    
    conn.commit()
    
    cursor.execute("SELECT * FROM reading_goals WHERE id = ?", (goal_id,))
    goal = cursor.fetchone()
    conn.close()
    
    return dict(goal)


def get_user_goals(user_id: int) -> List[Dict[str, Any]]:
    """Kullanıcının hedeflerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM reading_goals
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    goals = cursor.fetchall()
    conn.close()
    
    return [dict(g) for g in goals]


# ==================== İLERLEME İŞLEMLERİ ====================

def add_reading_progress(user_id: int, book_id: int, okunan_sayfa: int,
                         tarih: date = None) -> Dict[str, Any]:
    """Okuma ilerlemesi ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if tarih is None:
        tarih = date.today()
    
    cursor.execute("""
        INSERT INTO reading_progress (user_id, book_id, okunan_sayfa, tarih)
        VALUES (?, ?, ?, ?)
    """, (user_id, book_id, okunan_sayfa, tarih.isoformat()))
    
    conn.commit()
    progress_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM reading_progress WHERE id = ?", (progress_id,))
    progress = cursor.fetchone()
    conn.close()
    
    return dict(progress)


def get_book_progress(book_id: int) -> Dict[str, Any]:
    """Kitap ilerlemesini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Toplam okunan sayfa
    cursor.execute("""
        SELECT SUM(okunan_sayfa) as toplam_okunan
        FROM reading_progress
        WHERE book_id = ?
    """, (book_id,))
    
    result = cursor.fetchone()
    toplam_okunan = result['toplam_okunan'] if result['toplam_okunan'] else 0
    
    # Kitap bilgisi
    cursor.execute("SELECT toplam_sayfa FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    toplam_sayfa = book['toplam_sayfa'] if book else 0
    
    conn.close()
    
    yuzde = int((toplam_okunan / toplam_sayfa) * 100) if toplam_sayfa > 0 else 0
    
    return {
        'toplam_okunan': toplam_okunan,
        'toplam_sayfa': toplam_sayfa,
        'yuzde': yuzde,
        'kalan_sayfa': max(0, toplam_sayfa - toplam_okunan)
    }


def get_reading_stats(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Okuma istatistiklerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    from_date = (date.today() - timedelta(days=days-1)).isoformat()
    
    # Toplam okunan sayfa
    cursor.execute("""
        SELECT SUM(okunan_sayfa) as toplam
        FROM reading_progress
        WHERE user_id = ? AND tarih >= ?
    """, (user_id, from_date))
    
    result = cursor.fetchone()
    toplam = result['toplam'] if result['toplam'] else 0
    
    # Günlük ortalama
    ortalama = toplam / days if days > 0 else 0
    
    # Kitap bazında
    cursor.execute("""
        SELECT b.baslik, SUM(rp.okunan_sayfa) as okunan
        FROM reading_progress rp
        JOIN books b ON rp.book_id = b.id
        WHERE rp.user_id = ? AND rp.tarih >= ?
        GROUP BY b.id
        ORDER BY okunan DESC
    """, (user_id, from_date))
    
    kitap_bazinda = cursor.fetchall()
    conn.close()
    
    return {
        'toplam_sayfa': toplam,
        'gun_sayisi': days,
        'ortalama': round(ortalama, 1),
        'kitap_bazinda': [dict(k) for k in kitap_bazinda]
    }


# Veritabanını başlat
init_kitap_database()


# ==================== EKSİK FONKSİYONLAR ====================

def update_reading_progress(book_id: int, okunan_sayfa: int) -> bool:
    """Kitap okuma ilerlemesini güncelle"""
    conn = get_connection()
    cursor = conn.cursor()

    # Kitabın user_id'sini al
    cursor.execute("SELECT user_id FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()

    if not book:
        conn.close()
        return False

    # İlerleme ekle
    cursor.execute("""
        INSERT INTO reading_progress (user_id, book_id, okunan_sayfa, tarih)
        VALUES (?, ?, ?, ?)
    """, (book['user_id'], book_id, okunan_sayfa, date.today().isoformat()))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def add_reading_session(user_id: int, book_id: int, dakika: int, sayfa: int) -> Dict[str, Any]:
    """Okuma oturumu ekle (dakika ve sayfa)"""
    conn = get_connection()
    cursor = conn.cursor()

    tarih = date.today()

    # İlerleme ekle
    cursor.execute("""
        INSERT INTO reading_progress (user_id, book_id, okunan_sayfa, tarih)
        VALUES (?, ?, ?, ?)
    """, (user_id, book_id, sayfa, tarih.isoformat()))

    conn.commit()
    progress_id = cursor.lastrowid

    cursor.execute("SELECT * FROM reading_progress WHERE id = ?", (progress_id,))
    progress = cursor.fetchone()
    conn.close()

    return dict(progress)


def delete_book(book_id: int) -> bool:
    """Kitabı ve ilişkili tüm kayıtları sil"""
    conn = get_connection()
    cursor = conn.cursor()

    # İlişkili kayıtları sil
    cursor.execute("DELETE FROM book_notes WHERE book_id = ?", (book_id,))
    cursor.execute("DELETE FROM reading_progress WHERE book_id = ?", (book_id,))

    # Kitabı sil
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0
