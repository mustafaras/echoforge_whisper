"""
🗄️ Whisper AI - Veritabanı Yönetimi
=====================================
Bu modül uygulamanın tüm veritabanı işlemlerini yönetir.
"""

import sqlite3
import json
import hashlib
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Optional, Dict, Any, List, Tuple
import os
import tempfile
import threading

# Config'den import
from config import DATABASE_CONFIG, SECURITY_CONFIG, get_config

# Logger setup
logger = logging.getLogger(__name__)

# =============================================
# 🗄️ DATABASE MANAGER CLASS
# =============================================

class DatabaseManager:
    """Güvenli veritabanı yönetimi"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "whisper_history.db"  # Fallback değer
        self.lock = threading.Lock()
        self._connection_pool = {}
        self._init_logging()
    
    def _init_logging(self):
        """Logging kurulumu"""
        self.logger = logging.getLogger(f"{__name__}.DatabaseManager")
    
    def _make_json_serializable(self, data):
        """Veriyi JSON serializable hale getirir"""
        import numpy as np
        
        if isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, (np.integer, np.floating)):
            return data.item()
        elif hasattr(data, '__dict__'):
            # Custom object'leri dict'e çevir
            return self._make_json_serializable(data.__dict__)
        else:
            try:
                json.dumps(data)  # Test et
                return data
            except (TypeError, ValueError):
                return str(data)  # String'e çevir
    
    def _get_connection(self) -> sqlite3.Connection:
        """Thread-safe bağlantı alır"""
        thread_id = threading.get_ident()
        
        if thread_id not in self._connection_pool:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._connection_pool[thread_id] = conn
        
        return self._connection_pool[thread_id]
    
    def init_database(self) -> bool:
        """Veritabanını başlatır"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Mevcut tabloyu kontrol et
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    # Yeni tablo oluştur
                    cursor.execute('''
                        CREATE TABLE transcriptions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            file_name TEXT NOT NULL,
                            file_hash TEXT UNIQUE,
                            file_size INTEGER,
                            duration_seconds REAL,
                            language TEXT,
                            format_type TEXT,
                            transcript_text TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_favorite BOOLEAN DEFAULT 0,
                            summary TEXT,
                            keywords TEXT,
                            emotion_analysis TEXT,
                            speed_analysis TEXT,
                            confidence_score REAL,
                            processing_time REAL,
                            api_cost REAL,
                            metadata TEXT,
                            deleted_at TIMESTAMP NULL
                        )
                    ''')
                else:
                    # Mevcut tablo için migration
                    self._migrate_database(cursor)
                
                # Diğer tablolar
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE UNIQUE,
                        total_files INTEGER DEFAULT 0,
                        total_duration REAL DEFAULT 0,
                        total_size INTEGER DEFAULT 0,
                        total_cost REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE,
                        setting_value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT,
                        details TEXT,
                        transcription_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (transcription_id) REFERENCES transcriptions (id)
                    )
                ''')
                
                # İndexler
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON transcriptions(file_hash)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON transcriptions(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_favorite ON transcriptions(is_favorite)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_language ON transcriptions(language)')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
    
    def _migrate_database(self, cursor):
        """Veritabanı migrasyonları"""
        try:
            # Mevcut kolonları kontrol et
            cursor.execute("PRAGMA table_info(transcriptions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Eksik kolonları ekle
            migrations = [
                ("is_favorite", "ALTER TABLE transcriptions ADD COLUMN is_favorite BOOLEAN DEFAULT 0"),
                ("confidence_score", "ALTER TABLE transcriptions ADD COLUMN confidence_score REAL"),
                ("processing_time", "ALTER TABLE transcriptions ADD COLUMN processing_time REAL"),
                ("api_cost", "ALTER TABLE transcriptions ADD COLUMN api_cost REAL"),
                ("metadata", "ALTER TABLE transcriptions ADD COLUMN metadata TEXT"),
                ("deleted_at", "ALTER TABLE transcriptions ADD COLUMN deleted_at TIMESTAMP NULL"),
                ("speed_analysis", "ALTER TABLE transcriptions ADD COLUMN speed_analysis TEXT")
            ]
            
            for column_name, migration_sql in migrations:
                if column_name not in columns:
                    cursor.execute(migration_sql)
                    self.logger.info(f"Added column: {column_name}")
                    
        except Exception as e:
            self.logger.warning(f"Migration warning: {e}")
    
    def save_transcription(self, file_name: str, file_bytes: bytes, audio_info: dict,
                          language: str, format_type: str, transcript_text: str,
                          ai_analysis: dict = None, processing_info: dict = None) -> Optional[int]:
        """Transkripsiyon kaydeder"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Dosya hash'i
                file_hash = hashlib.md5(file_bytes).hexdigest()
                
                # Duplicate kontrolü
                cursor.execute("SELECT id FROM transcriptions WHERE file_hash = ? AND deleted_at IS NULL", (file_hash,))
                existing = cursor.fetchone()
                
                if existing:
                    self.logger.info(f"Duplicate file detected: {file_name}")
                    return existing[0]
                
                # AI analiz verilerini hazırla
                summary = ai_analysis.get('summary', '') if ai_analysis else ''
                keywords = ','.join(ai_analysis.get('keywords', [])) if ai_analysis else ''
                emotion_analysis = json.dumps(self._make_json_serializable(ai_analysis.get('emotion_analysis', {}))) if ai_analysis and ai_analysis.get('emotion_analysis') else ''
                speed_analysis = json.dumps(self._make_json_serializable(ai_analysis.get('speed_analysis', {}))) if ai_analysis and ai_analysis.get('speed_analysis') else ''
                
                # İşlem bilgileri
                confidence_score = processing_info.get('confidence_score', 0.0) if processing_info else 0.0
                processing_time = processing_info.get('processing_time', 0.0) if processing_info else 0.0
                api_cost = processing_info.get('api_cost', 0.0) if processing_info else 0.0
                
                # Metadata - JSON serializable hale getir
                metadata = {
                    'audio_info': self._make_json_serializable(audio_info),
                    'processing_info': self._make_json_serializable(processing_info or {}),
                    'ai_features_used': list(ai_analysis.keys()) if ai_analysis else []
                }
                
                # Kaydet
                cursor.execute('''
                    INSERT INTO transcriptions 
                    (file_name, file_hash, file_size, duration_seconds, language, format_type,
                     transcript_text, summary, keywords, emotion_analysis, speed_analysis,
                     confidence_score, processing_time, api_cost, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_name, file_hash, len(file_bytes), audio_info.get('duration', 0),
                    language, format_type, transcript_text, summary, keywords,
                    emotion_analysis, speed_analysis, confidence_score, processing_time,
                    api_cost, json.dumps(metadata)
                ))
                
                transcription_id = cursor.lastrowid
                
                # Log kaydı
                self._log_activity(cursor, "CREATE", f"Transcription created: {file_name}", transcription_id)
                
                # Günlük istatistikleri güncelle
                self._update_daily_stats(cursor, len(file_bytes), audio_info.get('duration', 0), api_cost)
                
                conn.commit()
                self.logger.info(f"Transcription saved with ID: {transcription_id}")
                return transcription_id
                
        except Exception as e:
            self.logger.error(f"Failed to save transcription: {e}")
            return None
    
    def get_transcription_history(self, limit: int = 100, offset: int = 0, 
                                 filters: dict = None) -> pd.DataFrame:
        """Transkripsiyon geçmişini getirir"""
        try:
            conn = self._get_connection()
            
            # Base query
            query = '''
                SELECT id, file_name, file_size, duration_seconds, language, format_type,
                       SUBSTR(transcript_text, 1, 200) as preview, created_at, is_favorite,
                       summary, keywords, confidence_score, processing_time
                FROM transcriptions 
                WHERE deleted_at IS NULL
            '''
            params = []
            
            # Filtreleri uygula
            if filters:
                if filters.get('language'):
                    query += " AND language = ?"
                    params.append(filters['language'])
                
                if filters.get('is_favorite'):
                    query += " AND is_favorite = 1"
                
                if filters.get('date_from'):
                    query += " AND created_at >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    query += " AND created_at <= ?"
                    params.append(filters['date_to'])
                
                if filters.get('search_text'):
                    query += " AND (file_name LIKE ? OR transcript_text LIKE ?)"
                    search_term = f"%{filters['search_text']}%"
                    params.extend([search_term, search_term])
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to get transcription history: {e}")
            return pd.DataFrame()
    
    def get_transcription_by_id(self, transcription_id: int) -> Optional[dict]:
        """ID'ye göre transkripsiyon detayını getirir"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM transcriptions 
                WHERE id = ? AND deleted_at IS NULL
            ''', (transcription_id,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Metadata'yı parse et
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get transcription by ID: {e}")
            return None
    
    def toggle_favorite(self, transcription_id: int) -> bool:
        """Favori durumunu değiştirir"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Mevcut durumu al
                cursor.execute("SELECT is_favorite FROM transcriptions WHERE id = ?", (transcription_id,))
                row = cursor.fetchone()
                
                if row:
                    new_status = not bool(row[0])
                    cursor.execute(
                        "UPDATE transcriptions SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_status, transcription_id)
                    )
                    
                    # Log kaydı
                    action = "FAVORITE" if new_status else "UNFAVORITE"
                    self._log_activity(cursor, action, f"Favorite status changed", transcription_id)
                    
                    conn.commit()
                    return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to toggle favorite: {e}")
            return False
    
    def delete_transcription(self, transcription_id: int, soft_delete: bool = True) -> bool:
        """Transkripsiyon siler (soft delete)"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                if soft_delete:
                    cursor.execute('''
                        UPDATE transcriptions 
                        SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (transcription_id,))
                    action = "SOFT_DELETE"
                else:
                    cursor.execute("DELETE FROM transcriptions WHERE id = ?", (transcription_id,))
                    action = "HARD_DELETE"
                
                if cursor.rowcount > 0:
                    self._log_activity(cursor, action, f"Transcription deleted", transcription_id)
                    conn.commit()
                    return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete transcription: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """Kapsamlı istatistikler"""
        try:
            conn = self._get_connection()
            
            stats = {}
            
            # Genel istatistikler
            general_query = '''
                SELECT 
                    COUNT(*) as total_files,
                    SUM(file_size) as total_size,
                    SUM(duration_seconds) as total_duration,
                    SUM(api_cost) as total_cost,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(CASE WHEN is_favorite = 1 THEN 1 END) as favorite_count
                FROM transcriptions 
                WHERE deleted_at IS NULL
            '''
            
            general_stats = pd.read_sql_query(general_query, conn).iloc[0].to_dict()
            stats['general'] = general_stats
            
            # Dil dağılımı
            language_query = '''
                SELECT language, COUNT(*) as count, SUM(duration_seconds) as total_duration
                FROM transcriptions 
                WHERE deleted_at IS NULL 
                GROUP BY language 
                ORDER BY count DESC
            '''
            stats['languages'] = pd.read_sql_query(language_query, conn).to_dict('records')
            
            # Aylık trend
            monthly_query = '''
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    COUNT(*) as count,
                    SUM(file_size) as size,
                    SUM(duration_seconds) as duration
                FROM transcriptions 
                WHERE deleted_at IS NULL 
                GROUP BY month 
                ORDER BY month DESC 
                LIMIT 12
            '''
            stats['monthly'] = pd.read_sql_query(monthly_query, conn).to_dict('records')
            
            # Kalite metrikleri
            quality_query = '''
                SELECT 
                    AVG(confidence_score) as avg_confidence,
                    AVG(processing_time) as avg_processing_time,
                    COUNT(CASE WHEN confidence_score > 0.8 THEN 1 END) as high_quality_count
                FROM transcriptions 
                WHERE deleted_at IS NULL AND confidence_score > 0
            '''
            stats['quality'] = pd.read_sql_query(quality_query, conn).iloc[0].to_dict()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def export_to_json(self, include_deleted: bool = False) -> Optional[str]:
        """Veritabanını JSON formatında export eder"""
        try:
            conn = self._get_connection()
            
            query = "SELECT * FROM transcriptions"
            if not include_deleted:
                query += " WHERE deleted_at IS NULL"
            
            df = pd.read_sql_query(query, conn)
            
            # JSON'a dönüştür
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_records': len(df),
                'transcriptions': df.to_dict('records')
            }
            
            return json.dumps(export_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")
            return None
    
    def cleanup_old_records(self, days: int = None) -> int:
        """Eski kayıtları temizler"""
        try:
            days = days or SECURITY_CONFIG.get("auto_delete_days", 30)
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Soft delete edilmiş ve süresi dolmuş kayıtları hard delete et
                cursor.execute('''
                    DELETE FROM transcriptions 
                    WHERE deleted_at IS NOT NULL AND deleted_at < ?
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                
                # Log temizliği
                cursor.execute('''
                    DELETE FROM activity_logs 
                    WHERE created_at < ?
                ''', (cutoff_date,))
                
                conn.commit()
                self.logger.info(f"Cleaned up {deleted_count} old records")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")
            return 0
    
    def clear_all_data(self) -> bool:
        """Tüm veritabanı verilerini temizler"""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Tüm tabloları temizle
                cursor.execute('DELETE FROM transcriptions')
                cursor.execute('DELETE FROM activity_logs')
                
                conn.commit()
                self.logger.info("All database data cleared successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to clear all data: {e}")
            return False
    
    def _log_activity(self, cursor, action: str, details: str, transcription_id: int = None):
        """Activity log kaydı"""
        try:
            cursor.execute('''
                INSERT INTO activity_logs (action, details, transcription_id)
                VALUES (?, ?, ?)
            ''', (action, details, transcription_id))
        except Exception as e:
            self.logger.warning(f"Failed to log activity: {e}")
    
    def _update_daily_stats(self, cursor, file_size: int, duration: float, cost: float):
        """Günlük istatistikleri günceller"""
        try:
            today = datetime.now().date()
            
            cursor.execute('''
                INSERT OR IGNORE INTO statistics (date, total_files, total_duration, total_size, total_cost)
                VALUES (?, 0, 0, 0, 0)
            ''', (today,))
            
            cursor.execute('''
                UPDATE statistics 
                SET total_files = total_files + 1,
                    total_duration = total_duration + ?,
                    total_size = total_size + ?,
                    total_cost = total_cost + ?
                WHERE date = ?
            ''', (duration, file_size, cost, today))
            
        except Exception as e:
            self.logger.warning(f"Failed to update daily stats: {e}")
    
    def backup_database(self, backup_path: str = None) -> bool:
        """Veritabanı yedeği alır"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_whisper_{timestamp}.db"
            
            # SQLite backup API kullan
            with self.lock:
                source_conn = self._get_connection()
                backup_conn = sqlite3.connect(backup_path)
                
                source_conn.backup(backup_conn)
                backup_conn.close()
                
                self.logger.info(f"Database backed up to: {backup_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to backup database: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Veritabanını geri yükler"""
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Mevcut bağlantıları kapat
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
            
            # Mevcut dosyayı yedekle
            if os.path.exists(self.db_path):
                backup_current = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.db_path, backup_current)
            
            # Backup'tan geri yükle
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            # Yeni bağlantıyı test et
            self.init_database()
            
            self.logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore database: {e}")
            return False
    
    def close_connections(self):
        """Tüm bağlantıları kapatır"""
        with self.lock:
            for conn in self._connection_pool.values():
                try:
                    conn.close()
                except:
                    pass
            self._connection_pool.clear()

