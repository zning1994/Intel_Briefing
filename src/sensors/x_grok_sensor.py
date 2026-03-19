import os
import sys
import datetime
import json
import httpx
from dotenv import load_dotenv

# Force UTF-8 stdout for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
# Default to official endpoint, but allow override for Relay Services (中转站)
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1/chat/completions")
MODEL_NAME = os.getenv("XAI_MODEL", "grok-3-mini")

def fetch_grok_intel(query: str, override_prompt: str = None) -> str:
    """
    Fetch intelligence from X using xAI's Grok API.
    Returns the markdown report.
    """
    if not XAI_API_KEY:
        print("❌ Error: XAI_API_KEY not found in .env files.")
        return "Error: No API Key."

    print(f"🦅 Grok Sensor: contacting xAI for '{query}'...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    year_str = datetime.datetime.now().strftime("%Y")

    if override_prompt:
        system_content = f"You are a specialized Data Analyst. Current Date: {today_str}. Follow the user's instructions strictly."
        user_content = override_prompt
    else:
        system_content = (
            f"You are an AI industry intelligence analyst monitoring X (Twitter). "
            f"**CURRENT DATE: {today_str}**.\n\n"
            "## Your mission\n"
            "Find HIGH-SIGNAL events from the **LAST 24 HOURS** on X about global AI developments.\n\n"
            "## What counts as high-signal\n"
            "- Funding rounds, acquisitions, IPO news (any size)\n"
            "- Major product launches or updates (models, APIs, tools)\n"
            "- Key personnel moves (hires, departures, founder drama)\n"
            "- Industry controversies, debates, or policy shifts\n"
            "- Surprising demos, benchmarks, or breakthroughs\n"
            "- Startup announcements from builders of any scale\n\n"
            "## What to SKIP\n"
            "- Generic AI opinions, thought-leader platitudes\n"
            "- Recycled news already covered by HN/ArXiv/Product Hunt\n"
            "- Promotional threads with no substance\n\n"
            "## Rules\n"
            f"- ❌ Do NOT report events from {int(year_str)-2} or {int(year_str)-1} as new. "
            "If referencing older context, label it explicitly as '历史背景'.\n"
            "- Each item MUST include at least one @handle or paraphrased tweet as source.\n"
            "- 直接输出结果，不要写分析过程说明或开场白。\n"
            "- 用简体中文回答。\n\n"
            "## Output format (strict)\n"
            "For each event, use this format:\n\n"
            "### {事件标题}\n"
            "- **信号类型**: 融资/产品/人事/争议/技术/政策\n"
            "- **关键人物/公司**: ...\n"
            "- **来源**: @handle 说了什么 (paraphrase)\n"
            "- **影响评估**: 一句话说明为什么值得关注\n\n"
            "Report 5-8 items, sorted by impact. If fewer than 3 genuine events found, "
            "say '过去24小时X平台无重大AI动态' and stop."
        )
        user_content = (
            f"Search X for the latest AI industry developments from the past 24 hours ({today_str}). "
            f"Cover: AI technology breakthroughs, startup funding & products, "
            f"industry moves & drama, China AI ecosystem, global AI policy. "
            f"Focus on {year_str} events only."
        )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "stream": False,
        "temperature": 0.3
    }

    try:
        response = httpx.post(XAI_BASE_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        print("\n" + "="*60)
        print(f"  🦅 Grok Intelligence Report: {query}")
        print("="*60 + "\n")
        print(content)
        
        return content
        
    except httpx.HTTPStatusError as e:
        err = f"⚠️ API Error: {e.response.status_code} - {e.response.text}"
        print(err)
        return err
    except Exception as e:
        err = f"⚠️ Connection Error: {e}"
        print(err)
        return err

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python x_grok_sensor.py <query>")
        print("Example: python x_grok_sensor.py 'AI Agents'")
    else:
        q = sys.argv[1]
        fetch_grok_intel(q)
