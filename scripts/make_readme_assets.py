#!/usr/bin/env python3
"""
Regenerate the screenshots used in README.md (docs/assets/) from the fictional demo profile
examples/sample_candidate_full.json. Never run this on a real person's profile.

  terminal-match.svg      `cli.py match` summary table
  terminal-programs.svg   `cli.py programs` table
  report.png              HTML report (needs Google Chrome or Chromium)
  social-preview.png      1280x640 card for Settings → Social preview (needs Chrome)
  dashboard.png           Excel dashboard (needs LibreOffice)

Usage: .venv/bin/python scripts/make_readme_assets.py
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from rich.console import Console  # noqa: E402

import cli  # noqa: E402
from planner import workspace as wsp  # noqa: E402

ASSETS = REPO / "docs" / "assets"
DEMO = REPO / "examples" / "sample_candidate_full.json"
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "", shutil.which("chromium-browser") or "",
]


def terminal_svg(name: str, title: str, fn, args: argparse.Namespace) -> None:
    console = Console(record=True, width=118, force_terminal=True, color_system="truecolor")
    cli.console = console
    fn(args)
    (ASSETS / name).write_text(console.export_svg(title=title), encoding="utf-8")
    print(f"wrote docs/assets/{name}")


def screenshot_html(html: Path, out: Path) -> None:
    chrome = next((c for c in CHROME_CANDIDATES if c and Path(c).exists()), None)
    if not chrome:
        print("skip report.png (no Chrome/Chromium found)")
        return
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1280,1500", f"--screenshot={out}", html.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)
    print(f"wrote docs/assets/{out.name}")


SOCIAL_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  * { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  body { width:1280px; height:640px; background:linear-gradient(135deg,#0B1F3A 0%,#1F4E79 55%,#2F5597 100%); color:#fff;
         display:flex; flex-direction:column; justify-content:center; padding:0 90px; position:relative; overflow:hidden; }
  .glow { position:absolute; right:-160px; top:-160px; width:620px; height:620px; border-radius:50%;
          background:radial-gradient(circle,rgba(245,158,11,.35),rgba(245,158,11,0) 70%); }
  .tag { display:inline-block; font-size:22px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
         color:#FCD34D; margin-bottom:22px; }
  h1 { font-size:84px; font-weight:800; line-height:1.02; letter-spacing:-.02em; }
  p { font-size:34px; color:#CBD5E1; margin-top:22px; max-width:960px; line-height:1.3; }
  .row { display:flex; gap:18px; margin-top:44px; }
  .pill { background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.25); border-radius:999px;
          padding:12px 24px; font-size:24px; font-weight:600; }
  .pill b { color:#FCD34D; }
  .foot { position:absolute; bottom:44px; left:90px; font-size:22px; color:#94A3B8; }
</style></head><body><div class="glow"></div>
  <div class="tag">🎓 Open source · free · AI-agent ready</div>
  <h1>Scholarship Navigator</h1>
  <p>Find the scholarships you can actually win: eligibility, match scores, missing papers and a dated plan.</p>
  <div class="row"><span class="pill"><b>35</b> scholarships</span><span class="pill"><b>55</b> Erasmus Mundus masters</span>
  <span class="pill"><b>47</b> paper types</span><span class="pill">MCP + skills</span></div>
  <div class="foot">github.com/OmarZen/scholarship-navigator</div>
</body></html>"""


def social_preview(out: Path, tmp: Path) -> None:
    chrome = next((c for c in CHROME_CANDIDATES if c and Path(c).exists()), None)
    if not chrome:
        print("skip social-preview.png (no Chrome/Chromium found)")
        return
    html = tmp / "social.html"
    html.write_text(SOCIAL_HTML, encoding="utf-8")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1280,640", f"--screenshot={out}", html.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)
    print(f"wrote docs/assets/{out.name}")


def screenshot_dashboard(xlsx: Path, out: Path, tmp: Path) -> None:
    soffice = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if not Path(soffice).exists():
        print("skip dashboard.png (no LibreOffice found)")
        return
    import openpyxl
    wb = openpyxl.load_workbook(xlsx)
    for ws in wb.worksheets:
        ws.sheet_state = "visible" if ws.title == "Dashboard" else "hidden"
    wb.active = wb.sheetnames.index("Dashboard")
    only = tmp / "dashboard.xlsx"
    wb.save(only)
    profile = tmp / "lo-profile"
    subprocess.run([soffice, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless", "--convert-to", "pdf",
                    "--outdir", str(tmp), str(only)], check=True, capture_output=True, timeout=180)
    pdf = tmp / "dashboard.pdf"
    if shutil.which("sips"):
        subprocess.run(["sips", "-s", "format", "png", "-Z", "1600", str(pdf), "--out", str(out)],
                       check=True, capture_output=True)
    elif shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(pdf), str(out.with_suffix(""))], check=True)
    else:
        print("skip dashboard.png (needs sips or pdftoppm)")
        return
    print(f"wrote docs/assets/{out.name}")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ws = wsp.create_workspace(json.loads(DEMO.read_text(encoding="utf-8")), root=tmp, name="demo")
        wsp.build_workspace(ws)
        base = dict(workspace=str(ws), profile=None, json=False)
        terminal_svg("terminal-match.svg", "cli.py match", cli.cmd_match,
                     argparse.Namespace(**base, limit=10, details=0, all=False))
        terminal_svg("terminal-programs.svg", "cli.py programs", cli.cmd_programs,
                     argparse.Namespace(**base, field=None, country=None, scheme=None, all=False, limit=8,
                                        choose=None, unchoose=None))
        screenshot_html(ws / "reports" / "scholarship_report.html", ASSETS / "report.png")
        social_preview(ASSETS / "social-preview.png", tmp)
        try:
            screenshot_dashboard(ws / "reports" / "scholarship_tracker.xlsx", ASSETS / "dashboard.png", tmp)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"skip dashboard.png ({e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
