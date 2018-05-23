
'''
Modification from BmpImagePlugin.py, pillow project

Change: 'RGBA' requires a different header, v3+
'''

from PIL.BmpImagePlugin import Image, ImageFile, o32, o16, o8

import struct

def bitmask( start, stop ):
    return(((1 << stop) - 1) >> start) << start

BITMAPINFOHEADER = 40
BITMAPINFOV4HEADER = 108



SAVE = {
    "1": ("1", 1, 2),
    "L": ("L", 8, 256),
    "P": ("P", 8, 256),
    "RGB": ("BGR", 24, 0),
    "RGBA": ("BGRA", 32, 0),
}


def _save(im, fp, filename):
    try:
        rawmode, bits, colors = SAVE[im.mode]
    except KeyError:
        raise IOError("cannot write mode %s as BMP" % im.mode)

    info = im.encoderinfo

    dpi = info.get("dpi", (96, 96))

    # 1 meter == 39.3701 inches
    ppm = tuple(map(lambda x: int(x * 39.3701), dpi))

    stride = ((im.size[0]*bits+7)//8+3) & (~3)
    if rawmode == "BGRA":
        header = BITMAPINFOV4HEADER # for v4 header
        compression = 3 # BI_BITFIELDS
    else:
        header = BITMAPINFOHEADER  # or 64 for OS/2 version 2
        compression = 0 # uncompressed

    offset = 14 + header + colors * 4
    image = stride * im.size[1]

    # bitmap header
    fp.write(b"BM" +                      # file type (magic)
             o32(offset+image) +          # file size
             o32(0) +                     # reserved
             o32(offset))                 # image data offset

    # bitmap info header
    fp.write(o32(header) +                # info header size
             o32(im.size[0]) +            # width
             o32(im.size[1]) +            # height
             o16(1) +                     # planes
             o16(bits) +                  # depth
             o32(compression) +           # compression (0=uncompressed)
             o32(image) +                 # size of bitmap
             o32(ppm[0]) + o32(ppm[1]) +  # resolution
             o32(colors) +                # colors used
             o32(colors))                 # colors important
    if header >= BITMAPINFOV4HEADER:
        fp.write(o32(bitmask(16,24)) +    # red channel bit mask
                 o32(bitmask(8, 16)) +    # green channel bit mask
                 o32(bitmask(0, 8)) +     # blue channel bit mask
                 o32(bitmask(24,32)) +    # alpha channel bit mask
                 "sRGB"[::-1])            # LCS windows color space

    # Pad remaining header(unused color space info)
    padding = offset - fp.tell()
    fp.write(b"\0" * (padding))
    

    if im.mode == "1":
        for i in (0, 255):
            fp.write(o8(i) * 4)
    elif im.mode == "L":
        for i in range(256):
            fp.write(o8(i) * 4)
    elif im.mode == "P":
        fp.write(im.im.getpalette("RGB", "BGRX"))

    ImageFile._save(im, fp, [("raw", (0, 0)+im.size, 0,
                    (rawmode, stride, -1))])
