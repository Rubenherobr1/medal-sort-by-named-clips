# escape codes for text formatting in the terminal
BOLD_UNDER = "\033[1;4m"
BOLD = "\033[1m"
RESET = "\033[0m"


# -decoding related-
class UnknownStrTypeError(Exception): pass

class DecodedStrs(str): # custom str class that can have attributes
    def __new__(cls, obj, pos):
        return super().__new__(cls, obj)

    def __init__(self, obj, pos):
        self.pos = pos


def normBin(decimalByte):
    byte = bin(decimalByte).replace("0b", "")
    byte = "0" * (8 - len(byte)) + byte # ensures the representation will have 8 bytes regardless

    return byte


def decodeStrType(metadata, strIDPos):
    strID = normBin(metadata[strIDPos])
    sizeID = int(strID[:4], 2)
    
    str8, str16 = int("C", 16), int("D", 16)
    unknownStrType = int("E", 16)

    skipSlash = True
    escapedTxt = ""


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
        raise UnknownStrTypeError(f"String type identified by '{sizeID:x}' is unknown")

    # the length of the str is the 1st nibble of the strID byte
    else:
        if sizeID == 0:
            return None
        
        strLen = sizeID
        strPos = strIDPos + 1

    txt = metadata[strPos : strPos + strLen].decode()

    for char in txt:
        if char == "\\" and skipSlash:
            skipSlash = False # if its another \
            continue
        else:
            skipSlash = True # reset value

        escapedTxt += char

    return DecodedStrs(escapedTxt, strPos)


