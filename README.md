# Auto voice-over audio cutter

Project for transcribing and cutting up large dialogue audio files into individual audio clips. 
The final output of the project is a folder containing the cut up audio segments that contain either 
unrecognized audio or successfully processed and labeled audio clips. 

This can be used for eg., auto-cutting recorded voice-overs for a game that come from the actor and 
are in one long audio file.


## Scripts

The processor is implemented via a series of three standalone scripts/executable files 
(`AudioCutter.exe`, `Transcriber.exe`, `ClipMaker.exe`), along with an optional 4th one (`FileRenamer.exe`).


### About `AudioCutter.exe`

Cuts up the large audio file into smaller segments by removing longer periods of silence and saves 
them into the Segments folder. The times of these non-silent segments are saved in the `Transcript.txt` file. 
Also saves the input variables into `args.json` file that can be reused by the later scripts. 

Mandatory arguments: 
 
 * `--audio` – the path to the large audio file, 
 * `--dialogue` – path to the `.txt` file containing the dialogue lines and the filenames that they should be titled with.
 
The dialogue text file should contain two columns separated by two tabs, first containing the text values of each 
line and the second containing the identification value of these lines which will later be used to give names to 
the cut audio clips. Here is an example structure of such file:

```
First line dialogue text  test_line_01
Second line dialogue text  test_line_02
Third line dialogue text  test_line_03
```

Optional arguments: 

 * `--top-db` – the average top decibels in an audio segment to consider it as silent, default is 40, 
 * `--minimum_silent` – the minimum amount of time needed for a segment to be silent for it to be cut out as a silent segment, default is 0.5,
 * `--minimum_non_silent` – the minimum amount if time needed for a segment to be not silent to not be rejected as random nois, default is 0.2, 
 * `--silent_buffer` – the amount of time of silence to be kept after the end of an audio clip, default is 0.25, 
 * `--frame_length` – the length of a segment to be checked when detecting silence for cutting segments, default is 2048,
 * `--hop_length` – the length between two frame samples taken when cutting for silence,
 * `--sample_rate` – parameter of the same name of the given audio file, 
 * `--substring_threshold` – for processing transcribed lines, determines the threshold that the similarity ration needs to meet 
   to consider a transcribed line as a substring of a real line, default is 0.724, 
 * `--match_threshold_short` – similarity threshold for matching transcript line as a match to the real line, 
   specifically when the line length is bellow a specified value, default is 0.875, 
 * `--match_threshold_long` – second threshold that can be set to be more lax for longer line match search, default is 0.775, 
 * `--short_long_separator` – the length value needed to be crossed to treat a line as long and use the long match threshold for it, default is 50, 
 * `--start_trim_threshold` – defines the percentage of the normalized frame loudness needed to be reached for a frame to be considered non-silent 
   while checking from the start of the file, used for final trimming of audio files, default is 0.0025,
 * `--end_trim_threshold` – same as above but while checking from the back, default is 0.0025,
 * `--start_trim_buffer` – time in seconds to be additionally included at the start after the cut is determined by loudness, default is 0,
 * `--end_trim_buffer` – same as above, but for including extra time at the end of the cut segment, default is 0.1,
 * `--backtrack_limit` – defines how far the search for the right script line can backtrack, useful for when the audio recorded 
   a few lines repeated in a few loops of different takes, default is 20),
 * `--forwardtrack_limit` – defines how far the search can look up forward for the match between line and transcript, 
   thus avoiding cases of unidentifiable script lines breaking the algorithm, default is 20,
 * `--max_random_name_length` – maximum length for the name that could be given to an audio file that was unidentified and thus had its transcript line added to its title.

Arguments are passed using the following format: `--{argument_name}="{value}"`.


### About `Transcriber.exe`

Uses Whisper NLP model to transcribe the cut up audio files into a transcript. 
The processing of this script takes a long time and is highly system dependant. 
Because of this the entire project is split in these three scripts, as `Transcriber.exe` 
should only be repeated once per large audio file. This script can only be run 
successfully if it can find the path to `ffmpeg.exe` file that is packed along with 
this script and shares the folder with the Whisper model `small.en.pt`. 
The output will be saved as Transcript.txt in the scripts folder. 

Links to Whisper model files can be found here: <https://github.com/openai/whisper/blob/main/whisper/__init__.py>

In case ffmpeg is not installed on the users machine, a precompiled `ffmpeg.exe` binary 
can be found here at <https://www.gyan.dev/ffmpeg/builds/> and then included in the tools folder. 


### About `ClipMaker.exe`

