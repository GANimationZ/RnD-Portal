import os
from datetime import datetime

from library.extensions import db
from library.models import PvAsset, User
from library.naming import name_from_email
from library.workspace.assets.importer import ImportFormatError, parse_assets_workbook

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


# Dummy PV assets so the Assets page can be tried right away. They are read
# from library/seed_data/pv_assets.xlsx -- the same layout as the Import
# template (No, Item Name, Serial Number, Owner, Location). To change the dummy
# data, edit that Excel file; no code changes needed. Only inserted when the
# asset table is empty.
ASSET_SEED_FILE = os.path.join(os.path.dirname(__file__), "seed_data", "pv_assets.xlsx")


def load_asset_seed():
    """[(name, serial, owner, location)] from the Excel file; invalid rows are skipped."""
    if not os.path.exists(ASSET_SEED_FILE):
        return []
    try:
        rows = parse_assets_workbook(ASSET_SEED_FILE)
    except ImportFormatError:
        return []
    return [(r["name"], r["serial"], r["owner"], r["location"]) for r in rows if not r["error"]]


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
    seed = load_asset_seed()

    if PvAsset.query.first():
        _migrate_legacy_asset_serials()
        # Databases created before Owner / Location existed: fill them in for
        # the dummy assets (only blanks; anything already entered is kept).
        changed = False
        for name, serial, owner, location in seed:
            asset = PvAsset.query.filter_by(serial_key=serial).first()
            if asset is None:
                continue
            if not asset.owner:
                asset.owner, changed = owner, True
            if not asset.location:
                asset.location, changed = location, True
        if changed:
            db.session.commit()
        return

    for name, serial, owner, location in seed:
        db.session.add(PvAsset(
            name=name,
            serial_number=serial,
            serial_key=serial,
            owner=owner,
            location=location,
        ))
    db.session.commit()


def seed_dummy_data():
    seed_users()
    seed_assets()
