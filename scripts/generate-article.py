#!/usr/bin/env python3
"""Generate a weekly blog article for lcpatrimoine.net using Claude API."""

import os
import re
import json
import glob
import xml.etree.ElementTree as ET
from datetime import date

import anthropic
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BLOG_DIR = "blog"
BLOG_HTML = "blog.html"
SITEMAP = "sitemap.xml"
SITE_URL = "https://www.lcpatrimoine.net"
STYLE_VERSION = "23"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Flux RSS : patrimoine, finance, économie, immobilier, fiscalité
RSS_FEEDS = [
    # Patrimoine & finances perso
    "https://www.lefigaro.fr/rss/figaro_placement.xml",
    "https://feed.prismamediadigital.com/v1/cap/rss?sources=capital&categories=votre-argent",
    "https://www.moneyvox.fr/actu/rss.php",
    # Économie générale
    "https://www.lefigaro.fr/rss/figaro_conjoncture.xml",
    "https://www.bfmtv.com/rss/economie/",
    "https://news.google.com/rss/search?q=patrimoine+OR+fiscalit%C3%A9+OR+%C3%A9pargne+OR+immobilier&hl=fr&gl=FR&ceid=FR:fr",
    # Immobilier
    "https://www.lefigaro.fr/rss/figaro_immobilier.xml",
    "https://edito.seloger.com/feed",
    # Fiscalité & droit
    "https://www.legifiscal.fr/rss.xml",
    "https://www.vie-publique.fr/actualites-feeds.xml",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_recent_headlines():
    """Fetch recent headlines + links from French financial RSS feeds."""
    headlines = []
    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0 LCPatrimoine-Bot"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            # RSS 2.0 format
            for item in root.findall(".//item")[:3]:
                title_el = item.find("title")
                link_el = item.find("link")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                    link = link_el.text.strip() if link_el is not None and link_el.text else ""
                    headlines.append((title, link))
        except Exception as e:
            print(f"Warning: could not fetch {feed_url}: {e}")
    # Deduplicate by title and limit
    seen = set()
    unique = []
    for title, link in headlines:
        if title not in seen:
            seen.add(title)
            unique.append((title, link))
    return unique[:40]

def get_existing_articles():
    """Return list of (slug, title) for all existing blog articles."""
    articles = []
    for path in sorted(glob.glob(f"{BLOG_DIR}/*.html")):
        slug = os.path.basename(path).replace(".html", "")
        title = slug  # fallback
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r"<h1>(.*?)</h1>", content)
            if m:
                title = m.group(1)
        articles.append((slug, title))
    return articles



def generate_article_html(title, slug, meta_description, breadcrumb_short, body_html, pub_date):
    """Generate the full HTML page for a blog article."""
    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | LC Patrimoine</title>
    <meta name="description" content="{meta_description}">
    <link rel="canonical" href="{SITE_URL}/blog/{slug}">
    <link rel="icon" href="../favicon.ico" type="image/x-icon">
    <link rel="icon" href="../favicon-192.png" type="image/png" sizes="192x192">
    <link rel="stylesheet" href="../style.css?v={STYLE_VERSION}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{SITE_URL}/blog/{slug}">
    <meta property="og:locale" content="fr_FR">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{title}",
        "author": {{
            "@type": "Person",
            "name": "Carine Savajols"
        }},
        "publisher": {{
            "@type": "Organization",
            "name": "LC Patrimoine"
        }},
        "datePublished": "{pub_date}",
        "description": "{meta_description}"
    }}
    </script>
