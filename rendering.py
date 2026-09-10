"""Server-side display rendering. Generated PNGs are never written to disk."""

from dataclasses import dataclass
from io import BytesIO
from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path(__file__).parent / "fonts/PixelOperator/PixelOperator.ttf"
BOLD_FONT = Path(__file__).parent / "fonts/PixelOperator/PixelOperator-Bold.ttf"


@dataclass(frozen=True)
class DisplayProfile:
    width: int = 960
    height: int = 540
    levels: int = 16


EPAPER = DisplayProfile()
DASHBOARDS = {"dashboard_onchain", "dashboard_mining", "lightning_dashboard"}
CENTRED_STATS = {"onchain_block_height", "fun_exchange_market_rate"}
QUOTE_SCREENS = {"fun_satoshi_quotes"}
SCREEN_TITLES = {
    "dashboard": "Bitcoin overview",
    "fun_satoshi_quotes": "Satoshi Nakamoto",
    "fun_exchange_market_rate": "Bitcoin price",
    "onchain_block_height": "Block height",
    "lnbits_wallets_balance": "Wallet balances",
    "url_checker": "Website status",
    "mempool_recommended_fees": "Recommended transaction fees",
}


def stipple(draw, box):
    """Small ordered dots echo the reference's printed e-paper shading."""
    left, top, right, bottom = [int(v) for v in box]
    for y in range(top, bottom, 3):
        for x in range(left + (y % 2), right, 3):
            draw.point((x, y), fill=0)


def panel(draw, box):
    left, top, right, bottom = box
    # Shallow offset faces, like the reference's block cards.
    draw.rectangle((left + 5, top + 5, right + 5, bottom + 5), fill=221, outline=0)
    stipple(draw, (right + 1, top + 5, right + 5, bottom + 5))
    stipple(draw, (left + 5, bottom + 1, right + 5, bottom + 5))
    draw.rounded_rectangle(box, radius=3, fill=255, outline=0, width=2)
    stipple(draw, (left + 3, top + 3, right - 2, top + 10))
    draw.line((left + 1, top + 12, right - 1, top + 12), fill=0)


def render_screen(data, slug, updated, profile=EPAPER):
    image = Image.new("L", (profile.width, profile.height), 255)
    draw = ImageDraw.Draw(image)
    title = SCREEN_TITLES.get(slug) or data["title"] or "Bitcoin statistics"
    top = 78
    bottom = profile.height - 43
    # Compact section heading and patterned rule shared by every screen.
    draw.rectangle((14, 18, 37, 41), outline=0, width=2)
    draw.rectangle((19, 13, 42, 36), fill=255, outline=0, width=2)
    stipple(draw, (22, 16, 40, 21))
    draw.line((24, 27, 36, 27), fill=0, width=2)
    draw.text((54, 13), title, font=ImageFont.truetype(str(BOLD_FONT), 30), fill=0)
    draw.line((14, 55, profile.width - 15, 55), fill=0, width=2)
    stipple(draw, (14, 59, profile.width - 14, 64))
    empty_message = (
        "No wallets configured"
        if slug == "lnbits_wallets_balance"
        else "No data available"
    )
    areas = data["areas"] or [[{"value": empty_message, "size": 20}]]
    fees = slug == "mempool_recommended_fees" and len(areas[0]) == 10
    if fees:
        items = areas[0]
        areas = [
            [dict(items[i]), {"value": items[i + 4]["value"], "size": 32}]
            for i in range(2, 6)
        ]
    columns = 2 if len(areas) > 1 else 1
    rows = ceil(len(areas) / columns)
    for index, items in enumerate(areas):
        cell_width = (profile.width - 28) / columns
        cell_height = (bottom - top) / rows
        panel_left = 12 + (index % columns) * cell_width
        panel_top = top + (index // columns) * cell_height
        panel_right = panel_left + cell_width - 12
        panel_bottom = panel_top + cell_height - 14
        panel(draw, (panel_left, panel_top, panel_right, panel_bottom))
        left = panel_left + 20
        y = panel_top + 26
        width = panel_right - left - 20
        height = panel_bottom - y - 18
        if slug in CENTRED_STATS:
            # Symmetric margins centre the visible text on the panel itself.
            y = max(y, profile.height - panel_bottom + 18)
            height = profile.height - 2 * y
        items = [dict(item) for item in items]
        for item_index, item in enumerate(items):
            if slug in DASHBOARDS:
                item["size"] += 2 if item_index == 0 else (1 if item_index == 1 else 0)
            elif slug in CENTRED_STATS:
                item["size"] += 2
            elif slug in QUOTE_SCREENS:
                item["size"] += 4
        scale = 1.6
        while True:
            lines = []
            for item_index, item in enumerate(items):
                font_path = (
                    BOLD_FONT if item_index == 0 and slug not in QUOTE_SCREENS else FONT
                )
                font = ImageFont.truetype(
                    str(font_path), max(10, int(item["size"] * scale))
                )
                # Wrap by measured pixels, including exceptionally long words.
                words = str(item["value"]).replace("\n", " ").split()
                line = ""
                for word in words:
                    candidate = f"{line} {word}".strip()
                    if draw.textlength(candidate, font=font) <= width:
                        line = candidate
                        continue
                    if line:
                        lines.append((line, font))
                    line = ""
                    for char in word:
                        if line and draw.textlength(line + char, font=font) > width:
                            lines.append((line, font))
                            line = ""
                        line += char
                if line:
                    lines.append((line, font))
            line_heights = [
                draw.textbbox((0, 0), line, font=font, anchor="mt")[3]
                for line, font in lines
            ]
            gaps = [font.size * 0.3 for _, font in lines[:-1]]
            total = sum(line_heights) + sum(gaps)
            if total <= height or scale <= 0.3:
                break
            scale *= 0.9
        cursor = y + max(0, (height - total) / 2)
        for line_index, (line, font) in enumerate(lines):
            if cursor + line_heights[line_index] > y + height:
                draw.text(
                    (left + width / 2, y + height - 12),
                    "…",
                    font=ImageFont.truetype(str(FONT), 12),
                    fill=0,
                    anchor="mt",
                )
                break
            draw.text((left + width / 2, cursor), line, font=font, fill=0, anchor="mt")
            cursor += line_heights[line_index]
            if line_index < len(gaps):
                cursor += gaps[line_index]
    footer = f"Updated {updated}"
    footer_font = ImageFont.truetype(str(FONT), 18)
    badge_left = profile.width - draw.textlength(footer, font=footer_font) - 48
    badge_top = profile.height - 32
    draw.rounded_rectangle(
        (badge_left, badge_top, profile.width - 12, profile.height - 8),
        radius=3,
        outline=0,
        width=1,
    )
    clock_x, clock_y = badge_left + 14, badge_top + 12
    draw.ellipse(
        (clock_x - 7, clock_y - 7, clock_x + 7, clock_y + 7), outline=0, width=2
    )
    draw.line(
        (clock_x, clock_y - 5, clock_x, clock_y, clock_x + 4, clock_y + 2), fill=0
    )
    draw.text(
        (profile.width - 20, badge_top + 4),
        footer,
        font=footer_font,
        fill=0,
        anchor="rt",
    )
    step = 255 / (profile.levels - 1)
    image = image.point([round(round(i / step) * step) for i in range(256)])
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
