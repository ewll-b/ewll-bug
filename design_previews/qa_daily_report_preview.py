from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa_daily_report_preview.png"

W, H = 1600, 1100
SCALE = 2
CANVAS = (W * SCALE, H * SCALE)


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc" if weight == "bold" else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size * SCALE, index=0)
        except Exception:
            continue
    return ImageFont.load_default()


F = {
    "display": font(58, "bold"),
    "title": font(42, "bold"),
    "h2": font(30, "bold"),
    "h3": font(24, "bold"),
    "body": font(22),
    "small": font(18),
    "tiny": font(15),
    "number": font(54, "bold"),
    "metric": font(42, "bold"),
    "ring": font(38, "bold"),
    "huge": font(82, "bold"),
}


def sc(v: int | float) -> int:
    return int(round(v * SCALE))


def xy(box):
    return tuple(sc(v) for v in box)


def draw_round(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy(box), sc(radius), fill=fill, outline=outline, width=sc(width))


def draw_text(draw: ImageDraw.ImageDraw, pos, text, fill, fnt, anchor=None, spacing=4):
    draw.multiline_text((sc(pos[0]), sc(pos[1])), text, fill=fill, font=fnt, anchor=anchor, spacing=sc(spacing))


def text_width(draw, text, fnt):
    b = draw.textbbox((0, 0), text, font=fnt)
    return (b[2] - b[0]) / SCALE


def draw_pill(draw, x, y, text, fill, text_fill, border=None):
    tw = text_width(draw, text, F["small"])
    h = 38
    w = tw + 34
    draw_round(draw, (x, y, x + w, y + h), 19, fill, border)
    draw_text(draw, (x + w / 2, y + h / 2 - 1), text, text_fill, F["small"], anchor="mm")
    return w


def draw_card(draw, box, fill="#ffffff", outline="#e4e9f2"):
    x1, y1, x2, y2 = box
    draw_round(draw, (x1 + 5, y1 + 7, x2 + 5, y2 + 7), 8, "#d8e0ec")
    draw_round(draw, box, 8, fill, outline, 1)


def draw_metric_card(draw, box, label, value, sub, accent, icon_label):
    draw_card(draw, box)
    x1, y1, x2, y2 = box
    draw_round(draw, (x1 + 30, y1 + 30, x1 + 76, y1 + 76), 8, accent)
    draw_text(draw, (x1 + 53, y1 + 54), icon_label, "#ffffff", F["small"], anchor="mm")
    draw_text(draw, (x1 + 98, y1 + 33), label, "#546173", F["small"])
    draw_text(draw, (x1 + 30, y1 + 91), value, "#172033", F["metric"])
    draw_text(draw, (x1 + 30, y1 + 154), sub, "#768296", F["small"])


def draw_progress_bar(draw, box, pct, fill, bg="#e8edf5"):
    x1, y1, x2, y2 = box
    draw_round(draw, box, 8, bg)
    draw_round(draw, (x1, y1, x1 + (x2 - x1) * pct, y2), 8, fill)


def draw_ring(draw, center, radius, width, pct, color, bg="#edf2f7"):
    cx, cy = center
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.arc(xy(bbox), start=0, end=360, fill=bg, width=sc(width))
    # Start at top, clockwise.
    draw.arc(xy(bbox), start=-90, end=-90 + 360 * pct, fill=color, width=sc(width))


def draw_step(draw, cx, cy, title, value, detail, color, active=True):
    r = 33
    fill = color if active else "#f3f6fa"
    txt = "#ffffff" if active else "#8893a5"
    draw_round(draw, (cx - r, cy - r, cx + r, cy + r), r, fill)
    draw_text(draw, (cx, cy - 1), value, txt, F["h2"], anchor="mm")
    draw_text(draw, (cx, cy + 55), title, "#1d2a3b", F["h3"], anchor="mm")
    draw_text(draw, (cx, cy + 87), detail, "#79859a", F["small"], anchor="mm")


def gradient_background(img):
    px = img.load()
    top = (239, 246, 249)
    bottom = (250, 252, 255)
    for y in range(CANVAS[1]):
        t = y / max(1, CANVAS[1] - 1)
        for x in range(CANVAS[0]):
            # A faint cool wash from upper left, not a decorative orb.
            d = math.hypot(x / CANVAS[0] - 0.16, y / CANVAS[1] - 0.08)
            wash = max(0, 1 - d * 2.1) * 0.08
            base = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            px[x, y] = tuple(min(255, int(base[i] * (1 - wash) + (214, 235, 235)[i] * wash)) for i in range(3))


