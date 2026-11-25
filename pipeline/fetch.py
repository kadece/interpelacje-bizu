"""Pobieranie listy interpelacji/zapytań BiZU z wyszukiwarki BIP (Liferay)."""
import re

from . import config, http

_PORTLET_RE = re.compile(r"(_web_content_search_portlet_INSTANCE_[0-9A-Za-z]+)")
_TOTAL_RE = re.compile(r"Poka&#379; wyniki \((\d+)\)|Poka&#380; wyniki \((\d+)\)|Pokaż wyniki \((\d+)\)")
_ROW_RE = re.compile(
    r'href="(?P<sciezka>/web/ursus/-/'
    r"(?P<slug>[a-z0-9-]+?)-(?P<typ>interpelacja|zapytanie|wniosek)-nr-(?P<numer>\d+))"
    r'"'
)


def discover_portlet() -> str:
    html = http.get_text(config.SEARCH_URL)
    match = _PORTLET_RE.search(html)
    if not match:
        raise RuntimeError("Nie znaleziono portletu wyszukiwarki na stronie BIP - zmiana layoutu? HTML: " + html[:300])
    return match.group(1)


def list_page_url(portlet: str, page: int, *, order: str = "desc") -> str:
    params = "&".join([
        "p_p_id=" + portlet,
        "p_p_lifecycle=0",
        "p_p_state=normal",
        "p_p_mode=view",
        portlet + "_mvcPath=/view.jsp",
        portlet + "_cur=" + str(page),
        portlet + "_sortType=date",
        portlet + "_orderByType=" + order,
        portlet + "_categoryIds=,,,,%d,%d" % (config.KADENCJA_ID, config.CLUB_BIZU_ID),
        portlet + "_district-configuration=%d" % config.DISTRICT_URSUS_ID,
    ])
    return config.SEARCH_URL + "?" + params


def parse_list_page(html: str):
    total = None
    match = _TOTAL_RE.search(html)
    if match:
        total = int(next(group for group in match.groups() if group))
    documents = []
    seen_on_page = set()
    for row in _ROW_RE.finditer(html):
        path = row.group("sciezka")
        document = {
            "id": "%s-%s" % (row.group("typ"), row.group("numer")),
            "typ": row.group("typ"),
            "numer": int(row.group("numer")),
            "slug": path[len(config.DETAIL_PREFIX):],
            "url_bip": config.BIP_BASE + path,
        }
        if document["id"] in seen_on_page:
            continue
        seen_on_page.add(document["id"])
        documents.append(document)
    return total, documents


def fetch_all(*, order: str = "desc", max_pages: int = 200) -> list:
    """Zwraca wszystkie dokumenty BiZU kadencji 2024-2029 (posortowane wg daty)."""
    portlet = discover_portlet()
    collected = []
    seen = set()
    page = 1
    while page <= max_pages:
        total, documents = parse_list_page(http.get_text(list_page_url(portlet, page, order=order)))
        fresh = [document for document in documents if document["id"] not in seen]
        if not fresh:
            break
        for document in fresh:
            seen.add(document["id"])
            collected.append(document)
        if total is not None and len(seen) >= total:
            break
        page = page + 1
    return collected
