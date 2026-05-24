import yt_dlp
import datetime

channels = {
    # HABER
    "HaberTürk": ("https://www.youtube.com/watch?v=RNVNlJSUFoE", "Haber"),
    "CNN Türk": ("https://www.youtube.com/watch?v=ztmY_cCtUl0", "Haber"),
    "NTV": ("https://www.youtube.com/watch?v=pqq5c6k70kk", "Haber"),
    "A Haber": ("https://www.youtube.com/watch?v=nmY9i63t6qo", "Haber"),
    "Halk TV": ("https://www.youtube.com/watch?v=8uNelFh0oz4", "Haber"),
    "Sözcü TV": ("https://www.youtube.com/watch?v=ztmY_cCtUl0", "Haber"),
    # DİZİ
    "Yalı Çapkını": ("https://www.youtube.com/watch?v=GiWeH1H1bDU", "7/24 Dizi/Film"),
    "Çocuklar Duymasın": ("https://www.youtube.com/watch?v=4SrvTqYmHvM", "7/24 Dizi/Film"),
    "Selena": ("https://www.youtube.com/watch?v=1lyLi6l74fs", "7/24 Dizi/Film"),
    "İstanbullu Gelin": ("https://www.youtube.com/watch?v=PGHUR6qaXfc", "7/24 Dizi/Film"),
    "Arka Sıradakiler": ("https://www.youtube.com/watch?v=VmXNuY5Sj5g", "7/24 Dizi/Film"),
    "Çukur": ("https://www.youtube.com/watch?v=Ho4471a9S4k", "7/24 Dizi/Film"),
    "Bizimkiler": ("https://www.youtube.com/watch?v=jvC6-s5exnI", "7/24 Dizi/Film"),
}

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'tv_embedded', 'ios'],
            'player_skip': ['webpage', 'configs'],
        }
    }
}

with open('youtube.m3u', 'w', encoding='utf-8') as f:
    f.write("#EXTM3U\n")
    f.write(f"# Son Güncelleme: {datetime.datetime.now()}\n\n")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name, (url, group) in channels.items():
            try:
                print(f"{name} linki çekiliyor...")
                info = ydl.extract_info(url, download=False)
                video_id = url.split("v=")[1]
                logo = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                live_url = None
                for fmt in info.get('formats', []):
                    if fmt.get('protocol') == 'm3u8_native':
                        live_url = fmt.get('url')
                        break
                if not live_url:
                    live_url = info.get('url')
                if live_url:
                    f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}\n')
                    f.write(f'{live_url}\n\n')
                    print(f"{name} tamam")
                else:
                    print(f"{name} için link bulunamadı")
            except Exception as e:
                print(f"Hata ({name}): {e}")

print("Tamamlandı!")
