import sys
from dataclasses import dataclass
from io import BufferedReader

BLOCK_SIZE = 4096
XMP_MAGIC_END = bytes.fromhex("01 FF FE FD FC FB FA F9 F8 F7 F6 F5 F4 F3 F2 F1 F0 EF EE ED EC \
                               EB EA E9 E8 E7 E6 E5 E4 E3 E2 E1 E0 DF DE DD DC DB DA D9 D8 D7 \
                               D6 D5 D4 D3 D2 D1 D0 CF CE CD CC CB CA C9 C8 C7 C6 C5 C4 C3 C2 \
                               C1 C0 BF BE BD BC BB BA B9 B8 B7 B6 B5 B4 B3 B2 B1 B0 AF AE AD \
                               AC AB AA A9 A8 A7 A6 A5 A4 A3 A2 A1 A0 9F 9E 9D 9C 9B 9A 99 98 \
                               97 96 95 94 93 92 91 90 8F 8E 8D 8C 8B 8A 89 88 87 86 85 84 83 \
                               82 81 80 7F 7E 7D 7C 7B 7A 79 78 77 76 75 74 73 72 71 70 6F 6E \
                               6D 6C 6B 6A 69 68 67 66 65 64 63 62 61 60 5F 5E 5D 5C 5B 5A 59 \
                               58 57 56 55 54 53 52 51 50 4F 4E 4D 4C 4B 4A 49 48 47 46 45 44 \
                               43 42 41 40 3F 3E 3D 3C 3B 3A 39 38 37 36 35 34 33 32 31 30 2F \
                               2E 2D 2C 2B 2A 29 28 27 26 25 24 23 22 21 20 1F 1E 1D 1C 1B 1A \
                               19 18 17 16 15 14 13 12 11 10 0F 0E 0D 0C 0B 0A 09 08 07 06 05 \
                               04 03 02 01 00 00")

APP_EXT_MARKER = bytes.fromhex("21 ff")
GFX_CTRL_EXT_MARKER = bytes.fromhex("21 f9")

@dataclass
class BufFile:
    file: BufferedReader
    buf: bytes
    index: int

def main():
    gif = sys.argv[1]
    out_gif = gif.replace(".gif", "-speed.gif")
    speed = sys.argv[2]
    specials = [parse_special(s) for s in sys.argv[3].split(",")] if len(sys.argv) > 3 else []

    with open(out_gif, "wb") as out:
        with open(gif, "rb") as in_file:
            file = BufFile(in_file, [], 0)
            _header = read_and_write(file, out, 6)
            _width = int.from_bytes(read_and_write(file, out, 2), byteorder="little")
            _height = int.from_bytes(read_and_write(file, out, 2), byteorder="little")
            # GCT, background color, pixel aspect ratio, global color table (skipped). 0x30D - 0x0A:
            read_and_write(file, out, 771)

            # netscape app ext
            marker = read_and_write(file, out, 2)
            if marker != APP_EXT_MARKER:
                raise Exception(f"Expected {APP_EXT_MARKER.hex(' ')} application extension marker")                
            block_len = int.from_bytes(read_and_write(file, out, 1), byteorder="little") # always 11
            netscape_app_id = read_and_write(file, out, block_len)
            read_and_write(file, out, 2) # num bytes in subblock & index of current sub block
            _num_reps = read_and_write(file, out, 2) # 0 = loop forever
            read_and_write(file, out, 1) #end of sub-block

            marker = read_and_write(file, out, 2)
            if marker == APP_EXT_MARKER:
                block_len = int.from_bytes(read_and_write(file, out, 1), byteorder="little") # always 11
                app_id = read_and_write(file, out, block_len)
                if app_id.decode("ascii") != "XMP DataXMP":
                    raise Exception(f"Unknown app id {app_id}")

                read_until(file, out, XMP_MAGIC_END)
                marker = read_and_write(file, out, 2)

            # Frames
            frame_index = 1
            while marker == GFX_CTRL_EXT_MARKER:
                special = next((sp for sp in specials if sp[0] <= frame_index <= sp[1]), None)
                frame_speed = special[2] if special else speed
                read_frame(file, out, frame_speed, frame_index)
                marker = read_and_write(file, out, 2)
                frame_index += 1

                if  marker != GFX_CTRL_EXT_MARKER and marker != bytes.fromhex("3b"):
                    raise Exception(f"Expected {GFX_CTRL_EXT_MARKER.hex(' ')} frame marker, or 3b EOF marker")

    print(f"Wrote modified GIF to {out_gif}")


def parse_special(s):
    parts = s.split(":")
    rng = parts[0].split("-")
    if len(rng) == 1:
        rng = [rng[0], rng[0]]

    return [int(rng[0]), int(rng[1]), parts[1]]

def read_frame(file, out, speed, frame_index):
    _num_bytes = read_and_write(file, out, 1)
    _reserved = read_and_write(file, out, 1)
    cur_frame_delay = int.from_bytes(read(file, 2), byteorder="little") / 100

    if speed.endswith("x"):
        frame_delay = cur_frame_delay / float(speed[:-1])
    else:
        frame_delay = float(speed)

    print(f"#{frame_index}: {cur_frame_delay} -> {frame_delay}")
    
    out.write(int(frame_delay * 100).to_bytes(2, byteorder="little"))

    _rest = read_and_write(file, out, 13)
    num_bytes = int.from_bytes(read_and_write(file, out, 1), byteorder="little")
    while num_bytes > 0:
        read_and_write(file, out, num_bytes)
        num_bytes = int.from_bytes(read_and_write(file, out, 1), byteorder="little")


def read_and_write(file, out, sz):
    data = read(file, sz)
    if data:
        out.write(data)
    return data


def read(buf_file: BufFile, sz):
    pre = bytes(buf_file.buf[buf_file.index:min(len(buf_file.buf), buf_file.index+sz)])
    if len(pre) == sz:
        buf_file.index = buf_file.index + sz
        return pre

    buf_file.buf = buf_file.file.read(BLOCK_SIZE)
    buf_file.index = 0

    if len(buf_file.buf) == 0:
        return pre
    
    return pre + read(buf_file, sz - len(pre))


def read_until(file, out, sequence):
    k = 0
    b = read_and_write(file, out, 1)
    while b:        
        if b[0] == sequence[k]:
            k += 1
        else:
            k = 0

        if k == len(sequence):
            return

        b = read_and_write(file, out, 1)


if __name__ == "__main__":
    main()
