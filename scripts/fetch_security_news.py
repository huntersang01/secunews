#!/usr/bin/env python3
"""Fetch boannews.com and boho.or.kr listing pages and update the digest
collection state.

This runs inside GitHub Actions (which has normal internet access) to
work around the Claude Code cloud routine environment's network egress
block that prevents WebFetch/curl from reaching these sites directly.
It replaces the LLM-based collector for the common case; the collector
agent remains as a fallback for when this script's output is missing
or stale (see .claude/skills/security-news-collect/SKILL.md).

Writes/updates:
  _workspace/security-news/{today}_collected.json
  _workspace/security-news/state.json
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")
WORKDIR = "_workspace/security-news"
STATE_PATH = os.path.join(WORKDIR, "state.json")
COLLECTED_PATH = os.path.join(WORKDIR, f"{TODAY}_collected.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SecuNewsBot/1.0"}
FIRST_RUN_LIMIT = 10  # cap backlog size when state.json has no prior watermark


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"boannews_last_idxno": 0, "kisa_last_nttid": 0, "last_run_at": None}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_boannews(html: str):
    items = []
    for block in re.findall(r'<li class="altlist-webzine-item">(.*?)</li>', html, re.S):
        m_id = re.search(r"articleView\.html\?idxno=(\d+)", block)
        m_title = re.search(r'<H2 class="altlist-subject">\s*<a[^>]*>(.*?)</a>', block, re.S | re.I)
        m_snippet = re.search(r'<p class="altlist-summary">\s*(.*?)\s*</p>', block, re.S)
        m_infos = re.findall(r'<div class="altlist-info-item">\s*(.*?)\s*</div>', block, re.S)
        if not (m_id and m_title):
            continue
        idxno = int(m_id.group(1))
        items.append({
            "title": clean(m_title.group(1)),
            "url": f"https://www.boannews.com/news/articleView.html?idxno={idxno}",
            "idxno": idxno,
            "published_at": clean(m_infos[-1]) if m_infos else None,
            "category": None,
            "snippet": clean(m_snippet.group(1)) if m_snippet else None,
        })
    return items


def parse_boho(html: str):
    items = []
    for block in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        m_id = re.search(r"nttId=(\d+)", block)
        m_title = re.search(r'<td class="sbj tal">\s*<a[^>]*>(.*?)</a>', block, re.S)
        m_date = re.search(r'<td class="date">\s*(.*?)\s*</td>', block, re.S)
        if not (m_id and m_title):
            continue
        ntt_id = int(m_id.group(1))
        items.append({
            "title": clean(m_title.group(1)),
            "url": f"https://www.boho.or.kr/kr/bbs/view.do?menuNo=205020&bbsId=B0000133&nttId={ntt_id}",
            "nttId": ntt_id,
            "published_at": clean(m_date.group(1)) if m_date else None,
            "snippet": None,
        })
    return items


def select_new(all_items, key, last_seen):
    all_items.sort(key=lambda it: it[key])
    if last_seen:
        return [it for it in all_items if it[key] > last_seen]
    return all_items[-FIRST_RUN_LIMIT:]


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    state = load_state()
    result = {"run_date": TODAY, "sources": {}}

    try:
        html = fetch("https://www.boannews.com/news/articleList.html?view_type=sm")
        all_items = parse_boannews(html)
        if not all_items:
            raise ValueError("parsed 0 items - page structure may have changed")
        last_idx = state.get("boannews_last_idxno") or 0
        new_items = select_new(all_items, "idxno", last_idx)
        result["sources"]["boannews"] = {"status": "ok", "items": new_items, "error": None}
        state["boannews_last_idxno"] = max(last_idx, max(it["idxno"] for it in all_items))
    except Exception as e:
        result["sources"]["boannews"] = {"status": "failed", "items": [], "error": str(e)}

    try:
        html = fetch("https://www.boho.or.kr/kr/bbs/list.do?menuNo=205020&bbsId=B0000133")
        all_items = parse_boho(html)
        if not all_items:
            raise ValueError("parsed 0 items - page structure may have changed")
        last_ntt = state.get("kisa_last_nttid") or 0
        new_items = select_new(all_items, "nttId", last_ntt)
        result["sources"]["kisa_boho"] = {"status": "ok", "items": new_items, "error": None}
        state["kisa_last_nttid"] = max(last_ntt, max(it["nttId"] for it in all_items))
    except Exception as e:
        result["sources"]["kisa_boho"] = {"status": "failed", "items": [], "error": str(e)}

    state["last_run_at"] = datetime.now(KST).isoformat()

    with open(COLLECTED_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    for src, data in result["sources"].items():
        print(f"{src}: {data['status']} - {len(data['items'])} new item(s)")


if __name__ == "__main__":
    main()
