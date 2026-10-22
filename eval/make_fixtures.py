"""Generate the synthetic images used by the evaluation fixtures.

Every fixture image is generated programmatically so the evaluation set is
reproducible and carries no licensing questions. Run with:

    python eval/make_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent / "fixtures"

WHITE = (255, 255, 255)
INK = (28, 32, 38)
BLUE = (37, 99, 235)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
GREY = (150, 156, 165)
LIGHT = (243, 244, 246)


def _font(size: int):
    """Return a truetype font when one is available, else the default."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def dashboard(path: Path) -> None:
    """A screenshot style admin dashboard with visible text."""
    img = Image.new("RGB", (640, 400), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 640, 56], fill=(30, 41, 59))
    d.text((20, 18), "Acme Analytics Dashboard", fill=WHITE, font=_font(20))
    d.rectangle([0, 56, 150, 400], fill=LIGHT)
    for i, item in enumerate(["Overview", "Reports", "Settings", "Billing", "Users"]):
        d.text((20, 80 + i * 30), item, fill=INK, font=_font(14))
    d.rectangle([170, 80, 380, 240], fill=WHITE, outline=GREY)
    d.text((186, 96), "Total Revenue", fill=GREY, font=_font(13))
    d.text((186, 118), "$48,210", fill=INK, font=_font(28))
    d.text((186, 160), "up 12% this month", fill=GREEN, font=_font(13))
    d.rectangle([400, 80, 620, 240], fill=WHITE, outline=GREY)
    d.text((416, 96), "Active Users", fill=GREY, font=_font(13))
    d.text((416, 118), "3,904", fill=INK, font=_font(28))
    d.text((416, 160), "down 3% this month", fill=RED, font=_font(13))
    for i, height in enumerate([70, 120, 90, 160, 140, 200]):
        x = 190 + i * 65
        d.rectangle([x, 380 - height, x + 40, 380], fill=BLUE)
    d.text((170, 250), "Monthly signups", fill=INK, font=_font(15))
    img.save(path)


def bar_chart(path: Path) -> None:
    """A bar chart with axis labels and a legend."""
    img = Image.new("RGB", (560, 380), WHITE)
    d = ImageDraw.Draw(img)
    d.text((30, 18), "Revenue by quarter", fill=INK, font=_font(19))
    d.line([70, 60, 70, 310], fill=INK, width=2)
    d.line([70, 310, 520, 310], fill=INK, width=2)
    values = [120, 190, 150, 240]
    labels = ["Q1", "Q2", "Q3", "Q4"]
    colors = [BLUE, GREEN, RED, GREY]
    for i, (value, label, color) in enumerate(zip(values, labels, colors)):
        x = 110 + i * 100
        d.rectangle([x, 310 - value, x + 60, 310], fill=color)
        d.text((x + 12, 320), label, fill=INK, font=_font(14))
        d.text((x + 8, 300 - value), str(value), fill=INK, font=_font(13))
    d.rectangle([380, 30, 398, 48], fill=BLUE)
    d.text((404, 30), "2024", fill=INK, font=_font(13))
    d.rectangle([380, 54, 398, 72], fill=GREY)
    d.text((404, 54), "2023", fill=INK, font=_font(13))
    img.save(path)


def line_chart(path: Path) -> None:
    """A line chart showing a rising trend."""
    img = Image.new("RGB", (560, 360), WHITE)
    d = ImageDraw.Draw(img)
    d.text((30, 18), "Weekly active users", fill=INK, font=_font(19))
    d.line([60, 70, 60, 300], fill=INK, width=2)
    d.line([60, 300, 520, 300], fill=INK, width=2)
    points = [(90, 250), (150, 235), (210, 200), (270, 185), (330, 140), (390, 110), (450, 75), (500, 60)]
    d.line(points, fill=BLUE, width=4)
    for x, y in points:
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=BLUE)
    for i, label in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        d.text((85 + i * 58, 310), label, fill=INK, font=_font(12))
    img.save(path)


