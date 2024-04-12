import librosa
import numpy as np
import soundfile as sf
import os
import sys
import shutil
import argparse
import json

# Gets the path relative to either script or .exe location
def get_dir():
    if getattr(sys, 'frozen', False):
        dir = os.path.dirname(sys.executable)
    else:
        dir = os.path.dirname(os.path.abspath(__file__))
    return dir

# Creates folder if one doesn't exist before
def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        shutil.rmtree(path)
        os.makedirs(path)

def main(args):
    
    # Definitions for filepaths used in the script
    directory = get_dir()
    audio_path = args.audio
    segment_directory =  os.path.join(directory, "Segments")

    create_folder(segment_directory)

    # Processing audiofile to get stream and sample rate
    y, sr = librosa.load(audio_path, sr = args.sample_rate)

    # Filters for non_silent segments
    non_silent = librosa.effects.split(y, top_db = args.top_db, frame_length = args.frame_length, hop_length = args.hop_length)

    # Finds all silent segments as a reverse compliment of non_silent
    total_duration = len(y) / sr
    silent = []
    for i in range(len(non_silent) + 1):
        start = 0 if i == 0 else non_silent[i - 1][1]
        end = total_duration if i == len(non_silent) else non_silent[i][0]
        silent.append((start, end))

    # Filters silent segments for long_silent
    long_silent = [interval for interval in silent if (interval[1] - interval[0]) / sr >= args.minimum_silent]

    # Finds longer non_silenet segments by finding a reverse compliment of long_silent segments
    new_non_silent = []
    for i in range(len(long_silent) + 1):
        start = 0 if i == 0 else long_silent[i - 1][1]
        end = total_duration if i == len(long_silent) else long_silent[i][0]
        new_non_silent.append((start, end))

    # Converts array to proper datatype
    new_non_silent = np.array(new_non_silent, dtype=np.int32)

    # Filters out too short audio segments
    filtered_non_silent = [interval for interval in new_non_silent if (interval[1] - interval[0]) / sr >= args.minimum_non_silent]
    filtered_non_silent = np.array(filtered_non_silent, dtype=np.int64)

    # Create proper segments for cutting up segments
    segments = []
    for start, end in filtered_non_silent:
        start -= int(args.silent_buffer * sr * 0.2)
        start = max(start, 0)
        end += int(args.silent_buffer * sr)
        end = min(end, len(y))
        segments.append(y[start:end])

    # Saves the cut up audio segments
    for i, segment in enumerate(segments):
        sf.write(os.path.join(segment_directory, f"segment{i:04d}.wav"), segment, sr, format='wav', subtype = 'PCM_32')

    # Saves the timestamps of the audio segments
    with open(os.path.join(directory, "Timestamps.txt"), 'w') as file:
        for start, end in filtered_non_silent:
            start -= int(args.silent_buffer * sr * 0.2)
            start = max(start, 0)
            end += int(args.silent_buffer * sr)
            end = min(end, len(y))
            file.write(f"{start},{end}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to cut up audio file by transcript")

    parser.add_argument("--audio", required=True)
    parser.add_argument("--dialogue", required=True)
    parser.add_argument("--top_db",type=int, default=40)
    parser.add_argument("--minimum_silent", type=float, default=0.5)
    parser.add_argument("--minimum_non_silent", type=float, default=0.2)
    parser.add_argument("--silent_buffer", type=float, default=0.25)
    parser.add_argument("--frame_length", type=int, default=2048)
    parser.add_argument("--hop_length", type=int, default=512)
    parser.add_argument("--sample_rate", type=int, default=48000)
    parser.add_argument("--substring_threshold", type=int, default=0.724)
    parser.add_argument("--match_threshold_short", type=int, default=0.875)
    parser.add_argument("--match_threshold_long", type=float, default=0.775)
    parser.add_argument("--short_long_separator", type=int, default=50)
    parser.add_argument("--start_trim_threshold", type=float, default=0.0025)
    parser.add_argument("--end_trim_threshold", type=float, default=0.0025)
    parser.add_argument("--start_trim_buffer", type=float, default=0)
    parser.add_argument("--end_trim_buffer", type=float, default=0.1)
    parser.add_argument("--backtrack_limit", type=int, default=20)
    parser.add_argument("--forwardtrack_limit", type=int, default=20)
    parser.add_argument("--max_random_name_length", type=int, default=100)

    args = parser.parse_args()

    with open(os.path.join(get_dir(), "args.json"), 'w') as file:
        json.dump(vars(args), file)

    main(args)