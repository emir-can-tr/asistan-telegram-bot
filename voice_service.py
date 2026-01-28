"""
Voice Service - Sesli mesajları text'e çevirme
Groq API (Whisper) kullanarak hızlı ve ücretsiz çeviri yapar
"""
import os
import tempfile
import requests
from config import GROQ_API_KEY, GEMINI_API_KEY

if not GROQ_API_KEY and GEMINI_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)


def transcribe_voice_groq(audio_path: str) -> dict:
    """
    Groq API ile ses dosyasını text'e çevir
    
    Args:
        audio_path: Ses dosyasının yolu
        
    Returns:
        dict: {'success': bool, 'text': str, 'error': str}
    """
    try:
        if not GROQ_API_KEY:
            return {
                'success': False,
                'text': '',
                'error': 'GROQ API key bulunamadı'
            }
            
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        
        # Dosyayı oku
        with open(audio_path, 'rb') as f:
            file_data = f.read()
        
        # Multipart form data
        files = {
            'file': ('voice.ogg', file_data, 'audio/ogg'),
            'model': (None, 'whisper-large-v3'),
            'language': (None, 'tr')  # Türkçe zorla
        }
        
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'text': result.get('text', '').strip(),
                'error': ''
            }
        else:
            return {
                'success': False,
                'text': '',
                'error': f'Groq Error: {response.text}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'text': '',
            'error': str(e)
        }


def transcribe_voice_gemini(audio_path: str) -> dict:
    """Yedek olarak Gemini kullan"""
    try:
        import google.generativeai as genai
        # Dosyayı yükle
        audio_file = genai.upload_file(audio_path)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = "Bu sesi Türkçe yazıya dök. Sadece dediklerini yaz."
        response = model.generate_content([prompt, audio_file])
        
        return {'success': True, 'text': response.text.strip(), 'error': ''}
    except Exception as e:
        return {'success': False, 'text': '', 'error': str(e)}


async def transcribe_telegram_voice(bot, voice_file_id: str) -> dict:
    """
    Telegram sesli mesajını indir ve transcribe et
    Önce Groq dener, başarısız olursa Gemini dener (eğer key varsa)
    """
    temp_path = None
    try:
        # Dosyayı indir
        file = await bot.get_file(voice_file_id)
        
        # Geçici dosya oluştur
        temp_fd, temp_path = tempfile.mkstemp(suffix='.ogg')
        os.close(temp_fd)
        
        # Dosyayı kaydet
        await file.download_to_drive(temp_path)
        
        # 1. Öncelik: Groq API
        if GROQ_API_KEY:
            result = transcribe_voice_groq(temp_path)
            if result['success']:
                return result
        
        # 2. Öncelik: Gemini API (Yedek)
        if GEMINI_API_KEY:
            return transcribe_voice_gemini(temp_path)
            
        return {
            'success': False, 
            'text': '', 
            'error': 'Aktif bir Speech-to-Text servisi bulunamadı (Groq veya Gemini)'
        }
        
    except Exception as e:
        return {
            'success': False,
            'text': '',
            'error': f'Dosya indirme hatası: {str(e)}'
        }
    finally:
        # Geçici dosyayı temizle
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
