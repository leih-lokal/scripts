import os
from socket import socket
from zlib import decompress
from win32api import GetSystemMetrics
import pygame
from tqdm import tqdm
from threading import Thread
from multiprocessing import Process
from zlib import compress
import time
from mss import mss
from win32con import SW_HIDE
from win32con import SW_SHOW
from win32con import GWL_EXSTYLE 
from win32con import WS_EX_TOOLWINDOW
import numpy as np
import win32gui, win32ui
from PIL import Image

_WIDTH = GetSystemMetrics(0)
_HEIGHT = GetSystemMetrics(17)


def set_pixel(img, w, x, y, rgb=(0,0,0)):
    """
    Set a pixel in a, RGB byte array
    """
    pos = (x*w + y)*3
    if pos>=len(img):return img # avoid setting pixel outside of frame
    img[pos:pos+3] = rgb
    return img

def add_mouse(img, w):
    img = bytearray(img)
    flags, hcursor, (cx,cy) = win32gui.GetCursorInfo()
    cursor = get_cursor(hcursor)
    cursor_mean = cursor.mean(-1)
    where = np.where(cursor_mean>0)
    for x, y in zip(where[0], where[1]):
        rgb = [x for x in cursor[x,y]]
        img = set_pixel(img, w, x+cy, y+cx, rgb=rgb)
    return img


def get_cursor(hcursor):
    info = win32gui.GetCursorInfo()
    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc, 36, 36)
    hdc = hdc.CreateCompatibleDC()
    hdc.SelectObject(hbmp)
    hdc.DrawIcon((0,0), hcursor)
    
    bmpinfo = hbmp.GetInfo()
    bmpbytes = hbmp.GetBitmapBits()
    bmpstr = hbmp.GetBitmapBits(True)
    im = np.array(Image.frombuffer(
        'RGB',
         (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
         bmpstr, 'raw', 'BGRX', 0, 1))
    
    win32gui.DestroyIcon(hcursor)    
    win32gui.DeleteObject(hbmp.GetHandle())
    hdc.DeleteDC()
    return im




def check_extended_display():
    t_width, t_height = GetSystemMetrics(79), GetSystemMetrics(78)
    c_width, c_height = GetSystemMetrics(1), GetSystemMetrics(0)
    
    if t_width==c_width and c_height==t_height:
        return False
    return True
            
def hide_from_taskbar(hw):
    try:
        win32gui.ShowWindow(hw, SW_HIDE)
        win32gui.SetWindowLong(hw, GWL_EXSTYLE,win32gui.GetWindowLong(hw, GWL_EXSTYLE)| WS_EX_TOOLWINDOW);
        win32gui.ShowWindow(hw, SW_SHOW);
    except win32gui.error:
        print("Error while hiding the window")
        return None     

def recvall(conn, length):
    """ Retreive all pixels. """

    buf = b''
    while len(buf) < length:
        data = conn.recv(length - len(buf))
        if not data:
            return data
        buf += data
    return buf

def send_screenshot(conn):
    with mss() as sct:
        # The region to capture
        rect = {'top': 0, 'left': 0, 'width': _WIDTH, 'height': _HEIGHT}
        img = bytes([0x00] * _WIDTH*_HEIGHT*3)
        while 'recording':
            # Capture the screen
            title = win32gui.GetWindowText (win32gui.GetForegroundWindow())
            if not 'Bürgerstiftung Karlsruhe' in title \
                or 'WordPress' in title:
                # COMMENT THIS LINE IN TO DISPLAY A BLACK SCREEN INSTEAD
                if int(os.environ['SCREEN_BLACK']):
                    img = bytes([0x00] * _WIDTH*_HEIGHT*3)             
            else:
                # Take a new screenshot
                img = sct.grab(rect).rgb
                img = add_mouse(img, w=rect['width']) # add mouse
            pixels = compress(img, 1)
            # Send the size of the pixels length
            size = len(pixels)
            size_len = (size.bit_length() + 7) // 8
            conn.send(bytes([size_len]))

            # Send the actual pixels length
            size_bytes = size.to_bytes(size_len, 'big')
            conn.send(size_bytes)
            
            # Send pixels
            conn.sendall(pixels)
            time.sleep(float(os.environ['SLEEP_BETWEEN']))
 
      
def client(host='127.0.0.1', port=5089):
    pygame.init()
    pygame.display.set_caption('Website-Spiegel')
    hw = win32gui.FindWindow(None, 'Website-Spiegel')
    hide_from_taskbar(hw)
    custom_res = os.environ.get('SECOND_MONITOR_RESOLUTION')
    if custom_res:
        res = [int(x) for x in custom_res.split(',')]
    else:
        res = (0, 0)
    screen = pygame.display.set_mode(res)
    watching = True    

    sock = socket()
    sock.connect((host, port))
    u = tqdm(total=0)
    clock = pygame.time.Clock()
    try:
        while watching:
            u.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    watching = False
                    break
                elif event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN):
                    watching = False
                    sock.close()
                    break
            
            # Retreive the size of the pixels length, the pixels length and pixels
            size_len = int.from_bytes(sock.recv(1), byteorder='big')
            size = int.from_bytes(sock.recv(size_len), byteorder='big')
            pixels = decompress(recvall(sock, size))
            
            # Create the Surface from raw pixels
            img = pygame.image.fromstring(pixels, (_WIDTH, _HEIGHT), 'RGB')
            if custom_res:
                img = pygame.transform.scale(img, res)
            
            if any(pygame.key.get_pressed()):
                break
            pygame.event.pump()
            # Display the picture
            screen.blit(img, (0, 0))
            pygame.display.flip()
            pygame.display.update()
            clock.tick(60)


    finally:
        pygame.display.quit()
        pygame.quit()
        sock.close()

def host(host='localhost', port=5089):
    sock = socket()
    sock.bind((host, port))
    try:
        sock.listen(5)
        print('Server started.')
        conn, addr = sock.accept()
        print('Client connected IP:{}'.format(addr))
        thread = Thread(target=send_screenshot, args=(conn,))
        thread.start()
    finally:
        sock.close()


def main():
    # if not GetSystemMetrics(80)==2: # checks number of attached screens
    #     raise Exception('Second screen is not attached.')
    # if not check_extended_display():
    #     raise Exception('\nDer Bildschirm ist nicht im modus "Erweitert"".\n'\
    #                     'Bitte drücke WINDOWS + P und wähle "Erweitert".')
    
    p = Process(target=host)
    p.start()
    client()
    p.join()
    

if __name__ == '__main__':
    ## SETTINGS ##
    os.environ['SDL_VIDEO_WINDOW_POS'] = "{},0".format(GetSystemMetrics(76)) # comment to display window on primary screen
    os.environ['SCREEN_BLACK'] = '0' # change this to make the screen black instead of keeping last image
    os.environ['SLEEP_BETWEEN'] = '0.2' # change this to reduce CPU usage
    # os.environ['SECOND_MONITOR_RESOLUTION'] = '800,600'  # set this to force another resolution
    main()
    
    
    
    
    
