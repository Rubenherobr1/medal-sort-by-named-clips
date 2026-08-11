import sqlite3 as sqlite
import subprocess
import inspect
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# modules that aren't bultin
import handle_title as htitle
import yt_dlp as ytdlp # https://github.com/yt-dlp/yt-dlp
from shared import decodeStrType, BOLD, RESET


class DownloadFailedError(Exception): pass

@dataclass
class Clips:
    id: str
    path: Path
    ogPath: Path = None
    remoteLink: str = None
    isNew: bool = False
    

# -pre-processing-
def getPreviousDir():
    jsonFileName = ".clips.json"
    clipsDirName = "Named_clips"

    # get a list of all clipsDir-like folders
    clipsDirMatches = list(
        Path.cwd().glob("Named_clips-[0-9]/", case_sensitive = True)
    )

    if Path(clipsDirName).exists():
        clipsDirMatches.append(Path(clipsDirName))

    clipsDirMatches = sorted(clipsDirMatches)
    nSuffixes = []

    # check if it has a json file. if it dosen't, it is assumed to be a user-created folder
    for dir in clipsDirMatches:
        if (jsonPath := dir / jsonFileName).exists():
            clipsDir = dir
            return True, jsonPath, clipsDir
        
        nSuffixes.append(str(dir.name).replace("Named_clips-", "")) # "Named_clips" won't be matched due to the '-'

    # create a dir path if none matched
    try: clipsDir
    except NameError:
        count = 1

        while True:
            if str(count) in nSuffixes or (count == 1 and "Named_clips" in nSuffixes):
                count += 1
                continue
            
            suffix = f"-{count}" if count != 1 else ""

            clipsDir = Path(clipsDirName + suffix)
            jsonPath = clipsDir / jsonFileName

            break

    return False, jsonPath, clipsDir


# -remote related-
def queryFileExt(link):
    info = ydl.extract_info(link, download = False)

    return f".{info["formats"][0]["ext"]}"


def downloadClips(remoteClipList):
    ydl.params["quiet"] = "false"

    if (errCode := ydl.download(remoteClipList)) != 0:
        raise DownloadFailedError(f"The download failed ({errCode})")


# -utility functions-
def endScript():
    print("Exiting...\n")
    sys.exit()


def plural(value):
    if value == 1: return ""
    else: return "s" # w/ 0, the gramticly correct thing is with s


def toggleJSONVisibility(hideFile):
    if sys.platform == "win32":
        subprocess.run(["attrib", f"{"+" if hideFile else "-"}H", jsonPath], check=True)


# find db path
medalPath = Path(Path.home(), "AppData", "Roaming", "Medal")

for path in medalPath.iterdir():
    if path.suffix == ".db":
        nIndex = len("medal-") # yields the index that's right after the hyphen, which includes only numbers if its the target db
        
        if path.stem[nIndex].isnumeric(): # ignores medal-guest.db and CustomGameDatabase.db
            dbPath = medalPath / path.name
            print(f"\nPath to database: {dbPath}")
            
            break


# connect to sqlite database and get the video metadata, path and id + the image path to check if it's an image or video
query = inspect.cleandoc("""
    SELECT local_content_id, video_path, metadata
    FROM contents
    WHERE image_path IS NULL
""")

db = sqlite.connect(dbPath) 
resultSet = db.execute(query)

print("Connected to database and executed query\n")


# create the folder where the clips will be in if it dosen't exist yet and get the previous JSON data
previousDir, jsonPath, clipsDir = getPreviousDir()

if previousDir:
    with open(jsonPath, "r") as fJSON:
        previousClips = json.load(fJSON)

else:
    previousClips = {} # what is expected to be outputed if i load a JSON file with an empty dict


# set up class that handles remote clips
config = {
    "quiet": "true", # don't print messages to terminal
    "overwrites": "false", # don't overwrite other files   

    "outtmpl": "%(title)s.%(ext)s", # filename template
    "paths": {"home": str(clipsDir)}, # the default path to put the downloads in

    # yt-dlp recommendation when downloading batch files
    "sleep_interval_requests": 1, # sleep 1s before each download
    "sleep_interval": 5 # sleep 5s between requests (during extraction)
}

ydl = ytdlp.YoutubeDL(config)


