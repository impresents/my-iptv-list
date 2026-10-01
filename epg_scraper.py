#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import xml.etree.ElementTree as ET
import re, json, os, tempfile, unicodedata, copy
from pathlib import Path
from datetime import datetime, timedelta, timezone

SAAT_AYARI = 3

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
    "Sözcü TV": ["szctv", "sozcu"], "TRT Spor Yıldız": ["trtyildiz", "trtspor2"]
}

def fix_time(time_str, offset_hours):
    try:
        # Örnek: 20260315120000 +0000
        clean_time = time_str.split(' ')[0]
        dt = datetime.strptime(clean_time, "%Y%m%d%H%M%S")
        dt = dt + timedelta(hours=offset_hours)
        return dt.strftime("%Y%m%d%H%M%S") + " +0300"
    except:
        return time_str

# Saat düzeltmesi TÜM yeni kaynaklarda yukarıdaki mevcut yöntemle uygulanır.
SOURCES = [(f"Turkey {n}", f"https://www.open-epg.com/files/turkey{n}.xml") for n in (3, 4, 5)]
ALIAS_MAP.update({"Kanal 24": ["24", "24 TV"], "TRT 3": ["TRT 3 Spor"],
                  "Bengütürk": ["Bengütürk TV"], "TELE1": ["TELE 1"]})
# 24 TV ve Kanal 24 aynı kanaldır; çift yayın akışı üretmeyiz.
CHANNELS_DATA.pop("24 TV", None)
CHANNELS_DATA.update({"BRT 1": "BRT1.tr", "BRT 2": "BRT2.tr"})

def normalize(text):
    text = re.sub(r"\.tr$", "", (text or "").strip(), flags=re.I)
    text = re.sub(r"\s+(?:HD|FHD|SD|4K|HEVC)\+?$", "", text, flags=re.I)
    text = unicodedata.normalize("NFKD", text).casefold().replace("ı", "i")
    return "".join(c for c in text if c.isalnum())

def instant(text):
    try:
        return datetime.strptime(text, "%Y%m%d%H%M%S %z")
    except (ValueError, TypeError):
        return None

def download(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        chunks, size = [], 0
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > 32 * 1024 * 1024:
                raise ValueError("XML boyut sınırı aşıldı")
            chunks.append(chunk)
    root = ET.fromstring(b"".join(chunks))
    if root.tag != "tv" or not root.findall("programme"):
        raise ValueError("Geçerli XMLTV programları bulunamadı")
    return root

def schedules(root, now, convert=True):
    aliases = {}
    for name, eid in CHANNELS_DATA.items():
        for alias in [name, eid] + ALIAS_MAP.get(name, []):
            aliases.setdefault(normalize(alias), set()).add(name)
    mapping, groups = {}, {}
    for channel in root.findall("channel"):
        cid = channel.get("id", "")
        names = [cid] + [x.text or "" for x in channel.findall("display-name")]
        matches = set().union(*(aliases.get(normalize(n), set()) for n in names))
        if len(matches) == 1:
            mapping[cid] = next(iter(matches))
    for programme in root.findall("programme"):
        cid = programme.get("channel")
        name = mapping.get(cid)
        if not name or not (programme.findtext("title") or "").strip():
            continue
        row = copy.deepcopy(programme)
        for attr in ("start", "stop"):
            value = row.get(attr)
            row.set(attr, (fix_time(value, SAAT_AYARI) if convert else value) or "")
        start, stop = instant(row.get("start")), instant(row.get("stop"))
        if not start or not stop or stop <= start:
            continue
        if stop < now - timedelta(hours=12) or start > now + timedelta(days=8):
            continue
        row.set("channel", name)  # Mevcut uygulamayla uyumlu kanal adları.
        groups.setdefault(name, {}).setdefault(cid, []).append(row)
    result = {}
    for name, variants in groups.items():
        # HD/SD kopyalarının programlarını birbirine karıştırma.
        candidates = []
        for cid, rows in variants.items():
            unique = {(r.get("start"), r.get("stop")): r for r in rows}
            rows = sorted(unique.values(), key=lambda r: instant(r.get("start")))
            current = any(instant(r.get("start")) <= now < instant(r.get("stop")) for r in rows)
            future = sum(instant(r.get("stop")) > now for r in rows)
            if future:
                candidates.append((current, future, cid, rows))
        if candidates:
            result[name] = max(candidates, key=lambda c: (c[0], c[1], c[2]))[3]
    return result

def atomic_write(path, data):
    path = Path(path)
    fd, temp = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def build(now, fetch=download, old_root=None):
    selected, origins, errors = {}, {}, {}
    for label, url in SOURCES:
        try:
            found = schedules(fetch(url), now)
            for name, rows in found.items():
                # Güncel program yoksa bir alt kaynak güncel akışı tamamlayabilir.
                has_now = lambda rs: any(instant(r.get("start")) <= now < instant(r.get("stop")) for r in rs)
                if name not in selected or (not has_now(selected[name]) and has_now(rows)):
                    selected[name], origins[name] = rows, label
        except Exception as error:
            errors[label] = type(error).__name__ + ": " + str(error)
    live_count = len(selected)
    if old_root is not None:
        for name, rows in schedules(old_root, now, convert=False).items():
            if name not in selected:
                selected[name], origins[name] = rows, "Önceki sağlam dosya"
    report = {"updated_utc": now.isoformat(), "channel_count": len(selected),
              "sources": origins, "errors": errors,
              "missing": sorted(set(CHANNELS_DATA) - set(selected)),
              "last_programme": {name: max(r.get("stop") for r in rows) for name, rows in selected.items()}}
    if live_count < 20 or len(selected) < 30:
        raise ValueError("Yeterli güncel kanal alınamadı; epg.xml korunuyor. " + json.dumps(errors, ensure_ascii=False))
    root = ET.Element("tv", {"generator-info-name": "BelesTiVi EPG"})
    for name in sorted(selected):
        channel = ET.SubElement(root, "channel", {"id": name})
        ET.SubElement(channel, "display-name").text = name
        root.extend(selected[name])
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), report

def main():
    now = datetime.now(timezone.utc)
    try:
        old = ET.parse("epg.xml").getroot()
    except (OSError, ET.ParseError):
        old = None
    xml, report = build(now, old_root=old)
    atomic_write("epg.xml", xml)
    atomic_write("epg-report.json", json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"EPG: {report['channel_count']} kanal. Eksik: {len(report['missing'])}")
    for source, error in report["errors"].items():
        print(f"UYARI {source}: {error}")

if __name__ == "__main__":
    main()
