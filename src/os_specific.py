# this module will include the filename sanitizing and hiding the json file part of the script, which is specific to different OS's
import subprocess
import os

from sys import platform


# -file visibility-
def revealFile(filePath):
    if platform == "win32" and filePath.exists(): # Windows
        subprocess.run(["attrib", "-H", filePath], check=True) # temporarily make the file visible again so i have write permissions


def hideFile(filePath):
    if platform == "win32": 
        # hide the file to disencourage edits/deletion
        subprocess.run(["attrib", "+H", filePath], check=True)


# -filename and path restrictions-
if platform == "win32":
    MAX_FILENAME = 255
    MAX_PATH = 260 - 1 # not counting the null terminator    

else: # unix based systems
    MAX_FILENAME = os.pathconf("/", "PC_NAME_MAX")  
    MAX_PATH = os.pathconf("/", "PC_PATH_MAX")
      

def make_sanitizeTitle():
    fakeChars = { # fullwidth variants of the restricted filename charecters
        "/": "\uff0f",
        ">": "\uff1e",
        "<": "\uff1c",
        "|": "\uff5c",
        ":": "\uff1a",
        "&": "\uff06",
        "?": "\uff1f",
        "*": "\uff0a"
    }

    if platform == "win32":
        fakeChars["\\"] = "\uff3c"
        fakeChars["\""] = "\uff02"

        # names that are reserved on Windows
        win32Names = ["CON", "PRN", "AUX", "NUL"] 

        for i in range(9):
            win32Names.append((
                f"COM{i+1}", f"LPT{i+1}"
            ))

        # superscript numbers from 1 to 3
        for supN in ("\u00b9", "\u00b2", "\u00b3"): 
            win32Names.append((
                f"COM{supN}", f"LPT{supN}"
            ))

    bannedChars = fakeChars.keys()


    def sanitizeTitle(title):
        for bannedChar in bannedChars:
            if bannedChar in title:
                for _ in range(title.count(bannedChar)):
                    title = title.replace(bannedChar, fakeChars[bannedChar])

        if platform == "win32":
            if title.endswith("."):
                # add full width dot to the end
                title = title[:-1] + "\uff0e"

            elif title.endswith(" "):
                title = title.strip()

    return sanitizeTitle

sanitizeTitle = make_sanitizeTitle()
        

# check if the title is repeated
def make_checkRepeatedTitle():
    ogTitles = [] # used to see how many times a title repeats

    def checkRepeatedTitle(title):
        # on windows, don't assume case sensitivity for filenames
        if platform == "win32": ogTitle = title.casefold()
        else: ogTitle = title

        ogTitles.append(ogTitle)


        if (nRepeats := ogTitles.count(title)) > 1:
            suffix = f"-{nRepeats}"
            print(f"\033[1;4mNote\033[0m: The title is repeated, so '{suffix}' will be added at the end")

        else:
            suffix = ""

        return suffix

    return checkRepeatedTitle

checkRepeatedTitle = make_checkRepeatedTitle()

