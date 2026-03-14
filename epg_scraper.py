#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import sys
import gzip

# 77 Kanallık Tam Liste
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

# Kanalların Kaynaktaki Olası Diğer İsimleri (Alias)
ALIAS_MAP = {
    "NOW": ["fox", "nowtv"],
    "TV8.5": ["tv85", "tv8bucuk"],
    "CNBC-e": ["cnbce"],
    "Kanal 24": ["24tv", "yirmidort"],
    "Sözcü TV": ["szctv", "sozcu"],
    "TRT Spor Yıldız": ["trtyildiz", "trtspor2"],
    "Haber Global": ["haberglobal"],
    "TELE1": ["tele1"],
    "Halk TV": ["halktv"],
    "tv100": ["tv100"],
    "FB TV": ["fbtv", "fenerbahce"],
    "Tivibu Spor": ["tivibuspor1", "tivibuspor"],
    "TJK TV": ["tjktv"],
    "TRT 2": ["trt2"],
    "TRT Arabi": ["trtarabi"],
    "Diyanet TV": ["diyanettv"],
    "Yaban TV": ["yabantv"],
    "TGRT Belgesel": ["tgrtbelgesel"],
    "VAV TV": ["vavtv"],
    "KRT": ["krttv"],
    "TRT EBA": ["trteba", "ebatv", "trtoku"]
}

MASTER_URLS = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz"
]

def normalize_name(name):
    n = name.lower()
    n = n.replace("hd", "").replace("fhd", "").replace("4k", "")
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def main():
    target_map = {}
    for ch in MY_CHANNELS:
        norm = normalize_name(ch)
        epg_id = ch.replace(" ", "") + ".tr" 
        
        # Eğer bu kanalın alias listesi varsa onları da temizle ve kaydet
        aliases = ALIAS_MAP.get(ch, [])
        norm_aliases = [normalize_name(a) for a in aliases]
        
        target_map[ch] = {
            "original_name": ch,
            "epg_id": epg_id,
            "norm_primary": norm,
            "norm_aliases": norm_aliases,
            "found": False
        }

    new_tv = ET.Element("tv", attrib={"generator-info-name": "BelesTiVi Smart EPG Generator"})
    total_prog_count = 0

    print("EPG Taraması Başlıyor...\n")

    for url in MASTER_URLS:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, timeout=40, headers=headers)
            
            if resp.status_code != 200:
                continue
                
            if url.endswith('.gz') or resp.content[:2] == b'\x1f\x8b':
                xml_data = gzip.decompress(resp.content)
            else:
                xml_data = resp.content
                
            root = ET.fromstring(xml_data)
        except Exception:
            continue

        matched_in_this_file = {} 

        for channel in root.findall('channel'):
            master_id = channel.get('id')
            display_name_el = channel.find('display-name')
            
            if display_name_el is not None and display_name_el.text:
                master_norm = normalize_name(display_name_el.text)

                for ch_key, data in target_map.items():
                    if data["found"]:
                        continue
                        
                    # Ana isme veya alias'lara uyuyor mu kontrol et
                    match_found = False
                    if data["norm_primary"] in master_norm or master_norm in data["norm_primary"]:
                        match_found = True
                    else:
                        for alias in data["norm_aliases"]:
                            if alias in master_norm or master_norm in alias:
                                match_found = True
                                break
                                
                    if match_found:
                        data["found"] = True
                        new_ch = ET.SubElement(new_tv, "channel", id=data["epg_id"])
                        new_dn = ET.SubElement(new_ch, "display-name", lang="tr")
                        new_dn.text = data["original_name"]
                        matched_in_this_file[master_id] = data["epg_id"]
                        break

        for prog in root.findall('programme'):
            master_prog_id = prog.get('channel')
            if master_prog_id in matched_in_this_file:
                prog.set('channel', matched_in_this_file[master_prog_id])
                new_tv.append(prog)
                total_prog_count += 1

    found_count = sum(1 for data in target_map.values() if data["found"])
    print(f"Başarıyla Bulunan Kanal: {found_count} / {len(MY_CHANNELS)}")
    print(f"Çekilen Toplam Program Sayısı: {total_prog_count}")

    rough_string = ET.tostring(new_tv, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))

    print("\n✅ İşlem Tamam!")

if __name__ == "__main__":
    main()
