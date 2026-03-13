"""
Intel Briefing HTTP wrapper.
Exposes run_mission.py as an on-demand API for Docker integration.
"""
import asyncio
import datetime
import glob
import os
import logging

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from src.config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Intel Briefing")

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "daily_briefings")
os.makedirs(REPORT_DIR, exist_ok=True)

# Simple state
_state = {"running": False, "last_report": None, "last_run": None, "error": None}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "running": _state["running"],
        "last_run": _state["last_run"],
        "has_report": _state["last_report"] is not None,
    }


@app.post("/run")
async def run(days: int = 1):
    if _state["running"]:
        return {"status": "already_running"}

    _state["running"] = True
    _state["error"] = None
    asyncio.get_event_loop().run_in_executor(None, _generate, days)
    return {"status": "started", "days": days}


@app.get("/report", response_class=PlainTextResponse)
def report():
    if _state["error"]:
        return PlainTextResponse(f"Last run failed: {_state['error']}", status_code=500)
    if _state["last_report"]:
        return _state["last_report"]
    return PlainTextResponse("No report yet. POST /run first.", status_code=404)


@app.get("/report/latest", response_class=PlainTextResponse)
def report_latest():
    """Read the latest report file from disk (survives restarts)."""
    files = sorted(glob.glob(os.path.join(REPORT_DIR, "*.md")))
    if not files:
        return PlainTextResponse("No reports on disk.", status_code=404)
    with open(files[-1], "r", encoding="utf-8") as f:
        return f.read()


def _generate(days: int):
    try:
        from src.intel_collector import fetch_all_sources
        from src.report_generator import generate_report

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        limit = 15 if days == 1 else 30
        title = f"每日商业情报简报: {date_str}" if days == 1 else f"周期性情报简报 (过去 {days} 天): {date_str}"
        file_name = f"Morning_Report_{date_str}.md" if days == 1 else f"Weekly_Report_{days}Days_{date_str}.md"

        logger.info(f"开始生成情报简报 - 周期: {days} 天")

        intel = fetch_all_sources(limit_per_source=limit)
        body = generate_report(intel, date_str)
        content = f"# {title}\n\n" + body.replace("# 🌐 全球情报日报 (Global Intel Briefing)", "")

        report_file = os.path.join(REPORT_DIR, file_name)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(content)

        _state["last_report"] = content
        _state["last_run"] = date_str
        _state["error"] = None
        logger.info(f"简报生成完成: {report_file}")

    except Exception as e:
        logger.exception("简报生成失败")
        _state["error"] = str(e)
    finally:
        _state["running"] = False
