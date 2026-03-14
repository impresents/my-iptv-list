#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import sys
import gzip
import io

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

# Güncel ve Çalışan Master EPG Kaynakları (2026)
MASTER_URLS = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://www.bevy.be/download.php?file=turkey.xml",
    "https://www.bevy.be/download.php?file=turkeypremium1.xml",
    "https://www.bevy.be/download.php?file=turkeypremium2.xml"
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
        target_map[norm] = {
            "original_name": ch,
            "epg_id": epg_id,
            "found": False,
            "source_url": None
        }

    new_tv = ET.Element("tv", attrib={"generator-info-name": "BelesTiVi Multi-Source EPG"})
    total_prog_count = 0

    print("Çoklu EPG Kaynak Taraması Başlıyor...\n")

    for url in MASTER_URLS:
        print(f"➤ Kaynak İndiriliyor: {url.split('/')[-1]}...")
        try:
            # Siteler bot olduğumuzu anlayıp engellemesin diye tarayıcı kimliği (User-Agent) ekledik
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
            resp = requests.get(url, timeout=40, headers=headers)
            
            if resp.status_code != 200:
                print(f"  ❌ HATA: Kaynak yanıt vermedi (HTTP {resp.status_code})")
                continue
                
            # EPG dosyası ".gz" (sıkıştırılmış) formatındaysa, hafızada anında açıyoruz
            if url.endswith('.gz') or resp.content[:2] == b'\x1f\x8b':
                xml_data = gzip.decompress(resp.content)
            else:
                xml_data = resp.content
                
            root = ET.fromstring(xml_data)
            print("  ✅ İndirildi ve ayrıştırıldı. Kanallar eşleştiriliyor...")
        except Exception as e:
            print(f"  ❌ HATA: İndirme veya okuma başarısız - {e}")
            continue

        matched_in_this_file = {} 

        for channel in root.findall('channel'):
            master_id = channel.get('id')
            display_name_el = channel.find('display-name')
            
            if display_name_el is not None and display_name_el.text:
                master_norm = normalize_name(display_name_el.text)

                for norm_key, data in target_map.items():
                    if norm_key in master_norm or master_norm in norm_key:
                        if not data["found"]:
                            data["found"] = True
                            data["source_url"] = url
                            
                            new_ch = ET.SubElement(new_tv, "channel", id=data["epg_id"])
                            new_dn = ET.SubElement(new_ch, "display-name", lang="tr")
                            new_dn.text = data["original_name"]
                        
                        if data["source_url"] == url:
                            matched_in_this_file[master_id] = data["epg_id"]
                        break

        prog_count = 0
        for prog in root.findall('programme'):
            master_prog_id = prog.get('channel')
            if master_prog_id in matched_in_this_file:
                prog.set('channel', matched_in_this_file[master_prog_id])
                new_tv.append(prog)
                prog_count += 1
                total_prog_count += 1
                
        print(f"  📌 Bu kaynaktan {len(matched_in_this_file)} kanal, {prog_count} program çekildi.\n")

    found_count = sum(1 for data in target_map.values() if data["found"])
    print("="*40)
    print(f"SONUÇ RAPORU")
    print("="*40)
    print(f"Toplam Hedef Kanal: {len(MY_CHANNELS)}")
    print(f"Başarıyla Bulunan Kanal: {found_count}")
    print(f"Çekilen Toplam Program Sayısı: {total_prog_count}")
    print("="*40)

    # Bulunamayanları da görelim
    if found_count < len(MY_CHANNELS):
        print("\nBulunamayan Kanallar (Kaynaklarda yayımlanmıyor olabilir):")
        for norm_key, data in target_map.items():
            if not data["found"]:
                print(f" - {data['original_name']}")

    rough_string = ET.tostring(new_tv, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))

    print("\n✅ epg.xml başarıyla oluşturuldu ve Github'a gönderilmeye hazır!")

if __name__ == "__main__":
    main()
