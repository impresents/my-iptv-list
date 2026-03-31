import yt_dlp
import datetime

# Kanalları ve YouTube Canlı Yayın /live linklerini buraya ekle
channels = {
    "HaberTürk": "https://www.youtube.com/watch?v=RNVNlJSUFoE",
    "CNN Türk": "https://www.youtube.com/watch?v=ztmY_cCtUl0",
    "NTV": "https://www.youtube.com/watch?v=pqq5c6k70kk",
    "A Haber": "https://www.youtube.com/watch?v=nmY9i63t6qo",
    "Halk TV": "https://www.youtube.com/watch?v=8uNelFh0oz4",
    "Sözcü TV": "https://www.youtube.com/watch?v=ztmY_cCtUl0"
}

# --- İŞTE YOUTUBE'U KANDIRAN YENİ "SMART TV" KALKANI ---
ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'tv_embedded', 'ios'],
            'player_skip': ['webpage', 'configs'],
        }
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
