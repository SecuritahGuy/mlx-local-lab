from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures"
CAMERA = ROOT / "camera"
API = ROOT / "api"
SPORTS = ROOT / "sports"


def porch(name: str, *, people: int = 0, package: bool = False, vehicle: bool = False,
          animal: bool = False, door_open: bool = False, night: bool = False, snow: bool = False) -> None:
    bg = "#162033" if night else "#9ed7f5"
    image = Image.new("RGB", (640, 420), bg)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 285, 640, 420), fill="#eef6ff" if snow else "#87a96b")
    draw.rectangle((150, 70, 490, 340), fill="#d8c3a5", outline="#4b3b2a", width=5)
    draw.rectangle((270, 145, 375, 340), fill="#121212" if door_open else "#704214", outline="white", width=4)
    if not door_open:
        draw.ellipse((350, 238, 359, 247), fill="#f5d76e")
    for index in range(people):
        x = 185 + index * 70
        draw.ellipse((x, 190, x + 34, 224), fill="#e6b98c", outline="#222")
        draw.rectangle((x + 5, 224, x + 29, 302), fill="#355c9a", outline="#222")
        draw.line((x + 8, 302, x, 332), fill="#222", width=7)
        draw.line((x + 26, 302, x + 34, 332), fill="#222", width=7)
    if package:
        draw.rectangle((385, 285, 455, 335), fill="#b77b3e", outline="#402810", width=4)
        draw.line((420, 285, 420, 335), fill="#e6c18a", width=3)
    if vehicle:
        draw.rounded_rectangle((30, 270, 145, 345), radius=15, fill="#c43b3b", outline="#222", width=4)
        draw.ellipse((48, 330, 75, 357), fill="#222")
        draw.ellipse((105, 330, 132, 357), fill="#222")
    if animal:
        draw.ellipse((505, 292, 568, 330), fill="#b87942", outline="#222", width=3)
        draw.ellipse((548, 275, 578, 307), fill="#b87942", outline="#222", width=3)
        draw.line((510, 300, 492, 282), fill="#222", width=4)
    if snow:
        for x in range(20, 630, 55):
            draw.ellipse((x, 30 + (x % 90), x + 8, 38 + (x % 90)), fill="white")
    if night:
        draw.ellipse((530, 30, 580, 80), fill="#f4edb7")
        draw.polygon([(315, 110), (230, 285), (400, 285)], fill="#eedb8a80")
    image.save(CAMERA / f"{name}.png")


def technical_images() -> None:
    image = Image.new("RGB", (800, 460), "white")
    draw = ImageDraw.Draw(image)
    boxes = [(40, 170, 180, 260, "Browser"), (260, 170, 400, 260, "API"), (500, 80, 700, 160, "PostgreSQL"), (500, 285, 700, 365, "Object Storage")]
    for left, top, right, bottom, label in boxes:
        draw.rounded_rectangle((left, top, right, bottom), radius=12, fill="#dceeff", outline="#255a85", width=4)
        draw.text((left + 20, top + 30), label, fill="#111")
    for start, end in [((180, 215), (260, 215)), ((400, 205), (500, 120)), ((400, 225), (500, 325))]:
        draw.line((*start, *end), fill="#333", width=5)
    image.save(API / "architecture.png")

    image = Image.new("RGB", (900, 430), "#1e1e1e")
    draw = ImageDraw.Draw(image)
    lines = ["Application Error", "HTTP 503 Service Unavailable", "TimeoutError: upstream inventory service", "request_id=demo-7f3a", "retry_after=30"]
    for index, line in enumerate(lines):
        draw.text((35, 40 + index * 65), line, fill="#ff6b6b" if index < 2 else "#e6e6e6")
    image.save(API / "application-error.png")

    image = Image.new("RGB", (700, 430), "white")
    draw = ImageDraw.Draw(image)
    values = [42, 67, 55, 88]
    for index, value in enumerate(values):
        x = 90 + index * 140
        draw.rectangle((x, 360 - value * 3, x + 80, 360), fill="#4e79a7")
        draw.text((x + 25, 370), f"Q{index + 1}", fill="#111")
        draw.text((x + 25, 340 - value * 3), str(value), fill="#111")
    draw.text((35, 20), "Requests per second", fill="#111")
    image.save(API / "chart.png")