# parse the db result set
clipList = []

for id, ogPath, metadata in resultSet: 
    titleKeyPos = metadata.index(b"title") # position of the key for the key: value pair where value is the actual title
    remoteLink = None # so it can be safely put as a param (no value error or whatev)
        
    # check if the clip is arleady in the directory
    if previousClips.get(id) is not None:
        path = Path(previousClips.get(id))
        clipList.append(Clips(id, path))

        print(f"Found '{path.stem}' (arleady in directory)")
        continue

    # check if the clip was manually imported
    isManualImport = False

    if (untitledPos := metadata.find(b"Untitled")) != -1:
        # for imported clips, a key called "contentTitle" will always be "Untitled", and never change,
        # and for clips that are manually imported, the "title" key will be at the end. Since the word
        # "title" is in "Untitled", i need to start the index search after that word

        if untitledPos + 2 == titleKeyPos:
            isManualImport = True

    # check if the clip is remote
    rTitle = htitle.getRawTitle(isManualImport, titleKeyPos, metadata)

    if rTitle is None: continue
    else: print(f"Found '{title}'")

    if ogPath is not None:
        ogPath = Path(ogPath)
        fileExt = ogPath.suffix

    else:
        if isManualImport: # title is after contentShareUrl
            indexStart = 0
            indexEnd = rTitle.pos
        else:
            # start search after the utf-8 encoded title (could have more bytes 
            # because of non-ASCII chars) to prevent any error due to user input

            indexStart = rTitle.pos + len(rTitle.encode("utf-8"))
            indexEnd = len(metadata)

        remoteLink = decodeStrType( 
            metadata, metadata.index(b"contentShareUrl", indexStart, indexEnd) + len("contentShareUrl")
        )

        fileExt = queryFileExt(remoteLink)


    # get the usable title (filename-wise)
    title = htitle.sanitizeTitle(rTitle, clipsDir, fileExt)

    path = clipsDir / (title + fileExt)
    clipList.append(Clips(id, path, ogPath, remoteLink, isNew = True))

print(f"{BOLD}Finished sorting through clips (found {len(clipList)}){RESET}")
db.close()

if len(clipList) == 0: endScript()


# delete outdated clips. if the previous directory didn't exist, create it, and don't check if there's any outdated clips
if previousDir: 
    clipIds = tuple(clip.id for clip in clipList)
    outdatedCount = 0

    for id in previousClips:
        if id not in clipIds:
            Path(previousClips[id]).unlink()
            outdatedCount += 1

    if outdatedCount:
        print(f"{BOLD}Found and deleted {outdatedCount} outdated clip{plural(outdatedCount)}{RESET}\n")

else:
    clipsDir.mkdir()


# copy/download new clips
newClips = tuple(clip for clip in clipList if clip.isNew)
remoteClips = []
hardlinkCount = 0

print("\nChecking if there are any new clips to link or download...")

if not newClips: print("No new clips have been found\n")
else: print()


for clip in newClips:
    if clip.remoteLink is None:
        print(f"Creating a link to '{clip.path.stem}'...")

        clip.path.hardlink_to(clip.ogPath)
        hardlinkCount += 1

    else:
        remoteClips.append(clip.remoteLink)

if hardlinkCount:
    print(f"{BOLD}Finished linking {hardlinkCount} clip{plural(hardlinkCount)}{RESET}\n")

if remoteClips:
    print(f"Downloading {len(remoteClips)} clip{plural(len(remoteClips))}, this might take a while...\n")

    downloadClips(remoteClips)
    print(f"{BOLD}Finished downloading {len(remoteClips)} clip{plural(len(remoteClips))}{RESET}\n")


# generate JSON file to differentiate between user-created "Named-clips" folders,
# to check if there are outdated clips or if a clips is arleady in the directory

# temporarily make the file visible again so i have write permissions
if jsonPath.exists(): 
    toggleJSONVisibility(hideFile = False)


with open(jsonPath, "w") as fJSON:
    json.dump({clip.id: str(clip.path) for clip in clipList}, fJSON, indent = "\t")


# hide the file to disencourage edits/deletion
toggleJSONVisibility(hideFile = True)

print(f"Generated JSON file successfully")
endScript()