Compares the transcript file with the dialogue script file in order to find the correctly 
transcribed audio segments that then get named apporpriately and stored in the `Clips` folder, 
following the naming scheme of `{timestamp}__{filename}__take_{take number}`. If the transcription 
of an audio segment failed to make a match, the file is saved as `{timestamp}__{UNKNOWN}__{transcribed text}`. 
If the transcription failed to detect words at all, the file is then saved as `{timestamp}__UNIDENTIFIED`. 
Original dialogue lines of which no instances were found are indicated by saving them in a 
separate file called `NotFound.txt`. This script is dependant on the `args.json`, `timestamps.txt` 
and transcript.txt files created by former scripts, as well as on the formerly used audio file.


#### Text normalization for comparisons

The current implementation of the script tries to normalize the transcript and dialogue script lines 
to be as similar as possible. These have been picked to fit a specific dialogue script standart. 
For instance, all text between `*` symbols gets deleted, assuming it is used to mark emotive sounds 
which can't be transcribed. For more general normalization, non-latin symbols are filtered out, 
as the used model can only transcribe them using Latin characters.  Also, all text is cast to lower-case letters. 
Ultimately, the code will require personalized tweaking for handling different standarts of dialogue scripts. 


### About `FileRenamer.exe`

Optional script that creates a new copy of the result `Clips` folder created by `ClipMaker.exe`, 
called `ClipsOrdered`. It then reads all the filenames of the clip files inside the folder and 
renames them in such a way that the timestamp of every take of a single line would be the same 
as the timestamp of the first take instance of that line. Thus, the files, when sorted by title, 
will group all the different lines together and thus help some users to navigate the results more easily. 


## Running the scripts

The scripts should be run in order. Example commands are as follows:

```
AudioCutter --file="%FILEPATH1%" --audio="%FILEPATH2%"
Transcriber
ClipMaker
FileRenamer
```


## Code dependencies

The processor is written in Python, using the install of Python 3.12.2. The dependencies for 
the project were acquired using the pip install command and the code it self was compiled 
into a onefile `.exe` using PyInstaller. This was done using the commands:

```
PyInstaller --onefile %DIR_PATH%\AudioCutter.py
PyInstaller --add-data="C:\Program Files\Python312\Lib\site-packages\whisper;whisper" --onefile %DIR_PATH%\Transcriber.py
PyInstaller --onefile %DIR_PATH%\ClipMaker.py
PyInstaller --onefile %DIR_PATH%\FileRenamer.py
```

Bellow is the result of the pip list command, giving the list of all dependencies that 
were presently installed during the making of this tool:

```
altgraph                  0.17.4
asttokens                 2.4.1
audioread                 3.0.1
certifi                   2024.2.2
cffi                      1.16.0
charset-normalizer        3.3.2
colorama                  0.4.6
comm                      0.2.1
cx_Freeze                 6.16.0.dev46
cx_Logging                3.1.0
Cython                    3.0.8
debugpy                   1.8.0
decorator                 5.1.1
editdistance              0.6.2
executing                 2.0.1
ffmpeg                    1.4
filelock                  3.13.1
fsspec                    2024.2.0
fuzzywuzzy                0.18.0
idna                      3.6
ipykernel                 6.29.2
ipython                   8.21.0
jedi                      0.19.1
Jinja2                    3.1.3
joblib                    1.3.2
jupyter_client            8.6.0
jupyter_core              5.7.1
lazy_loader               0.3
librosa                   0.10.1
lief                      0.14.0
llvmlite                  0.42.0
MarkupSafe                2.1.5
matplotlib-inline         0.1.6
more-itertools            10.2.0
mpmath                    1.3.0
msgpack                   1.0.7
multidict                 6.0.5
nest-asyncio              1.6.0
networkx                  3.2.1
Nuitka                    2.0.3
numba                     0.59.0
numpy                     1.26.4
openai-whisper            20231117
ordered-set               4.1.0
packaging                 23.2
parso                     0.8.3
pefile                    2023.2.7
pillow                    10.2.0
pip                       24.0
platformdirs              4.2.0
pooch                     1.8.0
prompt-toolkit            3.0.43
psutil                    5.9.8
pure-eval                 0.2.2
pycparser                 2.21
pydub                     0.25.1
Pygments                  2.17.2
pyinstaller               6.4.0
pyinstaller-hooks-contrib 2024.1
python-dateutil           2.8.2
pywin32                   306
pywin32-ctypes            0.2.2
pyzmq                     25.1.2
regex                     2023.12.25
requests                  2.31.0
scikit-learn              1.4.0
scipy                     1.12.0
setuptools                69.1.0
six                       1.16.0
soundfile                 0.12.1
soxr                      0.3.7
SpeechRecognition         3.10.1
spicy                     0.16.0
stack-data                0.6.3
sympy                     1.12
threadpoolctl             3.2.0
tiktoken                  0.5.2
torch                     2.2.0
tornado                   6.4
tqdm                      4.66.1
traitlets                 5.14.1
typing_extensions         4.9.0
urllib3                   2.2.0
wcwidth                   0.2.13
wheel                     0.42.0
zstandard                 0.22.0
```
