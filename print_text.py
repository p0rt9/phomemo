'''Print text and QR code to phomenu D30 Printer'''
import os
import click
import serial
from wand.image import Image
from wand.font import Font
from wand.drawing import Drawing
import PIL.Image
import qrcode
import image_helper

def check_mutually_exclusive(ctx, param, value):
    """Test to ensure options are mutally exclusive"""
    # List of mutually exclusive options
    options = ['qr', 'wrap', 'flag']
    # Check which options are provided
    provided_options = [opt for opt in options if ctx.params.get(opt)]
    # Raise an error if more than one option is provided
    if len(provided_options) > 1:
        raise click.UsageError(f"Only one of {', '.join('--' + opt for opt in options)}" +
                                " can be used at a time.")
    return value

@click.command()
@click.argument('text')
@click.option('--font', default="Helvetica", help='Path to TTF font file')
@click.option('--qr', default="", callback=check_mutually_exclusive, help='QR Code Data')
@click.option('--wrap', is_flag=True, callback=check_mutually_exclusive, help='Create a cable wrap')
@click.option('--flag', is_flag=True, callback=check_mutually_exclusive, help='Create a cable wrap')



def main(text, font, qr, wrap, flag):
    '''Main process to print image'''
    try:
        port = serial.Serial("/dev/rfcomm1", timeout=10)
    except Exception:
        print("unable to connect to rfcomm: Try running 'rfcomm connect 1 C4:1E:5E:37:5F:EE'")

    if qr:
        generate_qr(qr)
    if flag:
        filename = generate_flag(text, font, "temp.png")
    elif wrap:
        filename = generate_wrap(text, font, "temp.png")
    else:
        filename = generate_image(text, font, "temp.png", qr)
    header(port)
    print_image(port, filename)
    os.remove(filename)
    if qr:
        os.remove('qr.png')


def header(port):
    '''printer initialization sniffed from Android app "Print Master"'''
    packets = [
        '1f1138',
        '1f11121f1113',
        '1f1109',
        '1f1111',
        '1f1119',
        '1f1107',
        '1f110a1f110202'
    ]

    for packet in packets:
        port.write(bytes.fromhex(packet))
        port.flush()

def generate_qr(qr):
    '''Make QR Code if flag is present'''
    qr_img=qrcode.make(qr)
    big_qr_img = qr_img.resize((88,88))
    big_qr_img.save('qr.png')

def generate_flag(text, font, filename):
    '''Generate PNG of a file flag'''
    font = Font(path=font)
    width, height = 135, 88
    with Image(width=width, height=height, background="white") as img:
        # center text, fill canvas
        img.caption(text, font=font, gravity="center")
        # extent and rotate image
        img.background_color = "white"
        img.gravity = "center"
        with Image(width=300, height=88, background="white") as combined:
            combined.background_color = "white"
            combined.composite(img, left=0, top=0)
            combined.composite(img, left=165, top=0)
            with Drawing() as draw:
                draw.stroke_width = 2
                draw.line((150, 0), (150, 88))
                draw(combined)
            combined.extent(width=320, height=96, gravity="center")
            combined.rotate(270)
            combined.save(filename=filename)
    return filename

def generate_wrap(text, font, filename):
    """generate a PNG of a wire wrap"""
    font = Font(path=font)
    width, height = 88, 288
    text += "\n"
    with Image(width=width, height=height, background="white") as img:
        img.caption(text*10, font=font, gravity="north", height=1000)
        img.extent(width=96, height=320, gravity ="center")
        img.save(filename=filename)
    return filename

def generate_image(text, font, filename, qr):
    '''Generate PNG of print image'''
    font = Font(path=font)
    width, height = 288, 88
    if qr:
        width = 200
        
    with Image(width=width, height=height, background="white") as img:
        # center text, fill canvas
        img.caption(text, font=font, gravity="center")

        # extent and rotate image
        img.background_color = "white"
        img.gravity = "center"
        #if qr add images together.
        if qr:
            with Image(filename="qr.png") as qr_img:
                with Image(width=288, height=88, background="white") as combined:
                    combined.composite(qr_img, left=0, top=0)
                    combined.composite(img, left=88, top=0)
                    combined.gravity = "center"
                    combined.extent(width=320, height=96, gravity="center")
                    combined.rotate(270)
                    combined.save(filename=filename)
        else:
            img.extent(width=320, height=96, gravity ="center")
            img.rotate(270)
            img.save(filename=filename)
    return filename


def print_image(port, filename):
    '''Slice Image and send to printer'''
    width = 96

    with PIL.Image.open(filename) as src:
        image = image_helper.preprocess_image(src, width)

    # printer initialization sniffed from Android app "Print Master"
    output = '1f1124001b401d7630000c004001'

    # adapted from https://github.com/theacodes/phomemo_m02s/blob/main/phomemo_m02s/printer.py
    for chunk in image_helper.split_image(image):
        output = bytearray.fromhex(output)

        bits = image_helper.image_to_bits(chunk)
        for line in bits:
            for byte_num in range(width // 8):
                byte = 0
                for bit in range(8):
                    pixel = line[byte_num * 8 + bit]
                    byte |= (pixel & 0x01) << (7 - bit)
                output.append(byte)

        port.write(output)
        port.flush()

        output = ''


if __name__ == '__main__':
    main()
