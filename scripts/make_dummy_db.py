"""Build a ready-to-test database.db filled with dummy data.

    python scripts/make_dummy_db.py                  -> instance/database.db
    python scripts/make_dummy_db.py path/to/x.db     -> any other file

Every date is relative to TODAY (previous months, this month), so the KPI
charts, the History archive, priorities and overdue issues always look "live".
Re-run the script any time to regenerate everything (an existing target file
is replaced). Dummy upload files (issue / TV design pictures) are written to
static/assets/uploads/.

Logins (all dummy):
    super.admin@rndportal.local   SuperAdmin123   (Super Admin)
    qa.admin@rndportal.local      AdminQA12345    (Admin)
    <member e-mail below>         Member12345     (Member)
"""

import os
import random
import sys
from datetime import date, datetime, time, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_TARGET = os.path.join(ROOT, "instance", "database.db")
target = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
os.makedirs(os.path.dirname(target), exist_ok=True)
if os.path.exists(target):
    os.remove(target)
os.environ["DATABASE_URL"] = "sqlite:///" + target.replace("\\", "/")

from PIL import Image, ImageDraw  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from library import create_app  # noqa: E402
from library.extensions import db  # noqa: E402
from library.issue_lifecycle import refresh_issues  # noqa: E402
from library.models import (  # noqa: E402
    BestPractice, Issue, IssueAttachment, PvAsset, PvAssetScan, ToolLink,
    TvDesignAsset, TvDesignAttachment, User, UserCategoryScope, UserEventScope,
)
from library.naming import name_from_email  # noqa: E402
from library.schema import ensure_columns  # noqa: E402
from library.seed import seed_assets, seed_users  # noqa: E402

rng = random.Random(2026)
NOW = datetime.utcnow()
TODAY = date.today()
UPLOADS = os.path.join(ROOT, "static", "assets", "uploads")

# ---------------------------------------------------------------- members
MEMBER_PASSWORD = "Member12345"
MEMBERS = [
    # e-mail, job title, categories, events
    ("gibran.alhafidz@rndportal.local", "SQA Engineer", ["SQA", "OQA"], ["PV", "Pre-MP"]),
    ("aulia.rahma@rndportal.local", "PCBA Engineer", ["PCBA/SMT"], ["PV", "Pre-MP", "MP"]),
    ("rizky.pratama@rndportal.local", "Line Production Engineer", ["Line-Prod"], ["MP", "Field"]),
    ("dewi.lestari@rndportal.local", "OQA Inspector", ["OQA", "SQA"], ["MP", "Field"]),
    ("budi.santoso@rndportal.local", "Service Engineer", ["CSS/SVC"], ["Field", "MP"]),
    ("nadia.putri@rndportal.local", "Reliability Engineer", ["SQA", "PCBA/SMT"], ["PV", "MP"]),
]
FORMER = ("hendra.wijaya@rndportal.local", "Test Engineer", ["SQA"], ["PV", "MP"])  # contract ended
PENDING = ("salsa.maharani@rndportal.local", "QA Trainee", ["OQA"], ["MP"])        # waiting for approval

TITLES = {
    "PCBA/SMT": ["Solder bridge on U12 after reflow", "Pick-and-place offset on feeder 14",
                 "Stencil aperture clogging on fine-pitch pads", "Tombstoning on 0402 capacitors",
                 "Void rate above limit on BGA U3", "AOI false-call rate too high"],
    "SQA": ["Audio crackle at 80% volume", "Wi-Fi drops during OTA update", "Boot loop after factory reset",
            "HDMI handshake fails on cold boot", "Panel flicker at low brightness", "Bluetooth pairing timeout"],
    "Line-Prod": ["Torque out of spec at screw station 6", "Conveyor jam at packing", "ESD wrist-strap failures on line 2",
                  "Label printer misalignment", "Cycle time over target on station 4", "Missing screws in kitting tray"],
    "OQA": ["Cosmetic scratch on bezel (lot 2610)", "Carton label misprint", "Drop test failure on corner sample",
            "Gap between back cover and frame", "Accessory missing in sampled box", "Colour mismatch on remote"],
    "CSS/SVC": ["Customer return: no backlight", "Remote not pairing in the field", "Power board RMA analysis",
                "Intermittent no-signal complaint", "Firmware rollback request", "Speaker rattle reported by dealer"],
}
DESCRIPTIONS = [
    "Reported during routine checks. Needs root-cause analysis and a corrective action before the next build.",
    "Seen on several units from the same lot. Please verify, collect evidence and report back.",
    "Dummy issue for testing the portal. Reproduce, document the cause and close once verified.",
]

