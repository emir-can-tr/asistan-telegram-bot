"""
İngilizce Modülü Database
Ayrı database: modules/ingilizce/ingilizce.db
"""
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import os


# Database path - modules/ingilizce klasörü içinde
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DB_DIR, "ingilizce.db")


def get_connection():
    """İngilizce veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_ingilizce_database():
    """İngilizce modülü tablolarını oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kelimeler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            meaning TEXT NOT NULL,
            example1 TEXT,
            example2 TEXT,
            example3 TEXT,
            durum TEXT DEFAULT 'ogrenilmedi',
            learn_date DATE,
            last_review DATE,
            next_review DATE,
            review_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Günlük hedefler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gunluk_kelime_sayisi INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Öğrenme oturumları tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tarih DATE NOT NULL,
            kelime_sayisi INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


# ==================== KELİME İŞLEMLERİ ====================

def add_word(user_id: int, word: str, meaning: str, 
             example1: str = None, example2: str = None, example3: str = None) -> Dict[str, Any]:
    """Yeni kelime ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO words (user_id, word, meaning, example1, example2, example3)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, word.lower(), meaning, example1, example2, example3))
    
    conn.commit()
    word_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
    word_data = cursor.fetchone()
    conn.close()
    
    return dict(word_data)


def get_user_words(user_id: int, durum: str = None) -> List[Dict[str, Any]]:
    """Kullanıcının kelimelerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if durum:
        cursor.execute("""
            SELECT * FROM words 
            WHERE user_id = ? AND durum = ?
            ORDER BY created_at DESC
        """, (user_id, durum))
    else:
        cursor.execute("""
            SELECT * FROM words 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    
    words = cursor.fetchall()
    conn.close()
    
    return [dict(w) for w in words]


def get_word_by_word(user_id: int, word: str) -> Optional[Dict[str, Any]]:
    """Kelime ile ara"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM words
        WHERE user_id = ? AND LOWER(word) = ?
        LIMIT 1
    """, (user_id, word.lower()))
    
    word_data = cursor.fetchone()
    conn.close()
    
    return dict(word_data) if word_data else None


def mark_word_learned(word_id: int) -> bool:
    """Kelimeyi öğrenildi olarak işaretle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today()
    next_review = today + timedelta(days=1)  # İlk tekrar 1 gün sonra
    
    cursor.execute("""
        UPDATE words 
        SET durum = 'ogreniyor', 
            learn_date = ?,
            last_review = ?,
            next_review = ?,
            review_count = 1
        WHERE id = ?
    """, (today.isoformat(), today.isoformat(), next_review.isoformat(), word_id))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def update_word_review(word_id: int) -> Dict[str, Any]:
    """Kelime tekrarını güncelle (Spaced Repetition)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Mevcut durumu al
    cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
    word = cursor.fetchone()
    
    if not word:
        conn.close()
        return None
    
    review_count = word['review_count'] + 1
    today = date.today()
    
    # Spaced Repetition aralıkları
    intervals = [1, 3, 7, 14, 30]  # gün
    
    if review_count - 1 < len(intervals):
        days_to_add = intervals[review_count - 1]
    else:
        days_to_add = 30  # Maksimum 30 gün
    
    next_review = today + timedelta(days=days_to_add)
    
    # Eğer 5+ tekrar olduysa öğrenildi durumuna geç
    new_durum = 'ogrenildi' if review_count >= 5 else 'ogreniyor'
    
    cursor.execute("""
        UPDATE words 
        SET last_review = ?,
            next_review = ?,
            review_count = ?,
            durum = ?
        WHERE id = ?
    """, (today.isoformat(), next_review.isoformat(), review_count, new_durum, word_id))
    
    conn.commit()
    conn.close()
    
    return {
        'review_count': review_count,
        'next_review': next_review.isoformat(),
        'durum': new_durum,
        'interval_days': days_to_add
    }


def get_words_for_review(user_id: int) -> List[Dict[str, Any]]:
    """Tekrar edilecek kelimeleri getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute("""
        SELECT * FROM words
        WHERE user_id = ? 
        AND durum = 'ogreniyor'
        AND next_review <= ?
        ORDER BY next_review ASC
    """, (user_id, today))
    
    words = cursor.fetchall()
    conn.close()
    
    return [dict(w) for w in words]


# ==================== HEDEF İŞLEMLERİ ====================

def set_daily_goal(user_id: int, gunluk_kelime_sayisi: int) -> Dict[str, Any]:
    """Günlük hedef belirle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Eğer varsa güncelle, yoksa ekle
    cursor.execute("""
        SELECT id FROM daily_goals
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))
    
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE daily_goals
            SET gunluk_kelime_sayisi = ?
            WHERE id = ?
        """, (gunluk_kelime_sayisi, existing['id']))
        goal_id = existing['id']
    else:
        cursor.execute("""
            INSERT INTO daily_goals (user_id, gunluk_kelime_sayisi)
            VALUES (?, ?)
        """, (user_id, gunluk_kelime_sayisi))
        goal_id = cursor.lastrowid
    
    conn.commit()
    
    cursor.execute("SELECT * FROM daily_goals WHERE id = ?", (goal_id,))
    goal = cursor.fetchone()
    conn.close()
    
    return dict(goal)


def get_user_daily_goal(user_id: int) -> Optional[Dict[str, Any]]:
    """Kullanıcının günlük hedefini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM daily_goals
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))
    
    goal = cursor.fetchone()
    conn.close()
    
    return dict(goal) if goal else None


