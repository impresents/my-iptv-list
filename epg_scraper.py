#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Basit Türk TV EPG scraper
İlk aşamada sadece:
- ATV
- Kanal D
- Show TV
- Star TV

çıktısı üretir ve epg.xml oluşturur.
"""

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


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def to_xmltv_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = TURKEY_TZ.localize(dt)
    return dt.strftime("%Y%m%d%H%M%S %z")


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def parse_time_str(time_str: str, base_date: datetime) -> datetime | None:
    time_str = clean_text(time_str).replace(".", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def unique_programs(items: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        key = (item.get("start", ""), item.get("title", ""))
        if not item.get("title") or not item.get("start"):
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def normalize_programs(raw_programs: list[dict], base_date: datetime) -> list[tuple]:
    result = []
    day_base = base_date.replace(hour=0, minute=0, second=0, microsecond=0)

    for prog in raw_programs:
        title = clean_text(prog.get("title", ""))
        start_raw = clean_text(prog.get("start", ""))
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
        if i < len(result) - 1:
            end_dt = result[i + 1][1]
        else:
            end_dt = start_dt + timedelta(hours=2)
        fixed.append((title, start_dt, end_dt))

    return fixed


def extract_by_text_pairs(page_text: str) -> list[dict]:
    """
    Sayfa metninden:
    07:00
    Program Adı
    şeklindeki akışları toplamaya çalışır.
    """
    lines = [clean_text(x) for x in page_text.splitlines()]
    lines = [x for x in lines if x]

    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\d{1,2}:\d{2}$", line):
            title = ""
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if re.match(r"^\d{1,2}:\d{2}$", nxt):
                    break
                # çok kısa / anlamsız satırları atla
                if len(nxt) >= 2 and nxt.lower() not in {
                    "izle", "canli izle", "yayında", "detaya git",
                    "tekrar", "canlı", "yeni bölüm", "fragman izle",
                    "son bölüm", "son bölümü izle"
                }:
                    title = nxt
                    break
                j += 1

            if title:
                items.append({"start": line, "title": title})
        i += 1

    return unique_programs(items)


def extract_dom_pairs(soup: BeautifulSoup) -> list[dict]:
    """
    HTML içinde zaman ve başlığı yakın düğümlerden toplamaya çalışır.
    """
    items = []

    candidate_blocks = soup.select("li, article, .item, .swiper-slide, .card, .broadcast, .program")
    for block in candidate_blocks:
        text = clean_text(block.get_text("\n", strip=True))
        if not text:
            continue

        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", text)
        if not time_match:
            continue

        lines = [clean_text(x) for x in text.split("\n") if clean_text(x)]
        if len(lines) < 2:
            continue

        start = time_match.group(1)
        title = ""

        for ln in lines:
            if ln == start:
                continue
            if re.match(r"^\d{1,2}:\d{2}$", ln):
                continue
            if ln.lower() in {
                "izle", "canli izle", "yayında", "detaya git",
                "tekrar", "canlı", "yeni bölüm", "fragman izle",
                "son bölüm", "son bölümü izle"
            }:
                continue
            if len(ln) >= 2:
                title = ln
                break

        if title:
            items.append({"start": start, "title": title})

    return unique_programs(items)


def scrape_page(url: str) -> BeautifulSoup:
    session = get_session()
    resp = session.get(url, timeout=25)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def scrape_atv(url: str) -> list[dict]:
    soup = scrape_page(url)
    items = extract_dom_pairs(soup)
    if len(items) < 3:
        items = extract_by_text_pairs(soup.get_text("\n"))
    return items


def scrape_kanald(url: str) -> list[dict]:
    soup = scrape_page(url)
    items = extract_dom_pairs(soup)
    if len(items) < 3:
        items = extract_by_text_pairs(soup.get_text("\n"))
    return items


def scrape_showtv(url: str) -> list[dict]:
    soup = scrape_page(url)
    items = extract_dom_pairs(soup)
    if len(items) < 3:
        items = extract_by_text_pairs(soup.get_text("\n"))
    return items


def scrape_startv(url: str) -> list[dict]:
    soup = scrape_page(url)
    items = extract_dom_pairs(soup)
    if len(items) < 3:
        items = extract_by_text_pairs(soup.get_text("\n"))
    return items


def scrape_channel(channel_id: str, info: dict, base_date: datetime) -> list[tuple]:
    parser_name = info["parser"]
    url = info["url"]

    raw = []
    if parser_name == "atv":
        raw = scrape_atv(url)
    elif parser_name == "kanald":
        raw = scrape_kanald(url)
    elif parser_name == "showtv":
        raw = scrape_showtv(url)
    elif parser_name == "startv":
        raw = scrape_startv(url)

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
