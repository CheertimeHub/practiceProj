import pygame
import sys
import random
import os
import ctypes
from ctypes import wintypes
from PIL import Image
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage
import threading

# ตั้งค่าหน้าต่างให้อยู่บนสุดและโปร่งใส (Windows)
os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

# ตั้งค่าเริ่มต้น
pygame.init()

# ขนาดตัวละคร
CHARACTER_SIZE = 180 

# ฟังก์ชันโหลด GIF และแยก frames
def load_gif_frames(gif_path):
    """โหลด GIF และแปลงเป็น list ของ pygame surfaces"""
    frames = []
    try:
        gif = Image.open(gif_path)
        for frame_num in range(gif.n_frames):
            gif.seek(frame_num)
            # แปลงเป็น RGBA
            frame = gif.convert("RGBA")

            # ลบพื้นหลังสีม่วง (255, 0, 255) ให้เป็น transparent
            datas = frame.getdata()
            newData = []
            for item in datas:
                # ตรวจสอบสีม่วงแบบละเอียด (R และ B สูง, G ต่ำ)
                r, g, b = item[0], item[1], item[2]
                # ถ้าเป็นสีม่วง หรือสีชมพูอมม่วง
                if (r > 150 and b > 150 and g < 100) or (r == 255 and g == 0 and b == 255):
                    newData.append((255, 255, 255, 0))  # transparent
                else:
                    newData.append(item)
            frame.putdata(newData)

            # Scale ให้พอดีกับ CHARACTER_SIZE
            frame = frame.resize((CHARACTER_SIZE, CHARACTER_SIZE), Image.Resampling.LANCZOS)
            # แปลงเป็น pygame surface
            mode = frame.mode
            size = frame.size
            data = frame.tobytes()
            pygame_surface = pygame.image.fromstring(data, size, mode)
            frames.append(pygame_surface)
    except Exception as e:
        print(f"Error loading {gif_path}: {e}")
    return frames

# โหลด animations
ANIMATIONS = {
    'idle': load_gif_frames('Character/spr_idle.gif'),
    'walking': load_gif_frames('Character/spr_walking.gif'),
    'jump': load_gif_frames('Character/spr_jump.gif')
}

print(f"Loaded animations: idle={len(ANIMATIONS['idle'])} frames, walking={len(ANIMATIONS['walking'])} frames, jump={len(ANIMATIONS['jump'])} frames")

# สี (สำหรับ transparency key)
TRANSPARENT_COLOR = (255, 0, 255)  # สีม่วงจะถูกทำให้โปร่งใส
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
BLACK = (0, 0, 0)

# ได้ขนาดหน้าจอทั้งหมด (รวม multi-monitor)
import ctypes
try:
    user32 = ctypes.windll.user32
    # SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77
    # SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
    virtual_width = user32.GetSystemMetrics(78)  # Total width (all monitors)
    virtual_height = user32.GetSystemMetrics(79)  # Total height (all monitors)

    # ถ้ามี multi-monitor ใช้ virtual screen
    if virtual_width > 0 and virtual_height > 0:
        SCREEN_X = user32.GetSystemMetrics(76)  # Virtual screen left
        SCREEN_Y = user32.GetSystemMetrics(77)  # Virtual screen top
        SCREEN_WIDTH = virtual_width
        SCREEN_HEIGHT = virtual_height
    else:
        # ไม่มี multi-monitor ใช้หน้าจอหลัก
        SCREEN_X = 0
        SCREEN_Y = 0
        SCREEN_WIDTH = user32.GetSystemMetrics(0)
        SCREEN_HEIGHT = user32.GetSystemMetrics(1)

    print(f"Screen bounds: X={SCREEN_X}, Y={SCREEN_Y}, W={SCREEN_WIDTH}, H={SCREEN_HEIGHT}")
except:
    SCREEN_X = 0
    SCREEN_Y = 0
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080

