import whisper
import os
import sys

# Gets the path relative to either script or .exe location
def get_dir():
    if getattr(sys, 'frozen', False):
        dir = os.path.dirname(sys.executable)
    else:
        dir = os.path.dirname(os.path.abspath(__file__))
    return dir

# Definitions for filepaths used in the script
directory = get_dir()
segment_directory = os.path.join(directory, "Segments")

# Path to the used whisper model
MODEL_PATH = os.path.join(directory, "small.en.pt")

# Loading NLP model
model = whisper.load_model(MODEL_PATH)

# Variables for transcription loop
transcript = []
i = 0
files = os.listdir(segment_directory)

for i, file in enumerate(files):
    transcribed_text = model.transcribe(os.path.join(segment_directory, file), fp16=False)
    # Transcript always adds " " at the start of text, it is removed here
    transcribed_text = transcribed_text['text'][1:]
    print(f"Segment {i + 1:04d}/{len(files):04d}: \"{transcribed_text}\"")
    transcript.append(transcribed_text)

# Saving transcribed sentences to file
with open(os.path.join(directory, "Transcript.txt"), 'w', encoding="utf-8") as file:
    for line in transcript:
        file.write(line + '\n')