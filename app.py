import os
import sys
import traceback
import logging
import signal
import uuid
import tempfile
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Dict, Any, Tuple, List, Callable
import threading
import gc
import json
from datetime import timedelta
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import defaultdict

# Streamlit MUST be imported first
import streamlit as st

# Windows console encoding handled by Streamlit automatically

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv_available = True
except ImportError:
    load_dotenv_available = False
    load_dotenv = lambda: None  # Dummy function
    st.warning("⚠️ python-dotenv not installed. Using environment variables only.")

try:
    from openai import OpenAI  # type: ignore
except ImportError:
    st.error("❌ openai package not found! Please install: pip install openai")
    st.stop()

import numpy as np

try:
    import librosa  # type: ignore
except ImportError:
    librosa = None
    st.warning("⚠️ librosa not installed. Audio analysis features will be limited.")

try:
    import soundfile as sf  # type: ignore
except ImportError:
    sf = None

import pandas as pd

try:
    import plotly.graph_objects as go  # type: ignore
except ImportError:
    go = None
    st.warning("⚠️ plotly not installed. Visualization features will be limited.")

# .env dosyasını yükle - config import'larından ÖNCE
if load_dotenv_available:
    load_dotenv()

# Kendi modüllerimiz - Multilingual version
from config import (
    OPENAI_API_KEY, APP_CONFIG, ALLOWED_FORMATS, FILE_SIZE_LIMITS,
    LANGUAGES, RESPONSE_FORMATS, AI_MODELS, AI_CONFIG, AI_FEATURES,
    SPEECH_SPEED_CATEGORIES, VIEW_MODES, get_text, set_language, 
    get_available_languages, get_language_name, get_current_language,
    UI_TEXTS, THEME_CONFIG, SYSTEM_CONFIG, AUDIO_CONFIG, ADVANCED_CONFIG,
    get_view_modes
)

DEBUG_MODE = False
CONFIG = SYSTEM_CONFIG
KEYBOARD_SHORTCUTS = {}

# Akıllı loglama sistemi - tüm modüllerden ÖNCE import et
from logger_config import setup_logging, transcription_logger
setup_logging()

from database import (
    DatabaseManager, db_manager, save_transcription_to_db, get_transcription_history,
    get_transcription_by_id, toggle_favorite, delete_transcription, export_database_to_json,
    get_file_hash
)
from utils import (
    MemoryManager, SecurityManager, AsyncAPIHandler, 
    TempFileManager, FileChunker, analyze_audio_file, create_waveform_plot,
    estimate_processing_time, analyze_text_with_ai, get_speech_speed_category,
    highlight_keywords_in_text, create_ai_analysis_display, initialize_openai_client
)
from export_utils import PDFExporter, WordExporter, ExcelExporter, QRCodeGenerator, ZipArchiver, EmailSender
from youtube_transcriber import render_youtube_tab
from translation_tab import render_translation_tab
from upload_tab import render_upload_tab, apply_upload_tab_styles
import matplotlib.pyplot as plt

try:
    import plotly.graph_objects as go  # type: ignore
except ImportError:
    go = None

try:
    from pydub import AudioSegment  # type: ignore
except ImportError:
    AudioSegment = None

import tempfile
import io
import re
from collections import Counter
import json
import sqlite3
from datetime import datetime
import hashlib
import pandas as pd
import base64

try:
    import qrcode  # type: ignore
except ImportError:
    qrcode = None

from io import BytesIO

try:
    from PIL import Image  # type: ignore
except ImportError:
    Image = None

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

try:
    from reportlab.lib.pagesizes import letter, A4  # type: ignore
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib import colors  # type: ignore
    reportlab_available = True
except ImportError:
    reportlab_available = False

try:
    from docx import Document  # type: ignore
    from docx.shared import Inches, Pt  # type: ignore
    from docx.enum.text import WD_ALIGN_PARAGRAPH  # type: ignore
    from docx.oxml.shared import OxmlElement, qn  # type: ignore
    docx_available = True
except ImportError:
    docx_available = False

# =============================================
# 🛡️ STREAMLIT PAGE CONFIGURATION (MUST BE FIRST)
# =============================================

# Sayfa konfigürasyonu - her şeyden önce çağrılmalı
st.set_page_config(
    page_title="EchoForge v0.1 by Whisper AI - Multilingual",
    page_icon="🔥",
    layout="wide",  # wide layout için daha iyi responsive
    initial_sidebar_state="expanded"  # Sidebar açık başlat
)

# =============================================
# 🛡️ CONSTANTS & CONFIGURATION
# =============================================

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================
# 🛡️ ERROR HANDLING & LOGGING SYSTEM (MOVED UP)
# =============================================