# ---------------------------------------------------------------- helpers
def month_start(offset):
    y, m = TODAY.year, TODAY.month - offset
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def at(day, hour=None):
    hour = rng.randint(8, 16) if hour is None else hour
    return datetime.combine(day, time(hour, rng.randint(0, 59)))


def png(path, text, color):
    img = Image.new("RGB", (640, 400), color)
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 619, 379], outline="white", width=4)
    d.text((40, 40), "DUMMY DATA", fill="white")
    d.text((40, 90), text, fill="white")
    img.save(path)


def xlsx(path, title):
    wb = Workbook()
    ws = wb.active
    ws.title = "Log"
    ws.append(["Item", "Result"])
    for i in range(1, 6):
        ws.append([f"{title} #{i}", rng.choice(["OK", "NG", "OK"])])
    wb.save(path)


# ---------------------------------------------------------------- build
app = create_app()
with app.app_context():
    db.create_all()
    ensure_columns()
    seed_users()          # Super Admin + Admin
    seed_assets()         # 24 PV assets from library/seed_data/pv_assets.xlsx
    os.makedirs(os.path.join(UPLOADS, "issues"), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS, "tv-design"), exist_ok=True)

    admin = User.query.filter_by(role="Admin").first()
    superadmin = User.query.filter_by(role="Super Admin").first()

    # ---- users / members
    def add_member(spec, active=True, approved=True):
        email, title, cats, events = spec
        user = User(username=name_from_email(email), email=email, role="Member", job_title=title,
                    is_active=active, approved_at=NOW - timedelta(days=90) if approved else None)
        user.set_password(MEMBER_PASSWORD)
        db.session.add(user)
        db.session.flush()
        for c in cats:
            db.session.add(UserCategoryScope(user_id=user.id, category=c))
        for e in events:
            db.session.add(UserEventScope(user_id=user.id, event=e))
        return user

    members = [add_member(s) for s in MEMBERS]
    former = add_member(FORMER, active=False)
    add_member(PENDING, active=False, approved=False)
    db.session.commit()

    # ---- issues (KPI is computed from these)
    m0, m1, m2 = month_start(0), month_start(1), month_start(2)

    def clamp_day(day):
        return min(day, TODAY)

    def make_issue(member, created_day, deadline_days, status, closed_after=None):
        cat = rng.choice([c.category for c in UserCategoryScope.query.filter_by(user_id=member.id)])
        event = rng.choice([e.event for e in UserEventScope.query.filter_by(user_id=member.id)])
        created = at(clamp_day(created_day))
        closed_at = None
        if status == "Closed":
            closed_at = min(created + timedelta(days=closed_after, hours=rng.randint(0, 5)), NOW)
        issue = Issue(
            title=rng.choice(TITLES[cat]), description=rng.choice(DESCRIPTIONS),
            category=cat, event=event, status=status,
            deadline=created.date() + timedelta(days=deadline_days),
            owner_name=rng.choice([admin.username, superadmin.username]),
            assignee_id=member.id, created_at=created, closed_at=closed_at,
        )
        db.session.add(issue)
        return issue

    for i, member in enumerate(members):
        # two months ago: closed on time
        for k in range(2):
            make_issue(member, m2 + timedelta(days=3 + 5 * k + i), 10, "Closed", closed_after=rng.randint(3, 8))
        # last month: mostly on time, one late
        for k in range(3):
            make_issue(member, m1 + timedelta(days=2 + 6 * k + i), 9, "Closed", closed_after=rng.randint(2, 8))
        make_issue(member, m1 + timedelta(days=20 - i), 5, "Closed", closed_after=9)          # closed after the deadline
        # this month: every stage
        make_issue(member, m0 + timedelta(days=i % 3), 14, "Closed", closed_after=rng.randint(2, 6))
        make_issue(member, m0 + timedelta(days=1 + i % 4), 6, "Pending")
        make_issue(member, m0 + timedelta(days=2 + i % 5), 25, "Open")
        make_issue(member, TODAY - timedelta(days=rng.randint(0, 2)), 20, "Open")
        make_issue(member, m0 + timedelta(days=3 + i % 3), 3, "Open")                          # overdue if the month is far enough
        held = make_issue(member, m0 + timedelta(days=4), 18, "On Hold")
        held.held_since = TODAY - timedelta(days=3)   # on hold since 3 days: clock paused
        held.hold_days = 2 if i % 2 == 0 else 0       # some were already on hold earlier
    # an overdue issue for everyone, regardless of the day of the month
    for member in members:
        make_issue(member, TODAY - timedelta(days=12), 5, "Pending")
    # the former member keeps his history
    for k in range(4):
        make_issue(former, m1 + timedelta(days=3 + 5 * k), 8, "Closed", closed_after=rng.randint(2, 7))
    make_issue(former, m2 + timedelta(days=10), 7, "Closed", closed_after=5)
    # unassigned issues (no member yet)
    for cat, event in [("SQA", "PV"), ("OQA", "Field"), ("Line-Prod", "MP")]:
        db.session.add(Issue(title=rng.choice(TITLES[cat]), description=rng.choice(DESCRIPTIONS), category=cat,
                             event=event, status="Open", deadline=TODAY + timedelta(days=15),
                             owner_name=admin.username, created_at=at(TODAY - timedelta(days=2))))
    for n, closed in enumerate(Issue.query.filter_by(status="Closed").order_by(Issue.id).all()):
        if n % 6 == 0:
            closed.hold_days = 2   # was on hold for 2 days before it was finished
    db.session.commit()

    # attachments: pictures + an Excel log on some issues
    sample = Issue.query.filter(Issue.assignee_id.isnot(None)).order_by(Issue.id).all()
    colors = ["#a50034", "#2f6fdb", "#1c8f5a", "#c26a00", "#6b3fa0", "#444b57"]
    for n, issue in enumerate(sample[:6], 1):
        name = f"dummy-issue-{n}.png"
        png(os.path.join(UPLOADS, "issues", name), f"Issue #{issue.id}: {issue.title[:34]}", colors[n - 1])
        db.session.add(IssueAttachment(issue_id=issue.id, filename=name, original_name=f"evidence-{n}.png", file_type="image"))
        issue.image_filename = name
    for n, issue in enumerate(sample[6:8], 1):
        name = f"dummy-issue-log-{n}.xlsx"
        xlsx(os.path.join(UPLOADS, "issues", name), "Check")
        db.session.add(IssueAttachment(issue_id=issue.id, filename=name, original_name=f"test-log-{n}.xlsx", file_type="excel"))
    db.session.commit()

    # ---- best practice notes (shown in User Management / KPI)
    notes = [
        "Always attach a photo of the failing unit before closing an issue.",
        "Check the firmware version first; most boot issues are fixed in the latest build.",
        "Record the lot number in the issue description so the cause can be traced.",
        "Re-run the failing test three times to rule out a one-off glitch.",
        "Verify the fix on at least five units before reporting it as solved.",
    ]
    for member, count in zip(members[:4], (5, 4, 3, 3)):
        for order, note in enumerate(notes[:count]):
            db.session.add(BestPractice(user_id=member.id, note=note, sort_order=order))
    db.session.commit()

    # ---- tools (website links)
    tools = [
        ("GitHub", "Collaboration", "https://github.com", "Source code and issue tracking."),
        ("Confluence", "Documentation", "https://www.atlassian.com/software/confluence", "Team wiki and test reports."),
        ("Jira", "Collaboration", "https://www.atlassian.com/software/jira", "Ticketing for field and factory issues."),
        ("Figma", "Design", "https://www.figma.com", "UI mock-ups and design reviews."),
        ("Postman", "Testing", "https://www.postman.com", "API testing for the connected TV services."),
        ("Regex101", "Testing", "https://regex101.com", "Build and test regular expressions for log parsing."),
        ("Grafana", "Monitoring", "https://grafana.com", "Dashboards for the test-line telemetry."),
        ("Draw.io", "Design", "https://app.diagrams.net", "Flow charts and wiring diagrams."),
        ("Python Docs", "Documentation", "https://docs.python.org/3/", "Reference for the test scripts."),
    ]
    for name, cat, url, desc in tools:
        db.session.add(ToolLink(name=name, kind="Tool", category=cat, url=url, description=desc,
                                created_by_id=rng.choice([admin.id, superadmin.id])))
    db.session.commit()

    # ---- TV design concept
    designs = [
        ("55\" Bezel-less Concept A", "TVD-2610-001", "Batch 2610", "Jakarta Design Center", "Thin bezel, metal stand."),
        ("65\" OLED Back Cover Study", "TVD-2610-002", "Batch 2610", "Jakarta Design Center", "Back cover heat-dissipation study."),
        ("43\" Entry Model Stand", "TVD-2611-003", "Batch 2611", "Bekasi Plant", "Cost-down stand with 2 screws."),
        ("75\" Wall-mount Bracket", "TVD-2611-004", "Batch 2611", "Bekasi Plant", "New VESA bracket, tested to 40 kg."),
        ("Remote Control v3", "TVD-2612-005", "Batch 2612", "Seoul R&D", "Backlit keys and a voice button."),
        ("Soundbar Combo Concept", "TVD-2612-006", "Batch 2612", "Seoul R&D", "TV with an integrated soundbar."),
    ]
    for n, (title, serial, production, origin, note) in enumerate(designs, 1):
        asset = TvDesignAsset(title=title, serial_number=serial, production=production, origin=origin, notes=note,
                              created_by_id=rng.choice([admin.id, superadmin.id]))
        db.session.add(asset)
        db.session.flush()
        name = f"dummy-tv-{n}.png"
        png(os.path.join(UPLOADS, "tv-design", name), f"{serial} {title[:26]}", colors[(n + 2) % len(colors)])
        db.session.add(TvDesignAttachment(asset_id=asset.id, filename=name, original_name=f"{serial}.png", file_type="image"))
    db.session.commit()

    # ---- assets: a few already scanned (the rest stay "Not Checked")
    pv_assets = PvAsset.query.filter(db.func.lower(PvAsset.owner) == "pv").order_by(PvAsset.id).all()
    other_assets = PvAsset.query.filter(db.func.lower(PvAsset.owner) != "pv").order_by(PvAsset.id).all()
    scanners = [admin, superadmin]
    minutes = 5
    for asset in pv_assets[:6]:                                  # verified PV assets
        when = NOW - timedelta(hours=minutes)
        asset.scan_status, asset.scanned_at, asset.scanned_by_id = "match", when, rng.choice(scanners).id
        db.session.add(PvAssetScan(asset_id=asset.id, scanned_serial=asset.serial_number, result="match",
                                   scanned_by_id=asset.scanned_by_id, scanned_at=when))
        minutes += 7
    for asset in other_assets[:3]:                               # registered, but owned by another team
        when = NOW - timedelta(hours=minutes)
        asset.scanned_at, asset.scanned_by_id = when, rng.choice(scanners).id
        db.session.add(PvAssetScan(asset_id=asset.id, scanned_serial=asset.serial_number, result="unknown",
                                   scanned_by_id=asset.scanned_by_id, scanned_at=when))
        minutes += 7
    for serial in ("ZZZZ00000001", "ZZZZ00000002", "ZZZZ00000003"):  # not registered at all
        when = NOW - timedelta(hours=minutes)
        db.session.add(PvAssetScan(asset_id=None, scanned_serial=serial, result="unknown",
                                   scanned_by_id=rng.choice(scanners).id, scanned_at=when))
        minutes += 7
    db.session.commit()

    refresh_issues()  # automatic priority + Open -> Pending, exactly like the app does

    # ---- summary
    from collections import Counter
    print("database:", target)
    print("users:", User.query.count(), "(members:", User.query.filter_by(role="Member").count(), ")")
    print("issues:", Issue.query.count(), dict(Counter(i.status for i in Issue.query)))
    print("priorities:", dict(Counter(i.priority for i in Issue.query)))
    print("assets:", PvAsset.query.count(), "| scans:", PvAssetScan.query.count())
    print("tools:", ToolLink.query.count(), "| tv designs:", TvDesignAsset.query.count(),
          "| best-practice notes:", BestPractice.query.count())
