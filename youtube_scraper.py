import yt_dlp
import datetime

# Kanalları ve YouTube Canlı Yayın /live linklerini buraya ekle
# VİRGÜLLERE DİKKAT ETTİK, HEPSİ TAMAM!
channels = {
    "HaberTürk": "https://www.youtube.com/watch?v=RNVNlJSUFoE",
    "CNN Türk": "https://www.youtube.com/watch?v=ztmY_cCtUl0",
    "NTV": "https://www.youtube.com/watch?v=pqq5c6k70kk",
    "A Haber": "https://www.youtube.com/watch?v=nmY9i63t6qo",
    "Halk TV": "https://www.youtube.com/watch?v=8uNelFh0oz4",
    "Sözcü TV": "https://www.youtube.com/watch?v=ztmY_cCtUl0",
    "Kurtlar Vadisi Pusu": "https://www.youtube.com/watch?v=J-7jcpJE6QM"
}

# İŞTE YOUTUBE'U KANDIRAN ANDROID KALKANI BURADA:
ydl_opts = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {
        'youtube': ['player_client=android']
    }
}

# Sadece YouTube kanallarının olduğu yeni bir m3u listesi üretiyoruz
with open('youtube.m3u', 'w', encoding='utf-8') as f:
    f.write("#EXTM3U\n")
    f.write(f"# Son Güncelleme: {datetime.datetime.now()}\n\n")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name, url in channels.items():
            try:
                print(f"{name} linki çekiliyor...")
                info = ydl.extract_info(url, download=False)
                live_url = info.get('url', '')
                
                if live_url:
                    # EPG eşleşmesi için kanal adını tam yazıyoruz
                    f.write(f'#EXTINF:-1 tvg-logo="", group-title="Haber", {name}\n')
                    f.write(f'{live_url}\n\n')
            except Exception as e:
                print(f"Hata ({name}): {e}")

print("İşlem tamamlandı! youtube.m3u dosyası oluşturuldu.")
