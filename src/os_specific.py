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

