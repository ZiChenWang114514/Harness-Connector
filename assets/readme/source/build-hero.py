#!/usr/bin/env python3
"""Build self-contained Harness Connector README heroes."""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = ROOT / "assets" / "readme"
SOURCE_ROOT = ASSET_ROOT / "source"
BACKGROUND = SOURCE_ROOT / "hero-background-v1.png"

LOGOS = [
    ("OpenCode", ROOT / "skills/codex-opencode-session/assets/readme/opencode-logo.svg"),
    ("Grok Build", ROOT / "skills/codex-grok-build/assets/readme/grok-logo.svg"),
    ("Kimi Code", ROOT / "skills/codex-kimi-session/assets/readme/kimi-logo.svg"),
    ("ZCode", ROOT / "skills/codex-zcode-session/assets/readme/zai-logo.svg"),
    ("DeepSeek", ROOT / "skills/codex-dsh-session/assets/readme/deepseek-logo.svg"),
    ("Codex CLI", ROOT / "skills/codex-cli-session/assets/readme/openai-logo.svg"),
    ("Claude Code", ROOT / "skills/codex-claude-session/assets/readme/anthropic-logo.svg"),
    ("Pi", ROOT / "skills/codex-pi-session/assets/readme/pi-logo.svg"),
]


def encode_background(width: int, height: int, focus_x: float) -> str:
    image = Image.open(BACKGROUND).convert("RGB")
    scale = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = round(resized.width * focus_x - width / 2)
    top = round((resized.height - height) / 2)
    left = max(0, min(left, resized.width - width))
    top = max(0, min(top, resized.height - height))
    crop = resized.crop((left, top, left + width, top + height))
    payload = io.BytesIO()
    crop.save(payload, format="WEBP", quality=84, method=6)
    return "data:image/webp;base64," + base64.b64encode(payload.getvalue()).decode("ascii")


