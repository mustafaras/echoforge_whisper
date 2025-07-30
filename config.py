"""
⚙️ echo-forge - Çok Dilli Konfigürasyon Yönetimi
=====================================
Bu modül uygulamanın tüm konfigürasyon ayarlarını ve çok dilli desteği yönetir.
"""

import os
from pathlib import Path

# =============================================
# 🌍 LANGUAGE SUPPORT SYSTEM
# =============================================

import streamlit as st

# Session state üzerinden dil yönetimi
def get_current_language():
    """Get current language from session state or default"""
    if 'current_language' not in st.session_state:
        st.session_state.current_language = os.getenv("ECHO_FORGE_LANGUAGE", "tr")
    return st.session_state.current_language

# Current language setting - session state'ten al
CURRENT_LANGUAGE = get_current_language()

# UI Text translations
UI_TEXTS = {
    "tr": {
        # Genel
        "app_name": "echo-forge",
        "version": "v0.1",
        "description": "Gelişmiş Ses Transkripsiyon",
        "powered_by": "Powered by OpenAI • Made with ❤️",
        
        # Ana başlıklar
        "upload_files": "📁 Dosya Yükle",
        "youtube_url": "🎬 YouTube URL",
        "smart_translation": "🔄 Akıllı Çeviri",
        "history": "📚 Geçmiş İşlemler",
        "favorites": "⭐ Favoriler",
        "statistics": "📊 İstatistikler",
        
        # Yükleme alanı
        "upload_title": "Ses Dosyası Yükle",
        "upload_description": "Ses dosyalarınızı transkripsiyon için yükleyin",
        "upload_formats": "MP3 • WAV • M4A • MP4 • MPEG4 | Maksimum 25MB | Çoklu dosya desteklenir",
        "select_files": "Ses dosyalarınızı seçin",
        "multiple_files_help": "Birden fazla dosya seçebilirsiniz",
        "files_uploaded": "dosya yüklendi",
        "no_files": "🎵 Henüz dosya yüklenmedi",
        "drag_files": "Yukarıdaki alana ses dosyalarınızı sürükleyin veya seçin",
        
        # Sidebar
        "api_status": "🔌 API Durumu",
        "language_format": "Dil & Format Ayarları",
        "advanced_settings": "Gelişmiş Ayarlar",
        "ai_analysis": "AI Analiz Ayarları",
        "view_navigation": "Görünüm & Navigasyon",
        "quick_actions": "Hızlı Eylemler",
        "data_management": "Veri Yönetimi",
        "security": "🔐 Güvenlik",
        "memory_status": "🧠 Bellek Durumu",
        
        # Settings labels
        "transcription_language": "🌐 Dil:",
        "transcription_language_help": "Transkripsiyon dili seçin",
        "output_format": "📄 Format:",
        "output_format_help": "Çıktı formatını seçin",
        "temperature": "🌡️ Temperature",
        "max_tokens": "📝 Max Tokens",
        
        # Butonlar
        "process": "🚀 İşle",
        "download_text": "📥 Metin İndir",
        "add_favorites": "⭐ Favorilere Ekle",
        "download_analysis": "🤖 Analiz İndir",
        "clear": "🗑️ Temizle",
        "refresh": "🔄 Yenile",
        "clear_cache": "🧹 Cache Temizle",
        "cleanup_memory": "🧠 Bellek Temizle",
        
        # Durum mesajları
        "api_success": "✅ API Bağlantısı Başarılı",
        "api_error": "❌ API Hatası",
        "processing": "⏳ Bu dosya zaten işleniyor...",
        "processed_successfully": "başarıyla işlendi!",
        "pdf_ready": "✅ PDF hazır!",
        "pdf_error": "❌ PDF oluşturulamadı",
        "page_refreshed": "✅ Sayfa yenilendi",
        "cache_cleared": "✅ Cache temizlendi",
        
        # HTML metinleri
        "no_analysis_data_html": "📊 Henüz Analiz Edilecek Veri Yok",
        "upload_first_file_html": "İlk ses dosyanızı yükleyerek istatistikleri görmeye başlayın",
        "tip_after_upload": "💡 İpucu:",
        "audio_quality": "Ses Kalitesi:",
        "estimated_processing_time": "Tahmini İşlem Süresi:",
        "waveform": "Dalga Formu",
        "active_view": "Aktif Görünüm:",
        "main_file_upload": "Ana Dosya Yükleme",
        "youtube_rate_limiting_warning": "⚠️ YouTube Rate Limiting Uyarısı:",
        "youtube_rate_limiting_text": "YouTube yoğun kullanım sırasında geçici kısıtlamalar uygulayabilir. Problem yaşarsanız **manuel indirme** yöntemini kullanın veya **1 saat bekleyin**.",
        "translate_past_transcriptions": "Geçmiş transkripsiyon sonuçlarınızı 12 farklı dile çevirin",
        "minute": "dakika",
        "minutes_short": "dk",
        "words_per_minute": "kelime/dakika",
        "audio_duration": "Ses Süresi:",
        "speech_speed_rate": "Konuşma Hızı:",
        "transcription_processing": "🧠 Transkripsiyon işleniyor... (Bu birkaç dakika sürebilir)",
        "waiting_youtube_url": "YouTube URL Bekleniyor",
        "paste_youtube_link": "Yukarıdaki alana YouTube video linkini yapıştırın",
        "advanced_statistics_dashboard": "Gelişmiş İstatistik Dashboard",
        "calculating_statistics": "📊 İstatistikler hesaplanıyor...",
        "quick_statistics": "🔍 Hızlı İstatistikler",
        "statistics_calculation_error": "❌ İstatistik hesaplama hatası:",
        "no_transcription_history_yet": "📭 Henüz transkripsiyon geçmişiniz bulunmuyor.",
        
        # Sidebar navigation metinleri
        "main_file_upload_nav": "Ana Dosya Yükleme",
        "youtube_transcription_nav": "YouTube Transkripsiyon", 
        "translation_center": "Çeviri Merkezi",
        "history_view": "Geçmiş Görüntümü",
        "favorite_collection": "Favori Koleksiyonu",
        "statistics_dashboard": "İstatistik Dashboard",
        
        # Statistics sayfası HTML metinleri
        "detailed_usage_analytics": "Detaylı kullanım analitiği ve performans metrikleri",
        "usage_trends_analytics": "📈 Kullanım trendleri ve grafikler",
        "language_format_analysis": "🌍 Dil dağılımı ve format analizi", 
        "performance_metrics_detail": "⚡ Performans metrikleri",
        "advanced_export_options": "💾 Gelişmiş export seçenekleri",
        "basic_export_options": "📄 Temel export seçenekleri",
        
        # Upload tab metinleri
        "drag_drop_files": "Dosyalarınızı sürükleyip bırakın",
        "supported_formats": "Desteklenen formatlar",
        "max_file_size": "Maksimum dosya boyutu",
        "multiple_files_supported": "Çoklu dosya desteklenir",
        "analyzing": "analiz ediliyor",
        "audio_analysis_error": "Ses analizi hatası",
        "audio_quality": "Ses Kalitesi",
        "quality_high": "Yüksek",
        "quality_medium": "Orta", 
        "quality_low": "Düşük",
        "estimated_processing_time": "Tahmini İşlem Süresi",
        "minutes": "dakika",
        "start_transcription": "Transkripsiyon Başlat",
        "transcription_failed": "transkripsiyon başarısız",
        "processing_error": "İşlem hatası",
        
        # Help metinleri
        "select_main_screen_view": "Ana ekran görünümünü seçin",
        
        # Export tab metinleri
        "document_export": "📋 Doküman Export",
        "sharing": "🔗 Paylaşım", 
        "archive": "📦 Arşiv",
        "quality_high": "🟢 Yüksek",
        "quality_medium": "🟡 Orta",
        "quality_low": "🔴 Düşük",
        "quality_excellent": "🟢 Mükemmel", 
        "quality_good": "🟡 İyi",
        
        # Export seçenekleri
        "export_pdf_advanced": "📄 **Gelişmiş PDF Raporu** - Detaylı format, tablolar, grafik öğeler",
        "export_word": "📝 **Word Belgesi** - Düzenlenebilir format, tablolar, stil",
        "export_excel": "📊 **Excel Veri Tablosu** - Yapılandırılmış veri, çoklu sayfa",
        "export_qr": "🔲 **QR Kod** - Hızlı paylaşım için QR kod oluştur",
        "export_email": "📧 **Email Gönderimi**",
        "export_zip": "📦 **Komple ZIP Arşivi** - Tüm formatları tek pakette",
        
        # Dosya bilgileri
        "file_size": "**Boyut:**",
        "file_duration": "**Süre:**",
        "file_language": "**Dil:**",
        "seconds": "saniye",
        "automatic": "Otomatik",
        
        # Buton metinleri
        "view_detail": "👁️ Detay Gör",
        "remove_from_favorites": "💔 Favoriden Çıkar",
        "add_to_favorites": "⭐ Favorile",
        "memory_cleaned": "✅ temizlendi",
        "no_export_data": "ℹ️ Temizlenecek export verisi yok",
        
        # Hata mesajları
        "file_too_large": "çok büyük",
        "mb_limit": "MB sınırı",
        "unsupported_format": "desteklenmeyen format",
        "file_write_error": "❌ Dosya yazma hatası:",
        "temp_file_warning": "⚠️ Geçici dosya temizleme uyarısı:",
        "system_startup_error": "❌ Sistem başlatma hatası:",
        "memory_info_unavailable": "Bellek bilgisi alınamadı",
        "db_connection_error": "❌ DB bağlantı hatası",
        "too_many_files": "⚠️ Çok fazla dosya verisi",
        "memory_cleanup_recommended": "Bellek temizliği önerilir.",
        
        # Export
        "advanced_export": "📤 Gelişmiş Export ve Paylaşım Seçenekleri",
        "ai_analysis_results": "AI Analiz Sonuçları",
        "export_sharing": "📤 Export ve Paylaşım Seçenekleri",
        "openai_translation": "🤖 OpenAI API ile çeviri yapılacak",
        "original_text_only": "📄 Sadece orijinal metin",
        
        # Geçmiş
        "total_records": "📊 Toplam kayıt bulundu",
        "language_filter": "Dil filtresi:",
        "favorites_only": "Sadece favoriler",
        "view_detail": "👁️ Detay Gör",
        "remove_favorite": "💔 Favoriden Çıkar",
        "add_favorite": "⭐ Favorile",
        "favorite_updated": "✅ Favori durumu güncellendi!",
        "full_text": "**Tam Metin:**",
        "ai_summary": "**AI Özet:**",
        "keywords": "**Anahtar Kelimeler:**",
        "delete": "🗑️ Sil",
        "no_transcriptions": "📭 Henüz hiç transkripsiyon işlemi yapılmamış",
        "no_favorites": "⭐ Henüz hiç favori eklenmemiş",
        
        # İstatistikler
        "advanced_statistics": "📊 Gelişmiş İstatistik Dashboard",
        "detailed_analytics": "Detaylı kullanım analitiği ve performans metrikleri",
        "calculating_stats": "📊 İstatistikler hesaplanıyor...",
        "main_metrics": "🎯 Ana Performans Metrikleri",
        "total_files": "📁 Toplam Dosya",
        "total_size": "💾 Toplam Boyut",
        "total_duration": "⏱️ Toplam Süre",
        "favorites": "⭐ Favoriler",
        "avg_confidence": "🎯 Ortalama Güven",
        "total_cost": "💰 Toplam Maliyet",
        "no_analysis_data": "📊 Henüz Analiz Edilecek Veri Yok",
        "upload_first_file": "İlk ses dosyanızı yükleyerek istatistikleri görmeye başlayın",
        "help_tip": "💡 İpucu:",
        "stats_will_show": "Dosya yükledikten sonra burada detaylı analizler görünecek:",
        "usage_trends": "📈 Kullanım trendleri ve grafikler",
        "language_distribution": "🌍 Dil dağılımı ve format analizi",
        "performance_metrics": "⚡ Performans metrikleri",
        "export_options": "💾 Gelişmiş export seçenekleri",
        
        # Abstract
        "abstract": "📄 Abstract",
        
        # Diğer
        "automatic": "🔍 Otomatik",
        "all": "Tümü",
        "preview": "**Önizleme:**",
        "size": "**Boyut:**",
        "duration": "**Süre:**",
        "language": "**Dil:**",
        "id": "**ID:**",
        "minutes": "dk",
        "seconds": "saniye",
        "enable_ai_analysis": "AI Analiz Etkinleştir",
        "ai_analysis_help": "Transkripsiyon sonucunu AI ile analiz eder",
        "debug_mode": "🐛 Debug Modu",
        "session_keys": "📊 Session Keys:",
        "file_data": "File Data:",
        "keyboard_help": "<kbd>F1</kbd> Yardım • <kbd>Ctrl+R</kbd> Yenile",
        
        # Footer
        "footer_version": "🔥 <strong>echo-forge v0.1</strong>",
        "footer_powered": "Powered by OpenAI • Made with ❤️",
        "footer_help": "<kbd>F1</kbd> Yardım • <kbd>Ctrl+R</kbd> Yenile",
        
        # Sidebar advanced settings - missing translations
        "analysis_types": "📊 Analiz Türleri",
        "summary_analysis": "📝 Özetleme",
        "keywords_analysis": "🔑 Anahtar Kelimeler",
        "speech_speed": "⚡ Konuşma Hızı",
        "emotion_analysis": "💭 Duygusal Analiz",
        "quick_actions_title": "⚡ Hızlı Eylemler",
        "refresh_help": "Yenile",
        "clear_help": "Temizle",
        "export_clean_help": "Export Temizle",
        "page_refreshed_msg": "✅ Sayfa yenilendi",
        "process_data_cleaned": "işlem verisi temizlendi (export verileri korundu)",
        "export_data_cleaned": "export verisi temizlendi",
        "data_management_title": "🗄️ Veri Yönetimi",
        "db_statistics": "📊 DB İstatistikleri",
        "total_records_db": "📈 Toplam kayıt:",
        "cache_clear": "🧹 Cache Temizle",
        "security_title": "🔐 Güvenlik",
        "auto_delete": "🗑️ Otomatik Silme",
        "auto_delete_help": "30 gün sonra otomatik sil",
        "encryption": "🔒 Şifreleme",
        "encryption_help": "Verileri şifrele",
        "memory_status_title": "🧠 Bellek Durumu",
        "memory_check": "🔍 Bellek Kontrolü",
        "memory_cleanup": "🧹 Bellek Temizle",
        "memory_info_unavailable": "Bellek bilgisi alınamadı",
        "technical_details": "🔍 Teknik Detaylar:",
        "error_details": "🔍 Hata Detayları:",
        "unexpected_error": "❌ Beklenmeyen hata:",
        "openai_client_error": "❌ OpenAI Client başlatma hatası:",
        
        # Smart Translation Tab
        "past_transcription_results": "🎉 Önceki Transkripsiyon Sonucu:",
        "transcription_result_title": "### 📝 Transkripsiyon Sonucu",
        "clean_and_new": "🗑️ Temizle ve Yeni Video İşle",
        "delete_from_history": "🗂️ Geçmişten Sil",
        "deleted_from_history": "✅ Geçmişten silindi",
        "delete_error": "❌ Geçmişten silinirken hata oluştu",
        "delete_error_msg": "❌ Silme hatası:",
        
        # YouTube Transcriber
        "youtube_transcription": "## 🎬 YouTube URL Transkripsiyon",
        "youtube_description": "YouTube videolarından ses çıkarıp transkripsiyon yapın",
        "youtube_warning": "⚠️ **YouTube İndirme Sınırlamaları:**",
        "video_title": "### 🎬",
        "channel": "**Kanal:**",
        "duration": "**Süre:**",
        "language_detected": "**Dil:**",
        "unknown": "Bilinmiyor",
        "video_processing": "🚀 YouTube Videosunu İşle",
        "video_processing_wait": "⏳ Video zaten işleniyor...",
        "transcription_completed": "🎉 Transkripsiyon tamamlandı!",
        "valid_youtube_url": "✅ Geçerli YouTube URL - Video ID:",
        "video_found": "📺 Video bulundu:",
        "video_too_long": "⚠️ Video çok uzun ({} dakika). Maksimum 2 saat desteklenir.",
        "video_long_warning": "⚠️ Video uzun ({} dakika). İşlem biraz sürebilir.",
        "rate_limiting_detected": "🚫 YouTube Rate Limiting Tespit Edildi!",
        "rate_limiting_info": "📝 YouTube API limitlerini aştık. Lütfen:",
        "alternative_methods": "**💡 Alternatif Yöntemler:**",
        "online_converters": "**💡 Online MP3 Converter Önerileri:**",
        "download_error": "❌ İndirme hatası:",
        "transcription_saved": "✅ Transkripsiyon geçmişe kaydedildi (ID: {})",
        "save_failed": "⚠️ Geçmişe kaydetme başarısız oldu",
        "save_error": "⚠️ Geçmişe kaydetme hatası:",
        "api_rate_limiting": "🚫 API Rate Limiting",
        "wait_minutes": "⏰ 5-10 dakika bekleyip tekrar deneyin",
        "connection_problem": "🌐 İnternet Bağlantı Sorunu",
        "check_connection": "🔄 İnternet bağlantınızı kontrol edin",
        "timeout_error": "⏱️ İşlem Zaman Aşımı",
        "timeout_retry": "🔄 Tekrar deneyin veya daha küçük video kullanın",
        
        # Additional missing translations
        "too_many_file_data": "⚠️ Çok fazla dosya verisi ({}). Bellek temizliği önerilir.",
        "no_files_selected": "🎵 Henüz dosya seçilmedi",
        "drag_drop_files": "Ses dosyalarınızı buraya sürükleyip bırakın veya yukarıdan seçin",
        "no_export_file": "💡 Henüz export dosyası oluşturulmadı",
        "no_transcriptions_yet": "📭 Henüz hiç transkripsiyon işlemi yapılmamış",
        "no_favorites_yet": "⭐ Henüz favori kaydınız bulunmuyor.",
        "no_favorites_added": "⭐ Henüz hiç favori eklenmemiş",
        "file_processed_successfully": "✅ {} başarıyla işlendi!",
        "history_transcriptions": "## 📚 Geçmiş Transkripsiyon İşlemleri",
        "favorite_transcriptions": "## ⭐ Favori Transkripsiyon İşlemleri",
        "no_analysis_data_html": "📊 Henüz Analiz Edilecek Veri Yok",
        "upload_first_file_html": "İlk ses dosyanızı yükleyerek istatistikleri görmeye başlayın",
        "tip_after_upload": "💡 İpucu: Dosya yükledikten sonra burada detaylı analizler görünecek:",
        
        # Analysis depth options
        "analysis_depth_basic": "Basit",
        "analysis_depth_medium": "Orta", 
        "analysis_depth_detailed": "Detaylı",
        "analysis_depth_comprehensive": "Kapsamlı",
        "analysis_depth_label": "🔍 Analiz Detayı:",
        
        # Translation tab
        "past_transcription_selection": "📋 Geçmiş Transkripsiyon Seçimi",
        "first_use_upload_tabs": "💡 Önce 'Dosya Yükle' veya 'YouTube URL' sekmelerini kullanarak transkripsiyon yapın.",
        "removed_from_favorites": "Favorilerden çıkarıldı",
        "download_full_report": "📊 Tam Rapor İndir",
        "record_deleted": "Kayıt silindi!",
        
        # Audio file info labels
        "duration_label": "⏱️ Süre",
        "size_label": "📊 Boyut", 
        "sample_rate_label": "🎵 Sample Rate",
        "channel_label": "🔊 Kanal",
        "stereo": "Stereo",
        "mono": "Mono",
        
        # Waveform plot labels
        "waveform_title": "🌊 Ses Dalga Formu",
        "time_axis_label": "Zaman (saniye)",
        "amplitude_label": "Genlik",
        "waveform_trace_name": "Dalga Formu",
        
        # Processing result labels
        "transcription_result_header": "Transkripsiyon",
        "ai_analysis_results": "AI Analiz Sonuçları", 
        "export_sharing_options": "📤 Export ve Paylaşım Seçenekleri",
        "advanced_export_sharing": "📤 Gelişmiş Export ve Paylaşım Seçenekleri",
        "translation_option": "🌐 Çeviri Seçeneği:",
        "no_translation": "Çeviri Yok",
        "translate_to_english": "İngilizce'ye Çevir",
        "translate_to_turkish": "Türkçe'ye Çevir",
        "openai_translation_info": "🤖 OpenAI API ile çeviri yapılacak",
        "download_text_button": "📄 Metin İndir",
        "add_to_favorites_button": "⭐ Favorilere Ekle",
        "added_to_favorites": "✅ Favorilere eklendi!",
        "export_options": "📤 Export Seçenekleri",
        "additional_export_options": "🔗 Ek Export Seçenekleri",
        "advanced_export_options_header": "🚀 Gelişmiş Export Seçenekleri",
        
        # AI Analysis section headers
        "ai_summary_header": "📝 AI Özet",
        "ai_keywords_header": "🔑 Anahtar Kelimeler", 
        "speech_analysis_header": "⚡ Konuşma Hızı Analizi",
        "emotion_analysis_header": "💭 Duygusal Analiz",
        "highlighted_keywords_header": "🔍 Anahtar Kelimeler ile Vurgulanmış Metin",
        
        # AI Analysis processing messages
        "ai_analysis_processing": "🤖 AI ANALİZ YAPILIYOR...",
        "ai_analysis_completed": "✅ AI analiz tamamlandı!",
        
        # Speed analysis labels
        "total_words": "📖 Toplam Kelime",
        "duration": "⏱️ Süre", 
        "speed": "🗣️ Hız",
        "speed_category": "Konuşma Hızı:",
        "words_per_minute": "kelime/dk",
        
        # Emotion analysis labels
        "general_emotion": "Genel Duygu:",
        "detail": "Detay:",
        "confidence": "Güven:",
        
        # Translation Tab - Additional keys
        "no_transcription_history_yet": "🚫 Henüz transkripsiyon geçmişi yok",
        "select_transcription_to_translate": "🎯 Çevrilecek transkripsiyon seçin:",
        "transcription_preview": "� Seçili Transkripsiyon Önizlemesi",
        "translation_settings": "⚙️ Çeviri Ayarları",
        "target_language": "� Hedef Dil:",
        "ai_model_choice": "🤖 AI Model:",
        "estimated_cost": "💰 Tahmini maliyet:",
        "start_translation": "🚀 Çeviriyi Başlat",
        "text_too_long": "❌ Metin çok uzun! Maksimum 100,000 karakter desteklenmektedir.",
        "suggest_split_translation": "💡 Çok uzun metinler için parça parça çeviri yapmanız önerilir.",
        "translation_completed": "🎉 Çeviri başarıyla tamamlandı!",
        "translation_result": "📄 Çevirisi",
        "download_translation": "📥 Çeviriyi İndir",
        "clear_new_translation": "🗑️ Temizle ve Yeni Çeviri",
        "recent_files_available": "✨ yeni işlenmiş dosya mevcut!",
        "content_preview": "📝 İçerik Önizlemesi (İlk 500 karakter):",
        "full_content_will_translate": "💡 Sadece önizleme gösteriliyor. Çeviride **{} karakterin tamamı** kullanılacak.",
        "full_content": "📝 Tam İçerik:",
        "source_file": "🗂️ Kaynak:",
        "target_language_label": "🌍 Hedef Dil:",
        "model_used": "🤖 Model:",
        "character_count": "📊 Uzunluk:",
        "character_arrow": "→",
        "last_translation_result": "🎉 Son Çeviri Sonucu:",
        "translation_settings_help": "Metni hangi dile çevirmek istiyorsunuz?",
        "model_quality_help": "Çeviri kalitesi: GPT-4o > GPT-4 Turbo > GPT-4o Mini > GPT-3.5 Turbo"
    },
    
    "en": {
        # General
        "app_name": "echo-forge",
        "version": "v0.1",
        "description": "Advanced Audio Transcription",
        "powered_by": "Powered by OpenAI • Made with ❤️",
        
        # Main headers
        "upload_files": "📁 Upload Files",
        "youtube_url": "🎬 YouTube URL",
        "smart_translation": "🔄 Smart Translation",
        "history": "📚 History",
        "favorites": "⭐ Favorites",
        "statistics": "📊 Statistics",
        
        # Upload area
        "upload_title": "Upload Audio File",
        "upload_description": "Upload your audio files for transcription",
        "upload_formats": "MP3 • WAV • M4A • MP4 • MPEG4 | Maximum 25MB | Multiple files supported",
        "select_files": "Select your audio files",
        "multiple_files_help": "You can select multiple files",
        "files_uploaded": "files uploaded",
        "no_files": "🎵 No files uploaded yet",
        "drag_files": "Drag and drop your audio files above or click to select",
        
        # Sidebar
        "api_status": "🔌 API Status",
        "language_format": "Language & Format Settings",
        "advanced_settings": "Advanced Settings",
        "ai_analysis": "AI Analysis Settings",
        "view_navigation": "View & Navigation",
        "quick_actions": "Quick Actions",
        "data_management": "Data Management",
        "security": "🔐 Security",
        "memory_status": "🧠 Memory Status",
        
        # Settings labels
        "transcription_language": "🌐 Language:",
        "transcription_language_help": "Select transcription language",
        "output_format": "📄 Format:",
        "output_format_help": "Select output format",
        "temperature": "🌡️ Temperature",
        "max_tokens": "📝 Max Tokens",
        
        # Buttons
        "process": "🚀 Process",
        "download_text": "📥 Download Text",
        "add_favorites": "⭐ Add to Favorites",
        "download_analysis": "🤖 Download Analysis",
        "clear": "🗑️ Clear",
        "refresh": "🔄 Refresh",
        "clear_cache": "🧹 Clear Cache",
        "cleanup_memory": "🧠 Cleanup Memory",
        
        # Status messages
        "api_success": "✅ API Connection Successful",
        "api_error": "❌ API Error",
        "processing": "⏳ This file is already being processed...",
        "processed_successfully": "successfully processed!",
        "pdf_ready": "✅ PDF ready!",
        "pdf_error": "❌ PDF could not be created",
        "page_refreshed": "✅ Page refreshed",
        "cache_cleared": "✅ Cache cleared",
        
        # HTML texts
        "no_analysis_data_html": "📊 No Data to Analyze Yet",
        "upload_first_file_html": "Upload your first audio file to start viewing statistics",
        "tip_after_upload": "💡 Tip:",
        "audio_quality": "Audio Quality:",
        "estimated_processing_time": "Estimated Processing Time:",
        "waveform": "Waveform",
        "active_view": "Active View:",
        "main_file_upload": "Main File Upload",
        "youtube_rate_limiting_warning": "⚠️ YouTube Rate Limiting Warning:",
        "youtube_rate_limiting_text": "YouTube may apply temporary restrictions during heavy usage. If you experience problems, use **manual download** method or **wait 1 hour**.",
        "translate_past_transcriptions": "Translate your past transcription results to 12 different languages",
        "minute": "minute",
        "minutes_short": "min",
        "words_per_minute": "words/minute",
        "audio_duration": "Audio Duration:",
        "speech_speed_rate": "Speech Speed:",
        "transcription_processing": "🧠 Transcription processing... (This may take a few minutes)",
        "waiting_youtube_url": "Waiting for YouTube URL",
        "paste_youtube_link": "Paste the YouTube video link in the field above",
        "advanced_statistics_dashboard": "Advanced Statistics Dashboard",
        "calculating_statistics": "📊 Calculating statistics...",
        "quick_statistics": "🔍 Quick Statistics",
        "statistics_calculation_error": "❌ Statistics calculation error:",
        "no_transcription_history_yet": "📭 You don't have any transcription history yet.",
        
        # Sidebar navigation texts
        "main_file_upload_nav": "Main File Upload",
        "youtube_transcription_nav": "YouTube Transcription", 
        "translation_center": "Translation Center",
        "history_view": "History View",
        "favorite_collection": "Favorite Collection",
        "statistics_dashboard": "Statistics Dashboard",
        
        # Statistics page HTML texts
        "detailed_usage_analytics": "Detailed usage analytics and performance metrics",
        "usage_trends_analytics": "📈 Usage trends and charts",
        "language_format_analysis": "🌍 Language distribution and format analysis", 
        "performance_metrics_detail": "⚡ Performance metrics",
        "advanced_export_options": "💾 Advanced export options",
        "basic_export_options": "📄 Basic export options",
        
        # Upload tab texts
        "drag_drop_files": "Drag and drop your files",
        "supported_formats": "Supported formats",
        "max_file_size": "Maximum file size",
        "multiple_files_supported": "Multiple files supported",
        "analyzing": "analyzing",
        "audio_analysis_error": "Audio analysis error",
        "audio_quality": "Audio Quality",
        "quality_high": "High",
        "quality_medium": "Medium",
        "quality_low": "Low", 
        "estimated_processing_time": "Estimated Processing Time",
        "minutes": "minutes",
        "start_transcription": "Start Transcription",
        "transcription_failed": "transcription failed",
        "processing_error": "Processing error",
        
        # Help texts
        "select_main_screen_view": "Select main screen view",
        
        # Export tab texts
        "document_export": "📋 Document Export",
        "sharing": "🔗 Sharing", 
        "archive": "📦 Archive",
        "quality_high": "🟢 High",
        "quality_medium": "🟡 Medium",
        "quality_low": "🔴 Low",
        "quality_excellent": "🟢 Excellent", 
        "quality_good": "🟡 Good",
        
        # Export options
        "export_pdf_advanced": "📄 **Advanced PDF Report** - Detailed format, tables, graphic elements",
        "export_word": "📝 **Word Document** - Editable format, tables, style",
        "export_excel": "📊 **Excel Data Table** - Structured data, multiple sheets",
        "export_qr": "🔲 **QR Code** - Generate QR code for quick sharing",
        "export_email": "📧 **Email Sending**",
        "export_zip": "📦 **Complete ZIP Archive** - All formats in one package",
        
        # File information
        "file_size": "**Size:**",
        "file_duration": "**Duration:**",
        "file_language": "**Language:**",
        "seconds": "seconds",
        "automatic": "Automatic",
        
        # Button texts
        "view_detail": "👁️ View Details",
        "remove_from_favorites": "💔 Remove from Favorites",
        "add_to_favorites": "⭐ Add to Favorites",
        "memory_cleaned": "✅ cleaned",
        "no_export_data": "ℹ️ No export data to clean",
        
        # Error messages
        "file_too_large": "too large",
        "mb_limit": "MB limit",
        "unsupported_format": "unsupported format",
        "file_write_error": "❌ File write error:",
        "temp_file_warning": "⚠️ Temporary file cleanup warning:",
        "system_startup_error": "❌ System startup error:",
        "memory_info_unavailable": "Memory information unavailable",
        "db_connection_error": "❌ DB connection error",
        "too_many_files": "⚠️ Too many file data",
        "memory_cleanup_recommended": "Memory cleanup recommended.",
        
        # Export
        "advanced_export": "📤 Advanced Export and Sharing Options",
        "ai_analysis_results": "AI Analysis Results",
        "export_sharing": "📤 Export and Sharing Options",
        "openai_translation": "🤖 Translation with OpenAI API",
        "original_text_only": "📄 Original text only",
        
        # History
        "total_records": "📊 Total records found",
        "language_filter": "Language filter:",
        "favorites_only": "Favorites only",
        "view_detail": "👁️ View Details",
        "remove_favorite": "💔 Remove from Favorites",
        "add_favorite": "⭐ Add to Favorites",
        "favorite_updated": "✅ Favorite status updated!",
        "full_text": "**Full Text:**",
        "ai_summary": "**AI Summary:**",
        "keywords": "**Keywords:**",
        "delete": "🗑️ Delete",
        "no_transcriptions": "📭 No transcription operations yet",
        "no_favorites": "⭐ No favorites added yet",
        
        # Statistics
        "advanced_statistics": "📊 Advanced Statistics Dashboard",
        "detailed_analytics": "Detailed usage analytics and performance metrics",
        "calculating_stats": "📊 Calculating statistics...",
        "main_metrics": "🎯 Main Performance Metrics",
        "total_files": "📁 Total Files",
        "total_size": "💾 Total Size",
        "total_duration": "⏱️ Total Duration",
        "favorites": "⭐ Favorites",
        "avg_confidence": "🎯 Average Confidence",
        "total_cost": "💰 Total Cost",
        "no_analysis_data": "📊 No Data to Analyze Yet",
        "upload_first_file": "Upload your first audio file to start seeing statistics",
        "help_tip": "💡 Tip:",
        "stats_will_show": "After uploading files, detailed analytics will appear here:",
        "usage_trends": "📈 Usage trends and charts",
        "language_distribution": "🌍 Language distribution and format analysis",
        "performance_metrics": "⚡ Performance metrics",
        "export_options": "💾 Advanced export options",
        
        # Abstract
        "abstract": "📄 Abstract",
        
        # Other
        "automatic": "🔍 Automatic",
        "all": "All",
        "preview": "**Preview:**",
        "size": "**Size:**",
        "duration": "**Duration:**",
        "language": "**Language:**",
        "id": "**ID:**",
        "minutes": "min",
        "seconds": "seconds",
        "enable_ai_analysis": "Enable AI Analysis",
        "ai_analysis_help": "Analyzes transcription results with AI",
        "debug_mode": "🐛 Debug Mode",
        "session_keys": "📊 Session Keys:",
        "file_data": "File Data:",
        "keyboard_help": "<kbd>F1</kbd> Help • <kbd>Ctrl+R</kbd> Refresh",
        
        # Footer
        "footer_version": "🔥 <strong>echo-forge v0.1</strong>",
        "footer_powered": "Powered by OpenAI • Made with ❤️",
        "footer_help": "<kbd>F1</kbd> Help • <kbd>Ctrl+R</kbd> Refresh",
        
        # Sidebar advanced settings - missing translations
        "analysis_types": "📊 Analysis Types",
        "summary_analysis": "📝 Summary",
        "keywords_analysis": "🔑 Keywords",
        "speech_speed": "⚡ Speech Speed",
        "emotion_analysis": "💭 Emotion Analysis",
        "quick_actions_title": "⚡ Quick Actions",
        "refresh_help": "Refresh",
        "clear_help": "Clear",
        "export_clean_help": "Clear Export",
        "page_refreshed_msg": "✅ Page refreshed",
        "process_data_cleaned": "process data cleared (export data preserved)",
        "export_data_cleaned": "export data cleared",
        "data_management_title": "🗄️ Data Management",
        "db_statistics": "📊 DB Statistics",
        "total_records_db": "📈 Total records:",
        "cache_clear": "🧹 Clear Cache",
        "security_title": "🔐 Security",
        "auto_delete": "🗑️ Auto Delete",
        "auto_delete_help": "Auto delete after 30 days",
        "encryption": "🔒 Encryption",
        "encryption_help": "Encrypt data",
        "memory_status_title": "🧠 Memory Status",
        "memory_check": "🔍 Memory Check",
        "memory_cleanup": "🧹 Memory Cleanup",
        "technical_details": "🔍 Technical Details:",
        "error_details": "🔍 Error Details:",
        "unexpected_error": "❌ Unexpected error:",
        "openai_client_error": "❌ OpenAI Client initialization error:",
        
        # Smart Translation Tab
        "past_transcription_results": "🎉 Previous Transcription Result:",
        "transcription_result_title": "### 📝 Transcription Result",
        "clean_and_new": "🗑️ Clear and Process New Video",
        "delete_from_history": "🗂️ Delete from History",
        "deleted_from_history": "✅ Deleted from history",
        "delete_error": "❌ Error deleting from history",
        "delete_error_msg": "❌ Delete error:",
        
        # YouTube Transcriber
        "youtube_transcription": "## 🎬 YouTube URL Transcription",
        "youtube_description": "Extract audio from YouTube videos and transcribe",
        "youtube_warning": "⚠️ **YouTube Download Limitations:**",
        "video_title": "### 🎬",
        "channel": "**Channel:**",
        "duration": "**Duration:**",
        "language_detected": "**Language:**",
        "unknown": "Unknown",
        "video_processing": "🚀 Process YouTube Video",
        "video_processing_wait": "⏳ Video is already being processed...",
        "transcription_completed": "🎉 Transcription completed!",
        "valid_youtube_url": "✅ Valid YouTube URL - Video ID:",
        "video_found": "📺 Video found:",
        "video_too_long": "⚠️ Video too long ({} minutes). Maximum 2 hours supported.",
        "video_long_warning": "⚠️ Video is long ({} minutes). Processing may take a while.",
        "rate_limiting_detected": "🚫 YouTube Rate Limiting Detected!",
        "rate_limiting_info": "📝 YouTube API limits exceeded. Please:",
        "alternative_methods": "**💡 Alternative Methods:**",
        "online_converters": "**💡 Online MP3 Converter Suggestions:**",
        "download_error": "❌ Download error:",
        "transcription_saved": "✅ Transcription saved to history (ID: {})",
        "save_failed": "⚠️ Failed to save to history",
        "save_error": "⚠️ Save to history error:",
        "api_rate_limiting": "🚫 API Rate Limiting",
        "wait_minutes": "⏰ Wait 5-10 minutes and try again",
        "connection_problem": "🌐 Internet Connection Problem",
        "check_connection": "🔄 Check your internet connection",
        "timeout_error": "⏱️ Operation Timeout",
        "timeout_retry": "🔄 Try again or use a smaller video",
        
        # Additional missing translations
        "too_many_file_data": "⚠️ Too many file data ({}). Memory cleanup recommended.",
        "no_files_selected": "🎵 No files selected yet",
        "drag_drop_files": "Drag and drop your audio files here or select from above",
        "no_export_file": "💡 No export file created yet",
        "no_transcriptions_yet": "📭 No transcription operations performed yet",
        "no_favorites_yet": "⭐ No favorite records found yet.",
        "no_favorites_added": "⭐ No favorites added yet",
        "file_processed_successfully": "✅ {} processed successfully!",
        "history_transcriptions": "## 📚 Transcription History",
        "favorite_transcriptions": "## ⭐ Favorite Transcriptions",
        "no_analysis_data_html": "📊 No Data to Analyze Yet",
        "upload_first_file_html": "Upload your first audio file to start seeing statistics",
        "tip_after_upload": "💡 Tip: After uploading files, detailed analytics will appear here:",
        
        # Analysis depth options
        "analysis_depth_basic": "Basic",
        "analysis_depth_medium": "Medium",
        "analysis_depth_detailed": "Detailed", 
        "analysis_depth_comprehensive": "Comprehensive",
        "analysis_depth_label": "🔍 Analysis Detail:",
        
        # Translation tab
        "past_transcription_selection": "📋 Past Transcription Selection",
        "first_use_upload_tabs": "💡 First use 'Upload Files' or 'YouTube URL' tabs to perform transcription.",
        "removed_from_favorites": "Removed from favorites",
        "download_full_report": "📊 Download Full Report",
        "record_deleted": "Record deleted!",
        
        # Audio file info labels
        "duration_label": "⏱️ Duration",
        "size_label": "📊 Size",
        "sample_rate_label": "🎵 Sample Rate", 
        "channel_label": "🔊 Channel",
        "stereo": "Stereo",
        "mono": "Mono",
        
        # Waveform plot labels
        "waveform_title": "🌊 Audio Waveform",
        "time_axis_label": "Time (seconds)",
        "amplitude_label": "Amplitude", 
        "waveform_trace_name": "Waveform",
        
        # Processing result labels
        "transcription_result_header": "Transcription",
        "ai_analysis_results": "AI Analysis Results",
        "export_sharing_options": "📤 Export and Sharing Options", 
        "advanced_export_sharing": "📤 Advanced Export and Sharing Options",
        "translation_option": "🌐 Translation Option:",
        "no_translation": "No Translation",
        "translate_to_english": "Translate to English", 
        "translate_to_turkish": "Translate to Turkish",
        "openai_translation_info": "🤖 Translation will be done with OpenAI API",
        "download_text_button": "📄 Download Text",
        "add_to_favorites_button": "⭐ Add to Favorites",
        "added_to_favorites": "✅ Added to favorites!",
        "export_options": "📤 Export Options",
        "additional_export_options": "🔗 Additional Export Options",
        "advanced_export_options_header": "🚀 Advanced Export Options",
        
        # AI Analysis section headers
        "ai_summary_header": "📝 AI Summary",
        "ai_keywords_header": "🔑 Keywords",
        "speech_analysis_header": "⚡ Speech Speed Analysis", 
        "emotion_analysis_header": "💭 Emotion Analysis",
        "highlighted_keywords_header": "🔍 Text Highlighted with Keywords",
        
        # AI Analysis processing messages
        "ai_analysis_processing": "🤖 AI ANALYSIS IN PROGRESS...",
        "ai_analysis_completed": "✅ AI analysis completed!",
        
        # Speed analysis labels
        "total_words": "📖 Total Words",
        "duration": "⏱️ Duration",
        "speed": "🗣️ Speed", 
        "speed_category": "Speech Speed:",
        "words_per_minute": "words/min",
        
        # AI Analysis metrics and labels for utils.py
        "total_words_metric": "📖 Total Words",
        "duration_metric": "⏱️ Duration", 
        "speed_metric": "🗣️ Speed",
        "minutes_short": "min",
        "words_per_minute_unit": "words/min",
        "speech_speed_label": "Speech Speed",
        "highlighted_text_header": "🔍 Keywords Highlighted Text",
        
        # Emotion analysis labels
        "general_emotion": "General Emotion:",
        "detail": "Detail:",
        "confidence": "Confidence:",
        
        # Translation Tab - Additional keys
        "no_transcription_history_yet": "🚫 No transcription history yet",
        "select_transcription_to_translate": "🎯 Select transcription to translate:",
        "transcription_preview": "� Selected Transcription Preview",
        "translation_settings": "⚙️ Translation Settings",
        "target_language": "� Target Language:",
        "ai_model_choice": "🤖 AI Model:",
        "estimated_cost": "💰 Estimated cost:",
        "start_translation": "🚀 Start Translation",
        "text_too_long": "❌ Text too long! Maximum 100,000 characters supported.",
        "suggest_split_translation": "💡 For very long texts, split translation is recommended.",
        "translation_completed": "🎉 Translation completed successfully!",
        "translation_result": "📄 Translation",
        "download_translation": "📥 Download Translation",
        "clear_new_translation": "🗑️ Clear and New Translation",
        "recent_files_available": "✨ new processed files available!",
        "content_preview": "📝 Content Preview (First 500 characters):",
        "full_content_will_translate": "💡 Only preview shown. **All {} characters** will be used in translation.",
        "full_content": "📝 Full Content:",
        "source_file": "🗂️ Source:",
        "target_language_label": "� Target Language:",
        "model_used": "🤖 Model:",
        "character_count": "� Length:",
        "character_arrow": "→",
        "last_translation_result": "🎉 Last Translation Result:",
        "translation_settings_help": "Which language do you want to translate the text to?",
        "model_quality_help": "Translation quality: GPT-4o > GPT-4 Turbo > GPT-4o Mini > GPT-3.5 Turbo"
    }
}