</head>
<body>
    <nav>
        <div class="container">
            <a href="../index.html" class="logo"><img src="../logo.png" alt="LC Patrimoine - Gestion de patrimoine en Île-de-France"></a>
            <a href="https://www.linkedin.com/in/carinesavajols/" target="_blank" rel="noopener" class="nav-linkedin" aria-label="LinkedIn"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></a>
            <ul class="nav-links" id="navLinks">
                <li><a href="../index.html#objectifs">Vos objectifs</a></li>
                <li><a href="../index.html#methode">Comment ça marche</a></li>
                <li><a href="../index.html#apropos">À propos</a></li>
                <li><a href="../index.html#simulateur">Simulateur</a></li>
                <li><a href="../index.html#faq">FAQ</a></li>
                <li><a href="../index.html#contact">Contact</a></li>
                <li><a href="../blog.html">Blog</a></li>
                <li><a href="../index.html#contact" class="nav-cta">Bilan gratuit</a></li>
            </ul>
            <button class="menu-toggle" id="menuToggle" aria-label="Menu"><span></span><span></span><span></span></button>
        </div>
    </nav>

    <header class="page-hero">
        <div class="container">
            <div class="breadcrumb"><a href="../index.html">Accueil</a> <span>›</span> <a href="../blog.html">Blog</a> <span>›</span> {breadcrumb_short}</div>
            <h1>{title}</h1>
            <p>Publié le {format_date_fr(pub_date)} par Carine Savajols</p>
        </div>
    </header>

    <section class="page-content">
        <div class="container">
{body_html}

            <div class="cta-box">
                <h3>Besoin d'un accompagnement personnalisé ?</h3>
                <p>Chaque situation est unique. Faisons le point ensemble sur vos objectifs — c'est gratuit et sans engagement.</p>
                <a href="../index.html#contact" class="btn-primary">Prendre rendez-vous</a>
            </div>
        </div>
    </section>

    <footer>
        <div class="container">
            <div class="footer-grid">
                <div class="footer-about">
                    <a href="../index.html" class="logo"><img src="../logo.png" alt="LC Patrimoine" style="height:36px;"></a>
                    <p>Cabinet indépendant de gestion de patrimoine en Île-de-France. Bilan patrimonial gratuit.</p>
                </div>
                <div>
                    <h4>Nos services</h4>
                    <ul class="footer-links">
                        <li><a href="../defiscalisation.html">Défiscalisation</a></li>
                        <li><a href="../investissement.html">Investissement</a></li>
                        <li><a href="../retraite.html">Retraite</a></li>
                        <li><a href="../transmission.html">Transmission</a></li>
                        <li><a href="../assurance-emprunteur.html">Assurance emprunteur</a></li>
                    </ul>
                </div>
                <div>
                    <h4>Navigation</h4>
                    <ul class="footer-links">
                        <li><a href="../index.html#objectifs">Vos objectifs</a></li>
                        <li><a href="../index.html#apropos">À propos</a></li>
                        <li><a href="../index.html#simulateur">Simulateur</a></li>
                        <li><a href="../index.html#contact">Contact</a></li>
                    </ul>
                </div>
                <div>
                    <h4>Contact</h4>
                    <ul class="footer-links">
                        <li>06 22 18 78 28</li>
                        <li>75 Rue Marignan</li>
                        <li>94210 Saint-Maur-des-Fossés</li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <span>&copy; 2026 LC Patrimoine</span>
                <a href="../mentions-legales.html">Mentions légales</a>
            </div>
        </div>
    </footer>
    <script>document.getElementById('menuToggle').addEventListener('click', function() {{ document.getElementById('navLinks').classList.toggle('open'); }});</script>
</body>
</html>'''


def format_date_fr(iso_date):
    """Convert YYYY-MM-DD to French date string."""
    months = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    y, m, d = iso_date.split("-")
    return f"{int(d)} {months[int(m)]} {y}"


def add_blog_card(slug, title, summary, pub_date):
    """Insert a new blog card at the top of blog.html."""
    with open(BLOG_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    img_tag = ""

    card = f'''
                <!-- {format_date_fr(pub_date)} -->
                <a href="blog/{slug}.html" class="blog-card" style="text-decoration:none;">{img_tag}
                    <div class="blog-card-body">
                        <div class="blog-card-date">{format_date_fr(pub_date)}</div>
                        <h3>{title}</h3>
                        <p>{summary}</p>
                        <span class="service-link">Lire l'article →</span>
                    </div>
                </a>
