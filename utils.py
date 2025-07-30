"""
🔧 Whisper AI - Yardımcı Fonksiyonlar ve Sınıflar
===============================================
Bu modül uygulamanın yardımcı sınıflarını ve fonksiyonlarını içerir.
"""

import os
import sys
import gc
import time
import json
import tempfile
import threading
import logging
import hashlib
import numpy as np
import io
import signal
import subprocess
import asyncio
import shutil
import socket
from typing import Optional, Dict, Any, Tuple, List, Callable
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import re

import streamlit as st
try:
    from openai import OpenAI  # type: ignore
except ImportError:
    OpenAI = None
    st.warning("⚠️ openai package not found")

try:
    import librosa  # type: ignore
except ImportError:
    librosa = None

try:
    import soundfile as sf  # type: ignore
except ImportError:
    sf = None

try:
    from pydub import AudioSegment  # type: ignore
except ImportError:
    AudioSegment = None

try:
    import plotly.graph_objects as go  # type: ignore
except ImportError:
    go = None

# Optional imports with error handling - import edilen modüller runtime'da kontrol edilecek
try:
    import psutil  # type: ignore
except ImportError:
    psutil = None

# Config'den import
from config import ADVANCED_CONFIG, SPEECH_SPEED_CATEGORIES

# Logger setup
logger = logging.getLogger(__name__)

# =============================================
# 🧠 MEMORY MANAGEMENT CLASS
# =============================================

class MemoryManager:
    """Bellek yönetimi için sınıf - iyileştirilmiş versiyon"""
    
    @staticmethod
    def cleanup_session_state(prefixes: Optional[List[str]] = None, force_cleanup: bool = False):
        """Session state temizleme - iyileştirilmiş versiyon"""
        if prefixes is None:
            prefixes = ["processed_", "result_", "file_", "audio_", "chunk_", "temp_", "file_data_"]
        
        cleaned_count = 0
        total_size_freed = 0
        
        # Tüm file_data_ anahtarlarını bul ve boyutlarına göre sırala
        file_data_keys = []
        for key in st.session_state.keys():
            if isinstance(key, str) and key.startswith("file_data_"):
                try:
                    value = st.session_state[key]
                    size = sys.getsizeof(value)
                    # Eğer bytes data varsa onu da hesapla
                    if isinstance(value, dict) and 'file_bytes' in value:
                        size += len(value['file_bytes'])
                    file_data_keys.append((key, size))
                except Exception:
                    file_data_keys.append((key, 0))
        
        # Boyuta göre sırala (büyükten küçüğe)
        file_data_keys.sort(key=lambda x: x[1], reverse=True)
        
        # Force cleanup veya 5'ten fazla file_data varsa temizle
        if force_cleanup or len(file_data_keys) > 5:
            # En büyük dosyaları temizle
            keys_to_clean = file_data_keys[:max(len(file_data_keys) - 3, 1)]
            for key, size in keys_to_clean:
                if key in st.session_state:
                    # Geçici dosyayı da temizle
                    value = st.session_state[key]
                    if isinstance(value, dict) and 'file_path' in value:
                        TempFileManager.cleanup_temp_file(value['file_path'])
                    
                    del st.session_state[key]
                    cleaned_count += 1
                    total_size_freed += size
        
        # Diğer prefix'leri temizle
        for key in list(st.session_state.keys()):
            if isinstance(key, str) and any(key.startswith(prefix) for prefix in prefixes):
                try:
                    size = sys.getsizeof(st.session_state[key])
                    del st.session_state[key]
                    cleaned_count += 1
                    total_size_freed += size
                except Exception:
                    continue
        
        # Geçici dosyaları da temizle
        temp_cleaned = TempFileManager.cleanup_session_temp_files()
        
        # Python garbage collection
        gc.collect()
        
        logger.info(f"Cleaned {cleaned_count} session state variables, "
                   f"{total_size_freed/1024/1024:.1f}MB freed, "
                   f"{temp_cleaned} temp files cleaned")
        return cleaned_count
    
    @staticmethod
    def get_memory_usage():
        """Mevcut bellek kullanımını al"""
        try:
            if psutil:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                return {
                    'rss': memory_info.rss / 1024 / 1024,  # MB
                    'vms': memory_info.vms / 1024 / 1024,  # MB
                    'percent': process.memory_percent()
                }
            else:
                # psutil kullanılamıyorsa sys modülünü kullan
                return {
                    'rss': sys.getsizeof(globals()) / 1024 / 1024,
                    'vms': 0,
                    'percent': 0
                }
        except Exception:
            return {"error": "memory_info_unavailable"}
    
    @staticmethod
    def auto_cleanup_large_files(force: bool = False):
        """Büyük dosyaları otomatik temizle - her işlem sonrası çağrılır"""
        session_size = 0
        large_items = []
        
        for key, value in list(st.session_state.items()):
            try:
                if isinstance(value, bytes):
                    size = len(value)
                elif isinstance(value, str):
                    size = len(value.encode('utf-8'))
                elif isinstance(value, dict) and 'file_bytes' in value:
                    # file_bytes içeren dict'ler için özel işlem
                    size = len(value['file_bytes']) + sys.getsizeof(value)
                else:
                    size = sys.getsizeof(value)
                
                session_size += size
                
                # 5MB'dan büyük veya force flag varsa temizle
                if size > 5 * 1024 * 1024 or force:
                    large_items.append((key, size))
                    
            except Exception:
                continue
        
        # Büyük öğeleri temizle
        for key, size in large_items:
            if key in st.session_state:
                # Geçici dosya varsa onu da temizle
                value = st.session_state[key]
                if isinstance(value, dict) and 'file_path' in value:
                    TempFileManager.cleanup_temp_file(value['file_path'])
                
                del st.session_state[key]
                logger.info(f"Removed large item {key} ({size/1024/1024:.1f}MB)")
        
        # Garbage collection
        gc.collect()
        
        total_size_mb = session_size / 1024 / 1024
        logger.info(f"Session total size: {total_size_mb:.1f}MB, "
                   f"cleaned {len(large_items)} large items")
        
        return len(large_items)
    
    @staticmethod
    def smart_cleanup_after_processing():
        """İşlem sonrası akıllı temizlik"""
        # Önce büyük dosyaları temizle
        cleaned_large = MemoryManager.auto_cleanup_large_files()
        
        # Sonra genel session temizliği
        cleaned_session = MemoryManager.cleanup_session_state(force_cleanup=True)
        
        logger.info(f"Smart cleanup completed: {cleaned_large} large items, "
                   f"{cleaned_session} session items cleaned")
        
        return cleaned_large + cleaned_session

