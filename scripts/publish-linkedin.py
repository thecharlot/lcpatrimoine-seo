#!/usr/bin/env python3
"""Publish a LinkedIn post from linkedin-post.md."""

import os
import sys
import json

import requests


LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.environ.get("LINKEDIN_PERSON_URN", "")
POST_FILE = "linkedin-post.md"


def main():
    if not os.path.exists(POST_FILE):
        print(f"{POST_FILE} not found, nothing to publish.")
        sys.exit(0)

    with open(POST_FILE, "r", encoding="utf-8") as f:
        post_text = f.read().strip()

    if not post_text:
        print("Post is empty, skipping.")
        sys.exit(0)

    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        print("LinkedIn credentials not configured. Skipping publication.")
        print(f"Post content:\n{post_text}")
        sys.exit(0)

    # LinkedIn API v2 - Create a share
    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
        timeout=30,
    )

    if resp.status_code == 201:
        post_id = resp.json().get("id", "unknown")
        print(f"LinkedIn post published successfully! ID: {post_id}")
    else:
        print(f"LinkedIn API error {resp.status_code}: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