# =============================================
# 🔧 LEGACY FUNCTIONS - BACKWARD COMPATIBILITY
# =============================================

# Global database manager instance
db_manager = DatabaseManager()
db_manager.init_database()

def get_file_hash(file_bytes: bytes) -> str:
    """Dosya hash'i oluşturur"""
    return hashlib.md5(file_bytes).hexdigest()

def save_transcription_to_db(file_name: str, file_bytes: bytes, audio_info: dict, 
                           language: str, format_type: str, transcript_text: str, 
                           ai_analysis: dict = None) -> Optional[int]:
    """Legacy function - DatabaseManager kullanır"""
    return db_manager.save_transcription(
        file_name, file_bytes, audio_info, language, 
        format_type, transcript_text, ai_analysis
    )

def save_youtube_transcription(video_url: str, video_info: dict, transcript_text: str,
                              language: str, format_type: str = "text") -> Optional[int]:
    """YouTube transkripsiyon sonucunu veritabanına kaydeder"""
    try:
        # YouTube URL'sinden sahte dosya hash'i oluştur
        video_id = video_url.split('=')[-1].split('&')[0] if '=' in video_url else video_url.split('/')[-1]
        fake_file_bytes = video_url.encode('utf-8')  # URL'yi bytes olarak kullan
        
        # Dosya adı oluştur
        video_title = video_info.get('title', f'YouTube Video {video_id}')
        # Dosya adındaki geçersiz karakterleri temizle
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        file_name = f"YouTube - {safe_title}.{format_type}"
        
        # Audio info oluştur
        audio_info = {
            'source': 'youtube',
            'video_id': video_id,
            'url': video_url,
            'duration': video_info.get('duration_seconds', 0),
            'channel': video_info.get('channel', 'Bilinmiyor'),
            'views': video_info.get('views', 'Bilinmiyor'),
            'title': video_info.get('title', 'YouTube Video')
        }
        
        # AI analiz bilgileri (YouTube için basit)
        ai_analysis = {
            'source_type': 'youtube_video',
            'video_url': video_url,
            'video_metadata': video_info
        }
        
        # Processing info
        processing_info = {
            'source': 'youtube',
            'processed_at': datetime.now().isoformat(),
            'api_used': 'whisper-1'
        }
        
        # Veritabanına kaydet
        return db_manager.save_transcription(
            file_name=file_name,
            file_bytes=fake_file_bytes,
            audio_info=audio_info,
            language=language,
            format_type=format_type,
            transcript_text=transcript_text,
            ai_analysis=ai_analysis,
            processing_info=processing_info
        )
        
    except Exception as e:
        logger.error(f"YouTube transkripsiyon kaydedilemedi: {e}")
        return None

