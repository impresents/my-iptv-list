#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import sys

# Senin Kotlin'den gönderdiğin 77 Kanallık Tam Liste
MY_CHANNELS = [
    "TRT 1", "Show TV", "Kanal D", "ATV", "NOW", "Star TV", "TV8", "360",
    "CNBC-e", "Bloomberg HT", "A Haber", "TRT Haber", "Kanal 7", "A2", "Beyaz TV", "tv100",
    "Ülke TV", "TVNET", "Kanal 24", "24 TV", "NTV", "CNN Türk", "A Para", "Habertürk",
    "TGRT Haber", "Ekotürk", "Haber Global", "TELE1", "Ekol TV", "Flash Haber", "Lider Haber", "ULUSAL TV",
    "Halk TV", "Teve2", "TV8.5", "TRT 3", "TRT Avaz", "TRT Kurdi", "Türk Haber", "Sözcü TV",
    "TRT Türk", "KRT", "Bengütürk", "TV4", "TRT 2", "VAV TV", "Diyanet TV", "Akit TV", "GZT", "Bi Kanal", "MK TV",
    "TYT Türk", "TRT Spor", "A Spor", "HT Spor", "FB TV", "Tivibu Spor", "Sıfır TV", "TRT Spor Yıldız", "TJK TV",
    "Sports TV", "TLC", "TRT Müzik", "TRT Arabi", "A News", "BBC World", "TRT World",
    "TRT EBA", "TRT Çocuk", "STOON TV", "Cartoon Network", "Minika GO", "Minika Çocuk", "DMAX", "Yaban TV",
    "TRT Belgesel", "TGRT Belgesel"
]

# İnternetteki ana Türkçe TV Rehberi kaynağı (Her gün güncellenir)
MASTER_EPG_URL = "https://epg.koditvepg.com/TR/guide.xml"

# İsimleri eşleştirmek için temizleyen fonksiyon (Örn: "Kanal D HD" -> "kanald")
def normalize_name(name):
    n = name.lower()
    n = n.replace("hd", "").replace("fhd", "").replace("4k", "")
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def main():
    print("Master EPG indiriliyor (Bu işlem birkaç saniye sürebilir)...")
    try:
        resp = requests.get(MASTER_EPG_URL, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"HATA: Master XML indirilemedi - {e}")
        sys.exit(1)

    print("Master XML ayrıştırılıyor...")
    try:
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"HATA: XML parçalanamadı - {e}")
        sys.exit(1)

    # Hedef kanallarımız ve Android uygulamanın beklediği epgId'ler (Örn: KanalD.tr)
    target_map = {}
    for ch in MY_CHANNELS:
        norm = normalize_name(ch)
        # Uygulamadaki ID mantığın: Boşlukları sil ve sonuna .tr ekle
        epg_id = ch.replace(" ", "") + ".tr" 
        target_map[norm] = {
            "original_name": ch,
            "epg_id": epg_id,
            "found_master_id": None
        }

    new_tv = ET.Element("tv", attrib={"generator-info-name": "BelesTiVi EPG Generator v2.0"})
    matched_channel_ids = {} 

    # 1. Aşama: Kanalları Eşleştir
    for channel in root.findall('channel'):
        master_id = channel.get('id')
        display_name_el = channel.find('display-name')
        
        if display_name_el is not None and display_name_el.text:
            master_name = display_name_el.text
            master_norm = normalize_name(master_name)

            # Bizim 77 kanallık listede var mı kontrol et
            for norm_key, data in target_map.items():
                if norm_key in master_norm or master_norm in norm_key:
                    if data["found_master_id"] is None: # İlk eşleşeni al
                        data["found_master_id"] = master_id
                        matched_channel_ids[master_id] = data["epg_id"]

                        # Android uygulaman için yeni XML'e kanalı ekle
                        new_ch = ET.SubElement(new_tv, "channel", id=data["epg_id"])
                        new_dn = ET.SubElement(new_ch, "display-name", lang="tr")
                        new_dn.text = data["original_name"]
                    break

    # 2. Aşama: Sadece eşleşen kanalların programlarını al
    prog_count = 0
    for prog in root.findall('programme'):
        master_prog_id = prog.get('channel')
        if master_prog_id in matched_channel_ids:
            # ID'yi senin uygulamanın anladığı ID ile değiştir
            prog.set('channel', matched_channel_ids[master_prog_id])
            new_tv.append(prog)
            prog_count += 1

    print(f"\nSONUÇ:")
    print(f"Eşleşen ve Aktarılan Kanal Sayısı: {len(matched_channel_ids)} / {len(MY_CHANNELS)}")
    print(f"Aktarılan Toplam Program Sayısı: {prog_count}")

    # Yeni XML'i oluştur ve kaydet
    rough_string = ET.tostring(new_tv, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))

    print("\n✅ epg.xml başarıyla oluşturuldu ve Github'a gönderilmeye hazır!")

if __name__ == "__main__":
    main()
