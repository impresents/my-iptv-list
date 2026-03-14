# 📺 Türk TV EPG

Her gün otomatik güncellenen Türk TV kanalları için XMLTV formatında EPG.

## Kullanım

Uygulamanda EPG URL'si olarak şunu kullan:

```
https://raw.githubusercontent.com/impresents/my-iptv-list/main/epg.xml
```

## Kanallar

TRT 1, TRT 2, TRT Haber, TRT Spor, TRT Spor Yıldız, TRT Müzik, TRT Belgesel,
TRT Çocuk, TRT World, TRT Türk, TRT Avaz, TRT Kurdi, TRT Arabi, TRT EBA,
Show TV, Kanal D, ATV, NOW TV, Star TV, TV8, Kanal 7, NTV, CNN Türk,
Habertürk, A Haber, Halk TV, Sözcü TV, tv100, TGRT Haber, Haber Global,
360 TV, Teve2, TV8.5, A Spor, HT Spor, FB TV, Diyanet TV, Akit TV, Beyaz TV

## Otomatik Güncelleme

GitHub Actions her gece **00:30 Türkiye saatiyle** çalışır ve `epg.xml` dosyasını günceller.

## Kurulum

1. Bu repoyu fork'la veya klonla
2. `epg_scraper.py` ve `.github/workflows/update-epg.yml` dosyalarını kendi repona ekle
3. GitHub Actions'ı etkinleştir
4. İlk çalıştırma için: Actions → "EPG Güncelle" → "Run workflow"

## Kanal ID Formatı

EPG'deki kanal ID'leri M3U listenizdeki `tvg-id` değerleriyle eşleşmelidir:

| Kanal | EPG ID |
|-------|--------|
| TRT 1 | TRT1.tr |
| Show TV | ShowTV.tr |
| Kanal D | KanalD.tr |
| ATV | ATV.tr |
| ... | ... |