def main():
    img = Image.new("RGB", CANVAS, "#f7fafc")
    gradient_background(img)
    draw = ImageDraw.Draw(img)

    # Main shell
    draw_card(draw, (70, 58, 1530, 1040), "#ffffff", "#dfe6ef")

    # Header
    draw_round(draw, (70, 58, 1530, 225), 8, "#172033")
    draw.rectangle(xy((70, 185, 1530, 225)), fill="#172033")
    draw_round(draw, (110, 100, 172, 162), 8, "#24a094")
    draw_text(draw, (141, 132), "QA", "#ffffff", F["h3"], anchor="mm")
    draw_text(draw, (198, 95), "测试日报", "#ffffff", F["display"])
    draw_text(draw, (202, 165), "Alvin'S Club 2.9.0 · 发布前收尾验证", "#b9c7d8", F["body"])
    draw_pill(draw, 1186, 102, "低风险", "#e7fbf3", "#08795f")
    draw_pill(draw, 1304, 102, "缺陷清零", "#fff4d7", "#8a5d00")
    draw_text(draw, (1410, 174), "2026.07.29", "#d8e3ef", F["small"], anchor="mm")

    # Conclusion strip
    draw_round(draw, (110, 253, 1490, 330), 8, "#eef8f6", "#d5ebe7")
    draw_text(draw, (142, 278), "今日结论", "#08795f", F["h3"])
    draw_text(
        draw,
        (276, 279),
        "测试整体完成度 99%，缺陷已全部修复并完成回归；剩余 2 条用例建议在发版前完成收尾执行与冒烟复核。",
        "#233044",
        F["body"],
    )

    # Metric cards
    left = 110
    gap = 24
    card_w = (1380 - gap * 3) / 4
    y = 364
    h = 205
    metrics = [
        ("整体进度", "99%", "进入发版前收尾阶段", "#24a094", "总"),
        ("用例执行", "182 / 184", "剩余 2 条待执行", "#2f80ed", "例"),
        ("缺陷修复", "25 / 25", "修复率 100%", "#f2994a", "修"),
        ("打开缺陷", "0", "当前无阻塞缺陷", "#eb5757", "开"),
    ]
    for i, item in enumerate(metrics):
        x = left + i * (card_w + gap)
        draw_metric_card(draw, (x, y, x + card_w, y + h), *item)

    # Progress and defect panels
    draw_card(draw, (110, 606, 730, 850))
    draw_text(draw, (144, 637), "测试进度", "#172033", F["h2"])
    draw_text(draw, (144, 681), "用例执行进度与整体风险状态", "#768296", F["small"])
    draw_ring(draw, (266, 758), 52, 14, 0.99, "#24a094")
    draw_text(draw, (266, 752), "99%", "#172033", F["ring"], anchor="mm")
    draw_text(draw, (266, 822), "整体", "#768296", F["small"], anchor="mm")
    draw_text(draw, (395, 728), "已测 182 条 / 总用例 184 条", "#263244", F["body"])
    draw_progress_bar(draw, (395, 774, 670, 792), 182 / 184, "#2f80ed")
    draw_text(draw, (395, 814), "执行完成率 98.9% · 待测 2 条", "#768296", F["small"])

    draw_card(draw, (760, 606, 1490, 850))
    draw_text(draw, (794, 637), "缺陷闭环", "#172033", F["h2"])
    draw_text(draw, (794, 681), "发现、修复、回归、打开缺陷状态一屏看清", "#768296", F["small"])
    step_y = 748
    steps = [
        (880, step_y, "发现", "25", "累计提交", "#2f80ed", True),
        (1050, step_y, "修复", "25", "全部完成", "#f2994a", True),
        (1220, step_y, "回归", "25", "验证通过", "#24a094", True),
        (1390, step_y, "打开", "0", "无遗留", "#eb5757", False),
    ]
    for a, b in [(918, 1012), (1088, 1182), (1258, 1352)]:
        draw.line(xy((a, step_y, b, step_y)), fill="#d8e0eb", width=sc(3))
    for step in steps:
        draw_step(draw, *step)

    # Bottom panels
    draw_card(draw, (110, 884, 905, 1000), "#fbfcfe")
    draw_text(draw, (144, 915), "风险 / 备注", "#172033", F["h2"])
    draw_round(draw, (144, 955, 220, 982), 8, "#e7fbf3", "#cceee6")
    draw_text(draw, (182, 969), "低", "#08795f", F["small"], anchor="mm")
    draw_text(
        draw,
        (244, 951),
        "暂无打开缺陷；发布前重点关注剩余 2 条用例、核心路径冒烟与线上配置检查。",
        "#4b5668",
        F["small"],
    )

    draw_card(draw, (935, 884, 1490, 1000), "#fbfcfe")
    draw_text(draw, (969, 915), "明日/下一步", "#172033", F["h2"])
    draw_text(draw, (969, 956), "完成剩余用例 · 执行发版冒烟 · 同步最终测试结论", "#4b5668", F["small"])

    # Footer
    draw.line(xy((110, 1022, 1490, 1022)), fill="#edf1f7", width=sc(1))
    draw_text(draw, (112, 1039), "建议日报结构：结论先行 / 关键指标 / 缺陷闭环 / 风险备注 / 下一步", "#97a3b6", F["tiny"])
    draw_text(draw, (1490, 1039), "QA Daily Report", "#97a3b6", F["tiny"], anchor="ra")

    img = img.resize((W, H), Image.Resampling.LANCZOS)
    img.save(OUT, quality=96)
    print(OUT)


if __name__ == "__main__":
    main()
