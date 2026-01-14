#!/bin/bash
set -e

echo "=========================================="
echo "Asistan Bot VDS Kurulumu"
echo "=========================================="

INSTALL_DIR="/opt/asistan-bot"
SERVICE_USER="asistan"

if [ "$EUID" -ne 0 ]; then
    echo "Bu scripti root olarak calistirin: sudo ./setup.sh"
    exit 1
fi

echo "[1/7] Sistem guncelleniyor..."
apt update && apt upgrade -y

echo "[2/7] Python ve bagimliliklar kuruluyor..."
apt install -y python3 python3-pip python3-venv

echo "[3/7] Kullanici olusturuluyor..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false $SERVICE_USER
fi

echo "[4/7] Kurulum dizini olusturuluyor..."
mkdir -p $INSTALL_DIR
cp -r ./* $INSTALL_DIR/
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

echo "[5/7] Python sanal ortami olusturuluyor..."
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[6/7] Systemd servisi kuruluyor..."
cp asistan.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable asistan

echo "[7/7] .env dosyasi kontrol ediliyor..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env
    echo ".env dosyasini duzenlemeyi unutmayin: nano $INSTALL_DIR/.env"
fi

echo ""
echo "Kurulum Tamamlandi!"
echo "1. .env dosyasini duzenleyin: nano $INSTALL_DIR/.env"
echo "2. Botu baslatin: systemctl start asistan"
echo "3. Loglari kontrol edin: journalctl -u asistan -f"
