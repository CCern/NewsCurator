"""
News Curator — Punto de entrada principal.

Uso:
  python main.py              → corre completo y envía email
  python main.py --preview    → genera preview HTML sin enviar email
  python main.py --dry-run    → solo fetching y scoring, sin email
"""
import os
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
import argparse
from dotenv import load_dotenv

load_dotenv()

from fetcher import fetch_rss_feeds, fetch_newsapi, try_fetch_full_content
from curator import score_articles, select_top_articles, generate_summaries, generate_geopolitics_intro
from emailer import build_email_html, send_email, save_html_preview

FEEDBACK_ENDPOINT = os.getenv("FEEDBACK_ENDPOINT", "https://placeholder.com/feedback")


def main(preview_only: bool = False, dry_run: bool = False):
    print("=" * 60)
    print("NEWS CURATOR — Iniciando")
    print("=" * 60)

    # 1. Fetch noticias
    print("\n[1/5] Fetching noticias...")
    rss_articles = fetch_rss_feeds()
    newsapi_articles = fetch_newsapi()

    all_articles = rss_articles + newsapi_articles
    # Deduplicar por URL
    seen = set()
    unique_articles = []
    for a in all_articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique_articles.append(a)

    print(f"\nTotal artículos únicos fetched: {len(unique_articles)}")

    if not unique_articles:
        print("No se encontraron artículos. Abortando.")
        return

    if dry_run:
        print("\n[DRY RUN] Mostrando primeros 10 artículos:")
        for a in unique_articles[:10]:
            print(f"  - [{a['source']}] {a['title'][:80]}")
        return

    # 2. Scoring con Claude
    print("\n[2/5] Scoring con Claude...")
    scored = score_articles(unique_articles)

    # 3. Selección top artículos
    print("\n[3/5] Seleccionando top artículos...")
    top_articles = select_top_articles(scored)

    if not top_articles:
        print("No se encontraron artículos con score suficiente. Revisá el umbral en config.py")
        return

    # 4. Enriquecer con contenido completo (para mejor resumen)
    print("\n[4/5] Enriqueciendo con contenido completo...")
    for article in top_articles:
        content = try_fetch_full_content(article["url"])
        if content:
            article["full_content"] = content
            print(f"  [OK] Contenido obtenido: {article['title'][:60]}")
        else:
            print(f"  [~] Usando snippet: {article['title'][:60]}")

    # Generar resúmenes ejecutivos
    top_articles = generate_summaries(top_articles)

    # Generar intro geopolítica
    geopolitics_intro = generate_geopolitics_intro(scored)

    # 5. Generar y enviar email
    print("\n[5/5] Generando email...")
    html = build_email_html(geopolitics_intro, top_articles, FEEDBACK_ENDPOINT)

    # Siempre guardar preview local
    save_html_preview(html)

    if preview_only:
        print("\n[PREVIEW] Email generado. Abrí preview.html para verlo.")
        print("Para enviar, corrí: python main.py")
    else:
        send_email(html)

    print("\n" + "=" * 60)
    print("COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="News Curator")
    parser.add_argument("--preview", action="store_true", help="Genera preview sin enviar email")
    parser.add_argument("--dry-run", action="store_true", help="Solo fetch y scoring, sin email")
    args = parser.parse_args()
    main(preview_only=args.preview, dry_run=args.dry_run)
