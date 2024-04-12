import os
import editdistance
import librosa
import soundfile as sf
import sys
import shutil
import argparse
import json

def get_filenames(folder_path):
    # Check if the provided path is a directory
    if not os.path.isdir(folder_path):
        print("Error: Provided path is not a directory.")
        return []

    # Get list of files in the directory
    files = os.listdir(folder_path)
    
    # Filter out directories, if any, and filenames containing 'UNKNOWN' or 'UNIDENTIFIED'
    files = [file for file in files if os.path.isfile(os.path.join(folder_path, file)) and ('UNKNOWN' not in file) and ('UNIDENTIFIED' not in file)]

    return files


def split_string(input_str):
    # Find the index of the first '__'
    first_index = input_str.find('__')
    # Find the index of the last '__'
    last_index = input_str.rfind('__')
    
    # Extract string1, string2, and string3
    string1 = input_str[:first_index] if first_index != -1 else input_str
    string2 = input_str[first_index + 2:last_index] if first_index != -1 and last_index != -1 else ''
    string3 = input_str[last_index + 2:] if last_index != -1 else ''
    
    return [string1, string2, string3]

def get_dir():
    if getattr(sys, 'frozen', False):
        dir = os.path.dirname(sys.executable)
    else:
        dir = os.path.dirname(os.path.abspath(__file__))
    return dir

def copy_dir(source, new):
    shutil.copytree(source, new)

found_ids = {}
dirpath_old = get_dir() + "\\Clips\\"
dirpath_new = get_dir() + "\\ClipsOrdered\\"

if os.path.exists(dirpath_new):
    shutil.rmtree(dirpath_new)
shutil.copytree(dirpath_old, dirpath_new)

old_filenames = (get_filenames(dirpath_new))
new_filenames = []

for filename in old_filenames:
    name_info = split_string(filename)
    if name_info[1] not in found_ids:
        found_ids[name_info[1]] = name_info[0]
    else:
        name_info[0] = found_ids[name_info[1]]
    new_filenames.append(f"{name_info[0]}__{name_info[1]}__{name_info[2]}")

for old_filename, new_filename in zip(old_filenames, new_filenames):
    os.rename(dirpath_new + old_filename, dirpath_new + new_filename)