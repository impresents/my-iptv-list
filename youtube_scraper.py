import yt_dlp
import datetime

# Kanalları ve YouTube Canlı Yayın /live linklerini buraya ekle
channels = {
    "HaberTürk": "https://www.youtube.com/@HaberturkTV/live",
    "CNN Türk": "https://www.youtube.com/@cnnturk/live",
    "NTV": "https://www.youtube.com/@ntv/live",
    "A Haber": "https://www.youtube.com/@tvahaber/live",
    "Halk TV": "https://www.youtube.com/@HalkTvcomtr/live",
    "Sözcü TV": "https://www.youtube.com/@Sozcutv/live"
}

ydl_opts = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
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
