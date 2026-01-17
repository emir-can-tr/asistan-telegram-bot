"""
Veritabanı işlemleri - SQLite ile alışkanlık ve kullanıcı yönetimi
"""
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH


def get_connection():
    """Veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Veritabanı tablolarını oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kullanıcılar tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            timezone TEXT DEFAULT 'Europe/Istanbul',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migrasyon: timezone kolonu yoksa ekle
    try:
        cursor.execute("SELECT timezone FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("Migrasyon: users tablosuna timezone kolonu ekleniyor...")
        cursor.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Istanbul'")

    # Alışkanlıklar tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            frequency TEXT NOT NULL,
            target TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Alışkanlık tamamlama kayıtları
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            period_date DATE NOT NULL,
            notes TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        )
    """)
    
    # Hatırlatmalar tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            remind_date DATE,
            is_recurring BOOLEAN DEFAULT 0,
            is_sent BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Görevler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date DATE,
            is_completed BOOLEAN DEFAULT 0,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Notlar tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Konuşma geçmişi tablosu (AI hafızası için)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Kullanıcı aktif modül tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_current_module (
            user_id INTEGER PRIMARY KEY,
            module_name TEXT NOT NULL DEFAULT 'asistan',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()


# ==================== KULLANICI İŞLEMLERİ ====================

def get_all_users() -> List[Dict[str, Any]]:
    """Tüm kullanıcıları getir"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return [dict(u) for u in users]


def update_user_timezone(user_id: int, timezone: str):
    """Kullanıcının zaman dilimini güncelle"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET timezone = ? WHERE id = ?", (timezone, user_id))
    conn.commit()
    conn.close()


def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
    """Kullanıcıyı getir veya oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if user:
        conn.close()
        return dict(user)
    
    cursor.execute(
        "INSERT INTO users (telegram_id, username, first_name, timezone) VALUES (?, ?, ?, ?)",
        (telegram_id, username, first_name, 'Europe/Istanbul')
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user)


def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Telegram ID ile kullanıcı getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user) if user else None


# ==================== ALIŞKANLIK İŞLEMLERİ ====================

def add_habit(user_id: int, name: str, frequency: str, description: str = None, target: str = None) -> Dict[str, Any]:
    """Yeni alışkanlık ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO habits (user_id, name, description, frequency, target) 
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, name, description, frequency, target)
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM habits WHERE id = ?", (cursor.lastrowid,))
    habit = cursor.fetchone()
    conn.close()
    
    return dict(habit)


