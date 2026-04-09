"""
Generación y envío del email HTML con los artículos curados.
"""
import os
import resend
from datetime import datetime
from config import RECIPIENT_NAME

CATEGORY_ICONS = {
    "AI": "🤖",
    "Negocios": "📊",
    "Ciencia": "🔬",
    "Bitcoin": "₿",
    "Geopolítica": "🌍",
    "general": "📰",
}

CATEGORY_COLORS = {
    "AI": "#6366f1",
    "Negocios": "#0ea5e9",
    "Ciencia": "#10b981",
    "Bitcoin": "#f59e0b",
    "Geopolítica": "#8b5cf6",
    "general": "#6b7280",
}


def build_email_html(geopolitics_intro: str, articles: list[dict],
                     feedback_base_url: str, feedback_pat: str = "") -> str:
    """Construye el HTML del email."""
    date_str = datetime.now().strftime("%A %d de %B, %Y")
    today = datetime.now().strftime("%Y-%m-%d")
    articles_html = ""

    for i, article in enumerate(articles, 1):
        cat = article.get("category", "general")
        icon = CATEGORY_ICONS.get(cat, "📰")
        color = CATEGORY_COLORS.get(cat, "#6b7280")
        summary = article.get("executive_summary", article.get("summary", ""))[:800]
        url = article.get("url", "#")
        source = article.get("source", "")
        title = article.get("title", "Sin título")
        score = article.get("score", 0)

        # Para medios con paywall, redirigir via archive.ph que cachea el artículo completo
        PAYWALLED_DOMAINS = ["ft.com", "economist.com", "wsj.com", "bloomberg.com", "nytimes.com", "theverge.com", "wired.com"]
        is_paywalled = any(d in url for d in PAYWALLED_DOMAINS)
        read_url = f"https://archive.ph/newest/{url}" if is_paywalled else url
        paywall_badge = ' <span style="font-size:10px;background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:4px;">via archive</span>' if is_paywalled else ""

        # URLs de feedback con metadata completa + token para autenticación
        token_param = f"&token={feedback_pat}" if feedback_pat else ""
        like_url = (f"{feedback_base_url}?action=like&id={i}"
                    f"&title={_url_encode(title)}&source={_url_encode(source)}"
                    f"&category={_url_encode(cat)}&date={today}{token_param}")
        dislike_url = (f"{feedback_base_url}?action=dislike&id={i}"
                       f"&title={_url_encode(title)}&source={_url_encode(source)}"
                       f"&category={_url_encode(cat)}&date={today}{token_param}")

        articles_html += f"""
        <div style="background:#ffffff;border-radius:12px;padding:24px;margin-bottom:20px;
                    border-left:4px solid {color};box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;align-items:center;margin-bottom:10px;">
                <span style="background:{color};color:white;font-size:11px;font-weight:700;
                             padding:3px 10px;border-radius:20px;margin-right:10px;letter-spacing:0.5px;">
                    {icon} {cat.upper()}
                </span>
                <span style="color:#9ca3af;font-size:12px;">{source} · Relevancia {score}/10</span>
            </div>
            <h2 style="margin:0 0 12px 0;font-size:18px;font-weight:700;color:#111827;line-height:1.4;">
                <a href="{url}" target="_blank" rel="noopener" style="color:#111827;text-decoration:none;">{title}</a>
            </h2>
            <p style="margin:0 0 16px 0;color:#374151;font-size:14px;line-height:1.7;">
                {summary}
            </p>
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <a href="{read_url}" target="_blank" rel="noopener"
                   style="background:{color};color:white;padding:8px 18px;
                   border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
                    Leer artículo →{paywall_badge}
                </a>
                <a href="{like_url}" target="_blank" rel="noopener"
                   style="background:#f0fdf4;color:#16a34a;padding:8px 14px;
                   border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;
                   border:1px solid #bbf7d0;">
                    👍 Útil
                </a>
                <a href="{dislike_url}" target="_blank" rel="noopener"
                   style="background:#fef2f2;color:#dc2626;padding:8px 14px;
                   border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;
                   border:1px solid #fecaca;">
                    👎 No me sirve
                </a>
            </div>
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    <div style="max-width:640px;margin:0 auto;padding:24px 16px;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1e1b4b,#3730a3);border-radius:16px;
                    padding:32px;margin-bottom:24px;text-align:center;">
            <div style="font-size:28px;margin-bottom:8px;">📡</div>
            <h1 style="margin:0;color:white;font-size:22px;font-weight:800;letter-spacing:-0.5px;">
                Tu Briefing Curado
            </h1>
            <p style="margin:6px 0 0;color:#a5b4fc;font-size:13px;">{date_str}</p>
        </div>

        <!-- Geopolítica -->
        <div style="background:#1e293b;border-radius:12px;padding:20px 24px;margin-bottom:24px;">
            <div style="color:#94a3b8;font-size:11px;font-weight:700;letter-spacing:1px;
                        text-transform:uppercase;margin-bottom:10px;">🌍 Pulso Global</div>
            <p style="margin:0;color:#e2e8f0;font-size:14px;line-height:1.7;">
                {geopolitics_intro}
            </p>
        </div>

        <!-- Artículos -->
        <div style="margin-bottom:8px;color:#6b7280;font-size:11px;font-weight:700;
                    letter-spacing:1px;text-transform:uppercase;">
            Artículos seleccionados
        </div>
        {articles_html}

        <!-- Feedback cualitativo -->
        <div style="background:#f8fafc;border-radius:12px;padding:20px 24px;margin-bottom:20px;
                    border:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0 0 6px 0;color:#374151;font-size:14px;font-weight:600;">
                ¿Algo que mejorar en esta edición?
            </p>
            <p style="margin:0 0 14px 0;color:#6b7280;font-size:13px;">
                Tu feedback cualitativo se usa directamente para ajustar qué y cómo te curado.
            </p>
            <a href="{feedback_base_url}{'?token=' + feedback_pat if feedback_pat else ''}" target="_blank" rel="noopener"
               style="background:#1e1b4b;color:white;padding:10px 22px;border-radius:8px;
                      text-decoration:none;font-size:13px;font-weight:600;">
                Escribir feedback →
            </a>
        </div>

        <!-- Footer -->
        <div style="text-align:center;padding:20px;color:#9ca3af;font-size:12px;">
            <p style="margin:0;">Tu asistente de noticias personal · Curado por Claude</p>
            <p style="margin:4px 0 0;">Los 👍 👎 y tu feedback escrito mejoran la selección futura</p>
        </div>

    </div>
</body>
</html>
"""
    return html


def send_email(html_content: str, subject: str = None) -> bool:
    """Envía el email vía Resend."""
    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("RECIPIENT_EMAIL")

    if not all([api_key, recipient]):
        print("ERROR: Faltan RESEND_API_KEY o RECIPIENT_EMAIL en el .env")
        return False

    if not subject:
        subject = f"📡 Tu Briefing — {datetime.now().strftime('%d/%m')}"

    resend.api_key = api_key

    try:
        resend.Emails.send({
            "from": "Tu Briefing <onboarding@resend.dev>",
            "to": [recipient],
            "subject": subject,
            "html": html_content,
        })
        print(f"\n✅ Email enviado a {recipient}")
        return True
    except Exception as e:
        print(f"\n❌ Error enviando email: {e}")
        return False


def save_html_preview(html_content: str, path: str = "preview.html"):
    """Guarda el HTML localmente para preview antes de enviar."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\n📄 Preview guardado en: {path}")


def _url_encode(text: str) -> str:
    from urllib.parse import quote
    return quote(text[:100])
