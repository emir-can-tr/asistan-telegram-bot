"""
Not Defteri Database
Kategorili notlar, arama, favoriler
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DB_DIR, "notdefteri.db")

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_notdefteri_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            baslik TEXT NOT NULL,
            icerik TEXT NOT NULL,
            kategori_path TEXT DEFAULT 'Genel',
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Kategori yönetimi tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            parent_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name, parent_path)
        )
    """)
    
    conn.commit()
    conn.close()

def add_note(user_id: int, baslik: str, icerik: str, kategori_path: str = "Genel") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO notes (user_id, baslik, icerik, kategori_path)
        VALUES (?, ?, ?, ?)
    """, (user_id, baslik, icerik, kategori_path))
    
    conn.commit()
    note_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    conn.close()
    
    return dict(note)

def get_user_notes(user_id: int, kategori_path: str = None, favorites_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM notes WHERE user_id = ?"
    params = [user_id]
    
    if kategori_path:
        query += " AND kategori_path = ?"
        params.append(kategori_path)
    
    if favorites_only:
        query += " AND is_favorite = 1"
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    notes = cursor.fetchall()
    conn.close()
    
    return [dict(n) for n in notes]

def search_notes(user_id: int, keyword: str, kategori_path: str = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM notes 
        WHERE user_id = ? 
        AND (UPPER(baslik) LIKE ? OR UPPER(icerik) LIKE ?)
    """
    params = [user_id, f"%{keyword.upper()}%", f"%{keyword.upper()}%"]
    
    if kategori_path:
        query += " AND kategori_path = ?"
        params.append(kategori_path)
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    notes = cursor.fetchall()
    conn.close()
    
    return [dict(n) for n in notes]

def toggle_favorite(note_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_favorite FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    
    if not note:
        conn.close()
        return False
    
    new_value = 0 if note['is_favorite'] else 1
    
    cursor.execute("""
        UPDATE notes 
        SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_value, note_id))
    
    conn.commit()
    conn.close()
    
    return True

def delete_note(note_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0

def get_categories(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT kategori_path, COUNT(*) as sayi
        FROM notes
        WHERE user_id = ?
        GROUP BY kategori_path
        ORDER BY sayi DESC
    """, (user_id,))
    
    categories = cursor.fetchall()
    conn.close()
    
    return [dict(c) for c in categories]

def add_category(user_id: int, name: str, parent_path: str = None) -> Dict[str, Any]:
    """Yeni kategori ekle (hiyerarşik)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO categories (user_id, name, parent_path)
            VALUES (?, ?, ?)
        """, (user_id, name, parent_path))
        
        conn.commit()
        cat_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        category = cursor.fetchone()
        conn.close()
        
        return dict(category)
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_user_categories(user_id: int) -> List[Dict[str, Any]]:
    """Kullanıcının tüm kategorilerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM categories
        WHERE user_id = ?
        ORDER BY parent_path, name
    """, (user_id,))
    
    categories = cursor.fetchall()
    conn.close()
    
    return [dict(c) for c in categories]

def build_category_path(name: str, parent_path: str = None) -> str:
    """Kategori path oluştur: Ana > Alt > AltAlt"""
    if parent_path:
        return f"{parent_path} > {name}"
    return name


# ==================== EKSİK FONKSİYONLAR ====================

def get_notes_by_category(user_id: int, kategori: str) -> List[Dict[str, Any]]:
    """Kategoriye göre notları getir (get_user_notes wrapper)"""
    return get_user_notes(user_id, kategori_path=kategori)


init_notdefteri_database()