def get_user_habits(user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """Kullanıcının alışkanlıklarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute(
            "SELECT * FROM habits WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (user_id,)
        )
    else:
        cursor.execute(
            "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
    
    habits = cursor.fetchall()
    conn.close()
    
    return [dict(h) for h in habits]


def normalize_turkish(text: str) -> str:
    """Türkçe karakterleri normalize et ve küçük harfe çevir"""
    if not text:
        return ""
    text = text.lower()
    # Türkçe karakter dönüşümleri
    replacements = {
        'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def get_habit_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """İsme göre alışkanlık getir (Türkçe karakter ve büyük/küçük harf toleranslı)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tüm aktif alışkanlıkları getir
    cursor.execute(
        "SELECT * FROM habits WHERE user_id = ? AND is_active = 1",
        (user_id,)
    )
    habits = cursor.fetchall()
    conn.close()
    
    if not habits:
        return None
    
    # Aranan ismi normalize et
    search_normalized = normalize_turkish(name)
    
    # Önce tam eşleşme dene
    for habit in habits:
        habit_normalized = normalize_turkish(habit['name'])
        if habit_normalized == search_normalized:
            return dict(habit)
    
    # Sonra kısmi eşleşme dene (içeriyor mu?)
    for habit in habits:
        habit_normalized = normalize_turkish(habit['name'])
        if search_normalized in habit_normalized or habit_normalized in search_normalized:
            return dict(habit)
    
    # Son olarak kelime bazlı eşleşme dene
    search_words = set(search_normalized.split())
    for habit in habits:
        habit_normalized = normalize_turkish(habit['name'])
        habit_words = set(habit_normalized.split())
        # Herhangi bir kelime eşleşiyor mu?
        if search_words & habit_words:
            return dict(habit)
    
    return None


def delete_habit(habit_id: int) -> bool:
    """Alışkanlığı sil (pasif yap)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE habits SET is_active = 0 WHERE id = ?", (habit_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


# ==================== TAMAMLAMA İŞLEMLERİ ====================

def complete_habit(habit_id: int, period_date: date = None, notes: str = None) -> Dict[str, Any]:
    """Alışkanlığı tamamlandı olarak işaretle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if period_date is None:
        period_date = date.today()
    
    # Önce bu dönem için zaten tamamlanmış mı kontrol et
    cursor.execute(
        "SELECT * FROM habit_completions WHERE habit_id = ? AND period_date = ?",
        (habit_id, period_date.isoformat())
    )
    existing = cursor.fetchone()
    
    if existing:
        conn.close()
        return dict(existing)
    
    cursor.execute(
        "INSERT INTO habit_completions (habit_id, period_date, notes) VALUES (?, ?, ?)",
        (habit_id, period_date.isoformat(), notes)
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM habit_completions WHERE id = ?", (cursor.lastrowid,))
    completion = cursor.fetchone()
    conn.close()
    
    return dict(completion)


def is_habit_completed_today(habit_id: int) -> bool:
    """Alışkanlık bugün tamamlandı mı?"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    cursor.execute(
        "SELECT * FROM habit_completions WHERE habit_id = ? AND period_date = ?",
        (habit_id, today)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def get_uncompleted_habits_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Bugün tamamlanmamış alışkanlıkları getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute("""
        SELECT h.* FROM habits h
        WHERE h.user_id = ?
          AND h.is_active = 1
          AND h.frequency = 'daily'
          AND h.id NOT IN (
              SELECT habit_id FROM habit_completions WHERE period_date = ?
          )
    """, (user_id, today))
    
    habits = cursor.fetchall()
    conn.close()
    
    return [dict(h) for h in habits]


def get_all_users_with_uncompleted_habits() -> List[Dict[str, Any]]:
    """Tamamlanmamış alışkanlığı olan tüm kullanıcıları getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute("""
        SELECT DISTINCT u.* FROM users u
        INNER JOIN habits h ON h.user_id = u.id
        WHERE h.is_active = 1
          AND h.frequency = 'daily'
          AND h.id NOT IN (
              SELECT habit_id FROM habit_completions WHERE period_date = ?
          )
    """, (today,))
    
    users = cursor.fetchall()
    conn.close()
    
    return [dict(u) for u in users]


def get_habit_history(user_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """Kullanıcının alışkanlık geçmişini getir (belirtilen gün sayısı kadar)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    from_date = (date.today() - timedelta(days=days-1)).isoformat()
    
    cursor.execute("""
        SELECT 
            hc.period_date,
            h.name as habit_name,
            h.frequency,
            hc.completed_at
        FROM habit_completions hc
        INNER JOIN habits h ON h.id = hc.habit_id
        WHERE h.user_id = ?
          AND hc.period_date >= ?
        ORDER BY hc.period_date DESC, hc.completed_at DESC
    """, (user_id, from_date))
    
    completions = cursor.fetchall()
    conn.close()
    
    return [dict(c) for c in completions]


def get_daily_summary(user_id: int, target_date: date = None) -> Dict[str, Any]:
    """Belirli bir gün için alışkanlık özetini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.isoformat()
    
    # Günlük alışkanlıkları getir
    cursor.execute("""
        SELECT h.*, 
               CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed
        FROM habits h
        LEFT JOIN habit_completions hc ON h.id = hc.habit_id AND hc.period_date = ?
        WHERE h.user_id = ? AND h.is_active = 1 AND h.frequency = 'daily'
    """, (date_str, user_id))
    
    habits = cursor.fetchall()
    conn.close()
    
    completed = [dict(h) for h in habits if h['completed']]
    uncompleted = [dict(h) for h in habits if not h['completed']]
    
    return {
        'date': date_str,
        'completed': completed,
        'uncompleted': uncompleted,
        'total': len(habits),
        'completed_count': len(completed)
    }


# ==================== HATIRLATMA İŞLEMLERİ ====================

def add_reminder(user_id: int, title: str, remind_at: str, remind_date: date = None, is_recurring: bool = False) -> Dict[str, Any]:
    """Yeni hatırlatma ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    date_str = remind_date.isoformat() if remind_date else None
    
    cursor.execute(
        """INSERT INTO reminders (user_id, title, remind_at, remind_date, is_recurring) 
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, title, remind_at, date_str, is_recurring)
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,))
    reminder = cursor.fetchone()
    conn.close()
    
    return dict(reminder)


