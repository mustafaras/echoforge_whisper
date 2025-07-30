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
from datetime import datetime
from pathlib import Path

from config import (
    ALLOWED_FORMATS, FILE_SIZE_LIMITS, LANGUAGES, RESPONSE_FORMATS,
    get_text, get_current_language
)
from utils import (
    analyze_audio_file, create_waveform_plot, estimate_processing_time,
    analyze_text_with_ai, TranscriptionProcessor, MemoryManager
)
from database import save_transcription_to_db
from logger_config import transcription_logger


def _create_pdf_report(uploaded_file, transcript_text: str, ai_analysis: Optional[Dict], 
                      transcription_id: int, audio_info: Dict) -> Optional[str]:
    """AI analiz sonuçlarını otomatik PDF raporu olarak oluşturur ve kaydeder - Modern Tasarım"""
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
                                      PageBreak, KeepTogether, Image)
        from reportlab.lib import colors
        from reportlab.lib.units import cm, inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.graphics.shapes import Drawing, Rect
        from reportlab.graphics import renderPDF
        
        # PDF dosya yolu oluştur - "data" klasörü
        pdf_dir = Path("data")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name_clean = "".join(c for c in uploaded_file.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        pdf_path = pdf_dir / f"{file_name_clean}_{timestamp}_Premium_AI_Report.pdf"
        
        # PDF dökümanı oluştur - Modern margin'ler
        doc = SimpleDocTemplate(
            str(pdf_path), 
            pagesize=A4, 
            topMargin=1.5*cm, 
            bottomMargin=1.5*cm,
            leftMargin=2*cm,
            rightMargin=2*cm
        )
        
        # Unicode ve Türkçe karakter desteği için gelişmiş font yönetimi
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'
        
        try:
            # Unicode destekli fontları dene
            import os
            
            # Windows sistem fontları
            windows_fonts = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/calibri.ttf', 
                'C:/Windows/Fonts/tahoma.ttf'
            ]
            
            unicode_font_registered = False
            for font_path in windows_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
                        font_name = 'UnicodeFont'
                        unicode_font_registered = True
                        break
                    except:
                        continue
            
            if not unicode_font_registered:
                # Fallback: Built-in fonts ile Unicode karakterleri
                font_name = 'Helvetica'
                
        except Exception as e:
            transcription_logger.warning(f"Font registration error: {e}")
            font_name = 'Helvetica'
        
        # Modern stil tanımlamaları - Premium tasarım
        styles = getSampleStyleSheet()
        
        # Başlık stilleri - Gradient efekti için renk paleti
        title_style = ParagraphStyle(
            'PremiumTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=40,
            textColor=colors.HexColor('#1a365d'),  # Koyu mavi
            alignment=1,  # Center
            fontName=font_name,
            leading=30
        )
        
        subtitle_style = ParagraphStyle(
            'PremiumSubtitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceBefore=25,
            spaceAfter=15,
            textColor=colors.HexColor('#2b77ad'),  # Orta mavi
            fontName=font_name,
            leading=22
        )
        
        heading_style = ParagraphStyle(
            'PremiumHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2563eb'),  # Parlak mavi
            fontName=font_name,
            leading=18
        )
        
        normal_style = ParagraphStyle(
            'PremiumNormal',
            parent=styles['Normal'],
            fontSize=11,
            fontName=font_name,
            textColor=colors.HexColor('#1f2937'),  # Koyu gri
            leading=16,
            spaceAfter=6
        )
        
        # Highlighted text için özel stil
        highlight_style = ParagraphStyle(
            'PremiumHighlight',
            parent=normal_style,
            backColor=colors.HexColor('#f0f9ff'),  # Açık mavi background
            borderColor=colors.HexColor('#3b82f6'),
            borderWidth=1,
            borderPadding=8
        )
        
        # Türkçe karakter işleme fonksiyonu - Gelişmiş
        def safe_text(text, preserve_structure=True):
            """Türkçe karakterleri güvenli şekilde işler"""
            if not text:
                return "Metin bulunamadı"
            
            # Unicode normalizasyon dene
            try:
                import unicodedata
                normalized = unicodedata.normalize('NFC', str(text))
                
                # Eğer Unicode font kayıtlıysa, direkt kullan
                if 'UnicodeFont' in font_name:
                    return normalized
                
                # Değilse, güvenli karakterlere çevir
                turkish_map = {
                    'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G',
                    'ı': 'i', 'I': 'I', 'İ': 'I', 'i': 'i',
                    'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S',
                    'ü': 'u', 'Ü': 'U'
                }
                
                if preserve_structure:
                    # Yapıyı koruyarak çevir
                    result = normalized
                    for tr_char, en_char in turkish_map.items():
                        result = result.replace(tr_char, en_char)
                    return result
                else:
                    # ASCII'ye zorla çevir
                    return normalized.encode('ascii', 'ignore').decode('ascii')
                    
            except Exception as e:
                transcription_logger.warning(f"Text processing error: {e}")
                return str(text).encode('ascii', 'ignore').decode('ascii')
        
        content = []
        
        # PREMIUM BAŞLIK - Modern tasarım
        content.append(Spacer(1, 10))
        
        # Ana başlık
        title_text = safe_text("🤖 WhisperAI Premium Analiz Raporu")
        content.append(Paragraph(title_text, title_style))
        
        # Alt başlık - Dosya ismi
        subtitle_text = safe_text(f"📄 {uploaded_file.name}")
        content.append(Paragraph(subtitle_text, subtitle_style))
        content.append(Spacer(1, 25))
        
        # Premium header çizgisi
        content.append(Spacer(1, 10))
        
        # DOSYA BİLGİLERİ - Modern card tasarımı
        content.append(Paragraph(safe_text("📋 Dosya Bilgileri ve Teknik Detaylar"), heading_style))
        
        # Dosya bilgileri tablosu - Premium stil
        current_time = datetime.now()
        file_info_data = [
            ["📁 Dosya Adi", safe_text(uploaded_file.name)],
            ["📅 Tarih", current_time.strftime("%d/%m/%Y")],
            ["⏰ Saat", current_time.strftime("%H:%M:%S")],
            ["🆔 Rapor ID", f"#{transcription_id:06d}"],
            ["💻 Sistem", "WhisperAI Premium v2.0"]
        ]
        
        if audio_info:
            duration_min = audio_info.get('duration', 0) / 60
            size_mb = audio_info.get('file_size_bytes', 0) / (1024 * 1024)
            file_info_data.extend([
                ["🎵 Ses Suresi", f"{duration_min:.1f} dakika"],
                ["📊 Dosya Boyutu", f"{size_mb:.1f} MB"],
                ["🔊 Sample Rate", f"{audio_info.get('sample_rate', 0):,} Hz"],
                ["📻 Kanal", "Stereo" if audio_info.get('channels', 1) > 1 else "Mono"],
                ["📈 Ortalama dB", f"{audio_info.get('avg_db', -50):.1f} dBFS"]
            ])
        
        # Premium tablo tasarımı
        file_table = Table(file_info_data, colWidths=[5*cm, 11*cm])
        file_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3b82f6')),  # Mavi header
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), font_bold if 'UnicodeFont' not in font_name else font_name),
            ('FONTSIZE', (0, 0), (0, -1), 11),
            
            # Data style
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f8fafc')),  # Açık gri
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1f2937')),
            ('FONTNAME', (1, 0), (1, -1), font_name),
            ('FONTSIZE', (1, 0), (1, -1), 10),
            
            # Genel stil
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            
            # Sınırlar
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('ROUNDEDCORNERS', [5, 5, 5, 5]),
        ]))
        content.append(file_table)
        content.append(Spacer(1, 25))
        
        # TRANSKRİPSİYON METNİ - Premium tasarım
        content.append(Paragraph(safe_text("📝 Transkripsiyon Metni"), heading_style))
        
        # Metin uzunluğuna göre sayfa bölme
        safe_transcript = safe_text(transcript_text, preserve_structure=True)
        if not safe_transcript.strip():
            safe_transcript = safe_text("⚠️ Transkripsiyon metni işlenirken hata oluştu. Türkçe karakterler nedeniyle metin gösterilemiyor.")
        
        # Paragraf stilleme - highlight box
        transcript_content = Paragraph(safe_transcript, highlight_style)
        content.append(KeepTogether([transcript_content]))
        content.append(Spacer(1, 25))
        
        # AI ANALİZ SONUÇLARI - Premium dashboard tasarımı
        if ai_analysis:
            content.append(Paragraph(safe_text("🤖 Premium AI Analiz Dashboard"), heading_style))
            
            # İstatistikler kartı
            text_stats = ai_analysis.get('text_statistics', {})
            if text_stats:
                content.append(Paragraph(safe_text("📊 Metin İstatistikleri"), subtitle_style))
                
                stats_data = [
                    ["📝 Kelime Sayısı", f"{text_stats.get('word_count', 0):,}"],
                    ["🔤 Karakter Sayısı", f"{text_stats.get('character_count', 0):,}"],
                    ["📄 Cümle Sayısı", f"{text_stats.get('sentence_count', 0):,}"],
                    ["🗣️ Konuşma Hızı", f"{text_stats.get('words_per_minute', 0):.0f} kelime/dakika"],
                    ["⚖️ Ortalama Kelime/Cümle", f"{text_stats.get('average_words_per_sentence', 0):.1f}"],
                    ["📚 Okuma Süresi", f"{text_stats.get('reading_time_minutes', 0):.1f} dakika"]
                ]
                
                # Premium istatistik tablosu
                stats_table = Table(stats_data, colWidths=[7*cm, 9*cm])
                stats_table.setStyle(TableStyle([
                    # Gradient header
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#1e40af')),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                    ('FONTNAME', (0, 0), (0, -1), font_bold if 'UnicodeFont' not in font_name else font_name),
                    ('FONTSIZE', (0, 0), (0, -1), 11),
                    
                    # Alternating row colors
                    ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.HexColor('#f1f5f9'), colors.HexColor('#e2e8f0')]),
                    ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1f2937')),
                    ('FONTNAME', (1, 0), (1, -1), font_name),
                    ('FONTSIZE', (1, 0), (1, -1), 10),
                    
                    # Styling
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
                    ('TOPPADDING', (0, 0), (-1, -1), 14),
                    ('LEFTPADDING', (0, 0), (-1, -1), 18),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1'))
                ]))
                content.append(stats_table)
                content.append(Spacer(1, 20))
            
            # Anahtar kelimeler - Premium chip tasarımı
            keywords = ai_analysis.get('keywords', [])
            if keywords:
                content.append(Paragraph(safe_text("🏷️ Anahtar Kelimeler"), subtitle_style))
                
                # Safe keywords işleme
                safe_keywords = []
                for keyword in keywords[:15]:
                    safe_keyword = safe_text(str(keyword), preserve_structure=True)
                    if safe_keyword.strip():
                        safe_keywords.append(safe_keyword)
                
                if safe_keywords:
                    keywords_text = " • ".join(safe_keywords)
                    keyword_paragraph = Paragraph(keywords_text, normal_style)
                    content.append(keyword_paragraph)
                else:
                    content.append(Paragraph(safe_text("⚠️ Anahtar kelimeler işlenirken hata oluştu."), normal_style))
                
                content.append(Spacer(1, 20))
            
            # Duygu analizi - Modern card
            emotion_analysis = ai_analysis.get('emotion_analysis', '')
            if emotion_analysis and emotion_analysis != "Duygusal analiz yapılamadı":
                content.append(Paragraph(safe_text("💭 Duygu Analizi"), subtitle_style))
                safe_emotion = safe_text(str(emotion_analysis), preserve_structure=True)
                emotion_paragraph = Paragraph(safe_emotion, highlight_style)
                content.append(emotion_paragraph)
                content.append(Spacer(1, 20))
            
            # Özet - Premium format
            summary = ai_analysis.get('summary', '')
            if summary and summary != 'Özet bulunamadı':
                content.append(Paragraph(safe_text("📄 İçerik Özeti"), subtitle_style))
                safe_summary = safe_text(str(summary), preserve_structure=True)
                summary_paragraph = Paragraph(safe_summary, highlight_style)
                content.append(summary_paragraph)
                content.append(Spacer(1, 20))
            
            # Ana konular - Premium liste
            topics = ai_analysis.get('topics', [])
            if topics:
                content.append(Paragraph(safe_text("🎯 Ana Konular"), subtitle_style))
                safe_topics = []
                for topic in topics:
                    safe_topic = safe_text(str(topic), preserve_structure=True)
                    if safe_topic.strip():
                        safe_topics.append(safe_topic)
                
                if safe_topics:
                    topics_text = " | ".join(safe_topics)
                    topics_paragraph = Paragraph(topics_text, normal_style)
                    content.append(topics_paragraph)
                
                content.append(Spacer(1, 20))
            
            # En sık kullanılan kelimeler - Premium dashboard
            word_freq_data = ai_analysis.get('word_frequency', {})
            most_common = word_freq_data.get('most_common_words', [])
            if most_common:
                content.append(Paragraph(safe_text("🔥 En Sık Kullanılan Kelimeler"), subtitle_style))
                
                freq_data = [["🏆 Sıra", "📝 Kelime", "🔢 Kullanım", "📊 Oran"]]
                word_count = text_stats.get('word_count', 1)
                
                for i, (word, count) in enumerate(most_common[:10], 1):
                    percentage = (count / word_count) * 100 if word_count > 0 else 0
                    safe_word = safe_text(str(word), preserve_structure=True)
                    if safe_word.strip():
                        freq_data.append([
                            f"#{i}", 
                            safe_word, 
                            f"{count}x", 
                            f"%{percentage:.1f}"
                        ])
                
                # Premium frekans tablosu
                if len(freq_data) > 1:  # Header + en az 1 data row
                    freq_table = Table(freq_data, colWidths=[2*cm, 5*cm, 3*cm, 3*cm])
                    freq_table.setStyle(TableStyle([
                        # Premium header
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),  # Yeşil header
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), font_bold if 'UnicodeFont' not in font_name else font_name),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        
                        # Data rows - zebra striping
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
                        ('FONTNAME', (0, 1), (-1, -1), font_name),
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Sıra numarası
                        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Kelime
                        ('ALIGN', (2, 1), (-1, -1), 'CENTER'), # Kullanım ve oran
                        
                        # Styling
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                        ('TOPPADDING', (0, 0), (-1, -1), 12),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                        
                        # Rounded corners effect
                        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                    ]))
                    content.append(freq_table)
                    content.append(Spacer(1, 25))
        
        # PREMIUM FOOTER - Modern branding
        content.append(Spacer(1, 40))
        content.append(PageBreak())  # Yeni sayfa footer için
        
        # Footer card
        footer_info = [
            ["🕒 Rapor Tarihi", current_time.strftime("%d/%m/%Y %H:%M:%S")],
            ["⚙️ AI Engine", "OpenAI Whisper + GPT-4 Turbo"],
            ["🏢 Platform", "WhisperAI Multilingual Premium"],
            ["📋 Rapor Versiyonu", "v2.0 - Turkish Enhanced"],
            ["🔐 Güvenlik", "End-to-End Encrypted Processing"]
        ]
        
        footer_table = Table(footer_info, colWidths=[4*cm, 12*cm])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#6366f1')),  # Indigo
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f9fafb')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
        ]))
        content.append(footer_table)
        
        # Signature
        signature_text = safe_text("© 2025 WhisperAI Premium - Türkçe Dil Desteği Aktif")
        signature_para = Paragraph(signature_text, normal_style)
        content.append(Spacer(1, 15))
        content.append(signature_para)
        
        # PDF'i oluştur - Premium kalite
        try:
            doc.build(content)
            transcription_logger.info(f"Premium PDF report created successfully: {pdf_path}")
            return str(pdf_path)
        except Exception as build_error:
            transcription_logger.error(f"PDF build error: {build_error}")
            # Fallback: Basit PDF oluştur
            try:
                simple_content = [
                    Paragraph(safe_text("WhisperAI Transcription Report", preserve_structure=False), title_style),
                    Spacer(1, 20),
                    Paragraph(safe_text(f"File: {uploaded_file.name}", preserve_structure=False), normal_style),
                    Spacer(1, 10),
                    Paragraph(safe_text("Transcript:", preserve_structure=False), heading_style),
                    Paragraph(safe_text(transcript_text, preserve_structure=False), normal_style)
                ]
                doc.build(simple_content)
                return str(pdf_path)
            except Exception as fallback_error:
                transcription_logger.error(f"Fallback PDF creation also failed: {fallback_error}")
                return None
    
    except ImportError as import_err:
        transcription_logger.warning(f"ReportLab not installed: {import_err}")
        return None
    except Exception as e:
        transcription_logger.error(f"PDF creation error: {e}")
        return None