def architecture_diagram(path: Path) -> None:
    """A flowchart with boxes and labelled arrows."""
    img = Image.new("RGB", (640, 340), WHITE)
    d = ImageDraw.Draw(img)
    d.text((24, 18), "Request flow", fill=INK, font=_font(19))
    boxes = [
        (40, 110, 170, 180, "Client", BLUE),
        (240, 110, 380, 180, "API Gateway", GREEN),
        (450, 60, 600, 130, "Auth Service", RED),
        (450, 190, 600, 260, "Database", GREY),
    ]
    for x0, y0, x1, y1, label, color in boxes:
        d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=WHITE, outline=color, width=3)
        d.text((x0 + 16, y0 + 28), label, fill=INK, font=_font(15))
    d.line([170, 145, 240, 145], fill=INK, width=3)
    d.polygon([(240, 145), (228, 138), (228, 152)], fill=INK)
    d.line([380, 130, 450, 95], fill=INK, width=3)
    d.polygon([(450, 95), (438, 90), (441, 102)], fill=INK)
    d.line([380, 160, 450, 225], fill=INK, width=3)
    d.polygon([(450, 225), (437, 220), (440, 208)], fill=INK)
    d.text((180, 118), "request", fill=GREY, font=_font(12))
    d.text((392, 78), "verify", fill=GREY, font=_font(12))
    d.text((392, 190), "read", fill=GREY, font=_font(12))
    img.save(path)


def logo(path: Path) -> None:
    """A simple wordmark logo."""
    img = Image.new("RGB", (420, 200), WHITE)
    d = ImageDraw.Draw(img)
    d.ellipse([40, 55, 135, 150], fill=BLUE)
    d.polygon([(70, 150), (105, 150), (87, 95)], fill=WHITE)
    d.text((155, 78), "Northwind", fill=INK, font=_font(34))
    d.text((158, 122), "DATA TOOLS", fill=GREY, font=_font(14))
    img.save(path)


def photo_scene(path: Path) -> None:
    """A synthetic landscape photo."""
    img = Image.new("RGB", (640, 400), (135, 190, 235))
    d = ImageDraw.Draw(img)
    d.ellipse([470, 40, 545, 115], fill=(255, 240, 170))
    d.polygon([(0, 400), (190, 130), (330, 400)], fill=(90, 110, 130))
    d.polygon([(220, 400), (430, 90), (640, 400)], fill=(70, 90, 110))
    d.polygon([(255, 400), (430, 160), (560, 400)], fill=(240, 245, 250))
    d.rectangle([0, 340, 640, 400], fill=(45, 90, 60))
    d.rectangle([300, 320, 320, 360], fill=(60, 45, 30))
    d.polygon([(268, 320), (352, 320), (310, 250)], fill=(50, 100, 60))
    img.save(path)


def badge(path: Path) -> None:
    """A CI style badge used to test decorative detection."""
    img = Image.new("RGB", (120, 20), (49, 163, 84))
    d = ImageDraw.Draw(img)
    d.text((10, 4), "passing", fill=WHITE, font=_font(12))
    img.save(path)


def spacer(path: Path) -> None:
    """A tiny transparent spacer."""
    Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(path)


def terminal(path: Path) -> None:
    """A terminal screenshot with visible command text."""
    img = Image.new("RGB", (560, 320), (24, 26, 32))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 560, 30], fill=(44, 47, 56))
    d.text((12, 8), "bash - npm run deploy", fill=GREY, font=_font(13))
    lines = [
        ("$ npm run deploy", WHITE),
        ("building project...", GREY),
        ("compiled 42 modules in 3.2s", GREY),
        ("deploying to production...", GREY),
        ("deployed successfully", (120, 220, 140)),
    ]
    for i, (line, color) in enumerate(lines):
        d.text((14, 48 + i * 30), line, fill=color, font=_font(14))
    img.save(path)


FIXTURES = {
    "repo_dashboard/docs/dashboard.png": dashboard,
    "repo_dashboard/docs/revenue-bar.png": bar_chart,
    "repo_dashboard/docs/users-line.png": line_chart,
    "repo_charts/docs/quarterly-revenue.png": bar_chart,
    "repo_charts/docs/user-growth.png": line_chart,
    "repo_charts/docs/terminal-output.png": terminal,
    "repo_diagrams/docs/request-flow.png": architecture_diagram,
    "repo_diagrams/docs/northwind-logo.png": logo,
    "repo_screenshots/docs/login-screen.png": dashboard,
    "repo_screenshots/docs/northwind-logo.png": logo,
    "repo_screenshots/docs/terminal-output.png": terminal,
    "repo_mixed/docs/landscape.png": photo_scene,
    "repo_mixed/docs/build-badge.png": badge,
    "repo_mixed/docs/spacer.png": spacer,
    "repo_html/docs/architecture.png": architecture_diagram,
    "repo_rst/docs/report.png": line_chart,
}


def main() -> None:
    for relative, factory in FIXTURES.items():
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        factory(target)
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
