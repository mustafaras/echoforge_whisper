"""
Basit YouTube Transkripsiyon Modülü
Karmaşık olmayan, düz çalışan sistem
"""
import os
import tempfile
import streamlit as st
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import uuid
import time

# Akıllı loglama sistemi
from logger_config import youtube_logger, setup_logging

# Config import for multilingual support
from config import get_text

# Loglama sistemini başlat
setup_logging()

def extract_youtube_id(url):
    """YouTube URL'sinden video ID'sini çıkarır"""
    try:
        if 'youtube.com/watch' in url:
            parsed_url = urlparse(url)
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[-1].split('?')[0]
        elif 'youtube.com/embed/' in url:
            return url.split('embed/')[-1].split('?')[0]
        return None
    except:
        return None

def validate_youtube_url(url):
    """YouTube URL'sinin geçerli olup olmadığını kontrol eder"""
    video_id = extract_youtube_id(url)
    if not video_id:
        return False, "Geçerli bir YouTube URL'si değil"
    
    if len(video_id) != 11:
        return False, "YouTube video ID formatı hatalı"
    
    return True, video_id

def download_youtube_audio(url):
    """YouTube videosunu çoklu yöntemle indirir - rate limiting ve hata yönetimi ile"""
    video_id = extract_youtube_id(url)
    output_path = tempfile.mkdtemp()
    
    youtube_logger.start(f"YouTube video indirme başladı: {video_id}")
    
    # Rate limiting kontrolü için bekleme
    import time
    import random
    
    # Rastgele bekleme (1-3 saniye) - rate limiting önlemi
    wait_time = random.uniform(1, 3)
    youtube_logger.info(f"Rate limiting önlemi: {wait_time:.1f}s bekleniyor")
    time.sleep(wait_time)
    
    # Yöntem 1: yt-dlp (en stabil)
    try:
        youtube_logger.progress(1, 3, "yt-dlp yöntemi deneniyor (önerilen)...")
        import yt_dlp
        
        output_template = os.path.join(output_path, f'youtube_audio_{video_id}.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best[height<=480]',  # Düşük kalite, hızlı indirme
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extractaudio': True,
            'audioformat': 'm4a',
            'retries': 3,
            'fragment_retries': 3,
            'extractor_retries': 3,
            'sleep_interval': 2,  # 2 saniye bekleme
            'max_sleep_interval': 5,  # Maksimum 5 saniye
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
                
                # Dosyayı bul
                for ext in ['m4a', 'mp4', 'webm', 'mp3']:
                    potential_file = os.path.join(output_path, f'youtube_audio_{video_id}.{ext}')
                    if os.path.exists(potential_file) and os.path.getsize(potential_file) > 0:
                        youtube_logger.success("yt-dlp ile indirme başarılı")
                        st.success("✅ yt-dlp ile başarılı")
                        return potential_file, None
                
                raise Exception("yt-dlp: Dosya bulunamadı")
                
            except Exception as ydl_error:
                error_msg = str(ydl_error)
                if "rate-limited" in error_msg.lower() or "rate limit" in error_msg.lower():
                    youtube_logger.warning("YouTube rate limiting tespit edildi")
                    raise Exception("YouTube rate limiting: 1 saat bekleyin veya farklı ağ deneyin")
                elif "unavailable" in error_msg.lower() or "private" in error_msg.lower():
                    youtube_logger.warning("Video erişilemez durumda")
                    raise Exception("Video özel, silinmiş veya coğrafi kısıtlamalı")
                else:
                    raise ydl_error
            
    except Exception as e:
        error_msg = str(e)
        youtube_logger.warning(f"yt-dlp hatası: {error_msg[:100]}...")
        st.warning(f"❌ yt-dlp hatası: {error_msg[:150]}...")
        
        # Rate limiting hatası özel mesajı
        if "rate-limited" in error_msg.lower() or "rate limit" in error_msg.lower():
            st.error("🚫 YouTube rate limiting aktif!")
            st.info("""
            **🛠️ Çözüm önerileri:**
            1. **1 saat bekleyin** ve tekrar deneyin
            2. **Farklı internet bağlantısı** kullanın (mobil veri, VPN)
            3. **Manuel indirme:** Video → MP3 olarak indirin → "Dosya Yükle" sekmesini kullanın
            4. **Daha sonra** tekrar deneyin (YouTube limitleri geçicidir)
            """)
            return None, "YouTube rate limiting: Lütfen 1 saat bekleyin veya manuel indirme yapın"
    
    # Yöntem 2: pytube3 (yedek)
    try:
        youtube_logger.progress(2, 3, "pytube3 yöntemi deneniyor (yedek)...")
        from pytube import YouTube
        
        # Bekleme ekle
        time.sleep(random.uniform(2, 4))
        
        yt = YouTube(url)
        
        if yt.length > 7200:  # 2 saat
            youtube_logger.warning(f"Video çok uzun: {yt.length//60} dakika")
            return None, f"Video çok uzun ({yt.length//60} dakika). Maksimum 2 saat."
        
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        if not audio_stream:
            raise Exception("Pytube3: Ses stream bulunamadı")
        
        output_filename = f'youtube_audio_{video_id}.mp4'
        output_file = os.path.join(output_path, output_filename)
        
        audio_stream.download(output_path=output_path, filename=output_filename)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            youtube_logger.success("pytube3 ile indirme başarılı")
            st.info("✅ pytube3 ile başarılı")
            return output_file, None
        else:
            raise Exception("Pytube3: Dosya indirilemedi")
            
    except Exception as e:
        error_msg = str(e)
        youtube_logger.warning(f"pytube3 hatası: {error_msg[:50]}...")
        st.warning(f"❌ pytube3 hatası: {error_msg[:100]}...")
    
    # Yöntem 3: youtube-dl (son çare)
    try:
        youtube_logger.progress(3, 3, "youtube-dl yöntemi deneniyor (son çare)...")
        import youtube_dl
        
        # Daha uzun bekleme
        time.sleep(random.uniform(3, 6))
        
        output_template = os.path.join(output_path, f'youtube_audio_{video_id}.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best[height<=360]',  # Çok düşük kalite
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extractaudio': True,
            'audioformat': 'mp3',
            'socket_timeout': 30,
            'retries': 2,
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            # Dosyayı bul
            for ext in ['mp3', 'm4a', 'mp4', 'webm']:
                potential_file = os.path.join(output_path, f'youtube_audio_{video_id}.{ext}')
                if os.path.exists(potential_file) and os.path.getsize(potential_file) > 0:
                    youtube_logger.success("youtube-dl ile indirme başarılı")
                    print("✅ youtube-dl ile başarılı")
                    return potential_file, None
                    
            raise Exception("youtube-dl: Dosya bulunamadı")
            
    except Exception as e:
        youtube_logger.error(f"youtube-dl hatası: {str(e)[:50]}...")
        print(f"❌ youtube-dl hatası: {str(e)}")
    
    # Tüm yöntemler başarısız
    youtube_logger.error("Tüm indirme yöntemleri başarısız")
    
    return None, """❌ YouTube video indirme başarısız oldu.

🔧 **ÇÖZÜM ÖNERİLERİ:**

**🚫 Rate Limiting Sorunu:**
- YouTube 1 saatlik rate limit uygulamış
- Farklı internet bağlantısı deneyin (mobil veri, VPN)
- 1-2 saat bekleyip tekrar deneyin

**📱 Manuel İndirme:**
1. Video → MP3 olarak manuel indirin
2. "📁 Dosya Yükle" sekmesini kullanın
3. İndirdiğiniz MP3'ü buraya yükleyin

**🔄 Alternatif Çözümler:**
- Farklı YouTube video URL'i deneyin
- Video public/erişilebilir olduğundan emin olun
- Video çok yeni ise biraz bekleyin

**⚠️ Video Durumu:**
- Video silinmiş/private olabilir
- Coğrafi kısıtlama olabilir
- Yaş sınırı içerebilir"""

def get_video_info(video_id):
    """Video bilgilerini alır - geliştirilmiş hata yönetimi ile"""
    try:
        youtube_logger.info(f"Video bilgileri alınıyor: {video_id}")
        
        # Kısa bekleme - rate limiting önlemi
        import time
        import random
        time.sleep(random.uniform(0.5, 1.5))
        
        from pytube import YouTube
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(url)
        
        duration_seconds = yt.length or 0
        duration_str = f"{duration_seconds//60}:{duration_seconds%60:02d}" if duration_seconds else "Bilinmiyor"
        
        video_info = {
            'title': yt.title or f'YouTube Video {video_id}',
            'duration': duration_str,
            'duration_seconds': duration_seconds,
            'channel': yt.author or 'Bilinmiyor',
            'views': f"{yt.views:,}" if yt.views else "Bilinmiyor"
        }
        
        youtube_logger.success(f"Video bilgileri alındı: {video_info['title'][:30]}...")
        return video_info
        
    except Exception as e:
        error_msg = str(e)
        youtube_logger.warning(f"Video bilgileri alınamadı: {error_msg[:50]}...")
        
        # Sessiz çalış - sadlece logla, UI'da uyarı gösterme
        youtube_logger.warning(f"Video bilgi hatası: {error_msg[:50]}...")
        
        # Temel bilgilerle devam et
        return {
            'title': f'YouTube Video {video_id}',
            'duration': 'Bilinmiyor',
            'duration_seconds': 0,
            'channel': 'Bilinmiyor',
            'views': 'Bilinmiyor',
            'error': str(e)
        }

def render_youtube_tab():
    """YouTube transkripsiyon sekmesini render eder"""
    st.markdown(f"## {get_text('youtube_transcription')}")
    st.markdown(get_text("youtube_description"))
    
    # Önemli uyarı kutusu
    st.warning(f"""
    **{get_text('youtube_rate_limiting_warning')}**
    {get_text('youtube_rate_limiting_text')}
    """)
    
    # Session state başlatma
    if 'youtube_transcription_result' not in st.session_state:
        st.session_state.youtube_transcription_result = None
    if 'youtube_video_info' not in st.session_state:
        st.session_state.youtube_video_info = None
    
    # Global state'ten son işlenen dosyayı kontrol et
    recent_file_from_other_tabs = None
    if ("last_processed_file" in st.session_state and 
        st.session_state.last_processed_file and 
        st.session_state.last_processed_file.get('tab_source') != 'youtube'):
        recent_file_from_other_tabs = st.session_state.last_processed_file
    
    # Diğer sekmelerden işlenmiş dosya varsa göster
    if recent_file_from_other_tabs:
        st.info("🔥 Diğer sekmelerde yeni işlenmiş dosya mevcut!")
        with st.expander("👁️ Son İşlenen Dosyayı Görüntüle", expanded=False):
            st.markdown(f"**📄 Dosya:** {recent_file_from_other_tabs['file_name']}")
            st.markdown(f"**🌍 Kaynak:** {recent_file_from_other_tabs.get('tab_source', 'unknown').title()}")
            st.markdown(f"**📅 İşlenme:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(recent_file_from_other_tabs['processed_at']))}")
            st.text_area("📝 Transkripsiyon:", recent_file_from_other_tabs['result_text'], height=150, key="other_tab_result")
        st.markdown("---")
    
    # Önceki sonucu göster (varsa)
    if st.session_state.youtube_transcription_result:
        st.success(get_text("past_transcription_results"))
        
        video_info = st.session_state.youtube_video_info
        if video_info:
            st.markdown(f"{get_text('video_title')} {video_info.get('title', 'YouTube Video')}")
            st.markdown(f"{get_text('channel')} {video_info.get('channel', get_text('unknown'))}")
            st.markdown(f"{get_text('duration')} {video_info.get('duration', get_text('unknown'))}")
        
        st.markdown(get_text("transcription_result_title"))
        st.text_area("", st.session_state.youtube_transcription_result, height=300, key="previous_result")
        
        # İndirme butonu
        video_id = extract_youtube_id(st.session_state.get('youtube_last_url', '')) or 'video'
        st.download_button(
            label="📥 Metni İndir",
            data=st.session_state.youtube_transcription_result,
            file_name=f"youtube_transcript_{video_id}.txt",
            mime="text/plain",
            key="download_previous"
        )
        
        # Yeni transkripsiyon için temizle butonu
        col1, col2 = st.columns(2)
        with col1:
            if st.button(get_text("clean_and_new"), type="secondary"):
                st.session_state.youtube_transcription_result = None
                st.session_state.youtube_video_info = None
                st.session_state.youtube_last_url = None
                st.session_state.youtube_last_saved_id = None
                st.rerun()
        
        with col2:
            # Geçmişten silme butonu (eğer kaydedilmişse)
            if st.session_state.get('youtube_last_saved_id'):
                if st.button(get_text("delete_from_history"), type="secondary"):
                    try:
                        from database import db_manager
                        success = db_manager.delete_transcription(st.session_state.youtube_last_saved_id)
                        if success:
                            st.success("✅ Geçmişten silindi")
                            st.session_state.youtube_last_saved_id = None
                        else:
                            st.error("❌ Geçmişten silinirken hata oluştu")
                    except Exception as e:
                        st.error(f"❌ Silme hatası: {str(e)}")
                        
        st.markdown("---")
    
    # URL girişi
    youtube_url = st.text_input(
        "YouTube URL:",
        placeholder="https://www.youtube.com/watch?v=...",
        help="YouTube video linkini buraya yapıştırın"
    )
    
    if youtube_url:
        # URL doğrulama
        is_valid, result = validate_youtube_url(youtube_url)
        
        if is_valid:
            video_id = result
            st.success(f"✅ Geçerli YouTube URL - Video ID: {video_id}")
            
            # Video bilgilerini göster
            video_info = get_video_info(video_id)
            if video_info and not video_info.get('error'):
                st.success(f"📺 Video bulundu: **{video_info['title']}**")
                
                # Video bilgileri
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ Süre", video_info['duration'])
                with col2:
                    st.metric("📺 Kanal", video_info['channel'])
                with col3:
                    st.metric("👁️ Görüntülenme", video_info['views'])
                
                # Süre kontrolü
                duration_seconds = video_info.get('duration_seconds', 0)
                if duration_seconds > 7200:
                    st.error(f"⚠️ Video çok uzun ({duration_seconds//60} dakika). Maksimum 2 saat desteklenir.")
                    return
                elif duration_seconds > 3600:
                    st.warning(f"⚠️ Video uzun ({duration_seconds//60} dakika). İşlem biraz sürebilir.")
            
            # Basit ayarlar
            from config import LANGUAGES
            
            col1, col2 = st.columns(2)
            with col1:
                selected_language = st.selectbox(
                    "🌍 Dil:",
                    list(LANGUAGES.keys()),
                    index=0
                )
                language_code = LANGUAGES[selected_language]
            
            with col2:
                response_format = st.selectbox(
                    "📝 Format:",
                    ["text", "srt", "vtt"],
                    index=0
                )
            
            # İşleme butonu
            if st.button("🚀 YouTube Videosunu İşle", type="primary"):
                if 'youtube_processing' not in st.session_state:
                    st.session_state.youtube_processing = False
                
                if st.session_state.youtube_processing:
                    st.warning("⏳ Video zaten işleniyor...")
                else:
                    st.session_state.youtube_processing = True
                    
                    youtube_logger.start(f"YouTube transkripsiyon başladı: {video_info.get('title', 'Bilinmiyor')[:30]}...")
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # 1. Video indirme
                        youtube_logger.progress(1, 4, "Video indirme aşaması")
                        status_text.info("📥 YouTube videosu indiriliyor...")
                        progress_bar.progress(25)
                        
                        audio_file, error = download_youtube_audio(youtube_url)
                        
                        if error:
                            youtube_logger.error(f"Video indirme hatası: {error[:50]}...")
                            
                            # Özel hata mesajları
                            if "rate limit" in error.lower() or "rate-limited" in error.lower():
                                st.error("🚫 YouTube Rate Limiting Tespit Edildi!")
                                st.info("""
                                **🛠️ Hemen Deneyebilecekleriniz:**
                                1. **VPN veya mobil veri** ile farklı IP adresi deneyin
                                2. **1-2 saat bekleyin** ve tekrar deneyin  
                                3. **Manuel indirme:** Video → MP3 olarak indirin → "📁 Dosya Yükle" sekmesini kullanın
                                
                                **📱 Manuel İndirme Adımları:**
                                - YouTube → Video Url → Online MP3 converter
                                - MP3 dosyasını bilgisayarınıza kaydedin
                                - "📁 Dosya Yükle" sekmesinde MP3'ü yükleyin
                                """)
                                st.markdown("---")
                                st.markdown("**💡 Online MP3 Converter Önerileri:** youtube-mp3.org, ytmp3.cc, y2mate.com")
                            else:
                                st.error(f"❌ İndirme hatası: {error}")
                            
                            st.session_state.youtube_processing = False
                            return
                        
                        # 2. Transkripsiyon
                        youtube_logger.progress(2, 4, "OpenAI Whisper transkripsiyon")
                        status_text.info("🧠 Transkripsiyon işleniyor...")
                        progress_bar.progress(50)
                        
                        from config import OPENAI_API_KEY
                        from openai import OpenAI
                        client = OpenAI(api_key=OPENAI_API_KEY)
                        
                        # Dosya boyutunu logla
                        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
                        youtube_logger.info(f"Ses dosyası boyutu: {file_size_mb:.1f} MB")
                        
                        # Basit API çağrısı
                        with open(audio_file, "rb") as f:
                            if language_code:
                                transcript = client.audio.transcriptions.create(
                                    model="whisper-1",
                                    file=f,
                                    language=language_code,
                                    response_format=response_format
                                )
                            else:
                                transcript = client.audio.transcriptions.create(
                                    model="whisper-1",
                                    file=f,
                                    response_format=response_format
                                )
                        
                        # Sonucu al
                        if hasattr(transcript, 'text'):
                            result_text = transcript.text
                        else:
                            result_text = str(transcript)
                        
                        youtube_logger.success(f"Transkripsiyon tamamlandı: {len(result_text)} karakter")
                        
                        # 3. Veritabanı kaydetme
                        youtube_logger.progress(3, 4, "Veritabanına kaydetme")
                        progress_bar.progress(75)
                        
                        # Geçici dosyayı temizle
                        try:
                            if os.path.exists(audio_file):
                                os.unlink(audio_file)
                                youtube_logger.info("Geçici dosya temizlendi")
                        except:
                            pass
                        
                        # Session state'e kaydet
                        st.session_state.youtube_transcription_result = result_text
                        st.session_state.youtube_video_info = video_info
                        st.session_state.youtube_last_url = youtube_url
                        st.session_state.youtube_selected_language = selected_language
                        
                        # Global erişim için en son işlenen dosya bilgilerini sakla
                        st.session_state["last_processed_file"] = {
                            "result_text": result_text,
                            "ai_analysis": None,  # YouTube'da AI analiz yok
                            "transcription_id": None,  # Henüz yok, sonra eklenecek
                            "file_name": f"{video_info.get('title', 'YouTube Video')}.mp3",
                            "language_code": language_code,
                            "audio_info": {
                                "duration": video_info.get('duration_seconds', 0),
                                "duration_str": video_info.get('duration', 'Unknown'),
                                "source": "youtube"
                            },
                            "processed_at": time.time(),
                            "tab_source": "youtube",
                            "video_info": video_info,
                            "youtube_url": youtube_url
                        }
                        
                        # Tüm işlenmiş dosyaları bir listede tut
                        if "processed_files_list" not in st.session_state:
                            st.session_state.processed_files_list = []
                        
                        # Yeni dosyayı listeye ekle
                        st.session_state.processed_files_list.append({
                            "result_text": result_text,
                            "ai_analysis": None,
                            "transcription_id": None,
                            "file_name": f"{video_info.get('title', 'YouTube Video')}.mp3",
                            "language_code": language_code,
                            "audio_info": {
                                "duration": video_info.get('duration_seconds', 0),
                                "duration_str": video_info.get('duration', 'Unknown'),
                                "source": "youtube"
                            },
                            "processed_at": time.time(),
                            "tab_source": "youtube",
                            "video_info": video_info,
                            "youtube_url": youtube_url
                        })
                        
                        # Veritabanına otomatik kaydet
                        try:
                            from database import save_youtube_transcription
                            transcription_id = save_youtube_transcription(
                                video_url=youtube_url,
                                video_info=video_info,
                                transcript_text=result_text,
                                language=selected_language,
                                format_type=response_format
                            )
                            if transcription_id:
                                st.session_state.youtube_last_saved_id = transcription_id
                                youtube_logger.success(f"Veritabanına kaydedildi: ID {transcription_id}")
                                st.info(f"✅ Transkripsiyon geçmişe kaydedildi (ID: {transcription_id})")
                            else:
                                youtube_logger.warning("Veritabanı kaydetme başarısız")
                                st.warning("⚠️ Geçmişe kaydetme başarısız oldu")
                        except Exception as db_error:
                            youtube_logger.error(f"Veritabanı hatası: {str(db_error)[:50]}...")
                            st.warning(f"⚠️ Geçmişe kaydetme hatası: {str(db_error)}")
                        
                        # 4. Tamamlama
                        youtube_logger.progress(4, 4, "İşlem tamamlanıyor")
                        progress_bar.progress(100)
                        status_text.success("✅ İşlem tamamlandı!")
                        
                        youtube_logger.success("YouTube transkripsiyon süreci başarıyla tamamlandı")
                        
                        # Sonucu göster
                        st.success("🎉 Transkripsiyon tamamlandı!")
                        
                        st.markdown(f"### 🎬 {video_info.get('title', 'YouTube Video')}")
                        st.markdown(f"**Kanal:** {video_info.get('channel', 'Bilinmiyor')}")
                        st.markdown(f"**Süre:** {video_info.get('duration', 'Bilinmiyor')}")
                        st.markdown(f"**Dil:** {selected_language}")
                        
                        st.markdown("### 📝 Transkripsiyon Sonucu")
                        st.text_area("", result_text, height=300, key="current_result")
                        
                        # İndirme butonu
                        st.download_button(
                            label="📥 Metni İndir",
                            data=result_text,
                            file_name=f"youtube_transcript_{video_id}.txt",
                            mime="text/plain",
                            key="download_current"
                        )
                        
                    except Exception as e:
                        error_msg = str(e)
                        youtube_logger.error(f"Genel hata: {error_msg}")
                        
                        # Hata türüne göre özel mesajlar
                        if "rate limit" in error_msg.lower() or "429" in error_msg:
                            st.error("🚫 API Rate Limiting")
                            st.info("⏰ 5-10 dakika bekleyip tekrar deneyin")
                        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                            st.error("🌐 İnternet Bağlantı Sorunu")
                            st.info("🔄 İnternet bağlantınızı kontrol edin")
                        elif "timeout" in error_msg.lower():
                            st.error("⏱️ İşlem Zaman Aşımı")
                            st.info("🔄 Tekrar deneyin veya daha küçük video kullanın")
                        else:
                            st.error(f"❌ Beklenmeyen hata: {error_msg}")
                            
                        # Her durumda manuel indirme önerisi
                        with st.expander("🛠️ Alternatif Çözüm: Manuel İndirme"):
                            st.markdown("""
                            **📱 Hızlı Çözüm:**
                            1. YouTube video → Online MP3 converter kullanın
                            2. İndirilen MP3 dosyasını "📁 Dosya Yükle" sekmesine yükleyin
                            3. Normal transkripsiyon işlemi yapın
                            
                            **🌐 Önerilen siteler:** youtube-mp3.org, ytmp3.cc, y2mate.com
                            """)
                    
                    finally:
                        st.session_state.youtube_processing = False
        
        else:
            st.error(f"❌ {result}")
            st.markdown("""
            ### 📝 Desteklenen URL Formatları:
            - `https://www.youtube.com/watch?v=VIDEO_ID`
            - `https://youtu.be/VIDEO_ID`
            - `https://www.youtube.com/embed/VIDEO_ID`
            
            ### 🛠️ URL Sorunları Çözümleri:
            **🔗 URL Kontrolleri:**
            - Video URL'sinin doğru kopyalandığından emin olun
            - Video hala erişilebilir durumda olduğunu kontrol edin
            - Video private/gizli olmadığından emin olun
            
            **🔄 Alternatif Yöntemler:**
            - Videoyu tarayıcıda açıp URL'yi tekrar kopyalayın  
            - Farklı bir YouTube videosu deneyin
            - Video → MP3 manuel indirme yapın → "📁 Dosya Yükle" kullanın
            """)
            
            # Manuel indirme rehberi
            with st.expander("📱 Manuel İndirme Rehberi"):
                st.markdown("""
                **Adım 1:** YouTube videosunu tarayıcıda açın
                **Adım 2:** Video URL'sini online MP3 converter'a yapıştırın  
                **Adım 3:** MP3 olarak indirin
                **Adım 4:** İndirilen dosyayı "📁 Dosya Yükle" sekmesine yükleyin
                
                **🌐 Önerilen Siteler:** youtube-mp3.org, ytmp3.cc, y2mate.com
                """)
    
    else:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; color: #666;">
            <h3>🎬 {get_text('waiting_youtube_url')}</h3>
            <p>{get_text('paste_youtube_link')}</p>
        </div>
        """, unsafe_allow_html=True)