# =============================================
# 📁 TEMPORARY FILE MANAGER
# =============================================

class TempFileManager:
    """Geçici dosya yönetimi"""
    
    @staticmethod
    def create_temp_file(file_bytes: bytes, suffix: str = "") -> Optional[str]:
        """Güvenli geçici dosya oluştur"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_bytes)
                temp_path = tmp_file.name
            return temp_path
        except Exception as e:
            logger.error(f"Temp file creation failed: {e}")
            return None
    
    @staticmethod
    def cleanup_temp_file(file_path: Optional[str]) -> bool:
        """Geçici dosyayı temizle"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                return True
            return False
        except Exception as e:
            logger.warning(f"Temp file cleanup failed for {file_path}: {e}")
            return False
    
    @staticmethod
    def cleanup_session_temp_files() -> int:
        """Session'daki tüm geçici dosyaları temizle"""
        cleaned_count = 0
        for key, value in list(st.session_state.items()):
            if isinstance(value, dict) and 'file_path' in value:
                if TempFileManager.cleanup_temp_file(value['file_path']):
                    cleaned_count += 1
        return cleaned_count

# =============================================
# 🔐 SECURITY MANAGER
# =============================================

class SecurityManager:
    """Güvenlik yönetimi sınıfı"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """API anahtarı format validation"""
        if not api_key:
            return False
        
        # OpenAI API key format: sk-...
        if not api_key.startswith('sk-'):
            return False
        
        if len(api_key) < 20:
            return False
        
        return True
    
    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """API anahtarını maskele"""
        if not api_key or len(api_key) < 8:
            return "***"
        return f"{api_key[:8]}...{api_key[-4:]}"
    
    @staticmethod
    def validate_file_security(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
        """Dosya güvenlik kontrolleri"""
        # Dosya boyutu kontrolü
        max_size = 25 * 1024 * 1024  # 25MB
        if len(file_bytes) > max_size:
            return False, f"Dosya çok büyük: {len(file_bytes)/1024/1024:.1f}MB > 25MB"
        
        # Dosya uzantısı kontrolü
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.mp4', '.flac', '.ogg']
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in allowed_extensions:
            return False, f"Desteklenmeyen dosya türü: {file_ext}"
        
        # Basit magic number kontrolü
        magic_numbers = {
            b'ID3': 'MP3',
            b'RIFF': 'WAV',
            b'\x00\x00\x00': 'MP4/M4A',
            b'fLaC': 'FLAC',
            b'OggS': 'OGG'
        }
        
        file_start = file_bytes[:8]
        is_valid_audio = False
        for magic, format_name in magic_numbers.items():
            if file_start.startswith(magic):
                is_valid_audio = True
                break
        
        if not is_valid_audio:
            return False, "Dosya geçerli bir ses dosyası değil"
        
        return True, "OK"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Dosya adını temizle"""
        # Zararlı karakterleri kaldır
        dangerous_chars = '<>:"/\\|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Maksimum uzunluk
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:90] + ext
        
        return filename

# =============================================
# 🌐 ASYNC API HANDLER
# =============================================

