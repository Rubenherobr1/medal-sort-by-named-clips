import sqlite3 as sqlite
from pathlib import Path


# the function below is based off of the MessagePack specification (MessagePack is the encoding used in the clip metadata)
# https://github.com/msgpack/msgpack/blob/master/spec.md#str-format-family

class Format:
    #size of the first identifier byte when the value of a key is a string
    fixstr = int("10111111", 2) #in this case, it's the max value that the first byte can have
    str8 = int("d9", 16)
    str16 = int("da", 16)
    str32 = int("db", 16)


def decodeStr(bTitle: bytes):
    firstByte = bTitle[0]

    match(firstByte):
        case Format.str8: newTitle = bTitle[2:]
        case Format.str16: newTitle = bTitle[3:]
        case Format.str32: newTitle = bTitle[5:]

        case _:
            if firstByte <= Format.fixstr:
                newTitle = bTitle[1:]
            else:
                print(f"The first identifier byte dosen't have a valid value ({firstByte}).")

    return str(newTitle)


unnamedCount = namedCount = 0
medalPath = Path(Path().home(), "AppData", "Roaming", "Medal") 

for path in medalPath.iterdir():
    if path.suffix == ".db":
        nIndex = len("medal-") #yields the index that's right after the hyphen, which includes only numbers
        
        if path.stem[nIndex].isnumeric(): #ignores medal-guest.db and CustomGameDatabase.db
            dbPath = medalPath / path.name
            print(f"Path to database: {dbPath}")
            
            break


#connect to sqlite database and get the video id, it's path and it's metadata
db = sqlite.connect(dbPath) 
resultSet = db.execute("SELECT local_content_id, video_path, metadata FROM contents")

print("Connected to database and executed query.")


for id, path, metadata in resultSet: 
    #define bounds where the title for the video is in
    lowerBound = metadata.index(b"title") + len("title") #byte that's after the title key

    '''
    The hex code that appears when "clipDuration" is used as a clip name 
    is "\xc7\x0c". it will be repeated twice, if that is the case, since
    there is also a key that's named "clipDuration", but i cannot allow
    it since i use that key for my upper bound.
    '''

    if metadata.count(b"\xc7\x0cclipDuration") > 1: #
        raise NotImplementedError("Do not name your clips 'clipDuration'. Alternatively, open an issue on github and this error will be adressed.")

    upperBound = metadata.index(b"\xc7\x0cclipDuration")
    bTitle = metadata[lowerBound : upperBound]

    '''
    The hex code that appears inbetween the title and clipDuration keys
    when a clip does not have a name is "\x07".
    '''

    if bTitle == b"\x07":
        unnamedCount += 1
        continue
    else: 
        namedCount += 1
    
    title = decodeStr(bTitle)
    
    #print(f"{title}\n")


'''
TODO:
- Maybe save the clips to an album on Medal. If i cant do that, copy them to a folder.
- Look at the MessagePack specification for the part behind the title. Its the same.
'''


