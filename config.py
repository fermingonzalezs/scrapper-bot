"""
Configuración del bot de monitoreo de eBay
"""
import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class Config:
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # eBay Search Parameters
    EBAY_SEARCH_URL: str = "https://www.ebay.com/sch/i.html"
    SEARCH_QUERY: str = "laptop"
    CATEGORY_ID: str = "0"  # Todas las categorías para búsquedas más amplias
    
    # Configuración de scraping
    REQUEST_DELAY: float = 1.0
    REQUEST_TIMEOUT: int = 10
    
    # Headers para requests
    HEADERS: dict = field(default_factory=lambda: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    @classmethod
    def load(cls):
        """Cargar configuración desde variables de entorno"""
        return cls()
    
    def validate(self) -> bool:
        """Validar que la configuración sea correcta"""
        if not self.TELEGRAM_BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
            return False
        
        if not self.TELEGRAM_CHAT_ID:
            print("ERROR: TELEGRAM_CHAT_ID no configurado")
            return False
        
        return True