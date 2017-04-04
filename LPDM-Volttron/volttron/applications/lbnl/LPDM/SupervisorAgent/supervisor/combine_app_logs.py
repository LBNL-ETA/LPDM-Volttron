import os
from dateutil.parser import parse 
import re

pattern = "Day \d+ \d\d:\d\d:\d\d \((.*?)\)"

root_path = "/home/bob/workspace/volttron/applications/lbnl/LPDM/SupervisorAgent/supervisor/logs/"

all_lines = []

for root, dirs, _ in os.walk(root_path):
    for d in dirs:
        fname = root_path + d + "/app.log"
        with open(fname, "r") as f:
            all_lines.extend(f.readlines())
    break



cleaned = []
invalid_start = ""

for idx, line in enumerate(all_lines):
    try:
        match = re.search(pattern, line)
        if match:
            cleaned.append([float(match.groups()[0]), line])
    except Exception as e:
        print "Error on line {s}\t{e}".format(s = line, e = e)
    
#all_lines = [[parse(x[0]), x[0] + x[1]] for x in all_lines]
cleaned = sorted(cleaned, key=lambda x : x[0])

with open(root_path + "app.log", "w") as f:
    for ts, line in cleaned:
        f.write(line)
        
    if invalid_start:
        f.write("\n" + invalid_start + "\n")