def get_user_reminders(user_id: int) -> List[Dict[str, Any]]:
    """Kullanıcının aktif hatırlatmalarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    # Tekrarlayan veya bugün/gelecek için olan hatırlatmaları getir
    cursor.execute("""
        SELECT * FROM reminders 
        WHERE user_id = ? 
          AND (is_recurring = 1 OR remind_date IS NULL OR remind_date >= ?)
        ORDER BY remind_at ASC
    """, (user_id, today))
    
    reminders = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in reminders]


def get_pending_reminders(current_time: str) -> List[Dict[str, Any]]:
    """Gönderilmesi gereken hatırlatmaları getir (Deprecated - use get_pending_reminders_by_user)"""
    # Bu fonksiyon geriye dönük uyumluluk için, ancak yeni sistemde 
    # kullanıcı bazlı kontrol yapılacağı için bunu artık pek kullanmayacağız.
    # Yine de "default" timezone varsayımıyla çalışabilir.
    return []


def get_pending_reminders_for_user(user_id: int, user_time_str: str, user_date_str: str) -> List[Dict[str, Any]]:
    """Belirli bir kullanıcı için gönderilmesi gereken hatırlatmaları getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Şu an gönderilmesi gereken hatırlatmalar
    cursor.execute("""
        SELECT r.*
        FROM reminders r
        WHERE r.user_id = ?
          AND r.remind_at = ?
          AND (r.is_recurring = 1 OR r.remind_date IS NULL OR r.remind_date = ?)
          AND r.is_sent = 0
    """, (user_id, user_time_str, user_date_str))
    
    reminders = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in reminders]


def mark_reminder_sent(reminder_id: int, is_recurring: bool = False):
    """Hatırlatmayı gönderildi olarak işaretle veya sil"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_recurring:
        # Tekrarlayan hatırlatma - is_sent'i sıfırla (yarın tekrar gönderilecek)
        cursor.execute("UPDATE reminders SET is_sent = 0 WHERE id = ?", (reminder_id,))
    else:
        # Tek seferlik hatırlatma - sil
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    
    conn.commit()
    conn.close()


def reset_daily_reminders():
    """Günlük tekrarlayan hatırlatmaları sıfırla (gece yarısı çağrılır)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE reminders SET is_sent = 0 WHERE is_recurring = 1")
    
    conn.commit()
    conn.close()


def delete_reminder(reminder_id: int) -> bool:
    """Hatırlatmayı sil"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def get_reminder_by_title(user_id: int, title: str) -> Optional[Dict[str, Any]]:
    """Başlığa göre hatırlatma getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reminders WHERE user_id = ?", (user_id,))
    reminders = cursor.fetchall()
    conn.close()
    
    if not reminders:
        return None
    
    search_normalized = normalize_turkish(title)
    
    for reminder in reminders:
        reminder_normalized = normalize_turkish(reminder['title'])
        if search_normalized in reminder_normalized or reminder_normalized in search_normalized:
            return dict(reminder)
    
    return None


# ==================== GÖREV İŞLEMLERİ ====================

