import sqlite3 as sqlite
import subprocess
import json

from pathlib import Path
from sys import platform


def normBin(decimalByte):
    byte = bin(decimalByte).replace("0b", "")
    byte = "0" * (8 - len(byte)) + byte # ensures the representation will have 8 bytes regardless

    return byte


def decodeTitle(metadata, titleIDPos):
    titleID = normBin(metadata[titleIDPos])
    sizeID = int(titleID[:4], 2)
    
    str8, str16 = int("C", 16), int("D", 16) 


    # the length of the title is in the next byte
    if sizeID == str8:
        titleLen = metadata[titleIDPos + 1]
        titlePos = titleIDPos + 2

    # the length of the title is the next 2 bytes, as if the 1st of the 
    # two bytes was read together with the second byte. This is the limit
    # for medal clip names (280 bytes)

    elif sizeID == str16:
        byte1, byte2 = (
            normBin(metadata[titleIDPos + i]) for i in (1, 2)
        )

        titleLen = int(byte1 + byte2, 2)
        titlePos = titleIDPos + 3

    # the length of the title is the 1st nibble of the titleID byte
    else:
        if sizeID == 0:
            return None
        
        titleLen = sizeID
        titlePos = titleIDPos + 1

    return metadata[titlePos : titlePos + titleLen].decode("utf-8")


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


# find db path
medalPath = Path(Path.home(), "AppData", "Roaming", "Medal")

for path in medalPath.iterdir():
    if path.suffix == ".db":
        nIndex = len("medal-") # yields the index that's right after the hyphen, which includes only numbers if its the target db
        
        if path.stem[nIndex].isnumeric(): # ignores medal-guest.db and CustomGameDatabase.db
            dbPath = medalPath / path.name
            print(f"Path to database: {dbPath}")
            
            break


# connect to sqlite database and get the video id, path and it's metadata
db = sqlite.connect(dbPath) 
resultSet = db.execute("SELECT remote_content_id, video_path, metadata FROM contents")

print("Connected to database and executed query\n")


# create the folder where the clips will be in if it dosen't exist yet
previousDir, jsonPath, clipsDir = getPreviousDir()

if previousDir:
    with open(jsonPath, "r") as fJSON:
        oldCopiedFiles = json.load(fJSON)

else:
    clipsDir.mkdir()
    oldCopiedFiles = {} # what is expected to be outputed if i load a JSON file with an empty dict


# parse the db result set
MAX_PATH_LEN = 260 # on Windows
titleList = [] # used to see how many times a title repeats
idList = [] # used to check if a clip isn't in medal anymore
copiedFiles = {}
copyCount = 0

for id, path, metadata in resultSet: 
    path = Path(path)

    # get the title, check if it exists
    titleIDPos = metadata.index(b"title") + len("title")
    title = decodeTitle(metadata, titleIDPos)

    if title is None: continue
    print(f"Found '{title}'", end="")


    # check if the clip is arleady in the directory
    if oldCopiedFiles.get(id) is None:
        print(", copying...")
        newClip = True
    else:    
        print()        
        newClip = False

    titleList.append(title)
    idList.append(id)

    
    # alter the clip's title if necessary
    if (nRepeats := titleList.count(title)) > 1: # if the title is repeated
        print(f"\033[1mNote:\033[0m The title is repeated, so '-{nRepeats}' will be added at the end")
        title += f"-{nRepeats}"

    if len(str(clipsDir)) + len(title) + len(path.suffix) > MAX_PATH_LEN:
        print(f"\033[1mNote:\033[0m The title is too big, so it will be truncated")

        charsLeft = MAX_PATH_LEN - (len(str(clipsDir)) + len(path.suffix))
        title = title[:charsLeft] 

        if not title:
            PathSizeError = Exception()
            raise PathSizeError(f"The resulting path is too big (>{MAX_PATH_LEN}), even if the file name is truncated")


    # copy the clip, if it's new
    targetPath = clipsDir / (title + path.suffix)

    if newClip:
        path.copy(targetPath, preserve_metadata = True)
        copyCount += 1

    # save the file to the log
    copiedFiles[id] = str(targetPath)
    

# delete outdated clips
outdatedCount = 0

for id in oldCopiedFiles:
    if id not in idList:
        Path(oldCopiedFiles[id]).unlink()
        outdatedCount += 1

print(f"\nFound and deleted {outdatedCount} outdated clips")


# generate JSON file to check differentiate between user-created "Named-clips" folders,
# to check if there are outdated clips or if a clips is arleady in the directory

if platform == "win32" and jsonPath.exists(): # Windows
    subprocess.run(["attrib", "-H", jsonPath], check=True) # temporarily make the file visible again so i have write permissions

with open(jsonPath, "w") as fJSON:
    json.dump(copiedFiles, fJSON, indent = "\t")

if platform == "win32": 
    # hide the file to disencourage edits/deletion
    subprocess.run(["attrib", "+H", jsonPath], check=True)


print(f"Generated JSON file successfully")
print(f"Finished sorting through clips. Copied {copyCount}/{len(titleList)} files\n")



'''
TODO:
- Add minimum storage recomendation/requirement
- Handle edge case: imported clips have title at the end
- Add "instalation" and "usage" section to README (?)
- Explain how the script works on README (summed up)
- Maybe save the clips to an album on Medal
'''