class AsyncAPIHandler:
    """Asenkron API çağrıları için yardımcı sınıf"""
    
    @staticmethod
    def safe_api_call(func, *args, timeout=30, **kwargs):
        """API çağrısını güvenli şekilde yapar - timeout ile"""
        import signal
        
        class TimeoutError(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutError("API call timed out")
        
        try:
            # Windows için farklı yaklaşım
            if sys.platform.startswith('win'):
                # ThreadPoolExecutor kullan
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        result = future.result(timeout=timeout)
                        return True, result
                    except Exception as e:
                        return False, str(e)
            else:
                # Unix sistemler için signal kullan - Windows'ta çalışmaz
                try:
                    signal.signal(signal.SIGALRM, timeout_handler)  # type: ignore
                    signal.alarm(timeout)  # type: ignore
                    
                    try:
                        result = func(*args, **kwargs)
                        signal.alarm(0)  # type: ignore # Cancel alarm
                        return True, result
                    except TimeoutError:
                        return False, "API call timed out"
                    except Exception as e:
                        signal.alarm(0)  # type: ignore
                        return False, str(e)
                except AttributeError:
                    # signal.SIGALRM Windows'ta yok, ThreadPoolExecutor kullan
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(func, *args, **kwargs)
                        try:
                            result = future.result(timeout=timeout)
                            return True, result
                        except Exception as e:
                            return False, str(e)
                    
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    @staticmethod
    def test_api_connection(client) -> Tuple[bool, str]:
        """API bağlantısını güvenli şekilde test eder"""
        try:
            success, result = AsyncAPIHandler.safe_api_call(
                client.models.list,
                timeout=10
            )
            
            if success:
                return True, "API connection successful"
            else:
                return False, f"API test failed: {result}"
                
        except Exception as e:
            return False, f"API test error: {str(e)}"

# =============================================
# 📂 FILE CHUNKER
# =============================================

class FileChunker:
    """Büyük dosyaları parçalara bölen sınıf"""
    
    @staticmethod
    def should_chunk_file(file_size_mb: float, threshold_mb: float = 20) -> bool:
        """Dosyanın chunk'lanması gerekip gerekmediğini kontrol eder"""
        return file_size_mb > threshold_mb
    
    @staticmethod
    def chunk_audio_file(file_bytes: bytes, file_name: str, chunk_duration_seconds: int = 300) -> List[dict]:
        """Ses dosyasını belirtilen süre parçalarına böler"""
        temp_path: Optional[str] = None  # Initialize temp_path
        try:
            # Geçici dosya oluştur
            temp_path = TempFileManager.create_temp_file(file_bytes, os.path.splitext(file_name)[1])
            if not temp_path:
                raise Exception("Geçici dosya oluşturulamadı")
            
            # PyDub ile yükle
            if AudioSegment is None:
                raise Exception("pydub kütüphanesi yüklü değil")
            audio = AudioSegment.from_file(temp_path)
            
            # Chunk'lara böl
            chunk_length_ms = chunk_duration_seconds * 1000
            chunks = []
            
            for i in range(0, len(audio), chunk_length_ms):
                chunk = audio[i:i + chunk_length_ms]
                
                # Chunk'ı WAV formatında bytes'a çevir
                chunk_buffer = io.BytesIO()
                chunk.export(chunk_buffer, format="wav")
                chunk_bytes = chunk_buffer.getvalue()
                
                chunks.append({
                    'data': chunk_bytes,
                    'start_time': i / 1000,  # saniye
                    'end_time': min((i + chunk_length_ms) / 1000, len(audio) / 1000),
                    'duration': len(chunk) / 1000
                })
            
            # Geçici dosyayı temizle
            TempFileManager.cleanup_temp_file(temp_path)
            
            return chunks
            
        except Exception as e:
            logger.error(f"File chunking failed: {e}")
            # temp_path burada mutlaka tanımlı çünkü try bloğunda tanımlandı
            TempFileManager.cleanup_temp_file(temp_path)
            return []

# =============================================
# 🎵 TRANSCRIPTION PROCESSOR
# =============================================

class TranscriptionProcessor:
    """Gelişmiş transkripsiyon işlemcisi"""
    
    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.retry_count = 0
        self.max_retries = config.get('max_retries', 3)
    
    def process_audio_file(self, file_bytes: bytes, file_name: str, language: Optional[str] = None, 
                          response_format: str = "text", progress_callback=None) -> dict:
        """Ana transkripsiyon işlemi - chunking destekli"""
        
        start_time = time.time()
        
        # Dosya güvenlik kontrolü
        is_safe, security_msg = SecurityManager.validate_file_security(file_bytes, file_name)
        if not is_safe:
            raise Exception(f"Güvenlik hatası: {security_msg}")
        
        # Dosya boyutunu kontrol et
        file_size_mb = len(file_bytes) / (1024 * 1024)
        
        if progress_callback:
            progress_callback("🔍 Dosya analiz ediliyor...", 10)
        
        # Dosya büyükse chunk'lara böl
        if FileChunker.should_chunk_file(file_size_mb, threshold_mb=self.config.get('max_file_size_mb', 20)):
            return self._process_large_file(file_bytes, file_name, language, response_format, progress_callback)
        else:
            return self._process_single_file(file_bytes, file_name, language, response_format, progress_callback)
    
    def _process_single_file(self, file_bytes: bytes, file_name: str, language: Optional[str], 
                           response_format: str, progress_callback) -> dict:
        """Tek dosya işlemi"""
        
        start_time = time.time()
        temp_path: Optional[str] = None  # Initialize temp_path
        
        if progress_callback:
            progress_callback("📤 Whisper API'ya gönderiliyor...", 30)
        
        try:
            # Geçici dosya oluştur
            temp_path = TempFileManager.create_temp_file(file_bytes, os.path.splitext(file_name)[1])
            if not temp_path:
                raise Exception("Geçici dosya oluşturulamadı")
            
            if progress_callback:
                progress_callback("🧠 Transkripsiyon işleniyor...", 60)
            
            # API çağrısı
            with open(temp_path, "rb") as audio_file:
                transcript = self._call_whisper_api(audio_file, language, response_format)
            
            # Geçici dosyayı temizle
            TempFileManager.cleanup_temp_file(temp_path)
            
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
            if 'temp_path' in locals():
                TempFileManager.cleanup_temp_file(temp_path)
            raise e
    
    def _process_large_file(self, file_bytes: bytes, file_name: str, language: Optional[str], 
                          response_format: str, progress_callback) -> dict:
        """Büyük dosya chunk'lı işlemi"""
        
        start_time = time.time()
        
        if progress_callback:
            progress_callback("✂️ Dosya parçalara bölünüyor...", 20)
        
        # Dosyayı chunk'lara böl
        chunks = FileChunker.chunk_audio_file(file_bytes, file_name, self.config.get('chunk_duration_seconds', 300))
        
        if progress_callback:
            progress_callback(f"📦 {len(chunks)} parça oluşturuldu", 25)
        
        transcripts = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            temp_path: Optional[str] = None  # Initialize for each chunk
            try:
                if progress_callback:
                    progress = 25 + (i / total_chunks) * 60
                    progress_callback(f"🔄 Parça {i+1}/{total_chunks} işleniyor...", progress)
                
                # Chunk'ı geçici dosyaya kaydet
                temp_path = TempFileManager.create_temp_file(chunk['data'], ".wav")
                if not temp_path:
                    continue
                
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
                TempFileManager.cleanup_temp_file(temp_path)
                
                # Bellek temizliği
                if i % 3 == 0:  # Her 3 chunk'ta bir
                    gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                # temp_path burada tanımlı olmalı
                TempFileManager.cleanup_temp_file(temp_path)
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
        """Whisper API çağrısı - retry logic ile"""
        
        try:
            # API çağrısı
            if language:
                return self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format=response_format,
                    language=language,
                    timeout=self.config.get('api_timeout_seconds', 30)
                )
            else:
                return self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format=response_format,
                    timeout=self.config.get('api_timeout_seconds', 30)
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
                    raise Exception(f"Rate limit exceeded after retries: {error_message}")
            
            # Genel retry logic
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * 1  # Exponential backoff
                logger.warning(f"API call failed, retrying in {wait_time}s... (attempt {retry_count + 1})")
                time.sleep(wait_time)
                return self._call_whisper_api(audio_file, language, response_format, retry_count + 1)
            else:
                raise Exception(f"API call failed after retries: {error_message}")
    
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

