#!/usr/bin/env python3
"""Revise a blog article based on a PR comment using Claude API."""

import os
import re
import json
import glob

import anthropic


ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
COMMENT_BODY = os.environ["COMMENT_BODY"]
BLOG_DIR = "blog"


def find_latest_article():
    """Find the most recently modified article in blog/."""
    articles = glob.glob(f"{BLOG_DIR}/*.html")
    if not articles:
        raise FileNotFoundError("No articles found in blog/")
    return max(articles, key=os.path.getmtime)


def main():
    # 1. Find the article and linkedin post from this PR
    article_path = find_latest_article()
    slug = os.path.basename(article_path).replace(".html", "")

    with open(article_path, "r", encoding="utf-8") as f:
        article_html = f.read()

    linkedin_post = ""
    if os.path.exists("linkedin-post.md"):
        with open("linkedin-post.md", "r", encoding="utf-8") as f:
            linkedin_post = f.read()

    print(f"Article: {article_path}")
    print(f"Comment: {COMMENT_BODY[:100]}...")

    # 2. Call Claude to apply the revision
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Tu es l'assistant éditorial de LC Patrimoine. Carine Savajols a relu un article de blog et demande des modifications.

**Son commentaire** :
{COMMENT_BODY}

**Article actuel** (HTML complet) :
```html
{article_html}
```

**Post LinkedIn actuel** :
```
{linkedin_post}
```

Applique les modifications demandées par Carine. Garde le même format HTML, la même structure, le même ton.

Réponds UNIQUEMENT avec un JSON valide (sans blocs markdown) contenant :
- "article_html": l'article HTML complet modifié
- "linkedin_post": le post LinkedIn modifié (ou identique si pas de demande de modif)
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

    # 3. Write updated files
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(data["article_html"])
    print(f"Article updated: {article_path}")

    if data.get("linkedin_post"):
        with open("linkedin-post.md", "w", encoding="utf-8") as f:
            f.write(data["linkedin_post"])
        print("LinkedIn post updated.")

    print(f"Changes: {data.get('changes_summary', 'N/A')}")


if __name__ == "__main__":
    main()
