"""
🌍 Çeviri Modülü
===============
Geçmiş transkripsiyon sonuçlarını farklı dillere çeviren modül
OpenAI GPT modelleri kullanarak yüksek kaliteli çeviri sağlar
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from config import get_text
from openai import OpenAI
from config import OPENAI_API_KEY

# Akıllı loglama sistemi
from logger_config import translation_logger, database_logger, setup_logging

# Loglama sistemini başlat
setup_logging()

# Desteklenen diller (Fransızca hariç, 12 dil)
TRANSLATION_LANGUAGES = {
    "Türkçe": "tr",
    "İngilizce": "en", 
    "Almanca": "de",
    "İspanyolca": "es",
    "İtalyanca": "it",
    "Portekizce": "pt",
    "Rusça": "ru",
    "Japonca": "ja",
    "Korece": "ko",
    "Çince (Basitleştirilmiş)": "zh-CN",
    "Arapça": "ar",
    "Hollandaca": "nl"
}

# OpenAI Modelleri
OPENAI_MODELS = {
    "GPT-4o": "gpt-4o",
    "GPT-4o Mini": "gpt-4o-mini", 
    "GPT-4 Turbo": "gpt-4-turbo",
    "GPT-3.5 Turbo": "gpt-3.5-turbo"
}

def get_transcription_history():
    """Veritabanından transkripsiyon geçmişini alır"""
    try:
        from database import db_manager
        
        # Son 50 transkripsiyon al
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, file_name, transcript_text, language, created_at, metadata
            FROM transcriptions 
            WHERE deleted_at IS NULL 
            AND LENGTH(transcript_text) > 50
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        
        results = cursor.fetchall()
        
        transcriptions = []
        for row in results:
            transcriptions.append({
                'id': row[0],
                'file_name': row[1],
                'transcript_text': row[2],  # TAM metin - çeviride kullanılacak
                'language': row[3],
                'created_at': row[4],
                'preview': row[2][:100] + "..." if len(row[2]) > 100 else row[2]  # Sadece önizleme için
            })
            
        return transcriptions
        
    except Exception as e:
        st.error(f"❌ Geçmiş veriler alınırken hata: {str(e)}")
        return []

def translate_text(text, target_language, model_name):
    """OpenAI kullanarak metni çevirir"""
    try:
        translation_logger.start(f"Çeviri başladı: {model_name} -> {target_language}")
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Dil adını al
        language_name = [k for k, v in TRANSLATION_LANGUAGES.items() if v == target_language][0]
        
        translation_logger.info(f"Hedef dil: {language_name}, Metin uzunluğu: {len(text)} karakter")
        
        # Çeviri prompt'u
        system_prompt = f"""Sen profesyonel bir çevirmensin. Verilen metni {language_name} diline çevir.