# สร้างหน้าต่างแบบไม่มีกรอบ
screen = pygame.display.set_mode((CHARACTER_SIZE, CHARACTER_SIZE), pygame.NOFRAME)
pygame.display.set_caption("Desktop Pet")

# ทำให้หน้าต่างอยู่บนสุดเสมอและโปร่งใส (Windows)
try:
    hwnd = pygame.display.get_wm_info()['window']

    # ตั้งค่า WS_EX_LAYERED ก่อน
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000

    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)

    # ทำให้สีม่วงเป็นสีโปร่งใส
    # RGB to BGR for Windows
    transparent_color_bgr = (TRANSPARENT_COLOR[2] << 16) | (TRANSPARENT_COLOR[1] << 8) | TRANSPARENT_COLOR[0]
    LWA_COLORKEY = 0x00000001
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, transparent_color_bgr, 0, LWA_COLORKEY)

    # ตั้งให้อยู่บนสุด (HWND_TOPMOST = -1)
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

    # บังคับให้แสดงหน้าต่าง
    SW_SHOWNOACTIVATE = 4
    ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

    print("Transparency enabled successfully!")
except Exception as e:
    print(f"Warning: Could not set window transparency: {e}")

# ฟังก์ชันสำหรับ dynamic click-through
def set_click_through(hwnd, enabled):
    """เปิด/ปิด click-through mode"""
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000

    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enabled:
        # เปิด click-through
        new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
    else:
        # ปิด click-through
        new_style = (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT

    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

def ensure_topmost(hwnd):
    """บังคับให้หน้าต่างอยู่บนสุดโดยไม่แย่ง focus"""
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010

    ctypes.windll.user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )

def switch_to_mini_mode():
    """สลับไปโหมด Mini (หน้าต่างลอย)"""
    global screen, current_mode
    current_mode = AppMode.MINI

    # สร้างหน้าต่างใหม่ขนาดเล็ก
    screen = pygame.display.set_mode((CHARACTER_SIZE, CHARACTER_SIZE), pygame.NOFRAME)

    # ตั้งค่า transparency และ topmost
    try:
        hwnd = pygame.display.get_wm_info()['window']

        # ตั้งค่า WS_EX_LAYERED
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)

        # ทำให้สีม่วงเป็นสีโปร่งใส
        transparent_color_bgr = (TRANSPARENT_COLOR[2] << 16) | (TRANSPARENT_COLOR[1] << 8) | TRANSPARENT_COLOR[0]
        LWA_COLORKEY = 0x00000001
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, transparent_color_bgr, 0, LWA_COLORKEY)

        # ตั้งให้อยู่บนสุด
        ensure_topmost(hwnd)
    except Exception as e:
        print(f"Error setting mini mode: {e}")

