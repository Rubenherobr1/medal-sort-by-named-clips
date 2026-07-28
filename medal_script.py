import sqlite3 as sqlite
import yt_dlp as ytdlp # https://github.com/yt-dlp/yt-dlp
import subprocess
import json
import sys

from pathlib import Path
from sys import platform


class Clips:
    ogTitles = [] # used to see how many times a title repeats

    def __init__(self, id):
        self.id = id

        self.isNew = False
        self.link = None


# pre-processing
def getPreviousDir():
    jsonFileName = ".copied-clips.json"
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


# title related
def getTitleIDPos(metadata):
    key_titlePos = metadata.index(b"title") # position of the key for the key: value pair where value is the actual title

    try:
        if (untitledPos := metadata.find(b"Untitled")) != -1:
            # for imported clips, a key called "contentTitle" will always be "Untitled", and never change,
            # and for clips that are manually imported, the "title" key will be at the end. Since the word
            # "title" is in "Untitled", i need to start the index search after that word

            if untitledPos + 2 == key_titlePos:
                titleIDPos = metadata.index(b"title", key_titlePos + 1) + len("title")
                return titleIDPos
            
        titleIDPos = metadata.index(b"title") + len("title")
        return titleIDPos

    except ValueError: # if no title key is found
        return None


# decoding related
def normBin(decimalByte):
    byte = bin(decimalByte).replace("0b", "")
    byte = "0" * (8 - len(byte)) + byte # ensures the representation will have 8 bytes regardless

    return byte


def decodeStrType(metadata, strIDPos, yieldPos = False):
    strID = normBin(metadata[strIDPos])
    sizeID = int(strID[:4], 2)
    
    str8, str16 = int("C", 16), int("D", 16)
    unknownStrType = int("E", 16)


    # the length of the str is in the next byte
    if sizeID == str8:
        strLen = metadata[strIDPos + 1]
        strPos = strIDPos + 2

    # the length of the str is the next 2 bytes, as if the 1st of the 
    # two bytes was read together with the second byte

    elif sizeID == str16:
        byte1, byte2 = (
            normBin(metadata[strIDPos + i]) for i in (1, 2)
        )

        strLen = int(byte1 + byte2, 2)
        strPos = strIDPos + 3

    elif sizeID >= unknownStrType:
        UnknownStrTypeError = Exception()
        raise UnknownStrTypeError(f"String type identified by '{hex(sizeID).replace("0x", "")}' is unknown")

    # the length of the str is the 1st nibble of the strID byte
    else:
        if sizeID == 0:
            if not yieldPos: return None
            else: return None, None
        
        strLen = sizeID
        strPos = strIDPos + 1


    txt = metadata[strPos : strPos + strLen].decode("utf-8")

    if not yieldPos: return txt
    else: return txt, strPos


# remote related
def queryFileExtension(link):
    info = ydl.extract_info(link, download = False)

    return info["formats"][0]["ext"]


def downloadClips(remoteClipList):
    ydl.params["quiet"] = "false"

    if (errCode := ydl.download(remoteClipList)) != 0:
        DownloadFailedError = Exception()
        raise DownloadFailedError(f"The download failed (code: '{errCode}')")


# utility functions
def endScript():
    print("Exiting...\n")
    sys.exit()


def plural(value):
    if value == 1: return ""
    else: return "s" # w/ 0, the gramticly correct thing is with s


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
db = sqlite.connect(dbPath) 
resultSet = db.execute("SELECT metadata, local_content_id, video_path, image_path FROM contents")

print("Connected to database and executed query\n")


# create the folder where the clips will be in if it dosen't exist yet and get the previous JSON data
previousDir, jsonPath, clipsDir = getPreviousDir()

if previousDir:
    with open(jsonPath, "r") as fJSON:
        oldCopiedClips = json.load(fJSON)

else:
    clipsDir.mkdir()
    oldCopiedClips = {} # what is expected to be outputed if i load a JSON file with an empty dict


# set up class that handles remote clips
config = {
    "outtmpl": "%(title)s.%(ext)s", # the filename template
    "quiet": "true", # don't print messages to stdout
    "overwrites": "false", # don't overwrite other files
    "paths": {
        "home": str(clipsDir) # the default path to put the downloads in
    }
}

ydl = ytdlp.YoutubeDL(config)

