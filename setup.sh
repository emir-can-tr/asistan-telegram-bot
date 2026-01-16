#!/bin/bash
# ============================================
# Asistan Bot - VDS Kurulum Scripti
# ============================================

set -e

echo "=========================================="
echo "🤖 Asistan Bot VDS Kurulumu"
echo "=========================================="

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Çalışma dizini
INSTALL_DIR="/opt/asistan-bot"
SERVICE_USER="asistan"

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Bu scripti root olarak çalıştırın: sudo ./setup.sh${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/7] Sistem güncelleniyor...${NC}"
apt update && apt upgrade -y

echo -e "${YELLOW}[2/7] Python ve bağımlılıklar kuruluyor...${NC}"
apt install -y python3 python3-pip python3-venv

echo -e "${YELLOW}[3/7] Kullanıcı oluşturuluyor...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false $SERVICE_USER
    echo -e "${GREEN}Kullanıcı oluşturuldu: $SERVICE_USER${NC}"
else
    echo -e "${GREEN}Kullanıcı zaten mevcut: $SERVICE_USER${NC}"
fi

echo -e "${YELLOW}[4/7] Kurulum dizini oluşturuluyor...${NC}"
mkdir -p $INSTALL_DIR
cp -r ./* $INSTALL_DIR/
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

echo -e "${YELLOW}[5/7] Python sanal ortamı oluşturuluyor...${NC}"
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}[6/7] Systemd servisi kuruluyor...${NC}"
cp asistan.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable asistan

echo -e "${YELLOW}[7/7] .env dosyası oluşturuluyor...${NC}"
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env
    chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/.env
    chmod 600 $INSTALL_DIR/.env
    echo -e "${RED}⚠️  .env dosyasını düzenlemeyi unutmayın!${NC}"
    echo -e "${YELLOW}   nano $INSTALL_DIR/.env${NC}"
else
    echo -e "${GREEN}.env dosyası zaten mevcut${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Kurulum Tamamlandı!"
echo "==========================================${NC}"
echo ""
echo "Sonraki adımlar:"
echo "1. .env dosyasını düzenleyin:"
echo "   nano $INSTALL_DIR/.env"
echo ""
echo "2. Local API kurulumu (Ollama önerilen):"
echo "   curl -fsSL https://ollama.com/install.sh | sh"
echo "   ollama pull llama3.1"
echo ""
echo "3. Botu başlatın:"
echo "   systemctl start asistan"
echo ""
echo "4. Logları kontrol edin:"
echo "   journalctl -u asistan -f"
echo ""