# Logging konfigürasyonu - UTF-8 encoding ile ve safer handlers
try:
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('whisper_ai.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler with UTF-8 safe formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
except Exception as e:
    # Fallback to basic logging if there's an issue
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning(f"Logging setup warning: {e}")

class WhisperAIError(Exception):
    """Whisper AI uygulaması için özel hata sınıfı"""
    def __init__(self, message: str, error_type: str = "GENERAL", details: Optional[str] = None):
        self.message = message
        self.error_type = error_type
        self.details = details
        super().__init__(self.message)

class ErrorHandler:
    """Merkezi hata yönetim sınıfı"""
    
    @staticmethod
    def log_error(error: Exception, context: str = "", user_friendly: bool = True):
        """Hatayı logla ve kullanıcıya göster"""
        error_msg = f"Error in {context}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        if user_friendly:
            if isinstance(error, WhisperAIError):
                try:
                    st.error(f"❌ {error.error_type}: {error.message}")
                    if error.details:
                        st.info(f"{get_text('technical_details')} {error.details}")
                except:
                    # Streamlit context olmadığında fallback
                    print(f"❌ {error.error_type}: {error.message}")
                    if error.details:
                        print(f"{get_text('technical_details')} {error.details}")
            else:
                try:
                    st.error(f"{get_text('unexpected_error')} {context}")
                    st.info(f"{get_text('error_details')} {str(error)}")
                except:
                    # Streamlit context olmadığında fallback
                    print(f"{get_text('unexpected_error')} {context}")
                    print(f"🔍 Hata Detayları: {str(error)}")
    
    @staticmethod
    def handle_api_error(error: Exception) -> str:
        """OpenAI API hatalarını özel olarak işle"""
        error_str = str(error).lower()
        
        if "401" in error_str or "unauthorized" in error_str:
            return "🔑 API anahtarınız geçersiz. Lütfen .env dosyanızı kontrol edin."
        elif "429" in error_str or "rate limit" in error_str:
            return "⏰ API kullanım limiti aşıldı. Lütfen bir süre bekleyin."
        elif "403" in error_str or "forbidden" in error_str:
            return "🚫 Bu API anahtarıyla erişim izniz yok."
        elif "timeout" in error_str:
            return "⏱️ İstek zaman aşımına uğradı. Lütfen tekrar deneyin."
        elif "network" in error_str or "connection" in error_str:
            return "🌐 İnternet bağlantı sorunu. Lütfen bağlantınızı kontrol edin."
        else:
            return f"🔧 API Hatası: {str(error)}"

def error_handler(context: str = ""):
    """Fonksiyon decorator'ı ile hata yakalama"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.log_error(e, context or func.__name__)
                return None
        return wrapper
    return decorator

@contextmanager
def safe_operation(operation_name: str):
    """Context manager ile güvenli operasyon"""
    try:
        logger.info(f"Starting operation: {operation_name}")
        yield
        logger.info(f"Completed operation: {operation_name}")
    except Exception as e:
        ErrorHandler.log_error(e, operation_name)
        raise

# =============================================
# 🌐 REAL-TIME PROGRESS SYSTEM (Streamlit Compatible)
# =============================================

class RealTimeProgressManager:
    """Streamlit uyumlu progress tracking sistemi"""
    
    def __init__(self):
        self.progress_callbacks = defaultdict(list)
        
    def start_websocket_server(self):
        """WebSocket server devre dışı - Streamlit session state kullanılıyor"""
        pass
            
    def register_callback(self, session_id: str, callback: Callable):
        """Progress callback kaydı"""
        self.progress_callbacks[session_id].append(callback)
        
    def update_progress(self, session_id: str, message: str, percent: float, metadata: Optional[Dict] = None):
        """Streamlit progress güncelleme"""
        progress_data = {
            "message": message,
            "percent": percent,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        # Streamlit session state'e progress kaydet
        if 'progress_data' not in st.session_state:
            st.session_state.progress_data = {}
        st.session_state.progress_data[session_id] = progress_data
        
        # Local callbacks'i çağır
        for callback in self.progress_callbacks.get(session_id, []):
            try:
                callback(message, percent)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def cleanup_session(self, session_id: str):
        """Session temizleme"""
        if session_id in self.progress_callbacks:
            del self.progress_callbacks[session_id]
        if 'progress_data' in st.session_state and session_id in st.session_state.progress_data:
            del st.session_state.progress_data[session_id]

# =============================================
# ⚡ API RATE LIMITING SYSTEM
# =============================================

class APIRateLimiter:
    """API rate limiting ve token yönetimi"""
    
    def __init__(self, 
                 requests_per_minute: int = 50,
                 tokens_per_minute: int = 90000,
                 requests_per_day: int = 1000):
        
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.requests_per_day = requests_per_day
        
        # Tracking
        self.minute_requests = []
        self.minute_tokens = []
        self.daily_requests = []
        
        # Locks
        self.request_lock = threading.Lock()
        self.token_lock = threading.Lock()
        
    def can_make_request(self, estimated_tokens: int = 1000) -> Tuple[bool, str]:
        """Request yapılabilir mi kontrol et"""
        
        current_time = time.time()
        
        with self.request_lock:
            # Eski kayıtları temizle (1 dakika)
            minute_ago = current_time - 60
            self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
            self.minute_tokens = [t for t in self.minute_tokens if t['time'] > minute_ago]
            
            # Günlük kayıtları temizle (24 saat)
            day_ago = current_time - 86400
            self.daily_requests = [t for t in self.daily_requests if t > day_ago]
            
            # Rate limit kontrolleri
            if len(self.minute_requests) >= self.requests_per_minute:
                wait_time = 60 - (current_time - min(self.minute_requests))
                return False, f"Request limit aşıldı. {wait_time:.1f} saniye bekleyin."
            
            if len(self.daily_requests) >= self.requests_per_day:
                return False, "Günlük request limiti aşıldı."
            
            # Token kontrolü
            current_minute_tokens = sum(t['tokens'] for t in self.minute_tokens)
            if current_minute_tokens + estimated_tokens > self.tokens_per_minute:
                wait_time = 60 - (current_time - min(t['time'] for t in self.minute_tokens))
                return False, f"Token limit aşıldı. {wait_time:.1f} saniye bekleyin."
            
            return True, "OK"
    
    def record_request(self, actual_tokens: int = 1000):
        """Request kaydını tut"""
        
        current_time = time.time()
        
        with self.request_lock:
            self.minute_requests.append(current_time)
            self.minute_tokens.append({
                'time': current_time,
                'tokens': actual_tokens
            })
            self.daily_requests.append(current_time)
    
    def get_usage_stats(self) -> Dict:
        """Kullanım istatistikleri"""
        
        current_time = time.time()
        minute_ago = current_time - 60
        day_ago = current_time - 86400
        
        # Temizle
        self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
        self.minute_tokens = [t for t in self.minute_tokens if t['time'] > minute_ago]
        self.daily_requests = [t for t in self.daily_requests if t > day_ago]
        
        current_minute_tokens = sum(t['tokens'] for t in self.minute_tokens)
        
        return {
            'requests_this_minute': len(self.minute_requests),
            'requests_per_minute_limit': self.requests_per_minute,
            'tokens_this_minute': current_minute_tokens,
            'tokens_per_minute_limit': self.tokens_per_minute,
            'requests_today': len(self.daily_requests),
            'requests_per_day_limit': self.requests_per_day,
            'minute_usage_percent': (len(self.minute_requests) / self.requests_per_minute) * 100,
            'token_usage_percent': (current_minute_tokens / self.tokens_per_minute) * 100,
            'daily_usage_percent': (len(self.daily_requests) / self.requests_per_day) * 100
        }
    
    @contextmanager
    def rate_limited_request(self, estimated_tokens: int = 1000):
        """Rate limiting context manager"""
        
        can_proceed, message = self.can_make_request(estimated_tokens)
        
        if not can_proceed:
            raise Exception(f"Rate limit exceeded: {message}")
        
        start_time = time.time()
        
        try:
            yield
        finally:
            # İşlem sonrası gerçek token kullanımını kaydet
            processing_time = time.time() - start_time
            # Token tahmini (basit formula)
            actual_tokens = max(estimated_tokens, int(processing_time * 100))
            self.record_request(actual_tokens)

# =============================================
# 🛡️ ERROR HANDLING & LOGGING SYSTEM
# =============================================

# Logging konfigürasyonu - UTF-8 encoding ile ve safer handlers
try:
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('whisper_ai.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler with UTF-8 safe formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
except Exception as e:
    # Fallback to basic logging if there's an issue
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning(f"Logging setup warning: {e}")

# =============================================
# 🔐 SECURE API & DATABASE CONNECTION
# =============================================

# Client'ı güvenli şekilde başlat
try:
    client = initialize_openai_client()
except Exception as e:
    st.error(f"{get_text('openai_client_error')} {str(e)}")
    st.stop()

# =============================================
# 🗄️ SECURE DATABASE MANAGEMENT
# =============================================

# Export işlemleri tamamen export_utils.py modülünden gerçekleştirilir

# =============================================
# 🚀 ENHANCED TRANSCRIPTION WITH CHUNKING
# =============================================

class TranscriptionProcessor:
    """Gelişmiş transkripsiyon işlemcisi"""
    
    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.retry_count = 0
        self.max_retries = config['max_retries']
    
    @error_handler("transcription_process")
    def process_audio_file(self, file_bytes: bytes, file_name: str, language: Optional[str] = None,
                          response_format: str = "text", progress_callback=None) -> dict:
        """Ana transkripsiyon işlemi - chunking destekli"""
        
        start_time = time.time()
        
        # Dosya güvenlik kontrolü
        is_safe, security_msg = SecurityManager.validate_file_security(file_bytes, file_name)
        if not is_safe:
            raise WhisperAIError(security_msg, "SECURITY_ERROR")
        
        # Dosya boyutunu kontrol et
        file_size_mb = len(file_bytes) / (1024 * 1024)
        
        if progress_callback:
            progress_callback("🔍 Dosya analiz ediliyor...", 10)
        
        # Dosya büyükse chunk'lara böl
        if FileChunker.should_chunk_file(file_size_mb, threshold_mb=ADVANCED_CONFIG['max_file_size_mb']):
            return self._process_large_file(file_bytes, file_name, language, response_format, progress_callback)
        else:
            return self._process_single_file(file_bytes, file_name, language, response_format, progress_callback)
    
    def _process_single_file(self, file_bytes: bytes, file_name: str, language: Optional[str], 
                           response_format: str, progress_callback) -> dict:
        """Tek dosya işlemi"""
        
        start_time = time.time()
        temp_path = None  # Initialize temp_path
        
        if progress_callback:
            progress_callback("📤 Whisper API'ya gönderiliyor...", 30)
        
        try:
            # Geçici dosya oluştur
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp_file:
                tmp_file.write(file_bytes)
                temp_path = tmp_file.name
            
            if progress_callback:
                progress_callback("🧠 Transkripsiyon işleniyor...", 60)
            
            # API çağrısı
            with open(temp_path, "rb") as audio_file:
                transcript = self._call_whisper_api(audio_file, language, response_format)
            
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Silme işlemi başarısız olursa devam et
            
            if progress_callback:
                progress_callback("✅ İşlem tamamlandı!", 100)
            
            processing_time = time.time() - start_time
            
            return {
                'transcript': transcript,
                'chunk_count': 1,
                'processing_time': processing_time,
                'file_size_mb': len(file_bytes) / (1024 * 1024)
            }
            
        except Exception as e:
            # Hata durumunda geçici dosyayı temizlemeye çalış
            try:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
            except OSError:
                pass
            raise e
    
    def _process_large_file(self, file_bytes: bytes, file_name: str, language: Optional[str], 
                          response_format: str, progress_callback) -> dict:
        """Büyük dosya chunk'lı işlemi"""
        
        start_time = time.time()
        
        if progress_callback:
            progress_callback("✂️ Dosya parçalara bölünüyor...", 20)
        
        # Dosyayı chunk'lara böl
        chunks = FileChunker.chunk_audio_file(file_bytes, file_name, ADVANCED_CONFIG['chunk_duration_seconds'])
        
        if progress_callback:
            progress_callback(f"📦 {len(chunks)} parça oluşturuldu", 25)
        
        transcripts = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            temp_path = None  # Initialize temp_path for each chunk
            try:
                if progress_callback:
                    progress = 25 + (i / total_chunks) * 60
                    progress_callback(f"🔄 Parça {i+1}/{total_chunks} işleniyor...", progress)
                
                # Chunk'ı geçici dosyaya kaydet
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(chunk['data'])
                    temp_path = tmp_file.name
                
                # API çağrısı
                with open(temp_path, "rb") as audio_file:
                    chunk_transcript = self._call_whisper_api(audio_file, language, response_format)
                
                transcripts.append({
                    'text': chunk_transcript,
                    'start_time': chunk['start_time'],
                    'end_time': chunk['end_time'],
                    'duration': chunk['duration']
                })
                
                # Geçici dosyayı temizle
                os.unlink(temp_path)
                
                # Bellek temizliği
                if i % 3 == 0:  # Her 3 chunk'ta bir
                    gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                continue
        
        if progress_callback:
            progress_callback("🔗 Parçalar birleştiriliyor...", 90)
        
        # Transkriptleri birleştir
        if response_format == "text":
            full_transcript = " ".join([t['text'] for t in transcripts])
        else:
            # SRT/VTT için timestamp'leri ayarla
            full_transcript = self._merge_timestamped_transcripts(transcripts, response_format)
        
        processing_time = time.time() - start_time
        
        return {
            'transcript': full_transcript,
            'chunk_count': len(chunks),
            'processing_time': processing_time,
            'file_size_mb': len(file_bytes) / (1024 * 1024),
            'chunks_processed': len(transcripts)
        }
    
    def _call_whisper_api(self, audio_file, language: Optional[str], response_format: str, retry_count: int = 0):
        """Whisper API çağrısı - retry logic ve rate limiting ile"""
        
        # Dosya boyutuna göre token tahmini
        current_pos = audio_file.tell()
        audio_file.seek(0, 2)  # Dosya sonuna git
        file_size_mb = audio_file.tell() / (1024 * 1024)
        audio_file.seek(current_pos)  # Önceki pozisyona dön
        
        estimated_tokens = int(file_size_mb * 1000)  # Basit tahmin
        
        try:
            # Direct API call without rate limiting
            if language:
                return self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format=response_format,
                    language=language,
                    timeout=ADVANCED_CONFIG['api_timeout_seconds']
                )
            else:
                return self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format=response_format,
                    timeout=ADVANCED_CONFIG['api_timeout_seconds']
                )
        
        except Exception as e:
            error_message = str(e)
            
            # Rate limiting hatası
            if "Rate limit" in error_message or "rate_limit_exceeded" in error_message:
                logger.warning(f"Rate limit hit, waiting...")
                time.sleep(5)  # 5 saniye bekle
                if retry_count < 3:
                    return self._call_whisper_api(audio_file, language, response_format, retry_count + 1)
                else:
                    raise WhisperAIError(f"Rate limit exceeded after retries: {error_message}", "RATE_LIMIT")
            
            # Genel retry logic
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * 1  # Exponential backoff
                logger.warning(f"API call failed, retrying in {wait_time}s... (attempt {retry_count + 1})")
                time.sleep(wait_time)
                return self._call_whisper_api(audio_file, language, response_format, retry_count + 1)
            else:
                error_msg = ErrorHandler.handle_api_error(e)
                raise WhisperAIError(error_msg, "API_ERROR", str(e))
    
    def _merge_timestamped_transcripts(self, transcripts: list, format_type: str) -> str:
        """Timestamp'li transkriptleri birleştir"""
        if format_type == "srt":
            result = ""
            for i, transcript in enumerate(transcripts, 1):
                start_time = self._seconds_to_srt_time(transcript['start_time'])
                end_time = self._seconds_to_srt_time(transcript['end_time'])
                result += f"{i}\n{start_time} --> {end_time}\n{transcript['text']}\n\n"
            return result
        
        elif format_type == "vtt":
            result = "WEBVTT\n\n"
            for transcript in transcripts:
                start_time = self._seconds_to_vtt_time(transcript['start_time'])
                end_time = self._seconds_to_vtt_time(transcript['end_time'])
                result += f"{start_time} --> {end_time}\n{transcript['text']}\n\n"
            return result
        
        return " ".join([t['text'] for t in transcripts])
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Saniyeyi SRT zaman formatına çevir"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _seconds_to_vtt_time(self, seconds: float) -> str:
        """Saniyeyi VTT zaman formatına çevir"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

# Global transcription processor
# Global transcription processor - artık utils.py'de
transcription_processor = TranscriptionProcessor(client, ADVANCED_CONFIG)

# =============================================
# 📤 BASIT EXPORT FONKSİYONLARI (Export Utils Olmadan)
# =============================================

def check_dependencies():
    """Export bağımlılıklarını kontrol et"""
    try:
        import reportlab  # type: ignore
        pdf_available = True
    except ImportError:
        pdf_available = False
    
    try:
        import docx  # type: ignore
        word_available = True
    except ImportError:
        word_available = False
    
    try:
        import pandas as pd
        excel_available = True
    except ImportError:
        excel_available = False
    
    try:
        import qrcode  # type: ignore
        qr_available = True
    except ImportError:
        qr_available = False
    
    return {
        'pdf': pdf_available,
        'word': word_available,
        'excel': excel_available,
        'qr': qr_available
    }

def get_available_export_types():
    """Mevcut export türlerini listele"""
    deps = check_dependencies()
    return [
        {'name': 'PDF', 'available': deps['pdf']},
        {'name': 'Word', 'available': deps['word']},
        {'name': 'Excel', 'available': deps['excel']},
        {'name': 'QR', 'available': deps['qr']},
        {'name': 'ZIP', 'available': True}
    ]


# Export sınıfları artık export_utils.py'de

# Ses analizi fonksiyonları artık utils.py'de
# AI analiz fonksiyonları
# AI analiz fonksiyonları artık utils.py'de

def main():
    """Ana uygulama fonksiyonu"""
    
    # Uygulama başlangıcında bellek monitoring ve temizlik
    if 'app_initialized' not in st.session_state:
        # İlk başlatma temizliği
        MemoryManager.cleanup_session_state(force_cleanup=True)
        TempFileManager.cleanup_session_temp_files()
        st.session_state.app_initialized = True
        logger.info("Application initialized with memory cleanup")

    # Periyodik bellek kontrolü
    if 'last_memory_check' not in st.session_state:
        st.session_state.last_memory_check = time.time()

    # Her 5 dakikada bir bellek kontrolü
    current_time = time.time()
    if current_time - st.session_state.last_memory_check > 300:  # 5 dakika
        memory_info = MemoryManager.get_memory_usage()
        if isinstance(memory_info, dict) and 'error' not in memory_info:
            percent = memory_info.get('percent', 0)
            if isinstance(percent, (int, float)) and percent > 80:  # %80'den fazla bellek kullanımı
                logger.warning(f"High memory usage detected: {memory_info}")
                MemoryManager.auto_cleanup_large_files(force=True)
        
        st.session_state.last_memory_check = current_time

# Session state temizlik fonksiyonu - hafıza yönetimi - DEPRECATED
def cleanup_session_state():
    """Legacy function - use MemoryManager instead"""
    return MemoryManager.cleanup_session_state()
    
    # Her 50 işlemde bir temizlik yap
    if st.session_state.cleanup_counter > 50:
        keys_to_remove = []
        for key in st.session_state.keys():
            # Geçici processing flaglerini temizle
            if any(key.endswith(suffix) for suffix in ['_processing', '_updating', '_changing', '_saving_state']):
                keys_to_remove.append(key)
            # Eski dosya verilerini temizle (100'den fazla varsa)
            elif isinstance(key, str) and key.startswith('file_data_') and len([k for k in st.session_state.keys() if isinstance(k, str) and k.startswith('file_data_')]) > 10:
                try:
                    file_index = int(key.split('_')[-1])
                    if file_index < st.session_state.cleanup_counter - 10:
                        keys_to_remove.append(key)
                except:
                    pass
        
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.cleanup_counter = 0

# Cleanup çağrısı - moved to main function
# cleanup_session_state()

# Export state temizleme fonksiyonu
def cleanup_export_states(file_index=None):
    """Export state verilerini temizle - bellek optimizasyonu"""
    export_prefixes = [
        'pdf_ready_', 'pdf_data_', 'word_ready_', 'word_data_',
        'zip_ready_', 'zip_data_', 'qr_ready_', 'qr_data_',
        'excel_ready_', 'excel_data_', 'basic_pdf_ready_', 'basic_pdf_data_',
        'basic_word_ready_', 'basic_word_data_'
    ]
    
    keys_to_remove = []
    
    if file_index is not None:
        # Belirli bir dosya için temizle
        for prefix in export_prefixes:
            key = f"{prefix}{file_index}"
            if key in st.session_state:
                keys_to_remove.append(key)
    else:
        # Tüm export verilerini temizle
        for key in st.session_state.keys():
            if isinstance(key, str) and any(key.startswith(prefix) for prefix in export_prefixes):
                keys_to_remove.append(key)
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    
    if keys_to_remove:
        logger.info(f"Cleaned {len(keys_to_remove)} export state keys")
    
    return len(keys_to_remove)

# CSS stilleri
st.markdown("""
<style>
    /* Ana tema renkleri - Dark tema sabit */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Main header */
    .main-header {
        text-align: center;
        color: #fafafa;
        font-size: 2.5rem;
        font-weight: 300;
        margin: 2rem 0;
        letter-spacing: 2px;
    }
    
    /* Upload area */
    .upload-container {
        background: #1a1d23;
        border: 2px dashed #4a90e2;
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        margin: 2rem 0;
        transition: all 0.3s ease;
    }
    
    .upload-container:hover {
        border-color: #f59e0b;
        background: #2d3748;
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    /* Result container */
    .result-container {
        background: #1a1d23;
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid #2d3748;
    }
    
    /* Sidebar width - 550px sabit genişlik */
    .stSidebar > div:first-child {
        width: 550px !important;
        min-width: 550px;
    }
    
    /* Sidebar içeriği için padding ve scroll */
    .stSidebar .block-container {
        padding-top: 1rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-height: 100vh;
        overflow-y: auto;
    }
    
    /* Ana içerik alanını tam genişlikte ayarla */
    .main .block-container {
        margin-left: 0;
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Sidebar içindeki elementler için tam genişlik kullanımı */
    .stSidebar .element-container {
        max-width: 100%;
    }
    
    /* Selectbox ve form elementleri için genişlik optimizasyonu */
    .stSidebar .stSelectbox > div > div,
    .stSidebar .stNumberInput > div > div,
    .stSidebar .stSlider > div {
        max-width: 100%;
    }
    
    /* Sidebar expander'ları için genişlik kontrolü */
    .stSidebar .streamlit-expanderHeader {
        max-width: 100%;
        word-wrap: break-word;
    }
    
    /* Sidebar içindeki butonlar */
    .stSidebar .stButton > button {
        width: 100%;
        padding: 0.5rem 1rem;
        text-align: center;
    }
    
    /* Sidebar içindeki checkbox ve diğer elementler */
    .stSidebar .stCheckbox, 
    .stSidebar .stSlider,
    .stSidebar .stNumberInput,
    .stSidebar .stTextInput {
        max-width: 100%;
    }
    
    /* Column layout'lar için genişlik */
    .stSidebar .row-widget {
        width: 100%;
    }
    
    /* İki kolonlu düzenler için */
    .stSidebar .element-container [data-testid="column"] {
        width: 48% !important;
        margin-right: 4%;
    }
    
    .stSidebar .element-container [data-testid="column"]:last-child {
        margin-right: 0;
    }
</style>
""", unsafe_allow_html=True)

st.image("assets/echoforge.jpg", width=2000, use_container_width=True)

# Akademik Abstract - Expander içinde - multilingual
with st.expander(get_text("abstract") or "Abstract", expanded=False):
    # Abstract metni de çok dilli hale getir
    if get_current_language() == "en":
        abstract_text = """
        <div style="text-align: justify; line-height: 1.7; font-size: 0.95rem; color: #e2e8f0;">
            This study develops an advanced audio transcription and analysis system based on OpenAI's state-of-the-art Whisper-1 transformer model. The system supports audio data processing architecture with multi-modal audio data, supporting file sizes up to 25MB in MP3, WAV, M4A, MP4, and MPEG4 formats, providing automatic speech recognition (ASR), multilingual transcription, and deep learning-based text analysis capabilities. At the core of the application are adaptive chunking algorithms and memory optimization strategies, utilizing dynamic segmentation techniques for processing large audio files. The real-time progress tracking system provides asynchronous process monitoring with WebSocket protocol and Streamlit session state management, while comprehensive error handling mechanisms create a reliable user experience with HTTP status codes, API rate limiting, and exponential backoff strategies. The platform includes a YouTube video transcription module, integrating multi-download strategies with yt-dlp library, adaptive bitrate selection, and rate limiting protection. The system architecture includes persistent data storage with SQLite database, SHA-256 algorithm for file hashing, and input validation layers for security. Within the Natural Language Processing (NLP) scope, it features 12-language translation support with GPT-4 Turbo, GPT-4o, and GPT-3.5-turbo models (transformer-based neural machine translation), sentiment analysis (VADER and TextBlob algorithms), keyword extraction (TF-IDF and RAKE methodologies), text summarization (extractive and abstractive methods), and speech rate analysis features. The export module supports various output formats using ReportLab for PDF generation, python-docx for Word document creation, openpyxl for Excel spreadsheet formatting, and qrcode library for QR code generation. The system has responsive UI/UX design with modern web framework Streamlit, creating a comprehensive platform for academic research, professional transcription services, multilingual content analysis, and enterprise-level applications with real-time audio visualization, waveform plotting (matplotlib/plotly), memory management optimizations, concurrent processing capabilities, session state persistence, and cross-platform compatibility features.
        </div>
        """
    else:
        abstract_text = """
        <div style="text-align: justify; line-height: 1.7; font-size: 0.95rem; color: #e2e8f0;">
            Bu çalışma, OpenAI'nin state-of-the-art Whisper-1 transformer modelini temel alan ileri düzey bir ses transkripsiyon ve analiz sistemi geliştirmektedir. Sistem, çok modalı ses verisi işleme mimarisi ile MP3, WAV, M4A, MP4 ve MPEG4 formatlarında 25MB'a kadar dosya boyutlarını destekleyerek, otomatik konuşma tanıma (ASR), çok dilli transkripsiyon ve derin öğrenme tabanlı metin analizi yetenekleri sunmaktadır. Uygulamanın çekirdeğinde, adaptif chunking algoritmaları ve bellek optimizasyonu stratejileri bulunmakta olup, büyük ses dosyalarının işlenmesi için dinamik segmentasyon teknikleri kullanılmaktadır. Real-time progress tracking sistemi, WebSocket protokolü ve Streamlit session state management ile asenkron işlem takibi sağlarken, comprehensive error handling mekanizmaları HTTP status kodları, API rate limiting ve exponential backoff stratejileri ile güvenilir kullanıcı deneyimi oluşturmaktadır. Platform, YouTube video transkripsiyon modülünü içermekte olup, yt-dlp kütüphanesi ile çoklu indirme stratejileri, adaptive bitrate selection ve rate limiting koruması entegre edilmiştir. Sistem mimarisi, SQLite veritabanı ile persistent data storage, file hashing için SHA-256 algoritması ve güvenlik için input validation katmanları içermektedir. Natural Language Processing (NLP) kapsamında, GPT-4 Turbo, GPT-4o ve GPT-3.5-turbo modelleri ile 12 dilli çeviri desteği (transformer-based neural machine translation), sentiment analysis (VADER ve TextBlob algoritmaları), keyword extraction (TF-IDF ve RAKE metodolojileri), text summarization (extractive ve abstractive yöntemler) ve speech rate analysis özellikleri bulunmaktadır. Export modülü, ReportLab ile PDF generation, python-docx ile Word document creation, openpyxl ile Excel spreadsheet formatting ve QR code generation için qrcode kütüphanesi kullanarak çeşitli output formatları desteklemektedir. Sistem, modern web framework Streamlit ile responsive UI/UX tasarımına sahip olup, real-time audio visualization, waveform plotting (matplotlib/plotly), memory management optimizations, concurrent processing capabilities, session state persistence ve cross-platform compatibility özellikleri ile akademik araştırma, profesyonel transkripsiyon hizmetleri, çok dilli içerik analizi ve enterprise-level applications için kapsamlı bir platform oluşturmaktadır.
        </div>
        """
    
    st.markdown(abstract_text, unsafe_allow_html=True)

# Minimal sidebar - gelişmiş tasarım
with st.sidebar:
    # GIF Logo
    st.image("assets/echo.gif", use_container_width=True)
    
    # Language Selector - En üstte - Fixed version
    st.markdown("---")
    st.markdown("### 🌍 Language / Dil")
    
    # Initialize session state for language if not exists
    if 'current_language' not in st.session_state:
        st.session_state.current_language = "tr"
    
    current_lang = st.session_state.get('current_language', 'tr')
    
    language_col1, language_col2 = st.columns([3, 1])
    with language_col1:
        selected_ui_language = st.selectbox(
            "Interface Language:",
            options=get_available_languages(),
            format_func=get_language_name,
            index=get_available_languages().index(current_lang),
            key="ui_language_selector",
            label_visibility="collapsed"  # Hide label to prevent empty label warning
        )
    
    with language_col2:
        if st.button("Apply", help="Apply language change", key="apply_language", type="primary"):
            if set_language(selected_ui_language):
                st.success("✅")
                st.rerun()
    
    # Auto-update language if different
    if selected_ui_language != current_lang:
        set_language(selected_ui_language)
        st.rerun()
    
    # Alt başlık - multilingual
    st.markdown(f"""
    <div style="text-align: center; padding: 0.5rem 0; border-bottom: 2px solid #4a90e2; margin-bottom: 1.5rem;">
        <p style="margin: 0; color: #cccccc; font-size: 0.9rem;">{get_text("description") or "Whisper AI Transcription"}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # API Durum Kontrolü - multilingual
    with st.expander(get_text("api_status") or "API Status", expanded=True):
        try:
            models = client.models.list()
            st.success(get_text("api_success") or "API Connection Successful")
        except Exception as e:
            st.error(get_text("api_error") or "API Connection Error")
            st.error(f"🔧 {get_text('api_error') or 'Error'}: {str(e)}")
              
    # Dil ve Format Ayarları - multilingual
    with st.expander(get_text("language_format") or "Language & Format", expanded=True):
        # İki kolonlu düzen - 600px'de uygun - multilingual
        lang_col1, lang_col2 = st.columns(2)
        with lang_col1:
            selected_language = st.selectbox(
                get_text("transcription_language") or "Transcription Language",
                options=list(LANGUAGES.keys()),
                index=0,
                help=get_text("transcription_language_help") or "Select language for transcription"
            )
            
            language_code = LANGUAGES[selected_language]
        
        with lang_col2:
            response_format = st.selectbox(
                get_text("output_format") or "Output Format",
                RESPONSE_FORMATS,
                index=0,
                help=get_text("output_format_help") or "Select output format"
            )
        
        # Gelişmiş ayarlar - iki kolon - multilingual
        st.markdown(f"##### {get_text('advanced_settings') or 'Advanced Settings'}")
        adv_col1, adv_col2 = st.columns(2)
        with adv_col1:
            temperature = st.slider(get_text("temperature") or "Temperature", 0.0, 1.0, 0.0, 0.1)
        with adv_col2:
            max_tokens = st.number_input(get_text("max_tokens") or "Max Tokens", 100, 4000, 1000, 100)
    
    # AI Analiz Seçenekleri - multilingual
    with st.expander(get_text("ai_analysis") or "AI Analysis", expanded=True):
        enable_ai_analysis = st.checkbox(
            get_text("enable_ai_analysis") or "Enable AI Analysis", 
            value=True,
            help=get_text("ai_analysis_help") or "Enable detailed AI analysis"
        )
        
        if enable_ai_analysis:
            st.markdown(f"##### {get_text('analysis_types')}")
            
            # İki kolonlu grid layout - 600px'de uygun
            analysis_col1, analysis_col2 = st.columns(2)
            
            with analysis_col1:
                summary_enabled = st.checkbox(get_text("summary_analysis") or "Summary Analysis", value=True)
                keywords_enabled = st.checkbox(get_text("keywords_analysis") or "Keywords Analysis", value=True)
            
            with analysis_col2:
                speed_enabled = st.checkbox(get_text("speech_speed") or "Speech Speed", value=True)
                emotion_enabled = st.checkbox(get_text("emotion_analysis") or "Emotion Analysis", value=True)
            
            # AI model seçimi
            ai_model = st.selectbox(
                "🤖 AI Model:",
                ["gpt-4-turbo", "gpt-4o", "gpt-4", "gpt-3.5-turbo"],
                index=0,
                help="Analiz için kullanılacak AI model"
            )
            
            # Analiz detay seviyesi
            analysis_depth = st.select_slider(
                get_text("analysis_depth_label") or "Analysis Depth",
                options=[
                    get_text("analysis_depth_basic") or "Basic", 
                    get_text("analysis_depth_medium") or "Medium", 
                    get_text("analysis_depth_detailed") or "Detailed", 
                    get_text("analysis_depth_comprehensive") or "Comprehensive"
                ],
                value=get_text("analysis_depth_medium") or "Medium"
            )
            
            ai_features = []
            if summary_enabled: ai_features.append("📝 Özetleme")
            if keywords_enabled: ai_features.append("🔑 Anahtar Kelimeler")
            if speed_enabled: ai_features.append("⚡ Konuşma Hızı")
            if emotion_enabled: ai_features.append("💭 Duygusal Analiz")
        else:
            ai_features = []
            ai_model = "gpt-4-turbo"
            analysis_depth = get_text("analysis_depth_medium")
            temperature = 0.0
            max_tokens = 1000
    
    # Görünüm ve Navigasyon
    with st.expander(f"👁️ {get_text('view_navigation')}", expanded=True):
        view_mode = st.selectbox(
            f"📂 {get_text('active_view')}",
            get_view_modes(),
            index=0,
            help=get_text("select_main_screen_view")
        )
        
        # Hızlı eylemler - üç kolon düzeni
        st.markdown(f"##### {get_text('quick_actions_title')}")
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        
        with quick_col1:
            if st.button("🔄 " + (get_text("refresh_help") or "Refresh"), help=get_text("refresh_help") or "Refresh page", use_container_width=True, key="refresh_btn"):
                # Soft refresh - sadece cache temizle
                st.cache_data.clear()
                st.success(get_text("page_refreshed_msg") or "Page refreshed")
        
        with quick_col2:
            if st.button("🗑️ " + (get_text("clear_help") or "Clear"), help=get_text("clear_help") or "Clear data", use_container_width=True, key="clear_btn"):
                # Session state temizleme - döngü önleyici
                if not st.session_state.get("clearing", False):
                    st.session_state.clearing = True
                    
                    # GÜVENLI TEMİZLEME - SADECE GEÇİCİ VERİLERİ TEMİZLE
                    keys_to_clear = []
                    preserve_keys = {
                        # Export verilerini koru
                        "export_data_", "pdf_data_", "word_data_", "zip_data_", "qr_data_", "excel_data_",
                        "pdf_ready_", "word_ready_", "zip_ready_", "qr_ready_", "excel_ready_",
                        "basic_pdf_data_", "basic_word_data_", "basic_pdf_ready_", "basic_word_ready_",
                        # Sonuç verilerini koru
                        "transcript_result_", "ai_analysis_result_", "processing_result_",
                        # UI durumlarını koru
                        "show_detail_", "selected_language_code", "response_format", "enable_ai_analysis", "ai_model"
                    }
                    
                    for key in st.session_state.keys():
                        # Sadece geçici işlem verilerini temizle
                        if isinstance(key, str) and any(key.startswith(prefix) for prefix in [
                            "temp_", "processing_", "progress_", "chunk_", "file_bytes_"
                        ]):
                            # Korunacak verileri kontrol et
                            if not any(key.startswith(preserve_prefix) for preserve_prefix in preserve_keys):
                                keys_to_clear.append(key)
                    
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    # Sadece geçici cache'i temizle
                    if keys_to_clear:
                        st.cache_data.clear()
                    
                    st.session_state.clearing = False
                    st.success(f"✅ {len(keys_to_clear)} geçici veri temizlendi - Sonuçlar korundu!")
        
        with quick_col3:
            if st.button("📤 " + (get_text("export_clean_help") or "Export Clean"), help=get_text("export_clean_help") or "Clean export data", use_container_width=True, key="export_clean_btn"):
                # Sadece export verilerini temizle
                cleaned_count = cleanup_export_states()
                if cleaned_count > 0:
                    st.success(f"✅ {cleaned_count} {get_text('export_data_cleaned') or 'export data cleaned'}")
                else:
                    st.info(get_text("no_export_data") or "No export data")
    
    # Gelişmiş Ayarlar ve Araçlar
    with st.expander(f"🔧 {get_text('advanced_settings')}", expanded=False):
        st.markdown(f"##### {get_text('data_management_title')}")
        
        data_col1, data_col2 = st.columns(2)
        with data_col1:
            if st.button(get_text("db_statistics") or "DB Statistics", use_container_width=True):
                # Veritabanı istatistikleri göster
                try:
                    stats = db_manager.get_statistics()
                    total_count = stats.get('general', {}).get('total_files', 0)
                    st.success(f"{get_text('total_records_db') or 'Total records in DB'}: {total_count}")
                except:
                    st.error(get_text("db_connection_error") or "DB connection error")
        
        with data_col2:
            if st.button(get_text("cache_clear") or "Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.success(get_text("cache_cleared") or "Cache cleared")
        
        st.markdown(f"##### {get_text('security_title') or 'Security Settings'}")
        
        security_col1, security_col2 = st.columns(2)
        with security_col1:
            auto_delete = st.checkbox(get_text("auto_delete") or "Auto Delete", value=False, help=get_text("auto_delete_help") or "Auto delete files")
        
        with security_col2:
            encryption = st.checkbox(get_text("encryption") or "Encryption", value=True, help=get_text("encryption_help") or "Enable encryption")
        
        # Debug modu
        debug_mode = st.checkbox(get_text("debug_mode") or "Debug Mode", value=False)
        if debug_mode:
            st.json({
                "language": language_code,
                "format": response_format,
                "ai_enabled": enable_ai_analysis,
                "view_mode": view_mode
            })
        
        # Bellek Monitörü
        st.markdown(f"##### {get_text('memory_status_title') or 'Memory Status'}")
        memory_col1, memory_col2 = st.columns(2)
        
        with memory_col1:
            if st.button(get_text("memory_check") or "Memory Check", use_container_width=True):
                memory_info = MemoryManager.get_memory_usage()
                if isinstance(memory_info, dict) and 'error' not in memory_info:
                    st.metric("RSS", f"{memory_info.get('rss', 0):.1f} MB")
                    st.metric("Kullanım %", f"{memory_info.get('percent', 0):.1f}%")
                else:
                    st.info(get_text("memory_info_unavailable") or "Memory info unavailable")
        
        with memory_col2:
            if st.button(get_text("memory_cleanup") or "Memory Cleanup", use_container_width=True):
                cleaned = MemoryManager.smart_cleanup_after_processing()
                st.success(f"✅ {cleaned} {get_text('memory_cleaned') or 'memory cleaned'}")
        
        # Session state istatistikleri
        session_keys = len(st.session_state.keys())
        file_data_keys = len([k for k in st.session_state.keys() if isinstance(k, str) and k.startswith('file_data_')])
        
        st.caption(f"📊 Session Keys: {session_keys} | File Data: {file_data_keys}")
        
        if file_data_keys > 5:
            warning_text = get_text("too_many_file_data")
            if warning_text:
                st.warning(warning_text.format(file_data_keys))
            else:
                st.warning(f"Too many file data entries: {file_data_keys}")
    
    # Footer bilgileri - multilingual
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0; color: #cccccc; font-size: 0.8rem;">
        <p>{get_text("footer_version")}</p>
        <p>{get_text("footer_powered")}</p>
        <p>{get_text("footer_help")}</p>
    </div>
    """, unsafe_allow_html=True)

# Ana Tab Yapısı
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    get_text("upload_files") or "Upload Files", 
    get_text("youtube_url") or "YouTube URL", 
    get_text("smart_translation") or "Smart Translation",
    get_text("history") or "History", 
    get_text("favorites") or "Favorites", 
    get_text("statistics") or "Statistics"
])

with tab1:
    # Upload tab CSS stillerini uygula
    apply_upload_tab_styles()
    
    # Sidebar'dan settings'leri session state'e koy
    st.session_state['selected_language_code'] = language_code
    st.session_state['response_format'] = response_format
    st.session_state['enable_ai_analysis'] = enable_ai_analysis
    st.session_state['ai_model'] = ai_model
    
    # Upload tab'ını render et
    render_upload_tab(client, transcription_processor)

with tab2:
    # YouTube transkripsiyon sekmesi
    render_youtube_tab()

with tab3:
    # Çeviri sekmesi
    render_translation_tab()

with tab4:
    st.markdown(get_text("history_transcriptions"))
    
    # Geçmiş kayıtları getir
    history_df = get_transcription_history()
    
    if not history_df.empty:
        st.info(f"{get_text('total_records')} {len(history_df)}")
        
        # Filtreleme seçenekleri
        col1, col2 = st.columns(2)
        with col1:
            filter_language = st.selectbox(
                get_text("language_filter") or "Language Filter",
                [get_text("all") or "All"] + list(history_df['language'].dropna().unique())
            )
        with col2:
            show_favorites_only = st.checkbox(get_text("favorites_only") or "Favorites Only")
        
        # Filtreleme uygula
        filtered_df = history_df.copy()
        if filter_language != (get_text("all") or "All"):
            filtered_df = filtered_df[filtered_df['language'] == filter_language]
        if show_favorites_only:
            filtered_df = filtered_df[filtered_df['is_favorite'] == True]
        
        # Kayıtları göster
        for index, row in filtered_df.iterrows():
            with st.expander(f"{'⭐ ' if row['is_favorite'] else ''}📄 {row['file_name']} - {row['created_at'][:16]}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"{get_text('file_size')} {row['file_size']/1024/1024:.1f} MB")
                    st.write(f"{get_text('file_duration')} {row['duration_seconds']:.0f} {get_text('seconds')}")
                
                with col2:
                    st.write(f"{get_text('file_language')} {row['language'] or get_text('automatic')}")
                    st.write(f"**ID:** {row['id']}")
                
                with col3:
                    if st.button(get_text("view_detail") or "View Detail", key=f"view_{row['id']}"):
                        st.session_state[f"show_detail_{row['id']}"] = True
                    
                    fav_text = (get_text("remove_from_favorites") or "Remove from Favorites") if row['is_favorite'] else (get_text("add_to_favorites") or "Add to Favorites")
                    if st.button(fav_text, key=f"fav_toggle_{row['id']}"):
                        if toggle_favorite(row['id']):
                            st.success("✅ Favori durumu güncellendi!")
                            # st.rerun() kaldırıldı - success mesajı gösterme yeterli
                
                # Önizleme
                st.markdown(f"**{get_text('preview')}** {row['preview']}...")
                
                # Detay gösterimi
                if st.session_state.get(f"show_detail_{row['id']}", False):
                    detail = get_transcription_by_id(row['id'])
                    if detail:
                        st.markdown("---")
                        st.markdown(f"**{get_text('full_text') or 'Full Text'}**")
                        st.text_area(get_text('full_text') or 'Full Text', detail['transcript_text'], height=200, key=f"text_{row['id']}", label_visibility="hidden")
                        
                        if detail['summary']:
                            st.markdown(f"**{get_text('ai_summary')}**")
                            st.info(detail['summary'])
                        
                        if detail['keywords']:
                            st.markdown(f"**{get_text('keywords')}**")
                            keywords = detail['keywords'].split(',')
                            keyword_html = ""
                            for kw in keywords:
                                keyword_html += f'<span style="background: #4a90e2; color: white; padding: 4px 8px; margin: 2px; border-radius: 15px; display: inline-block;">{kw.strip()}</span> '
                            st.markdown(keyword_html, unsafe_allow_html=True)
                        
                        # İndirme ve Export butonları
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.download_button(
                                get_text("download_text") or "Download Text",
                                data=detail['transcript_text'],
                                file_name=f"{detail['file_name']}_transcript.txt",
                                key=f"download_text_{row['id']}"
                            )
                        with col2:
                            if detail['summary']:
                                current_lang = get_current_language()
                                if current_lang == "en":
                                    full_report = f"""
TRANSCRIPTION REPORT
===================
File: {detail['file_name']}
Date: {detail['created_at']}
Language: {detail['language'] or 'Automatic'}

TRANSCRIPTION:
{detail['transcript_text']}

AI SUMMARY:
{detail['summary']}

KEYWORDS:
{detail['keywords']}

EMOTIONAL ANALYSIS:
{detail['emotion_analysis'] or 'Not performed'}
"""
                                else:
                                    full_report = f"""
TRANSKRIPSIYON RAPORU
====================
Dosya: {detail['file_name']}
Tarih: {detail['created_at']}
Dil: {detail['language'] or 'Otomatik'}

TRANSKRIPSIYON:
{detail['transcript_text']}

AI ÖZET:
{detail['summary']}

ANAHTAR KELİMELER:
{detail['keywords']}

DUYGUSAL ANALİZ:
{detail['emotion_analysis'] or 'Yapılmadı'}
"""
                                st.download_button(
                                    get_text("download_full_report") or "Download Full Report",
                                    data=full_report,
                                    file_name=f"{detail['file_name']}_full_report.txt",
                                    key=f"download_report_{row['id']}"
                                )

                        
                        # Silme butonu
                        if st.button(get_text("delete") or "Delete", key=f"delete_{row['id']}"):
                            if delete_transcription(row['id']):
                                st.success(get_text("record_deleted"))
                                # st.rerun() kaldırıldı - success mesajı gösterme yeterli
    else:
        st.info(get_text("no_transcriptions_yet"))

with tab5:
    st.markdown(get_text("favorite_transcriptions"))
    
    # Sadece favorileri getir
    history_df = get_transcription_history()
    
    # Check if dataframe is empty or doesn't have is_favorite column
    if history_df is None or history_df.empty or 'is_favorite' not in history_df.columns:
        st.info(get_text("no_favorites_yet"))
    else:
        favorites_df = history_df[history_df['is_favorite'] == True]
        
        if not favorites_df.empty:
            total_records_text = get_text('total_records')
            total_records_lower = total_records_text.lower() if total_records_text else "records"
            st.info(f"⭐ {len(favorites_df)} {get_text('favorites') or 'favorites'} {total_records_lower}")
            
            for index, row in favorites_df.iterrows():
                with st.expander(f"⭐ {row['file_name']} - {row['created_at'][:16]}"):
                    detail = get_transcription_by_id(row['id'])
                    if detail:
                        st.markdown(f"**{get_text('full_text') or 'Full Text'}**")
                        st.text_area(get_text('full_text') or 'Full Text', detail['transcript_text'], height=150, key=f"fav_text_{row['id']}", label_visibility="hidden")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if st.button(get_text("remove_from_favorites") or "Remove from Favorites", key=f"unfav_{row['id']}"):
                                if toggle_favorite(row['id']):
                                    st.success("✅ " + (get_text("removed_from_favorites") or "Removed from favorites"))
                                    # st.rerun() kaldırıldı - success mesajı gösterme yeterli
                        with col2:
                            st.download_button(
                                get_text("download_text") or "Download Text",
                                data=detail['transcript_text'],
                                file_name=f"{detail['file_name']}_favorite.txt",
                                key=f"download_fav_{row['id']}"
                            )
        else:
            st.info(get_text("no_favorites_added"))

with tab6:
    # Gelişmiş istatistikler başlığı
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <h1 style="color: #4a90e2; font-size: 2.5rem; margin-bottom: 0.5rem;">📊 {get_text('advanced_statistics_dashboard')}</h1>
        <p style="color: #888; font-size: 1.1rem;">{get_text('detailed_usage_analytics')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Veritabanından kapsamlı istatistikler al
    with st.spinner(get_text("calculating_statistics") or "Calculating statistics..."):
        try:
            # Ana veri kaynakları
            history_df = get_transcription_history()
            db_stats = db_manager.get_statistics()
            
            if not history_df.empty:
                # ===== ANA METRİKLER =====
                st.markdown("### 🎯 Ana Performans Metrikleri")
                
                # 6 kolonlu metrik layout
                metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
                
                with metric_col1:
                    total_files = len(history_df)
                    st.metric("📁 Toplam Dosya", total_files, 
                             delta=f"+{total_files - db_stats.get('general', {}).get('total_files', total_files)}" if db_stats.get('general') else None)
                
                with metric_col2:
                    total_size_mb = history_df['file_size'].sum() / (1024 * 1024)
                    st.metric("💾 Toplam Boyut", f"{total_size_mb:.1f} MB")
                
                with metric_col3:
                    total_duration_min = history_df['duration_seconds'].sum() / 60
                    st.metric("⏱️ Toplam Süre", f"{total_duration_min:.1f} dk")
                
                with metric_col4:
                    favorites_count = len(history_df[history_df['is_favorite'] == True])
                    st.metric("⭐ Favoriler", favorites_count, 
                             delta=f"{(favorites_count/total_files*100):.1f}%" if total_files > 0 else None)
                
                with metric_col5:
                    avg_confidence = db_stats.get('quality', {}).get('avg_confidence', 0)
                    confidence_display = f"{avg_confidence:.1%}" if avg_confidence and avg_confidence > 0 else "N/A"
                    st.metric("🎯 Ortalama Güven", confidence_display)
                
                with metric_col6:
                    total_cost = db_stats.get('general', {}).get('total_cost', 0)
                    cost_display = f"${total_cost:.2f}" if total_cost else "$0.00"
                    st.metric("💰 Toplam Maliyet", cost_display)
                
                # ===== TREND ANALİZİ =====
                st.markdown("### 📈 Trend Analizi")
                
                trend_col1, trend_col2 = st.columns(2)
                
                with trend_col1:
                    st.markdown("#### 📅 Günlük Aktivite")
                    # Günlük trend grafiği
                    history_df['created_at'] = pd.to_datetime(history_df['created_at'])
                    daily_counts = history_df.set_index('created_at').resample('D').size().tail(30)
                    
                    if len(daily_counts) > 0:
                        if go is not None:
                            fig_daily = go.Figure()
                            fig_daily.add_trace(go.Scatter(
                                x=daily_counts.index,
                                y=daily_counts.values,
                                mode='lines+markers',
                                line=dict(color='#4a90e2', width=3),
                                marker=dict(size=6),
                                fill='tonexty',
                                fillcolor='rgba(74, 144, 226, 0.1)'
                            ))
                            fig_daily.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                height=300,
                                showlegend=False,
                                xaxis_title="Tarih",
                                yaxis_title="İşlem Sayısı"
                            )
                            st.plotly_chart(fig_daily, use_container_width=True, key="stats_daily_chart")
                        else:
                            # Plotly yoksa basit chart
                            st.line_chart(daily_counts)
                    else:
                        st.info("Henüz yeterli veri yok")
                
                with trend_col2:
                    st.markdown("#### ⏰ Saatlik Dağılım")
                    # Saatlik kullanım dağılımı
                    history_df['hour'] = history_df['created_at'].dt.hour
                    hourly_counts = history_df['hour'].value_counts().sort_index()
                    
                    if len(hourly_counts) > 0:
                        if go is not None:
                            fig_hourly = go.Figure()
                            fig_hourly.add_trace(go.Bar(
                                x=hourly_counts.index,
                                y=hourly_counts.values,
                                marker_color='#f59e0b',
                                opacity=0.8
                            ))
                            fig_hourly.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                height=300,
                                xaxis_title="Saat",
                                yaxis_title="İşlem Sayısı",
                                xaxis=dict(tickmode='linear', tick0=0, dtick=2)
                            )
                            st.plotly_chart(fig_hourly, use_container_width=True, key="stats_hourly_chart")
                        else:
                            # Plotly yoksa basit chart
                            st.bar_chart(hourly_counts)
                    else:
                        st.info("Henüz yeterli veri yok")
                
                # ===== DİL VE FORMAT ANALİZİ =====
                st.markdown("### 🌍 Dil ve Format Analizi")
                
                format_col1, format_col2, format_col3 = st.columns(3)
                
                with format_col1:
                    st.markdown("#### 🌐 Dil Dağılımı")
                    lang_counts = history_df['language'].value_counts()
                    if not lang_counts.empty:
                        if go is not None:
                            fig_lang = go.Figure(data=[go.Pie(
                                labels=lang_counts.index,
                                values=lang_counts.values,
                                hole=0.4,
                                marker_colors=['#4a90e2', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#f97316']
                            )])
                            fig_lang.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                height=300,
                                showlegend=True
                            )
                            st.plotly_chart(fig_lang, use_container_width=True, key="stats_language_chart")
                        else:
                            # Plotly yoksa basit chart
                            st.bar_chart(lang_counts)
                    else:
                        st.info("Henüz dil verisi yok")
                
                with format_col2:
                    st.markdown("#### � Dosya Formatları")
                    # Dosya uzantılarını analiz et
                    history_df['file_extension'] = history_df['file_name'].apply(lambda x: os.path.splitext(x)[1].lower() if pd.notna(x) else 'unknown')
                    format_counts = history_df['file_extension'].value_counts()
                    
                    if not format_counts.empty:
                        if go is not None:
                            fig_format = go.Figure(data=[go.Bar(
                                x=format_counts.index,
                                y=format_counts.values,
                                marker_color='#10b981',
                                opacity=0.8
                            )])
                            fig_format.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                height=300,
                                xaxis_title="Format",
                                yaxis_title="Sayı"
                            )
                            st.plotly_chart(fig_format, use_container_width=True, key="stats_format_chart")
                        else:
                            # Plotly yoksa basit chart
                            st.bar_chart(format_counts)
                    else:
                        st.info("Henüz format verisi yok")
                
                with format_col3:
                    st.markdown("#### 📊 Dosya Boyutu Dağılımı")
                    # Dosya boyutu kategorileri
                    history_df['size_category'] = pd.cut(
                        history_df['file_size'] / (1024 * 1024),  # MB'ye çevir
                        bins=[0, 1, 5, 10, 25],
                        labels=['<1MB', '1-5MB', '5-10MB', '10-25MB']
                    )
                    size_counts = history_df['size_category'].value_counts()
                    
                    if not size_counts.empty:
                        if go is not None:
                            fig_size = go.Figure(data=[go.Pie(
                                labels=size_counts.index,
                                values=size_counts.values,
                                hole=0.3,
                                marker_colors=['#ef4444', '#f59e0b', '#10b981', '#8b5cf6']
                            )])
                            fig_size.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                height=300,
                                showlegend=True
                            )
                            st.plotly_chart(fig_size, use_container_width=True, key="stats_size_chart")
                        else:
                            # Plotly yoksa basit chart
                            st.bar_chart(size_counts)
                    else:
                        st.info("Henüz boyut verisi yok")
                
                # ===== PERFORMANS METRİKLERİ =====
                st.markdown("### ⚡ Performans Metrikleri")
                
                perf_col1, perf_col2 = st.columns(2)
                
                with perf_col1:
                    st.markdown("#### 🚀 İşlem Süresi Analizi")
                    if 'processing_time' in history_df.columns:
                        processing_times = history_df['processing_time'].dropna()
                        if len(processing_times) > 0:
                            if go is not None:
                                fig_perf = go.Figure()
                                fig_perf.add_trace(go.Histogram(
                                    x=processing_times,
                                    nbinsx=20,
                                    marker_color='#8b5cf6',
                                    opacity=0.7
                                ))
                                fig_perf.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'),
                                    height=300,
                                    xaxis_title="İşlem Süresi (saniye)",
                                    yaxis_title="Frekans"
                                )
                                st.plotly_chart(fig_perf, use_container_width=True, key="stats_performance_chart")
                            else:
                                # Plotly yoksa basit chart
                                st.line_chart(processing_times)
                            
                            # Performans istatistikleri
                            avg_time = processing_times.mean()
                            max_time = processing_times.max()
                            min_time = processing_times.min()
                            
                            st.markdown(f"""
                            **⚡ Performans Özeti:**
                            - Ortalama: {avg_time:.2f}s
                            - En hızlı: {min_time:.2f}s  
                            - En yavaş: {max_time:.2f}s
                            """)
                    else:
                        st.info("Performans verisi bulunamadı")
                
                with perf_col2:
                    st.markdown("#### 🎯 Kalite Dağılımı")
                    if 'confidence_score' in history_df.columns:
                        confidence_scores = history_df['confidence_score'].dropna()
                        if len(confidence_scores) > 0:
                            # Kalite kategorileri
                            history_df['quality_category'] = pd.cut(
                                confidence_scores,
                                bins=[0, 0.6, 0.8, 0.9, 1.0],
                                labels=['Düşük (<60%)', 'Orta (60-80%)', 'İyi (80-90%)', 'Mükemmel (90%+)']
                            )
                            quality_counts = history_df['quality_category'].value_counts()
                            
                            if go is not None:
                                fig_quality = go.Figure(data=[go.Bar(
                                    x=quality_counts.index,
                                    y=quality_counts.values,
                                    marker_color=['#ef4444', '#f59e0b', '#10b981', '#4a90e2'],
                                    opacity=0.8
                                )])
                                fig_quality.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'),
                                    height=300,
                                    xaxis_title="Kalite Kategorisi",
                                    yaxis_title="Sayı"
                                )
                                st.plotly_chart(fig_quality, use_container_width=True, key="stats_quality_chart")
                            else:
                                st.warning("📊 Plotly is not available. Quality visualization cannot be displayed.")
                    else:
                        st.info("Kalite verisi bulunamadı")
                
                # ===== GELİŞMİŞ EXPORT SEÇENEKLERİ =====
                st.markdown("### 💾 Gelişmiş Export Seçenekleri")
                
                export_col1, export_col2, export_col3, export_col4 = st.columns(4)
                
                with export_col1:
                    if st.button("📊 Detaylı Rapor", use_container_width=True):
                        # Detaylı analiz raporu oluştur
                        report_data = {
                            "genel_istatistikler": {
                                "toplam_dosya": total_files,
                                "toplam_boyut_mb": round(total_size_mb, 2),
                                "toplam_sure_dakika": round(total_duration_min, 2),
                                "favori_sayisi": favorites_count,
                                "ortalama_guven_skoru": round(avg_confidence, 3) if avg_confidence else 0
                            },
                            "dil_dagilimi": lang_counts.to_dict(),
                            "format_dagilimi": format_counts.to_dict(),
                            "aylik_trend": db_stats.get('monthly', []),
                            "rapor_tarihi": datetime.now().isoformat()
                        }
                        
                        st.download_button(
                            "📥 Detaylı Rapor İndir",
                            data=json.dumps(report_data, indent=2, ensure_ascii=False),
                            file_name=f"whisper_detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                
                with export_col2:
                    if st.button("📄 CSV Export", use_container_width=True):
                        csv_data = history_df.to_csv(index=False)
                        st.download_button(
                            "📥 CSV İndir",
                            data=csv_data,
                            file_name=f"whisper_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                with export_col3:
                    if st.button("🔧 JSON Backup", use_container_width=True):
                        json_data = export_database_to_json()
                        if json_data:
                            st.download_button(
                                "📥 JSON İndir",
                                data=json_data,
                                file_name=f"whisper_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                
                with export_col4:
                    if st.button("📈 Excel Rapor", use_container_width=True):
                        try:
                            # Excel export (eğer openpyxl varsa)
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                history_df.to_excel(writer, sheet_name='Raw_Data', index=False)
                                
                                # İstatistik sayfası
                                stats_df = pd.DataFrame([{
                                    'Metrik': 'Toplam Dosya',
                                    'Değer': total_files
                                }, {
                                    'Metrik': 'Toplam Boyut (MB)',
                                    'Değer': round(total_size_mb, 2)
                                }, {
                                    'Metrik': 'Toplam Süre (dk)',
                                    'Değer': round(total_duration_min, 2)
                                }])
                                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                            
                            st.download_button(
                                "� Excel İndir",
                                data=excel_buffer.getvalue(),
                                file_name=f"whisper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        except ImportError:
                            st.error("Excel export için openpyxl kütüphanesi gerekli")
                        except Exception as e:
                            st.error(f"Excel export hatası: {str(e)}")
                
                # ===== HIZLI İSTATİSTİKLER =====
                st.markdown(f"### {get_text('quick_statistics')}")
                
                quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
                
                with quick_col1:
                    most_popular_lang = str(lang_counts.index[0]) if not lang_counts.empty else "N/A"
                    st.metric("🏆 En Popüler Dil", most_popular_lang)
                
                with quick_col2:
                    most_used_format = str(format_counts.index[0]) if not format_counts.empty else "N/A"
                    st.metric("📁 En Çok Kullanılan Format", most_used_format)
                
                with quick_col3:
                    avg_file_size = total_size_mb / total_files if total_files > 0 else 0
                    st.metric("📊 Ortalama Dosya Boyutu", f"{avg_file_size:.1f} MB")
                
                with quick_col4:
                    avg_duration = total_duration_min / total_files if total_files > 0 else 0
                    st.metric("⏱️ Ortalama Süre", f"{avg_duration:.1f} dk")
            
            else:
                # Veri yoksa özel tasarım
                st.markdown(f"""
                <div style="text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, #1a1d23 0%, #2d3748 100%); border-radius: 15px; margin: 2rem 0;">
                    <h2 style="color: #4a90e2; margin-bottom: 1rem;">{get_text('no_analysis_data_html')}</h2>
                    <p style="color: #888; font-size: 1.1rem; margin-bottom: 2rem;">{get_text('upload_first_file_html')}</p>
                    <div style="background: rgba(74, 144, 226, 0.1); padding: 1.5rem; border-radius: 10px; border-left: 4px solid #4a90e2;">
                        <strong style="color: #4a90e2;">{get_text('tip_after_upload')}</strong>
                        <ul style="text-align: left; margin: 1rem 0; color: #cccccc;">
                            <li>{get_text('usage_trends_analytics')}</li>
                            <li>{get_text('language_format_analysis')}</li>
                            <li>{get_text('performance_metrics_detail')}</li>
                            <li>{get_text('advanced_export_options')}</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"{get_text('statistics_calculation_error')} {str(e)}")
            logger.error(f"Statistics calculation error: {str(e)}")

# =============================================
# 🚀 APPLICATION ENTRY POINT 
# =============================================

# Global sistem başlatma
try:
    # Veritabanı başlatma (database.py'den import edildi)
    
    # Global managers initialization
    
    # Memory management
    memory_manager = MemoryManager()
    
    # Real-time progress manager (WebSocket disabled for Streamlit compatibility)
    progress_manager = RealTimeProgressManager()
    # progress_manager.start_websocket_server()  # Disabled due to event loop conflicts
    
    # Her 100 işlemde bir otomatik temizlik
    if 'cleanup_counter' not in st.session_state:
        st.session_state.cleanup_counter = 0
    
    st.session_state.cleanup_counter += 1
    if st.session_state.cleanup_counter % 100 == 0:
        memory_manager.cleanup_session_state()
        
    # Güvenlik kontrolü
    security_manager = SecurityManager()
    
    logger.info("Whisper AI Application started - Streamlined Version")
    
except Exception as e:
    st.error(f"❌ S {str(e)}")
    logger.error(f"System startup error: {str(e)}")
    st.stop()

if __name__ == "__main__":
    main()