# parse the db result set
MAX_PATH_LEN = 260 # on Windows
clipList = []

for metadata, id, path, imgPath in resultSet: 
    clip = Clips(id)

    if imgPath: continue # if it's a screenshot, by example

    # check if the clip is arleady in the directory
    if oldCopiedClips.get(id) is not None:
        clip.path = Path(oldCopiedClips.get(id))
        clipList.append(clip)

        print(f"Found '{clip.path.stem}'")

        continue


    # get the title
    titleIDPos = getTitleIDPos(metadata)
    if titleIDPos is None: continue

    title, titlePos = decodeStrType(metadata, titleIDPos, yieldPos = True)
    if title is None: continue
        
    print(f"Found '{title}'")

    Clips.ogTitles.append(title)
    clip.isNew = True


    # check if the clip is remote
    if path is not None:
        path = Path(path)

        clip.ogPath = path
        fileExtension = path.suffix

    else:
        clip.link = decodeStrType( # start search after the title to prevent any error due to user input
            metadata, metadata.index(b"contentShareUrl", titlePos + len(title.encode("utf-8"))) + len("contentShareUrl")
        )
        
        fileExtension = queryFileExtension(clip.link) 
        
        
    # check if the title is repeated
    if (nRepeats := Clips.ogTitles.count(title)) > 1:
        suffix = f"-{nRepeats}"
        print(f"\033[1;4mNote\033[0m: The title is repeated, so '{suffix}' will be added at the end")

        title += suffix
        
    else:
        suffix = ""

    # check if the title is too long
    minPathLen = len(str(clipsDir)) + len(fileExtension) + len(suffix)

    if minPathLen + len(title) > MAX_PATH_LEN:
        print(f"\033[1;4mNote\033[0m: The title is too big, so it will be truncated")

        charsLeft = MAX_PATH_LEN - minPathLen
        title = title[:charsLeft] 

        if not title:
            PathSizeError = Exception()
            raise PathSizeError(f"The resulting path is too big (>{MAX_PATH_LEN}), even if the file name is truncated")


    clip.path = clipsDir / (title + fileExtension)
    clipList.append(clip)

print(f"Finished sorting through clips (found {len(clipList)})")
db.close()

if len(clipList) == 0: endScript()


# copy/download new clips
newClips = tuple(clip for clip in clipList if clip.isNew)
remoteClips = []
copyCount = 0

print("\nChecking if there are any new clips to copy or download...")

if not newClips: print("No new clips have been found\n")
else: print()


for clip in newClips:
    if clip.link is None:
        print(f"Copying '{clip.path.stem}'...")

        clip.ogPath.copy(clip.path, preserve_metadata = True)
        copyCount += 1

    else:
        remoteClips.append(clip.link)

if copyCount:
    print(f"Finished copying {copyCount} clip{plural(copyCount)}\n")

if remoteClips:
    print(f"Downloading {len(remoteClips)} clip{plural(len(remoteClips))}, this might take a while...\n")

    downloadClips(remoteClips)
    print(f"Finished downloading {len(remoteClips)} clip{plural(len(remoteClips))}\n")


# delete outdated clips
clipIds = tuple(clip.id for clip in clipList)
outdatedCount = 0

for id in oldCopiedClips:
    if id not in clipIds:
        Path(oldCopiedClips[id]).unlink()
        outdatedCount += 1

if outdatedCount:
    print(f"Found and deleted {outdatedCount} outdated clip{plural(outdatedCount)}\n")


# generate JSON file to differentiate between user-created "Named-clips" folders,
# to check if there are outdated clips or if a clips is arleady in the directory

if platform == "win32" and jsonPath.exists(): # Windows
    subprocess.run(["attrib", "-H", jsonPath], check=True) # temporarily make the file visible again so i have write permissions

with open(jsonPath, "w") as fJSON:
    json.dump({clip.id: str(clip.path) for clip in clipList}, fJSON, indent = "\t")

if platform == "win32": 
    # hide the file to disencourage edits/deletion
    subprocess.run(["attrib", "+H", jsonPath], check=True)

print(f"Generated JSON file successfully")
endScript()


'''
TODO:
- Add minimum storage recomendation/requirement
- Add "instalation" and "usage" section to README (?)
- Explain how the script works on README (summed up)
- Maybe save the clips to an album on Medal
'''


