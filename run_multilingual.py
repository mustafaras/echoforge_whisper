#!/usr/bin/env python
"""
echo-forge Multilingual App Launcher
====================================
Çok dilli echo-forge uygulamasını başlatır
"""

import os
import sys
import subprocess

def main():
    # Multilingual klasörüne geç
    os.chdir(r"c:\Users\m_ras\Desktop\AGENTS\whisper\multilingual")
    
    # Streamlit uygulamasını başlat
    try:
        print("🔥 echo-forge Multilingual Edition başlatılıyor...")
        print("📁 Dizin:", os.getcwd())
        print("🌍 Dil desteği: Türkçe/English")
        print("=" * 50)
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8502",  # Farklı port kullan
            "--server.headless", "false",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 echo-forge kapatılıyor...")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