# =============================================
# 🎵 AUDIO ANALYSIS FUNCTIONS
# =============================================

@st.cache_data
def analyze_audio_file(file_bytes, file_name):
    """Ses dosyasını analiz eder ve bilgileri döndürür"""
    try:
        # Geçici dosya oluştur
        temp_path = TempFileManager.create_temp_file(file_bytes, os.path.splitext(file_name)[1])
        if not temp_path:
            raise Exception("Geçici dosya oluşturulamadı")
        
        # PyDub ile ses dosyasını yükle (daha güvenilir)
        if AudioSegment is None:
            raise Exception("pydub kütüphanesi yüklü değil")
        audio = AudioSegment.from_file(temp_path)
        
        # Temel bilgiler
        duration = len(audio) / 1000.0  # milliseconds to seconds
        duration_minutes = int(duration // 60)
        duration_seconds = int(duration % 60)
        
        # Ses kalitesi bilgileri
        sample_rate = audio.frame_rate
        channels = audio.channels
        sample_width = audio.sample_width
        
        # dB hesaplaması
        avg_db = audio.dBFS
        
        # Dalga formu verisi için basit örnekleme
        raw_data = audio.get_array_of_samples()
        if channels == 2:
            # Stereo ise mono'ya çevir
            raw_data = np.array(raw_data).reshape((-1, 2)).mean(axis=1)
        else:
            raw_data = np.array(raw_data)
        
        # Downsampling for visualization
        downsample_factor = max(1, len(raw_data) // 2000)
        time_axis = np.arange(0, len(raw_data), downsample_factor) / sample_rate
        waveform_data = raw_data[::downsample_factor]
        
        # Normalize waveform
        if len(waveform_data) > 0:
            waveform_data = waveform_data / np.max(np.abs(waveform_data)) if np.max(np.abs(waveform_data)) > 0 else waveform_data
        
        # Geçici dosyayı temizle
        TempFileManager.cleanup_temp_file(temp_path)
        
        return {
            'duration': duration,
            'duration_str': f"{duration_minutes:02d}:{duration_seconds:02d}",
            'sample_rate': sample_rate,
            'channels': channels,
            'avg_db': avg_db,
            'sample_width': sample_width,
            'time_axis': time_axis,
            'waveform': waveform_data,
            'file_size_mb': len(file_bytes) / (1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Ses analizi hatası: {e}")
        return None

def create_waveform_plot(time_axis, waveform):
    """Dalga formu grafiği oluşturur - multilingual support"""
    from config import get_text
    
    if go is None:
        # Plotly yoksa basit bir mesaj döndür
        import streamlit as st
        st.warning("📊 Plotly is not available. Waveform visualization cannot be displayed.")
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_axis,
        y=waveform,
        mode='lines',
        name=get_text('waveform_trace_name'),
        line=dict(color='#4a90e2', width=1)
    ))
    
    fig.update_layout(
        title=get_text('waveform_title'),
        xaxis_title=get_text('time_axis_label'),
        yaxis_title=get_text('amplitude_label'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def estimate_processing_time(duration_minutes):
    """İşlem süresi tahmini"""
    # Ortalama olarak 1 dakika ses = 10-15 saniye işlem süresi
    estimated_seconds = duration_minutes * 12
    if estimated_seconds < 60:
        return f"~{estimated_seconds:.0f} saniye"
    else:
        return f"~{estimated_seconds/60:.1f} dakika"

# =============================================
# 🤖 AI ANALYSIS FUNCTIONS
# =============================================

def analyze_text_with_ai(text, client, duration_seconds=None, model="gpt-4-turbo"):
    """Metni AI ile analiz eder - asenkron ve güvenli versiyon"""
    
    def safe_ai_call(prompt, max_tokens=200, temperature=0.3, timeout=30):
        """Güvenli AI çağrısı"""
        success, result = AsyncAPIHandler.safe_api_call(
            client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        
        if success:
            # result OpenAI response objesi olmalı
            try:
                # Type güvenli erişim
                result_obj: Any = result
                if hasattr(result_obj, 'choices') and result_obj.choices:
                    return result_obj.choices[0].message.content.strip()
                else:
                    # Eğer string ise direkt döndür
                    return str(result)
            except:
                return str(result)
        else:
            raise Exception(f"AI call failed: {result}")
    
    try:
        # Metin çok uzunsa kısalt
        if len(text) > 8000:
            text = text[:8000] + "\n\n[Metin analiz için kısaltılmıştır...]"
        
        # 1. Özetleme - asenkron
        summary_prompt = f"""
        Lütfen aşağıdaki metni özetle. Ana konuları ve önemli noktaları vurgula:
        
        {text}
        
        Özet:
        """
        
        try:
            summary = safe_ai_call(summary_prompt, max_tokens=200, timeout=20)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            summary = "Özet oluşturulamadı"
        
        # 2. Anahtar kelime çıkarma - asenkron
        keywords_prompt = f"""
        Aşağıdaki metinden en önemli 10 anahtar kelimeyi çıkar. Sadece kelimeleri virgülle ayırarak listele:
        
        {text}
        
        Anahtar kelimeler:
        """
        
        try:
            keywords_text = safe_ai_call(keywords_prompt, max_tokens=100, timeout=15)
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
        except Exception as e:
            logger.warning(f"Keywords generation failed: {e}")
            keywords = []
        
        # 3. Duygusal analiz - asenkron
        emotion_prompt = f"""
        Aşağıdaki metnin duygusal tonunu analiz et. Sadece bu formatla cevap ver:
        Genel Duygu: [pozitif/negatif/nötr]
        Detay: [kısa açıklama]
        Güven: [%]
        
        {text[:2000]}
        """
        
        try:
            emotion_analysis = safe_ai_call(emotion_prompt, max_tokens=150, timeout=15)
        except Exception as e:
            logger.warning(f"Emotion analysis failed: {e}")
            emotion_analysis = "Duygusal analiz yapılamadı"
        
        # 4. Konuşma hızı analizi
        word_count = len(text.split())
        if duration_seconds and duration_seconds > 0:
            words_per_minute = (word_count / duration_seconds) * 60
            speed_category = get_speech_speed_category(words_per_minute)
            
            # Kalite değerlendirmesi
            if 120 <= words_per_minute <= 160:
                quality_assessment = "Mükemmel - İdeal konuşma hızı"
            elif 100 <= words_per_minute < 120 or 160 < words_per_minute <= 180:
                quality_assessment = "İyi - Kabul edilebilir hız"
            elif 80 <= words_per_minute < 100 or 180 < words_per_minute <= 220:
                quality_assessment = "Orta - Biraz yavaş/hızlı"
            else:
                quality_assessment = "Düşük - Çok yavaş veya çok hızlı"
            
            speed_analysis = {
                'word_count': word_count,
                'duration_minutes': duration_seconds / 60,
                'words_per_minute': words_per_minute,
                'speed_category': speed_category,
                'quality_assessment': quality_assessment
            }
        else:
            speed_analysis = {
                'word_count': word_count,
                'duration_minutes': 0,
                'words_per_minute': 0,
                'speed_category': 'Süre bilgisi yok',
                'quality_assessment': 'Değerlendirilemiyor - Süre bilgisi eksik'
            }
        
        return {
            'summary': summary,
            'keywords': keywords,
            'emotion_analysis': emotion_analysis,
            'speed_analysis': speed_analysis,
            'model': model,  # Kullanılan AI model bilgisi
            'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),  # Analiz zamanı
            'text_length': len(text),  # Analiz edilen metin uzunluğu
            'analysis_quality': 'High' if len(text) > 100 else 'Limited'  # Analiz kalitesi
        }
        
    except Exception as e:
        logger.error(f"AI analiz hatası: {e}")
        return None

def get_speech_speed_category(wpm):
    """Konuşma hızı kategorisini belirler"""
    if wpm < 120:
        return "🐌 Yavaş"
    elif wpm < 160:
        return "🚶 Normal"
    elif wpm < 200:
        return "🏃 Hızlı"
    else:
        return "🏃‍♂️ Çok Hızlı"

def highlight_keywords_in_text(text, keywords):
    """Metinde anahtar kelimeleri vurgular"""
    highlighted_text = text
    for keyword in keywords:
        if keyword and len(keyword.strip()) > 2:  # En az 3 karakter
            pattern = re.compile(re.escape(keyword.strip()), re.IGNORECASE)
            highlighted_text = pattern.sub(f'<mark style="background-color: #4a90e2; color: white; padding: 2px 4px; border-radius: 3px;">{keyword.strip()}</mark>', highlighted_text)
    return highlighted_text

def create_ai_analysis_display(ai_analysis, original_text):
    """AI analiz sonuçlarını temiz ve düzenli bir şekilde gösterir - GELİŞTİRİLMİŞ SÜRÜM"""
    from config import get_text
    
    if not ai_analysis:
        st.info("🤖 AI analiz verisi bulunamadı")
        return

    # Ana AI analiz container - gelişmiş layout
    with st.container():
        st.markdown("### 🤖 Detaylı AI Analiz Sonuçları")
        
        # İlk satır - Özet ve Anahtar Kelimeler
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # GELİŞTİRİLMİŞ ÖZETLEME BÖLÜMÜ
            st.markdown("#### 📝 AI Özet")
            summary = ai_analysis.get('summary', 'Özet bulunamadı')
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1d23 0%, #2d3748 100%); 
                       padding: 1.5rem; border-radius: 12px; 
                       border-left: 4px solid #4a90e2; margin-bottom: 1rem;
                       box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <p style="margin: 0; line-height: 1.7; font-size: 1rem; color: #f7fafc;">
                    {summary}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # GELİŞTİRİLMİŞ ANAHTAR KELİMELER
            st.markdown("#### 🔑 Anahtar Kelimeler")
            keywords = ai_analysis.get('keywords', [])
            if keywords:
                keyword_badges = ""
                for i, keyword in enumerate(keywords[:8]):  # 8 anahtar kelime
                    if keyword.strip():
                        # Renkli badges
                        colors = ['#4a90e2', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#f97316', '#06b6d4', '#84cc16']
                        color = colors[i % len(colors)]
                        keyword_badges += f'''
                        <span style="background: {color}; color: white; 
                                   padding: 6px 12px; margin: 3px; 
                                   border-radius: 15px; display: inline-block; 
                                   font-size: 0.85rem; font-weight: 500;
                                   box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                            {keyword.strip()}
                        </span> '''
                
                st.markdown(f"""
                <div style="background: #1a1d23; padding: 1.5rem; border-radius: 12px; 
                           border: 1px solid #374151; min-height: 120px;
                           display: flex; flex-wrap: wrap; align-content: flex-start;">
                    {keyword_badges}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Anahtar kelime bulunamadı")
        
        # İkinci satır - Konuşma Hızı ve Duygusal Analiz
        st.markdown("---")
        col3, col4 = st.columns(2)
        
        with col3:
            # GELİŞTİRİLMİŞ KONUŞMA HIZI ANALİZİ
            st.markdown("#### ⚡ Konuşma Hızı Analizi")
            speed = ai_analysis.get('speed_analysis', {})
            
            if speed:
                # Metrik kartları
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric(
                        "📖 Toplam Kelime", 
                        f"{speed.get('word_count', 0):,}",
                        help="Metindeki toplam kelime sayısı"
                    )
                with metric_col2:
                    duration_min = speed.get('duration_minutes', 0)
                    st.metric(
                        "⏱️ Süre", 
                        f"{duration_min:.1f} dk",
                        help="Ses dosyasının toplam süresi"
                    )
                with metric_col3:
                    wpm = speed.get('words_per_minute', 0)
                    st.metric(
                        "🗣️ Hız", 
                        f"{wpm:.0f} k/dk",
                        help="Dakikadaki kelime sayısı"
                    )
                
                # Hız kategorisi ve kalite değerlendirmesi
                speed_category = speed.get('speed_category', 'Bilinmiyor')
                quality_assessment = speed.get('quality_assessment', 'Değerlendirilemiyor')
                
                # Hız görselleştirmesi
                speed_colors = {
                    "🐌 Yavaş": "#ef4444",
                    "🚶 Normal": "#10b981", 
                    "🏃 Hızlı": "#f59e0b",
                    "🏃‍♂️ Çok Hızlı": "#ef4444"
                }
                category_color = speed_colors.get(speed_category, "#6b7280")
                
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, {category_color}22 0%, {category_color}11 100%); 
                           padding: 1rem; border-radius: 10px; border-left: 4px solid {category_color}; margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: {category_color};">Kategori:</strong> 
                            <span style="color: #f7fafc;">{speed_category}</span>
                        </div>
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #cbd5e0;">
                        <strong>Kalite:</strong> {quality_assessment}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Konuşma hızı analizi bulunamadı")
        
        with col4:
            # GELİŞTİRİLMİŞ DUYGUSAL ANALİZ
            st.markdown("#### 💭 Duygusal Analiz")
            emotion = ai_analysis.get('emotion_analysis', 'Duygusal analiz bulunamadı')
            
            # Duygu parsing (eğer structured format varsa)
            if isinstance(emotion, str) and "Genel Duygu:" in emotion:
                lines = emotion.split('\n')
                emotion_info = {}
                for line in lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        emotion_info[key.strip()] = value.strip()
                
                general_emotion = emotion_info.get('Genel Duygu', 'Bilinmiyor')
                detail = emotion_info.get('Detay', '')
                confidence = emotion_info.get('Güven', '0%')
                
                # Duygu renklendirilmesi
                emotion_colors = {
                    'pozitif': '#10b981',
                    'negatif': '#ef4444', 
                    'nötr': '#6b7280',
                    'mixed': '#f59e0b'
                }
                
                emotion_color = emotion_colors.get(general_emotion.lower(), '#6b7280')
                
                # Confidence percentage extraction
                try:
                    conf_percent = int(confidence.replace('%', ''))
                except:
                    conf_percent = 0
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {emotion_color}22 0%, {emotion_color}11 100%); 
                           padding: 1.5rem; border-radius: 12px; 
                           border-left: 4px solid {emotion_color};">
                    <div style="margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                            <span style="background: {emotion_color}; color: white; 
                                       padding: 4px 12px; border-radius: 20px; 
                                       font-size: 0.8rem; font-weight: 600; margin-right: 1rem;">
                                {general_emotion.upper()}
                            </span>
                            <span style="color: #cbd5e0; font-size: 0.9rem;">
                                Güven: {confidence}
                            </span>
                        </div>
                        <div style="background: {emotion_color}33; height: 6px; border-radius: 3px; overflow: hidden;">
                            <div style="background: {emotion_color}; height: 100%; width: {conf_percent}%; transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                    <p style="margin: 0; color: #f7fafc; line-height: 1.5; font-size: 0.95rem;">
                        {detail}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: #1a1d23; padding: 1.5rem; border-radius: 12px; 
                           border-left: 4px solid #f59e0b;">
                    <p style="margin: 0; line-height: 1.5; font-size: 0.95rem; color: #f7fafc;">
                        {emotion}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
        # Üçüncü satır - Vurgulanan Metin (Expandable)
        st.markdown("---")
        with st.expander("🔍 Anahtar Kelimelerle Vurgulanmış Metin", expanded=False):
            if keywords and original_text:
                highlighted_text = highlight_keywords_in_text(original_text, keywords)
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a1d23 0%, #2d3748 100%); 
                           padding: 2rem; border-radius: 12px; line-height: 1.8; 
                           font-size: 1rem; max-height: 400px; overflow-y: auto;
                           border: 1px solid #374151;">
                    {highlighted_text}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Vurgulanacak anahtar kelime bulunamadı")
        
        # Analiz Meta Bilgileri
        if ai_analysis.get('analysis_timestamp'):
            st.caption(f"🕐 Analiz Zamanı: {ai_analysis.get('analysis_timestamp')} | "
                      f"📊 Model: {ai_analysis.get('model', 'GPT-4-Turbo')} | "
                      f"📏 Metin Uzunluğu: {ai_analysis.get('text_length', 0):,} karakter | "
                      f"🎯 Kalite: {ai_analysis.get('analysis_quality', 'Standart')}")

# =============================================
# 📤 INITIALIZATION HELPER
# =============================================

def initialize_openai_client():
    """Güvenli OpenAI client başlatma - asenkron test ile"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise Exception("API anahtarı bulunamadı. Lütfen .env dosyanıza OPENAI_API_KEY ekleyin")
    
    if not SecurityManager.validate_api_key(api_key):
        raise Exception("Geçersiz API anahtarı formatı. API anahtarı 'sk-' ile başlamalı ve en az 20 karakter olmalı")
    
    try:
        if OpenAI is None:
            raise Exception("OpenAI kütüphanesi yüklü değil")
            
        client = OpenAI(
            api_key=api_key,
            timeout=ADVANCED_CONFIG.get('api_timeout_seconds', 30)
        )
        
        # API bağlantısını güvenli şekilde test et
        test_success, test_message = AsyncAPIHandler.test_api_connection(client)
        
        if test_success:
            logger.info(f"OpenAI API connected successfully with key: {SecurityManager.mask_api_key(api_key)}")
            return client
        else:
            raise Exception(f"API connection test failed: {test_message}")
        
    except Exception as e:
        raise Exception(f"OpenAI client initialization failed: {str(e)}")

# =============================================
# 🔗 ALTERNATIVE DOWNLOAD MANAGERS
# =============================================

class AlternativeDownloadManager:
    """Alternatif indirme yöneticileri sınıfı"""
    
    @staticmethod
    def download_with_requests(url: str, progress_callback: Optional[Callable] = None) -> Tuple[Optional[bytes], Dict]:
        """Requests ile direkt URL indirme (extract edilmiş URL gerekli)"""
        try:
            # Requests import - hata varsa yakala
            try:
                import requests
            except ImportError:
                return None, {'error': 'Requests kütüphanesi yüklü değil. Lütfen: pip install requests'}
            
            import time
            from urllib.parse import urlparse
            
            start_time = time.time()
            
            if progress_callback:
                progress_callback("🌐 Requests ile bağlantı kuruluyor...", 10)
            
            # Stream download with progress
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            if progress_callback:
                progress_callback(f"📥 Requests ile indiriliyor ({total_size/(1024*1024):.1f} MB)...", 20)
            
            audio_data = bytearray()
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    audio_data.extend(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0 and progress_callback:
                        percent = (downloaded / total_size) * 100
                        progress_callback(f"📥 İndiriliyor: {percent:.1f}%", min(percent * 0.8, 80))
            
            total_time = time.time() - start_time
            
            if progress_callback:
                progress_callback("✅ Requests indirme tamamlandı!", 100)
            
            # Basit metadata
            filename = urlparse(url).path.split('/')[-1] or "audio_file"
            
            metadata = {
                'title': filename,
                'file_size_mb': len(audio_data) / (1024 * 1024),
                'original_url': url,
                'download_time': total_time,
                'downloader': 'requests'
            }
            
            return bytes(audio_data), metadata
            
        except Exception as e:
            logger.error(f"Requests download error: {e}")
            return None, {'error': f'Requests hatası: {str(e)}'}
    
    @staticmethod
    def download_with_aria2(url: str, progress_callback: Optional[Callable] = None) -> Tuple[Optional[bytes], Dict]:
        """Aria2 ile indirme (external process)"""
        try:
            import subprocess
            import tempfile
            import time
            import os
            
            start_time = time.time()
            
            if progress_callback:
                progress_callback("🚀 Aria2 download manager başlatılıyor...", 10)
            
            # Geçici dizin
            temp_dir = tempfile.mkdtemp()
            output_file = os.path.join(temp_dir, "aria2_audio")
            
            # Aria2 komutu
            aria2_cmd = [
                'aria2c',
                '--max-connection-per-server=8',
                '--split=8',
                '--min-split-size=1M',
                '--max-download-limit=0',
                '--file-allocation=falloc',
                '--continue=true',
                '--auto-file-renaming=false',
                '--allow-overwrite=true',
                '--summary-interval=1',
                f'--dir={temp_dir}',
                f'--out=aria2_audio',
                url
            ]
            
            if progress_callback:
                progress_callback("📥 Aria2 ile hızlı indirme başlatılıyor...", 20)
            
            # Aria2 çalıştır
            process = subprocess.run(aria2_cmd, capture_output=True, text=True, timeout=300)
            
            if process.returncode != 0:
                return None, {'error': f'Aria2 error: {process.stderr}'}
            
            # İndirilen dosyayı bul
            downloaded_file = None
            for file in os.listdir(temp_dir):
                if file.startswith("aria2_audio"):
                    downloaded_file = os.path.join(temp_dir, file)
                    break
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                return None, {'error': 'Aria2 ile dosya indirilemedi'}
            
            if progress_callback:
                progress_callback("📖 Dosya okunuyor...", 90)
            
            # Dosyayı oku
            with open(downloaded_file, 'rb') as f:
                audio_data = f.read()
            
            # Temizlik
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            total_time = time.time() - start_time
            
            if progress_callback:
                progress_callback("✅ Aria2 indirme tamamlandı!", 100)
            
            metadata = {
                'title': 'Aria2 Download',
                'file_size_mb': len(audio_data) / (1024 * 1024),
                'original_url': url,
                'download_time': total_time,
                'downloader': 'aria2'
            }
            
            return audio_data, metadata
            
        except Exception as e:
            logger.error(f"Aria2 download error: {e}")
            return None, {'error': f'Aria2 hatası: {str(e)}'}
    
    @staticmethod
    def download_with_httpx(url: str, progress_callback: Optional[Callable] = None) -> Tuple[Optional[bytes], Dict]:
        """HTTPX ile asenkron indirme"""
        try:
            # HTTPX import - hata varsa yakala
            try:
                import httpx  # type: ignore
            except ImportError:
                return None, {'error': 'HTTPX kütüphanesi yüklü değil. Lütfen: pip install httpx'}
            
            import asyncio
            import time
            
            start_time = time.time()
            
            async def async_download():
                if progress_callback:
                    progress_callback("⚡ HTTPX async indirme başlatılıyor...", 10)
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    async with client.stream('GET', url, headers=headers) as response:
                        response.raise_for_status()
                        
                        total_size = int(response.headers.get('content-length', 0))
                        audio_data = bytearray()
                        downloaded = 0
                        
                        if progress_callback:
                            progress_callback(f"📥 HTTPX ile indiriliyor ({total_size/(1024*1024):.1f} MB)...", 20)
                        
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            audio_data.extend(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0 and progress_callback:
                                percent = (downloaded / total_size) * 100
                                progress_callback(f"📥 İndiriliyor: {percent:.1f}%", min(percent * 0.8, 80))
                        
                        return bytes(audio_data)
            
            # Async download çalıştır
            audio_data = asyncio.run(async_download())
            
            total_time = time.time() - start_time
            
            if progress_callback:
                progress_callback("✅ HTTPX indirme tamamlandı!", 100)
            
            metadata = {
                'title': 'HTTPX Download',
                'file_size_mb': len(audio_data) / (1024 * 1024),
                'original_url': url,
                'download_time': total_time,
                'downloader': 'httpx'
            }
            
            return audio_data, metadata
            
        except Exception as e:
            logger.error(f"HTTPX download error: {e}")
            return None, {'error': f'HTTPX hatası: {str(e)}'}

# End of file
