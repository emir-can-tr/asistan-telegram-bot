"""
AI Servisi - Local API (OpenAI uyumlu) ve Gemini destegi
"""
import json
from openai import OpenAI
from typing import Dict, Any
from config import (
    API_MODE, LOCAL_API_URL, LOCAL_MODEL_NAME, LOCAL_API_KEY,
    GEMINI_API_KEY
)

local_client = None
if API_MODE == "local":
    local_client = OpenAI(
        base_url=LOCAL_API_URL,
        api_key=LOCAL_API_KEY
    )

gemini_model = None
if API_MODE == "gemini" and GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash')
    except:
        pass


def call_local_api(prompt: str) -> str:
    """Local API cagrisi (OpenAI uyumlu format)"""
    if not local_client:
        print("Local API client yapilandirilmamis")
        return ""

    try:
        response = local_client.chat.completions.create(
            model=LOCAL_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Sen bir kisisel asistan botsun. Sadece JSON formatinda yanit ver."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Local API hatasi: {e}")
        return ""


def call_gemini_api(prompt: str) -> str:
    """Gemini API cagrisi"""
    if not gemini_model:
        return ""
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API hatasi: {e}")
        return ""


SYSTEM_PROMPT = """Sen bir kisisel asistansin. Kullanicilarin aliskanliklarini, hatirlatmalarini, gorevlerini ve notlarini yonetmelerine yardimci oluyorsun.

BUGUNUN TARIHI: {current_date}

Kullanici mesajlarini analiz et ve asagidaki JSON formatinda yanit ver:

{{
    "action": "add_habit | complete_habit | list_habits | delete_habit | show_history | show_today | add_reminder | list_reminders | delete_reminder | add_task | list_tasks | complete_task | delete_task | add_note | list_notes | delete_note | chat",
    "habit_name": "Aliskanlik adi (varsa)",
    "frequency": "daily | weekly | monthly (yeni aliskanlik icin)",
    "target": "Hedef aciklamasi (varsa)",
    "days": 7,
    "reminder_title": "Hatirlatma basligi",
    "remind_at": "HH:MM formatinda saat",
    "remind_date": "YYYY-MM-DD formatinda tarih",
    "is_recurring": false,
    "task_title": "Gorev basligi",
    "task_due_date": "YYYY-MM-DD formatinda son tarih",
    "note_content": "Not icerigi",
    "response": "Kullaniciya gosterilecek Turkce mesaj"
}}

Her zaman samimi ve motive edici ol. Turkce yanit ver.
Sadece JSON formatinda yanit ver."""


async def analyze_message(user_message: str, user_habits: list = None, conversation_history: list = None) -> Dict[str, Any]:
    """Kullanici mesajini analiz et ve yapilacak islemi belirle"""
    from datetime import date
    
    current_date = date.today().isoformat()
    prompt_with_date = SYSTEM_PROMPT.format(current_date=current_date)
    
    context = ""
    if user_habits:
        habit_info = [f"'{h['name']}' ({h['frequency']})" for h in user_habits]
        context = f"\n\nKullanicinin mevcut aliskanliklari: {', '.join(habit_info)}"
    
    history_context = ""
    if conversation_history and len(conversation_history) > 0:
        history_lines = ["\n\nSON KONUSMALAR:"]
        for msg in conversation_history[-10:]:
            role_label = "Kullanici" if msg['role'] == 'user' else "Asistan"
            history_lines.append(f"- {role_label}: {msg['message'][:150]}")
        history_context = "\n".join(history_lines)
    
    prompt = f"{prompt_with_date}{context}{history_context}\n\nKullanici mesaji: {user_message}"
    
    try:
        if API_MODE == "local":
            response_text = call_local_api(prompt)
        else:
            response_text = call_gemini_api(prompt)

        if not response_text:
            return {
                "action": "chat",
                "response": "Uzgunum, su anda yanit veremiyorum. Lutfen tekrar deneyin."
            }

        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            response_text = response_text[start_idx:end_idx]

        result = json.loads(response_text)
        return result
        
    except json.JSONDecodeError:
        return {
            "action": "chat",
            "response": "Uzgunum, bir hata olustu. Lutfen tekrar deneyin."
        }
    except Exception as e:
        return {
            "action": "error",
            "response": f"Bir hata olustu: {str(e)}"
        }