'''

    # Insert after <div class="blog-grid">
    marker = '<div class="blog-grid">'
    html = html.replace(marker, marker + "\n" + card, 1)

    with open(BLOG_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Blog card added to {BLOG_HTML}")


def update_sitemap(slug, pub_date):
    """Add a new URL entry to sitemap.xml."""
    with open(SITEMAP, "r", encoding="utf-8") as f:
        content = f.read()

    new_entry = f"""    <url>
        <loc>{SITE_URL}/blog/{slug}</loc>
        <lastmod>{pub_date}</lastmod>
        <priority>0.6</priority>
    </url>"""

    # Insert before </urlset>
    content = content.replace("</urlset>", new_entry + "\n</urlset>")

    # Also update blog lastmod
    content = re.sub(
        r"(<loc>https://www\.lcpatrimoine\.net/blog</loc>\s*<lastmod>)\d{4}-\d{2}-\d{2}(</lastmod>)",
        rf"\g<1>{pub_date}\2",
        content,
    )

    with open(SITEMAP, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Sitemap updated with {slug}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = date.today().isoformat()

    # 1. Collect existing articles
    existing = get_existing_articles()
    existing_info = "\n".join(f"- {slug}: {title}" for slug, title in existing)
    print(f"Found {len(existing)} existing articles.")

    # 2. Fetch recent news headlines
    print("Fetching recent financial headlines...")
    headlines = fetch_recent_headlines()
    if headlines:
        headlines_text = "\n".join(f"- {title} ({link})" if link else f"- {title}" for title, link in headlines)
        print(f"Found {len(headlines)} headlines.")
    else:
        headlines_text = "(aucun titre récupéré)"
        print("Warning: no headlines fetched.")

    # 3. Call Claude to generate article content
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    topic_hint = os.environ.get("TOPIC_HINT", "").strip()

    topic_instruction = (
        f'**Thème demandé** : {topic_hint}\nÉcris l\'article sur ce thème en faisant le lien avec les solutions patrimoniales de Carine.'
        if topic_hint
        else '**Mission** : Choisis UNE actualité parmi les titres récents ci-dessous et rédige un article de blog (800-1200 mots) qui fait le lien avec les solutions patrimoniales que Carine propose.'
    )

    prompt = f"""Tu es le rédacteur du blog de LC Patrimoine (lcpatrimoine.net), cabinet indépendant de gestion de patrimoine en Île-de-France dirigé par Carine Savajols.

{topic_instruction}

**Actualités récentes (titres réels du jour)** :
{headlines_text}

**Domaines** : défiscalisation, investissement, retraite, transmission, assurance emprunteur.
**Outils à mettre en avant** : PER, Girardin, GFI, Denormandie, assurance-vie, SCPI, contrat de capitalisation, LMNP, démembrement, SCI, assurance emprunteur.
**Ton** : accessible, concret, professionnel mais pas jargonneux. Tu tutoies pas le lecteur, tu le vouvoies.
**Sources** : quand tu cites un chiffre, une loi, une étude ou une info factuelle importante, ajoute un lien source dans le HTML (balise <a href="..." target="_blank">). Utilise les liens des actualités ci-dessus ou des sources officielles (INSEE, service-public.fr, legifrance.gouv.fr, Banque de France, etc.).
**IMPORTANT** : Nous sommes en {today[:4]}. Ne fais JAMAIS référence à des événements d'années passées comme s'ils étaient actuels.
**IMPORTANT** : Ne parle JAMAIS de "premier rendez-vous". L'offre est "bilan et rendez-vous gratuits" (pas de notion de "premier").

**Articles existants (à ne pas répéter ni trop chevaucher)** :
{existing_info}

**Date de publication** : {today}

Réponds UNIQUEMENT avec un JSON valide (sans blocs markdown) contenant ces clés :
- "title": titre de l'article (accrocheur, max 80 caractères)
- "slug": slug URL (minuscules, tirets, pas d'accents, max 60 caractères)
- "meta_description": description SEO (max 160 caractères)
- "breadcrumb_short": mot-clé court pour le fil d'Ariane (ex: "PER", "SCPI", "Retraite")
- "summary": résumé pour la carte blog (1-2 phrases, max 200 caractères)
- "body_html": le contenu HTML de l'article (utilise h2, p, ul/li, strong, div class="highlight-box" pour les astuces). Indente avec 12 espaces.
- "linkedin_post": post LinkedIn de teasing (1-2 phrases, ton personnel comme si Carine écrivait, avec un lien vers l'article sous la forme {SITE_URL}/blog/[slug]). Max 300 caractères. Ajoute 2-3 hashtags pertinents."""

    print("Calling Claude API...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Remove potential markdown code block wrapping
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    data = json.loads(raw)

    title = data["title"]
    slug = data["slug"]
    meta_description = data["meta_description"]
    breadcrumb_short = data["breadcrumb_short"]
    summary = data["summary"]
    body_html = data["body_html"]
    linkedin_post = data["linkedin_post"]

    print(f"Article generated: {title} ({slug})")

    # 3. Write article HTML
    article_html = generate_article_html(
        title, slug, meta_description, breadcrumb_short, body_html, today,
    )
    article_path = f"{BLOG_DIR}/{slug}.html"
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(article_html)
    print(f"Article written: {article_path}")

    # 4. Update blog.html with new card
    add_blog_card(slug, title, summary, today)

    # 6. Update sitemap.xml
    update_sitemap(slug, today)

    # 7. Write slug for the workflow (used to build preview link)
    with open("article-slug.txt", "w", encoding="utf-8") as f:
        f.write(slug)

    # 8. Write PR description for the workflow
    pr_body = f"""## Nouvel article de blog

**Titre** : {title}
**Slug** : `{slug}`
**Date** : {format_date_fr(today)}

### Aperçu
{summary}

### Post LinkedIn (à copier-coller)
```
{linkedin_post}
```

### Ajouter une image
Glissez-déposez une image dans un commentaire ci-dessous. Le bot l'intégrera automatiquement à l'article.

---
*Relisez l'article et le teasing LinkedIn. Mergez la PR pour publier sur le site, puis postez le teasing sur LinkedIn.*
*Vous pouvez aussi commenter cette PR pour demander des modifications texte.*
"""
    with open("pr-description.md", "w", encoding="utf-8") as f:
        f.write(pr_body)

    # 9. Write title for PR
    with open("article-title.txt", "w", encoding="utf-8") as f:
        f.write(title)

    print("Done!")


if __name__ == "__main__":
    main()
