import os
import editdistance
import librosa
import soundfile as sf
import sys
import shutil
import argparse
import json
import re

# Gets the path relative to either .py or .exe location
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

# Generates all possible ways that words could be broken down to sentences
def generate_sentences(words):
    sentences = []
    for i in range(len(words)):
        for j in range(i + 1, len(words)  + 1):
            sentence = words[i]
            for k in range(i + 1, j):
                sentence += " " + words[k]
            sentences.append(sentence)
    return sentences

# Normalizes a string to be only lower-case characters and spaces, removing special expresions
def normalize_string(input_str):
    if input_str is None:
        return ""

    # Normalizes tagged text, eg italics
    input_str = re.sub('<.*?>', '', input_str)
    # Removes expressions that are presumed to be all text between *'s
    input_str = re.sub(r'\*(.*?)\*', '', input_str)
    input_str = input_str.lower()
    # Removes remaining characters that are not letters
    input_str = re.sub(r'[^a-z0-9\s]', '', input_str)

    if not input_str:
        return ""

    if input_str[-1] == ' ':
        input_str = input_str[:-1]

    return input_str

# Finds the similarity ratio between two strings
def get_similarity(string1, string2):
    if len(string1) == 0 or len(string2) == 0:
        return 0
    distance = editdistance.eval(string1, string2)
    max_len = max(len(string1), len(string2))
    return 1 - (distance / max_len)

# Checks if possible_substring is likely to be a real substring of full_string using similarity threshold
def is_string_substring(full_string, possible_substring, threshold):
    if len(possible_substring) == 0 or len(possible_substring) / len(full_string) > 0.99:
        return False
    words = full_string.split()
    substrings = generate_sentences(words)
    for substring in substrings:
        similarity = get_similarity(substring, possible_substring)
        if similarity >= threshold:
            return True
    return False

# Checks if two strings can be considered similar enough to be treated as a perfect match
def is_perfect_match(string1, string2, threshold):
    similarity = get_similarity(string1, string2)
    if similarity >= threshold:
        return True
    return False

# Converts the int value of the audio segment timestamps into concrete min-sec-millisec value for the audio file
def get_timestamp(old_timestamp, sr):
    seconds = old_timestamp / sr
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{minutes:02d}-{int(seconds):02d}-{milliseconds:03d}"

# Function for reading the data in the dialogue file
def read_dialogue_file(filename):
    sentences_with_titles = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) == 2:
                    sentence = parts[0]
                    title = parts[1]
                    sentences_with_titles.append((sentence, title))
    lines = [item[0] for item in sentences_with_titles]
    ids = [item[1] for item in sentences_with_titles]
    return (lines, ids)

def update_instance_count(dictionary, index, ids):
    if ids[index] in dictionary:
        dictionary[ids[index]] += 1
    else: 
        dictionary[ids[index]] = 1
    return dictionary

def get_match_threshold_by_length(len):
    if len > args.short_long_separator:
        return args.match_threshold_long
    return args.match_threshold_short

