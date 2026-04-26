"""
Curaduría con Claude: scoring de relevancia, generación de resúmenes y selección final.
"""
import os
import json
import anthropic
from config import TOPICS, SELECTION
from feedback_store import load_feedback, build_feedback_context

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

USER_PROFILE = """
El usuario es Carlos, ejecutivo senior en Mercado Pago / Insurtech. Sus intereses:

TEMAS (en orden de importancia):
1. AI: editoriales y análisis estratégico. Fuentes curadas como Citrini Research. No quiere noticias triviales de producto.
2. Negocios/Estrategia: Big Tech, bancos, tecnológicas chinas. Análisis estratégico, no press releases.
3. Ciencia/Research: estudios con impacto social real (ej: niños y redes sociales, desintermediación farmacéutica).
4. Bitcoin: principalmente BTC. Evitar ruido de altcoins y DeFi genérico.

PERFIL DE SELECCIÓN:
- Prefiere análisis > noticias de último momento
- Valora autores como Harari, Dan Ariely, perspectivas de Raoul Pal, Elon Musk (trasfondo, no tweets)
- Fuentes de calidad: The Economist, FT, Reuters, Scientific American, Wired
- Idiomas: español, inglés, portugués
- EXCLUIR: clickbait, sensacionalismo, noticias sin sustancia, artículos de < 400 palabras
"""

SCORE_SYSTEM = """Eres un curador de noticias de élite. Tu tarea es evaluar artículos para un ejecutivo senior.

{user_profile}

Respondé SOLO con un JSON válido con este formato exacto:
{{
  "score": <número del 0 al 10>,
  "category": "<AI|Negocios|Ciencia|Bitcoin|Geopolítica|Descartado>",
  "reason": "<por qué merece o no ser incluido, max 20 palabras>"
}}

Criterios de scoring:
- 9-10: Análisis profundo, fuente de élite, muy relevante para el perfil
- 7-8: Relevante y bien fundamentado
- 5-6: Interesante pero no urgente
- 0-4: Trivial, clickbait, o no alineado con el perfil"""

SCORE_USER = """Artículo a evaluar:
- Título: {title}
- Fuente: {source}
- Resumen/snippet: {summary}"""

SUMMARY_PROMPT = """
Eres el asistente personal de noticias de Carlos, ejecutivo senior en fintech/insurtech.

Tu objetivo es que Carlos NO necesite abrir el artículo para entender el valor completo.
Escribí un resumen ejecutivo en 5-6 oraciones que cubra:
1. El hecho o hallazgo central (qué pasó o qué dice el paper/análisis)
2. Por qué importa estratégicamente (la implicancia de fondo)
3. El contexto relevante (quiénes son los actores, qué venía antes)
4. Una perspectiva crítica o dato sorprendente si existe

Reglas:
- Empezá directo, sin "El artículo dice que..." ni "Según..."
- Mismo idioma que el artículo (español o inglés)
- Tono ejecutivo, no periodístico

Artículo:
- Título: {title}
- Fuente: {source}
- Contenido: {content}

Respondé SOLO con el resumen, sin títulos ni formato especial.
"""

GEOPOLITICS_PROMPT = """
Eres un analista geopolítico senior. Basándote en estos titulares de los últimos 2 días,
escribí un párrafo introductorio de 2-3 líneas con lo más relevante que sucedió en el mundo.
Tono: conciso, ejecutivo, sin sensacionalismo. En español.

Titulares disponibles:
{headlines}

Respondé SOLO con el párrafo, sin títulos ni formato especial.
"""


