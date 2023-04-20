import os
import shutil
from datetime import datetime, timedelta

# set the path of the directory containing the files
path = "./processed/notConverted"
path_trg = "./data"
os.makedirs(path_trg, exist_ok=True)

# create the train, test and dev directories
os.makedirs(os.path.join(path_trg, "train"), exist_ok=True)
os.makedirs(os.path.join(path_trg, "test"), exist_ok=True)
os.makedirs(os.path.join(path_trg, "dev"), exist_ok=True)

earliest_date = datetime.now().date()
latest_date = datetime.strptime("19700101", '%Y%m%d').date()

for root, dirs, files in os.walk(path):
    for file in files:
        # check if the file has the correct filename format
        if not file.startswith("interp_") or not file.endswith(".txt"):
            continue

        # extract the date from the filename
        date_str = file[7:15]
        date = datetime.strptime(date_str, '%Y%m%d').date()

        # update the earliest date if necessary
        if date < earliest_date:
            earliest_date = date

        if date > latest_date:
            latest_date = date

total_days = (latest_date-earliest_date).days

# iterate over all the files in the directory and its subdirectories
for root, dirs, files in os.walk(path):
    for file in files:
        # check if the file has the correct filename format
        if not file.startswith("interp_") or not file.endswith(".txt"):
            continue

        # extract the date from the filename
        date_str = file[7:15]
        date = datetime.strptime(date_str, '%Y%m%d').date()

        # determine which directory to move the file to
        cur_days = (date-earliest_date).days
        train_cutoff = int(total_days * 0.8)
        test_cutoff = int(total_days * 0.9)

        if cur_days <= train_cutoff:
            dest_dir = "train"
        elif cur_days <= test_cutoff:
            dest_dir = "test"
        else:
            dest_dir = "dev"

        # create the subdirectory in the target directory
        sub_dir = os.path.join(path_trg, dest_dir, os.path.relpath(root, path))
        os.makedirs(sub_dir, exist_ok=True)

        # move the file to the corresponding directory with a new filename
        new_filename = os.path.basename(file)
        dest_path = os.path.join(sub_dir, new_filename)
        shutil.copy(os.path.join(root, file), dest_path)
