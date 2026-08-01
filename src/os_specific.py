# this module will include the filename sanitizing and hiding the json file part of the script, which is specific to different OS's
import subprocess

from sys import platform


# -file visibility-
def revealFile(filePath):
    if platform == "win32" and filePath.exists():
        # temporarily make the file visible again so i have write permissions
        subprocess.run(["attrib", "-H", filePath], check=True) 


def hideFile(filePath):
    if platform == "win32": 
        # hide the file to disencourage edits/deletion
        subprocess.run(["attrib", "+H", filePath], check=True)


