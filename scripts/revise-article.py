#!/usr/bin/env python3
"""Revise a blog article based on a PR comment using Claude API."""

import os
import re
import json
import glob
import subprocess

import anthropic


ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
COMMENT_BODY = os.environ["COMMENT_BODY"]
BLOG_DIR = "blog"


def find_new_article():
    """Find the article added in this branch compared to main."""
    # Use git diff to find new files in blog/
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", "origin/main", "HEAD", "--", "blog/*.html"],
        capture_output=True, text=True,
    )
    new_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    if new_files:
        return new_files[0]

    # Fallback: find modified files in blog/
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "HEAD", "--", "blog/*.html"],
        capture_output=True, text=True,
    )
    modified = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    if modified:
        return modified[0]

    raise FileNotFoundError("No new or modified article found in this branch")


def main():
    # 1. Find the article from this PR (new file vs main)
    article_path = find_new_article()
    slug = os.path.basename(article_path).replace(".html", "")

    with open(article_path, "r", encoding="utf-8") as f:
        article_html = f.read()

    print(f"Article: {article_path} (slug: {slug})")
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

    # 3. Write updated article
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(data["article_html"])
    print(f"Article updated: {article_path}")

    # 4. Write slug for the workflow
    with open("article-slug.txt", "w", encoding="utf-8") as f:
        f.write(slug)

    print(f"Changes: {data.get('changes_summary', 'N/A')}")


if __name__ == "__main__":
    main()
