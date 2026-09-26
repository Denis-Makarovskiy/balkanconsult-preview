"""Fail closed before publishing the static portal preview.

With --stage, compare every dossier and information page to the reviewed source
JSON, then seal the exact public files. CI verifies the seal and every route.
The source comparison proves rendering fidelity, not legal correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

LANGUAGES = ("ru", "me", "en")
PUBLIC_ROOTS = ("ru", "me", "en", "static")
PUBLIC_TOP = ("index.html", "404.html", ".nojekyll")
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
ATTR = re.compile(r'(?:href|src|action)="([^"]+)"')
MARKERS = {"ru": "Это ИИ-проект", "me": "Ovo je AI projekat", "en": "This is an AI project"}


def public_files(site: Path) -> list[Path]:
    paths = [site / name for name in PUBLIC_TOP]
    for name in PUBLIC_ROOTS:
        paths.extend(p for p in (site / name).rglob("*") if p.is_file())
    return sorted(paths)


def plain(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html.unescape(raw))).strip()


def audit(site: Path, repo: str, stage: Path | None) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    files = public_files(site)
    if any(not p.is_file() for p in files):
        errors.append("required public file is missing")
    html_files = [p for p in files if p.suffix == ".html"]
    css_path = site / "static/portal.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        if len(re.findall(r"(?m)^\s*\.title\s*\{", css)) < 3 or not re.search(r"(?m)^\s*\.flow\s*\{", css):
            errors.append("portal.css: page title or flow selector missing")
        if re.search(r"(?m)^\s*(?:title|flow)\s*\{", css):
            errors.append("portal.css: unscoped title or flow selector")
    counts = {"html": len(html_files), "dossiers": 0, "info": 0, "sections": 0, "laws": 0}
    for file in html_files:
        relative = file.relative_to(site).as_posix()
        source = file.read_text(encoding="utf-8")
        rendered = plain(source)
        if NOINDEX not in source:
            errors.append(f"{relative}: noindex missing")
        if "portal.example.test" in source or "127.0.0.1" in source or "core-inbox" in source:
            errors.append(f"{relative}: local or placeholder value leaked")
        if not re.search(r"<title>[^<]+</title>", source):
            errors.append(f"{relative}: title missing")
        parts = Path(relative).parts
        if parts[0] in LANGUAGES:
            lang = parts[0]
            if f'<html lang="{lang}"' not in source:
                errors.append(f"{relative}: wrong HTML language")
            if MARKERS[lang] not in rendered:
                errors.append(f"{relative}: AI notice missing")
            if "<h1" not in source:
                errors.append(f"{relative}: page heading missing")
            if len(parts) > 2:
                kind = {"dossier": "dossiers", "info": "info", "sections": "sections",
                        "law": "laws"}.get(parts[1])
                if kind:
                    counts[kind] += 1
            if len(parts) > 2 and parts[1] == "dossier":
                for n in range(1, 6):
                    if f'id="p{n}"' not in source:
                        errors.append(f"{relative}: dossier part {n} missing")
            if len(parts) > 2 and parts[1] == "law" and parts[2] not in rendered:
                errors.append(f"{relative}: law identifier missing")
            if len(parts) > 2 and parts[1] == "law" and lang in ("me", "en"):
                if re.search(r'<aside class="toc".*?</aside>', source, re.S) and any(
                    label in re.search(r'<aside class="toc".*?</aside>', source, re.S).group(0)
                    for label in ("Редакции", "Связи", "Используется в досье")
                ):
                    errors.append(f"{relative}: Russian navigation in translated law page")
        for url in ATTR.findall(source):
            if not url.startswith(f"/{repo}/"):
                if url.startswith(("/ru/", "/me/", "/en/", "/static/")):
                    errors.append(f"{relative}: unprefixed URL {url}")
                continue
            local = urlsplit(url).path.removeprefix(f"/{repo}/")
            target = site / local
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                errors.append(f"{relative}: broken URL {url}")

    expected = {"html": 380, "dossiers": 147, "info": 18, "sections": 36, "laws": 168}
    for key, value in expected.items():
        if counts[key] != value:
            errors.append(f"{key}: expected {value}, got {counts[key]}")
    if stage:
        manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("stage") != "v74-rc4" or manifest.get("pages") != 147:
            errors.append("source stage identity or page count differs")
        content = stage / "content"
        for row in manifest["pages_manifest"]:
            key, lang = row["subject_key"], row["lang"]
            file = site / lang / "dossier" / key / "index.html"
            if not file.is_file():
                errors.append(f"dossier missing: {lang}/{key}")
                continue
            data_name = key + ("." + lang if lang != "ru" else "") + ".json"
            data = json.loads((content / "dossiers" / data_name).read_text(encoding="utf-8"))
            raw = html.unescape(file.read_text(encoding="utf-8"))
            text = plain(raw)
            fields = [data["title"], data["summary"], data["parts"]["norms"]["note"]]
            fields += data["parts"].get("gaps", [])
            fields += [r["value"] for r in data["parts"]["conditions"]["rows"]]
            for value in fields:
                if re.sub(r"\s+", " ", value).strip() not in text:
                    errors.append(f"{lang}/{key}: source text missing: {value[:45]}")
            for source in data["sources"]:
                if source["url"] not in raw:
                    errors.append(f"{lang}/{key}: source URL missing: {source['url']}")
            yyyy, mm, dd = data["as_of"].split("-")
            if f"{dd}.{mm}.{yyyy}" not in text:
                errors.append(f"{lang}/{key}: as-of date missing")
        for lang in LANGUAGES:
            for slug in ("kto-my", "kak-my-rabotaem", "kak-proveryaem", "usloviya", "dannye", "kontakty"):
                suffix = "" if lang == "ru" else "." + lang
                data = json.loads((content / "info" / f"{slug}{suffix}.json").read_text(encoding="utf-8"))
                rendered = plain((site / lang / "info" / slug / "index.html").read_text(encoding="utf-8"))
                if data["title"] not in rendered or data["lead"] not in rendered:
                    errors.append(f"{lang}/info/{slug}: title or lead differs from source")
                for section in data["sections"]:
                    for paragraph in section.get("paragraphs", []):
                        if re.sub(r"\s+", " ", paragraph).strip() not in rendered:
                            errors.append(f"{lang}/info/{slug}: paragraph differs from source")
    return errors, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("."))
    parser.add_argument("--repo", default="balkanconsult-preview")
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--seal", action="store_true", help="record checked public file hashes; requires --stage")
    args = parser.parse_args()
    site = args.site.resolve()
    stage = args.stage.resolve() if args.stage else None
    errors, counts = audit(site, args.repo, stage)
    seal_path = site / "qa/approved-files.json"
    files = {p.relative_to(site).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in public_files(site)}
    if args.seal:
        if not stage:
            errors.append("--seal requires --stage source comparison")
        if not errors:
            seal_path.parent.mkdir(parents=True, exist_ok=True)
            seal_path.write_text(json.dumps({"stage": "v74-rc4", "date": str(date.today()),
                "scope": "all public files, every route, 147 dossier source parities, 18 info source parities",
                "claim_limit": "AI rendering and consistency audit; not a lawyer review or guarantee of legal correctness",
                "counts": counts, "sha256": files}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        if not seal_path.is_file():
            errors.append("approved file seal missing")
        else:
            seal = json.loads(seal_path.read_text(encoding="utf-8"))
            if seal.get("sha256") != files:
                errors.append("public files changed since full-page audit; rerun source comparison and reseal")
            if seal.get("counts") != counts:
                errors.append("page counts differ from approved audit")
    print(json.dumps({"ok": not errors, "counts": counts, "files": len(files),
                      "source_compared": stage is not None, "errors": errors[:30]}, ensure_ascii=False))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
