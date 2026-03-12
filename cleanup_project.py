import os
import shutil


paths_to_remove = [
    "run.py",
    "app",
    "templates",
    "flask_migrate",
    "instance",
    "migrations",
]

for path in paths_to_remove:
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

print("Flask files removed successfully.")