# =============================================
# 🔑 API VE TEMEL AYARLAR
# =============================================

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Uygulama ayarları
APP_CONFIG = {
    "name": "echo-forge",
    "version": "0.1",
    "description": "Advanced Audio Transcription",
    "author": "echo-forge Team",
    "page_title": "echo-forge",
    "page_icon": "🔥",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# =============================================
# 🌍 MULTILINGUAL HELPER FUNCTIONS
# =============================================

def get_text(key, lang=None):
    """
    Gets translated text for the given key
    
    Args:
        key (str): Text key to translate
        lang (str, optional): Language code. Defaults to current session language.
    
    Returns:
        str: Translated text or key if not found
    """
    if lang is None:
        lang = get_current_language()
    
    return UI_TEXTS.get(lang, {}).get(key, key)

def set_language(language_code):
    """
    Sets the current application language in session state
    
    Args:
        language_code (str): Language code ('tr' or 'en')
    """
    if language_code in UI_TEXTS:
        st.session_state.current_language = language_code
        return True
    return False

def get_available_languages():
    """
    Returns list of available language codes
    
    Returns:
        list: Available language codes
    """
    return list(UI_TEXTS.keys())

def get_language_name(lang_code):
    """
    Returns human-readable language name
    
    Args:
        lang_code (str): Language code
    
    Returns:
        str: Language name (guaranteed to be string)
    """
    names = {
        "tr": "🇹🇷 Türkçe",
        "en": "🇺🇸 English"
    }
    return names.get(lang_code, str(lang_code))

# =============================================
# 📁 DOSYA VE FORMAT AYARLARI
# =============================================

# Desteklenen ses formatları
ALLOWED_FORMATS = ["mp3", "wav", "m4a", "mp4"]

# Dosya boyutu limitleri (byte)
FILE_SIZE_LIMITS = {
    "max_file_size": 25 * 1024 * 1024,  # 25 MB
    "max_total_size": 100 * 1024 * 1024,  # 100 MB toplam
    "chunk_size": 5 * 1024 * 1024  # 5 MB chunk
}

# =============================================
# 🌍 DİL VE FORMAT SEÇENEKLERİ
# =============================================

LANGUAGES = {
    "🔍 Otomatik": None,
    "🇹🇷 Türkçe": "tr",
    "🇺🇸 İngilizce": "en",
    "🇩🇪 Almanca": "de",
    "🇫🇷 Fransızca": "fr",
    "🇪🇸 İspanyolca": "es",
    "🇮🇹 İtalyanca": "it",
    "🇷🇺 Rusça": "ru",
    "🇯🇵 Japonca": "ja",
    "🇰🇷 Korece": "ko",
    "🇨🇳 Çince": "zh",
    "🇦🇪 Arapça": "ar"
}

RESPONSE_FORMATS = ["text", "srt", "vtt"]

# =============================================
# 🤖 AI MODEL AYARLARI
# =============================================

AI_MODELS = {
    "whisper": "whisper-1",
    "gpt_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"],
    "default_gpt": "gpt-4-turbo"
}

