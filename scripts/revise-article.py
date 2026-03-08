#!/usr/bin/env python3
"""Revise a blog article based on a PR comment using Claude API."""

import os
import re
import json
import glob
import subprocess

import anthropic
import requests


ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
COMMENT_BODY = os.environ["COMMENT_BODY"]
BLOG_DIR = "blog"


def find_new_article():
    """Find the article added in this branch compared to main."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", "origin/main", "HEAD", "--", "blog/*.html"],
        capture_output=True, text=True,
    )
    new_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    if new_files:
        return new_files[0]

    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "HEAD", "--", "blog/*.html"],
        capture_output=True, text=True,
    )
    modified = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    if modified:
        return modified[0]

    raise FileNotFoundError("No new or modified article found in this branch")


def extract_image_url(comment):
    """Check if the comment is an image replacement command.

    Supported formats:
        image: https://example.com/photo.jpg
        image https://example.com/photo.jpg
        image: https://example.com/photo  (sans extension, on tente quand même)
        https://example.com/photo.jpg  (URL brute avec extension image)
    """
    comment = comment.strip()

    # "image:" prefix → on prend n'importe quelle URL qui suit
    m = re.match(r'^image\s*:?\s*(https?://\S+)', comment, re.IGNORECASE)
    if m:
        return m.group(1)

    # URL brute seule (avec extension image ou domaine connu de banques d'images)
    if re.match(r'^https?://\S+$', comment, re.IGNORECASE):
        url = comment.strip()
        image_domains = ['unsplash.com', 'images.unsplash.com', 'pexels.com', 'images.pexels.com',
                         'pixabay.com', 'cdn.pixabay.com', 'img.freepik.com']
        if any(d in url for d in image_domains):
            return url
        if re.search(r'\.(jpg|jpeg|png|webp)(\?\S*)?$', url, re.IGNORECASE):
            return url

    return None


def replace_image(slug, image_url):
    """Download image and update the article HTML to use the local path."""
    os.makedirs(f"{BLOG_DIR}/img", exist_ok=True)
    img_path = f"{BLOG_DIR}/img/{slug}.jpg"

    print(f"Downloading image: {image_url}")
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()

    with open(img_path, "wb") as f:
        f.write(resp.content)
    print(f"Image saved: {img_path}")

    # Update article HTML to use local image path
    article_path = f"{BLOG_DIR}/{slug}.html"
    if os.path.exists(article_path):
        with open(article_path, "r", encoding="utf-8") as f:
            html = f.read()

        local_img = f'img/{slug}.jpg'
        # Replace any existing <img> in the article content (external URL or old local path)
        if f'<img src="{local_img}"' in html:
            print("Article already uses local image path.")
        elif '<img src="' in html:
            # Replace the first img src in the page-content section
            html = re.sub(
                r'(<section class="page-content">.*?<img src=")([^"]+)(")',
                rf'\g<1>{local_img}\3',
                html,
                count=1,
                flags=re.DOTALL,
            )
            with open(article_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Article HTML updated to use {local_img}")
        else:
            # No image tag yet — insert one at the top of the content
            img_tag = f'            <img src="{local_img}" alt="{slug.replace("-", " ").title()}" style="width:100%;max-height:400px;object-fit:cover;border-radius:12px;margin-bottom:2rem;">\n'
            html = html.replace(
                '<section class="page-content">\n        <div class="container">\n',
                f'<section class="page-content">\n        <div class="container">\n{img_tag}',
                1,
            )
            with open(article_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Image tag inserted in article.")

    return img_path


def main():
    article_path = find_new_article()
    slug = os.path.basename(article_path).replace(".html", "")

    print(f"Article: {article_path} (slug: {slug})")
    print(f"Comment: {COMMENT_BODY[:100]}...")

    # Write slug for the workflow
    with open("article-slug.txt", "w", encoding="utf-8") as f:
        f.write(slug)

    # Check if comment is an image replacement
    image_url = extract_image_url(COMMENT_BODY)
    if image_url:
        replace_image(slug, image_url)
        print("Image replacement done — no text revision needed.")
        return

    # Otherwise, apply text revision via Claude
    with open(article_path, "r", encoding="utf-8") as f:
        article_html = f.read()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Tu es l'assistant éditorial de LC Patrimoine. Carine Savajols a relu un article de blog et demande des modifications.

**Son commentaire** :
{COMMENT_BODY}

**Article actuel** (HTML complet) :
```html
{article_html}
```

Applique les modifications demandées par Carine. Garde le même format HTML, la même structure, le même ton.

Réponds UNIQUEMENT avec un JSON valide (sans blocs markdown) contenant :
- "article_html": l'article HTML complet modifié
- "changes_summary": résumé en 1 phrase des modifications apportées"""

    print("Calling Claude API for revision...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    data = json.loads(raw)

    with open(article_path, "w", encoding="utf-8") as f:
        f.write(data["article_html"])
    print(f"Article updated: {article_path}")
    print(f"Changes: {data.get('changes_summary', 'N/A')}")


if __name__ == "__main__":
    main()
