"""
Upload Tab - Dosya Yükleme ve İşleme Modülü
Temiz ve düzenli dosya yükleme arayüzü
"""

import streamlit as st
import os
import time
import gc
import tempfile
import json
from typing import Optional, Dict, Any
from collections import Counter

from config import (
    ALLOWED_FORMATS, FILE_SIZE_LIMITS, LANGUAGES, RESPONSE_FORMATS,
    get_text, get_current_language
)
from utils import (
    analyze_audio_file, create_waveform_plot, estimate_processing_time,
    analyze_text_with_ai, create_ai_analysis_display, TranscriptionProcessor,
    MemoryManager
)
from database import save_transcription_to_db
from logger_config import transcription_logger


def render_upload_tab(client, transcription_processor):
    
    if not ai_analysis:
        st.warning("⚠️ AI analiz verisi bulunamadı")
        return
    
    # Ana metrikler - 4 kolonlu gösterim
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Metin uzunluğu
        word_count = len(transcript_text.split())
        st.metric("📝 Kelime Sayısı", f"{word_count:,}")
    
    with col2:
        # Karakter sayısı
        char_count = len(transcript_text)
        st.metric("🔤 Karakter Sayısı", f"{char_count:,}")
    
    with col3:
        # Süre bilgisi
        duration = ai_analysis.get('audio_duration_minutes', 0)
        if duration:
            st.metric("⏱️ Süre", f"{duration:.1f} dk")
        else:
            st.metric("⏱️ Süre", "Bilinmiyor")
    
    with col4:
        # Konuşma hızı (eğer süre varsa)
        if duration and duration > 0:
            wpm = word_count / duration
            st.metric("🗣️ Konuşma Hızı", f"{wpm:.0f} kelime/dk")
        else:
            st.metric("🗣️ Konuşma Hızı", "Hesaplanamadı")
    
    # Detaylı analizler - tab'lı görünüm
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📄 Özet", 
        "🏷️ Anahtar Kelimeler", 
        "💭 Duygu Analizi", 
        "📊 İstatistikler",
        "🎯 İçerik Analizi"
    ])
    
    with tab1:
        # Özet analizi
        summary = ai_analysis.get('summary', 'Özet bulunamadı')
        st.markdown(f"""
        <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #10b981;">
            <h4 style="color: #10b981; margin-bottom: 1rem;">📋 İçerik Özeti</h4>
            <p style="line-height: 1.6; color: #fafafa; margin: 0;">{summary}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Konu analizi (varsa)
        topics = ai_analysis.get('topics', [])
        if topics:
            st.markdown("#### 🎯 Ana Konular")
            topic_cols = st.columns(min(len(topics), 3))
            for i, topic in enumerate(topics[:3]):
                with topic_cols[i % 3]:
                    st.markdown(f"""
                    <div style="background: #2d3748; padding: 1rem; border-radius: 8px; text-align: center; margin: 0.5rem 0;">
                        <strong style="color: #4a90e2;">{topic}</strong>
                    </div>
                    """, unsafe_allow_html=True)
    
    with tab2:
        # Anahtar kelimeler
        keywords = ai_analysis.get('keywords', [])
        if keywords:
            st.markdown("#### 🏷️ Anahtar Kelimeler")
            
            # Anahtar kelimeleri chip'ler halinde göster
            keywords_html = ""
            for keyword in keywords[:15]:  # İlk 15 anahtar kelime
                keywords_html += f"""
                <span style="display: inline-block; background: #4a90e2; color: white; 
                           padding: 0.5rem 1rem; margin: 0.25rem; border-radius: 20px; 
                           font-size: 0.9rem;">{keyword}</span>
                """
            
            st.markdown(f"""
            <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #4a90e2;">
                {keywords_html}
            </div>
            """, unsafe_allow_html=True)
            
            # Kelime bulutu etkisi için fazla kelime varsa uyarı
            if len(keywords) > 15:
                st.info(f"💡 Toplam {len(keywords)} anahtar kelime bulundu. İlk 15 tanesi gösteriliyor.")
        else:
            st.warning("⚠️ Anahtar kelime bulunamadı")
    
    with tab3:
        # Duygu analizi
        emotion_analysis = ai_analysis.get('emotion_analysis', '')
        if emotion_analysis and emotion_analysis != "Duygusal analiz yapılamadı":
            st.markdown("#### 💭 Duygu Analizi")
            
            # Emotion analysis'i parse etmeye çalış
            try:
                # JSON formatında geliyorsa parse et
                if emotion_analysis.strip().startswith('{'):
                    import json
                    emotion_data = json.loads(emotion_analysis)
                    
                    # Ana duygu
                    main_emotion = emotion_data.get('Ana Duygu', 'Bilinmiyor')
                    confidence = emotion_data.get('Güven', '0%')
                    tone = emotion_data.get('Ton', 'Bilinmiyor')
                    
                    # Görsel gösterim
                    emotion_color = _get_emotion_color(main_emotion)
                    confidence_num = int(confidence.replace('%', '')) if '%' in confidence else 0
                    
                    st.markdown(f"""
                    <div style="background: {emotion_color}; padding: 1.5rem; border-radius: 10px; text-align: center;">
                        <h3 style="color: white; margin-bottom: 1rem;">😊 {main_emotion}</h3>
                        <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 8px;">
                            <p style="color: white; margin: 0;"><strong>Güven Oranı:</strong> {confidence}</p>
                            <p style="color: white; margin: 0.5rem 0 0 0;"><strong>Genel Ton:</strong> {tone}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Güven oranı progress bar
                    st.progress(confidence_num / 100, text=f"Güven Oranı: {confidence}")
                    
                else:
                    # Düz metin formatında
                    st.markdown(f"""
                    <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #f59e0b;">
                        <p style="line-height: 1.6; color: #fafafa; margin: 0;">{emotion_analysis}</p>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                # Parse edilemezse düz göster
                st.markdown(f"""
                <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #f59e0b;">
                    <p style="line-height: 1.6; color: #fafafa; margin: 0;">{emotion_analysis}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Duygu analizi bulunamadı veya yapılamadı")
    
    with tab4:
        # İstatistikler
        st.markdown("#### 📊 Metin İstatistikleri")
        
        # İstatistik hesaplamaları
        sentences = len([s for s in transcript_text.split('.') if s.strip()])
        paragraphs = len([p for p in transcript_text.split('\n\n') if p.strip()])
        avg_words_per_sentence = word_count / max(sentences, 1)
        
        # 2 kolonlu istatistik gösterimi
        stat_col1, stat_col2 = st.columns(2)
        
        with stat_col1:
            st.metric("📝 Cümle Sayısı", f"{sentences:,}")
            st.metric("📄 Paragraf Sayısı", f"{paragraphs:,}")
            
        with stat_col2:
            st.metric("📏 Ortalama Kelime/Cümle", f"{avg_words_per_sentence:.1f}")
            reading_time = word_count / 200  # Ortalama okuma hızı 200 kelime/dk
            st.metric("📖 Okuma Süresi", f"{reading_time:.1f} dakika")
        
        # Kelime frekansı analizi (basit)
        if word_count > 10:
            st.markdown("##### 🔤 En Sık Kullanılan Kelimeler")
            words = transcript_text.lower().split()
            # Stopwords'ları filtrele (basit Türkçe stopwords)
            stopwords = {'ve', 'bir', 'bu', 'da', 'de', 'ile', 'için', 'olan', 'olarak', 'var', 'yok', 'gibi', 'kadar', 'daha', 'çok', 'az', 'ya', 'ya da', 'ama', 'fakat', 'ancak', 'lakin', 'hem', 'ise', 'eğer', 'şayet'}
            filtered_words = [w for w in words if len(w) > 3 and w not in stopwords]
            
            from collections import Counter
            word_freq = Counter(filtered_words).most_common(5)
            
            if word_freq:
                freq_cols = st.columns(min(len(word_freq), 5))
                for i, (word, count) in enumerate(word_freq):
                    with freq_cols[i]:
                        st.metric(f"🏷️ {word}", f"{count}x")
    
    with tab5:
        # İçerik analizi
        st.markdown("#### 🎯 İçerik Analizi")
        
        # Sentiment skoru (eğer varsa)
        sentiment_score = ai_analysis.get('sentiment_score', None)
        if sentiment_score is not None:
            score_color = _get_sentiment_color(sentiment_score)
            st.markdown(f"""
            <div style="background: {score_color}; padding: 1rem; border-radius: 8px; text-align: center;">
                <h4 style="color: white; margin: 0;">Genel Sentiment Skoru: {sentiment_score:.2f}</h4>
            </div>
            """, unsafe_allow_html=True)
        
        # İçerik kategorisi (eğer analiz edilmişse)
        content_category = ai_analysis.get('content_category', 'Bilinmiyor')
        language_detected = ai_analysis.get('language_detected', 'Bilinmiyor')
        
        category_col1, category_col2 = st.columns(2)
        with category_col1:
            st.info(f"🏷️ **İçerik Kategorisi:** {content_category}")
        with category_col2:
            st.info(f"🌍 **Tespit Edilen Dil:** {language_detected}")
        
        # Kalite değerlendirmesi
        quality_metrics = ai_analysis.get('quality_metrics', {})
        if quality_metrics:
            st.markdown("##### 🎯 Kalite Değerlendirmesi")
            
            clarity = quality_metrics.get('clarity', 'Bilinmiyor')
            completeness = quality_metrics.get('completeness', 'Bilinmiyor')
            coherence = quality_metrics.get('coherence', 'Bilinmiyor')
            
            quality_col1, quality_col2, quality_col3 = st.columns(3)
            with quality_col1:
                st.metric("🔍 Netlik", clarity)
            with quality_col2:
                st.metric("✅ Tamlık", completeness)
            with quality_col3:
                st.metric("🔗 Tutarlılık", coherence)
    
    # Orjinal analiz fonksiyonunu da çağır (tam uyumluluk için)
    st.markdown("---")
    st.markdown("### 🔧 Detaylı Analiz Raporu")
    create_ai_analysis_display(ai_analysis, transcript_text)


def _get_emotion_color(emotion: str) -> str:
    """Duyguya göre renk döndürür"""
    emotion_colors = {
        'Pozitif': 'linear-gradient(135deg, #10b981, #047857)',
        'Negatif': 'linear-gradient(135deg, #ef4444, #dc2626)',
        'Nötr': 'linear-gradient(135deg, #6b7280, #4b5563)',
        'Mutlu': 'linear-gradient(135deg, #f59e0b, #d97706)',
        'Üzgün': 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
        'Öfkeli': 'linear-gradient(135deg, #ef4444, #991b1b)',
        'Heyecanlı': 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
        'Sakin': 'linear-gradient(135deg, #06b6d4, #0891b2)',
    }
    return emotion_colors.get(emotion, 'linear-gradient(135deg, #6b7280, #4b5563)')


def _get_sentiment_color(score: float) -> str:
    """Sentiment skoruna göre renk döndürür"""
    if score >= 0.5:
        return 'linear-gradient(135deg, #10b981, #047857)'  # Pozitif - yeşil
    elif score <= -0.5:
        return 'linear-gradient(135deg, #ef4444, #dc2626)'  # Negatif - kırmızı
    else:
        return 'linear-gradient(135deg, #f59e0b, #d97706)'  # Nötr - turuncuessing_time,
    analyze_text_with_ai, create_ai_analysis_display, TranscriptionProcessor,
    MemoryManager
)
from database import save_transcription_to_db
from logger_config import transcription_logger


def render_upload_tab(client, transcription_processor):
    """Dosya yükleme tab'ını render eder"""
    
    # Temiz başlık
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <h1 style="color: #4a90e2; font-size: 2.2rem; margin-bottom: 1rem;">
            🎵 {get_text("upload_title")}
        </h1>
        <p style="color: #888; font-size: 1rem; margin-bottom: 0.5rem;">
            {get_text("upload_description")}
        </p>
        <p style="color: #666; font-size: 0.9rem;">
            <strong>{get_text("upload_formats")}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Dosya yükleme alanı
    uploaded_files = st.file_uploader(
        "",  # Boş label - çünkü üstte açıklama var
        type=ALLOWED_FORMATS, 
        accept_multiple_files=True,
        help=get_text("multiple_files_help"),
        label_visibility="collapsed"
    )

    if not uploaded_files:
        # Yükleme alanı boşken bilgi göster
        st.markdown(f"""
        <div style="text-align: center; padding: 3rem; background: #1a1d23; border-radius: 12px; margin: 2rem 0;">
            <h3 style="color: #4a90e2; margin-bottom: 1rem;">📁 {get_text("drag_drop_files")}</h3>
            <p style="color: #888;">
                {get_text("supported_formats")}: MP3, WAV, M4A, MP4, MPEG4<br>
                {get_text("max_file_size")}: {FILE_SIZE_LIMITS["max_file_size"] // (1024*1024)} MB<br>
                {get_text("multiple_files_supported")}
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Dosyalar yüklendiyse işleme başla
    st.markdown(f"""
    <div style="text-align: center; margin: 1.5rem 0;">
        <h3 style="color: #4a90e2;">📊 {len(uploaded_files)} {get_text("files_uploaded")}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Her dosyayı işle
    for i, uploaded_file in enumerate(uploaded_files):
        _process_single_file(uploaded_file, i, client, transcription_processor)


def _process_single_file(uploaded_file, file_index: int, client, transcription_processor):
    """Tek bir dosyayı işler"""
    
    st.markdown("---")
    
    # Dosya başlığı
    st.markdown(f"### 📄 {uploaded_file.name}")
    
    # Dosya validasyonu
    if not _validate_file(uploaded_file):
        return
    
    # Ses analizi
    file_bytes = uploaded_file.getvalue()
    audio_info = _analyze_audio(uploaded_file.name, file_bytes)
    
    if not audio_info:
        return
    
    # Dosya bilgilerini göster
    _display_file_info(audio_info)
    
    # Transkripsiyon işlemi
    _handle_transcription(uploaded_file, file_index, file_bytes, audio_info, client, transcription_processor)


def _validate_file(uploaded_file) -> bool:
    """Dosya validasyonu"""
    
    # Boyut kontrolü
    if uploaded_file.size > FILE_SIZE_LIMITS["max_file_size"]:
        st.error(f"❌ {uploaded_file.name} {get_text('file_too_large')} "
                f"({FILE_SIZE_LIMITS['max_file_size'] // (1024*1024)} {get_text('mb_limit')})")
        return False
    
    # Format kontrolü
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()[1:]
    if file_extension not in ALLOWED_FORMATS:
        st.error(f"❌ {uploaded_file.name} {get_text('unsupported_format')}")
        return False
    
    return True


def _analyze_audio(file_name: str, file_bytes: bytes) -> Optional[Dict]:
    """Ses dosyası analizi"""
    
    with st.spinner(f"🔍 {file_name} {get_text('analyzing')}..."):
        try:
            return analyze_audio_file(file_bytes, file_name)
        except Exception as e:
            st.error(f"❌ {get_text('audio_analysis_error')}: {str(e)}")
            return None


def _display_file_info(audio_info: Dict):
    """Dosya bilgilerini göster"""
    
    # 4 kolonlu bilgi gösterimi
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        duration_min = audio_info['duration'] / 60
        st.metric("⏱️ Süre", f"{duration_min:.1f} dk")
    
    with col2:
        size_mb = audio_info.get('file_size_bytes', 0) / (1024 * 1024)
        st.metric("📊 Boyut", f"{size_mb:.1f} MB")
    
    with col3:
        sample_rate = audio_info.get('sample_rate', 0)
        st.metric("🎵 Sample Rate", f"{sample_rate} Hz")
    
    with col4:
        channels = "Stereo" if audio_info.get('channels', 1) > 1 else "Mono"
        st.metric("🔊 Kanal", channels)
    
    # Ses kalitesi değerlendirmesi
    db_value = audio_info.get('avg_db', -50)
    if db_value > -12:
        quality = f"🟢 {get_text('quality_high')} ({db_value:.1f} dBFS)"
    elif db_value > -20:
        quality = f"🟡 {get_text('quality_medium')} ({db_value:.1f} dBFS)"
    else:
        quality = f"🔴 {get_text('quality_low')} ({db_value:.1f} dBFS)"
    
    st.info(f"**{get_text('audio_quality')}:** {quality}")
    
    # Tahmini işlem süresi
    duration_minutes = audio_info['duration'] / 60  # saniyeyi dakikaya çevir
    estimated_time = estimate_processing_time(duration_minutes)
    st.info(f"**{get_text('estimated_processing_time')}:** {estimated_time}")


def _handle_transcription(uploaded_file, file_index: int, file_bytes: bytes, 
                         audio_info: Dict, client, transcription_processor):
    """Transkripsiyon işlemini yönetir"""
    
    # Processing kontrolü
    processing_key = f"processing_{file_index}"
    
    if st.session_state.get(processing_key, False):
        st.warning(f"⏳ {uploaded_file.name} işleniyor...")
        return
    
    # İşlem butonu
    if st.button(f"🚀 {uploaded_file.name} {get_text('start_transcription')}", 
                key=f"process_btn_{file_index}",
                type="primary",
                use_container_width=True):
        
        st.session_state[processing_key] = True
        _perform_transcription(uploaded_file, file_index, file_bytes, audio_info, client, transcription_processor)


def _perform_transcription(uploaded_file, file_index: int, file_bytes: bytes,
                          audio_info: Dict, client, transcription_processor):
    """Gerçek transkripsiyon işlemi"""
    
    try:
        # Sidebar'dan ayarları al
        language_code = st.session_state.get('selected_language_code', None)
        response_format = st.session_state.get('response_format', 'text')
        enable_ai_analysis = st.session_state.get('enable_ai_analysis', True)
        ai_model = st.session_state.get('ai_model', 'gpt-4-turbo')
        
        # Progress placeholders
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(message: str, percent: float):
                progress_bar.progress(percent / 100.0)
                status_text.info(f"🔄 {message}")
            
            # Transkripsiyon
            status_text.info("🎵 Transkripsiyon başlıyor...")
            result = transcription_processor.process_audio_file(
                file_bytes, 
                uploaded_file.name, 
                language_code,
                response_format,
                progress_callback
            )
            
            if not result or not result.get('transcript'):
                st.error(f"❌ {uploaded_file.name} {get_text('transcription_failed')}")
                return
            
            transcript_text = result['transcript']
            
            # AI Analiz
            ai_analysis = None
            if enable_ai_analysis and transcript_text.strip():
                status_text.info("🤖 AI analiz yapılıyor...")
                progress_bar.progress(0.85)
                
                try:
                    ai_analysis = analyze_text_with_ai(
                        transcript_text, 
                        client,
                        audio_info.get('duration', 0),
                        ai_model
                    )
                except Exception as e:
                    st.warning(f"⚠️ AI analiz hatası: {str(e)}")
            
            # Veritabanına kaydet
            status_text.info("💾 Veritabanına kaydediliyor...")
            progress_bar.progress(0.95)
            
            transcription_id = save_transcription_to_db(
                uploaded_file.name,
                file_bytes,
                audio_info,
                language_code or 'auto',
                response_format,
                transcript_text,
                ai_analysis
            )
            
            # Tamamlandı
            progress_bar.progress(1.0)
            status_text.success(f"✅ {uploaded_file.name} başarıyla işlendi!")
            
            # Session state'e sonuçları kaydet - DOWNLOAD'da korunması için
            if transcription_id:
                result_key = f"transcript_result_{transcription_id}"
                st.session_state[result_key] = {
                    'transcript_text': transcript_text,
                    'ai_analysis': ai_analysis,
                    'transcription_id': transcription_id,
                    'file_name': uploaded_file.name,
                    'audio_info': audio_info,
                    'processing_complete': True,
                    'timestamp': time.time()
                }
            
            # Sonuçları göster
            if transcription_id:
                _display_results(uploaded_file, transcript_text, ai_analysis, transcription_id, audio_info)
            else:
                st.error("❌ Veritabanına kayıt başarısız oldu")
    
    except Exception as e:
        st.error(f"❌ {get_text('processing_error')}: {str(e)}")
        transcription_logger.error(f"Transcription error for {uploaded_file.name}: {e}")
    
    finally:
        # Processing flagini temizle
        if f"processing_{file_index}" in st.session_state:
            del st.session_state[f"processing_{file_index}"]
        
        # Bellek temizliği
        MemoryManager.smart_cleanup_after_processing()


def _display_results(uploaded_file, transcript_text: str, ai_analysis: Optional[Dict],
                    transcription_id: int, audio_info: Dict):
    """Sonuçları göster"""
    
    st.markdown("---")
    
    # Transkripsiyon sonucu
    st.markdown(f"### 📝 {uploaded_file.name} - {get_text('transcription_result_header')}")
    
    with st.container():
        st.markdown(f"""
        <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; border-left: 4px solid #4a90e2;">
            <p style="line-height: 1.6; color: #fafafa; margin: 0;">{transcript_text}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # AI Analiz sonuçları (eğer varsa)
    if ai_analysis:
        st.markdown("---")
        st.markdown(f"### 🤖 {get_text('ai_analysis_results')}")
        
        # Detaylı AI analiz gösterimi
        _display_detailed_ai_analysis(ai_analysis, transcript_text)
    
    # Export seçenekleri
    st.markdown("---")
    _display_export_options(uploaded_file, transcript_text, ai_analysis, transcription_id, audio_info)


def _display_export_options(uploaded_file, transcript_text: str, ai_analysis: Optional[Dict],
                           transcription_id: int, audio_info: Dict):
    """Export seçeneklerini göster"""
    
    st.markdown(f"### 📤 {get_text('export_sharing_options')}")
    
    # Hızlı indirme seçenekleri
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Metin indirme - session state korunarak
        download_key = f"download_txt_{transcription_id}_{int(time.time())}"
        st.download_button(
            "💾 Metin İndir",
            data=transcript_text,
            file_name=f"{uploaded_file.name}_transcript.txt",
            mime="text/plain",
            key=download_key,
            use_container_width=True,
            help="📝 Sadece transkripsiyon metnini indir"
        )
    
    with col2:
        # JSON indirme (AI analiz ile birlikte) - session state korunarak
        if ai_analysis:
            export_data = {
                "file_name": uploaded_file.name,
                "transcript": transcript_text,
                "ai_analysis": ai_analysis,
                "audio_info": audio_info,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_key = f"download_json_{transcription_id}_{int(time.time())}"
            st.download_button(
                "📊 Detaylı JSON İndir",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"{uploaded_file.name}_full_analysis.json",
                mime="application/json",
                key=json_key,
                use_container_width=True,
                help="🤖 AI analiz sonuçları ile birlikte tam rapor"
            )
        else:
            # Sadece transkripsiyon JSON'u
            simple_data = {
                "file_name": uploaded_file.name,
                "transcript": transcript_text,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_key = f"download_simple_json_{transcription_id}_{int(time.time())}"
            st.download_button(
                "📄 Basit JSON İndir",
                data=json.dumps(simple_data, ensure_ascii=False, indent=2),
                file_name=f"{uploaded_file.name}_transcript.json",
                mime="application/json",
                key=json_key,
                use_container_width=True,
                help="📝 Sadece transkripsiyon verisi"
            )
    
    with col3:
        # Gelişmiş export seçenekleri için session state'e kaydet
        advanced_export_key = f"advanced_export_{transcription_id}_{int(time.time())}"
        if st.button("� Gelişmiş Export", key=advanced_export_key, use_container_width=True):
            # Session state'e export verisini kaydet - KALICI OLARAK
            export_session_key = f"export_data_{transcription_id}"
            st.session_state[export_session_key] = {
                'result_text': transcript_text,
                'ai_analysis': ai_analysis,
                'transcription_id': transcription_id,
                'file_name': uploaded_file.name,
                'audio_info': audio_info,
                'language': st.session_state.get('selected_language_code', 'auto'),
                'duration_seconds': audio_info.get('duration', 0),
                'file_size': audio_info.get('file_size_bytes', 0),
                'created_timestamp': time.time(),
                'export_ready': True
            }
            
            st.success("✅ Export verisi hazırlandı! Diğer sekmelerden de erişebilirsiniz.")
            st.info("💡 Bu veri session süresince korunacak - sayfa yenilenmelerinde kaybolmaz.")
            
            # Ekspander ile gelişmiş seçenekleri göster
            with st.expander("🎯 Mevcut Gelişmiş Export Seçenekleri", expanded=True):
                st.markdown("""
                **📤 Export Türleri:**
                - 📄 **PDF Rapor**: Formatlanmış PDF dökümanı
                - 📝 **Word Dökümanı**: Düzenlenebilir Word dosyası  
                - 📊 **Excel Tablosu**: Analiz verilerini içeren Excel
                - 🎯 **QR Kod**: Hızlı paylaşım için QR kod
                - 📦 **ZIP Arşivi**: Tüm dosyaları içeren arşiv
                - 📧 **E-posta**: Doğrudan e-posta gönderimi
                
                **💾 Nasıl Kullanılır:**
                1. "🚀 Gelişmiş Export" butonuna tıklayın  
                2. Diğer sekmelerde export seçenekleri aktif olur
                3. İstediğiniz formatta indirin
                """)
                
                # Mevcut export verilerini göster
                export_keys = [k for k in st.session_state.keys() if isinstance(k, str) and k.startswith('export_data_')]
                if export_keys:
                    st.markdown(f"**� Hazır Export Verileri:** {len(export_keys)} adet")
                    for key in export_keys[-3:]:  # Son 3 tanesini göster
                        data = st.session_state[key]
                        st.caption(f"• {data.get('file_name', 'Unknown')} - ID: {data.get('transcription_id', 'N/A')}")
                
            st.info("�💡 Bu bölümde PDF, Word, Excel, ZIP ve QR kod seçenekleri bulunabilir.")
            st.markdown("**🔧 Yakında:** Detaylı export modülü entegrasyonu")


# CSS stilleri - sadece bu modül için
def apply_upload_tab_styles():
    """Upload tab için özel CSS stilleri"""
    st.markdown("""
    <style>
        /* Upload specific styles */
        .upload-file-container {
            background: #1a1d23;
            border: 2px dashed #4a90e2;
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            margin: 1rem 0;
            transition: all 0.3s ease;
        }
        
        .upload-file-container:hover {
            border-color: #f59e0b;
            background: #2d3748;
        }
        
        .file-info-card {
            background: #1a1d23;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 3px solid #4a90e2;
        }
        
        .result-card {
            background: #1a1d23;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid #4a90e2;
        }
    </style>
    """, unsafe_allow_html=True)
