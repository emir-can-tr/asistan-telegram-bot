"""
Voice Service - Sesli mesajları text'e çevirme
Gemini API'nin audio desteğini kullanır
"""
import os
import tempfile
import google.generativeai as genai
from config import GEMINI_API_KEY, API_MODE, LOCAL_API_URL, LOCAL_API_KEY, LOCAL_MODEL_NAME

# Gemini API'yi yapılandır
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def transcribe_voice_gemini(audio_path: str) -> dict:
    """
    Gemini API ile ses dosyasını text'e çevir
    
    Args:
        audio_path: Ses dosyasının yolu (.ogg, .mp3, .wav, .m4a)
        
    Returns:
        dict: {'success': bool, 'text': str, 'error': str}
    """
    try:
        if not GEMINI_API_KEY:
            return {
                'success': False,
                'text': '',
                'error': 'Gemini API key bulunamadı'
            }
        
        # Dosyayı yükle
        audio_file = genai.upload_file(audio_path)
        
        # Model oluştur
        model = genai.GenerativeModel('gemini-3.0-flash')
        
        # Transcription prompt
        prompt = """Bu ses dosyasını dinle ve içindeki konuşmayı Türkçe olarak yazıya dök.
        
Sadece konuşmanın metnini yaz, başka açıklama ekleme.
Eğer ses net değilse, anladığın kadarını yaz."""
        
        # Generate content
        response = model.generate_content([prompt, audio_file])
        
        if response.text:
            return {
                'success': True,
                'text': response.text.strip(),
                'error': ''
            }
        else:
            return {
                'success': False,
                'text': '',
                'error': 'Gemini yanıt vermedi'
            }
            
    except Exception as e:
        return {
            'success': False,
            'text': '',
            'error': str(e)
        }


async def transcribe_telegram_voice(bot, voice_file_id: str) -> dict:
    """
    Telegram sesli mesajını indir ve transcribe et
    
    Args:
        bot: Telegram bot instance
        voice_file_id: Telegram dosya ID'si
        
    Returns:
        dict: {'success': bool, 'text': str, 'error': str}
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
        
        # Transcribe et
        result = transcribe_voice_gemini(temp_path)
        
        return result
        
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
