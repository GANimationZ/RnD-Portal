"""Run once after copying the update, then delete this file.

The update moved some stylesheets and scripts into new folders. Copying a zip
over the project cannot delete the old copies, so this script removes them.
Only the exact files listed below are touched; missing files are skipped.

    python cleanup_old_files.py
"""

import os

OLD_FILES = [
    "static/css/admin/user-management/style.scss",
    "static/css/admin/user-management/style.css",
    "static/css/admin/user-management/style.css.map",
    "static/css/team/structure/style.scss",
    "static/css/team/structure/style.css",
    "static/css/team/structure/style.css.map",
    "static/css/workspace/assets.scss",
    "static/css/workspace/assets.css",
    "static/css/workspace/assets.css.map",
    "static/css/workspace/kpi-dashboard.scss",
    "static/css/workspace/kpi-dashboard.css",
    "static/css/workspace/kpi-dashboard.css.map",
    "static/css/workspace/tools.scss",
    "static/css/workspace/tools.css",
    "static/css/workspace/tools.css.map",
    "static/css/workspace/tv-design.scss",
    "static/css/workspace/tv-design.css",
    "static/css/workspace/tv-design.css.map",
    "static/css/shared/notify.scss",
    "static/css/shared/notify.css",
    "static/css/shared/notify.css.map",
    "static/css/shared/file-preview.scss",
    "static/css/shared/file-preview.css",
    "static/css/shared/file-preview.css.map",
    "static/css/shared/modal.scss",
    "static/css/shared/modal.css",
    "static/css/shared/modal.css.map",
    "static/javascript/shared/notify.js",
    "static/javascript/shared/file-preview.js",
    "static/javascript/shared/excel-export.js",
]

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    removed = 0
    for rel in OLD_FILES:
        path = os.path.join(ROOT, *rel.split("/"))
        if os.path.isfile(path):
            os.remove(path)
            removed += 1
            print("removed", rel)

    for rel in OLD_FILES:
        folder = os.path.dirname(os.path.join(ROOT, *rel.split("/")))
        while folder != ROOT and os.path.isdir(folder) and not os.listdir(folder):
            os.rmdir(folder)
            print("removed empty folder", os.path.relpath(folder, ROOT).replace(os.sep, "/"))
            folder = os.path.dirname(folder)

    print(f"Done: {removed} old file(s) removed.")


if __name__ == "__main__":
    main()
