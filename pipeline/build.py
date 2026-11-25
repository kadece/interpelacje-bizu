"""Budowa statycznej strony w site/ (Jinja2 -> HTML + JSON)."""
import json

from jinja2 import Environment, FileSystemLoader

from . import config


def _stats(documents: list) -> dict:
    answered = sum(1 for d in documents if d.get("status") == "udzielono")
    by_radny = {}
    for d in documents:
        name = d.get("radny") or "?"
        by_radny[name] = by_radny.get(name, 0) + 1
    return {"total": len(documents), "answered": answered, "by_radny": by_radny}


def build_site(documents: list, radni: list) -> None:
    env = Environment(
        loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    (config.SITE_DIR / "dokument").mkdir(parents=True, exist_ok=True)
    (config.SITE_DIR / "data").mkdir(exist_ok=True)
    (config.SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")

    index = []
    for d in documents:
        index.append({
            "id": d["id"],
            "typ": d.get("typ"),
            "numer": d.get("numer"),
            "data": d.get("data"),
            "radny": d.get("radny"),
            "temat": d.get("temat"),
            "obszary": d.get("obszary", []),
            "tematy": d.get("tematy", []),
            "status": d.get("status"),
            "pismo_url": "dokument/" + d["id"] + ".html",
            "podsumowanie": d.get("podsumowanie_pismo"),
        })
    with open(config.SITE_DIR / "data" / "index.json", "w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False)

    stats = _stats(documents)
    (config.SITE_DIR / "index.html").write_text(
        env.get_template("index.html").render(radni=radni, stats=stats),
        encoding="utf-8",
    )

    template = env.get_template("document.html")
    for d in documents:
        (config.SITE_DIR / "dokument" / (d["id"] + ".html")).write_text(
            template.render(document=d), encoding="utf-8",
        )

    for name in ("app.js", "style.css"):
        source = config.STATIC_DIR / name
        (config.SITE_DIR / name).write_bytes(source.read_bytes())
    (config.SITE_DIR / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
