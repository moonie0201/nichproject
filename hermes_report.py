#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paperclip project reporter -> Discord via Bot API."""

import json
import os
import sys
import urllib.request
from datetime import datetime

PROJECT_NAME = "NichProject"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_HOME_CHANNEL", "1492927950306283651")


def load_json(filename):
    path = os.path.join(PROJECT_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_report():
    agents = load_json("agents.json")
    issues = load_json("issues.json")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    running = [a for a in agents if a.get("status") == "running"]
    idle = [a for a in agents if a.get("status") == "idle"]

    done = [i for i in issues if i.get("status") == "done"]
    in_progress = [i for i in issues if i.get("status") == "in_progress"]
    in_review = [i for i in issues if i.get("status") == "in_review"]
    blocked = [i for i in issues if i.get("status") == "blocked"]

    lines = []
    lines.append(f"## {PROJECT_NAME} -- {now}\n")
    lines.append(f"Agent: {len(running)} active / {len(idle)} idle")
    lines.append(
        f"Issues: {len(done)} done | {len(in_progress)} in_progress | "
        f"{len(in_review)} in_review | {len(blocked)} blocked\n"
    )

    needs_attention = in_review + blocked
    if needs_attention:
        lines.append("**Action needed:**")
        for issue in needs_attention:
            ident = issue.get("identifier", "?")
            title = issue.get("title", "")[:50]
            status = issue.get("status", "")
            lines.append(f"- {ident}: {title} -> {status}")
        lines.append("")

    if done:
        lines.append("**Done:**")
        for issue in done:
            ident = issue.get("identifier", "?")
            title = issue.get("title", "")[:50]
            lines.append(f"- {ident}: {title}")
        lines.append("")

    if in_progress:
        lines.append("**In progress:**")
        for issue in in_progress:
            ident = issue.get("identifier", "?")
            title = issue.get("title", "")[:50]
            lines.append(f"- {ident}: {title}")

    return "\n".join(lines)


def send_via_bot(message):
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    data = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "PaperclipReporter/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    report = build_report()
    print(report)
    print("---")

    if DISCORD_BOT_TOKEN:
        status = send_via_bot(report)
        print(f"Sent via Bot API: {status}")
    else:
        print("No DISCORD_BOT_TOKEN set.")
        sys.exit(1)


if __name__ == "__main__":
    main()
