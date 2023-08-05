import os
import time
import re
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def get_relative_path(path):
    return os.path.relpath(path)


def merge_files(original, backup, conflict):
    command = ["git", "merge-file", "--union", original, backup, conflict]
    print("Performing command:", " ".join(command))
    exitcode = subprocess.call(command, cwd=os.getcwd())
    if exitcode != 0:
        raise RuntimeError("Git command failed!")


def merge_if_applicable(src_path):
    if not os.path.isfile(src_path):
        # print(src_path, "is not a file")
        return

    candidate_file_path = get_relative_path(src_path)

    match = re.search(
        # . is converted to %2F when a conflict file is opened in Logseq
        "^(.*?)(?:\.|%2F)sync-conflict-([0-9]{8})-([0-9]{6})-(.{7})\.?(.*)$",
        candidate_file_path,
    )

    if match is None:
        # The file is not a syncthing conflict file
        # print(candidate_file_path, "is not a conflict file")
        return

    conflict_file_path = candidate_file_path
    # Run easier to recognize
    print()
    print("Conflict file found:", conflict_file_path)

    # print(x.groups())

    conflict_file_name = match.group(1)
    conflict_file_date = match.group(2)
    conflict_file_time = match.group(3)
    conflict_file_id = match.group(4)
    conflict_file_extension = match.group(5)
    # print(conflict_file_path, conflict_file_date, conflict_file_time, conflict_file_id, conflict_file_extension)

    # HACK: Give Syncthing some time to move the tmpfile (.syncthing.MyFileName) to its real location
    time.sleep(0.1)

    original_file_path = conflict_file_name + "." + conflict_file_extension
    if not os.path.isfile(original_file_path):
        print("... but original file", original_file_path, "doesn't exist")
        # Here we may be too early to leave before Syncthing has moved its timpfile to the real location
        # .syncthing.Testseite.md.tmp
        # print("... what about the Syncthing tempfile?")
        # p = list(os.path.split(original_file_path))
        # tmpfile_name = ".syncthing." + p.pop() + ".tmp"
        # print("name:", tmpfile_name, "path:", p)
        return

    print("For original file:", original_file_path)

    backup_file_regex_string = (
        ".stversions/"
        + conflict_file_name
        + r"~([0-9]{8})-([0-9]{6})\."
        + conflict_file_extension
    )
    backup_file_regex = re.compile(backup_file_regex_string)

    backup_files = []

    for dirpath, subdirs, files in os.walk(os.getcwd() + "/.stversions/"):
        for file in files:
            candidate_path = str(os.path.join(get_relative_path(dirpath), file))
            # print("Test:", candidate)

            match = backup_file_regex.match(candidate_path)
            if match:
                backup_file_date = match.group(1)
                backup_file_time = match.group(2)
                # print("Matched:", candidate_path, backup_file_date, backup_file_time)
                backup_files.append(candidate_path)

    if len(backup_files) == 0:
        print("No backup file candidates were found")
        return

    # print("Backup files:", backup_files)

    # We want the latest backup file, which is the first in the list (??? maybe they are sorted differently)
    backup_file = backup_files[0]
    print("Latest backup file:", backup_file)

    merge_files(original_file_path, backup_file, conflict_file_path)

    print("Deleting conflict file")

    os.remove(os.path.join(os.getcwd(), conflict_file_path))


class Handler(FileSystemEventHandler):

    # To support manually "touch"ing
    @staticmethod
    def on_modified(event):
        merge_if_applicable(event.src_path)

    # This is how Syncthing creates the conflict files
    @staticmethod
    def on_moved(event):
        # print(event) # Syncthing does some moving-around business
        merge_if_applicable(event.dest_path)


if __name__ == "__main__":
    print("Running deconflicter")

    # timeout=10 prevents events being lost on macOS
    observer = Observer(timeout=10)
    event_handler = Handler()
    path = "."

    # From quickstart
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
        print("Stopped deconflicter")