AI_CONFIG = {
    "temperature": 0.0,
    "max_tokens": 1000,
    "timeout": 30,
    "retry_count": 3,
    "analysis_depth": ["Basit", "Orta", "Detaylı", "Kapsamlı"]
}

# Advanced config for backward compatibility
ADVANCED_CONFIG = {
    'max_file_size_mb': 25,
    'chunk_duration_seconds': 300,
    'api_timeout_seconds': 30,
    'retry_count': 3,
    'max_retries': 3,  # Eklenen alan
    'openai_api_key': OPENAI_API_KEY,
    'whisper_model': 'whisper-1',
    'enable_chunking': True,
    'overlap_seconds': 5
}

# =============================================
# 📊 ANALIZ SEÇENEKLERİ
# =============================================

AI_FEATURES = {
    "summary": "📝 Özetleme",
    "keywords": "🔑 Anahtar Kelimeler",
    "speed": "⚡ Konuşma Hızı",
    "emotion": "💭 Duygusal Analiz"
}

# Konuşma hızı kategorileri (kelime/dakika)
SPEECH_SPEED_CATEGORIES = {
    "slow": {"min": 0, "max": 120, "label": "🐌 Yavaş"},
    "normal": {"min": 120, "max": 160, "label": "🚶 Normal"},
    "fast": {"min": 160, "max": 200, "label": "🏃 Hızlı"},
    "very_fast": {"min": 200, "max": 999, "label": "🏃‍♂️ Çok Hızlı"}
}