def score_articles(articles: list[dict]) -> list[dict]:
    """Puntúa cada artículo por relevancia usando Claude."""
    print(f"\nScoring {len(articles)} artículos con Claude...")

    feedback = load_feedback()
    feedback_context = build_feedback_context(feedback)
    if feedback_context:
        print("  [✓] Feedback histórico cargado — ajustando scoring")
    effective_profile = USER_PROFILE + feedback_context

    # Construir system_text UNA vez para toda la corrida (mismo para los ~150 artículos).
    # cache_control lo cachea si supera 1024 tokens; si no, es no-op seguro.
    system_text = SCORE_SYSTEM.format(user_profile=effective_profile)
    scored = []
    cache_hits = 0

    for i, article in enumerate(articles):
        try:
            user_text = SCORE_USER.format(
                title=article["title"],
                source=article["source"],
                summary=article["summary"][:500],
            )
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                system=[{
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_text}],
            )
            if getattr(response.usage, "cache_read_input_tokens", 0) > 0:
                cache_hits += 1
            raw = response.content[0].text.strip()
            # Limpiar markdown si Claude envuelve en ```json ... ```
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            result = json.loads(raw)
            article["score"] = result.get("score", 0)
            article["category"] = result.get("category", "general")
            article["score_reason"] = result.get("reason", "")
            scored.append(article)

            if (i + 1) % 10 == 0:
                print(f"  Scored {i + 1}/{len(articles)}...")
        except Exception as e:
            print(f"  Error scoring '{article['title'][:50]}': {e} | raw: '{raw[:80] if 'raw' in dir() else 'no response'}'")
            article["score"] = 0
            article["category"] = "Descartado"
            scored.append(article)

    if cache_hits > 0:
        print(f"  [cache] {cache_hits}/{len(articles)} hits — prefix cacheado correctamente")
    return scored


def select_top_articles(scored_articles: list[dict]) -> list[dict]:
    """
    Selecciona los mejores artículos con diversidad de categorías.
    Objetivo: entre 3 y 5 artículos, con al menos 2 categorías distintas.
    """
    min_score = SELECTION["min_relevance_score"]

    # Filtrar por score mínimo y excluir descartados
    candidates = [
        a for a in scored_articles
        if a.get("score", 0) >= min_score and a.get("category") != "Descartado"
    ]

    # Ordenar por score descendente
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Selección con diversidad: máximo 2 artículos por categoría
    selected = []
    category_counts = {}
    for article in candidates:
        cat = article.get("category", "general")
        if category_counts.get(cat, 0) >= 2:
            continue
        selected.append(article)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if len(selected) >= SELECTION["max_articles"]:
            break

    print(f"\nSeleccionados: {len(selected)} artículos (de {len(candidates)} candidatos)")
    for a in selected:
        print(f"  [{a['score']}/10] [{a['category']}] {a['title'][:70]}")

    return selected


def generate_summaries(articles: list[dict]) -> list[dict]:
    """Genera resúmenes ejecutivos para los artículos seleccionados."""
    print("\nGenerando resúmenes...")

    for article in articles:
        try:
            content = article.get("full_content") or article.get("summary", "")
            prompt = SUMMARY_PROMPT.format(
                title=article["title"],
                source=article["source"],
                content=content[:2000],
            )
            response = client.messages.create(
                model="claude-sonnet-4-6",  # Sonnet para resúmenes de calidad
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            article["executive_summary"] = response.content[0].text.strip()
            print(f"  ✓ {article['title'][:60]}")
        except Exception as e:
            print(f"  Error en resumen: {e}")
            article["executive_summary"] = article.get("summary", "")[:300]

    return articles


def generate_geopolitics_intro(all_articles: list[dict]) -> str:
    """Genera el párrafo introductorio de geopolítica basado en los titulares disponibles."""
    print("\nGenerando intro geopolítica...")

    # Usar titulares de Reuters y fuentes generales como base
    general_sources = ["Reuters", "Reuters Tech", "Reuters Business", "The Economist", "Financial Times"]
    headlines = [
        a["title"] for a in all_articles
        if any(src in a.get("source", "") for src in general_sources)
    ][:20]

    if not headlines:
        headlines = [a["title"] for a in all_articles][:20]

    try:
        prompt = GEOPOLITICS_PROMPT.format(headlines="\n".join(f"- {h}" for h in headlines))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Error generando intro geopolítica: {e}")
        return "Resumen geopolítico no disponible en esta edición."
