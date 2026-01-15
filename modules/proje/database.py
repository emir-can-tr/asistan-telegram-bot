"""
Proje Database - Projeler, Milestone'lar, Task'lar
"""
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DB_DIR, "proje.db")

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_proje_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Projeler
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            deadline DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Milestone'lar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            deadline DATE,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    
    # Task'lar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            milestone_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (milestone_id) REFERENCES milestones(id)
        )
    """)
    
    conn.commit()
    conn.close()

# Proje fonksiyonları
def add_project(user_id: int, name: str, description: str = None, deadline: date = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (user_id, name, description, deadline) VALUES (?, ?, ?, ?)",
                   (user_id, name, description, deadline.isoformat() if deadline else None))
    conn.commit()
    project_id = cursor.lastrowid
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()
    return dict(project)

def get_user_projects(user_id: int, status: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM projects WHERE user_id = ? AND status = ? ORDER BY created_at DESC", (user_id, status))
    else:
        cursor.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    projects = cursor.fetchall()
    conn.close()
    return [dict(p) for p in projects]

def add_milestone(project_id: int, name: str, deadline: date = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO milestones (project_id, name, deadline) VALUES (?, ?, ?)",
                   (project_id, name, deadline.isoformat() if deadline else None))
    conn.commit()
    milestone_id = cursor.lastrowid
    cursor.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()
    conn.close()
    return dict(milestone)

def add_task(milestone_id: int, name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (milestone_id, name) VALUES (?, ?)", (milestone_id, name))
    conn.commit()
    task_id = cursor.lastrowid
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()
    return dict(task)

def complete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def get_project_progress(project_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM milestones WHERE project_id = ?", (project_id,))
    total_milestones = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as completed FROM milestones WHERE project_id = ? AND completed = 1", (project_id,))
    completed_milestones = cursor.fetchone()['completed']

    conn.close()

    progress = int((completed_milestones / total_milestones) * 100) if total_milestones > 0 else 0

    return {
        'total_milestones': total_milestones,
        'completed_milestones': completed_milestones,
        'progress': progress
    }


# ==================== EKSİK FONKSİYONLAR ====================

def get_project_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """İsme göre proje bul"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM projects
        WHERE user_id = ? AND UPPER(name) LIKE ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, f"%{name.upper()}%"))

    project = cursor.fetchone()
    conn.close()

    return dict(project) if project else None


def add_project_task(project_id: int, name: str) -> Dict[str, Any]:
    """Projeye direkt görev ekle (önce varsayılan milestone oluşturur)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Projenin varsayılan milestone'unu bul veya oluştur
    cursor.execute("""
        SELECT id FROM milestones
        WHERE project_id = ? AND name = 'Genel'
        LIMIT 1
    """, (project_id,))

    milestone = cursor.fetchone()

    if milestone:
        milestone_id = milestone['id']
    else:
        # Varsayılan milestone oluştur
        cursor.execute("""
            INSERT INTO milestones (project_id, name)
            VALUES (?, 'Genel')
        """, (project_id,))
        milestone_id = cursor.lastrowid

    # Görevi ekle
    cursor.execute("""
        INSERT INTO tasks (milestone_id, name)
        VALUES (?, ?)
    """, (milestone_id, name))

    conn.commit()
    task_id = cursor.lastrowid

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()

    return dict(task)


def get_project_tasks(project_id: int) -> List[Dict[str, Any]]:
    """Projenin tüm görevlerini getir"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.*, m.name as milestone_name
        FROM tasks t
        JOIN milestones m ON t.milestone_id = m.id
        WHERE m.project_id = ?
        ORDER BY t.completed ASC, t.created_at DESC
    """, (project_id,))

    tasks = cursor.fetchall()
    conn.close()

    return [dict(t) for t in tasks]


def complete_project_task(task_id: int) -> bool:
    """Proje görevini tamamla"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def get_project_stats(user_id: int) -> Dict[str, Any]:
    """Proje istatistiklerini getir"""
    conn = get_connection()
    cursor = conn.cursor()

    # Toplam proje sayısı
    cursor.execute("SELECT COUNT(*) as toplam FROM projects WHERE user_id = ?", (user_id,))
    toplam_proje = cursor.fetchone()['toplam']

    # Aktif projeler
    cursor.execute("SELECT COUNT(*) as aktif FROM projects WHERE user_id = ? AND status = 'active'", (user_id,))
    aktif_proje = cursor.fetchone()['aktif']

    # Tamamlanan projeler
    cursor.execute("SELECT COUNT(*) as tamamlanan FROM projects WHERE user_id = ? AND status = 'completed'", (user_id,))
    tamamlanan_proje = cursor.fetchone()['tamamlanan']

    conn.close()

    return {
        'toplam_proje': toplam_proje,
        'aktif_proje': aktif_proje,
        'tamamlanan_proje': tamamlanan_proje
    }


def delete_project(project_id: int) -> bool:
    """Projeyi ve ilişkili tüm kayıtları sil"""
    conn = get_connection()
    cursor = conn.cursor()

    # Önce milestone'lara ait task'ları sil
    cursor.execute("""
        DELETE FROM tasks WHERE milestone_id IN (
            SELECT id FROM milestones WHERE project_id = ?
        )
    """, (project_id,))

    # Milestone'ları sil
    cursor.execute("DELETE FROM milestones WHERE project_id = ?", (project_id,))

    # Projeyi sil
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


init_proje_database()
