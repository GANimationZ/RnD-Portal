"""Seeds two demo accounts (Super Admin + QA Admin) so the User
Management flow can be tried immediately. No Issue/KPI/Tool dummy data --
all of that comes from real usage through the UI. The only sample data besides
the accounts is a small PV asset list (see ASSET_SEED) so the Assets page can be
tried right away.

Display names are derived from the emails (see library/naming.py):
super.admin@... -> "Super Admin", qa.admin@... -> "Qa Admin".
Log in with the EMAIL.

Usage:
    from library.seed import seed_dummy_data
    with app.app_context():
        db.create_all()
        seed_dummy_data()   # idempotent, no-op if users already exist
"""

from datetime import datetime

from library.extensions import db
from library.models import PvAsset, User
from library.naming import name_from_email

USER_SEED = [
    {
        "email": "super.admin@rndportal.local",
        "password": "SuperAdmin123",
        "role": "Super Admin",
    },
    {
        "email": "qa.admin@rndportal.local",
        "password": "AdminQA12345",
        "role": "Admin",
    },
]


def seed_users():
    if User.query.first():
        return

    for spec in USER_SEED:
        user = User(
            username=name_from_email(spec["email"]),
            email=spec["email"],
            role=spec["role"],
            approved_at=datetime.utcnow(),
        )
        user.set_password(spec["password"])
        db.session.add(user)

    db.session.commit()


# Sample PV assets so the Assets page can be tried right away. Only inserted
# when the table is empty; delete/replace freely once real data is entered.
ASSET_SEED = [
    ("Digital Multimeter Fluke 87V", "FLK-87V-48210931"),
    ("Oscilloscope Tektronix MSO44", "TEK-MSO44-B0127845"),
    ("DC Power Supply Keysight E36313A", "KS-E36313A-MY61004521"),
    ("Color Analyzer Konica Minolta CA-410", "KM-CA410-30417761"),
    ("Spectroradiometer Konica Minolta CS-2000", "KM-CS2000-20153398"),
    ("Hipot Tester GW Instek GPT-9803", "GW-9803-GEW0912345"),
    ("Thermal Chamber ESPEC SU-262", "ESP-SU262-0045781"),
    ("Video Signal Generator Astro VG-879", "ASTRO-VG879-7791204"),
    ("HDMI Analyzer Quantum Data 780", "QD-780-D1182009"),
    ("Torque Screwdriver Kolver FAB12", "KLV-FAB12-5520914"),
    ("ESD Wrist Strap Tester", "ESD-WT-0012093"),
    ("Infrared Thermometer Fluke 568", "FLK-568-61827340"),
    ("Clamp Meter Hioki CM4375", "HIK-CM4375-230981644"),
    ("LCR Meter Hioki IM3536", "HIK-IM3536-220714502"),
    ("Spectrum Analyzer R&S FPC1500", "RS-FPC1500-103928"),
    ("Logic Analyzer Saleae Logic Pro 16", "SAL-LP16-00418237"),
    ("Sound Level Meter Rion NL-62", "RION-NL62-00871234"),
    ("Luminance Meter Konica Minolta LS-150", "KM-LS150-10094478"),
    ("Colorimeter X-Rite i1Pro 3", "XR-I1PRO3-A002917"),
    ("Soldering Station Hakko FX-951", "HKO-FX951-FX9510773"),
    ("Digital Caliper Mitutoyo 500-196", "MTY-500196-18040215"),
    ("Vibration Tester", "VIB-TST-0003391"),
    ("Remote Control Tester", "RCT-LG-000127"),
    ("Test Jig TV 55 Inch", "JIG-TV55-0092"),
]


def seed_assets():
    if PvAsset.query.first():
        return

    for name, serial in ASSET_SEED:
        db.session.add(PvAsset(
            name=name,
            serial_number=serial,
            serial_key=serial.replace(" ", "").upper(),
        ))
    db.session.commit()


def seed_dummy_data():
    seed_users()
    seed_assets()
