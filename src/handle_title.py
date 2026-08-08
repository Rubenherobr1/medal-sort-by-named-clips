# title-related functions
import sys


def getIDPos(metadata):
    key_titlePos = metadata.index(b"title") # position of the key for the key: value pair where value is the actual title
# setup list of restricted charecters and names for filenames
fakeChars = { # fullwidth variants of restricted charecters
    "/": "\uff0f",
    ">": "\uff1e",
    "<": "\uff1c",
    "|": "\uff5c",
    ":": "\uff1a",
    "&": "\uff06",
    "?": "\uff1f",
    "*": "\uff0a"
}

if sys.platform == "win32":
    fakeChars["\\"] = "\uff3c"
    fakeChars["\""] = "\uff02"

    # names that are reserved on Windows
    win32Names = ["CON", "PRN", "AUX", "NUL"] 

    for i in range(9):
        win32Names.extend((
            f"COM{i+1}", f"LPT{i+1}"
        ))

    # superscript numbers from 1 to 3
    for supN in ("\u00b9", "\u00b2", "\u00b3"): 
        win32Names.extend((
            f"COM{supN}", f"LPT{supN}"
        ))

bannedChars = fakeChars.keys()

# define length limit constants
if sys.platform == "win32":
    MAX_FILENAME = 255
    MAX_PATH = 260 - 1 # not counting the null terminator    

else: # unix based systems
    import os

    MAX_FILENAME = os.pathconf("/", "PC_NAME_MAX")  
    MAX_PATH = os.pathconf("/", "PC_PATH_MAX")

    try:
        if (untitledPos := metadata.find(b"Untitled")) != -1:
            # for imported clips, a key called "contentTitle" will always be "Untitled", and never change,
            # and for clips that are manually imported, the "title" key will be at the end. Since the word
            # "title" is in "Untitled", i need to start the index search after that word

            if untitledPos + 2 == key_titlePos:
                titleIDPos = metadata.index(b"title", key_titlePos + 1) + len("title")
                return titleIDPos, True
            
        titleIDPos = metadata.index(b"title") + len("title")
        return titleIDPos, False

    except ValueError: # if no title key is found
        return None, False









    def sanitize(title):
        for bannedChar in bannedChars:
            if bannedChar in title:
                for _ in range(title.count(bannedChar)):
                    title = title.replace(bannedChar, fakeChars[bannedChar])

        if sys.platform == "win32":
            if title.endswith("."):
                # add full width dot to the end
                title = title[:-1] + "\uff0e"

            elif title.endswith(" "):
                title = title.strip()


        
# -checks-
# check if the title is repeated
def make_checkRepeated():
    ogTitles = [] # used to see how many times a title repeats

    def checkRepeated(title):
        # on windows, don't assume case sensitivity for filenames
        if sys.platform == "win32": ogTitle = title.casefold()
        else: ogTitle = title

        ogTitles.append(ogTitle)


        if (nRepeats := ogTitles.count(title)) > 1:
            suffix = f"-{nRepeats}"
            print(f"\033[1;4mNote\033[0m: The title is repeated, so '{suffix}' will be added at the end")

        else:
            suffix = ""

        return suffix

    return checkRepeated

checkRepeated = make_checkRepeated()


# check if the title is too long
class PathSizeError(Exception): pass

def checkLen(relPath, title, minPathLen):
    path = str(relPath.absolute()) # fix

    if len(title) > MAX_FILENAME or len(path) > MAX_PATH:
        print(f"\033[1;4mNote\033[0m: The title is too big, so it will be truncated")

        if len(title) > MAX_FILENAME:
            title = title[:(MAX_FILENAME - 1)]

        if len(path) > MAX_PATH:
            charsLeft = MAX_PATH - minPathLen
            title = title[:charsLeft] 
    
            if not title:
                raise PathSizeError(
                    f"The resulting path is too big (>{MAX_PATH}), even if the file name is truncated:\n" /
                    path
                )
    
        return title

    return None