def main(args):
    # log.txt will store the execution steps of the algorithm and thus help debugging
    log = open("log.txt", "w", encoding="utf8")

    # Definitions for filepaths used in the script
    directory = get_dir()
    audio_path = args.audio
    dialogue_path = args.dialogue
    transcript_path = os.path.join(directory, "Transcript.txt")
    timestamps_path = os.path.join(directory, "Timestamps.txt")
    final_directory = os.path.join(directory, "Clips")
    not_found_path = os.path.join(directory, "NotFound.txt")

    create_folder(final_directory)

    # Processing audiofile to get stream and sample rate
    y, sr = librosa.load(audio_path, sr = args.sample_rate)


    # Read the outputs of the transcript and the audio segment timestamps
    with open(transcript_path, 'r', encoding="utf8") as file:
        transcript = file.readlines()
    transcript = [string.strip() for string in transcript]
    transcript = [normalize_string(string) for string in transcript]

    with open(timestamps_path, 'r') as file:
        timestamps = file.readlines()
    timestamps = [string.strip() for string in timestamps]
    timestamps = [[int(num) for num in string.split(',')] for string in timestamps]


    # Gets the dialogue lines and the filenames that they need to have (ids)
    (lines, ids) = read_dialogue_file(dialogue_path)
    # Original values are saved for the purpose of printing out original line contents in the NotFound.txt file
    not_normalized = lines    
    lines = [normalize_string(string) for string in lines]

    # Script lines that are normalized to empty strings can't be found via the algorithm and will be saved here. 
    empty_line_ids = []
    to_remove = []
    for i in range(len(lines)):
        if not lines[i]:
            empty_line_ids.append(ids[i] + "   " + not_normalized[i] + "\n")
            to_remove.append(i)

    for i in reversed(to_remove):
        del ids[i]
        del lines[i]
        del not_normalized[i]
    
    # Initializing variables for the matching algorithm

    # Timestamps will be used for cutting the correct audio segment and adding the timestamp to the filename
    final_timestamps = []
    # Saves the filenames of the final result files
    filenames = []

    # Stores found script line IDs to keep track of how many takes a line had
    id_dictionary = {}

    # Indexes to keep track which line from script and line from transcript is being checked while iterating
    lidx = 0
    tidx = 0

    # lidx_saved will store the current lidx value while the algorithm conducts lookup via backtracking and forwardtracking
    lidx_saved = 0

    # Current amount of backtracing / forwardtracking steps taken and the maximum limit of many can be taken
    backtrack = 0
    backtrack_limit = args.backtrack_limit
    forwardtrack = 0
    forwardtrack_limit = args.forwardtrack_limit

    # Parameter for naming unidentified files - the filename stores the transcripted dialogue which can otherwise overflow the name limit
    max_random_name_length = args.max_random_name_length
    
    
    # Algorithm only ends after all transcribed lines are processed. Each transcript line is only processed once
    while tidx < len(transcript):

        # Sometimes the recording will go through the script and later repeat select groups of lines. Thus, if the scrip line list is ever fully iterated over, the process is reset. 
        if  lidx >= len(lines):
            lidx = 0
        
        log.writelines(f"Current transcript line: {transcript[tidx]}\n")
        if tidx + 1 < len(transcript):
            log.writelines(f"Following transcript line:   {transcript[tidx + 1]}\n")
        else:
            log.writelines(f"Following transcript line doesn't exist\n")
            
        log.writelines(f"Current script line:     {lines[lidx]}\n")
        if lidx + 1 < len(lines):
            log.writelines(f"Following script line:   {lines[lidx + 1]}\n")
        else:
            log.writelines(f"Following script line doesn't exist\n")

        # Catches transcripts that failed to identify any text
        if len(transcript[tidx]) == 0:

            final_timestamps.append([timestamps[tidx][0], timestamps[tidx][1]])
            filenames.append(f"UNIDENTIFIED.wav")
            log.writelines(f"No match found after forward and backtrack, saving as UNIDENTIFIED.wav\n\n")
            tidx += 1
            continue

        # Checks if the transcript line is either a substring of or a match with the script line
        if tidx < len(transcript) - 1 and (is_string_substring(lines[lidx], transcript[tidx], args.substring_threshold) 
                                           or is_perfect_match(lines[lidx], transcript[tidx], get_match_threshold_by_length(len(lines[lidx])))):

            log.writelines(f"Found possible match with current line\n")

            # The current index is saved in case its incremented while finding sunbstrings but the final result fails to match
            start_tidx = tidx

            # Current transcript line is saved as the start substring of a sentence that could be a match for the line
            sentence = transcript[tidx]
            # This lines timestamps are saved as the start and end timestamps (a member of timestamps saves both start and end value of an individual line)
            clip_start = timestamps[tidx]
            clip_end = timestamps[tidx]

            # while booleans duplicated for debugging
            is_next_substring = is_string_substring(lines[lidx], transcript[tidx + 1], args.substring_threshold)
            does_similarity_improve = get_similarity(lines[lidx], sentence) < get_similarity(lines[lidx], sentence + " " + transcript[tidx + 1])
            log.writelines(f"Next is substring: {is_next_substring}\n")
            log.writelines(f"Similarity improves: {does_similarity_improve}\n")
            
            # while cycle that takes in more transcribed lines to expand the sentence, so long as it is a substring of the script line and the similarity improves for the sentence with the script line
            while (is_string_substring(lines[lidx], transcript[tidx + 1], args.substring_threshold) and 
                   get_similarity(lines[lidx], sentence) < get_similarity(lines[lidx], sentence + " " + transcript[tidx + 1])):
                tidx += 1
                sentence += " " + transcript[tidx]
                # End timestamp is changed to be the timestamp of the new added transcript line
                clip_end = timestamps[tidx]
                log.writelines(f"Current substring: {sentence}\n")

            log.writelines(f"Checking for match between: \nT: {sentence}\nL: {lines[lidx]}\n")

            # This if filters out non-matching sentences, mainly intended to filter out random strings that satisfied initial if by being substrings of some part of the script line
            if is_perfect_match(lines[lidx], sentence, get_match_threshold_by_length(len(lines[lidx]))):
                
                log.writelines(f"Match found!\n")

                # Saves the data for cutting up the main audio file: timestamp of when to start and end cut as well as the files name
                final_timestamps.append([clip_start[0], clip_end[1]])
                update_instance_count(id_dictionary, lidx, ids)
                filenames.append(f"{ids[lidx]}__take_{id_dictionary[ids[lidx]]}.wav")

                log.writelines(f"Saving substring match as {ids[lidx]}__take_{id_dictionary[ids[lidx]]}.wav\n")

                tidx += 1
                backtrack = 0
                forwardtrack = 0
                
                log.writelines("\n")    
                continue

            else:
                log.writelines(f"Not matching. Similarity only {get_similarity(lines[lidx], sentence)}\n")
                tidx = start_tidx
        

        # Checks if the transcript line is either a substring of or a match with the NEXT script line
        # Main difference is that the script line index lidx gets incremented only in this case
        if tidx < len(transcript) - 1 and lidx + 1 < len(lines) and (is_string_substring(lines[lidx + 1], transcript[tidx], args.substring_threshold)
                                                                       or is_perfect_match(lines[lidx], transcript[tidx], get_match_threshold_by_length(len(lines[lidx + 1])))):
            
            log.writelines(f"Found possible match with the following line\n")

            start_tidx = tidx

            sentence = transcript[tidx]
            clip_start = timestamps[tidx]
            clip_end = timestamps[tidx]

            is_next_substring = is_string_substring(lines[lidx + 1], transcript[tidx + 1], args.substring_threshold)
            does_similarity_improve = get_similarity(lines[lidx + 1], sentence) < get_similarity(lines[lidx + 1], sentence + " " + transcript[tidx + 1])
            log.writelines(f"Next is substring: {is_next_substring}\n")
            log.writelines(f"Similarity improves: {does_similarity_improve}\n")

            while (is_string_substring(lines[lidx + 1], transcript[tidx + 1], args.substring_threshold) and 
                   get_similarity(lines[lidx + 1], sentence) < get_similarity(lines[lidx + 1], sentence + " " + transcript[tidx + 1])):
                tidx += 1
                sentence += " " + transcript[tidx]
                clip_end = timestamps[tidx]
                log.writelines(f"Current substring: {sentence}\n")

            log.writelines(f"Checking for match between: \nT: {sentence}\nL: {lines[lidx + 1]}\n")

            if is_perfect_match(lines[lidx + 1], sentence, get_match_threshold_by_length(len(lines[lidx + 1]))):
            
                log.writelines(f"Match found!\n")

                final_timestamps.append([clip_start[0], clip_end[1]])
                update_instance_count(id_dictionary, lidx + 1, ids)
                filenames.append(f"{ids[lidx + 1]}__take_{id_dictionary[ids[lidx + 1]]}.wav")
                
                log.writelines(f"Saving substring match as {ids[lidx + 1]}__take_{id_dictionary[ids[lidx + 1]]}.wav\n")

                lidx += 1
                tidx += 1
                backtrack = 0
                forwardtrack = 0

                log.writelines("\n")    
                continue

            else:
                log.writelines(f"Not matching. Similarity only {get_similarity(lines[lidx + 1], sentence)}\n")
                tidx = start_tidx


        # Look-up logic

        # If this code is reached it means that the current lidx and tidx pair failed to get a match and a look-up is necessary
        # The look-up searches for a possible match between the current tidx and a series of prior and later lidx values

        # Starting first with backtrack
        if backtrack == 0:
            log.writelines(f"Starting backtrack at {lidx}\n")
            lidx_saved = lidx

        # lidx incremented while backtrack is bellow backtrack limit
        if lidx > 0 and backtrack < backtrack_limit:
            log.writelines(f"Executing backtrack to {lidx - 1}\n")
            lidx -= 1
            backtrack += 1
        
        # Forwardtracking if backtracking fails to get a match
        else:
            backtrack = backtrack_limit

            # Same general logic as backtrack
            if forwardtrack == 0:
                log.writelines(f"Starting forwardtrack at {lidx}\n")
                lidx = lidx_saved

            if lidx < len(lines) and forwardtrack < forwardtrack_limit:
                lidx += 1
                if lidx < len(lines):
                    forwardtrack += 1
                else:
                    forwardtrack = forwardtrack_limit
            
                log.writelines(f"Executing forwardtrack to {lidx}\n")

            # If forwardtrack also fails, then the tidx transcript line is considered as unknown and is saved as such
            else:
                # Unknown's filename contains the transcribed value
                unknown_name = "UNKNOWN__" + transcript[tidx].replace(" ", "_")

                # Trims the name in case the transcripted text is too long for a filename
                if len(unknown_name) > max_random_name_length:
                    unknown_name = unknown_name[:max_random_name_length]

                clip_start = timestamps[tidx]
                clip_end = timestamps[tidx]
                final_timestamps.append([clip_start[0], clip_end[1]])

                filenames.append(f"{unknown_name}.wav")

                # Resets lidx to the original value before lookup
                lidx = lidx_saved
                # Increments tidx to bypass the unknown line
                tidx += 1
                backtrack = 0
                forwardtrack = 0
                log.writelines(f"No match found after forward and backtrack, saving as {unknown_name}.wav\n")

        log.writelines("\n")    

    log.close()

    not_found_ids = []

    # Finding the ids that were not discovered while processing the audio file
    for id in ids:
        if not id in id_dictionary:
            not_found_ids.append(id)

    # Not found ids are saved to a separate file along with the filtered lines after normalization
    with open(not_found_path, 'w', encoding="utf-8") as file:
        file.write("Unfound line IDs:\n")
        for id in not_found_ids:
            id_index = ids.index(id)
            file.write(id + "   " + not_normalized[id_index] + "\n")
        file.write("\nFiltered line IDs:\n")
        for id_and_line in empty_line_ids:
            file.write(id_and_line)

    # Creating segment data from timestamps by which the identified audio clips will be saved
    final_segments = []
    for i, (start, end) in enumerate(final_timestamps):
        # Audio is trimmed to remove silence at the start and end of clip
        start_trim_threshold = args.start_trim_threshold
        end_trim_threshold = args.end_trim_threshold

        # A defined amount of additional time is used as a buffer to not cut too mutch
        start_trim_buffer = args.start_trim_buffer * sr
        end_trim_buffer = args.end_trim_buffer * sr

        clip_audio = y[start:end]
        
        # Cutting frames one by one until one reaching threshold value is found
        i_start = 0
        while clip_audio[i_start] < start_trim_threshold and clip_audio[i_start] > -1 * start_trim_threshold:
            start += 1
            i_start += 1
            
            # This if handles exceptions where an audio segment doesn't have detectable audio
            if i_start > len(clip_audio) - 1:
                start -= i_start
                break

        # Buffer extends the timestamp for cutting
        if start - int(start_trim_buffer) < 0:
            start = 0
        else:
            start -= int(start_trim_buffer)

        # Audio clip processed in reverse for faster array access
        reversed_clip_audio = clip_audio[::-1]

        # Repeated for end of audio clip, logic stays the same
        i_end = 0
        while reversed_clip_audio[i_end] < end_trim_threshold and reversed_clip_audio[i_end] > -1 * end_trim_threshold:
            end -= 1
            i_end += 1
            if i_end > len(reversed_clip_audio) - 1:
                start += i_start
                break
        
        if i_end + int(end_trim_buffer) > len(y) - 1:
            end = len(y) - 1
        else:
            end += int(end_trim_buffer)

        trimmed_audio = y[start:end]
        final_segments.append(trimmed_audio)
        trimmed_timestamp = get_timestamp(start, sr)
        filenames[i] = f"{trimmed_timestamp}__{filenames[i]}"

    # Saving final audio clip
    for i, segment in enumerate(final_segments):
        clip_path = os.path.join(final_directory, filenames[i])
        sf.write(clip_path, segment, sr, format='wav', subtype = 'PCM_32')

# Main to extract the .json file as input variables
if __name__ == "__main__":

    with open(os.path.join(get_dir(), "args.json"), 'r') as file:
        args = json.load(file)
    args = argparse.Namespace(**args)

    main(args)