def get_daily_words(user_id: int, count: int) -> List[Dict[str, Any]]:
    """Günlük öğrenilecek kelimeleri getir (öğrenilmemiş)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM words
        WHERE user_id = ? AND durum = 'ogrenilmedi'
        ORDER BY created_at ASC
        LIMIT ?
    """, (user_id, count))
    
    words = cursor.fetchall()
    conn.close()
    
    return [dict(w) for w in words]


# ==================== OTURUM İŞLEMLERİ ====================

def add_learning_session(user_id: int, kelime_sayisi: int, tarih: date = None) -> Dict[str, Any]:
    """Öğrenme oturumu ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if tarih is None:
        tarih = date.today()
    
    cursor.execute("""
        INSERT INTO learning_sessions (user_id, tarih, kelime_sayisi)
        VALUES (?, ?, ?)
    """, (user_id, tarih.isoformat(), kelime_sayisi))
    
    conn.commit()
    session_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM learning_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    conn.close()
    
    return dict(session)


def get_learning_stats(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Öğrenme istatistiklerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Toplam kelime sayıları
    cursor.execute("""
        SELECT COUNT(*) as toplam FROM words WHERE user_id = ?
    """, (user_id,))
    toplam = cursor.fetchone()['toplam']
    
    cursor.execute("""
        SELECT COUNT(*) as ogrenildi FROM words 
        WHERE user_id = ? AND durum = 'ogrenildi'
    """, (user_id,))
    ogrenildi = cursor.fetchone()['ogrenildi']
    
    cursor.execute("""
        SELECT COUNT(*) as ogreniyor FROM words 
        WHERE user_id = ? AND durum = 'ogreniyor'
    """, (user_id,))
    ogreniyor = cursor.fetchone()['ogreniyor']
    
    cursor.execute("""
        SELECT COUNT(*) as ogrenilmedi FROM words 
        WHERE user_id = ? AND durum = 'ogrenilmedi'
    """, (user_id,))
    ogrenilmedi = cursor.fetchone()['ogrenilmedi']
    
    # Son X günün oturumları
    from_date = (date.today() - timedelta(days=days-1)).isoformat()
    cursor.execute("""
        SELECT SUM(kelime_sayisi) as toplam_ogrenilen
        FROM learning_sessions
        WHERE user_id = ? AND tarih >= ?
    """, (user_id, from_date))
    
    result = cursor.fetchone()
    toplam_ogrenilen = result['toplam_ogrenilen'] if result['toplam_ogrenilen'] else 0
    
    conn.close()
    
    return {
        'toplam': toplam,
        'ogrenildi': ogrenildi,
        'ogreniyor': ogreniyor,
        'ogrenilmedi': ogrenilmedi,
        'son_gun': days,
        'toplam_ogrenilen': toplam_ogrenilen,
        'gunluk_ortalama': round(toplam_ogrenilen / days, 1) if days > 0 else 0
    }


# Veritabanını başlat
init_ingilizce_database()


# ==================== EKSİK FONKSİYONLAR ====================

def get_word_by_text(user_id: int, word: str) -> Optional[Dict[str, Any]]:
    """Kelime ile ara (get_word_by_word alias)"""
    return get_word_by_word(user_id, word)


def start_learning_word(word_id: int) -> bool:
    """Kelimeyi öğrenmeye başla (mark_word_learned alias)"""
    return mark_word_learned(word_id)


def delete_word(word_id: int) -> bool:
    """Kelimeyi sil"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM words WHERE id = ?", (word_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0