ÖNEMLİ KURALLAR:
1. Sadece çeviriyi döndür, başka açıklama yapma
2. Orijinal anlamı ve tonunu koru
3. Doğal ve akıcı çeviri yap
4. Teknik terimler varsa doğru karşılıklarını kullan
5. Kültürel bağlamı dikkate al"""

        user_prompt = f"Bu metni {language_name} diline çevir:\n\n{text}"
        
        translation_logger.info("OpenAI API çağrısı yapılıyor...")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=8000  # Daha büyük limitler için artırıldı
        )
        
        result = response.choices[0].message.content.strip()
        translation_logger.success(f"Çeviri tamamlandı: {len(result)} karakter")
        
        return result
        
    except Exception as e:
        translation_logger.error(f"Çeviri hatası: {str(e)}")
        return f"❌ Çeviri hatası: {str(e)}"

def save_translation_to_history(original_id, original_text, translated_text, target_language, model_used):
    """Çeviri sonucunu geçmişe kaydet"""
    try:
        database_logger.start(f"Çeviri geçmişe kaydediliyor: ID {original_id}")
        
        from database import db_manager
        
        # Çeviri için özel dosya adı oluştur
        language_name = [k for k, v in TRANSLATION_LANGUAGES.items() if v == target_language][0]
        
        # Orijinal transkripsiyon bilgisini al
        original = db_manager.get_transcription_by_id(original_id)
        if original:
            original_file_name = original.get('file_name', 'Bilinmiyor')
            file_name = f"[Çeviri] {original_file_name} → {language_name}"
        else:
            file_name = f"[Çeviri] → {language_name}"
        
        database_logger.info(f"Dosya adı: {file_name}")
        
        # Sahte dosya bytes'ı (çeviri için)
        fake_bytes = translated_text.encode('utf-8')
        
        # Audio info
        audio_info = {
            'source': 'translation',
            'original_transcription_id': original_id,
            'target_language': target_language,
            'model_used': model_used,
            'translation_date': datetime.now().isoformat()
        }
        
        # AI analysis
        ai_analysis = {
            'translation_info': {
                'source_language': 'auto-detected',
                'target_language': language_name,
                'model_used': model_used,
                'original_length': len(original_text),
                'translated_length': len(translated_text)
            }
        }
        
        # Processing info
        processing_info = {
            'type': 'translation',
            'model': model_used,
            'processed_at': datetime.now().isoformat()
        }
        
        # Kaydet
        translation_id = db_manager.save_transcription(
            file_name=file_name,
            file_bytes=fake_bytes,
            audio_info=audio_info,
            language=target_language,
            format_type='text',
            transcript_text=translated_text,
            ai_analysis=ai_analysis,
            processing_info=processing_info
        )
        
        if translation_id:
            database_logger.success(f"Çeviri kaydedildi: ID {translation_id}")
        else:
            database_logger.warning("Çeviri kaydedilemedi")
            
        return translation_id
        
    except Exception as e:
        database_logger.error(f"Çeviri kaydetme hatası: {str(e)}")
        st.error(f"❌ Çeviri kaydedilemedi: {str(e)}")
        return None

def render_translation_tab():
    """Çeviri sekmesini render eder"""
    st.markdown(f"## {get_text('smart_translation')}")
    st.markdown(get_text("translate_past_transcriptions"))
    
    # Session state için çeviri sonucu
    if 'translation_result' not in st.session_state:
        st.session_state.translation_result = None
    if 'translation_info' not in st.session_state:
        st.session_state.translation_info = None
    
    # Önceki çeviri sonucunu göster (varsa)
    if st.session_state.translation_result:
        st.success(get_text("last_translation_result"))
        
        info = st.session_state.translation_info
        if info:
            st.markdown(f"**{get_text('source_file')}** {info['source_file']}")
            st.markdown(f"**{get_text('target_language_label')}** {info['target_language']}")
            st.markdown(f"**{get_text('model_used')}** {info['model_used']}")
            st.markdown(f"**{get_text('character_count')}** {len(info['original_text'])} {get_text('character_arrow')} {len(st.session_state.translation_result)} karakter")
        
        st.markdown(f"### {get_text('translation_result')}")
        st.text_area("", st.session_state.translation_result, height=400, key="previous_translation")
        
        # İndirme butonu
        if info:
            filename = f"translation_{info['target_language']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            st.download_button(
                label=get_text("download_translation"),
                data=st.session_state.translation_result,
                file_name=filename,
                mime="text/plain",
                key="download_translation"
            )
        
        # Temizle butonu
        if st.button(get_text("clear_new_translation"), type="secondary"):
            st.session_state.translation_result = None
            st.session_state.translation_info = None
            st.rerun()
        
        st.markdown("---")
    
    # Geçmiş transkripsiyon listesi
    st.markdown(f"### {get_text('past_transcription_selection')}")
    
    # Önce güncel session state'ten son işlenen dosyaları kontrol et
    recent_files = []
    if "processed_files_list" in st.session_state and st.session_state.processed_files_list:
        recent_files = st.session_state.processed_files_list[-5:]  # Son 5 dosya
        recent_files.reverse()  # En yeniden en eskiye
    
    # Veritabanından geçmiş kayıtları al
    with st.spinner("📚 Geçmiş veriler yükleniyor..."):
        db_transcriptions = get_transcription_history()
    
    # Toplam liste oluştur: Son işlenen dosyalar + DB kayıtları
    all_transcriptions = []
    
    # Önce son işlenen dosyaları ekle
    for i, file_data in enumerate(recent_files):
        all_transcriptions.append({
            'id': f"session_{i}",
            'file_name': file_data['file_name'],
            'transcript_text': file_data['result_text'],
            'created_at': datetime.fromtimestamp(file_data['processed_at']).strftime('%Y-%m-%d %H:%M:%S'),
            'language': file_data.get('language_code', 'auto'),
            'source': file_data.get('tab_source', 'unknown'),
            'is_recent': True,
            'session_data': file_data
        })
    
    # Sonra veritabanı kayıtlarını ekle
    if db_transcriptions:
        for t in db_transcriptions:
            # Aynı dosya adı ve benzer zamanda değilse ekle (duplikasyon önleme)
            is_duplicate = False
            for recent in recent_files:
                if (recent['file_name'] == t['file_name'] and 
                    abs(recent['processed_at'] - datetime.strptime(t['created_at'], '%Y-%m-%d %H:%M:%S').timestamp()) < 60):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                t['is_recent'] = False
                t['source'] = 'database'
                all_transcriptions.append(t)
    
    if not all_transcriptions:
        st.warning(get_text("no_transcription_history_yet"))
        st.info(get_text("first_use_upload_tabs"))
        return
    
    # Transkripsiyon seçimi
    st.markdown(f"**📊 Toplam {len(all_transcriptions)} transkripsiyon bulundu**")
    
    # Son işlenen dosyaları vurgula
    if recent_files:
        st.success(f"✨ {len(recent_files)} {get_text('recent_files_available')}")
    
    # Dropdown ile seçim
    transcription_options = []
    for i, t in enumerate(all_transcriptions):
        date_str = t['created_at'][:16].replace('T', ' ')  # 2024-01-01 12:00 formatı
        source_icon = "🔥" if t.get('is_recent', False) else "📄"
        option_text = f"{source_icon} {date_str} | {t['file_name'][:40]}{'...' if len(t['file_name']) > 40 else ''}"
        transcription_options.append(option_text)
    
    selected_index = st.selectbox(
        get_text("select_transcription_to_translate"),
        range(len(all_transcriptions)),
        format_func=lambda x: transcription_options[x],
        help="Çevirmek istediğiniz transkripsiyon sonucunu seçin (🔥 = yeni işlenen)"
    )
    
    selected_transcription = all_transcriptions[selected_index]
    
    # Seçili transkripsiyon önizlemesi
    with st.expander(get_text("transcription_preview"), expanded=False):
        st.markdown(f"**📄 Dosya:** {selected_transcription['file_name']}")
        st.markdown(f"**📅 Tarih:** {selected_transcription['created_at'][:16].replace('T', ' ')}")
        st.markdown(f"**🌍 Dil:** {selected_transcription['language']}")
        st.markdown(f"**📊 Uzunluk:** {len(selected_transcription['transcript_text'])} karakter")
        
        # TAM METİN gösterimi - sadece görsel olarak kısıtla
        full_text = selected_transcription['transcript_text']
        if len(full_text) > 500:
            st.markdown(get_text("content_preview"))
            st.text_area("", full_text[:500] + "\n\n... (TAM METİN ÇEVRİLECEK)", height=150, disabled=True, key="preview_text")
            st.info(get_text("full_content_will_translate").format(len(full_text)))
        else:
            st.markdown(get_text("full_content"))
            st.text_area("", full_text, height=150, disabled=True, key="full_text")
    
    # Çeviri ayarları
    st.markdown(f"### {get_text('translation_settings')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_language = st.selectbox(
            get_text("target_language"),
            list(TRANSLATION_LANGUAGES.keys()),
            index=0,
            help=get_text("translation_settings_help")
        )
        language_code = TRANSLATION_LANGUAGES[target_language]
    
    with col2:
        model_choice = st.selectbox(
            get_text("ai_model_choice"),
            list(OPENAI_MODELS.keys()),
            index=1,  # GPT-4o Mini varsayılan
            help=get_text("model_quality_help")
        )
        model_name = OPENAI_MODELS[model_choice]
    
    # Maliyet tahmini
    text_length = len(selected_transcription['transcript_text'])
    estimated_tokens = text_length // 3  # Yaklaşık token hesabı
    
    cost_info = {
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.0001,
        "gpt-4-turbo": 0.001,
        "gpt-3.5-turbo": 0.0005
    }
    
    estimated_cost = (estimated_tokens / 1000) * cost_info.get(model_name, 0.001)
    
    st.info(f"{get_text('estimated_cost')} ~${estimated_cost:.4f} ({estimated_tokens:,} token)")
    
    # Çevir butonu
    if st.button(get_text("start_translation"), type="primary"):
        if text_length > 100000:  # Limiti artırdık
            st.error(get_text("text_too_long"))
            st.info(get_text("suggest_split_translation"))
            return
        
        translation_logger.start(f"Çeviri süreci başladı: {target_language} - {model_choice}")
        
        with st.spinner(f"🤖 {model_choice} ile {target_language} diline çevriliyor..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Çeviri işlemi
            translation_logger.progress(1, 4, "AI çeviri işlemi başlatılıyor")
            status_text.info("🧠 AI çeviri işlemi başladı...")
            progress_bar.progress(30)
            
            translation_result = translate_text(
                selected_transcription['transcript_text'],
                language_code,
                model_name
            )
            
            translation_logger.progress(2, 4, "Çeviri sonucu işleniyor")
            progress_bar.progress(70)
            status_text.info("💾 Sonuç kaydediliyor...")
            
            # Sonucu session state'e kaydet
            st.session_state.translation_result = translation_result
            st.session_state.translation_info = {
                'source_file': selected_transcription['file_name'],
                'target_language': target_language,
                'model_used': model_choice,
                'original_text': selected_transcription['transcript_text'],
                'source_id': selected_transcription['id']
            }
            
            translation_logger.progress(3, 4, "Veritabanına kaydetme")
            
            # Veritabanına kaydet
            try:
                translation_id = save_translation_to_history(
                    selected_transcription['id'],
                    selected_transcription['transcript_text'],
                    translation_result,
                    language_code,
                    model_choice
                )
                if translation_id:
                    st.session_state.translation_saved_id = translation_id
                    translation_logger.success(f"Çeviri ID {translation_id} ile veritabanına kaydedildi")
                else:
                    translation_logger.warning("Veritabanı kaydetme başarısız")
            except Exception as e:
                translation_logger.error(f"Veritabanı kaydetme hatası: {str(e)}")
                st.warning(f"⚠️ Çeviri geçmişe kaydedilemedi: {str(e)}")
            
            translation_logger.progress(4, 4, "Çeviri süreci tamamlanıyor")
            progress_bar.progress(100)
            status_text.success("✅ Çeviri tamamlandı!")
            
            translation_logger.success("Çeviri süreci başarıyla tamamlandı")
            
            # Sonucu göster
            st.success(get_text("translation_completed"))
            
            st.markdown(f"### {get_text('translation_result')}")
            st.markdown(f"**{get_text('source_file')}** {selected_transcription['file_name']}")
            st.markdown(f"**{get_text('model_used')}** {model_choice}")
            st.markdown(f"**{get_text('character_count')}** {len(selected_transcription['transcript_text'])} {get_text('character_arrow')} {len(translation_result)} karakter")
            
            st.markdown(f"### {get_text('translation_result')}")
            st.text_area("", translation_result, height=400, key="current_translation")
            
            # İndirme butonu
            filename = f"translation_{language_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            st.download_button(
                label=get_text("download_translation"),
                data=translation_result,
                file_name=filename,
                mime="text/plain",
                key="download_current_translation"
            )

if __name__ == "__main__":
    render_translation_tab()