def add_task(user_id: int, title: str, description: str = None, due_date: date = None) -> Dict[str, Any]:
    """Yeni görev ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    date_str = due_date.isoformat() if due_date else None
    
    cursor.execute(
        """INSERT INTO tasks (user_id, title, description, due_date) 
           VALUES (?, ?, ?, ?)""",
        (user_id, title, description, date_str)
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,))
    task = cursor.fetchone()
    conn.close()
    
    return dict(task)


def get_user_tasks(user_id: int, include_completed: bool = False) -> List[Dict[str, Any]]:
    """Kullanıcının görevlerini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if include_completed:
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY is_completed ASC, created_at DESC",
            (user_id,)
        )
    else:
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND is_completed = 0 ORDER BY created_at DESC",
            (user_id,)
        )
    
    tasks = cursor.fetchall()
    conn.close()
    
    return [dict(t) for t in tasks]


def complete_task(task_id: int) -> bool:
    """Görevi tamamla"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE tasks SET is_completed = 1, completed_at = ? WHERE id = ?",
        (datetime.now().isoformat(), task_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def delete_task(task_id: int) -> bool:
    """Görevi sil"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def get_task_by_title(user_id: int, title: str) -> Optional[Dict[str, Any]]:
    """Başlığa göre görev getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND is_completed = 0", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        return None
    
    search_normalized = normalize_turkish(title)
    
    for task in tasks:
        task_normalized = normalize_turkish(task['title'])
        if search_normalized in task_normalized or task_normalized in search_normalized:
            return dict(task)
    
    return None


# ==================== NOT İŞLEMLERİ ====================

def add_note(user_id: int, content: str, title: str = None) -> Dict[str, Any]:
    """Yeni not ekle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO notes (user_id, title, content) 
           VALUES (?, ?, ?)""",
        (user_id, title, content)
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,))
    note = cursor.fetchone()
    conn.close()
    
    return dict(note)


def get_user_notes(user_id: int) -> List[Dict[str, Any]]:
    """Kullanıcının notlarını getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    
    notes = cursor.fetchall()
    conn.close()
    
    return [dict(n) for n in notes]


def delete_note(note_id: int) -> bool:
    """Notu sil"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def get_note_by_content(user_id: int, search_text: str) -> Optional[Dict[str, Any]]:
    """İçeriğe göre not getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM notes WHERE user_id = ?", (user_id,))
    notes = cursor.fetchall()
    conn.close()
    
    if not notes:
        return None
    
    search_normalized = normalize_turkish(search_text)
    
    for note in notes:
        content_normalized = normalize_turkish(note['content'])
        title_normalized = normalize_turkish(note['title'] or '')
        if search_normalized in content_normalized or search_normalized in title_normalized:
            return dict(note)
    
    return None


# ==================== KONUŞMA GEÇMİŞİ İŞLEMLERİ ====================

def add_conversation_message(user_id: int, role: str, message: str):
    """Konuşma geçmişine mesaj ekle (role: 'user' veya 'assistant')"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO conversation_history (user_id, role, message) 
           VALUES (?, ?, ?)""",
        (user_id, role, message)
    )
    conn.commit()
    conn.close()


def get_conversation_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Kullanıcının son konuşma geçmişini getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, message, created_at FROM conversation_history 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))
    
    messages = cursor.fetchall()
    conn.close()
    
    # Ters çevir (eski mesajlar önce)
    return [dict(m) for m in reversed(messages)]


def clear_old_conversation_history(user_id: int, keep_last: int = 20):
    """Eski konuşma geçmişini temizle (son N mesajı tut)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM conversation_history 
        WHERE user_id = ? AND id NOT IN (
            SELECT id FROM conversation_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        )
    """, (user_id, user_id, keep_last))
    
    conn.commit()
    conn.close()



# ==================== MODÜL YÖNETİMİ ====================

def get_user_current_module(user_id: int) -> str:
    """Kullanıcının aktif modülünü getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT module_name FROM user_current_module WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result['module_name']
    
    # Varsayılan modül asistan
    set_user_current_module(user_id, 'asistan')
    return 'asistan'


def set_user_current_module(user_id: int, module_name: str):
    """Kullanıcının aktif modülünü ayarla"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO user_current_module (user_id, module_name, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET module_name = ?, updated_at = ?
    """, (user_id, module_name, datetime.now().isoformat(), module_name, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


# Veritabanını başlat
init_database()
