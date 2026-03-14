#!/usr/bin/env python3
"""
Türk TV Kanalları EPG Scraper
Her gün çalışır, kanalların yayın akışını çeker ve XMLTV formatında EPG üretir.
GitHub Actions ile otomatik çalışır.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import json
import re
import time
import sys
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

TURKEY_TZ = pytz.timezone("Europe/Istanbul")

# ─────────────────────────────────────────
#  KANAL TANIMI
# ─────────────────────────────────────────
CHANNELS = {
    "TRT1.tr":           {"name": "TRT 1",         "scraper": "trt",       "trt_id": "trt-1"},
    "TRT2.tr":           {"name": "TRT 2",          "scraper": "trt",       "trt_id": "trt-2"},
    "TRTHaber.tr":       {"name": "TRT Haber",      "scraper": "trt",       "trt_id": "trt-haber"},
    "TRTSpor.tr":        {"name": "TRT Spor",       "scraper": "trt",       "trt_id": "trt-spor"},
    "TRTSporYildiz.tr":  {"name": "TRT Spor Yıldız","scraper": "trt",       "trt_id": "trt-spor-yildiz"},
    "TRTMuzik.tr":       {"name": "TRT Müzik",      "scraper": "trt",       "trt_id": "trt-muzik"},
    "TRTBelgesel.tr":    {"name": "TRT Belgesel",   "scraper": "trt",       "trt_id": "trt-belgesel"},
    "TRTCocuk.tr":       {"name": "TRT Çocuk",      "scraper": "trt",       "trt_id": "trt-cocuk"},
    "TRTWorld.tr":       {"name": "TRT World",      "scraper": "trt",       "trt_id": "trt-world"},
    "TRTTurk.tr":        {"name": "TRT Türk",       "scraper": "trt",       "trt_id": "trt-turk"},
    "TRTAvaz.tr":        {"name": "TRT Avaz",       "scraper": "trt",       "trt_id": "trt-avaz"},
    "TRTKurdi.tr":       {"name": "TRT Kurdi",      "scraper": "trt",       "trt_id": "trt-kurdi"},
    "TRTArabi.tr":       {"name": "TRT Arabi",      "scraper": "trt",       "trt_id": "trt-arabi"},
    "TRTEBA.tr":         {"name": "TRT EBA",        "scraper": "trt",       "trt_id": "trt-eba"},
    "ShowTV.tr":         {"name": "Show TV",        "scraper": "showtv"},
    "KanalD.tr":         {"name": "Kanal D",        "scraper": "kanald"},
    "ATV.tr":            {"name": "ATV",            "scraper": "atv"},
    "NOWTV.tr":          {"name": "NOW TV",         {"scraper": "nowtv"},
    "StarTV.tr":         {"name": "Star TV",        "scraper": "startv"},
    "TV8.tr":            {"name": "TV8",            "scraper": "tv8"},
    "Kanal7.tr":         {"name": "Kanal 7",        "scraper": "kanal7"},
    "NTV.tr":            {"name": "NTV",            "scraper": "ntv"},
    "CNNTurk.tr":        {"name": "CNN Türk",       "scraper": "cnnturk"},
    "HaberturkTV.tr":    {"name": "Habertürk",      "scraper": "haberturk"},
    "AHaber.tr":         {"name": "A Haber",        "scraper": "ahaber"},
    "HalkTV.tr":         {"name": "Halk TV",        "scraper": "halktv"},
    "SozcuTV.tr":        {"name": "Sözcü TV",       "scraper": "sozcutv"},
    "TV100.tr":          {"name": "tv100",          "scraper": "tv100"},
    "TGRTHaber.tr":      {"name": "TGRT Haber",     "scraper": "tgrthaber"},
    "HaberGlobal.tr":    {"name": "Haber Global",   "scraper": "haberglobal"},
    "360TV.tr":          {"name": "360 TV",         "scraper": "360tv"},
    "Teve2.tr":          {"name": "Teve2",          "scraper": "teve2"},
    "TV85.tr":           {"name": "TV8.5",          "scraper": "tv85"},
    "ASpor.tr":          {"name": "A Spor",         "scraper": "aspor"},
    "HTSpor.tr":         {"name": "HT Spor",        "scraper": "htspor"},
    "FBTV.tr":           {"name": "FB TV",          "scraper": "fbtv"},
    "DiyanetTV.tr":      {"name": "Diyanet TV",     "scraper": "diyanettv"},
    "AkitTV.tr":         {"name": "Akit TV",        "scraper": "akittv"},
    "BeyazTV.tr":        {"name": "Beyaz TV",       "scraper": "beyaztv"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─────────────────────────────────────────
#  YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────

def to_xmltv_time(dt: datetime) -> str:
    """datetime → XMLTV format: 20260314130000 +0300"""
    if dt.tzinfo is None:
        dt = TURKEY_TZ.localize(dt)
    return dt.strftime("%Y%m%d%H%M%S %z")


def parse_time_str(time_str: str, base_date: datetime) -> datetime:
    """'20:00' gibi string'i datetime'a çevir."""
    time_str = time_str.strip().replace(".", ":")
    match = re.match(r"(\d{1,2}):(\d{2})", time_str)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt


def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


# ─────────────────────────────────────────
#  TRT SCRAPER
# ─────────────────────────────────────────

def scrape_trt(channel_id: str, trt_id: str, date: datetime) -> list:
    """
    TRT kanalları için yayın akışı çeker.
    URL: https://www.trt.net.tr/yayin-akisi/{trt_id}?date=YYYY-MM-DD
    """
    programs = []
    date_str = date.strftime("%Y-%m-%d")
    url = f"https://www.trt.net.tr/yayin-akisi/{trt_id}?date={date_str}"

    try:
        session = get_session()
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"  [TRT] {trt_id} HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # TRT sayfasında program listesi genellikle JSON içinde ya da liste elemanlarında
        # Önce JSON script tag deneyelim
        scripts = soup.find_all("script")
        schedule_data = None
        for script in scripts:
            if script.string and ("schedule" in script.string.lower() or "yayin" in script.string.lower()):
                # JSON verisini çıkarmaya çalış
                json_match = re.search(r'\[(\{.*?"title".*?\})\]', script.string, re.DOTALL)
                if json_match:
                    try:
                        schedule_data = json.loads("[" + json_match.group(1) + "]")
                        break
                    except Exception:
                        pass

        if schedule_data:
            for item in schedule_data:
                title = item.get("title") or item.get("name") or ""
                start_str = item.get("startTime") or item.get("start") or ""
                end_str = item.get("endTime") or item.get("end") or ""
                if title and start_str:
                    programs.append({
                        "title": title,
                        "start": start_str,
                        "end": end_str
                    })
        else:
            # HTML parse: program listesi
            items = soup.select(".schedule-item, .program-item, [class*='schedule'], [class*='program-list'] li")
            for item in items:
                time_el = item.select_one("[class*='time'], time, .hour, .saat")
                title_el = item.select_one("[class*='title'], h3, h4, .name, strong")
                if time_el and title_el:
                    programs.append({
                        "title": title_el.get_text(strip=True),
                        "start": time_el.get_text(strip=True),
                        "end": ""
                    })

        print(f"  [TRT] {trt_id}: {len(programs)} program")
    except Exception as e:
        print(f"  [TRT] {trt_id} hata: {e}")

    return programs


# ─────────────────────────────────────────
#  GENEL HTML SCRAPER
# ─────────────────────────────────────────

SCRAPER_URLS = {
    "showtv":     "https://www.showtv.com.tr/yayin-akisi",
    "kanald":     "https://www.kanald.com.tr/yayin-akisi",
    "atv":        "https://www.atv.com.tr/yayin-akisi",
    "nowtv":      "https://www.nowtv.com.tr/yayin-akisi",
    "startv":     "https://www.startv.com.tr/yayin-akisi",
    "tv8":        "https://www.tv8.com.tr/yayin-akisi",
    "kanal7":     "https://www.kanal7.com/yayin-akisi",
    "ntv":        "https://www.ntv.com.tr/yayin-akisi",
    "cnnturk":    "https://www.cnnturk.com/yayin-akisi",
    "haberturk":  "https://www.haberturk.com/tv/yayin-akisi",
    "ahaber":     "https://www.ahaber.com.tr/yayin-akisi",
    "halktv":     "https://www.halktv.com.tr/yayin-akisi",
    "sozcutv":    "https://www.sozcutv.com.tr/yayin-akisi",
    "tv100":      "https://www.tv100.com/yayin-akisi",
    "tgrthaber":  "https://www.tgrthaber.com.tr/yayin-akisi",
    "haberglobal":"https://www.haberglobal.com.tr/yayin-akisi",
    "360tv":      "https://www.360.com.tr/yayin-akisi",
    "teve2":      "https://www.teve2.com.tr/yayin-akisi",
    "tv85":       "https://www.tv8.com.tr/tv85/yayin-akisi",
    "aspor":      "https://www.aspor.com.tr/yayin-akisi",
    "htspor":     "https://www.htspor.com.tr/yayin-akisi",
    "fbtv":       "https://www.fbtv.com.tr/yayin-akisi",
    "diyanettv":  "https://www.diyanettv.com.tr/yayin-akisi",
    "akittv":     "https://www.akittv.com.tr/yayin-akisi",
    "beyaztv":    "https://www.beyaztv.com.tr/yayin-akisi",
}

def scrape_generic(scraper_key: str, date: datetime) -> list:
    """
    Genel HTML scraper: yayin-akisi sayfasını parse eder.
    """
    url = SCRAPER_URLS.get(scraper_key)
    if not url:
        return []

    programs = []
    try:
        session = get_session()
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"  [{scraper_key}] HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Yaygın CSS seçiciler dene
        selectors = [
            (".schedule-list li", ".time", ".title"),
            (".yayin-akisi li", ".saat", ".program-adi"),
            ("[class*='schedule'] li", "[class*='time']", "[class*='name']"),
            (".program-list .item", ".hour", "h3"),
            ("table.schedule tr", "td:nth-child(1)", "td:nth-child(2)"),
        ]

        for container_sel, time_sel, title_sel in selectors:
            items = soup.select(container_sel)
            if not items:
                continue
            found = 0
            for item in items:
                time_el  = item.select_one(time_sel)
                title_el = item.select_one(title_sel)
                if time_el and title_el:
                    t = time_el.get_text(strip=True)
                    n = title_el.get_text(strip=True)
                    if re.match(r"\d{1,2}[:.]\d{2}", t) and len(n) > 1:
                        programs.append({"title": n, "start": t, "end": ""})
                        found += 1
            if found > 3:
                break

        # JSON-LD veya script içi veri dene
        if not programs:
            for script in soup.find_all("script"):
                txt = script.string or ""
                if "startTime" in txt or "startDate" in txt:
                    try:
                        data = json.loads(txt)
                        items = data if isinstance(data, list) else data.get("schedule", data.get("programs", []))
                        for item in items:
                            title = item.get("name") or item.get("title") or ""
                            start = item.get("startTime") or item.get("startDate") or ""
                            if title and start:
                                programs.append({"title": title, "start": start, "end": item.get("endTime", "")})
                    except Exception:
                        pass
                    if programs:
                        break

        print(f"  [{scraper_key}]: {len(programs)} program")
    except Exception as e:
        print(f"  [{scraper_key}] hata: {e}")

    return programs


# ─────────────────────────────────────────
#  PROGRAM LİSTESİNİ ZAMAN DİLİMİNE DÖNÜŞTÜR
# ─────────────────────────────────────────

def normalize_programs(raw_programs: list, base_date: datetime) -> list:
    """
    Ham program listesini (title, start string, end string) →
    (title, start datetime, end datetime) listesine çevirir.
    """
    result = []
    base = TURKEY_TZ.localize(base_date.replace(hour=0, minute=0, second=0, microsecond=0))

    for i, prog in enumerate(raw_programs):
        title = prog.get("title", "").strip()
        start_raw = prog.get("start", "")
        end_raw   = prog.get("end", "")

        if not title or not start_raw:
            continue

        # ISO datetime mı?
        try:
            if "T" in start_raw or len(start_raw) >= 14:
                start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    start_dt = TURKEY_TZ.localize(start_dt)
            else:
                start_dt = parse_time_str(start_raw, base)
                if start_dt is None:
                    continue
                # Gece yarısını geç (örn 01:00 bir sonraki güne ait)
                if result and start_dt < result[-1][1]:
                    start_dt += timedelta(days=1)
        except Exception:
            continue

        if end_raw:
            try:
                if "T" in end_raw or len(end_raw) >= 14:
                    end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                    if end_dt.tzinfo is None:
                        end_dt = TURKEY_TZ.localize(end_dt)
                else:
                    end_dt = parse_time_str(end_raw, base)
                    if end_dt and end_dt < start_dt:
                        end_dt += timedelta(days=1)
            except Exception:
                end_dt = None
        else:
            end_dt = None

        result.append((title, start_dt, end_dt))

    # Bitiş zamanı boşsa bir sonrakinin başlangıcını kullan
    for i in range(len(result) - 1):
        if result[i][2] is None:
            result[i] = (result[i][0], result[i][1], result[i + 1][1])
    # Son programın bitişi: +2 saat
    if result and result[-1][2] is None:
        last = result[-1]
        result[-1] = (last[0], last[1], last[1] + timedelta(hours=2))

    return result


# ─────────────────────────────────────────
#  XMLTV ÜRET
# ─────────────────────────────────────────

def build_xmltv(all_programs: dict) -> str:
    """
    all_programs: {channel_id: [(title, start_dt, end_dt), ...]}
    → XMLTV XML string
    """
    tv = Element("tv", attrib={"generator-info-name": "BelesTiVi EPG Scraper"})

    # Kanal tanımları
    for ch_id, ch_info in CHANNELS.items():
        if ch_id not in all_programs or not all_programs[ch_id]:
            continue
        channel = SubElement(tv, "channel", id=ch_id)
        name = SubElement(channel, "display-name", lang="tr")
        name.text = ch_info["name"]

    # Programlar
    for ch_id, programs in all_programs.items():
        for title, start, end in programs:
            prog = SubElement(tv, "programme", **{
                "start":   to_xmltv_time(start),
                "stop":    to_xmltv_time(end),
                "channel": ch_id
            })
            t = SubElement(prog, "title", lang="tr")
            t.text = title

    # Güzel formatlı XML
    rough = tostring(tv, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding=None).replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')


# ─────────────────────────────────────────
#  ANA DÖNGÜ
# ─────────────────────────────────────────

def main():
    now = datetime.now(TURKEY_TZ)
    # Bugün ve yarın için veri çek (2 günlük EPG)
    dates = [now.date(), (now + timedelta(days=1)).date()]

    all_programs = {}  # {channel_id: [(title, start, end), ...]}

    for ch_id, ch_info in CHANNELS.items():
        print(f"\n[{ch_id}] {ch_info['name']} çekiliyor...")
        ch_programs = []

        for d in dates:
            base_dt = datetime(d.year, d.month, d.day)

            if ch_info["scraper"] == "trt":
                raw = scrape_trt(ch_id, ch_info["trt_id"], base_dt)
            else:
                raw = scrape_generic(ch_info["scraper"], base_dt)

            if raw:
                normalized = normalize_programs(raw, base_dt)
                ch_programs.extend(normalized)

            time.sleep(0.5)  # Sunucuya fazla yük bindirme

        if ch_programs:
            all_programs[ch_id] = ch_programs
            print(f"  → Toplam {len(ch_programs)} program")
        else:
            print(f"  → Veri alınamadı")

    # XML üret
    xmltv_content = build_xmltv(all_programs)

    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xmltv_content)

    total = sum(len(v) for v in all_programs.values())
    print(f"\n✅ epg.xml oluşturuldu: {len(all_programs)} kanal, {total} program")


if __name__ == "__main__":
    main()