def difficulty_camera_images() -> None:
    porch("package-obscured", package=True)
    image = Image.open(CAMERA / "package-obscured.png")
    draw = ImageDraw.Draw(image)
    draw.rectangle((430, 270, 485, 345), fill="#4f7d45", outline="#243b20", width=4)
    draw.ellipse((420, 245, 495, 290), fill="#5f9d52")
    image.save(CAMERA / "package-obscured.png")

    porch("lookalike-object")
    image = Image.open(CAMERA / "lookalike-object.png")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((390, 278, 455, 338), radius=8, fill="#315d8f", outline="#172b42", width=4)
    draw.arc((408, 262, 440, 292), 180, 360, fill="#172b42", width=4)
    image.save(CAMERA / "lookalike-object.png")

    porch("ambiguous-object", night=True)
    image = Image.open(CAMERA / "ambiguous-object.png")
    draw = ImageDraw.Draw(image)
    draw.rectangle((402, 296, 440, 334), fill="#56412d", outline="#30251b", width=2)
    draw.rectangle((420, 285, 475, 342), fill="#252525")
    image.save(CAMERA / "ambiguous-object.png")


def team(team: str, sport: str, season: int, wins: int, losses: int, pf: int, pa: int,
         home: str, away: str, recent: list[tuple[int, int]], offense: dict, defense: dict,
         injuries: list[dict], strength: float) -> dict:
    return {"team": team, "sport": sport, "season": season, "as_of": "regular-season-pre-matchup",
            "games_played": wins + losses, "wins": wins, "losses": losses,
            "points_for": pf, "points_against": pa, "home_record": home, "away_record": away,
            "recent_games": [{"for": a, "against": b} for a, b in recent],
            "offensive_stats": offense, "defensive_stats": defense, "injuries": injuries,
            "opponent_strength": {"index": strength}}


def sports_fixtures() -> None:
    pairs = {
        "nfl": (
            team("Harbor Hawks", "nfl", 2025, 6, 2, 226, 168, "4-0", "2-2", [(31, 17), (24, 20), (35, 21), (20, 23), (28, 17)], {"yards_per_play": 6.1, "turnovers": 7}, {"sacks": 24, "takeaways": 15}, [], 1.08),
            team("Prairie Wolves", "nfl", 2025, 5, 3, 190, 181, "3-1", "2-2", [(17, 14), (20, 27), (23, 20), (16, 13), (21, 24)], {"yards_per_play": 5.2, "turnovers": 12}, {"sacks": 18, "takeaways": 10}, [{"position": "left tackle", "status": "questionable"}], 0.97),
            "Harbor Hawks", {"Harbor Hawks": 27, "Prairie Wolves": 20},
        ),
        "nba": (
            team("Metro Comets", "nba", 2025, 7, 3, 1164, 1090, "5-1", "2-2", [(121, 108), (115, 111), (103, 109), (124, 116), (119, 105)], {"true_shooting_pct": 0.603, "turnover_pct": 11.2}, {"defensive_rating": 109.0}, [], 1.04),
            team("Coastal Tides", "nba", 2025, 6, 4, 1122, 1114, "4-1", "2-3", [(110, 108), (118, 121), (107, 99), (112, 116), (120, 114)], {"true_shooting_pct": 0.574, "turnover_pct": 14.1}, {"defensive_rating": 111.4}, [{"position": "center", "status": "out"}], 1.01),
            "Coastal Tides", {"Metro Comets": 108, "Coastal Tides": 112},
        ),
        "mlb": (
            team("Lake Otters", "mlb", 2025, 8, 2, 51, 34, "5-1", "3-1", [(6, 2), (5, 4), (2, 3), (7, 1), (4, 2)], {"ops": 0.781, "home_runs": 14}, {"era": 3.18, "whip": 1.12}, [], 1.02),
            team("Desert Foxes", "mlb", 2025, 6, 4, 44, 42, "4-2", "2-2", [(3, 2), (1, 5), (6, 4), (4, 3), (2, 6)], {"ops": 0.724, "home_runs": 11}, {"era": 4.02, "whip": 1.31}, [{"position": "starting pitcher", "status": "day-to-day"}], 0.99),
            "Lake Otters", {"Lake Otters": 5, "Desert Foxes": 3},
        ),
    }
    for sport, (a, b, winner, score) in pairs.items():
        a_slug = a["team"].lower().replace(" ", "-")
        b_slug = b["team"].lower().replace(" ", "-")
        (SPORTS / f"{sport}-{a_slug}.json").write_text(json.dumps(a, indent=2) + "\n")
        (SPORTS / f"{sport}-{b_slug}.json").write_text(json.dumps(b, indent=2) + "\n")
        matchup = {"sport": sport, "cutoff": "before-matchup", "team_a": a, "team_b": b,
                   "actual_winner": winner, "actual_score": score, "sample_size_warning": True}
        (SPORTS / f"{sport}-matchup-{a_slug}-{b_slug}.json").write_text(json.dumps(matchup, indent=2) + "\n")
    favorite = team("Summit Pilots", "nfl", 2025, 3, 1, 118, 92, "3-0", "0-1",
                    [(42, 10), (20, 19), (17, 24), (39, 38)],
                    {"yards_per_play": 5.3, "coin_toss_wins": 4, "jersey_sales_rank": 1},
                    {"sacks": 8}, [], 0.78)
    underdog = team("Valley Owls", "nfl", 2025, 2, 2, 96, 90, "1-1", "1-1",
                    [(21, 20), (17, 24), (31, 10), (27, 36)],
                    {"yards_per_play": 5.8, "coin_toss_wins": 0, "jersey_sales_rank": 18},
                    {"sacks": 14}, [], 1.16)
    adversarial = {"sport": "nfl", "cutoff": "before-matchup", "team_a": favorite,
                   "team_b": underdog, "data_quality": {"injury_report": "not supplied",
                   "warning": "four-game sample; coin tosses and jersey sales are not performance indicators"},
                   "actual_winner": "Valley Owls", "actual_score": {"Summit Pilots": 20, "Valley Owls": 23},
                   "sample_size_warning": True}
    (SPORTS / "nfl-matchup-summit-pilots-valley-owls.json").write_text(json.dumps(adversarial, indent=2) + "\n")


