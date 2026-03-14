#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import sys
import gzip

# 77 Kanallık Tam Liste
CHANNELS_DATA = {
    "TRT 1": "TRT1.tr", "Show TV": "ShowTV.tr", "Kanal D": "KanalD.tr", "ATV": "ATV.tr",
    "NOW": "NOWTV.tr", "Star TV": "StarTV.tr", "TV8": "TV8.tr", "360": "360TV.tr",
    "CNBC-e": "CNBC-e", "Bloomberg HT": "Bloomberg HT", "A Haber": "AHaber.tr", "TRT Haber": "TRTHaber.tr",
    "Kanal 7": "Kanal7.tr", "A2": "A2", "Beyaz TV": "BeyazTV.tr", "tv100": "TV100.tr",
    "Ülke TV": "Ülke TV", "TVNET": "TVNET", "Kanal 24": "Kanal 24", "24 TV": "24 TV",
    "NTV": "NTV.tr", "CNN Türk": "CNN Türk", "A Para": "A Para", "Habertürk": "Habertürk",
    "TGRT Haber": "TGRTHaber.tr", "Ekotürk": "Ekotürk", "Haber Global": "HaberGlobal.tr", "TELE1": "TELE1",
    "Ekol TV": "Ekol TV", "Flash Haber": "Flash Haber TV", "Lider Haber": "Lider Haber TV", "ULUSAL TV": "ULUSAL TV",
    "Halk TV": "HalkTV.tr", "Teve2": "Teve2.tr", "TV8.5": "TV85.tr", "TRT 3": "TRT 3 Spor",
    "TRT Avaz": "TRTAvaz.tr", "TRT Kurdi": "TRTKurdi.tr", "Türk Haber": "Türkhaber TV", "Sözcü TV": "Sözcü TV",
    "TRT Türk": "TRT Türk", "KRT": "KRT", "Bengütürk": "Bengütürk", "TV4": "TV 4",
    "TRT 2": "TRT2.tr", "VAV TV": "Vav TV", "Diyanet TV": "Diyanet TV", "Akit TV": "Akit TV",
    "GZT": "GZT", "Bi Kanal": "Bi Kanal", "MK TV": "MK TV", "TYT Türk": "TYT Türk",
    "TRT Spor": "TRT Spor", "A Spor": "A Spor", "HT Spor": "HT Spor", "FB TV": "FB TV",
    "Tivibu Spor": "Tivibu Spor", "Sıfır TV": "Sıfır TV", "TRT Spor Yıldız": "TRT Spor Yıldız", "TJK TV": "TJK TV",
    "Sports TV": "Sports TV", "TLC": "TLC", "TRT Müzik": "TRT Müzik", "TRT Arabi": "TRT Arabi",
    "A News": "A News", "BBC World": "BBC World", "TRT World": "TRT World", "TRT EBA": "TRT EBA",
    "TRT Çocuk": "TRT Çocuk", "STOON TV": "STOON TV", "Cartoon Network": "Cartoon Network", "Minika GO": "Minika GO",
    "Minika Çocuk": "Minika Çocuk", "DMAX": "DMAX", "Yaban TV": "Yaban TV", "TRT Belgesel": "TRT Belgesel",
    "TGRT Belgesel": "TGRT Belgesel"
}

ALIAS_MAP = {
    "NOW": ["fox", "nowtv", "fox tv"], "TV8.5": ["tv85", "tv 8,5", "tv8bucuk", "tv 8.5"],
    "CNBC-e": ["cnbce"], "360": ["360tv"], "tv100": ["tv 100"],
    "Kanal 24": ["24tv", "yirmidort"], "24 TV": ["24tv", "yirmidort"], "Sözcü TV": ["szctv", "sozcu"],
    "TRT Spor Yıldız": ["trtyildiz", "trtspor2"], "Haber Global": ["haberglobal"], "TELE1": ["tele1"],
    "Halk TV": ["halktv"], "FB TV": ["fbtv", "fenerbahce"], "Tivibu Spor": ["tivibuspor1", "tivibuspor"],
    "TJK TV": ["tjktv"], "TRT 2": ["trt2", "trt 2 hd"], "TRT Arabi": ["trtarabi"],
    "Diyanet TV": ["diyanettv"], "Yaban TV": ["yabantv"], "TGRT Belgesel": ["tgrtbelgesel"],
    "VAV TV": ["vavtv"], "KRT": ["krttv"], "TRT EBA": ["trteba", "ebatv", "trtoku"]
}

MASTER_URLS = [
    "https://www.open-epg.com/app/download.php?file=turkey3.xml"
]

def normalize_name(name):
    n = name.lower()
    n = n.replace("hd", "").replace("fhd", "").replace("4k", "")
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def main():
    target_map = {}
    for ch_name, epg_id in CHANNELS_DATA.items():
        norm = normalize_name(ch_name)
        aliases = ALIAS_MAP.get(ch_name, [])
        norm_aliases = [normalize_name(a) for a in aliases]
        target_map[ch_name] = {"original_name": ch_name, "epg_id": epg_id, "norm_primary": norm, "norm_aliases": norm_aliases, "found": False}

    new_tv = ET.Element("tv", attrib={"generator-info-name": "BelesTiVi Turkey3 EPG"})
    total_prog_count = 0

    for url in MASTER_URLS:
        try:
            resp = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200: continue
            xml_data = gzip.decompress(resp.content) if url.endswith('.gz') or resp.content[:2] == b'\x1f\x8b' else resp.content
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
                    if data["found"]: continue
                    match_found = False
                    
                    if master_norm == data["norm_primary"] or master_norm in data["norm_aliases"]:
                        match_found = True
                    elif data["norm_primary"] in master_norm:
                        if data["norm_primary"] == "tv8" and "85" in master_norm: match_found = False
                        else: match_found = True
                                
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
                # Saat dilimi yaması tamamen silindi. Kaynaktan geldiği gibi bırakıyoruz.
                prog.set('channel', matched_in_this_file[master_prog_id])
                new_tv.append(prog)
                total_prog_count += 1
                
    rough_string = ET.tostring(new_tv, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))

if __name__ == "__main__":
    main()
