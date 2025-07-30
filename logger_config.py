"""
🔍 Akıllı Loglama Sistemi
========================
Streamlit uyarılarını filtreler ve sadece önemli mesajları gösterir
"""

import logging
import warnings
import sys
from datetime import datetime
import streamlit as st

class StreamlitLogFilter(logging.Filter):
    """Streamlit'in gereksiz uyarılarını filtreler"""
    
    FILTERED_MESSAGES = [
        "missing ScriptRunContext",
        "ScriptRunContext",
        "Thread 'MainThread'",
        "Session state does not function when running a script without",
        "Warning: to view this Streamlit app on a browser, run it with the following",
        "streamlit run",
        "scriptrunner_utils",
        "runtime.scriptrunner"
    ]
    
    def filter(self, record):
        """Mesajı filtrele"""
        message = record.getMessage()
        
        # Gereksiz Streamlit mesajlarını engelle
        for filtered_msg in self.FILTERED_MESSAGES:
            if filtered_msg in message:
                return False
        
        # Diğer mesajları geçir
        return True

class CustomFormatter(logging.Formatter):
    """Özel log formatı"""
    
    # ANSI renk kodları
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Zamanı kısalt
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Level'e göre renk seç
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Emoji seç
        emoji_map = {
            'DEBUG': '🔍',
            'INFO': '✅', 
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        emoji = emoji_map.get(record.levelname, '📝')
        
        # Modül adını kısalt
        module_name = record.name.split('.')[-1] if '.' in record.name else record.name
        
        # Format: [HH:MM:SS] 🔍 MODULE: Message
        formatted = f"[{timestamp}] {emoji} {color}{module_name.upper()}{reset}: {record.getMessage()}"
        
        return formatted

def setup_logging():
    """Loglama sistemini kur"""
    
    # Streamlit logger'ını sessizleştir
    streamlit_logger = logging.getLogger('streamlit')
    streamlit_logger.setLevel(logging.ERROR)
    streamlit_logger.addFilter(StreamlitLogFilter())
    
    # Ana logger'ı kur
    logger = logging.getLogger('whisper_app')
    logger.setLevel(logging.INFO)
    
    # Handler varsa temizle
    if logger.handlers:
        logger.handlers.clear()
    
    # Console handler ekle
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())
    console_handler.addFilter(StreamlitLogFilter())
    
    logger.addHandler(console_handler)
    
    # Python warnings'leri de filtrele
    warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
    warnings.filterwarnings("ignore", message=".*Thread.*MainThread.*")
    warnings.filterwarnings("ignore", module="streamlit.runtime.*")
    
    return logger

def get_logger(name):
    """Modül için logger al"""
    logger = logging.getLogger(f'whisper_app.{name}')
    return logger

# Ana logger'ı kur
setup_logging()
main_logger = get_logger('main')

# Progress logger'ı - Streamlit progress mesajları için
class ProgressLogger:
    """İşlem ilerlemesi için özel logger"""
    
    def __init__(self, name):
        self.name = name
        self.logger = get_logger(name)
    
    def start(self, message):
        """İşlem başlangıcı"""
        self.logger.info(f"🚀 {message}")
    
    def progress(self, step, total, message):
        """İlerleme durumu"""
        percentage = (step / total) * 100
        self.logger.info(f"⏳ {message} ({step}/{total} - {percentage:.0f}%)")
    
    def success(self, message):
        """Başarılı tamamlama"""
        self.logger.info(f"✅ {message}")
    
    def warning(self, message):
        """Uyarı"""
        self.logger.warning(f"⚠️ {message}")
    
    def error(self, message):
        """Hata"""
        self.logger.error(f"❌ {message}")
    
    def info(self, message):
        """Bilgi"""
        self.logger.info(f"📝 {message}")

# Özel loggerlar
youtube_logger = ProgressLogger('youtube')
translation_logger = ProgressLogger('translation')
database_logger = ProgressLogger('database')
transcription_logger = ProgressLogger('transcription')

if __name__ == "__main__":
    # Test
    test_logger = get_logger('test')
    test_logger.info("Test mesajı")
    test_logger.warning("Test uyarısı")
    test_logger.error("Test hatası")
    
    # Progress test
    progress = ProgressLogger('test_progress')
    progress.start("Test işlemi başladı")
    progress.progress(1, 3, "İlk adım")
    progress.progress(2, 3, "İkinci adım")
    progress.success("Test tamamlandı")
