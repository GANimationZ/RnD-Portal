"""
Seeder akun demo.

PERUBAHAN (poin 2 permintaan perombakan): sebelumnya file ini juga
menyeed dummy Employee/KPIRecord/BestPractice/Issue/Member -- semua
DIHAPUS. Sekarang cuma nyeed 2 akun (Super Admin & QA/Admin) supaya bisa
langsung login & coba fitur User Management sejak awal. Semua data lain
(Member, kapabilitas category/event, Issue, KPI) murni hasil pemakaian
nyata lewat UI -- tidak ada lagi data "boongan" yang bercampur dengan
data asli (ini juga yang dimaksud "hubungkan semuanya jadi satu": KPI
Dashboard sekarang membaca User asli ber-role Member, bukan tabel
Employee terpisah yang tidak terhubung ke akun manapun).

Cara pakai:
    from library.seed import seed_dummy_data
    with app.app_context():
        db.create_all()
        seed_dummy_data()   # idempotent -- no-op kalau User sudah ada isinya
"""

from library.extensions import db
from library.models import User

# Password sengaja dituliskan apa adanya di sini (bukan project
# production) supaya gampang dicoba pertama kali -- SEGERA ganti password
# ini via halaman User Management begitu sudah dipakai beneran.
USER_SEED = [
    {
        "username": "superadmin",
        "email": "superadmin@rndportal.local",
        "password": "SuperAdmin123",
        "role": "Super Admin",
    },
    {
        "username": "qa.admin",
        "email": "qa.admin@rndportal.local",
        "password": "AdminQA12345",
        "role": "Admin",
    },
]


def seed_users():
    if User.query.first():
        return

    for spec in USER_SEED:
        user = User(username=spec["username"], email=spec["email"], role=spec["role"])
        user.set_password(spec["password"])
        db.session.add(user)

    db.session.commit()


def seed_dummy_data():
    """Idempotent: no-op kalau tabel users sudah terisi."""
    seed_users()
