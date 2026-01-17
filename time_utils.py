"""
Zaman ve Tarih Yardımcı Modülü
Timezone ayarlı doğru zaman yönetimi için kullanılır.
"""
from datetime import datetime, date, timedelta
import pytz
from config import TIMEZONE

def get_timezone(tz_name: str = None):
    """Config'deki veya verilen timezone objesini döndür"""
    try:
        return pytz.timezone(tz_name or TIMEZONE)
    except Exception:
        # Fallback to Europe/Istanbul if invalid
        return pytz.timezone('Europe/Istanbul')

def get_now() -> datetime:
    """Sistem timezone ayarlı şimdiki zamanı döndür"""
    tz = get_timezone()
    return datetime.now(tz)

def get_user_now(user_timezone: str = None) -> datetime:
    """Kullanıcının timezone ayarlı şimdiki zamanını döndür"""
    tz = get_timezone(user_timezone)
    return datetime.now(tz)

def get_current_time_str() -> str:
    """Şimdiki saati HH:MM formatında döndür"""
    return get_now().strftime("%H:%M")

def get_today_str() -> str:
    """Bugünün tarihini ISO formatında (YYYY-MM-DD) döndür"""
    return get_now().date().isoformat()

def get_today_date() -> date:
    """Bugünün tarihini date objesi olarak döndür"""
    return get_now().date()

def str_to_time(time_str: str) -> datetime:
    """HH:MM stringini bugünün timezone ayarlı datetime objesine çevir"""
    now = get_now()
    try:
        hour, minute = map(int, time_str.split(':'))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return now
