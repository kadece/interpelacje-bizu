"""Orkiestracja: BIP -> metadane -> OCR -> tagi -> podsumowania -> strona."""
import argparse
import datetime as dt
import json
import os
import sys
import traceback

from . import build, classify, config, fetch, http, ocr, parse, summarize


def load_documents() -> list:
    path = config.DATA_DIR / "interpelacje.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_documents(documents: list) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    documents.sort(key=lambda d: (d.get("data") or "", d.get("id") or ""), reverse=True)
    with open(config.DATA_DIR / "interpelacje.json", "w", encoding="utf-8") as handle:
        json.dump(documents, handle, ensure_ascii=False, indent=1)


def load_radni() -> list:
    path = config.DATA_DIR / "radni.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        return (json.load(handle) or {}).get("radni", [])


def _detail_needed(document, full_scan: bool) -> bool:
    if document is None or full_scan:
        return True
    if document.get("status") != "udzielono":
        return True  # odpowiedz moga wlasnie nadplynac
    if not document.get("tresc"):
        return True
    if not document.get("tresc_odpowiedzi"):
        return True
    return False


def _merge(existing, fields: dict, today: str) -> dict:
    if existing is None:
        document = dict(fields)
        document["pierwsze_pobranie"] = today
        document["created"] = today
        return document
    if existing.get("pdf_pismo_url") != fields.get("pdf_pismo_url"):
        existing["tresc"] = None
    if existing.get("pdf_odpowiedz_url") != fields.get("pdf_odpowiedz_url"):
        existing["tresc_odpowiedzi"] = None
        existing["podsumowanie_odpowiedz"] = None
    if existing.get("status") != "udzielono" and fields.get("status") == "udzielono":
        existing["tresc_odpowiedzi"] = None
        existing["podsumowanie_odpowiedz"] = None
    for key, value in fields.items():
        if value is not None:
            existing[key] = value
    existing["updated"] = today
    return existing


def _main() -> None:
    parser = argparse.ArgumentParser(description="Aktualizacja danych Interpelacje BiZU")
    parser.add_argument("--full", action="store_true", help="pelny reskan stron szczegolow")
    parser.add_argument("--no-ocr", action="store_true", help="pomin OCR skanow")
    parser.add_argument("--no-llm", action="store_true", help="pomin klasyfikacje/podsumowania LLM")
    parser.add_argument("--max-pages", type=int, default=None, help="limit stron listy (testy)")
    parser.add_argument("--max-docs", type=int, default=None, help="limit dokumentow (testy)")
    parser.add_argument("--build-only", action="store_true", help="tylko przebudowa strony")
    args = parser.parse_args()
    today = dt.date.today().isoformat()

    catalog = {d["id"]: d for d in load_documents()}
    radni = load_radni()

    if args.build_only:
        build.build_site(list(catalog.values()), radni)
        print("Strona przebudowana (%d dokumentow)" % len(catalog))
        return

    listing = fetch.fetch_all(max_pages=args.max_pages or 200)
    if args.max_docs:
        listing = listing[:args.max_docs]
    print("BIP: %d dokumentow (w bazie: %d)" % (len(listing), len(catalog)))

    taxonomy = classify.load_taxonomy()
    refreshed_ids = []
    for entry in listing:
        existing = catalog.get(entry["id"])
        if not _detail_needed(existing, args.full):
            continue
        html = http.get_text(entry["url_bip"])
        fields = parse.parse_detail(html, entry["url_bip"])
        fields["id"] = entry["id"]
        fields["slug"] = entry["slug"]
        fields.setdefault("url_bip", entry["url_bip"])
        catalog[entry["id"]] = _merge(existing, fields, today)
        refreshed_ids.append(entry["id"])
        print("+ %s: %s" % (entry["id"], fields.get("temat") or "?"))

    if not args.no_ocr:
        for document in catalog.values():
            if not document.get("tresc") and document.get("pdf_pismo_url"):
                try:
                    text, engine, quality = ocr.ocr_pdf(document["pdf_pismo_url"])
                except RuntimeError as error:
                    print("  ! OCR pisma %s: %s" % (document["id"], error))
                    text = None
                if text:
                    document["tresc"] = text
                    document["ocr_engine"] = engine
                    document["ocr_quality"] = quality
            if (document.get("status") == "udzielono" and not document.get("tresc_odpowiedzi")
                    and document.get("pdf_odpowiedz_url")):
                try:
                    text, engine, quality = ocr.ocr_pdf(document["pdf_odpowiedz_url"])
                except RuntimeError as error:
                    print("  ! OCR odpowiedzi %s: %s" % (document["id"], error))
                    text = None
                if text:
                    document["tresc_odpowiedzi"] = text
                    document["ocr_odpowiedz_engine"] = engine
                    document["ocr_odpowiedz_quality"] = quality

    use_llm = not args.no_llm and ocr.mistral_available()
    for document in catalog.values():
        if not document.get("obszary") or not document.get("tematy") or document["id"] in refreshed_ids:
            classify.classify(document, taxonomy, use_llm=use_llm)

    if use_llm:
        for document in catalog.values():
            need = document.get("podsumowanie_pismo") is None and document.get("tresc")
            if document.get("status") == "udzielono" and document.get("tresc_odpowiedzi"):
                need = need or document.get("podsumowanie_odpowiedz") is None
            if need:
                summarize.summarize(document)

    documents = list(catalog.values())
    classify.apply_overrides(documents, classify.load_overrides())
    save_documents(documents)
    build.build_site(documents, radni)

    for stale in ("diag.log", "bip_probe.log"):
        stale_path = config.DATA_DIR / stale
        if stale_path.exists():
            stale_path.unlink()

    answered = sum(1 for d in documents if d.get("status") == "udzielono")
    weak = [d["id"] for d in documents
            if d.get("ocr_quality") is not None and d["ocr_quality"] < 0.5]
    report = (
        "### Interpelacje BiZU - raport przebiegu\n\n"
        "- dokumentow w bazie: %d (z odpowiedzia: %d)\n"
        "- nowych/pobranych w tym przebiegu: %d\n"
        "- slaby OCR (do kontroli): %d\n"
        % (len(documents), answered, len(refreshed_ids), len(weak))
    )
    print(report)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(report)


def main() -> None:
    try:
        _main()
    except Exception:  # noqa: BLE001 - diagnostyka do repo; wyjatek propaguje dalej
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.DATA_DIR / "diag.log", "w", encoding="utf-8") as handle:
            handle.write(dt.datetime.now().isoformat() + " argv=" + " ".join(sys.argv) + "\n\n")
            traceback.print_exc(file=handle)
        raise


if __name__ == "__main__":
    main()
