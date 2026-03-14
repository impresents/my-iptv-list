#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import time
from datetime import datetime, timedelta
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

import pytz
import requests
from bs4 import BeautifulSoup

TURKEY_TZ = pytz.timezone("Europe/Istanbul")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CHANNELS = {
    "ATV.tr": {
        "name": "ATV",
        "url": "https://www.atv.com.tr/yayin-akisi",
        "parser": "atv",
    },
    "KanalD.tr": {
        "name": "Kanal D",
        "url": "https://www.kanald.com.tr/yayin-akisi",
        "parser": "kanald",
    },
    "ShowTV.tr": {
        "name": "Show TV",
        "url": "https://www.showtv.com.tr/yayin-akisi",
        "parser": "showtv",
    },
    "StarTV.tr": {
        "name": "Star TV",
        "url": "https://www.startv.com.tr/yayin-akisi",
        "parser": "startv",
    },
}

NOISE_LINES = {
    "YAYINDA",
    "CANLI",
    "CANLI İZLE",
    "İZLE",
    "ŞİMDİ İZLE",
    "DETAYA GİT",
    "BÖLÜM İZLE",
    "FRAGMAN İZLE",
    "SON BÖLÜMÜ İZLE",
    "YENİ BÖLÜM",
    "TEKRAR",
    "HABER - CANLI",
    "YERLİ DİZİ - TEKRAR",
    "YAŞAM",
    "YAŞAM - YENİ BÖLÜM",
    "YABANCI FİLM",
    "YERLİ SİNEMA",
    "YABANCI SİNEMA",
}

def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def to_xmltv_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = TURKEY_TZ.localize(dt)
    return dt.strftime("%Y%m%d%H%M%S %z")

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def normalize_time_text(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"(\d{1,2})\s*:\s*(\d{2})", r"\1:\2", text)
    return text

def parse_time_str(time_str: str, base_date: datetime):
    t = normalize_time_text(time_str)
    m = re.match(r"^(\d{1,2}):(\d{2})$", t)
    if not m:
        return None
    return base_date.replace(
        hour=int(m.group(1)),
        minute=int(m.group(2)),
        second=0,
        microsecond=0,
    )

def is_noise_line(text: str) -> bool:
    t = clean_text(text)
    if not t:
        return True
    if t.upper() in NOISE_LINES:
        return True
    if re.fullmatch(r"\d+\.\s*Bölüm", t, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"[A-ZÇĞİÖŞÜa-zçğıöşü]+\s*-\s*(Canlı|Tekrar|Yeni Bölüm)", t, flags=re.IGNORECASE):
        return True
    return False

def unique_programs(items):
    seen = set()
    result = []
    for item in items:
        start = normalize_time_text(item.get("start", ""))
        title = clean_text(item.get("title", ""))
        if not start or not title:
            continue
        key = (start, title)
        if key in seen:
            continue
        seen.add(key)
        result.append({"start": start, "title": title})
    return result

def normalize_programs(raw_programs, base_date):
    result = []
    day_base = base_date.replace(hour=0, minute=0, second=0, microsecond=0)

    for prog in raw_programs:
        title = clean_text(prog.get("title", ""))
        start_raw = normalize_time_text(prog.get("start", ""))
        if not title or not start_raw:
            continue

        start_dt = parse_time_str(start_raw, day_base)
        if start_dt is None:
            continue

        if result and start_dt < result[-1][1].replace(tzinfo=None):
            start_dt += timedelta(days=1)

        start_dt = TURKEY_TZ.localize(start_dt)
        result.append((title, start_dt, None))

    fixed = []
    for i, item in enumerate(result):
        title, start_dt, _ = item
        end_dt = result[i + 1][1] if i < len(result) - 1 else start_dt + timedelta(hours=2)
        fixed.append((title, start_dt, end_dt))
    return fixed

def scrape_page(url: str) -> BeautifulSoup:
    session = get_session()
    resp = session.get(url, timeout=25)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def scrape_kanald(url: str):
    soup = scrape_page(url)
    items = []

    # Kanal D'de saatten sonra gerçek başlık h3 altında geliyor, ayrıca YAYINDA gürültüsü var
    for title_el in soup.select("h3, h4, h5"):
        title = clean_text(title_el.get_text(" ", strip=True))
        if not title or is_noise_line(title):
            continue

        prev = title_el.find_previous(string=re.compile(r"\b\d{1,2}:\d{2}\b"))
        if not prev:
            continue

        m = re.search(r"\b(\d{1,2}:\d{2})\b", str(prev))
        if not m:
            continue

        items.append({
            "start": m.group(1),
            "title": title,
        })

    return unique_programs(items)

