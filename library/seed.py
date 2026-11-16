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
# Serial Number format: 4 letters + 8 digits, no dashes (e.g. ABCD12345678).
ASSET_SEED = [
    ("Digital Multimeter Fluke 87V", "FLKE48210931"),
    ("Oscilloscope Tektronix MSO44", "TEKT01278450"),
    ("DC Power Supply Keysight E36313A", "KEYS61004521"),
    ("Color Analyzer Konica Minolta CA-410", "KMCA30417761"),
    ("Spectroradiometer Konica Minolta CS-2000", "KMCS20153398"),
    ("Hipot Tester GW Instek GPT-9803", "GWIN09123450"),
    ("Thermal Chamber ESPEC SU-262", "ESPC00457810"),
    ("Video Signal Generator Astro VG-879", "ASTR77912040"),
    ("HDMI Analyzer Quantum Data 780", "QDAT11820090"),
    ("Torque Screwdriver Kolver FAB12", "KOLV55209140"),
    ("ESD Wrist Strap Tester", "ESDT00120930"),
    ("Infrared Thermometer Fluke 568", "FLKI61827340"),
    ("Clamp Meter Hioki CM4375", "HIOK23098164"),
    ("LCR Meter Hioki IM3536", "HIOL22071450"),
    ("Spectrum Analyzer R&S FPC1500", "RSFP10392800"),
    ("Logic Analyzer Saleae Logic Pro 16", "SALE00418237"),
    ("Sound Level Meter Rion NL-62", "RION00871234"),
    ("Luminance Meter Konica Minolta LS-150", "KMLS10094478"),
    ("Colorimeter X-Rite i1Pro 3", "XRIT00291700"),
    ("Soldering Station Hakko FX-951", "HAKK95107730"),
    ("Digital Caliper Mitutoyo 500-196", "MITU18040215"),
    ("Vibration Tester", "VIBT00033910"),
    ("Remote Control Tester", "RCTL00012700"),
    ("Test Jig TV 55 Inch", "JIGT00920000"),
]

# The first version of the sample data used serials with dashes
# (e.g. FLK-87V-48210931). Databases that already contain those rows get them
# converted to the new format once, so nothing has to be re-entered.
LEGACY_SAMPLE_SERIALS = {
    "FLK-87V-48210931": "FLKE48210931",
    "TEK-MSO44-B0127845": "TEKT01278450",
    "KS-E36313A-MY61004521": "KEYS61004521",
    "KM-CA410-30417761": "KMCA30417761",
    "KM-CS2000-20153398": "KMCS20153398",
    "GW-9803-GEW0912345": "GWIN09123450",
    "ESP-SU262-0045781": "ESPC00457810",
    "ASTRO-VG879-7791204": "ASTR77912040",
    "QD-780-D1182009": "QDAT11820090",
    "KLV-FAB12-5520914": "KOLV55209140",
    "ESD-WT-0012093": "ESDT00120930",
    "FLK-568-61827340": "FLKI61827340",
    "HIK-CM4375-230981644": "HIOK23098164",
    "HIK-IM3536-220714502": "HIOL22071450",
    "RS-FPC1500-103928": "RSFP10392800",
    "SAL-LP16-00418237": "SALE00418237",
    "RION-NL62-00871234": "RION00871234",
    "KM-LS150-10094478": "KMLS10094478",
    "XR-I1PRO3-A002917": "XRIT00291700",
    "HKO-FX951-FX9510773": "HAKK95107730",
    "MTY-500196-18040215": "MITU18040215",
    "VIB-TST-0003391": "VIBT00033910",
    "RCT-LG-000127": "RCTL00012700",
    "JIG-TV55-0092": "JIGT00920000",
}


def _migrate_legacy_asset_serials():
    changed = False
    for old, new in LEGACY_SAMPLE_SERIALS.items():
        asset = PvAsset.query.filter_by(serial_key=old).first()
        if asset and not PvAsset.query.filter_by(serial_key=new).first():
            asset.serial_number = new
            asset.serial_key = new
            changed = True
    if changed:
        db.session.commit()


def seed_assets():
    if PvAsset.query.first():
        _migrate_legacy_asset_serials()
        return

    for name, serial in ASSET_SEED:
        db.session.add(PvAsset(
            name=name,
            serial_number=serial,
            serial_key=serial,
        ))
    db.session.commit()


def seed_dummy_data():
    seed_users()
    seed_assets()