# =============================================
# 🎵 AUDIO PROCESSING AYARLARI
# =============================================

AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_duration": 300,  # 5 dakika chunks
    "overlap_duration": 5,  # 5 saniye overlap
    "quality_threshold": 0.7,
    "noise_reduction": True,
    "auto_gain_control": True
}

# =============================================
# 🔧 SYSTEM CONFIGURATION
# =============================================

SYSTEM_CONFIG = {
    "max_concurrent_jobs": 3,
    "cache_duration": 3600,  # 1 saat
    "session_timeout": 7200,  # 2 saat
    "auto_cleanup": True,
    "memory_threshold": 0.85,  # %85 bellek kullanımında temizlik
    "temp_file_cleanup": True
}

# =============================================
# 🗄️ DATABASE CONFIGURATION
# =============================================

DATABASE_CONFIG = {
    "database_path": "whisper_history.db",
    "connection_timeout": 30.0,
    "check_same_thread": False,
    "backup_interval": 3600,  # 1 saat
    "max_connections": 10,
    "pragma_settings": {
        "foreign_keys": "ON",
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "cache_size": "-64000",  # 64MB cache
        "temp_store": "MEMORY"
    }
}

# =============================================
# 📊 PERFORMANCE MONITORING
# =============================================

PERFORMANCE_CONFIG = {
    "enable_monitoring": True,
    "log_level": "INFO",
    "metrics_collection": True,
    "error_tracking": True,
    "performance_alerts": True,
    "memory_monitoring": True
}

