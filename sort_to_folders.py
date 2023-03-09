from os import listdir
from os.path import isfile, join

entries = []
labels = set()
with open("./records/_records.txt") as f:
    contents = list(map(str.rstrip, f.readlines()))
    for entry in contents:
        splitted = entry.split(':')
        file_name = splitted[0] + '.wav'
        label = splitted[1].strip()
        entries.append((label, file_name))
        labels.add(label)
print(labels)

from pathlib import Path
for label in labels:
    Path('./records_by_classes/' + label).mkdir(parents=True, exist_ok=True)

import shutil
for entry in entries:
    shutil.copy2('./records/' + entry[1], './records_by_classes/' + entry[0])
    
print('Success')
