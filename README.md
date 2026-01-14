# 🤖 Asistan Bot - VDS Kurulum Rehberi

Kişisel asistan Telegram botu. OpenAI uyumlu Local API veya Gemini API desteği.

## 📋 Özellikler

- 🤖 **Asistan**: Alışkanlık takibi, hatırlatmalar, görevler, notlar
- 📚 **Ders**: Ders programı, çalışma kaydı, soru çözümü, ödev takibi
- 🇬🇧 **İngilizce**: Kelime öğrenme, spaced repetition
- 📖 **Kitap**: Okuma listesi, kitap notları
- 📔 **Not Defteri**: Kategorili not sistemi
- 🚀 **Proje**: Proje yönetimi

## 🚀 Hızlı Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/emir-can-tr/asistan-telegram-bot.git
cd asistan-telegram-bot

# 2. Kurulum scriptini çalıştır
sudo ./setup.sh
```

## 📦 Manuel Kurulum

### 1. Sistem Gereksinimleri

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv
```

### 2. Bot Kurulumu

```bash
# Dizin oluştur
sudo mkdir -p /opt/asistan-bot
sudo cp -r * /opt/asistan-bot/
cd /opt/asistan-bot

# Sanal ortam
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env dosyasını düzenle
cp .env.example .env
nano .env
```

### 3. .env Yapılandırması

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
API_MODE=local
LOCAL_API_URL=http://127.0.0.1:8045/v1
LOCAL_API_KEY=your_api_key_here
LOCAL_MODEL_NAME=your_model_name
REMINDER_START_HOUR=8
REMINDER_END_HOUR=22
REMINDER_ENABLED=true
TIMEZONE=Europe/Istanbul
```

### 4. Systemd Servisi

```bash
sudo cp asistan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable asistan
sudo systemctl start asistan
```

## 📁 Dosya Yapısı

```
asistan-telegram-bot/
├── bot.py              # Ana bot
├── config.py           # Yapılandırma
├── database.py         # Ana veritabanı
├── scheduler.py        # Hatırlatmalar
├── ai_service.py       # AI servisi
├── requirements.txt    # Python bağımlılıkları
├── modules/            # Bot modülleri
│   ├── asistan_bot.py
│   ├── ders_bot.py
│   ├── ingilizce_bot.py
│   ├── kitap_bot.py
│   ├── notdefteri_bot.py
│   └── proje_bot.py
└── venv/               # Python sanal ortam
```

## 📝 Lisans

MIT License