# =============================================
# 🔐 SECURITY SETTINGS
# =============================================

SECURITY_CONFIG = {
    "file_validation": True,
    "content_scanning": True,
    "rate_limiting": True,
    "input_sanitization": True,
    "secure_headers": True,
    "encryption_at_rest": False,  # SQLite için
    "audit_logging": True
}

# =============================================
# 📱 VIEW MODES VE NAVIGATION
# =============================================

def get_view_modes():
    """Aktif dil için VIEW_MODES listesini döndür"""
    return [
        f"📁 {get_text('main_file_upload_nav')}",
        f"🎬 {get_text('youtube_transcription_nav')}", 
        f"🌍 {get_text('translation_center')}",
        f"📚 {get_text('history_view')}",
        f"⭐ {get_text('favorite_collection')}",
        f"📊 {get_text('statistics_dashboard')}"
    ]

# Backward compatibility için static liste (eski kod uyumluluğu)
VIEW_MODES = [
    "📁 Ana Dosya Yükleme",
    "🎬 YouTube Transkripsiyon", 
    "🌍 Çeviri Merkezi",
    "📚 Geçmiş Görünümü",
    "⭐ Favori Koleksiyonu",
    "📊 İstatistik Dashboard"
]

# =============================================
# 🎨 UI THEME CONFIGURATION  
# =============================================

