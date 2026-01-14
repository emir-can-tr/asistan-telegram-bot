"""
Base Module - Tum bot modullerinin miras aldigi base class
"""
from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import Application, ContextTypes


class BaseModule(ABC):
    """Temel modul sinifi - Tum bot modulleri bu siniftan turer"""
    
    def __init__(self):
        self.module_name = self.get_module_name()
        self.module_description = self.get_module_description()
        self.module_emoji = self.get_module_emoji()
    
    @abstractmethod
    def get_module_name(self) -> str:
        """Modul adini dondur"""
        pass
    
    @abstractmethod
    def get_module_description(self) -> str:
        """Modul aciklamasini dondur"""
        pass
    
    @abstractmethod
    def get_module_emoji(self) -> str:
        """Modul emojisini dondur"""
        pass
    
    @abstractmethod
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Modul baslatma komutu"""
        pass
    
    @abstractmethod
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
        """Modul mesaj isleyici"""
        pass
    
    @abstractmethod
    def register_handlers(self, application: Application):
        """Modul handler'larini kaydet"""
        pass
    
    def get_help_text(self) -> str:
        """Modul yardim metnini dondur"""
        return f"{self.module_emoji} *{self.module_name.title()} Modulu*\n\n{self.module_description}"