def get_transcription_history() -> pd.DataFrame:
    """Legacy function - DatabaseManager kullanır"""
    return db_manager.get_transcription_history()

def get_transcription_by_id(transcription_id: int) -> Optional[dict]:
    """Legacy function - DatabaseManager kullanır"""
    return db_manager.get_transcription_by_id(transcription_id)

def toggle_favorite(transcription_id: int) -> bool:
    """Legacy function - DatabaseManager kullanır"""
    return db_manager.toggle_favorite(transcription_id)

def delete_transcription(transcription_id: int) -> bool:
    """Legacy function - DatabaseManager kullanır"""
    return db_manager.delete_transcription(transcription_id)

def export_database_to_json() -> Optional[str]:
    """Legacy function - DatabaseManager kullanır"""
    return db_manager.export_to_json()

# =============================================
# 🔧 UTILITY FUNCTIONS
# =============================================

def init_database(db_path: str = None) -> DatabaseManager:
    """Veritabanını başlatır ve manager döndürür"""
    manager = DatabaseManager(db_path)
    manager.init_database()
    return manager

def get_database_info(db_path: str = None) -> dict:
    """Veritabanı bilgilerini döndürür"""
    try:
        db_path = db_path or DATABASE_CONFIG["name"]
        
        if not os.path.exists(db_path):
            return {"exists": False}
        
        # Dosya bilgileri
        stat = os.stat(db_path)
        
        # Tablo bilgileri
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        info = {
            "exists": True,
            "path": db_path,
            "size_mb": stat.st_size / (1024 * 1024),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "tables": tables
        }
        
        # Kayıt sayıları
        for table in ["transcriptions", "statistics", "activity_logs"]:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                info[f"{table}_count"] = cursor.fetchone()[0]
        
        conn.close()
        return info
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"exists": False, "error": str(e)}