THEME_CONFIG = {
    "primary_color": "#4a90e2",
    "secondary_color": "#f59e0b", 
    "success_color": "#10b981",
    "error_color": "#ef4444",
    "warning_color": "#f59e0b",
    "info_color": "#8b5cf6",
    "dark_theme": True,
    "sidebar_width": 550,
    "layout_margins": {
        "top": "2rem",
        "sides": "2rem", 
        "bottom": "1rem"
    }
}

# =============================================
# 🗂️ ADVANCED EXPORT CONFIGURATION
# =============================================

EXPORT_CONFIG = {
    "pdf_settings": {
        "page_size": "A4",
        "margins": {"top": 2, "bottom": 2, "left": 2, "right": 2},
        "font_family": "Helvetica",
        "font_size": 12,
        "include_metadata": True,
        "include_timestamps": True
    },
    "word_settings": {
        "template": "default",
        "include_cover": True,
        "include_toc": True,
        "include_analysis": True
    },
    "excel_settings": {
        "include_charts": True,
        "include_pivot": True,
        "worksheet_names": ["Transcript", "Analysis", "Statistics"]
    },
    "zip_compression": 6,
    "qr_settings": {
        "size": (200, 200),
        "error_correction": "M",
        "border": 4
    }
}

# =============================================
# 🔄 ADVANCED CONFIGURATION LOADING
# =============================================

