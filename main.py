import pygame
import sys
import random
import os
import ctypes
from ctypes import wintypes

# ตั้งค่าหน้าต่างให้อยู่บนสุดและโปร่งใส (Windows)
os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

# ตั้งค่าเริ่มต้น
pygame.init()

# ขนาดตัวละคร
CHARACTER_SIZE = 60

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

            # ถึงพื้นแล้ว
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.velocity_y = 0
                self.is_falling = False

        # เดินไปทางซ้ายหรือขวา (เฉพาะตอนอยู่บนพื้น)
        if not self.is_falling:
            self.x += self.speed * self.direction

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
        # วาดตัวตัวละคร - วงกลมสีน้ำเงิน
        pygame.draw.circle(screen, self.color, (CHARACTER_SIZE // 2, CHARACTER_SIZE // 2), CHARACTER_SIZE // 2 - 2)

        # วาดหน้าตา
        # ตา
        eye_y = CHARACTER_SIZE // 2 - 5
        pygame.draw.circle(screen, WHITE, (CHARACTER_SIZE // 2 - 10, eye_y), 5)
        pygame.draw.circle(screen, WHITE, (CHARACTER_SIZE // 2 + 10, eye_y), 5)
        pygame.draw.circle(screen, BLACK, (CHARACTER_SIZE // 2 - 10, eye_y), 3)
        pygame.draw.circle(screen, BLACK, (CHARACTER_SIZE // 2 + 10, eye_y), 3)

        # ปาก
        mouth_rect = pygame.Rect(CHARACTER_SIZE // 2 - 10, CHARACTER_SIZE // 2 + 5, 20, 10)
        pygame.draw.arc(screen, BLACK, mouth_rect, 3.14, 0, 2)

# สร้างตัวละคร
player = Character()

# Game loop
clock = pygame.time.Clock()
running = True
mouse_pressed = False

while running:
    # จัดการ events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_window_pos = pygame.mouse.get_pos()
                if player.check_click(mouse_window_pos):
                    # แปลงตำแหน่ง mouse จาก window เป็น screen coordinates
                    mouse_screen_x = player.x + mouse_window_pos[0]
                    mouse_screen_y = player.y + mouse_window_pos[1]
                    player.start_drag((mouse_screen_x, mouse_screen_y))
                    mouse_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_pressed = False

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

        # ใช้ MoveWindow เพื่อความเร็วในการย้าย
        ctypes.windll.user32.MoveWindow(hwnd, window_pos[0], window_pos[1],
                                         CHARACTER_SIZE, CHARACTER_SIZE, False)

        # บังคับให้อยู่บนสุดเสมอโดยไม่ activate
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010

        ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    except Exception as e:
        pass

    # วาดทุกอย่าง
    screen.fill(TRANSPARENT_COLOR)  # พื้นหลังโปร่งใส
    player.draw(screen)

    # อัพเดทหน้าจอ
    pygame.display.flip()
    clock.tick(60)  # 60 FPS

# ปิดเกม
pygame.quit()
sys.exit()