def switch_to_full_mode():
    """สลับไปโหมด Full UI (หน้าต่างเต็ม)"""
    global screen, current_mode
    current_mode = AppMode.FULL

    # สร้างหน้าต่างใหม่ขนาดใหญ่
    screen = pygame.display.set_mode((FULL_UI_WIDTH, FULL_UI_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Desktop Pet - Settings")

    # ยกเลิก topmost และ transparency
    try:
        hwnd = pygame.display.get_wm_info()['window']

        # ลบ WS_EX_LAYERED และ WS_EX_TRANSPARENT
        GWL_EXSTYLE = -20
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        new_style = style & ~(WS_EX_LAYERED | WS_EX_TRANSPARENT)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

        # ลบ topmost
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    except Exception as e:
        print(f"Error setting full mode: {e}")

# ฟังก์ชันหาข้อมูลจอที่ตัวละครอยู่
def get_monitor_at_point(x, y):
    """หาข้อมูลจอที่ตำแหน่ง x, y"""
    from ctypes import Structure
    from ctypes.wintypes import RECT, DWORD

    class MONITORINFO(Structure):
        _fields_ = [
            ('cbSize', DWORD),
            ('rcMonitor', RECT),
            ('rcWork', RECT),
            ('dwFlags', DWORD)
        ]

    MonitorFromPoint = ctypes.windll.user32.MonitorFromPoint
    GetMonitorInfoW = ctypes.windll.user32.GetMonitorInfoW

    # หาจอที่มีตำแหน่งนี้
    pt = wintypes.POINT(int(x), int(y))
    hMonitor = MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST

    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)

    if GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
        # ได้ขนาดจอจริง
        monitor_left = mi.rcMonitor.left
        monitor_top = mi.rcMonitor.top
        monitor_right = mi.rcMonitor.right
        monitor_bottom = mi.rcMonitor.bottom
        monitor_width = monitor_right - monitor_left
        monitor_height = monitor_bottom - monitor_top

        return {
            'left': monitor_left,
            'top': monitor_top,
            'width': monitor_width,
            'height': monitor_height,
            'bottom': monitor_bottom
        }

    # ถ้าหาไม่เจอ ใช้จอหลัก
    primary_width = ctypes.windll.user32.GetSystemMetrics(0)
    primary_height = ctypes.windll.user32.GetSystemMetrics(1)
    return {
        'left': 0,
        'top': 0,
        'width': primary_width,
        'height': primary_height,
        'bottom': primary_height
    }

# ตัวละคร
class Character:
    def __init__(self):
        # เริ่มที่กลางจอหลัก
        primary_width = ctypes.windll.user32.GetSystemMetrics(0)
        primary_height = ctypes.windll.user32.GetSystemMetrics(1)

        # เริ่มที่กลางหน้าจอ
        self.x = primary_width // 2
        self.y = primary_height // 2
        self.ground_y = primary_height - CHARACTER_SIZE - 40  # จำตำแหน่งพื้น
        self.speed = 1.5  # ความเร็วเดินซ้าย-ขวา
        self.velocity_y = 0  # ความเร็วในแนวตั้ง (สำหรับแรงโน้มถ่วง)
        self.gravity = 1.2  # แรงโน้มถ่วง
        self.is_falling = True  # เริ่มต้นด้วยการตก
        self.color = BLUE
        self.direction = random.choice([-1, 1])  # -1 = ซ้าย, 1 = ขวา
        self.change_direction_timer = 0
        self.change_direction_interval = random.randint(120, 300)  # เปลี่ยนทิศทุก 2-5 วินาที
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Animation system
        self.current_animation = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15  # ความเร็วของ animation (ยิ่งน้อยยิ่งช้า)
        self.animation_timer = 0

        print(f"Character spawned at: x={self.x}, y={self.y} (Primary monitor: {primary_width}x{primary_height})")

    def update(self, mouse_screen_pos, mouse_pressed):
        """อัพเดทตำแหน่งตัวละคร"""
        # ถ้ากำลังลาก
        if self.is_dragging:
            if mouse_pressed:
                self.x = mouse_screen_pos[0] - self.drag_offset_x
                self.y = mouse_screen_pos[1] - self.drag_offset_y
                # จำกัดไม่ให้ออกนอกขอบจอ (รองรับ multi-monitor)
                self.x = max(SCREEN_X, min(self.x, SCREEN_X + SCREEN_WIDTH - CHARACTER_SIZE))
                self.y = max(SCREEN_Y, min(self.y, SCREEN_Y + SCREEN_HEIGHT - CHARACTER_SIZE))
                # ใช้ animation jump ตอนถูกลาก
                self.current_animation = 'jump'
            else:
                # ปล่อยแล้ว - เริ่มตก!
                self.is_dragging = False
                # หาจอที่ตัวละครอยู่ตอนนี้
                monitor = get_monitor_at_point(self.x, self.y)
                self.ground_y = monitor['bottom'] - CHARACTER_SIZE - 40
                if self.y < self.ground_y:
                    self.is_falling = True
                    self.velocity_y = 0  # เริ่มความเร็วตกจากศูนย์
            return

        # แรงโน้มถ่วง - ถ้าอยู่เหนือพื้น
        # หาจอที่ตัวละครอยู่และคำนวณพื้น
        monitor = get_monitor_at_point(self.x, self.y)
        target_ground = monitor['bottom'] - CHARACTER_SIZE - 40

        if self.is_falling or self.y < target_ground:
            self.is_falling = True
            self.ground_y = target_ground  # อัพเดทพื้นตามจอที่อยู่
            self.velocity_y += self.gravity  # เพิ่มความเร็วตก
            self.y += self.velocity_y

            # ใช้ animation jump ตอนกำลังตก
            self.current_animation = 'jump'

            # ถึงพื้นแล้ว
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.velocity_y = 0
                self.is_falling = False
                # เปลี่ยนเป็น idle เมื่อลงพื้น
                self.current_animation = 'idle'

        # เดินไปทางซ้ายหรือขวา (เฉพาะตอนอยู่บนพื้น)
        if not self.is_falling:
            self.x += self.speed * self.direction

            # ใช้ animation walking ตอนเดิน
            self.current_animation = 'walking'

            # เช็คขอบจอและเด้ง (รองรับ multi-monitor)
            if self.x <= SCREEN_X:
                self.x = SCREEN_X
                self.direction = 1
            elif self.x >= SCREEN_X + SCREEN_WIDTH - CHARACTER_SIZE:
                self.x = SCREEN_X + SCREEN_WIDTH - CHARACTER_SIZE
                self.direction = -1

            # สุ่มเปลี่ยนทิศทาง
            self.change_direction_timer += 1
            if self.change_direction_timer >= self.change_direction_interval:
                self.direction *= -1
                self.change_direction_timer = 0
                self.change_direction_interval = random.randint(120, 300)

        # อัพเดท animation frame
        self.update_animation()

    def update_animation(self):
        """อัพเดทเฟรมของ animation"""
        self.animation_timer += self.animation_speed
        if self.animation_timer >= 1:
            self.animation_timer = 0
            frames = ANIMATIONS.get(self.current_animation, [])
            if frames:
                self.frame_index = (self.frame_index + 1) % len(frames)

    def check_click(self, mouse_pos):
        """เช็คว่าคลิกที่ตัวละครหรือไม่"""
        center_x = CHARACTER_SIZE // 2
        center_y = CHARACTER_SIZE // 2
        distance = ((mouse_pos[0] - center_x) ** 2 + (mouse_pos[1] - center_y) ** 2) ** 0.5
        return distance <= CHARACTER_SIZE // 2

    def start_drag(self, mouse_screen_pos):
        """เริ่มลากตัวละคร"""
        self.is_dragging = True
        # เก็บ offset จากตำแหน่งคลิกกับมุมซ้ายบนของตัวละคร
        self.drag_offset_x = mouse_screen_pos[0] - self.x
        self.drag_offset_y = mouse_screen_pos[1] - self.y

    def get_window_position(self):
        """คืนค่าตำแหน่งหน้าต่าง"""
        return (int(self.x), int(self.y))

    def draw(self, screen):
        """วาดตัวละคร"""
        # ดึง frames จาก animation ปัจจุบัน
        frames = ANIMATIONS.get(self.current_animation, [])

        if frames and len(frames) > 0:
            # วาด frame ปัจจุบัน
            current_frame = frames[self.frame_index % len(frames)]

            # flip sprite ตามทิศทางการเดิน
            if self.direction == -1:
                current_frame = pygame.transform.flip(current_frame, True, False)

            screen.blit(current_frame, (0, 0))
        else:
            # fallback: วาดวงกลมถ้าโหลด animation ไม่ได้
            pygame.draw.circle(screen, self.color, (CHARACTER_SIZE // 2, CHARACTER_SIZE // 2), CHARACTER_SIZE // 2 - 2)

# สร้าง System Tray Icon
def create_tray_icon():
    """สร้างไอคอนในถาดระบบ"""
    # สร้างรูปไอคอน (วงกลมสีฟ้า 64x64)
    icon_image = PILImage.new('RGB', (64, 64), color=(255, 0, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(icon_image)
    draw.ellipse([8, 8, 56, 56], fill=(100, 150, 255))

    def on_quit(icon, item):
        global running
        running = False
        icon.stop()

    def on_show(icon, item):
        print("Show clicked")

    # เมนูใน system tray
    menu = (
        item('Show', on_show),
        item('Exit', on_quit)
    )

    return pystray.Icon("desktop_pet", icon_image, "Desktop Pet", menu)

# สร้างตัวละคร
player = Character()

# สร้างและเริ่ม system tray icon ใน thread แยก
tray_icon = create_tray_icon()
tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
tray_thread.start()

# ตัวแปรสำหรับ right-click menu
show_context_menu = False
context_menu_pos = (0, 0)
context_menu_items = ["Settings", "About", "Exit"]
context_menu_selected = -1

# ระบบ 2 โหมด: Mini Mode และ Full UI Mode
class AppMode:
    MINI = "mini"  # โหมดหน้าต่างลอยเล็กๆ
    FULL = "full"  # โหมด UI เต็มจอ

current_mode = AppMode.MINI
FULL_UI_WIDTH = 800
FULL_UI_HEIGHT = 700  # เพิ่มความสูงเพื่อให้พอดีกับ UI

# Game loop
clock = pygame.time.Clock()
running = True
mouse_pressed = False
topmost_check_interval = 10  # เช็ค topmost ทุก 10 frames (ประมาณ 167ms ที่ 60 FPS)
topmost_check_counter = 0  # นับ frame สำหรับบังคับ topmost

while running:
    # จัดการ events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if current_mode == AppMode.MINI:
                if event.button == 1:  # Left click
                    mouse_window_pos = pygame.mouse.get_pos()

                    # ถ้า context menu กำลังแสดง - เช็คว่าคลิกที่เมนูไหม
                    if show_context_menu:
                        # คำนวณตำแหน่งเมนู
                        menu_x = 10
                        menu_y = 10
                        menu_width = 150
                        menu_item_height = 30

                        for i, menu_item in enumerate(context_menu_items):
                            item_y = menu_y + (i * menu_item_height)
                            if (menu_x <= mouse_window_pos[0] <= menu_x + menu_width and
                                item_y <= mouse_window_pos[1] <= item_y + menu_item_height):
                                # คลิกที่เมนู
                                if menu_item == "Exit":
                                    running = False
                                elif menu_item == "Settings":
                                    switch_to_full_mode()
                                elif menu_item == "About":
                                    print("About clicked")
                        show_context_menu = False
                    elif player.check_click(mouse_window_pos):
                        # แปลงตำแหน่ง mouse จาก window เป็น screen coordinates
                        mouse_screen_x = player.x + mouse_window_pos[0]
                        mouse_screen_y = player.y + mouse_window_pos[1]
                        player.start_drag((mouse_screen_x, mouse_screen_y))
                        mouse_pressed = True
                elif event.button == 3:  # Right click
                    show_context_menu = True
                    context_menu_pos = pygame.mouse.get_pos()
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_pressed = False
        elif event.type == pygame.MOUSEMOTION:
            # ถ้า context menu แสดงอยู่ - highlight item ที่ hover
            if show_context_menu:
                mouse_pos = pygame.mouse.get_pos()
                menu_x = 10
                menu_y = 10
                menu_width = 150
                menu_item_height = 30
                context_menu_selected = -1

                for i in range(len(context_menu_items)):
                    item_y = menu_y + (i * menu_item_height)
                    if (menu_x <= mouse_pos[0] <= menu_x + menu_width and
                        item_y <= mouse_pos[1] <= item_y + menu_item_height):
                        context_menu_selected = i

    # เช็คว่า mouse อยู่บนตัวละครไหม สำหรับ dynamic click-through (เฉพาะ Mini Mode)
    if current_mode == AppMode.MINI:
        try:
            hwnd = pygame.display.get_wm_info()['window']
            mouse_screen_pos = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(mouse_screen_pos))

            # แปลง screen coordinates เป็น window coordinates
            window_pos = player.get_window_position()
            mouse_window_x = mouse_screen_pos.x - window_pos[0]
            mouse_window_y = mouse_screen_pos.y - window_pos[1]

            # เช็คว่า mouse อยู่ในหน้าต่างและบนตัวละครหรือไม่
            if (0 <= mouse_window_x < CHARACTER_SIZE and 0 <= mouse_window_y < CHARACTER_SIZE):
                # mouse อยู่ในหน้าต่าง - เช็คว่าอยู่บนตัวละครจริงๆไหม
                if player.check_click((mouse_window_x, mouse_window_y)) or show_context_menu:
                    # mouse อยู่บนตัวละครหรือ context menu - ปิด click-through
                    set_click_through(hwnd, False)
                else:
                    # mouse อยู่บนพื้นหลังโปร่งใส - เปิด click-through
                    set_click_through(hwnd, True)
            else:
                # mouse อยู่นอกหน้าต่าง - เปิด click-through
                set_click_through(hwnd, True)
        except:
            pass

    # ============= โหมด MINI =============
    if current_mode == AppMode.MINI:
        # อัพเดทตัวละคร
        if player.is_dragging and mouse_pressed:
            # ได้ตำแหน่ง mouse บนหน้าจอจริงๆ (สำหรับการลาก)
            mouse_screen_pos = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(mouse_screen_pos))
            player.update((mouse_screen_pos.x, mouse_screen_pos.y), True)
        else:
            # เดินตามปกติ
            player.update((0, 0), False)

        # เลื่อนหน้าต่างตามตัวละคร
        window_pos = player.get_window_position()

        # ย้ายหน้าต่างไปตามตำแหน่งตัวละคร (ทุก frame)
        try:
            hwnd = pygame.display.get_wm_info()['window']

            # ย้ายหน้าต่างก่อน
            ctypes.windll.user32.MoveWindow(
                hwnd,
                window_pos[0],
                window_pos[1],
                CHARACTER_SIZE,
                CHARACTER_SIZE,
                False
            )

            # บังคับให้อยู่บนสุดเสมอ แบบ Mini Cozy Room (เช็คทุก interval)
            topmost_check_counter += 1
            if topmost_check_counter >= topmost_check_interval:
                topmost_check_counter = 0
                ensure_topmost(hwnd)
        except Exception as e:
            pass

        # วาดทุกอย่าง (Mini Mode)
        screen.fill(TRANSPARENT_COLOR)  # พื้นหลังโปร่งใส
        player.draw(screen)

        # วาด context menu ถ้าแสดงอยู่
        if show_context_menu:
            menu_x = 10
            menu_y = 10
            menu_width = 150
            menu_item_height = 30
            menu_height = len(context_menu_items) * menu_item_height

            # พื้นหลังเมนู
            menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
            menu_surface.fill((50, 50, 50, 230))  # สีเทาเข้มโปร่งใส
            pygame.draw.rect(menu_surface, (100, 100, 100), (0, 0, menu_width, menu_height), 2)

            # วาดแต่ละ item
            font = pygame.font.Font(None, 24)
            for i, menu_item in enumerate(context_menu_items):
                item_y = i * menu_item_height

                # ถ้า hover - highlight
                if i == context_menu_selected:
                    pygame.draw.rect(menu_surface, (80, 120, 200, 200), (2, item_y + 2, menu_width - 4, menu_item_height - 4))

                # ข้อความ
                text_color = (255, 255, 255) if i == context_menu_selected else (200, 200, 200)
                text = font.render(menu_item, True, text_color)
                text_rect = text.get_rect(center=(menu_width // 2, item_y + menu_item_height // 2))
                menu_surface.blit(text, text_rect)

            screen.blit(menu_surface, (menu_x, menu_y))

    # ============= โหมด FULL UI =============
    elif current_mode == AppMode.FULL:
        # อัพเดท animation ของตัวละคร
        player.update_animation()

        # พื้นหลัง
        screen.fill((245, 235, 220))  # สีครีมอ่อน

        # === ส่วนบนสุด: Title Bar ===
        pygame.draw.rect(screen, (255, 255, 255), (0, 0, FULL_UI_WIDTH, 60))
        title_font = pygame.font.Font(None, 36)
        title_text = title_font.render("Mini Cozy Room : Lo-Fi", True, (60, 60, 60))
        screen.blit(title_text, (20, 18))

        # ปุ่ม minimize, maximize, close (ขวาบน)
        close_btn_x = FULL_UI_WIDTH - 40
        pygame.draw.circle(screen, (220, 220, 220), (close_btn_x, 30), 12)

        # === พื้นที่แสดงตัวละคร (กลางจอ) ===
        room_y = 80
        room_height = 380

        # วาดพื้นหลังห้อง (สีเขียวอ่อนๆ เหมือนมีต้นไม้)
        pygame.draw.rect(screen, (230, 240, 230), (0, room_y, FULL_UI_WIDTH, room_height))

        # แสดงตัวละครตรงกลาง
        char_preview_size = 280
        frames = ANIMATIONS.get('idle', [])
        if frames:
            preview_frame = frames[player.frame_index % len(frames)]
            scaled_frame = pygame.transform.scale(preview_frame, (char_preview_size, char_preview_size))
            char_x = (FULL_UI_WIDTH - char_preview_size) // 2
            char_y = room_y + (room_height - char_preview_size) // 2 + 20
            screen.blit(scaled_frame, (char_x, char_y))

        # === เมนูหลัก (Decor, Activity, Pet, Wardrobe) ===
        menu_y = 470
        menu_items = [
            ("Decor", "\u2302"),      # house icon
            ("Activity", "\u25b6"),   # play icon
            ("Pet", "\u263a"),        # smile icon
            ("Wardrobe", "\u2663")    # club icon
        ]

        menu_item_width = FULL_UI_WIDTH // 4
        mouse_pos = pygame.mouse.get_pos()

        for i, (label, icon) in enumerate(menu_items):
            x = i * menu_item_width
            # เช็ค hover
            is_hover = (x <= mouse_pos[0] < x + menu_item_width and
                       menu_y <= mouse_pos[1] < menu_y + 60)

            # สีพื้นหลัง
            bg_color = (60, 60, 60) if is_hover else (50, 50, 50)
            pygame.draw.rect(screen, bg_color, (x, menu_y, menu_item_width, 60))
            pygame.draw.rect(screen, (80, 80, 80), (x, menu_y, menu_item_width, 60), 1)

            # ไอคอน
            icon_font = pygame.font.Font(None, 40)
            icon_text = icon_font.render(icon, True, (200, 200, 200))
            icon_rect = icon_text.get_rect(center=(x + menu_item_width // 2, menu_y + 20))
            screen.blit(icon_text, icon_rect)

            # ชื่อเมนู
            label_font = pygame.font.Font(None, 20)
            label_text = label_font.render(label, True, (180, 180, 180))
            label_rect = label_text.get_rect(center=(x + menu_item_width // 2, menu_y + 45))
            screen.blit(label_text, label_rect)

        # === Music Player (Lo-Fi Player) ===
        player_y = 535
        player_height = 90
        pygame.draw.rect(screen, (40, 40, 40), (40, player_y, FULL_UI_WIDTH - 80, player_height), border_radius=10)

        # ชื่อเพลง
        song_font = pygame.font.Font(None, 24)
        song_text = song_font.render("Lo-Fi", True, (255, 255, 255))
        screen.blit(song_text, (60, player_y + 10))

        # ปุ่มควบคุมเพลง
        control_y = player_y + 40
        controls = [
            ("\u23ea", 150),  # previous
            ("\u23ef", 220),  # pause/play
            ("\u23e9", 290),  # next
        ]

        for symbol, x in controls:
            btn_hover = ((x - 20) <= mouse_pos[0] <= (x + 20) and
                        (control_y - 15) <= mouse_pos[1] <= (control_y + 15))
            color = (255, 255, 255) if btn_hover else (180, 180, 180)

            ctrl_font = pygame.font.Font(None, 32)
            ctrl_text = ctrl_font.render(symbol, True, color)
            ctrl_rect = ctrl_text.get_rect(center=(x, control_y))
            screen.blit(ctrl_text, ctrl_rect)

        # ปุ่ม ALBUM และ AMBIENT
        album_x = FULL_UI_WIDTH - 250
        pygame.draw.rect(screen, (60, 60, 60), (album_x, control_y - 15, 80, 30), border_radius=5)
        album_font = pygame.font.Font(None, 18)
        album_text = album_font.render("ALBUM", True, (220, 220, 220))
        screen.blit(album_text, (album_x + 12, control_y - 8))

        ambient_x = album_x + 100
        pygame.draw.rect(screen, (60, 60, 60), (ambient_x, control_y - 15, 90, 30), border_radius=5)
        ambient_text = album_font.render("AMBIENT", True, (220, 220, 220))
        screen.blit(ambient_text, (ambient_x + 8, control_y - 8))

        # === ปุ่มด้านล่าง (MEMO, TO-DO, TIMER) ===
        bottom_y = 635
        bottom_btns = [
            ("MEMO", "\u270e", 100),
            ("TO-DO", "\u2713", 300),
            ("TIMER", "\u23f0", 500)
        ]

        for label, icon, x in bottom_btns:
            btn_hover = ((x - 40) <= mouse_pos[0] <= (x + 40) and
                        (bottom_y - 25) <= mouse_pos[1] <= (bottom_y + 25))

            # วงกลมพื้นหลัง
            circle_color = (90, 90, 90) if btn_hover else (70, 70, 70)
            pygame.draw.circle(screen, circle_color, (x, bottom_y - 5), 28)

            # ไอคอน
            icon_font = pygame.font.Font(None, 32)
            icon_text = icon_font.render(icon, True, (220, 220, 220))
            icon_rect = icon_text.get_rect(center=(x, bottom_y - 10))
            screen.blit(icon_text, icon_rect)

            # ชื่อ
            label_font = pygame.font.Font(None, 18)
            label_text = label_font.render(label, True, (100, 100, 100))
            label_rect = label_text.get_rect(center=(x, bottom_y + 25))
            screen.blit(label_text, label_rect)

        # ปุ่ม Mini Mode (มุมขวาล่าง เล็กๆ)
        mini_btn_x = FULL_UI_WIDTH - 120
        mini_btn_y = bottom_y - 5
        mini_hover = ((mini_btn_x - 50) <= mouse_pos[0] <= (mini_btn_x + 50) and
                     (mini_btn_y - 20) <= mouse_pos[1] <= (mini_btn_y + 20))

        mini_color = (100, 150, 255) if mini_hover else (80, 120, 200)
        pygame.draw.rect(screen, mini_color, (mini_btn_x - 50, mini_btn_y - 20, 100, 40), border_radius=8)

        mini_font = pygame.font.Font(None, 22)
        mini_text = mini_font.render("Mini Mode", True, (255, 255, 255))
        mini_rect = mini_text.get_rect(center=(mini_btn_x, mini_btn_y))
        screen.blit(mini_text, mini_rect)

        # เช็คคลิกปุ่ม Mini Mode
        for event in pygame.event.get(pygame.MOUSEBUTTONDOWN):
            if event.button == 1 and mini_hover:
                switch_to_mini_mode()

    # อัพเดทหน้าจอ
    pygame.display.flip()
    clock.tick(60)  # 60 FPS

# ปิดเกม
tray_icon.stop()
pygame.quit()
sys.exit()
