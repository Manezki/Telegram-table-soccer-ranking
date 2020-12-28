import subprocess
import datetime
import os

# Create folder for the backup
date = datetime.date.today()
backups_folder = os.path.join(os.path.dirname(__file__), "..", "backups")

try:
    os.mkdir(backups_folder)
except FileExistsError:
    pass

dated_backup = os.path.join(backups_folder, str(date))

try:
    os.mkdir(dated_backup)
except FileExistsError:
    pass

# TODO Update at runtime.
# username@server
username_server = ""

# Transfer files
p = subprocess.Popen(["scp", "-r", "{}:TG_Ranking/persistent_storage".format(username_server), dated_backup])
os.waitpid(p.pid, 0)

p = subprocess.Popen(["scp", "-r", "{}:TG_Ranking/message_history".format(username_server), dated_backup])
os.waitpid(p.pid, 0)

p = subprocess.Popen(["scp", "-r", "{}:TG_Ranking/log.txt".format(username_server), dated_backup])
os.waitpid(p.pid, 0)