def load_user_config():
    """Load user-specific configuration overrides"""
    user_config_path = Path("user_config.json")
    if user_config_path.exists():
        import json
        try:
            with open(user_config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # Safely merge user config with defaults
                return user_config
        except Exception as e:
            print(f"Warning: Could not load user config: {e}")
    return {}

# Load user overrides
USER_CONFIG = load_user_config()

# =============================================
# 🌟 CONFIGURATION VALIDATION
# =============================================

def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Check OpenAI API key
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY environment variable not set")
    
    # Check required directories
    required_dirs = ["temp", "uploads", "assets"]
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            try:
                Path(dir_name).mkdir(exist_ok=True)
            except Exception as e:
                errors.append(f"Could not create directory {dir_name}: {e}")
    
    # Validate file size limits
    if FILE_SIZE_LIMITS["max_file_size"] > FILE_SIZE_LIMITS["max_total_size"]:
        errors.append("max_file_size cannot be larger than max_total_size")
    
    return errors

# =============================================
# 🚀 CONFIGURATION EXPORT
# =============================================

def get_config_summary():
    """Get a summary of current configuration"""
    return {
        "app": APP_CONFIG,
        "current_language": get_current_language(),
        "available_languages": get_available_languages(),
        "file_limits": FILE_SIZE_LIMITS,
        "ai_models": AI_MODELS,
        "theme": THEME_CONFIG,
        "system": SYSTEM_CONFIG,
        "security": SECURITY_CONFIG,
        "database": DATABASE_CONFIG
    }

def get_config(section=None):
    """Get configuration section or all config"""
    all_config = get_config_summary()
    
    if section is None:
        return all_config
    
    return all_config.get(section, {})

# Validate configuration on import
CONFIG_ERRORS = validate_config()
if CONFIG_ERRORS:
    print("⚠️ Configuration warnings:")
    for error in CONFIG_ERRORS:
        print(f"  - {error}")