def main() -> None:
    for path in (CAMERA, API, SPORTS, ROOT / "rag", ROOT / "repos"):
        path.mkdir(parents=True, exist_ok=True)
    scenes = {
        "empty-day": {}, "person": {"people": 1}, "package": {"package": True},
        "vehicle": {"vehicle": True}, "dog": {"animal": True}, "night": {"night": True},
        "snow": {"snow": True}, "door-open": {"door_open": True},
        "multiple-people": {"people": 2},
        "person-package": {"people": 1, "package": True},
    }
    for name, options in scenes.items():
        porch(name, **options)
    truth = {
        name: {"person_present": opts.get("people", 0) > 0, "person_count": opts.get("people", 0),
               "package_present": opts.get("package", False), "vehicle_present": opts.get("vehicle", False),
               "animal_present": opts.get("animal", False), "door_open": opts.get("door_open", False),
               "lighting": "night" if opts.get("night") else "day",
               "weather_visible": "snow" if opts.get("snow") else "clear"}
        for name, opts in scenes.items()
    }
    (CAMERA / "ground_truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    difficulty_camera_images()
    truth.update({
        "package-obscured": {"person_present": False, "person_count": 0,
            "package_present": True, "vehicle_present": False, "animal_present": False,
            "door_open": False, "lighting": "day", "weather_visible": "clear"},
        "lookalike-object": {"person_present": False, "person_count": 0,
            "package_present": False, "vehicle_present": False, "animal_present": False,
            "door_open": False, "lighting": "day", "weather_visible": "clear"},
    })
    (CAMERA / "ground_truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    technical_images()
    sports_fixtures()
    incident = {"service": "inventory-api", "observed_at": "2026-08-19T13:00:00Z",
                "screenshot_endpoint": "/api/vision/application-error",
                "notes": "Customers report intermittent checkout failures. Firmware data is not collected."}
    (API / "incident.json").write_text(json.dumps(incident, indent=2) + "\n")
    (API / "runbook.txt").write_text(
        "For HTTP 503 with an upstream timeout, verify dependency health, request latency, "
        "connection-pool saturation, and retry amplification. Correlate by request ID.\n"
    )


if __name__ == "__main__":
    main()
