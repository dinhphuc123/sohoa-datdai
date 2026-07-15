# scripts/package_artifact.py
"""
Cross-platform artifact packaging script for PyInstaller output.
ASCII-only output to avoid Windows cp1252 encoding errors.
"""
import os
import sys
import shutil

def package(artifact_name: str):
    dist_dir = "dist"
    if not os.path.exists(dist_dir):
        print(f"Error: {dist_dir} directory does not exist.")
        sys.exit(1)

    items = os.listdir(dist_dir)
    print(f"Found items in dist/: {items}")

    target_item = None
    for item in items:
        if item.endswith(".app") or item == "DatDaiDesktop":
            target_item = item
            break

    if not target_item and items:
        target_item = items[0]

    if not target_item:
        print("Error: No built executable found in dist/")
        sys.exit(1)

    source_path = os.path.join(dist_dir, target_item)
    print(f"Archiving {source_path} into {artifact_name}.zip ...")

    shutil.make_archive(artifact_name, "zip", root_dir=dist_dir, base_dir=target_item)
    print(f"[OK] Successfully created {artifact_name}.zip")

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "DatDaiDesktop-Release"
    package(name)
