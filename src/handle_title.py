import sys
from shared import decodeStrType


class PathSizeError(Exception): pass

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


def getRawTitle(clipIsManualImport, titleKeyPos, metadata):
    # get the identifier for the title value and decode the title str
    try:
        if clipIsManualImport:
            IDPos = metadata.index(b"title", titleKeyPos + 1) + len("title")
        else:  
            IDPos = metadata.index(b"title") + len("title")

    except ValueError: # if no title key is found
        return None

    rTitle = decodeStrType(metadata, IDPos)
    return rTitle


def make_truncateTitle():
    isFirstCall = True

    def truncateTitle(txt, path, minPathLen):
        nonlocal isFirstCall

        if len(txt) > MAX_FILENAME or len(path) > MAX_PATH:
            if isFirstCall:
                print(f"\033[1;4mNote\033[0m: The title is too big, so it will be truncated")
                isFirstCall = False

            if len(txt) > MAX_FILENAME:
                txt = txt[:(MAX_FILENAME - 1)]

            if len(path) > MAX_PATH:
                charsLeft = MAX_PATH - minPathLen
                txt = txt[:charsLeft] 

                if not txt:
                    raise PathSizeError(
                        f"The resulting path is too big (>{MAX_PATH}), even if the file name is truncated:\n" /
                        path
                    )
                
        return txt    
    return truncateTitle

truncateTitle = make_truncateTitle()


def make_sanitizeTitle():
    ogTitles = [] # used to see how many times a title repeats

    def sanitizeTitle(title, clipsDir, fileExt):
        minPathLen = len(str(clipsDir)) + len(fileExt)
        testPath = str(
            (clipsDir / (title + fileExt)).absolute()
        )

        # sanitize the title to make it as accurate as possible to the 
        # original clips' name, yet still be a valid filename
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

        # check if the current title needs to be truncated
        title = truncateTitle(title, testPath, minPathLen)

        # on windows, don't assume case sensitivity for filenames
        if sys.platform == "win32": ogTitle = title.casefold()
        else: ogTitle = title

        ogTitles.append(ogTitle)

        # check if the truncated title is repeated (since 2 different 
        # titles at the start might yield the same truncated one)
        if (nRepeats := ogTitles.count(title)) > 1:
            suffix = f"-{nRepeats}"
            print(f"\033[1;4mNote\033[0m: The title is repeated, so '{suffix}' will be added at the end")

            ogTitle = title
            title += suffix

            testPath.replace(ogTitle + ".", title + ".") # the dot guarantees its not a dir with the same name as the file
            minPathLen += len(suffix)

            # check again if it should be truncated due to the added suffix
            title = truncateTitle(title, testPath, minPathLen)

        return title
    return sanitizeTitle

sanitizeTitle = make_sanitizeTitle()