def scrape_startv(url: str):
    soup = scrape_page(url)
    items = []

    # Star TV'de gerçek başlık ##### altında, "Yaşam" gibi tür satırları ayrı
    for title_el in soup.select("h5, h4, h3"):
        title = clean_text(title_el.get_text(" ", strip=True))
        if not title or is_noise_line(title):
            continue

        prev = title_el.find_previous(string=re.compile(r"\b\d{1,2}:\d{2}\b"))
        if not prev:
            continue

        m = re.search(r"\b(\d{1,2}:\d{2})\b", str(prev))
        if not m:
            continue

        items.append({
            "start": m.group(1),
            "title": title,
        })

    return unique_programs(items)

def scrape_atv(url: str):
    soup = scrape_page(url)
    page_text = soup.get_text("\n")

    lines = [clean_text(x) for x in page_text.splitlines()]
    lines = [x for x in lines if x]

    items = []
    i = 0
    while i < len(lines):
        line = normalize_time_text(lines[i])

        # Saat satırı: 06:20 veya 06: 20 gibi
        if re.match(r"^\d{1,2}:\d{2}$", line):
            title = ""
            j = i + 1

            while j < len(lines):
                nxt = clean_text(lines[j])
                nxt_norm = normalize_time_text(nxt)

                # bir sonraki saate geldiysek bırak
                if re.match(r"^\d{1,2}:\d{2}$", nxt_norm):
                    break

                # gürültü satırlarını atla
                if not is_noise_line(nxt):
                    title = nxt
                    break

                j += 1

            if title:
                items.append({
                    "start": line,
                    "title": title
                })

        i += 1

    return unique_programs(items)
def scrape_showtv(url: str):
    soup = scrape_page(url)
    return extract_showtv_text_pairs(soup.get_text("\n"))

def scrape_channel(channel_id: str, info: dict, base_date: datetime):
    parser_name = info["parser"]
    url = info["url"]

    if parser_name == "atv":
        raw = scrape_atv(url)
    elif parser_name == "kanald":
        raw = scrape_kanald(url)
    elif parser_name == "showtv":
        raw = scrape_showtv(url)
    elif parser_name == "startv":
        raw = scrape_startv(url)
    else:
        raw = []

    print(f"  Ham veri: {len(raw)} program")
    normalized = normalize_programs(raw, base_date)
    print(f"  Normalize: {len(normalized)} program")
    return normalized

def build_xmltv(all_programs: dict) -> str:
    tv = Element("tv", attrib={"generator-info-name": "Simple Turkish EPG Scraper"})

    for ch_id, ch_info in CHANNELS.items():
        if ch_id not in all_programs or not all_programs[ch_id]:
            continue
        channel = SubElement(tv, "channel", id=ch_id)
        dn = SubElement(channel, "display-name", lang="tr")
        dn.text = ch_info["name"]

    for ch_id, programs in all_programs.items():
        for title, start_dt, end_dt in programs:
            pr = SubElement(tv, "programme", attrib={
                "start": to_xmltv_time(start_dt),
                "stop": to_xmltv_time(end_dt),
                "channel": ch_id,
            })
            title_el = SubElement(pr, "title", lang="tr")
            title_el.text = title

    rough = tostring(tv, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    return pretty.decode("utf-8")

def main():
    today = datetime.now(TURKEY_TZ).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    all_programs = {}

    print("EPG üretimi başladı...")

    for ch_id, info in CHANNELS.items():
        print(f"\n[{ch_id}] {info['name']} çekiliyor...")
        try:
            programs = scrape_channel(ch_id, info, today)
            if programs:
                all_programs[ch_id] = programs
                print(f"  OK → {len(programs)} program")
            else:
                print("  Veri alınamadı")
        except Exception as e:
            print(f"  HATA: {e}")

        time.sleep(1)

    xml_content = build_xmltv(all_programs)
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    total_programs = sum(len(v) for v in all_programs.values())
    print(f"\nTamamlandı: {len(all_programs)} kanal, {total_programs} program")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"GENEL HATA: {exc}")
        sys.exit(1)