def _install_reportlab_if_needed():
    """ReportLab kütüphanesini kontrol eder, yoksa kullanıcıyı uyarır"""
    try:
        import reportlab
        return True
    except ImportError:
        st.warning("⚠️ PDF raporu oluşturmak için ReportLab kütüphanesi gerekli. Yüklemek için: `pip install reportlab`")
        return False


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
            
            # AI Analiz - EN DETAYLI HALI
            ai_analysis = None
            if enable_ai_analysis and transcript_text.strip():
                status_text.info("🤖 Detaylı AI analiz yapılıyor (duygu, anahtar kelimeler, konu analizi)...")
                progress_bar.progress(0.85)
                
                try:
                    ai_analysis = analyze_text_with_ai(
                        transcript_text, 
                        client,
                        audio_info.get('duration', 0),
                        ai_model
                    )
                    
                    # AI analiz sonucunu zenginleştir
                    if ai_analysis:
                        ai_analysis = _enhance_ai_analysis(ai_analysis, transcript_text, audio_info)
                        
                except Exception as e:
                    st.warning(f"⚠️ AI analiz hatası: {str(e)}")
                    transcription_logger.error(f"AI analysis error: {e}")
            
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
                ai_analysis or {}
            )
            
            # Tamamlandı
            progress_bar.progress(1.0)
            status_text.success(f"✅ {uploaded_file.name} başarıyla işlendi!")
            
            # Session state'e minimal bilgi kaydet - sadece ID
            if transcription_id:
                # Sadece gerekli bilgiyi kaydet - session state şişmemesi için
                st.session_state[f"completed_{transcription_id}"] = {
                    'file_name': uploaded_file.name,
                    'completed_at': datetime.now().strftime("%H:%M:%S"),
                    'has_ai_analysis': bool(ai_analysis)
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


def _enhance_ai_analysis(ai_analysis: Dict, transcript_text: str, audio_info: Dict) -> Dict:
    """AI analiz sonucunu ek verilerle zenginleştir"""
    
    try:
        # Temel metin istatistikleri ekle
        words = transcript_text.split()
        word_count = len(words)
        char_count = len(transcript_text)
        sentences = len([s for s in transcript_text.split('.') if s.strip()])
        
        # Ses verisi ile bağlantı kur
        duration_seconds = audio_info.get('duration', 0)
        duration_minutes = duration_seconds / 60 if duration_seconds > 0 else 0
        
        # Konuşma hızı hesapla
        words_per_minute = word_count / duration_minutes if duration_minutes > 0 else 0
        
        # Ek metrikleri AI analizine ekle
        ai_analysis.update({
            'text_statistics': {
                'word_count': word_count,
                'character_count': char_count,
                'sentence_count': sentences,
                'average_words_per_sentence': word_count / max(sentences, 1),
                'words_per_minute': words_per_minute,
                'reading_time_minutes': word_count / 200  # Ortalama okuma hızı
            },
            'audio_metadata': {
                'duration_seconds': duration_seconds,
                'duration_minutes': duration_minutes,
                'file_size_mb': audio_info.get('file_size_bytes', 0) / (1024 * 1024),
                'sample_rate': audio_info.get('sample_rate', 0),
                'channels': audio_info.get('channels', 1),
                'avg_db': audio_info.get('avg_db', -50)
            },
            'content_quality': {
                'speech_rate': 'Normal' if 120 <= words_per_minute <= 180 else 
                              'Hızlı' if words_per_minute > 180 else 'Yavaş',
                'audio_quality': 'Yüksek' if audio_info.get('avg_db', -50) > -12 else
                                'Orta' if audio_info.get('avg_db', -50) > -20 else 'Düşük'
            }
        })
        
        # Kelime frekansı analizi
        if word_count > 10:
            # Temel Türkçe stopwords
            stopwords = {
                've', 'bir', 'bu', 'da', 'de', 'ile', 'için', 'olan', 'olarak', 
                'var', 'yok', 'gibi', 'kadar', 'daha', 'çok', 'az', 'ya', 'ya da', 
                'ama', 'fakat', 'ancak', 'lakin', 'hem', 'ise', 'eğer', 'şayet',
                'ki', 'mi', 'mı', 'mu', 'mü', 'ne', 'nasıl', 'neden', 'niçin',
                'ben', 'sen', 'o', 'biz', 'siz', 'onlar', 'bu', 'şu', 'o'
            }
            
            # Kelimeleri temizle ve filtrele
            clean_words = []
            for word in words:
                clean_word = word.lower().strip('.,!?;:"()[]{}')
                if len(clean_word) > 2 and clean_word not in stopwords:
                    clean_words.append(clean_word)
            
            # En sık kullanılan kelimeleri bul
            word_freq = Counter(clean_words).most_common(10)
            
            ai_analysis['word_frequency'] = {
                'most_common_words': word_freq,
                'unique_word_count': len(set(clean_words)),
                'vocabulary_richness': len(set(clean_words)) / max(len(clean_words), 1)
            }
    
    except Exception as e:
        transcription_logger.warning(f"Enhancement error: {e}")
    
    return ai_analysis


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
    
    # AI Analiz sonuçları (eğer varsa) - DETAYLI VERSIYON
    if ai_analysis:
        st.markdown("---")
        st.markdown(f"### 🤖 {get_text('ai_analysis_results')}")
        
        # Detaylı AI analiz gösterimi
        _display_detailed_ai_analysis(ai_analysis, transcript_text)
    
    # Export seçenekleri
    st.markdown("---")
    _display_export_options(uploaded_file, transcript_text, ai_analysis, transcription_id, audio_info)


def _display_detailed_ai_analysis(ai_analysis: Dict[str, Any], transcript_text: str):
    """DETAYLI AI ANALİZ SONUÇLARINI GÖSTERIR - TÜM ÖZELLİKLERİ KULLANIR"""
    
    if not ai_analysis:
        st.warning("⚠️ AI analiz verisi bulunamadı")
        return
    
    # HİZ METRIKLER OVERVIEW
    st.markdown("#### ⚡ Hızlı Bakış")
    quick_col1, quick_col2, quick_col3, quick_col4, quick_col5 = st.columns(5)
    
    # Temel metrikleri al
    text_stats = ai_analysis.get('text_statistics', {})
    audio_meta = ai_analysis.get('audio_metadata', {})
    content_quality = ai_analysis.get('content_quality', {})
    
    with quick_col1:
        word_count = text_stats.get('word_count', len(transcript_text.split()))
        st.metric("📝 Kelime", f"{word_count:,}")
    
    with quick_col2:
        duration_min = audio_meta.get('duration_minutes', 0)
        st.metric("⏱️ Süre", f"{duration_min:.1f}dk")
    
    with quick_col3:
        wpm = text_stats.get('words_per_minute', 0)
        if wpm > 0:
            st.metric("🗣️ Konuşma Hızı", f"{wpm:.0f} kel/dk")
        else:
            st.metric("🗣️ Konuşma Hızı", "N/A")
    
    with quick_col4:
        # Ana duyguyu çıkar
        emotion = ai_analysis.get('emotion_analysis', 'Bilinmiyor')
        if isinstance(emotion, str) and emotion != "Duygusal analiz yapılamadı":
            try:
                import json
                if emotion.strip().startswith('{'):
                    emotion_data = json.loads(emotion)
                    main_emotion = emotion_data.get('Ana Duygu', 'Bilinmiyor')
                else:
                    main_emotion = emotion.split()[0] if emotion else 'Bilinmiyor'
            except:
                main_emotion = 'Bilinmiyor'
        else:
            main_emotion = 'Bilinmiyor'
        
        st.metric("💭 Duygu", main_emotion)
    
    with quick_col5:
        # Ses kalitesi
        audio_quality = content_quality.get('audio_quality', 'Bilinmiyor')
        quality_color = "🟢" if audio_quality == "Yüksek" else "🟡" if audio_quality == "Orta" else "🔴"
        st.metric("🎵 Ses Kalitesi", f"{quality_color} {audio_quality}")
    
    # DETAYLI ANALIZ TABLARI
    st.markdown("---")
    
    # Tab'lı detaylı görünüm
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 İstatistikler", 
        "🏷️ Anahtar Kelimeler", 
        "💭 Duygu Analizi",
        "📋 Özet & Konular",
        "🎵 Ses Analizi",
        "📈 Kelime Analizi"
    ])
    
    with tab1:
        # DETAYLI İSTATİSTİKLER
        st.markdown("#### 📊 Detaylı Metin İstatistikleri")
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        
        with stat_col1:
            st.markdown("**📝 Metin Yapısı**")
            char_count = text_stats.get('character_count', len(transcript_text))
            sentence_count = text_stats.get('sentence_count', len([s for s in transcript_text.split('.') if s.strip()]))
            avg_words_per_sentence = text_stats.get('average_words_per_sentence', 0)
            
            st.write(f"• **Karakter Sayısı:** {char_count:,}")
            st.write(f"• **Cümle Sayısı:** {sentence_count:,}")
            st.write(f"• **Ortalama Kelime/Cümle:** {avg_words_per_sentence:.1f}")
            
        with stat_col2:
            st.markdown("**⏱️ Zaman Analizi**")
            reading_time = text_stats.get('reading_time_minutes', word_count / 200)
            
            st.write(f"• **Okuma Süresi:** {reading_time:.1f} dakika")
            st.write(f"• **Konuşma Süresi:** {duration_min:.1f} dakika")
            if duration_min > 0:
                efficiency = reading_time / duration_min
                st.write(f"• **Verimlilik Oranı:** {efficiency:.2f}x")
        
        with stat_col3:
            st.markdown("**🎯 Kalite Metrikleri**")
            speech_rate = content_quality.get('speech_rate', 'Bilinmiyor')
            
            # Kelime zenginliği
            word_freq_data = ai_analysis.get('word_frequency', {})
            vocab_richness = word_freq_data.get('vocabulary_richness', 0)
            unique_words = word_freq_data.get('unique_word_count', 0)
            
            st.write(f"• **Konuşma Hızı:** {speech_rate}")
            st.write(f"• **Benzersiz Kelime:** {unique_words:,}")
            st.write(f"• **Kelime Zenginliği:** {vocab_richness:.2%}")
    
    with tab2:
        # ANAHTAR KELİMELER VE KELİME FREKANSI
        st.markdown("#### 🏷️ Anahtar Kelimeler ve Kelime Analizi")
        
        # AI'dan gelen anahtar kelimeler
        keywords = ai_analysis.get('keywords', [])
        if keywords:
            st.markdown("**🎯 AI Tespit Ettiği Anahtar Kelimeler**")
            
            # Anahtar kelimeleri güzel chip'ler halinde göster - tek seferde
            if keywords:
                st.markdown("**🎯 AI Tespit Ettiği Anahtar Kelimeler**")
                
                # Kolayca okunabilir chip gösterimi
                keywords_html = '<div style="background: #1a1d23; padding: 1rem; border-radius: 10px; border-left: 4px solid #4a90e2;">'
                
                for i, keyword in enumerate(keywords[:15]):  # İlk 15 anahtar kelime
                    # Renkli gradient'ler
                    colors = [
                        'linear-gradient(135deg, #4a90e2, #667eea)',
                        'linear-gradient(135deg, #10b981, #34d399)', 
                        'linear-gradient(135deg, #f59e0b, #fbbf24)',
                        'linear-gradient(135deg, #ef4444, #f87171)',
                        'linear-gradient(135deg, #8b5cf6, #a78bfa)',
                        'linear-gradient(135deg, #f97316, #fb923c)',
                        'linear-gradient(135deg, #06b6d4, #22d3ee)',
                        'linear-gradient(135deg, #84cc16, #a3e635)'
                    ]
                    color = colors[i % len(colors)]
                    
                    keywords_html += f'''
                    <span style="display: inline-block; background: {color}; 
                                 color: white; padding: 6px 12px; margin: 3px; 
                                 border-radius: 15px; font-size: 0.85rem; font-weight: 500;
                                 box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        {keyword}
                    </span>'''
                
                keywords_html += '</div>'
                
                st.markdown(keywords_html, unsafe_allow_html=True)
                
                # Fazla kelime varsa bilgi göster
                if len(keywords) > 15:
                    st.info(f"💡 Toplam {len(keywords)} anahtar kelime bulundu. İlk 15 tanesi gösteriliyor.")
            else:
                st.warning("⚠️ Anahtar kelime bulunamadı")
        
        # Kelime frekansı analizi
        st.markdown("---")
        word_freq_data = ai_analysis.get('word_frequency', {})
        most_common = word_freq_data.get('most_common_words', [])
        
        if most_common:
            st.markdown("**📊 En Sık Kullanılan Kelimeler**")
            
            freq_col1, freq_col2 = st.columns(2)
            
            with freq_col1:
                # İlk 5 kelime
                for i, (word, count) in enumerate(most_common[:5]):
                    percentage = (count / word_count) * 100 if word_count > 0 else 0
                    st.metric(
                        label=f"🏷️ {word}",
                        value=f"{count}x",
                        delta=f"{percentage:.1f}%"
                    )
            
            with freq_col2:
                # Kelime frekansı grafiği için basit gösterim
                st.markdown("**📈 Kullanım Sıklığı**")
                for word, count in most_common[:5]:
                    progress_value = count / most_common[0][1] if most_common else 0
                    st.progress(progress_value, text=f"{word}: {count}x")
    
    with tab3:
        # DUYGU ANALİZİ
        st.markdown("#### 💭 Detaylı Duygu Analizi")
        
        emotion_analysis = ai_analysis.get('emotion_analysis', '')
        if emotion_analysis and emotion_analysis != "Duygusal analiz yapılamadı":
            try:
                # JSON formatında geliyorsa parse et
                if emotion_analysis.strip().startswith('{'):
                    import json
                    emotion_data = json.loads(emotion_analysis)
                    
                    # Ana duygu ve detaylar
                    main_emotion = emotion_data.get('Ana Duygu', 'Bilinmiyor')
                    confidence = emotion_data.get('Güven', '0%')
                    tone = emotion_data.get('Ton', 'Bilinmiyor')
                    
                    # Görsel duygu gösterimi
                    emotion_color = _get_emotion_color(main_emotion)
                    confidence_num = int(confidence.replace('%', '')) if '%' in confidence else 0
                    
                    emo_col1, emo_col2 = st.columns([2, 1])
                    
                    with emo_col1:
                        st.markdown(f"""
                        <div style="background: {emotion_color}; padding: 2rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                            <h2 style="color: white; margin-bottom: 1rem;">😊 {main_emotion}</h2>
                            <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                                <p style="color: white; margin: 0; font-size: 1.1rem;"><strong>Güven Oranı:</strong> {confidence}</p>
                                <p style="color: white; margin: 0.5rem 0 0 0; font-size: 1.1rem;"><strong>Genel Ton:</strong> {tone}</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with emo_col2:
                        st.markdown("**🎯 Duygu Metrikleri**")
                        st.metric("📊 Güven Seviyesi", f"{confidence_num}%")
                        st.progress(confidence_num / 100, text=f"Güven: {confidence}")
                        
                        # Duygu kategorisi
                        if confidence_num >= 80:
                            certainty = "🟢 Çok Yüksek"
                        elif confidence_num >= 60:
                            certainty = "🟡 Yüksek"
                        elif confidence_num >= 40:
                            certainty = "🟠 Orta"
                        else:
                            certainty = "🔴 Düşük"
                        
                        st.write(f"**Kesinlik:** {certainty}")
                        
                        # Sentiment skoru varsa göster
                        sentiment_score = ai_analysis.get('sentiment_score', None)
                        if sentiment_score is not None:
                            st.metric("📈 Sentiment Skoru", f"{sentiment_score:.2f}")
                
                else:
                    # Düz metin formatında
                    st.markdown(f"""
                    <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #f59e0b;">
                        <h4 style="color: #f59e0b; margin-bottom: 1rem;">💭 Duygu Analizi</h4>
                        <p style="line-height: 1.6; color: #fafafa; margin: 0;">{emotion_analysis}</p>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Duygu analizi parse hatası: {e}")
                st.text(emotion_analysis)
        else:
            st.warning("⚠️ Duygu analizi bulunamadı veya yapılamadı")
    
    with tab4:
        # ÖZET VE KONULAR
        st.markdown("#### 📋 İçerik Özeti ve Konu Analizi")
        
        # Özet gösterimi
        summary = ai_analysis.get('summary', 'Özet bulunamadı')
        st.markdown(f"""
        <div style="background: #1a1d23; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #10b981;">
            <h4 style="color: #10b981; margin-bottom: 1rem;">📄 İçerik Özeti</h4>
            <p style="line-height: 1.8; color: #fafafa; margin: 0; font-size: 1.1rem;">{summary}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Ana konular
        topics = ai_analysis.get('topics', [])
        if topics:
            st.markdown("#### 🎯 Ana Konular")
            
            # Konuları grid halinde göster
            topic_cols = st.columns(min(len(topics), 3))
            for i, topic in enumerate(topics):
                with topic_cols[i % 3]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                               padding: 1.5rem; border-radius: 10px; text-align: center; 
                               margin: 0.5rem 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">{topic}</h4>
                    </div>
                    """, unsafe_allow_html=True)
        
        # İçerik kategorisi
        content_category = ai_analysis.get('content_category', 'Bilinmiyor')
        language_detected = ai_analysis.get('language_detected', 'Bilinmiyor')
        
        cat_col1, cat_col2 = st.columns(2)
        with cat_col1:
            st.info(f"🏷️ **İçerik Kategorisi:** {content_category}")
        with cat_col2:
            st.info(f"🌍 **Tespit Edilen Dil:** {language_detected}")
    
    with tab5:
        # SES ANALİZİ
        st.markdown("#### 🎵 Ses Kalitesi ve Teknik Analiz")
        
        audio_col1, audio_col2, audio_col3 = st.columns(3)
        
        with audio_col1:
            st.markdown("**🔊 Ses Özellikleri**")
            sample_rate = audio_meta.get('sample_rate', 0)
            channels = audio_meta.get('channels', 1)
            file_size_mb = audio_meta.get('file_size_mb', 0)
            
            st.write(f"• **Sample Rate:** {sample_rate:,} Hz")
            st.write(f"• **Kanallar:** {channels} ({'Stereo' if channels > 1 else 'Mono'})")
            st.write(f"• **Dosya Boyutu:** {file_size_mb:.1f} MB")
        
        with audio_col2:
            st.markdown("**📊 Ses Kalitesi**")
            avg_db = audio_meta.get('avg_db', -50)
            audio_quality = content_quality.get('audio_quality', 'Bilinmiyor')
            
            # dB değerine göre kalite göstergesi
            if avg_db > -12:
                db_color = "🟢"
                db_desc = "Mükemmel"
            elif avg_db > -20:
                db_color = "🟡"
                db_desc = "İyi"
            elif avg_db > -30:
                db_color = "🟠"
                db_desc = "Orta"
            else:
                db_color = "🔴"
                db_desc = "Düşük"
            
            st.write(f"• **Ortalama dB:** {avg_db:.1f} dBFS")
            st.write(f"• **Kalite:** {db_color} {db_desc}")
            st.write(f"• **Genel Değerlendirme:** {audio_quality}")
        
        with audio_col3:
            st.markdown("**⚡ Performans Metrikleri**")
            speech_rate = content_quality.get('speech_rate', 'Bilinmiyor')
            
            # Konuşma hızı değerlendirmesi
            if wpm > 0:
                if wpm < 120:
                    rate_desc = "🐌 Yavaş"
                elif wpm > 180:
                    rate_desc = "🏃 Hızlı"
                else:
                    rate_desc = "👍 Normal"
            else:
                rate_desc = "❓ Bilinmiyor"
            
            st.write(f"• **Konuşma Hızı:** {rate_desc}")
            st.write(f"• **Kelime/Dakika:** {wpm:.0f}" if wpm > 0 else "• **Kelime/Dakika:** N/A")
            st.write(f"• **Değerlendirme:** {speech_rate}")
    
    with tab6:
        # KELİME ANALİZİ VE İSTATİSTİKLER
        st.markdown("#### 📈 Gelişmiş Kelime Analizi")
        
        word_freq_data = ai_analysis.get('word_frequency', {})
        
        if word_freq_data:
            vocab_richness = word_freq_data.get('vocabulary_richness', 0)
            unique_words = word_freq_data.get('unique_word_count', 0)
            most_common = word_freq_data.get('most_common_words', [])
            
            # Kelime zenginliği gösterimi
            vocab_col1, vocab_col2 = st.columns(2)
            
            with vocab_col1:
                st.markdown("**📊 Kelime Zenginliği**")
                st.metric("🏷️ Benzersiz Kelime", f"{unique_words:,}")
                st.metric("📈 Zenginlik Oranı", f"{vocab_richness:.2%}")
                
                # Zenginlik değerlendirmesi
                if vocab_richness > 0.5:
                    richness_desc = "🌟 Çok Zengin"
                elif vocab_richness > 0.3:
                    richness_desc = "👍 Zengin"
                elif vocab_richness > 0.2:
                    richness_desc = "📝 Orta"
                else:
                    richness_desc = "📉 Sınırlı"
                
                st.info(f"**Değerlendirme:** {richness_desc}")
            
            with vocab_col2:
                st.markdown("**🔥 En Popüler Kelimeler**")
                
                # Top 10 kelimeleri tablo halinde
                if most_common:
                    for i, (word, count) in enumerate(most_common[:8], 1):
                        percentage = (count / word_count) * 100 if word_count > 0 else 0
                        st.write(f"{i}. **{word}** - {count}x ({percentage:.1f}%)")
        
        # Kelime uzunluğu analizi
        words = transcript_text.split()
        if words:
            avg_word_length = sum(len(word.strip('.,!?;:"()[]{}')) for word in words) / len(words)
            long_words = len([word for word in words if len(word.strip('.,!?;:"()[]{}')) > 6])
            
            length_col1, length_col2 = st.columns(2)
            
            with length_col1:
                st.markdown("**📏 Kelime Uzunluğu Analizi**")
                st.metric("📐 Ortalama Uzunluk", f"{avg_word_length:.1f} harf")
                st.metric("📚 Uzun Kelime Sayısı", f"{long_words:,}")
            
            with length_col2:
                # Basit kelime uzunluğu dağılımı
                st.markdown("**📊 Uzunluk Dağılımı**")
                short_words = len([w for w in words if len(w.strip('.,!?;:"()[]{}')) <= 4])
                medium_words = len([w for w in words if 5 <= len(w.strip('.,!?;:"()[]{}')) <= 6])
                
                st.write(f"• **Kısa (≤4 harf):** {short_words:,}")
                st.write(f"• **Orta (5-6 harf):** {medium_words:,}")
                st.write(f"• **Uzun (>6 harf):** {long_words:,}")
    
    # Ek bilgi notu (expander kaldırıldı - nested expander hatası nedeniyle)
    st.markdown("---")
    st.info("� **Detaylı AI Analiz:** Yukarıdaki sekmeli görünümde tüm analiz sonuçları bulunmaktadır.")


def _clean_for_json(obj):
    """Nesneyi JSON serializable hale getirir (numpy array'leri vs. temizler)"""
    import numpy as np
    
    if isinstance(obj, dict):
        return {key: _clean_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_clean_for_json(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # numpy array'i listeye çevir
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()  # numpy scalar'ı Python scalar'a çevir
    elif hasattr(obj, 'dtype'):  # Diğer numpy türleri
        return str(obj)
    else:
        return obj


def _auto_save_pdf_report(uploaded_file, transcript_text: str, ai_analysis: Optional[Dict],
                         transcription_id: int, audio_info: Dict):
    """Otomatik PDF raporu oluşturur ve 'data' klasörüne kaydeder - export butonu olmadan"""
    
    st.markdown("---")
    st.markdown("### 📄 Otomatik PDF Raporu")
    
    # ReportLab kontrolü
    if not _install_reportlab_if_needed():
        st.error("❌ PDF raporu oluşturulamadı: ReportLab kütüphanesi bulunamadı")
        return
    
    with st.spinner("🔄 Detaylı AI analiz raporu PDF olarak hazırlanıyor..."):
        try:
            pdf_path = _create_pdf_report(
                uploaded_file, 
                transcript_text, 
                ai_analysis, 
                transcription_id, 
                audio_info
            )
            
            if pdf_path:
                st.success(f"✅ PDF raporu otomatik olarak kaydedildi!")
                
                # PDF bilgileri göster
                pdf_file = Path(pdf_path)
                file_size = pdf_file.stat().st_size / 1024  # KB
                
                # Bilgi kartı - export butonu olmadan
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4a90e2, #667eea); 
                           padding: 2rem; border-radius: 15px; margin: 1rem 0; 
                           box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h3 style="color: white; margin: 0 0 1rem 0; text-align: center;">
                        � PDF Raporu Hazır!
                    </h3>
                    <div style="background: rgba(255,255,255,0.2); padding: 1.5rem; border-radius: 10px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; color: white;">
                            <div style="text-align: center;">
                                <h4 style="margin: 0; font-size: 2rem;">📄</h4>
                                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">PDF Boyutu</p>
                                <p style="margin: 0; font-weight: bold;">{file_size:.1f} KB</p>
                            </div>
                            <div style="text-align: center;">
                                <h4 style="margin: 0; font-size: 2rem;">📂</h4>
                                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Kayıt Konumu</p>
                                <p style="margin: 0; font-weight: bold;">data/</p>
                            </div>
                            <div style="text-align: center;">
                                <h4 style="margin: 0; font-size: 2rem;">⏰</h4>
                                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Oluşturma Zamanı</p>
                                <p style="margin: 0; font-weight: bold;">{datetime.now().strftime("%H:%M:%S")}</p>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Dosya yolu bilgisi
                st.info(f"""
                **📁 Dosya Yolu:** `{pdf_path}`
                
                **📋 İçerik:**
                • Dosya bilgileri ve teknik detaylar  
                • Tam transkripsiyon metni
                • Detaylı AI analiz sonuçları
                • İstatistiksel veriler ve tablolar
                • Anahtar kelimeler ve duygu analizi
                • Türkçe karakter uyumlu format
                """)
                
                # Başarı mesajı
                st.balloons()
                
            else:
                st.error("❌ PDF raporu oluşturulamadı")
                
        except Exception as e:
            st.error(f"❌ PDF oluşturma hatası: {str(e)}")
            transcription_logger.error(f"Auto PDF creation error: {e}")
    
    # Ek bilgi - export butonu yok
    st.markdown("---")
    st.info("""
    🤖 **Otomatik PDF Kaydetme Sistemi:**
    
    • **Tam Otomatik:** Her transkripsiyon işleminden sonra otomatik oluşturulur
    • **Kayıt Konumu:** Proje klasöründe `data/` dizini
    • **Türkçe Destek:** Türkçe karakterler uyumlu format
    • **Detaylı İçerik:** AI analizi, istatistikler, tablolar
    • **Benzersiz İsim:** Tarih-saat damgası ile çakışma önlenir
    • **Export Butonu Yok:** Otomatik kaydetme, manual export gerekmez
    """)


def _display_export_options(uploaded_file, transcript_text: str, ai_analysis: Optional[Dict],
                           transcription_id: int, audio_info: Dict):
    """Otomatik PDF kaydetme - export seçenekleri tamamen kaldırıldı"""
    
    # Otomatik PDF raporu oluştur - buton olmadan
    _auto_save_pdf_report(uploaded_file, transcript_text, ai_analysis, transcription_id, audio_info)


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
        'Gergin': 'linear-gradient(135deg, #f97316, #ea580c)',
        'Rahat': 'linear-gradient(135deg, #22c55e, #16a34a)',
    }
    return emotion_colors.get(emotion, 'linear-gradient(135deg, #6b7280, #4b5563)')


def _get_sentiment_color(score: float) -> str:
    """Sentiment skoruna göre renk döndürür"""
    if score >= 0.5:
        return 'linear-gradient(135deg, #10b981, #047857)'  # Pozitif - yeşil
    elif score <= -0.5:
        return 'linear-gradient(135deg, #ef4444, #dc2626)'  # Negatif - kırmızı
    else:
        return 'linear-gradient(135deg, #f59e0b, #d97706)'  # Nötr - turuncu


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
        
        /* Enhanced analysis cards */
        .analysis-card {
            background: linear-gradient(135deg, #1a1d23 0%, #2d3748 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            border: 1px solid rgba(74, 144, 226, 0.3);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #2d3748;
            border-radius: 8px;
            color: #cbd5e0;
            padding: 0.5rem 1rem;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #4a90e2;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
