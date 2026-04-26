from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(tags=["legal"])


def _render_page(*, title: str, intro: str, sections: list[tuple[str, list[str]]]) -> HTMLResponse:
    section_html = []
    for heading, paragraphs in sections:
        paragraphs_html = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        section_html.append(f"<section><h2>{escape(heading)}</h2>{paragraphs_html}</section>")

    body = "".join(section_html)
    app_name = escape(settings.project_name)
    page_title = escape(title)
    intro_text = escape(intro)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title} | {app_name}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f3eb;
      --surface: #fffdf8;
      --text: #1f2937;
      --muted: #5b6472;
      --line: #d7d2c8;
      --accent: #b45309;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top, rgba(180, 83, 9, 0.12), transparent 35%),
        var(--bg);
      color: var(--text);
      line-height: 1.65;
    }}
    main {{
      max-width: 820px;
      margin: 0 auto;
      padding: 48px 20px 72px;
    }}
    article {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 32px 24px;
      box-shadow: 0 20px 45px rgba(31, 41, 55, 0.08);
    }}
    h1, h2 {{
      margin: 0 0 16px;
      line-height: 1.2;
    }}
    h1 {{
      font-size: clamp(2rem, 4vw, 3rem);
    }}
    h2 {{
      font-size: 1.25rem;
      color: var(--accent);
      margin-top: 28px;
    }}
    p {{
      margin: 0 0 14px;
    }}
    .intro {{
      color: var(--muted);
      font-size: 1.05rem;
      margin-bottom: 24px;
    }}
    footer {{
      margin-top: 32px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
  </style>
</head>
<body>
  <main>
    <article>
      <h1>{page_title}</h1>
      <p class="intro">{intro_text}</p>
      {body}
      <footer>
        These pages are served directly by the backend application for public access.
      </footer>
    </article>
  </main>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy() -> HTMLResponse:
    return _render_page(
        title="Privacy Policy",
        intro="This page explains the baseline privacy practices for this service.",
        sections=[
            (
                "Information We Collect",
                [
                    "When you sign in with Google, the service may receive your basic profile information such as your email address, display name, and Google account identifier.",
                    "The service also stores session data, application content you create, and technical logs needed to operate, secure, and troubleshoot the platform.",
                ],
            ),
            (
                "How We Use Information",
                [
                    "We use collected information to authenticate users, provide core product features, maintain account access, and improve reliability and security.",
                    "Information may also be used to investigate abuse, respond to support requests, and comply with legal obligations.",
                ],
            ),
            (
                "Sharing and Retention",
                [
                    "We do not sell personal information. Data may be shared with infrastructure or service providers strictly as needed to run the application.",
                    "Information is retained only for as long as necessary to provide the service, satisfy operational needs, or comply with applicable law.",
                ],
            ),
            (
                "Your Choices",
                [
                    "You may stop using the service at any time. If you need account or data assistance, contact the service administrator through the support channel associated with this deployment.",
                ],
            ),
        ],
    )


@router.get("/terms", response_class=HTMLResponse)
async def terms_of_service() -> HTMLResponse:
    return _render_page(
        title="Terms of Service",
        intro="These terms describe the basic rules for using this service.",
        sections=[
            (
                "Use of the Service",
                [
                    "By accessing or using this service, you agree to use it only for lawful purposes and in a way that does not interfere with the service or other users.",
                    "Access may require a supported sign-in method, and you are responsible for activity that occurs under your account.",
                ],
            ),
            (
                "Acceptable Conduct",
                [
                    "You agree not to attempt unauthorized access, disrupt normal operation, upload harmful material, or misuse the platform for fraudulent or abusive activity.",
                ],
            ),
            (
                "Availability and Changes",
                [
                    "The service may be updated, suspended, or discontinued at any time. Features and access policies may change as the product evolves.",
                ],
            ),
            (
                "Limitation and Termination",
                [
                    "The service is provided on an as-available basis unless separate written terms state otherwise. Access may be suspended or terminated for misuse, security concerns, or operational reasons.",
                ],
            ),
            (
                "Contact",
                [
                    "Questions about these terms should be directed to the service administrator or support contact associated with this deployment.",
                ],
            ),
        ],
    )
