import os
from pathlib import Path
import serial
import sys
import time

# Works with the HP2225A printer & AR488 GPIB driver
# input text

# page width = 80 cols (80 characters per line)
# page height = 66 lines (default)
# Text length = 60 lines (default)
# Feed page
# Buffer size 1024 bytes

# Configure GPIB switches of printer as such:
# | SW 1 | SW 2 | SW 3 | SW 4 | SW 5 | SW 6 | SW 7 |
# | SRQ  | LSN  | A5   | A4   | A3   | A2   | A1   |
# | 1    | 0    | 0    | 0    | 0    | 0    | 1    |
# SRQ EN  = Service request enable (true) --asserts srq line if
#       self test failed
#       out of paper
#       carriage motion disabled
# SRQ will never be asserted if Listen Always is set
# LSN = Listen Always (false) -- also listen if address is not correct

os.chdir(Path(__file__).parent)

# Global variable used to store which GPIB is under control currently
currentGPIB = None

class ResourceManager():
    GPIBcom = None
    readTimeout = None

    def __init__(self, comport, readTimeout=10, serialBaud=2400, serialTimeout=1):
        global GPIBcom
        try:
            GPIBcom = serial.Serial(comport, baudrate=serialBaud, timeout=serialTimeout )
            # GPIBcom.write(("++read_tmo_ms " + str(readTimeout) + "\n").encode())
        except serial.SerialException:
            print("Cannot connect to Serial port. Port already in use")
            sys.exit(1)

    def close(self):
        GPIBcom.close()
        
    class open_resource():
        # This address is the instance's address
        resourceAddress = None

        def selectAddress(self, address):
            global currentGPIB
            # GPIBcom.write(("++addr " + str(address) + "\n").encode())
            currentGPIB = address

        def __init__(self, address):
            self.resourceAddress = address
            self.selectAddress(address)

        def write(self, data: bytes):
            if(currentGPIB != self.resourceAddress):
                self.selectAddress(self.resourceAddress)
            if type(data) != bytes:
                data = data.encode('ascii')
            # every ESC (\x1b) character needs to be escaped for AR488 driver
            data = data.replace(b'\x1b', b'\x1b\x1b')
            # carriage return needs to be escaped
            data = data.replace(b'\r', b'\x1b\r')
            # newline to print needs to be escaped
            data = data.replace(b'\n', b'\x1b\n')
            # newline is needed to indicate end-command
            GPIBcom.write(data + b"\n")
            print(data)

        def read(self):
            # GPIBcom.write(b"++read eoi\n")
            data = GPIBcom.readline().decode('ascii').rstrip()
            return(data)

        def query(self, data):
            self.write(data)
            data = self.read()
            return(data)


def setup_printer_defaults():
    # \x1b is ESC
    # ESC &k0G = execute CR, LF and FF as sent (seperately)
    # ESC &k1W = Bidirectional printing
    # ESC Z = Display functions off
    # ESC &s0C = enable auto wrap-around at end of line
    # page length, page width
    return "\x1b&k0G\x1b&k1W\x1bZ\x1b&s0C"
    

def pitch(text, level):
    if level < 0 or level > 3:
        raise ValueError("level out of range")      
    return f"\x1b&k{level}S{text}\x1b&k0S"
def bold(text):
    return f"\x0e{text}\x0f"

def underline(text):
    return f"\x1b&dD{text}\x1b&d@"
		
if __name__ == '__main__':
    GPIB = ResourceManager("COM10")

    # Creates a path to use GPIB address 1
    inst1 = GPIB.open_resource(1)
    time.sleep(2)
    inst1.write(setup_printer_defaults())
    inst1.write(f"here is more text to print, i want to see the end of the line happen \ndo not dissapoint nog meer zin, nog meer zin, nog meer zin\rnog een stukje")
    # query serial poll, get the status of the remote device
    # bit   |value  | meaning
    # ------+-------+--------------
    # 7     | 128   | Self test failed (MSB)
    # 6     | 64    | Always 0
    # 5     | 32    | Out of Paper
    # 4     | 16    | Always 0
    # 3     | 8     | Buffer Full
    # 2     | 4     | Buffer Empty
    # 1     | 2     | Always 0
    # 0     | 1     | Carriage Motion Disabled

    print(inst1.query("++spoll"))
    time.sleep(5)
    print(inst1.query("++spoll"))
    # print(inst1.read())# Gets Identifcation of GPIB 1 and GPIB 2
    
    # print horizontal lines, low density graphics 640)
    val = b"\x1b*r640S\x1b*rA"
    for i in range(0,55):
        val += b"\x1b*b5W"
        for i in range(0,5):
            val+= b"\x88"
    val += b"\x1b*rB"
    inst1.write("\r")
    # 565 bytes long
    inst1.write(val)
    # with open("local.txt", 'rb') as f:
    #     contents = f.read()
    #     inst1.write(contents)