def format_habits_list(habits: list) -> str:
    """Aliskanlik listesini guzel formatta goster"""
    if not habits:
        return "Henuz hic aliskanliginiz yok. Yeni bir aliskanlik eklemek icin bana soyleyin!"
    
    frequency_emoji = {
        "daily": "Gunluk",
        "weekly": "Haftalik",
        "monthly": "Aylik"
    }
    
    lines = ["*Aliskanliklariniz:*\n"]
    
    for i, habit in enumerate(habits, 1):
        freq = frequency_emoji.get(habit['frequency'], habit['frequency'])
        target = f" - {habit['target']}" if habit.get('target') else ""
        lines.append(f"{i}. *{habit['name']}* ({freq}){target}")
    
    return "\n".join(lines)


def format_reminder_message(habits: list) -> str:
    """Hatirlatma mesajini formatla"""
    if not habits:
        return None
    
    lines = ["*Hatirlatma!*\n\nBugun henuz tamamlamadiginiz aliskanliklar:\n"]
    
    for habit in habits:
        target = f" ({habit['target']})" if habit.get('target') else ""
        lines.append(f"- {habit['name']}{target}")
    
    lines.append("\nTamamladiginizda bana soylemeyi unutmayin!")
    
    return "\n".join(lines)


def format_history(completions: list, days: int) -> str:
    """Aliskanlik gecmisini formatla"""
    if not completions:
        return f"Son {days} gunde tamamlanmis aliskanlik bulunamadi."
    
    lines = [f"*Son {days} Gunluk Gecmisiniz:*\n"]
    
    from collections import defaultdict
    by_date = defaultdict(list)
    for c in completions:
        by_date[c['period_date']].append(c['habit_name'])
    
    for date_str in sorted(by_date.keys(), reverse=True):
        habits = by_date[date_str]
        lines.append(f"*{date_str}*")
        for habit in habits:
            lines.append(f"   - {habit}")
        lines.append("")
    
    return "\n".join(lines)


def format_today_summary(summary: dict) -> str:
    """Bugunku ozeti formatla"""
    date_str = summary['date']
    completed = summary['completed']
    uncompleted = summary['uncompleted']
    total = summary['total']
    completed_count = summary['completed_count']
    
    if total == 0:
        return "Henuz gunluk aliskanliginiz yok."
    
    percentage = int((completed_count / total) * 100) if total > 0 else 0
    
    lines = [f"*Bugunku Durumunuz ({date_str})*\n"]
    lines.append(f"Ilerleme: {completed_count}/{total} ({percentage}%)\n")
    
    if completed:
        lines.append("*Tamamlananlar:*")
        for h in completed:
            lines.append(f"   - {h['name']}")
        lines.append("")
    
    if uncompleted:
        lines.append("*Bekleyenler:*")
        for h in uncompleted:
            lines.append(f"   - {h['name']}")
    
    return "\n".join(lines)


def format_reminders_list(reminders: list) -> str:
    """Hatirlatma listesini guzel formatta goster"""
    if not reminders:
        return "Henuz hic hatirlatmaniz yok."
    
    lines = ["*Hatirlatmalariniz:*\n"]
    
    for i, reminder in enumerate(reminders, 1):
        recurring = "(tekrarli)" if reminder.get('is_recurring') else ""
        date_info = ""
        if reminder.get('remind_date'):
            date_info = f" ({reminder['remind_date']})"
        lines.append(f"{i}. *{reminder['title']}* - {reminder['remind_at']}{date_info} {recurring}")
    
    return "\n".join(lines)


def format_tasks_list(tasks: list) -> str:
    """Gorev listesini guzel formatta goster"""
    if not tasks:
        return "Henuz hic goreviniz yok."
    
    lines = ["*Gorevleriniz:*\n"]
    
    for i, task in enumerate(tasks, 1):
        status = "[x]" if task.get('is_completed') else "[ ]"
        due_info = ""
        if task.get('due_date'):
            due_info = f" ({task['due_date']})"
        lines.append(f"{i}. {status} *{task['title']}*{due_info}")
    
    return "\n".join(lines)


def format_reminder_notification(reminder: dict) -> str:
    """Hatirlatma bildirim mesajini formatla"""
    return f"*Hatirlatma!*\n\n{reminder['title']}\n\nSaat: {reminder['remind_at']}"


def format_notes_list(notes: list) -> str:
    """Not listesini guzel formatta goster"""
    if not notes:
        return "Henuz hic notunuz yok."
    
    lines = ["*Notlariniz:*\n"]
    
    for i, note in enumerate(notes, 1):
        content = note['content']
        if len(content) > 50:
            content = content[:50] + "..."
        
        created = note.get('created_at', '')
        if created:
            date_part = created.split(' ')[0] if ' ' in created else created.split('T')[0]
            lines.append(f"{i}. {content} ({date_part})")
        else:
            lines.append(f"{i}. {content}")
    
    return "\n".join(lines)
