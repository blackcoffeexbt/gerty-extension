"""Server-side display rendering. Generated PNGs are never written to disk."""

from dataclasses import dataclass
from io import BytesIO
from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = (
    Path(__file__).parent
    / "fonts/ProximaNova/ProximaNovaRegular/ProximaNovaRegular.ttf"
)


@dataclass(frozen=True)
class DisplayProfile:
    width: int = 960
    height: int = 540
    levels: int = 16


EPAPER = DisplayProfile()
DASHBOARDS = {"dashboard_onchain", "dashboard_mining", "lightning_dashboard"}
CENTRED_STATS = {"onchain_block_height", "fun_exchange_market_rate"}
QUOTE_SCREENS = {"fun_satoshi_quotes"}


def render_screen(data, slug, updated, profile=EPAPER):
    image = Image.new("L", (profile.width, profile.height), 255)
    draw = ImageDraw.Draw(image)
    title = data["title"] if slug != "dashboard" else ""
    top = 80 if title else 20
    bottom = profile.height - 45
    if title:
        draw.text(
            (profile.width / 2, 30),
            title,
            font=ImageFont.truetype(str(FONT), 32),
            fill=0,
            anchor="mt",
        )
    empty_message = (
        "No wallets configured"
        if slug == "lnbits_wallets_balance"
        else "No data available"
    )
    areas = data["areas"] or [[{"value": empty_message, "size": 20}]]
    columns = 2 if len(areas) > 1 else 1
    rows = ceil(len(areas) / columns)
    for index, items in enumerate(areas):
        left = (index % columns) * profile.width / columns + 20
        y = top + (index // columns) * (bottom - top) / rows
        width = profile.width / columns - 40
        height = (bottom - top) / rows - 20
        if slug in CENTRED_STATS:
            # Symmetric margins centre the visible text on the panel itself.
            y = 45
            height = profile.height - 90
        items = [dict(item) for item in items]
        for item_index, item in enumerate(items):
            if slug in DASHBOARDS:
                item["size"] += 2 if item_index == 0 else (1 if item_index == 1 else 0)
            elif slug in CENTRED_STATS:
                item["size"] += 2
            elif slug in QUOTE_SCREENS:
                item["size"] += 4
        # Explicit firmware coordinates are layout hints; group fee labels and
        # values into columns rather than inheriting device pixel positions.
        if slug == "mempool_recommended_fees" and len(items) == 10:
            items = [items[0], items[1]] + [
                {"value": f"{items[i]['value']}: {items[i + 4]['value']}", "size": 20}
                for i in range(2, 6)
            ]
        scale = 1.6
        while True:
            lines = []
            for item in items:
                font = ImageFont.truetype(str(FONT), max(10, int(item["size"] * scale)))
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
    draw.text(
        (profile.width - 15, profile.height - 12),
        f"Updated {updated}",
        font=ImageFont.truetype(str(FONT), 18),
        fill=0,
        anchor="rs",
    )
    step = 255 / (profile.levels - 1)
    image = image.point([round(round(i / step) * step) for i in range(256)])
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
