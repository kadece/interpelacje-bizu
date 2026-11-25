"""Parser strony szczegółów dokumentu w BIP (metadane + linki do PDF)."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _text(element) -> str:
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def parse_detail(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.bip-article") or soup

    fields = {}
    for tile in article.select(".bip-article-data-tile"):
        label = _text(tile.find(["dt", "h3"]))
        value = _text(tile.find(["dd", "p"]))
        if label and value and label not in fields:
            fields[label] = value

    files = []
    for link in article.select("a[href]"):
        href = link.get("href", "")
        if ".pdf" not in href.lower():
            continue
        tile = link.find_parent(class_="sublist-container") or link.find_parent(class_="sublist-item") or link.find_parent(class_="bip-article-data-tile")
        label = _text(tile.find(["dt", "h3"])) if tile else ""
        filename = _text(link)
        if tile:
            for span in tile.select("span, p"):
                candidate = _text(span)
                if candidate.lower().endswith(".pdf"):
                    filename = candidate
                    break
        files.append((label, urljoin(url, href), filename))

    pismo = next((f for f in files if "odpowiedz" not in _normalize(label)), None)
    odpowiedz = next((f for f in files if "odpowiedz" in _normalize(f[0])), None)
    if odpowiedz is None:
        odpowiedz = next((f for f in files if f[2].lower().endswith("a.pdf")), None)

    status_raw = fields.get("Odpowiedź", "")
    if "udzielono" in status_raw.lower() and status_raw.strip().lower() != "nie udzielono":
        status = "udzielono"
    else:
        status = "nie udzielono" if status_raw else ""
    numer = re.sub(r"\D", "", fields.get("Numer", ""))
    return {
        "typ": (fields.get("Interpelacja/zapytanie") or "").strip().lower() or None,
        "numer": int(numer) if numer else None,
        "data": fields.get("Data"),
        "temat": fields.get("W sprawie"),
        "radny": fields.get("Radny"),
        "klub": fields.get("Klub"),
        "kadencja": fields.get("Kadencja"),
        "status": status,
        "pdf_pismo_url": pismo[1] if pismo else None,
        "pdf_pismo_nazwa": pismo[2] if pismo else None,
        "pdf_odpowiedz_url": odpowiedz[1] if odpowiedz else None,
        "pdf_odpowiedz_nazwa": odpowiedz[2] if odpowiedz else None,
    }


def _normalize(text: str) -> str:
    return (text or "").lower()