def encode_logo(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("currentColor", "#F8FAFC")
    text = re.sub(r"\.logo-mark\s*\{[^}]*\}", ".logo-mark { fill: #F8FAFC; }", text, count=1)
    root_tag = text[text.find("<svg") : text.find(">", text.find("<svg"))]
    if " fill=" not in root_tag:
        text = re.sub(r"<svg\b", '<svg fill="#F8FAFC"', text, count=1)
    return "data:image/svg+xml;base64," + base64.b64encode(text.encode("utf-8")).decode("ascii")


def node(x: int, y: int, size: int, logo_uri: str, label: str, label_y: int | None = None) -> str:
    inner = round(size * 0.22)
    logo_size = size - 2 * inner
    label_svg = ""
    if label_y is not None:
        label_svg = (
            f'<text x="{x + size / 2:g}" y="{label_y}" text-anchor="middle" '
            'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" '
            f'font-size="18" font-weight="600" fill="#DCE9F7">{label}</text>'
        )
    rendered = f"""
    <g aria-label="{label}">
      <circle cx="{x + size / 2:g}" cy="{y + size / 2:g}" r="{size / 2:g}" fill="#07111F" fill-opacity=".84" stroke="#B8D8F5" stroke-opacity=".42" stroke-width="1.5"/>
      <circle cx="{x + size / 2:g}" cy="{y + size / 2:g}" r="{size / 2 - 5:g}" fill="none" stroke="#64E6C4" stroke-opacity=".18"/>
      <image href="{logo_uri}" x="{x + inner}" y="{y + inner}" width="{logo_size}" height="{logo_size}" preserveAspectRatio="xMidYMid meet"/>
      {label_svg}
    </g>"""
    return "\n".join(line.rstrip() for line in rendered.splitlines())


def connections(points: list[tuple[int, int]], core: tuple[int, int]) -> str:
    paths = []
    for index, (x, y) in enumerate(points):
        bend_x = round((x + core[0]) / 2 + (-20 if index % 2 else 20))
        paths.append(
            f'<path d="M{x} {y} Q{bend_x} {y} {core[0]} {core[1]}" '
            'fill="none" stroke="url(#route)" stroke-width="2" stroke-linecap="round" opacity=".62"/>'
        )
    return "\n".join(paths)


def desktop(logos: list[str]) -> str:
    width, height = 1200, 420
    background = encode_background(width, height, 0.5)
    node_xy = [(738, 50), (842, 24), (958, 32), (1064, 92), (1078, 220), (976, 304), (852, 310), (742, 258)]
    size = 68
    centers = [(x + size // 2, y + size // 2) for x, y in node_xy]
    core = (946, 203)
    nodes = "\n".join(node(x, y, size, logos[i], LOGOS[i][0]) for i, (x, y) in enumerate(node_xy))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">
  <title id="title">Harness Connector</title>
  <desc id="desc">Eight independent coding harness logos connect through one reusable session-skill collection.</desc>
  <defs>
    <clipPath id="canvas"><rect width="1200" height="420" rx="28"/></clipPath>
    <linearGradient id="shade" x1="0" x2="1"><stop offset="0" stop-color="#050C17" stop-opacity=".98"/><stop offset=".5" stop-color="#07111F" stop-opacity=".78"/><stop offset=".78" stop-color="#07111F" stop-opacity=".12"/><stop offset="1" stop-color="#07111F" stop-opacity=".42"/></linearGradient>
    <linearGradient id="route"><stop stop-color="#5BA8FF"/><stop offset="1" stop-color="#64E6C4"/></linearGradient>
  </defs>
  <g clip-path="url(#canvas)">
    <rect width="1200" height="420" fill="#07111F"/>
    <image href="{background}" width="1200" height="420" preserveAspectRatio="xMidYMid slice"/>
    <rect width="1200" height="420" fill="url(#shade)"/>
    <path d="M64 30H1136" stroke="#B8D8F5" stroke-opacity=".12"/>
    <path d="M64 390H1136" stroke="#B8D8F5" stroke-opacity=".12"/>
    <g id="routing-field">{connections(centers, core)}</g>
    <g id="brand-nodes">{nodes}</g>
    <g id="connector-core">
      <circle cx="{core[0]}" cy="{core[1]}" r="67" fill="#07111F" fill-opacity=".9" stroke="#64E6C4" stroke-opacity=".64" stroke-width="2"/>
      <circle cx="{core[0]}" cy="{core[1]}" r="55" fill="#10253B" fill-opacity=".9" stroke="#5BA8FF" stroke-opacity=".42"/>
      <path d="M919 203h54M946 176v54" stroke="#F8FAFC" stroke-width="3" stroke-linecap="round" opacity=".94"/>
      <circle cx="946" cy="203" r="8" fill="#64E6C4"/>
      <text x="946" y="255" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="15" font-weight="700" letter-spacing="1.5" fill="#CFE5F7">SESSION</text>
    </g>
    <g id="title-block" transform="translate(64 56)">
      <text x="0" y="0" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="18" font-weight="700" letter-spacing="2.2" fill="#64E6C4">PLUGIN-READY · 8 INDEPENDENT SKILLS</text>
      <text x="0" y="88" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="70" font-weight="760" letter-spacing="-2.4" fill="#F8FAFC">Harness</text>
      <text x="0" y="154" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="70" font-weight="760" letter-spacing="-2.4" fill="#F8FAFC">Connector</text>
      <rect x="0" y="177" width="98" height="4" rx="2" fill="#64E6C4"/>
      <text x="0" y="222" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="23" font-weight="560" fill="#D9E8F5">Connect any compatible coding harness</text>
      <text x="0" y="254" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="23" font-weight="560" fill="#D9E8F5">to the exact CLI workdir, model, and session.</text>
      <g transform="translate(0 286)">
        <rect width="500" height="46" rx="23" fill="#10253B" fill-opacity=".86" stroke="#B8D8F5" stroke-opacity=".2"/>
        <circle cx="23" cy="23" r="6" fill="#64E6C4"/>
        <text x="43" y="29" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="18" font-weight="650" fill="#CFE5F7">ANY HARNESS → TARGET HARNESS → EXACT SESSION</text>
      </g>
    </g>
  </g>
</svg>
"""


def mobile(logos: list[str]) -> str:
    width, height = 720, 760
    background = encode_background(width, height, 0.67)
    node_xy = [(72, 344), (190, 310), (412, 310), (530, 344), (530, 520), (412, 558), (190, 558), (72, 520)]
    size = 72
    centers = [(x + size // 2, y + size // 2) for x, y in node_xy]
    core = (360, 470)
    nodes = "\n".join(node(x, y, size, logos[i], LOGOS[i][0]) for i, (x, y) in enumerate(node_xy))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="760" viewBox="0 0 720 760" role="img" aria-labelledby="title desc">
  <title id="title">Harness Connector</title>
  <desc id="desc">Mobile cover showing eight coding harness logos linked to one exact session connector.</desc>
  <defs>
    <clipPath id="canvas"><rect width="720" height="760" rx="30"/></clipPath>
    <linearGradient id="shade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#050C17" stop-opacity=".98"/><stop offset=".43" stop-color="#07111F" stop-opacity=".86"/><stop offset=".72" stop-color="#07111F" stop-opacity=".22"/><stop offset="1" stop-color="#07111F" stop-opacity=".78"/></linearGradient>
    <linearGradient id="route"><stop stop-color="#5BA8FF"/><stop offset="1" stop-color="#64E6C4"/></linearGradient>
  </defs>
  <g clip-path="url(#canvas)">
    <rect width="720" height="760" fill="#07111F"/>
    <image href="{background}" width="720" height="760" preserveAspectRatio="xMidYMid slice"/>
    <rect width="720" height="760" fill="url(#shade)"/>
    <g id="title-block" transform="translate(44 58)">
      <text x="0" y="0" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="18" font-weight="700" letter-spacing="1.8" fill="#64E6C4">8 INDEPENDENT SESSION SKILLS</text>
      <text x="0" y="78" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="60" font-weight="760" letter-spacing="-1.8" fill="#F8FAFC">Harness</text>
      <text x="0" y="136" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="60" font-weight="760" letter-spacing="-1.8" fill="#F8FAFC">Connector</text>
      <rect x="0" y="160" width="92" height="4" rx="2" fill="#64E6C4"/>
      <text x="0" y="204" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" font-size="21" font-weight="560" fill="#D9E8F5">Any coding harness → exact CLI session</text>
    </g>
    <g id="routing-field">{connections(centers, core)}</g>
    <g id="brand-nodes">{nodes}</g>
    <g id="connector-core">
      <circle cx="360" cy="470" r="76" fill="#07111F" fill-opacity=".92" stroke="#64E6C4" stroke-opacity=".68" stroke-width="2"/>
      <circle cx="360" cy="470" r="62" fill="#10253B" fill-opacity=".92" stroke="#5BA8FF" stroke-opacity=".42"/>
      <path d="M330 470h60M360 440v60" stroke="#F8FAFC" stroke-width="4" stroke-linecap="round" opacity=".94"/>
      <circle cx="360" cy="470" r="9" fill="#64E6C4"/>
      <text x="360" y="536" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="18" font-weight="700" letter-spacing="1.6" fill="#CFE5F7">EXACT SESSION</text>
    </g>
    <g transform="translate(44 686)">
      <rect width="632" height="46" rx="23" fill="#10253B" fill-opacity=".9" stroke="#B8D8F5" stroke-opacity=".2"/>
      <circle cx="23" cy="23" r="6" fill="#64E6C4"/>
      <text x="43" y="29" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="18" font-weight="650" fill="#CFE5F7">WORKDIR · MODEL · SESSION ID · STRUCTURED JSON</text>
    </g>
  </g>
</svg>
"""


def main() -> None:
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    logos = [encode_logo(path) for _, path in LOGOS]
    (ASSET_ROOT / "hero.svg").write_text(desktop(logos), encoding="utf-8", newline="\n")
    (ASSET_ROOT / "hero-mobile.svg").write_text(mobile(logos), encoding="utf-8", newline="\n")
    print(f"built {ASSET_ROOT / 'hero.svg'}")
    print(f"built {ASSET_ROOT / 'hero-mobile.svg'}")


if __name__ == "__main__":
    main()
