"""Native 480x320 RGB layouts for the Guition JC3248W535."""

import re
from datetime import datetime, timezone
from io import BytesIO
from math import ceil

from PIL import Image, ImageDraw, ImageFont

from .display_settings import COLOUR_THEMES
from .rendering import BOLD_FONT, FONT, SCREEN_TITLES, SINGLE_STATS


def render_colour_screen(data, slug, updated, theme="Orange Pill"):
    palette = COLOUR_THEMES[theme]
    image = Image.new("RGB", (480, 320), palette["background"])
    draw = ImageDraw.Draw(image)

    def text(x, y, value, size=20, colour="text", bold=False, anchor="lt"):
        font = ImageFont.truetype(str(BOLD_FONT if bold else FONT), size)
        draw.text((x, y), str(value), font=font, fill=palette[colour], anchor=anchor)

    def card(box):
        draw.rounded_rectangle(
            box, radius=5, fill=palette["surface"], outline=palette["border"]
        )
        draw.line(
            (box[0] + 6, box[1] + 1, box[2] - 6, box[1] + 1),
            fill=palette["accent"],
            width=2,
        )

    def fit(items, box, centred=True):
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        factor = 1.0
        while True:
            lines = []
            for value, size, colour, bold in items:
                font = ImageFont.truetype(
                    str(BOLD_FONT if bold else FONT), max(12, int(size * factor))
                )
                line = ""
                for word in str(value).replace("\n", " ").split():
                    candidate = (line + " " + word).strip()
                    if draw.textlength(candidate, font=font) <= width:
                        line = candidate
                    else:
                        if line:
                            lines.append((line, font, colour))
                        line = ""
                        for char in word:
                            if line and draw.textlength(line + char, font=font) > width:
                                lines.append((line, font, colour))
                                line = ""
                            line += char
                if line:
                    lines.append((line, font, colour))
            heights = [
                draw.textbbox((0, 0), line, font=font, anchor="lt")[3]
                for line, font, _ in lines
            ]
            total = sum(heights) + max(0, len(lines) - 1) * 6
            if total <= height or factor < 0.4:
                break
            factor *= 0.9
        y = top + max(0, (height - total) / 2)
        for (line, font, colour), line_height in zip(lines, heights, strict=True):
            if y + line_height > bottom:
                break
            draw.text(
                ((left + right) / 2 if centred else left, y),
                line,
                font=font,
                fill=palette[colour],
                anchor="mt" if centred else "lt",
            )
            y += line_height + 6

    title = (
        "Block explorer"
        if slug == "block_explorer"
        else SCREEN_TITLES.get(slug) or data.get("title") or "Bitcoin statistics"
    )
    text(12, 9, title, 26, "accent", True)
    text(468, 304, f"Updated {updated}", 16, "muted", anchor="rt")

    if slug == "block_explorer":
        _block_dashboard(data, draw, text, card, palette)
    else:
        areas = data["areas"] or [[{"value": "No data available", "size": 20}]]
        if slug == "mempool_recommended_fees" and len(areas[0]) == 10:
            source = areas[0]
            areas = [[source[i], source[i + 4]] for i in range(2, 6)]
        columns = 2 if len(areas) > 1 else 1
        rows = ceil(len(areas) / columns)
        for i, area in enumerate(areas):
            left = 8 + (i % columns) * 236
            top = 40 + (i // columns) * (256 / rows)
            right = left + (228 if columns == 2 else 464)
            bottom = top + 256 / rows - 8
            card((left, top, right, bottom))
            items = []
            for j, item in enumerate(area):
                value = str(item["value"]).replace("\n", " ")
                if slug == "bitcoin_history":
                    size, colour, bold = (
                        (24, "accent", True)
                        if j == 0
                        else (21, "text", False) if j == 1 else (16, "muted", False)
                    )
                elif slug == "fun_satoshi_quotes":
                    size, colour, bold = (
                        (23, "text", False) if j == 0 else (19, "secondary", False)
                    )
                elif j == 0:
                    size, colour, bold = 22, "muted", True
                    value = value.removesuffix("'s Wallet")
                elif j == 1:
                    size, colour, bold = (
                        (100 if slug in SINGLE_STATS else 42),
                        "accent",
                        False,
                    )
                    if len(value) > 22:
                        size = 28
                    if slug == "url_checker":
                        colour = "positive" if value.startswith("2") else "negative"
                else:
                    size, colour, bold = 18, "muted", False
                value = re.sub(r"\bCurrent\s+", "", value)
                items.append((value, size, colour, bold))
            fit(
                items,
                (left + 12, top + 12, right - 12, bottom - 12),
                slug not in {"fun_satoshi_quotes", "bitcoin_history"},
            )
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _block_dashboard(data, draw, text, card, palette):
    from .block_explorer import smooth_points

    # Match the e-paper layout: fee estimates and recent blocks share one row.
    now = datetime.now(timezone.utc).timestamp()
    for i, target in enumerate((144, 6, 3, 1)):
        left = 4 + i * 59
        card((left, 38, left + 55, 92))
        text(
            left + 27,
            44,
            str(target),
            13,
            "muted",
            True,
            "mt",
        )
        rate = data["estimates"].get(str(target))
        text(
            left + 27,
            62,
            f"{rate:.1f}" if rate is not None else "N/A",
            14,
            "accent",
            anchor="mt",
        )
        text(left + 27, 78, "sat/vB", 8, "muted", anchor="mt")
    for i, block in enumerate(data["blocks"][:4]):
        # Leave breathing room around the chain-tip divider.
        left = 9 + (i + 4) * 59
        card((left, 38, left + 55, 92))
        text(left + 27, 44, f"#{block['height']}", 12, "text", True, "mt")
        age = max(0, int((now - block["timestamp"]) / 60))
        text(left + 27, 63, f"{age}m", 13, "muted", anchor="mt")
        text(left + 27, 78, "ago", 8, "muted", anchor="mt")
    # Divider marks the chain tip between fee targets and recent blocks.
    # Keep the chain-tip marker the same height as the cards, with breathing
    # room above and below instead of extending into the chart panels.
    draw.line((240, 31, 240, 99), fill=palette["secondary"], width=2)
    lower_top, lower_bottom = 112, 296
    card((8, lower_top, 236, lower_bottom))
    card((244, lower_top, 472, lower_bottom))
    text(18, 121, "Block intervals", 22, "text", True)
    text(254, 121, "Mempool fees", 22, "text", True)
    values = list(reversed(data["intervals"]))
    low = min(0, min((v for _, v in values), default=0))
    high = max(15, max((v for _, v in values), default=10))
    for y in (174, 218, 262):
        draw.line((34, y, 224, y), fill=palette["border"])
        draw.line((268, y, 458, y), fill=palette["border"])
    chart_top, chart_bottom = 174, 262
    target_y = chart_bottom - (10 - low) / (high - low) * (chart_bottom - chart_top)
    for x in range(34, 224, 10):
        draw.line((x, target_y, x + 5, target_y), fill=palette["secondary"])
    points = [
        (
            34 + i * 190 / max(1, len(values) - 1),
            chart_bottom - (v - low) / (high - low) * (chart_bottom - chart_top),
        )
        for i, (_, v) in enumerate(values)
    ]
    if len(points) > 1:
        draw.line(smooth_points(points), fill=palette["accent"], width=2)
    for x, y in points:
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=palette["accent"])
    average = sum(v for _, v in values) / len(values) if values else None
    text(
        18,
        181,
        f"Avg {average:.1f} min" if average is not None else "No history",
        17,
        "muted",
    )
    text(28, 199, f"{high:.0f}", 14, "muted", anchor="rt")
    text(28, 254, f"{low:.0f}", 14, "muted", anchor="rt")
    if values:
        text(34, 273, values[0][0], 15, "muted")
        text(224, 273, values[-1][0], 15, "muted", anchor="rt")
    edges = (1, 2, 5, 10, 50, float("inf"))
    bins = [0.0] * len(edges)
    for rate, size in data["histogram"]:
        for i, edge in enumerate(edges):
            if rate < edge:
                bins[i] += size / 1000000
                break
    total = sum(bins)
    text(254, 181, f"{total:.2f} MvB", 17, "muted")
    maximum = max(max(bins), 1)
    for i, size in enumerate(bins):
        x = 270 + i * 32
        if size:
            draw.rectangle(
                (
                    x,
                    chart_bottom - size / maximum * (chart_bottom - chart_top),
                    x + 21,
                    chart_bottom,
                ),
                fill=palette["accent"],
            )
        text(
            x + 10,
            273,
            ("<1", "1-2", "2-5", "5-10", "10-50", "50+")[i],
            12,
            "muted",
            anchor="mt",
        )
    text(460, 291, "sat/vB", 12, "muted", anchor="rb")