def migrate_old_database(old_db_path: str, new_db_path: str = None) -> bool:
    """Eski veritabanını yeni formata migrate eder"""
    try:
        if not os.path.exists(old_db_path):
            logger.error(f"Old database not found: {old_db_path}")
            return False
        
        new_db_path = new_db_path or DATABASE_CONFIG["name"]
        
        # Yeni veritabanını oluştur
        new_manager = DatabaseManager(new_db_path)
        new_manager.init_database()
        
        # Eski veritabanından veri oku
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        
        cursor = old_conn.cursor()
        cursor.execute("SELECT * FROM transcriptions")
        
        migrated_count = 0
        for row in cursor.fetchall():
            try:
                # Veriyi yeni formata dönüştür
                row_dict = dict(row)
                
                # Yeni veritabanına kaydet
                new_manager.save_transcription(
                    file_name=row_dict.get('file_name', ''),
                    file_bytes=b'',  # Hash varsa kullan
                    audio_info={"duration": row_dict.get('duration_seconds', 0)},
                    language=row_dict.get('language', ''),
                    format_type=row_dict.get('format', 'text'),  # 'format' kolonunu kullan
                    transcript_text=row_dict.get('transcript_text', ''),
                    ai_analysis={
                        'summary': row_dict.get('summary', ''),
                        'keywords': row_dict.get('keywords', '').split(',') if row_dict.get('keywords') else []
                    }
                )
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to migrate record {row_dict.get('id')}: {e}")
        
        old_conn.close()
        logger.info(f"Migrated {migrated_count} records from {old_db_path} to {new_db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        return False

def clear_transcription_history() -> bool:
    """Tüm transkripsiyon geçmişini temizler"""
    try:
        return db_manager.clear_all_data()
    except Exception as e:
        logger.error(f"Failed to clear transcription history: {e}")
        return False
