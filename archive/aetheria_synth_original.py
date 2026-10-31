"""
====================================================================================================
PROJECT: AETHERIA GRAND PRIX — SULAM 2026 NEO-SYMPHONIC EXHIBITION MASTERPIECE
ROLE: PRINCIPAL GAME ARCHITECT & 3D GRAPHICS/AUDIO SYSTEMS ENGINEER (AAA PRODUCTION SPEC)
PART 1 / 3: CORE 3D PERSPECTIVE ENGINE, ADVANCED SHADOW & AMBIENT OCCLUSION PIPELINE,
            BEVELED GLASSMORPHIC 3D UI SUITE, ASYNC VISION TRACKER & PROCEDURAL AUDIO DSP
====================================================================================================
"""

import cv2
import numpy as np
import pygame
import math
import sys
import os
import threading
import time
import socket
import json
import random
import urllib.request
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
from collections import deque

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# ==================================================================================================
# 1. CORE ENGINE CONFIGURATION & DISPLAY CONSTANTS
# ==================================================================================================
WIDTH, HEIGHT = 1280, 720
TARGET_FPS = 60
SAMPLE_RATE = 22050
AUDIO_CHANNELS = 2
AUDIO_BUFFER = 512
UDP_PORT = 37020

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
GESTURE_PINCH_THRESHOLD_NEAR = 42.0
GESTURE_PINCH_THRESHOLD_FAR = 62.0
GESTURE_FIST_CURL_RATIO = 1.15
ONE_EURO_MIN_CUTOFF = 0.8
ONE_EURO_BETA = 0.03
ONE_EURO_D_CUTOFF = 1.0

# 3D Depth & Perspective Projection Constants
PERSPECTIVE_FOV = 65.0
VANISHING_POINT_X = WIDTH // 2
VANISHING_POINT_Y = 140
CAMERA_ELEVATION = 280.0
ROAD_Z_START = 80.0
ROAD_Z_END = 950.0

# ==================================================================================================
# 2. NEO-SYMPHONIC 3D DESIGN SYSTEM & COLOR HIERARCHY
# ==================================================================================================
class UITheme:
    # Deep Sci-Fi Void & Substrates
    VOID_BLACK       = (3, 5, 8)
    VOID_DEEP        = (6, 10, 18)
    VOID_SURFACE     = (10, 16, 28)
    VOID_ELEVATED    = (15, 22, 38)
    
    # Layered 3D Glass & Beveled Plates (SRCALPHA RGBA)
    GLASS_SURF       = (12, 18, 32, 215)
    GLASS_SURF_HI    = (20, 30, 52, 240)
    GLASS_SURF_LOW   = (8, 12, 22, 185)
    GLASS_BORDER     = (38, 58, 96, 175)
    GLASS_BORDER_HI  = (80, 140, 240, 235)
    GLASS_HIGHLIGHT  = (255, 255, 255, 140)
    GLASS_BEVEL_LIGHT= (160, 210, 255, 120)
    GLASS_BEVEL_DARK = (4, 6, 12, 190)

    # Ambient Occlusion & Volumetric Drop Shadow Layers
    SHADOW_CORE      = (0, 0, 0, 190)
    SHADOW_MID       = (0, 0, 0, 110)
    SHADOW_SOFT      = (0, 0, 0, 45)
    SHADOW_AMBIENT   = (2, 4, 8, 80)
    
    # Semantic Neon Energy Accents
    NEON_CYAN        = (0, 242, 255)      # Tech, Spatial Lasers, Air Triggers
    NEON_PURPLE      = (170, 70, 255)     # Magic, Singularity, AI Resonators
    NEON_PINK        = (255, 42, 135)     # Percussion, Slasher Right Blade
    NEON_GREEN       = (30, 250, 145)     # High Precision, Perfect Hits, Vitality
    NEON_GOLD        = (255, 212, 50)     # Soloists, S+ Ranks, Wall of Fame
    NEON_ORANGE      = (255, 135, 30)     # Slasher Left Blade, Brass, Warnings
    NEON_BLUE        = (40, 120, 255)     # Secondary Tech & Defensive Shields
    
    # Text & Standard Primaries
    PURE_WHITE       = (248, 250, 255)    # Cues, Direct Focus, Primary Text
    TEXT_MUTED       = (135, 155, 190)    # Subtitles, Tech Metadata, Inactive
    TEXT_DARK        = (15, 20, 30)       # High-contrast Dark Labels
    
    # Premium Concert Stage Lighting
    STAGE_WOOD       = (195, 115, 30)
    STAGE_WOOD_DARK  = (135, 70, 16)
    STAGE_BACKDROP   = (22, 12, 12)
    CHOIR_ROBE       = (125, 22, 48)
    CHOIR_GOLD       = (245, 200, 75)

FINGERTIP_IDS = [4, 8, 12, 16, 20]
FINGER_COLORS = [
    UITheme.NEON_GREEN,
    UITheme.NEON_CYAN,
    UITheme.NEON_PURPLE,
    UITheme.NEON_GOLD,
    UITheme.NEON_PINK
]

# ==================================================================================================
# 3. 3D VECTOR MATH, CAMERA PROJECTION & PERSPECTIVE TRANSFORM
# ==================================================================================================
class Vector3D:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def set(self, x, y, z):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def add(self, v):
        return Vector3D(self.x + v.x, self.y + v.y, self.z + v.z)

    def sub(self, v):
        return Vector3D(self.x - v.x, self.y - v.y, self.z - v.z)

    def mult(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def div(self, scalar):
        return Vector3D(self.x / scalar if scalar != 0 else 0,
                        self.y / scalar if scalar != 0 else 0,
                        self.z / scalar if scalar != 0 else 0)

    def magnitude(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def to_tuple(self):
        return (self.x, self.y, self.z)

class Perspective3D:
    """
    High-performance 3D perspective projection pipeline.
    Translates world coordinates (X_world, Y_world, Z_depth) onto the 2D viewport.
    """
    @staticmethod
    def project(world_x, world_y, world_z, vp_x=VANISHING_POINT_X, vp_y=VANISHING_POINT_Y, fov=480.0):
        clamped_z = max(1.0, float(world_z))
        scale = fov / clamped_z
        screen_x = vp_x + (world_x * scale)
        screen_y = vp_y + (world_y * scale)
        return int(screen_x), int(screen_y), scale

    @staticmethod
    def project_quad(quad_pts, vp_x=VANISHING_POINT_X, vp_y=VANISHING_POINT_Y, fov=480.0):
        projected = []
        scales = []
        for x, y, z in quad_pts:
            px, py, sc = Perspective3D.project(x, y, z, vp_x, vp_y, fov)
            projected.append((px, py))
            scales.append(sc)
        return projected, (sum(scales) / max(1, len(scales)))

class Vector2D:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def set(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def add(self, v):
        return Vector2D(self.x + v.x, self.y + v.y)

    def sub(self, v):
        return Vector2D(self.x - v.x, self.y - v.y)

    def mult(self, scalar):
        return Vector2D(self.x * scalar, self.y * scalar)

    def div(self, scalar):
        return Vector2D(self.x / scalar if scalar != 0 else 0, self.y / scalar if scalar != 0 else 0)

    def magnitude(self):
        return math.hypot(self.x, self.y)

    def normalize(self):
        mag = self.magnitude()
        if mag > 1e-5:
            return self.div(mag)
        return Vector2D(0, 0)

    def distance_to(self, v):
        return math.hypot(self.x - v.x, self.y - v.y)

    def to_tuple(self):
        return (int(self.x), int(self.y))

class Easing:
    @staticmethod
    def ease_out_cubic(t):
        t = np.clip(t, 0.0, 1.0)
        return 1.0 - math.pow(1.0 - t, 3)

    @staticmethod
    def ease_in_cubic(t):
        t = np.clip(t, 0.0, 1.0)
        return t * t * t

    @staticmethod
    def ease_out_back(t, s=1.70158):
        t = np.clip(t, 0.0, 1.0)
        return 1.0 + (s + 1.0) * math.pow(t - 1.0, 3) + s * math.pow(t - 1.0, 2)

    @staticmethod
    def ease_in_out_quad(t):
        t = np.clip(t, 0.0, 1.0)
        return 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2

    @staticmethod
    def ease_out_elastic(t):
        t = np.clip(t, 0.0, 1.0)
        if t == 0: return 0.0
        if t == 1: return 1.0
        p = 0.3
        return math.pow(2, -10 * t) * math.sin((t - p / 4.0) * (2.0 * math.pi) / p) + 1.0

    @staticmethod
    def lerp(a, b, t):
        return a + (b - a) * np.clip(t, 0.0, 1.0)

    @staticmethod
    def lerp_color(c1, c2, t):
        t = np.clip(t, 0.0, 1.0)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        if len(c1) == 4 and len(c2) == 4:
            a = int(c1[3] + (c2[3] - c1[3]) * t)
            return (r, g, b, a)
        return (r, g, b)

# ==================================================================================================
# 4. ADVANCED 3D SHADOW & AMBIENT OCCLUSION PIPELINE
# ==================================================================================================
class ShadowEngine:
    """
    Industrial-grade multi-tier soft drop shadow and ambient occlusion generator.
    Caches calculated shadow blits to maintain consistent 60 FPS performance.
    """
    _shadow_cache = {}

    @classmethod
    def get_soft_shadow(cls, width, height, radius=18, elevation=12, blur_passes=3):
        key = (int(width), int(height), int(radius), int(elevation), int(blur_passes))
        if key in cls._shadow_cache:
            return cls._shadow_cache[key]

        pad = elevation * 3 + 16
        surf_w = width + pad * 2
        surf_h = height + pad * 2
        shadow_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # Multi-stage radial falloff simulation for realistic penumbra
        layers = [
            (elevation * 2.2, 38, pad + 12),
            (elevation * 1.5, 65, pad + 8),
            (elevation * 0.9, 105, pad + 4),
            (elevation * 0.4, 160, pad + 1)
        ]

        for offset_y, alpha, spread in layers:
            s_rect = pygame.Rect(
                pad - spread // 2,
                pad + int(offset_y) - spread // 4,
                width + spread,
                height + spread // 2
            )
            pygame.draw.rect(shadow_surf, (0, 2, 6, alpha), s_rect, border_radius=radius + spread // 3)

        cls._shadow_cache[key] = (shadow_surf, pad)
        return shadow_surf, pad

    @classmethod
    def blit_drop_shadow(cls, target_surf, dest_rect, radius=18, elevation=14):
        shadow_surf, pad = cls.get_soft_shadow(dest_rect.width, dest_rect.height, radius, elevation)
        target_surf.blit(
            shadow_surf,
            (dest_rect.x - pad, dest_rect.y - pad),
            special_flags=pygame.BLEND_ALPHA_SDL2
        )

    @classmethod
    def draw_projected_ground_shadow(cls, surf, center_x, center_y, width, height, alpha=140):
        """Draws a perspectively foreshortened ground ellipse shadow under floating objects."""
        s = pygame.Surface((width * 2, height * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, alpha), (width // 2, height // 2, width, height))
        pygame.draw.ellipse(s, (0, 0, 0, int(alpha * 0.45)), (width // 2 - 6, height // 2 - 4, width + 12, height + 8))
        surf.blit(s, (center_x - width, center_y - height), special_flags=pygame.BLEND_ALPHA_SDL2)

# ==================================================================================================
# 5. BEVELED 3D GLASS UI & TACTILE SHOCKWAVE VISUAL FX
# ==================================================================================================
class NeonFX:
    _glow_cache = {}

    @classmethod
    def draw_glow_circle(cls, surf, color, center, radius, glow_size=20, max_alpha=160):
        key = (color[:3], int(radius), int(glow_size), int(max_alpha))
        if key not in cls._glow_cache:
            size = int((radius + glow_size) * 2)
            glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            steps = 6
            for i in range(steps):
                cur_r = radius + glow_size * ((steps - i) / steps)
                alpha = int(max_alpha * ((i + 1) / (steps + 1)) * 0.40)
                pygame.draw.circle(glow_surf, (*color[:3], alpha), (c, c), int(cur_r))
            pygame.draw.circle(glow_surf, (*color[:3], max_alpha), (c, c), int(radius))
            cls._glow_cache[key] = glow_surf

        cached = cls._glow_cache[key]
        surf.blit(
            cached,
            (center[0] - cached.get_width() // 2, center[1] - cached.get_height() // 2),
            special_flags=pygame.BLEND_ALPHA_SDL2
        )

    @classmethod
    def draw_cyber_brackets(cls, surf, rect, color, bracket_len=16, thickness=2):
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        col = (*color[:3], 230) if len(color) == 3 else color
        # Top-Left
        pygame.draw.line(surf, col, (x, y), (x + bracket_len, y), thickness)
        pygame.draw.line(surf, col, (x, y), (x, y + bracket_len), thickness)
        # Top-Right
        pygame.draw.line(surf, col, (x + w, y), (x + w - bracket_len, y), thickness)
        pygame.draw.line(surf, col, (x + w, y), (x + w, y + bracket_len), thickness)
        # Bottom-Left
        pygame.draw.line(surf, col, (x, y + h), (x + bracket_len, y + h), thickness)
        pygame.draw.line(surf, col, (x, y + h), (x, y + h - bracket_len), thickness)
        # Bottom-Right
        pygame.draw.line(surf, col, (x + w, y + h), (x + w - bracket_len, y + h), thickness)
        pygame.draw.line(surf, col, (x + w, y + h), (x + w, y + h - bracket_len), thickness)

    @classmethod
    def draw_glass_card(cls, surf, rect, border_color=UITheme.NEON_CYAN, border_width=2, radius=18,
                        show_brackets=True, high_lum=False, elevation=14, is_3d=True):
        """
        Renders a fully dimensional 3D glassmorphic panel with soft multi-tier cast shadow,
        specular light rim on top edge, and dark depth bevel on bottom edge.
        """
        # Step 1: Cast realistic soft ground/backdrop drop shadow
        if elevation > 0:
            ShadowEngine.blit_drop_shadow(surf, rect, radius=radius, elevation=elevation)

        # Step 2: Render 3D side depth plate if 3D relief is activated
        if is_3d:
            depth_h = min(8, elevation // 2 + 3)
            extruded_rect = pygame.Rect(rect.x, rect.y + depth_h, rect.width, rect.height)
            plate_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(plate_surf, (6, 10, 18, 230), (0, 0, rect.width, rect.height), border_radius=radius)
            surf.blit(plate_surf, extruded_rect.topleft)

        # Step 3: Glass surface body
        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        base_bg = UITheme.GLASS_SURF_HI if high_lum else UITheme.GLASS_SURF
        pygame.draw.rect(card_surf, base_bg, (0, 0, rect.width, rect.height), border_radius=radius)
        pygame.draw.rect(card_surf, (*border_color[:3], 180), (0, 0, rect.width, rect.height), border_width, border_radius=radius)
        
        # Step 4: 3D Top Specular Light Highlight & Inner Ambient Chamfer
        pygame.draw.line(card_surf, UITheme.GLASS_HIGHLIGHT, (radius, 2), (rect.width - radius, 2), 2)
        pygame.draw.line(card_surf, UITheme.GLASS_BEVEL_LIGHT, (2, radius), (2, rect.height - radius), 1)

        # Step 5: Bottom Inner Dark Bevel (Ambient Occlusion)
        pygame.draw.line(card_surf, UITheme.GLASS_BEVEL_DARK, (radius, rect.height - 2), (rect.width - radius, rect.height - 2), 2)
        pygame.draw.line(card_surf, UITheme.GLASS_BEVEL_DARK, (rect.width - 2, radius), (rect.width - 2, rect.height - radius), 2)

        surf.blit(card_surf, rect.topleft)

        if show_brackets:
            cls.draw_cyber_brackets(surf, rect.inflate(8, 8), border_color, bracket_len=14, thickness=2)

    @classmethod
    def draw_hud_pill(cls, surf, rect, border_color=UITheme.GLASS_BORDER, fill_color=UITheme.GLASS_SURF, radius=12, elevation=8):
        """Pill-shaped 3D badge with drop shadow and specular rim."""
        if elevation > 0:
            ShadowEngine.blit_drop_shadow(surf, rect, radius=radius, elevation=elevation)

        pill_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(pill_surf, fill_color, (0, 0, rect.width, rect.height), border_radius=radius)
        pygame.draw.rect(pill_surf, (*border_color[:3], 200), (0, 0, rect.width, rect.height), 1, border_radius=radius)
        
        # 3D Emissive Top Glint
        pygame.draw.line(pill_surf, UITheme.GLASS_HIGHLIGHT, (radius, 1), (rect.width - radius, 1), 1)
        # 3D Bottom Occlusion
        pygame.draw.line(pill_surf, UITheme.GLASS_BEVEL_DARK, (radius, rect.height - 1), (rect.width - radius, rect.height - 1), 1)
        
        surf.blit(pill_surf, rect.topleft)

    @classmethod
    def draw_glowing_ring(cls, surf, color, center, radius, width=3, glow_alpha=120):
        r_int = int(radius)
        size = (r_int + 20) * 2
        ring_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        
        for i in range(3):
            w_extra = (3 - i) * 2
            a = int(glow_alpha * ((i + 1) / 4.0))
            pygame.draw.circle(ring_surf, (*color[:3], a), (c, c), r_int, width + w_extra)
        
        pygame.draw.circle(ring_surf, (*color[:3], 240), (c, c), r_int, width)
        surf.blit(ring_surf, (center[0] - c, center[1] - c), special_flags=pygame.BLEND_ALPHA_SDL2)

def draw_star(surf, col, x, y, size):
    pts = []
    for i in range(10):
        a = i * math.pi / 5 - math.pi / 2
        r = size if i % 2 == 0 else size * 0.44
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    pygame.draw.polygon(surf, col, pts)

def draw_heart(surf, col, x, y, size):
    # 3D Drop Shadow for hearts
    s_col = (0, 0, 0, 130)
    pygame.draw.circle(surf, s_col, (x - size // 2, y + 2), size // 2)
    pygame.draw.circle(surf, s_col, (x + size // 2, y + 2), size // 2)
    pygame.draw.polygon(surf, s_col, [(x - size, y + size // 4 + 2), (x + size, y + size // 4 + 2), (x, y + int(size * 1.35) + 2)])

    pygame.draw.circle(surf, col, (x - size // 2, y), size // 2)
    pygame.draw.circle(surf, col, (x + size // 2, y), size // 2)
    pygame.draw.polygon(surf, col, [(x - size, y + size // 4), (x + size, y + size // 4), (x, y + int(size * 1.35))])
    # 3D Specular highlight dot
    pygame.draw.circle(surf, UITheme.PURE_WHITE, (x - size // 2 - 1, y - 2), max(1, size // 5))

def draw_ribbon(surf, font, text, x, y, w, h, col, txt_col=UITheme.PURE_WHITE):
    rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
    
    # 3D Cast Shadow
    ShadowEngine.blit_drop_shadow(surf, rect, radius=12, elevation=14)

    r_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(r_surf, (*col[:3], 215), (0, 0, w, h), border_radius=12)
    pygame.draw.rect(r_surf, UITheme.PURE_WHITE, (0, 0, w, h), 2, border_radius=12)
    pygame.draw.line(r_surf, UITheme.GLASS_HIGHLIGHT, (12, 2), (w - 12, 2), 2)
    pygame.draw.line(r_surf, UITheme.GLASS_BEVEL_DARK, (12, h - 2), (w - 12, h - 2), 2)
    surf.blit(r_surf, rect.topleft)

    NeonFX.draw_cyber_brackets(surf, rect.inflate(6, 6), col, bracket_len=10, thickness=2)

    # 3D Text Shadow
    t_shadow = font.render(text, True, (0, 0, 0))
    surf.blit(t_shadow, (x - t_shadow.get_width() // 2 + 2, y - t_shadow.get_height() // 2 + 2))
    t = font.render(text, True, txt_col)
    surf.blit(t, (x - t.get_width() // 2, y - t.get_height() // 2))

# ==================================================================================================
# 6. HIGH-PRECISION MOTION FILTERING (ONE-EURO & KALMAN SIGNAL PROCESSORS)
# ==================================================================================================
class OneEuroFilter:
    """
    1-Euro Filter for jitter removal on high-speed hand landmarks and 3D ray targets.
    Dynamically balances smoothness during static holds and responsiveness during rapid slashes.
    """
    def __init__(self, t0, x0, dx0=0.0, min_cutoff=ONE_EURO_MIN_CUTOFF, beta=ONE_EURO_BETA, d_cutoff=ONE_EURO_D_CUTOFF):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)
        self.t_prev = float(t0)

    def __call__(self, t, x):
        dt = max(1e-4, t - self.t_prev)
        a_d = self._alpha(dt, self.d_cutoff)
        dx = (x - self.x_prev) / dt
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(dt, cutoff)
        x_hat = a * x + (1.0 - a) * self.x_prev
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat

    def _alpha(self, dt, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

class AdaptiveSmoothFilter:
    def __init__(self, alpha=0.35):
        self.alpha = alpha
        self.val = None

    def update(self, v):
        if self.val is None:
            self.val = v
        else:
            self.val = self.val * (1.0 - self.alpha) + v * self.alpha
        return self.val

    def reset(self):
        self.val = None

# ==================================================================================================
# 7. ASYNC VISION ENGINE WITH 3D DEPTH RAYCASTING & EXTENDED 1-2M REACH
# ==================================================================================================
class AsyncVisionTracker:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        # Drop frame queue delay
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._ensure_model()

        # VIDEO mode keeps track of hand landmarks across frames without full re-detection
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path="hand_landmarker.task"),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.45,
            min_hand_presence_confidence=0.45,
            min_tracking_confidence=0.45
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.filters = {}
        self.latest_hands = []
        self.running = True
        self.last_timestamp_ms = 0
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _ensure_model(self):
        if not os.path.exists("hand_landmarker.task"):
            print("[VISION 3D] Downloading hand_landmarker.task neural asset...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, "hand_landmarker.task")
            print("[VISION 3D] Download complete.")

    def _worker(self):
        while self.running:
            success, frame = self.cap.read()
            if not success:
                time.sleep(0.002)
                continue

            frame = cv2.flip(frame, 1)

            # Downsample to 320x240 for 4x faster neural inference (normalized coordinates scale back cleanly)
            small_frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_LINEAR)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_small)

            # Strictly monotonic millisecond timestamp required for detect_for_video
            now_ms = int(time.time() * 1000)
            if now_ms <= self.last_timestamp_ms:
                now_ms = self.last_timestamp_ms + 1
            self.last_timestamp_ms = now_ms

            try:
                res = self.detector.detect_for_video(mp_image, now_ms)
            except Exception:
                continue

            current_t = time.time()
            hands_data = []

            if res.hand_landmarks:
                # Sort hands left-to-right by wrist X to lock filter slots and stop cross-hand jitter
                sorted_landmarks = sorted(res.hand_landmarks, key=lambda hl: hl[0].x)

                for h_idx, hl in enumerate(sorted_landmarks):
                    filtered_landmarks = []
                    for j_idx, pt in enumerate(hl):
                        raw_x = pt.x * WIDTH
                        raw_y = pt.y * HEIGHT
                        fx_key = (h_idx, j_idx, 'x')
                        fy_key = (h_idx, j_idx, 'y')
                        if fx_key not in self.filters:
                            # Higher beta (0.08) snaps instantaneously to high-speed finger taps without lag
                            self.filters[fx_key] = OneEuroFilter(current_t, raw_x, min_cutoff=1.5, beta=0.08)
                            self.filters[fy_key] = OneEuroFilter(current_t, raw_y, min_cutoff=1.5, beta=0.08)

                        filtered_landmarks.append((
                            int(self.filters[fx_key](current_t, raw_x)),
                            int(self.filters[fy_key](current_t, raw_y))
                        ))

                    wrist = filtered_landmarks[0]
                    index_mcp = filtered_landmarks[5]
                    pinky_mcp = filtered_landmarks[17]

                    # 3D Distance Estimation via Hand Span in Pixels
                    hand_span = math.hypot(pinky_mcp[0] - index_mcp[0], pinky_mcp[1] - index_mcp[1])
                    is_distant = hand_span < 68.0

                    v1 = (index_mcp[0] - wrist[0], index_mcp[1] - wrist[1])
                    v2 = (pinky_mcp[0] - wrist[0], pinky_mcp[1] - wrist[1])
                    cross_product = (v1[0] * v2[1]) - (v1[1] * v2[0])
                    is_left = cross_product < 0

                    curled_fingers = 0
                    for tip_i, pip_i in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                        d_tip = math.hypot(filtered_landmarks[tip_i][0] - wrist[0], filtered_landmarks[tip_i][1] - wrist[1])
                        d_pip = math.hypot(filtered_landmarks[pip_i][0] - wrist[0], filtered_landmarks[pip_i][1] - wrist[1])
                        if d_tip < (d_pip * GESTURE_FIST_CURL_RATIO):
                            curled_fingers += 1

                    is_fist = (curled_fingers >= 3)
                    pinch_gap = math.hypot(filtered_landmarks[4][0] - filtered_landmarks[8][0],
                                           filtered_landmarks[4][1] - filtered_landmarks[8][1])
                    is_pinching = pinch_gap < (GESTURE_PINCH_THRESHOLD_FAR if is_distant else GESTURE_PINCH_THRESHOLD_NEAR)

                    # Spatial Forward Projection Beam Vector
                    tip_x, tip_y = filtered_landmarks[8]
                    pip_x, pip_y = filtered_landmarks[6]
                    beam_dx = tip_x - pip_x
                    beam_dy = tip_y - pip_y
                    beam_len = math.hypot(beam_dx, beam_dy)
                    if beam_len > 1e-3:
                        beam_target = (int(tip_x + (beam_dx / beam_len) * 115),
                                       int(tip_y + (beam_dy / beam_len) * 115))
                    else:
                        beam_target = (tip_x, tip_y)

                    hands_data.append({
                        "is_left": is_left,
                        "is_fist": is_fist,
                        "is_pinching": is_pinching,
                        "is_distant": is_distant,
                        "hand_span": hand_span,
                        "palm": filtered_landmarks[9],
                        "wrist": wrist,
                        "lead_tip": filtered_landmarks[8],
                        "beam_target": beam_target,
                        "all_tips": [filtered_landmarks[idx] for idx in FINGERTIP_IDS],
                        "landmarks": filtered_landmarks
                    })

            with self.lock:
                self.latest_hands = hands_data

    def get_hands(self):
        with self.lock:
            return list(self.latest_hands)

    def release(self):
        self.running = False
        self.cap.release()

# ==================================================================================================
# 8. PROCEDURAL ACOUSTIC, CHORAL & SYNTHESIZED DSP ENGINE
# ==================================================================================================
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=AUDIO_CHANNELS, buffer=AUDIO_BUFFER)
pygame.mixer.set_num_channels(32)

CHAN_STRINGS_L = pygame.mixer.Channel(0)
CHAN_STRINGS_H = pygame.mixer.Channel(1)
CHAN_WOODWINDS = pygame.mixer.Channel(2)
CHAN_BRASS     = pygame.mixer.Channel(3)
CHAN_TIMPANI   = pygame.mixer.Channel(4)
CHAN_TUTTI     = pygame.mixer.Channel(5)
CHAN_CHOIR     = pygame.mixer.Channel(6)

class AudioDSP:
    @staticmethod
    def _create_spatial_stereo(buf_1d, pan=0.0, gain=1.0):
        buf = np.clip(buf_1d * gain, -1.0, 1.0)
        pan = np.clip(pan, -1.0, 1.0)
        angle = (pan + 1.0) * (np.pi / 4.0)
        l_chan = (buf * np.cos(angle) * 32767.0 * 0.88).astype(np.int16)
        r_chan = (buf * np.sin(angle) * 32767.0 * 0.88).astype(np.int16)
        return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack((l_chan, r_chan))))

    @classmethod
    def synth_piano(cls, freq, pan=0.0):
        dur = 1.8
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        p = 2.0 * np.pi * freq * t
        buf = 0.55 * np.sin(p) + 0.28 * np.sin(p * 2.002) + 0.15 * np.sin(p * 3.008)
        env = np.exp(-t * 2.4) + (np.exp(-t * 36.0) * np.random.uniform(-0.2, 0.2, len(t)))
        return cls._create_spatial_stereo(buf * env, pan=pan)

    @classmethod
    def synth_synth_blade(cls, freq, pan=0.0):
        dur = 0.70
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        saw = 2.0 * ((freq * t) % 1.0) - 1.0
        square = np.sign(np.sin(2.0 * np.pi * freq * 1.5 * t)) * 0.35
        noise = np.random.uniform(-0.25, 0.25, len(t)) * np.exp(-t * 20.0)
        return cls._create_spatial_stereo((saw * 0.55 + square + noise) * np.exp(-t * 4.0), pan=pan, gain=1.2)

    @classmethod
    def synth_trumpet(cls, freq, pan=0.2):
        dur = 1.8
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        p = 2.0 * np.pi * freq * t
        buf = (0.50 * np.sin(p) + 0.32 * np.sin(p * 2.0) + 0.22 * np.sin(p * 3.0)) * (1.0 + np.sin(2.0 * np.pi * 6.0 * t) * 0.04)
        return cls._create_spatial_stereo(buf * np.exp(-t * 1.6), pan=pan, gain=1.2)

    @classmethod
    def synth_saxophone(cls, freq, pan=-0.2):
        dur = 2.0
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        p = 2.0 * np.pi * freq * t
        square = np.sign(np.sin(p)) * 0.45 + np.sin(p * 2.0) * 0.25
        return cls._create_spatial_stereo(square * np.exp(-t * 1.3), pan=pan, gain=1.1)

    @classmethod
    def synth_harp(cls, freq, pan=0.0):
        dur = 2.4
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        p = 2.0 * np.pi * freq * t
        buf = (np.sin(p) * 0.70 + np.sin(p * 2.001) * 0.25) * np.exp(-t * 2.0)
        return cls._create_spatial_stereo(buf, pan=pan, gain=1.15)

    @classmethod
    def synth_guitar(cls, freq, pan=0.0):
        dur = 1.8
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        tri = 2.0 * np.abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0
        return cls._create_spatial_stereo(tri * np.exp(-t * 3.0), pan=pan, gain=1.1)

    @classmethod
    def synth_viola(cls, freq, pan=-0.3):
        dur = 2.2
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        saw = 2.0 * ((freq * t) % 1.0) - 1.0
        return cls._create_spatial_stereo(saw * (1.0 + np.sin(2.0 * np.pi * 5.5 * t) * 0.08) * np.exp(-t * 1.4), pan=pan, gain=1.0)

    @classmethod
    def synth_drum(cls, d_type):
        dur = 0.45
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        if d_type == "KICK":
            buf = np.sin(2.0 * np.pi * np.cumsum(190.0 * np.exp(-t * 38.0) + 38.0) / SAMPLE_RATE) * np.exp(-t * 8.0)
        elif d_type == "BOMB":
            buf = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 4.5) + np.sin(2.0 * np.pi * 60.0 * t) * np.exp(-t * 3.5)
        else:
            buf = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 26.0)
        return cls._create_spatial_stereo(buf)

    @classmethod
    def synth_grand_tutti(cls):
        dur = 3.6
        n = int(dur * SAMPLE_RATE)
        t = np.linspace(0, dur, n, False)
        chord = [65.41, 130.81, 196.00, 261.63, 329.63, 392.00, 523.25]
        buf = np.zeros(n)
        for idx, f in enumerate(chord):
            buf += (np.sin(2.0 * np.pi * f * t) * 0.5 + (2.0 * ((f * t) % 1.0) - 1.0) * 0.25) * (1.0 / (idx + 1.1))
        crash = np.random.uniform(-0.35, 0.35, n) * np.exp(-t * 3.6)
        timp = np.sin(2.0 * np.pi * (110.0 * np.exp(-t * 12.0) + 45.0) * t) * np.exp(-t * 3.0) * 0.8
        return cls._create_spatial_stereo((buf * np.exp(-t * 1.1)) + crash + timp, pan=0.0, gain=1.4)

    @classmethod
    def synth_choir_ensemble(cls, chord_freqs, pan=0.0):
        dur = 4.8
        n = int(dur * SAMPLE_RATE)
        t = np.linspace(0, dur, n, False)
        buf = np.zeros(n)
        for f in chord_freqs:
            vib = np.sin(2.0 * np.pi * 5.2 * t) * 0.015
            f_inst = f * (1.0 + vib)
            phase = 2.0 * np.pi * np.cumsum(f_inst) / SAMPLE_RATE
            buf += (np.sin(phase) * 0.55 + np.sin(phase * 2.0) * 0.28)
        buf = buf / len(chord_freqs)
        att = int(SAMPLE_RATE * 0.45)
        buf[:att] *= np.linspace(0.0, 1.0, att)
        buf[-att:] *= np.linspace(1.0, 0.0, att)
        return cls._create_spatial_stereo(buf, pan=pan, gain=1.35)

    @classmethod
    def synth_strings_ensemble(cls, chord_freqs, pan=-0.5):
        dur = 4.5
        n = int(dur * SAMPLE_RATE)
        t = np.linspace(0, dur, n, False)
        buf = np.zeros(n)
        for f in chord_freqs:
            saw = 2.0 * ((f * t) % 1.0) - 1.0
            buf += saw * 0.6
        buf = buf / len(chord_freqs)
        att = int(SAMPLE_RATE * 0.25)
        buf[:att] *= np.linspace(0.0, 1.0, att)
        buf[-att:] *= np.linspace(1.0, 0.0, att)
        return cls._create_spatial_stereo(buf, pan=pan, gain=1.2)

    @classmethod
    def synth_woodwinds_ensemble(cls, chord_freqs, pan=0.0):
        dur = 4.5
        n = int(dur * SAMPLE_RATE)
        t = np.linspace(0, dur, n, False)
        buf = np.zeros(n)
        for f in chord_freqs:
            buf += np.sin(2.0 * np.pi * f * t) * 0.75
        buf = buf / len(chord_freqs)
        att = int(SAMPLE_RATE * 0.18)
        buf[:att] *= np.linspace(0.0, 1.0, att)
        buf[-att:] *= np.linspace(1.0, 0.0, att)
        return cls._create_spatial_stereo(buf, pan=pan, gain=1.0)

    @classmethod
    def synth_brass_fanfare(cls, chord_freqs, pan=0.6):
        dur = 4.5
        n = int(dur * SAMPLE_RATE)
        t = np.linspace(0, dur, n, False)
        buf = np.zeros(n)
        for f in chord_freqs:
            p = 2.0 * np.pi * f * t
            buf += 0.5 * np.sin(p) + 0.35 * np.sin(p * 2.0)
        buf = buf / len(chord_freqs)
        att = int(SAMPLE_RATE * 0.12)
        buf[:att] *= np.linspace(0.0, 1.0, att)
        buf[-att:] *= np.linspace(1.0, 0.0, att)
        return cls._create_spatial_stereo(buf, pan=pan, gain=1.35)

    @classmethod
    def synth_timpani_roll(cls):
        dur = 2.2
        n = int(dur * SAMPLE_RATE)
        t = np.linspace(0, dur, n, False)
        f_sweep = 120.0 * np.exp(-t * 14.0) + 48.0
        membrane = np.sin(2.0 * np.pi * np.cumsum(f_sweep) / SAMPLE_RATE) * np.exp(-t * 2.4)
        strike = np.sin(2.0 * np.pi * 92.0 * t) * np.exp(-t * 18.0) * 0.6
        return cls._create_spatial_stereo(membrane + strike, pan=0.65, gain=1.5)

    @classmethod
    def synth_gong(cls):
        dur = 3.0
        t = np.linspace(0, dur, int(dur * SAMPLE_RATE), False)
        phase = 2.0 * np.pi * 55.0 * t + 3.2 * np.sin(2.0 * np.pi * 11.0 * t)
        return cls._create_spatial_stereo(np.sin(phase) * np.exp(-t * 1.4), gain=1.2)

dsp = AudioDSP()

PIANO_FREQS = [130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94, 261.63, 293.66, 329.63, 349.23, 392.00]
PIANO_BLACK_FREQS = [138.59, 155.56, None, 185.00, 207.65, 233.08, None, 277.18, 311.13, None, 369.99]
TRUMPET_FREQS = [233.08, 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 523.25]
SAX_FREQS = [196.00, 220.00, 246.94, 261.63, 293.66, 329.63, 392.00, 440.00]
HARP_FREQS = [130.81, 164.81, 196.00, 220.00, 261.63, 329.63, 392.00, 523.25]
GUITAR_FREQS = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63, 392.00, 440.00]
VIOLA_FREQS = [130.81, 164.81, 196.00, 220.00, 261.63, 329.63, 392.00, 440.00]
SLASHER_FREQS = [146.83, 196.00, 220.00, 293.66, 392.00, 440.00, 587.33, 659.25]

PIANO_WHITE_BANK = [dsp.synth_piano(f) for f in PIANO_FREQS]
PIANO_BLACK_BANK = [dsp.synth_piano(f) if f else None for f in PIANO_BLACK_FREQS]
TRUMPET_BANK = [dsp.synth_trumpet(f) for f in TRUMPET_FREQS]
SAX_BANK = [dsp.synth_saxophone(f) for f in SAX_FREQS]
HARP_BANK = [dsp.synth_harp(f) for f in HARP_FREQS]
GUITAR_BANK = [dsp.synth_guitar(f) for f in GUITAR_FREQS]
VIOLA_BANK = [dsp.synth_viola(f) for f in VIOLA_FREQS]
SLASHER_BANK = [dsp.synth_synth_blade(f) for f in SLASHER_FREQS]
DRUM_BANK = {
    "KICK": dsp.synth_drum("KICK"),
    "SNARE": dsp.synth_drum("SNARE"),
    "HIHAT": dsp.synth_drum("HIHAT"),
    "BOMB": dsp.synth_drum("BOMB")
}

SOUND_STRINGS_LOW = dsp.synth_strings_ensemble([65.41, 98.00, 130.81, 164.81, 196.00], pan=-0.6)
SOUND_STRINGS_HIGH = dsp.synth_strings_ensemble([261.63, 329.63, 392.00, 523.25, 659.25], pan=-0.4)
SOUND_WOODWINDS = dsp.synth_woodwinds_ensemble([196.00, 261.63, 329.63, 392.00, 523.25], pan=0.0)
SOUND_BRASS = dsp.synth_brass_fanfare([98.00, 130.81, 196.00, 261.63, 329.63], pan=0.6)
SOUND_TIMPANI = dsp.synth_timpani_roll()
SOUND_TUTTI = dsp.synth_grand_tutti()
SOUND_CHOIR = dsp.synth_choir_ensemble([130.81, 196.00, 261.63, 329.63, 392.00, 523.25], pan=0.0)
SND_GONG = dsp.synth_gong()

audio_energy = 0.0

# ==================================================================================================
# 9. DUAL-LAPTOP UDP PEER-TO-PEER SCORE SYNCHRONIZATION ENGINE
# ==================================================================================================
class NetworkSyncEngine:
    def __init__(self, port=UDP_PORT, app_reference=None):
        self.port = port
        self.app = app_reference
        self.player_id = f"PILOT_{random.randint(100, 999)}"
        self.peer_id = "RIVAL_PILOT"
        self.peer_score = 0
        self.peer_combo = 0
        self.peer_game = "MENU"
        self.last_packet_time = 0.0
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            self.sock.bind(("", self.port))
            self.sock.settimeout(0.02)
        except Exception as e:
            print(f"[NET DEBUG] Socket bind notice: {e}")

        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

        threading.Timer(1.0, self.request_full_sync).start()

    def _send_broadcast(self, packet):
        data = json.dumps(packet).encode("utf-8")
        try:
            self.sock.sendto(data, ("<broadcast>", self.port))
        except Exception:
            try:
                self.sock.sendto(data, ("127.0.0.1", self.port))
            except Exception:
                pass

    def request_full_sync(self):
        packet = {
            "type": "SYNC_REQUEST",
            "player_id": self.player_id,
            "time": time.time()
        }
        self._send_broadcast(packet)

    def broadcast_full_sync_response(self):
        if not self.app:
            return
            
        sync_data = {
            "wall_of_fame_tiles.json": self.app.game2_tiles.board.scores,
            "wall_of_fame_blades.json": self.app.game3_blades.board.scores,
            "wall_of_fame_catcher.json": self.app.game5_singularity.board.scores
        }
        
        packet = {
            "type": "SYNC_RESPONSE",
            "player_id": self.player_id,
            "boards": sync_data,
            "time": time.time()
        }
        self._send_broadcast(packet)

    def broadcast_state(self, current_game, score, combo):
        packet = {
            "type": "HEARTBEAT",
            "player_id": self.player_id,
            "game": current_game,
            "score": int(score),
            "combo": int(combo),
            "time": time.time()
        }
        self._send_broadcast(packet)

    def broadcast_high_score(self, board_file, tag, score, combo):
        packet = {
            "type": "NEW_HIGH_SCORE",
            "player_id": self.player_id,
            "board_file": board_file,
            "tag": tag,
            "score": int(score),
            "combo": int(combo)
        }
        self._send_broadcast(packet)

    def _merge_single_score(self, board_file, tag, score, combo):
        if not board_file or tag is None or score is None:
            return
        if "tiles" in board_file:
            self.app.game2_tiles.board.add_score(tag, score, combo, network_engine=self, is_remote=True)
        elif "blades" in board_file:
            self.app.game3_blades.board.add_score(tag, score, combo, network_engine=self, is_remote=True)
        elif "catcher" in board_file:
            self.app.game5_singularity.board.add_score(tag, score, combo, network_engine=self, is_remote=True)

    def _worker(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("player_id") != self.player_id:
                    msg_type = msg.get("type", "HEARTBEAT")
                    
                    if msg_type == "HEARTBEAT":
                        self.peer_id = msg.get("player_id", "RIVAL")
                        self.peer_score = msg.get("score", 0)
                        self.peer_combo = msg.get("combo", 0)
                        self.peer_game = msg.get("game", "MENU")
                        self.last_packet_time = time.time()

                    elif msg_type == "NEW_HIGH_SCORE" and self.app:
                        self._merge_single_score(msg.get("board_file"), msg.get("tag"), msg.get("score"), msg.get("combo"))

                    elif msg_type == "SYNC_REQUEST" and self.app:
                        self.broadcast_full_sync_response()

                    elif msg_type == "SYNC_RESPONSE" and self.app:
                        boards = msg.get("boards", {})
                        for board_file, scores in boards.items():
                            for entry in scores:
                                self._merge_single_score(board_file, entry.get("tag"), entry.get("score"), entry.get("combo"))
            except Exception:
                pass
            time.sleep(0.015)

    def is_peer_active(self):
        return (time.time() - self.last_packet_time) < 2.5

    def draw_hud(self, surf, font_sm, local_score, local_combo):
        rect = pygame.Rect(WIDTH - 380, 16, 360, 48)
        peer_online = self.is_peer_active()
        border_col = UITheme.NEON_GREEN if peer_online else UITheme.NEON_PINK
        
        NeonFX.draw_hud_pill(surf, rect, border_color=border_col, radius=12, elevation=8)
        status_col = UITheme.NEON_GREEN if peer_online else (100, 110, 130)
        pygame.draw.circle(surf, status_col, (rect.x + 18, rect.centery), 6)
        if peer_online:
            NeonFX.draw_glow_circle(surf, status_col, (rect.x + 18, rect.centery), 6, glow_size=8, max_alpha=180)

        status_lbl = "RIVAL LINK: CONNECTED" if peer_online else "NET: BROADCASTING (SOLO)"
        surf.blit(font_sm.render(status_lbl, True, status_col), (rect.x + 34, rect.y + 6))

        delta = local_score - self.peer_score
        delta_str = f"+{delta}" if delta >= 0 else f"{delta}"
        delta_col = UITheme.NEON_CYAN if delta >= 0 else UITheme.NEON_PINK
        stats = f"YOU: {local_score} | RIVAL: {self.peer_score} ({delta_str})" if peer_online else f"LOCAL ID: {self.player_id}"
        surf.blit(font_sm.render(stats, True, delta_col if peer_online else UITheme.TEXT_MUTED), (rect.x + 34, rect.y + 26))

# ==================================================================================================
# 10. EXHIBITION SESSION TIMEOUT WATCHDOG ENGINE
# ==================================================================================================
class ExhibitionSessionManager:
    def __init__(self, duration_minutes=12.0):
        self.duration = duration_minutes * 60.0
        self.time_left = self.duration
        self.is_expired = False
        self.active = False

    def update(self, dt):
        if not self.active or self.is_expired:
            return
        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0.0:
            self.is_expired = True

    def reset_session(self):
        self.time_left = self.duration
        self.is_expired = False

    def draw_hud(self, surf, font_sm, font_md, font_lg):
        mins = int(self.time_left // 60)
        secs = int(self.time_left % 60)
        t_str = f"{mins:02d}:{secs:02d}"

        col = UITheme.NEON_CYAN if self.time_left > 300 else (UITheme.NEON_ORANGE if self.time_left > 120 else UITheme.NEON_PINK)
        rect = pygame.Rect(20, 16, 210, 48)
        NeonFX.draw_hud_pill(surf, rect, border_color=col, radius=12, elevation=8)
        surf.blit(font_sm.render("SESSION LIMIT", True, UITheme.TEXT_MUTED), (rect.x + 14, rect.y + 5))
        surf.blit(font_md.render(t_str, True, col), (rect.x + 14, rect.y + 22))

        if self.is_expired:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((4, 6, 10, 245))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(WIDTH // 2 - 320, HEIGHT // 2 - 180, 640, 360)
            NeonFX.draw_glass_card(surf, card, border_color=UITheme.NEON_PINK, border_width=4, radius=24, elevation=24)
            draw_ribbon(surf, font_lg, "SESSION LIMIT REACHED", WIDTH // 2, card.y, 480, 56, UITheme.NEON_PINK)

            t1 = font_md.render("THANK YOU FOR EXPERIENCING AETHERIA GRAND PRIX!", True, UITheme.PURE_WHITE)
            t2 = font_sm.render("Your session time has ended to welcome the next player in the exhibition.", True, UITheme.TEXT_MUTED)
            t3 = font_sm.render("Please scan the booth QR to save your Musical DNA Certificate.", True, UITheme.NEON_GOLD)
            t4 = font_sm.render("OPERATOR: PRESS [F12] OR [ESC] TO COMMENCE NEXT PLAYER SESSION", True, UITheme.NEON_CYAN)

            surf.blit(t1, (WIDTH // 2 - t1.get_width() // 2, card.y + 90))
            surf.blit(t2, (WIDTH // 2 - t2.get_width() // 2, card.y + 140))
            surf.blit(t3, (WIDTH // 2 - t3.get_width() // 2, card.y + 180))
            surf.blit(t4, (WIDTH // 2 - t4.get_width() // 2, card.bottom - 45))

# ==================================================================================================
# 11. 3D WALL OF FAME SCOREBOARD & LEADERBOARD SYSTEM (TOP 20 ARCADE EDITION)
# ==================================================================================================
class WallOfFameBoard:
    def __init__(self, filename, title="WALL OF FAME"):
        self.filename = filename
        self.title = title
        self.scores = []
        self.entering_name = False
        self.player_input_tag = ""
        self.pending_score = 0
        self.pending_combo = 0
        
        # Smooth Kinetic Scroll Engine
        self.scroll_y = 0.0
        self.target_scroll_y = 0.0
        self.prev_mouse_y = None
        self.prev_hand_y = None
        self.is_hand_scrolling = False
        self.last_draw_time = time.time()
        
        self._load_or_default()

    def _load_or_default(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    loaded = json.load(f)
                    if loaded and len(loaded) > 0:
                        self.scores = loaded[:20]
                        for idx, row in enumerate(self.scores):
                            row["rank"] = idx + 1
                        return
            except Exception:
                pass

        # 20 Authentic Arcade Master High Scores
        arcade_presets = [
            ("CYBER_VIRTUOSO", 28500, "S+", 94),
            ("NEO_MAESTRO",    25200, "S+", 86),
            ("SYNTH_RACER",    22400, "S",  78),
            ("AETHER_PILOT",   19800, "S",  69),
            ("QUANTUM_BEAT",   18100, "S",  63),
            ("HYPER_CONDUCT",  16500, "A",  56),
            ("PULSE_KNIGHT",   15100, "A",  51),
            ("VOID_WALKER",    13800, "A",  45),
            ("SONIC_VALKYRIE", 12700, "A",  41),
            ("CHORD_MASTER",   11800, "A",  38),
            ("STELLA_STRIKE",  10900, "B",  35),
            ("OMEGA_RHYTHM",   10100, "B",  32),
            ("GLITCH_RUNNER",  9300,  "B",  29),
            ("ECHO_SYNTH",     8700,  "B",  27),
            ("AURA_PILOT",     8000,  "B",  24),
            ("CADET_CHORD",    7300,  "B",  21),
            ("NEON_BLADE",     6600,  "C",  18),
            ("STAR_DRIFTER",   5900,  "C",  15),
            ("BIT_MAESTRO",    5200,  "C",  12),
            ("SOUND_WAVE",     4500,  "C",  10)
        ]
        self.scores = [
            {"rank": i + 1, "tag": tag, "score": sc, "grade": gr, "combo": cb}
            for i, (tag, sc, gr, cb) in enumerate(arcade_presets)
        ]
        self.save()

    def save(self):
        try:
            with open(self.filename, "w") as f:
                json.dump(self.scores[:20], f, indent=2)
        except Exception:
            pass

    def start_name_entry(self, score, combo):
        self.pending_score = int(score)
        self.pending_combo = int(combo)
        self.player_input_tag = ""
        self.entering_name = True
        self.scroll_y = 0.0
        self.target_scroll_y = 0.0

    def handle_wheel(self, y_offset):
        self.target_scroll_y -= y_offset * 52.0

    def handle_key_input(self, event, network_engine=None):
        if not self.entering_name:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                final_tag = self.player_input_tag.strip().upper() or "AETHER_PILOT"
                self.add_score(final_tag, self.pending_score, self.pending_combo, network_engine, is_remote=False)
                self.entering_name = False
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.player_input_tag = self.player_input_tag[:-1]
            elif len(self.player_input_tag) < 12 and event.unicode.isalnum():
                self.player_input_tag += event.unicode.upper()
        return False

    def add_score(self, tag, score, combo, network_engine=None, is_remote=False):
        grade = "S+" if score > 20000 else ("S" if score > 15000 else ("A" if score > 10000 else "B"))
        new_entry = {"tag": tag, "score": int(score), "grade": grade, "combo": int(combo)}

        if not any(e["tag"] == tag and e["score"] == score for e in self.scores):
            self.scores.append(new_entry)
            self.scores = sorted(self.scores, key=lambda x: x["score"], reverse=True)[:20]
            for idx, row in enumerate(self.scores):
                row["rank"] = idx + 1
            self.save()

            if network_engine and not is_remote:
                network_engine.broadcast_high_score(self.filename, tag, score, combo)

    def draw(self, surf, font_sm, font_md, font_lg, close_lbl="[SPACE] REPLAY | [ESC] MAIN HUB", hands=[]):
        now = time.time()
        dt = min(0.05, max(1e-4, now - self.last_draw_time))
        self.last_draw_time = now

        card = pygame.Rect(WIDTH // 2 - 380, 50, 760, 615)
        NeonFX.draw_glass_card(surf, card, border_color=UITheme.NEON_GOLD, border_width=3, radius=24, elevation=24, is_3d=True)
        draw_ribbon(surf, font_lg, self.title, WIDTH // 2, 50, 620, 56, UITheme.NEON_PURPLE)

        # Name Entry Dialog
        if self.entering_name:
            prompt_card = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 110, 520, 220)
            NeonFX.draw_glass_card(surf, prompt_card, border_color=UITheme.NEON_CYAN, border_width=3, radius=22, elevation=24)
            
            t_prompt = font_md.render("NEW HIGH SCORE! ENTER PILOT TAG:", True, UITheme.NEON_GOLD)
            surf.blit(t_prompt, (WIDTH // 2 - t_prompt.get_width() // 2, prompt_card.y + 26))

            input_rect = pygame.Rect(WIDTH // 2 - 190, prompt_card.y + 80, 380, 52)
            NeonFX.draw_hud_pill(surf, input_rect, border_color=UITheme.NEON_CYAN, radius=12, elevation=10)
            
            tag_display = self.player_input_tag + ("_" if (time.time() * 2) % 1 > 0.5 else "")
            t_tag = font_lg.render(tag_display or "_", True, UITheme.PURE_WHITE)
            surf.blit(t_tag, (WIDTH // 2 - t_tag.get_width() // 2, input_rect.y + 4))

            t_sub = font_sm.render("TYPE YOUR PILOT NAME & PRESS [ENTER]", True, UITheme.TEXT_MUTED)
            surf.blit(t_sub, (WIDTH // 2 - t_sub.get_width() // 2, prompt_card.bottom - 36))
            return

        # Modern Arcade Column Headers
        header_y = 118
        headers = [
            ("RANK", 42),
            ("PILOT CALLSIGN", 175),
            ("HIGH SCORE", 370),
            ("MAX STREAK", 515),
            ("TIER", 635)
        ]
        for h_txt, x_off in headers:
            surf.blit(font_sm.render(h_txt, True, UITheme.TEXT_MUTED), (card.x + x_off, header_y))

        # Glowing Neon Divider Line
        pygame.draw.line(surf, (40, 60, 100), (card.x + 24, 142), (card.right - 24, 142), 2)
        pygame.draw.line(surf, UITheme.NEON_CYAN, (card.x + 24, 142), (card.x + 180, 142), 2)

        # ----------------- SCROLLABLE VIEWPORT (TOP 20) -----------------
        list_rect = pygame.Rect(card.x + 20, 148, card.width - 40, 400)
        row_height = 54
        gap = 8
        total_content_h = len(self.scores) * (row_height + gap)
        max_scroll = max(0.0, float(total_content_h - list_rect.height))

        # 1. Mouse Drag / Click Scroll Processing
        mx, my = pygame.mouse.get_pos()
        m_pressed = pygame.mouse.get_pressed()[0]
        if m_pressed and list_rect.collidepoint(mx, my):
            if self.prev_mouse_y is not None:
                dy = my - self.prev_mouse_y
                self.target_scroll_y -= dy * 1.6
            self.prev_mouse_y = my
        else:
            self.prev_mouse_y = None

        # 2. Hand Gesture Scroll Processing (Pinch/Fist Drag or Right-bar Hover)
        self.is_hand_scrolling = False
        if hands:
            for h in hands:
                pt = h["beam_target"] if h["is_distant"] else h["lead_tip"]
                hx, hy = pt
                if card.collidepoint(hx, hy):
                    if h["is_pinching"] or h["is_fist"]:
                        self.is_hand_scrolling = True
                        if self.prev_hand_y is not None:
                            dy = hy - self.prev_hand_y
                            self.target_scroll_y -= dy * 1.8
                        self.prev_hand_y = hy
                        break
                    elif hx > card.right - 70:
                        # Direct slider mapping along the right scroll bar
                        rel = np.clip((hy - list_rect.y) / float(list_rect.height), 0.0, 1.0)
                        self.target_scroll_y = rel * max_scroll
                        self.is_hand_scrolling = True
                        break
        if not self.is_hand_scrolling:
            self.prev_hand_y = None

        # Clamp & Smooth Scroll Lerp
        self.target_scroll_y = np.clip(self.target_scroll_y, 0.0, max_scroll)
        self.scroll_y += (self.target_scroll_y - self.scroll_y) * min(1.0, 12.0 * dt)

        # Draw Clipped Rows
        prev_clip = surf.get_clip()
        surf.set_clip(list_rect)

        for r_idx, row in enumerate(self.scores[:20]):
            yy = list_rect.y + r_idx * (row_height + gap) - int(self.scroll_y)
            if yy + row_height < list_rect.y - 10 or yy > list_rect.bottom + 10:
                continue

            row_rect = pygame.Rect(list_rect.x + 8, yy, list_rect.width - 32, row_height)
            rank_num = row["rank"]

            # Distinct Tier Styling (AAA Modern Arcade Layout)
            if rank_num == 1:
                # Gold Stage Ace
                border_c = UITheme.NEON_GOLD
                bg_tint = (30, 24, 12, 235)
                rank_badge_col = UITheme.NEON_GOLD
                rank_lbl = "★ #1"
                txt_col = UITheme.PURE_WHITE
            elif rank_num == 2:
                # Silver Master
                border_c = (195, 220, 255)
                bg_tint = (18, 24, 38, 235)
                rank_badge_col = (195, 220, 255)
                rank_lbl = "✦ #2"
                txt_col = UITheme.PURE_WHITE
            elif rank_num == 3:
                # Bronze Elite
                border_c = UITheme.NEON_ORANGE
                bg_tint = (28, 18, 14, 235)
                rank_badge_col = UITheme.NEON_ORANGE
                rank_lbl = "◆ #3"
                txt_col = UITheme.PURE_WHITE
            else:
                border_c = UITheme.GLASS_BORDER if rank_num <= 10 else (28, 42, 68)
                bg_tint = (12, 16, 28, 210)
                rank_badge_col = UITheme.NEON_CYAN if rank_num <= 10 else UITheme.TEXT_MUTED
                rank_lbl = f"#{rank_num:02d}"
                txt_col = (230, 238, 255) if rank_num <= 10 else UITheme.TEXT_MUTED

            row_surf = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(row_surf, bg_tint, (0, 0, row_rect.width, row_rect.height), border_radius=12)
            pygame.draw.rect(row_surf, (*border_c[:3], 210), (0, 0, row_rect.width, row_rect.height), 2 if rank_num <= 3 else 1, border_radius=12)
            
            # 3D Specular Highlight on Row Top
            pygame.draw.line(row_surf, UITheme.GLASS_HIGHLIGHT, (12, 1), (row_rect.width - 12, 1), 1)
            surf.blit(row_surf, row_rect.topleft)

            # Draw Columns
            surf.blit(font_md.render(rank_lbl, True, rank_badge_col), (row_rect.x + 18, yy + 13))
            surf.blit(font_md.render(row["tag"], True, txt_col), (row_rect.x + 155, yy + 13))
            surf.blit(font_md.render(str(row["score"]), True, UITheme.NEON_GREEN), (row_rect.x + 350, yy + 13))
            surf.blit(font_md.render(f"{row['combo']}x", True, UITheme.NEON_GOLD), (row_rect.x + 495, yy + 13))
            
            # Grade Badge Pill
            grade_pill = pygame.Rect(row_rect.x + 615, yy + 11, 48, 30)
            g_col = UITheme.NEON_PINK if "S" in row["grade"] else (UITheme.NEON_CYAN if "A" in row["grade"] else UITheme.TEXT_MUTED)
            pygame.draw.rect(surf, (15, 20, 32), grade_pill, border_radius=8)
            pygame.draw.rect(surf, g_col, grade_pill, 1, border_radius=8)
            g_txt = font_sm.render(row["grade"], True, g_col)
            surf.blit(g_txt, (grade_pill.centerx - g_txt.get_width() // 2, grade_pill.centery - g_txt.get_height() // 2))

        # Restore Surface Clipping
        surf.set_clip(prev_clip)

        # ----------------- CYBERNETIC SCROLLBAR TRACK & THUMB -----------------
        if max_scroll > 0:
            track_rect = pygame.Rect(card.right - 24, list_rect.y, 8, list_rect.height)
            pygame.draw.rect(surf, (16, 22, 38), track_rect, border_radius=4)
            pygame.draw.rect(surf, (35, 50, 80), track_rect, 1, border_radius=4)

            thumb_ratio = list_rect.height / float(total_content_h)
            thumb_h = max(28, int(list_rect.height * thumb_ratio))
            thumb_y = list_rect.y + int((self.scroll_y / max_scroll) * (list_rect.height - thumb_h))
            thumb_rect = pygame.Rect(track_rect.x - 1, thumb_y, 10, thumb_h)
            
            NeonFX.draw_glow_circle(surf, UITheme.NEON_CYAN, thumb_rect.center, 8, glow_size=8, max_alpha=160)
            pygame.draw.rect(surf, UITheme.NEON_CYAN, thumb_rect, border_radius=5)
            pygame.draw.rect(surf, UITheme.PURE_WHITE, thumb_rect, 1, border_radius=5)

        # Bottom Hint & Status
        hint_col = UITheme.NEON_GOLD if self.is_hand_scrolling else UITheme.PURE_WHITE
        scroll_status = "✋ [HAND SCROLLING]" if self.is_hand_scrolling else "[SCROLL: MOUSE WHEEL / DRAG OR PINCH HAND]"
        t_hint = font_sm.render(f"{scroll_status}  |  {close_lbl}", True, hint_col)
        surf.blit(t_hint, (WIDTH // 2 - t_hint.get_width() // 2, card.bottom - 36))

# ==================================================================================================
# 12. MASTER COMBINED 3D SCOREBOARD HUB (TOP 20 GLOBAL HALL OF FAME)
# ==================================================================================================
class MasterScoreboardHub:
    def __init__(self, tiles_board, blades_board, singularity_board):
        self.boards = [
            ("NEO PIANO TILES", tiles_board, UITheme.NEON_CYAN),
            ("SYNTH BLADE", blades_board, UITheme.NEON_GOLD),
            ("CELESTIAL HARP", singularity_board, UITheme.NEON_PURPLE)
        ]
        # Independent smooth scroll channels for each column
        self.scroll_y = [0.0, 0.0, 0.0]
        self.target_scroll_y = [0.0, 0.0, 0.0]
        self.prev_mouse_y = None
        self.prev_hand_y = None
        self.active_col_idx = 0
        self.last_draw_time = time.time()

    def handle_wheel(self, y_offset):
        mx, _ = pygame.mouse.get_pos()
        col_w = 380
        gap = 16
        start_x = (WIDTH - (col_w * 3 + gap * 2)) // 2
        
        # Scroll the specific column under cursor, or all if outside
        scrolled_any = False
        for idx in range(3):
            cx = start_x + idx * (col_w + gap)
            if cx <= mx <= cx + col_w:
                self.target_scroll_y[idx] -= y_offset * 54.0
                scrolled_any = True
                break
        if not scrolled_any:
            for idx in range(3):
                self.target_scroll_y[idx] -= y_offset * 54.0

    def draw(self, surf, font_sm, font_md, font_lg, hands=[]):
        now = time.time()
        dt = min(0.05, max(1e-4, now - self.last_draw_time))
        self.last_draw_time = now

        main_card = pygame.Rect(25, 25, WIDTH - 50, HEIGHT - 50)
        NeonFX.draw_glass_card(surf, main_card, border_color=UITheme.NEON_GOLD, border_width=2, radius=24, elevation=24, is_3d=True)
        draw_ribbon(surf, font_lg, "GLOBAL HALL OF FAME — TOP 20 PILOTS", WIDTH // 2, 25, 720, 52, UITheme.NEON_PURPLE)

        col_w = 380
        gap = 16
        start_x = (WIDTH - (col_w * 3 + gap * 2)) // 2
        row_height = 46
        row_gap = 6

        mx, my = pygame.mouse.get_pos()
        m_pressed = pygame.mouse.get_pressed()[0]

        for idx, (title, board, theme_col) in enumerate(self.boards):
            cx = start_x + idx * (col_w + gap)
            card = pygame.Rect(cx, 88, col_w, 530)
            NeonFX.draw_glass_card(surf, card, border_color=theme_col, border_width=2, radius=18, elevation=12, is_3d=True)
            
            # Column Pill Header
            header_rect = pygame.Rect(cx + 10, 98, col_w - 20, 36)
            NeonFX.draw_hud_pill(surf, header_rect, border_color=theme_col, radius=10, elevation=6)
            t_hdr = font_md.render(title, True, theme_col)
            surf.blit(t_hdr, (header_rect.centerx - t_hdr.get_width() // 2, header_rect.centery - t_hdr.get_height() // 2))

            # Column Subheaders
            surf.blit(font_sm.render("RANK", True, UITheme.TEXT_MUTED), (cx + 18, 142))
            surf.blit(font_sm.render("PILOT", True, UITheme.TEXT_MUTED), (cx + 80, 142))
            surf.blit(font_sm.render("SCORE", True, UITheme.TEXT_MUTED), (cx + 215, 142))
            surf.blit(font_sm.render("STREAK", True, UITheme.TEXT_MUTED), (cx + 305, 142))
            pygame.draw.line(surf, (40, 60, 100), (cx + 14, 162), (cx + col_w - 14, 162), 1)

            # Viewport Clip Setup
            list_rect = pygame.Rect(cx + 8, 168, col_w - 16, 435)
            scores_to_show = board.scores[:20]
            total_content_h = len(scores_to_show) * (row_height + row_gap)
            max_scroll = max(0.0, float(total_content_h - list_rect.height))

            # 1. Mouse Drag
            if m_pressed and list_rect.collidepoint(mx, my):
                if self.prev_mouse_y is not None:
                    dy = my - self.prev_mouse_y
                    self.target_scroll_y[idx] -= dy * 1.5
                self.prev_mouse_y = my
            elif not m_pressed and idx == 2:
                self.prev_mouse_y = None

            # 2. Hand Gesture Drag
            if hands:
                for h in hands:
                    pt = h["beam_target"] if h["is_distant"] else h["lead_tip"]
                    hx, hy = pt
                    if list_rect.collidepoint(hx, hy) and (h["is_pinching"] or h["is_fist"]):
                        if self.prev_hand_y is not None:
                            dy = hy - self.prev_hand_y
                            self.target_scroll_y[idx] -= dy * 1.6
                        self.prev_hand_y = hy
                        break
            if not hands and idx == 2:
                self.prev_hand_y = None

            # Smooth Interpolation & Clamping
            self.target_scroll_y[idx] = np.clip(self.target_scroll_y[idx], 0.0, max_scroll)
            self.scroll_y[idx] += (self.target_scroll_y[idx] - self.scroll_y[idx]) * min(1.0, 12.0 * dt)

            # Draw Clipped Rows
            prev_clip = surf.get_clip()
            surf.set_clip(list_rect)

            for r_idx, row in enumerate(scores_to_show):
                yy = list_rect.y + r_idx * (row_height + row_gap) - int(self.scroll_y[idx])
                if yy + row_height < list_rect.y - 10 or yy > list_rect.bottom + 10:
                    continue

                row_rect = pygame.Rect(list_rect.x + 4, yy, list_rect.width - 18, row_height)
                rank_num = row["rank"]

                # Modern Arcade Crests
                if rank_num == 1:
                    border_c = UITheme.NEON_GOLD
                    bg_tint = (32, 26, 14, 230)
                    rank_c = UITheme.NEON_GOLD
                    badge_str = "★ #1"
                elif rank_num == 2:
                    border_c = (190, 220, 255)
                    bg_tint = (16, 22, 36, 230)
                    rank_c = (190, 220, 255)
                    badge_str = "✦ #2"
                elif rank_num == 3:
                    border_c = UITheme.NEON_ORANGE
                    bg_tint = (26, 18, 16, 230)
                    rank_c = UITheme.NEON_ORANGE
                    badge_str = "◆ #3"
                else:
                    border_c = (35, 52, 80)
                    bg_tint = (12, 16, 26, 195)
                    rank_c = UITheme.NEON_CYAN if rank_num <= 10 else UITheme.TEXT_MUTED
                    badge_str = f"#{rank_num:02d}"

                row_surf = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(row_surf, bg_tint, (0, 0, row_rect.width, row_rect.height), border_radius=10)
                pygame.draw.rect(row_surf, (*border_c[:3], 210), (0, 0, row_rect.width, row_rect.height), 2 if rank_num <= 3 else 1, border_radius=10)
                pygame.draw.line(row_surf, UITheme.GLASS_HIGHLIGHT, (8, 1), (row_rect.width - 8, 1), 1)
                surf.blit(row_surf, row_rect.topleft)

                surf.blit(font_md.render(badge_str, True, rank_c), (cx + 18, yy + 10))
                surf.blit(font_sm.render(row['tag'][:11], True, UITheme.PURE_WHITE), (cx + 80, yy + 14))
                surf.blit(font_sm.render(str(row['score']), True, UITheme.NEON_GREEN), (cx + 215, yy + 14))
                surf.blit(font_sm.render(f"{row['combo']}x", True, UITheme.NEON_GOLD), (cx + 305, yy + 14))

            surf.set_clip(prev_clip)

            # Miniature Column Scrollbar
            if max_scroll > 0:
                bar_x = card.right - 12
                bar_rect = pygame.Rect(bar_x, list_rect.y, 4, list_rect.height)
                pygame.draw.rect(surf, (15, 20, 32), bar_rect, border_radius=2)
                
                s_ratio = list_rect.height / float(total_content_h)
                s_thumb_h = max(24, int(list_rect.height * s_ratio))
                s_thumb_y = list_rect.y + int((self.scroll_y[idx] / max_scroll) * (list_rect.height - s_thumb_h))
                s_thumb = pygame.Rect(bar_x - 1, s_thumb_y, 6, s_thumb_h)
                pygame.draw.rect(surf, theme_col, s_thumb, border_radius=3)

        foot = font_sm.render("[SCROLL: MOUSE WHEEL / PINCH GESTURE]  |  [ESC] / [SPACE] MAIN MENU  |  [F11] NETWORK SYNC", True, UITheme.PURE_WHITE)
        surf.blit(foot, (WIDTH // 2 - foot.get_width() // 2, HEIGHT - 38))

# ==================================================================================================
# [END OF PART 1/3]
# Paste this block into your code file. When you are ready for Part 2, reply: continue
# ==================================================================================================
"""
====================================================================================================
PROJECT: AETHERIA GRAND PRIX — SULAM 2026 NEO-SYMPHONIC EXHIBITION MASTERPIECE
ROLE: PRINCIPAL GAME ARCHITECT & 3D GRAPHICS/AUDIO SYSTEMS ENGINEER (AAA PRODUCTION SPEC)
PART 2 / 3: REALISTIC 3D GLOVE & DOCK HUD, 3D PARTICLE/COSMIC VFX PIPELINE,
            ANIMATED CONCERT ORCHESTRA & CINEMATIC CAMERA DIRECTOR,
            3D SPATIAL GESTURE HUB, 3D PHYSICAL INSTRUMENT CONTROLLERS,
            FREESTYLE LAB & ACCELERATING 3D PERSPECTIVE PIANO TILES ENGINE
====================================================================================================
"""

# ==================================================================================================
# 13. REALISTIC EMISSIVE GLOVE & 3D HOLOGRAPHIC WRIST DOCK HUD
# ==================================================================================================
def draw_realistic_hand(surf, hand_data):
    """
    Renders an anatomically articulated conductor glove with realistic ambient cast shadow,
    depth contours, gold cuff accents, and emissive joint articulation.
    """
    lm = hand_data["landmarks"]
    is_fist = hand_data["is_fist"]
    is_pinching = hand_data["is_pinching"]

    GLOVE_BASE      = (240, 245, 255)
    GLOVE_SHADOW    = (150, 165, 195)
    GLOVE_DEEP_SHD  = (95, 110, 140)
    GLOVE_HIGHLIGHT = (255, 255, 255)
    GLOVE_STITCH    = (175, 190, 215)
    GOLD_CUFF       = (245, 195, 55)
    GOLD_GLOW       = (255, 230, 110)

    wrist = np.array(lm[0], dtype=float)
    index_mcp = np.array(lm[5], dtype=float)
    pinky_mcp = np.array(lm[17], dtype=float)

    # 3D Soft Ground / Backdrop Cast Shadow behind the entire hand
    palm_center = lm[9]
    ShadowEngine.draw_projected_ground_shadow(surf, palm_center[0] + 10, palm_center[1] + 16, 95, 45, alpha=110)

    # Articulated Arm & Gold Embroidered Cuff
    arm_dir = wrist - ((index_mcp + pinky_mcp) * 0.5)
    arm_dist = np.linalg.norm(arm_dir)
    if arm_dist > 1e-3:
        arm_unit = arm_dir / arm_dist
        arm_perp = np.array([-arm_unit[1], arm_unit[0]])
        cuff_base = wrist + arm_unit * 34.0
        
        # Extruded 3D Sleeve Underlay (Shadow Bevel)
        sleeve_shd_pts = [
            (wrist + arm_perp * 26.0 + np.array([2, 4])).astype(int),
            (cuff_base + arm_perp * 34.0 + np.array([2, 4])).astype(int),
            (cuff_base - arm_perp * 34.0 + np.array([2, 4])).astype(int),
            (wrist - arm_perp * 26.0 + np.array([2, 4])).astype(int)
        ]
        pygame.draw.polygon(surf, (15, 20, 32), sleeve_shd_pts)

        cuff_pts = [
            (wrist + arm_perp * 25.0).astype(int), (cuff_base + arm_perp * 33.0).astype(int),
            (cuff_base - arm_perp * 33.0).astype(int), (wrist - arm_perp * 25.0).astype(int)
        ]
        pygame.draw.polygon(surf, GLOVE_SHADOW, cuff_pts)
        pygame.draw.polygon(surf, GLOVE_BASE, [
            (wrist + arm_perp * 20.0).astype(int), (cuff_base + arm_perp * 28.0).astype(int),
            (cuff_base - arm_perp * 28.0).astype(int), (wrist - arm_perp * 20.0).astype(int)
        ])
        pygame.draw.polygon(surf, GLOVE_DEEP_SHD, cuff_pts, 2)
        
        cufflink_pos = (wrist + arm_unit * 16.0 + arm_perp * 18.0).astype(int)
        pygame.draw.circle(surf, GOLD_CUFF, cufflink_pos, 6)
        pygame.draw.circle(surf, GOLD_GLOW, cufflink_pos, 3)
        NeonFX.draw_glow_circle(surf, GOLD_GLOW, cufflink_pos, 4, glow_size=8, max_alpha=180)

    # Articulated Palm Plate
    palm_ids = [0, 1, 2, 5, 9, 13, 17]
    palm_pts = [lm[i] for i in palm_ids]
    
    # Palm Ambient Depth Underlay
    shadow_offset_pts = [(p[0] + 3, p[1] + 4) for p in palm_pts]
    pygame.draw.polygon(surf, GLOVE_DEEP_SHD, shadow_offset_pts)

    pygame.draw.polygon(surf, GLOVE_SHADOW, palm_pts)
    inner_palm = [((p[0] * 4 + lm[9][0]) // 5, (p[1] * 4 + lm[9][1]) // 5) for p in palm_pts]
    pygame.draw.polygon(surf, GLOVE_BASE, inner_palm)
    pygame.draw.polygon(surf, GLOVE_DEEP_SHD, palm_pts, 2)

    # Glove Stitch Details
    for base_id in [5, 9, 13]:
        p_base = np.array(lm[base_id], dtype=float)
        p_mid = wrist + (p_base - wrist) * 0.45
        pygame.draw.line(surf, GLOVE_STITCH, (int(p_mid[0]), int(p_mid[1])), (int(p_base[0]), int(p_base[1])), 2)

    # 3D Cylindrical Finger Bones with Dynamic Lighting & Bevel Highlights
    finger_chains = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]
    for f_idx, chain in enumerate(finger_chains):
        for seg in range(len(chain) - 1):
            p1 = np.array(lm[chain[seg]], dtype=float)
            p2 = np.array(lm[chain[seg + 1]], dtype=float)
            vec = p2 - p1
            dist = np.linalg.norm(vec)
            if dist < 1e-4: continue
            normal = np.array([-vec[1], vec[0]]) / dist
            w1 = max(6.0, 13.5 - (seg * 2.2) - (1.5 if f_idx == 4 else 0.0))
            w2 = max(5.0, 11.5 - ((seg + 1) * 2.2) - (1.5 if f_idx == 4 else 0.0))
            
            # Cast shadow under individual finger segments
            poly_shd = [
                (p1 + normal * w1 + np.array([2, 3])).astype(int),
                (p2 + normal * w2 + np.array([2, 3])).astype(int),
                (p2 - normal * w2 + np.array([2, 3])).astype(int),
                (p1 - normal * w1 + np.array([2, 3])).astype(int)
            ]
            pygame.draw.polygon(surf, (20, 26, 40, 120), poly_shd)

            poly_pts = [
                (p1 + normal * w1).astype(int), (p2 + normal * w2).astype(int),
                (p2 - normal * w2).astype(int), (p1 - normal * w1).astype(int)
            ]
            pygame.draw.polygon(surf, GLOVE_SHADOW, poly_pts)
            pygame.draw.polygon(surf, GLOVE_BASE, [
                (p1 + normal * (w1 * 0.75)).astype(int), (p2 + normal * (w2 * 0.75)).astype(int),
                (p2 - normal * (w2 * 0.5)).astype(int), (p1 - normal * (w1 * 0.5)).astype(int)
            ])
            pygame.draw.polygon(surf, GLOVE_DEEP_SHD, poly_pts, 1)
            pygame.draw.line(surf, GLOVE_HIGHLIGHT, (p1 + normal * (w1 * 0.45)).astype(int), (p2 + normal * (w2 * 0.45)).astype(int), 2)
            pygame.draw.circle(surf, GLOVE_BASE, tuple(p1.astype(int)), int(w1 * 0.85))

        tip = tuple(lm[chain[-1]])
        pygame.draw.circle(surf, GLOVE_BASE, tip, 6)
        pygame.draw.circle(surf, GLOVE_HIGHLIGHT, (tip[0] - 1, tip[1] - 1), 3)

    if is_pinching:
        mid_pinch = ((lm[4][0] + lm[8][0]) // 2, (lm[4][1] + lm[8][1]) // 2)
        NeonFX.draw_glow_circle(surf, UITheme.NEON_GOLD, mid_pinch, 14, glow_size=18, max_alpha=180)
        pygame.draw.circle(surf, UITheme.PURE_WHITE, mid_pinch, 6)
        pygame.draw.line(surf, UITheme.NEON_GOLD, lm[4], lm[8], 2)
    elif is_fist:
        NeonFX.draw_glow_circle(surf, UITheme.NEON_PINK, lm[9], 20, glow_size=22, max_alpha=160)

def draw_apple_wrist_hud(surf, hand, app_state, font_sm, other_hands=[]):
    """
    Renders the floating holographic Apple Vision Pro-style wrist quick-dock
    with 3D multi-tier cast drop shadows and beveled floating action buttons.
    """
    if not hand["is_left"]: return None
    wrist_x, wrist_y = hand["wrist"]
    if wrist_y < 100 or wrist_y > HEIGHT - 100: return None

    dock_center = (wrist_x - 75, wrist_y)
    dock_rect = pygame.Rect(dock_center[0] - 48, dock_center[1] - 145, 96, 290)

    # Holographic depth tether line
    pygame.draw.line(surf, (*UITheme.NEON_CYAN[:3], 90), (wrist_x, wrist_y), (dock_center[0] + 48, dock_center[1]), 2)
    pygame.draw.circle(surf, UITheme.NEON_CYAN, (wrist_x, wrist_y), 4)

    # 3D Glass Dock Card with Elevated Shadow
    NeonFX.draw_glass_card(surf, dock_rect, border_color=UITheme.NEON_CYAN, border_width=2, radius=22,
                           show_brackets=True, elevation=18, is_3d=True)

    buttons = [
        ("HUB",    "MENU",         UITheme.NEON_CYAN,   -105, "⌂"),
        ("BLADE",  "GAME_3",       UITheme.NEON_PINK,    -52, "⚡"),
        ("LIVE",   "ORCHESTRA",    UITheme.NEON_GOLD,      0, "𝄢"),
        ("TILES",  "GAME_2",       UITheme.NEON_GREEN,    52, "♪"),
        ("STAR",   "GAME_5",       UITheme.NEON_PURPLE,  105, "★")
    ]

    selected_state = None
    right_fingertips = []
    for h in other_hands:
        if not h["is_left"]:
            right_fingertips.append((h["lead_tip"], h["is_pinching"]))

    for lbl, state_target, col, y_off, icon in buttons:
        btn_center = (dock_center[0], dock_center[1] + y_off)
        btn_rect = pygame.Rect(btn_center[0] - 22, btn_center[1] - 20, 44, 40)
        
        is_hovered = any(btn_rect.collidepoint(fx, fy) for (fx, fy), _ in right_fingertips)
        for (fx, fy), is_pinch in right_fingertips:
            if btn_rect.collidepoint(fx, fy) and is_pinch:
                selected_state = state_target

        is_active = (app_state == state_target)
        
        # 3D Floating Button Shadow
        ShadowEngine.draw_projected_ground_shadow(surf, btn_center[0], btn_center[1] + 6, 22, 10, alpha=130)

        if is_active or is_hovered:
            NeonFX.draw_glow_circle(surf, col, btn_center, 18, glow_size=14, max_alpha=180)
            pygame.draw.circle(surf, col, btn_center, 18)
            pygame.draw.circle(surf, UITheme.PURE_WHITE, btn_center, 18, 2)
            pygame.draw.circle(surf, (255, 255, 255, 180), (btn_center[0] - 3, btn_center[1] - 4), 3)
            t = font_sm.render(lbl, True, UITheme.VOID_BLACK)
        else:
            pygame.draw.circle(surf, (16, 22, 38), btn_center, 16)
            pygame.draw.circle(surf, col, btn_center, 16, 1)
            pygame.draw.arc(surf, UITheme.GLASS_HIGHLIGHT, (btn_center[0] - 16, btn_center[1] - 16, 32, 32), 0.7, 2.4, 2)
            t = font_sm.render(lbl, True, UITheme.PURE_WHITE)

        surf.blit(t, (btn_center[0] - t.get_width() // 2, btn_center[1] - t.get_height() // 2))

    return selected_state

# ==================================================================================================
# 14. SCENE TRANSITION ENGINE & 3D PARTICLE / COSMIC VISUAL FX PIPELINE
# ==================================================================================================
class SceneTransitionEngine:
    def __init__(self):
        self.alpha = 0.0
        self.fade_speed = 5.0
        self.is_transitioning = False
        self.target_state = None
        self.on_switch_callback = None
        self.fade_surface = pygame.Surface((WIDTH, HEIGHT))
        self.fade_surface.fill(UITheme.VOID_BLACK)

    def change_scene(self, target_state, on_switch=None):
        if not self.is_transitioning:
            self.is_transitioning = True
            self.target_state = target_state
            self.on_switch_callback = on_switch
            self.alpha = 0.0

    def update(self, dt, app):
        if not self.is_transitioning:
            return

        if self.target_state is not None:
            self.alpha = min(255.0, self.alpha + 255.0 * self.fade_speed * dt)
            if self.alpha >= 255.0:
                app.app_state = self.target_state
                if self.on_switch_callback:
                    self.on_switch_callback()
                self.target_state = None
        else:
            self.alpha = max(0.0, self.alpha - 255.0 * self.fade_speed * dt)
            if self.alpha <= 0.0:
                self.is_transitioning = False

    def draw(self, surf):
        if self.alpha > 1.0:
            self.fade_surface.set_alpha(int(self.alpha))
            surf.blit(self.fade_surface, (0, 0))

class Particle:
    def __init__(self, x, y, color, vx, vy, life=0.65, size=4.5, is_note=False, note_char="♪", z_elev=0.0):
        self.x, self.y = float(x), float(y)
        self.color, self.vx, self.vy = color, vx, vy
        self.life, self.max_life = life, life
        self.size = size
        self.is_note = is_note
        self.note_char = note_char
        self.z_elev = z_elev

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z_elev += 24.0 * dt
        self.life = max(0.0, self.life - dt)

    def draw(self, surf, font):
        if self.life > 0:
            ratio = self.life / self.max_life
            
            # Ground contact shadow for elevated sparks
            if not self.is_note:
                s_size = max(1, int(self.size * ratio * 0.8))
                shd_surf = pygame.Surface((s_size * 2, s_size), pygame.SRCALPHA)
                pygame.draw.ellipse(shd_surf, (0, 0, 0, int(80 * ratio)), (0, 0, s_size * 2, s_size))
                surf.blit(shd_surf, (int(self.x - s_size), int(self.y + self.z_elev * 0.4)))

            if self.is_note:
                # 3D Note with drop shadow
                t_shadow = font.render(self.note_char, True, (0, 0, 0))
                t_shadow.set_alpha(int(140 * ratio))
                surf.blit(t_shadow, (int(self.x + 2), int(self.y + 2)))

                t_surf = font.render(self.note_char, True, self.color)
                t_surf.set_alpha(int(255 * ratio))
                surf.blit(t_surf, (int(self.x), int(self.y)))
            else:
                sz = max(1, int(self.size * ratio))
                p_surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*self.color[:3], int(255 * ratio)), (sz, sz), sz)
                pygame.draw.circle(p_surf, (255, 255, 255, int(180 * ratio)), (sz - sz // 3, sz - sz // 3), max(1, sz // 2))
                surf.blit(p_surf, (int(self.x - sz), int(self.y - sz)))

class StageMote:
    def __init__(self):
        self.x = random.uniform(50, WIDTH - 50)
        self.y = random.uniform(80, HEIGHT - 80)
        self.z_depth = random.uniform(0.5, 1.8)
        self.vx = random.uniform(-15, 15) * self.z_depth
        self.vy = random.uniform(-25, -5) * self.z_depth
        self.alpha = random.uniform(40, 160)
        self.size = random.uniform(1.5, 3.5) * self.z_depth

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < 60:
            self.y = HEIGHT - 60
            self.x = random.uniform(50, WIDTH - 50)

    def draw(self, surf):
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 240, 180, int(self.alpha)), (int(self.size), int(self.size)), int(self.size))
        surf.blit(s, (int(self.x), int(self.y)))

class VisualFXEngine:
    def __init__(self):
        self.particles = []
        self.motes = [StageMote() for _ in range(45)]
        self.shake_duration = 0.0
        self.shake_intensity = 0.0

    def trigger_shake(self, dur=0.2, intensity=6.0):
        self.shake_duration, self.shake_intensity = dur, intensity

    def get_shake_offset(self):
        if self.shake_duration > 0:
            return int(random.uniform(-self.shake_intensity, self.shake_intensity)), int(random.uniform(-self.shake_intensity, self.shake_intensity))
        return (0, 0)

    def burst(self, x, y, color, count=16, with_notes=True):
        for _ in range(count):
            a = random.uniform(0, 2 * math.pi)
            spd = random.uniform(80, 320)
            self.particles.append(Particle(
                x, y, color, math.cos(a) * spd, math.sin(a) * spd,
                random.uniform(0.35, 0.75), random.uniform(3.0, 6.0)
            ))
        if with_notes:
            for _ in range(3):
                self.particles.append(Particle(
                    x, y, UITheme.NEON_GOLD, random.uniform(-40, 40), random.uniform(-130, -50),
                    random.uniform(0.6, 1.0), 14, is_note=True, note_char=random.choice(["♪", "♫", "♩", "𝄢", "𝄞"])
                ))

    def update(self, dt):
        if self.shake_duration > 0:
            self.shake_duration = max(0.0, self.shake_duration - dt)
        for p in self.particles: p.update(dt)
        for m in self.motes: m.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, surf, font):
        for m in self.motes: m.draw(surf)
        for p in self.particles: p.draw(surf, font)

class CosmicVisualizer:
    def __init__(self):
        self.ripples = []
        self.shockwaves = []

    def trigger_note_ripple(self, x, y, color):
        self.ripples.append({"x": x, "y": y, "radius": 8.0, "max_r": 180.0, "color": color, "alpha": 255})

    def trigger_drum_shockwave(self, x, y):
        self.shockwaves.append({"x": x, "y": y, "radius": 20.0, "alpha": 255})

    def update(self, dt):
        for r in self.ripples:
            r["radius"] += 280.0 * dt
            r["alpha"] = max(0, int(255 * (1.0 - (r["radius"] / r["max_r"]))))
        self.ripples = [r for r in self.ripples if r["alpha"] > 0]

        for sw in self.shockwaves:
            sw["radius"] += 450.0 * dt
            sw["alpha"] = max(0, int(255 * (1.0 - (sw["radius"] / 320.0))))
        self.shockwaves = [sw for sw in self.shockwaves if sw["alpha"] > 0]

    def draw(self, surf):
        # 3D Depth Rings with drop shadow underlays
        for r in self.ripples:
            # Shadow underlay
            shd_surf = pygame.Surface((int(r["radius"] * 2 + 8), int(r["radius"] * 2 + 8)), pygame.SRCALPHA)
            pygame.draw.circle(shd_surf, (0, 0, 0, int(r["alpha"] * 0.4)), (int(r["radius"] + 4), int(r["radius"] + 4)), int(r["radius"]), 3)
            surf.blit(shd_surf, (int(r["x"] - r["radius"] - 2), int(r["y"] - r["radius"] + 3)))

            r_surf = pygame.Surface((int(r["radius"] * 2), int(r["radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(r_surf, (*r["color"][:3], r["alpha"]), (int(r["radius"]), int(r["radius"])), int(r["radius"]), 2)
            surf.blit(r_surf, (int(r["x"] - r["radius"]), int(r["y"] - r["radius"])))

        for sw in self.shockwaves:
            s_surf = pygame.Surface((int(sw["radius"] * 2), int(sw["radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (255, 255, 255, sw["alpha"]), (int(sw["radius"]), int(sw["radius"])), int(sw["radius"]), 3)
            surf.blit(s_surf, (int(sw["x"] - sw["radius"]), int(sw["y"] - sw["radius"])))

# ==================================================================================================
# 15. ANIMATED CONCERT HALL CHARACTER MUSICIANS & CHOIR
# ==================================================================================================
class MusicianCharacter:
    def __init__(self, x, y, section, inst_type, skin_col, hair_col, name="Orchestra Member", scale=1.0):
        self.base_x, self.base_y = x, y
        self.section = section
        self.inst_type = inst_type
        self.skin_col = skin_col
        self.hair_col = hair_col
        self.name = name
        self.scale = scale
        self.stand_ratio = 0.0
        self.anim_phase = random.uniform(0, math.pi * 2)

    def update(self, is_active, volume, dt):
        target_stand = 1.0 if (is_active and volume > 0.10) else 0.0
        self.stand_ratio += (target_stand - self.stand_ratio) * 6.0 * dt
        if is_active and volume > 0.05:
            self.anim_phase += (6.0 + volume * 10.0) * dt
        else:
            self.anim_phase += 1.5 * dt

    def draw(self, surf, is_active, volume):
        curr_y = self.base_y - int(16 * self.stand_ratio)
        cx = self.base_x
        t = self.anim_phase

        # Stage contact realistic ambient cast shadow
        shadow_w = int(36 * self.scale)
        shadow_h = int(12 * self.scale)
        ShadowEngine.draw_projected_ground_shadow(surf, cx, self.base_y + 16, shadow_w, shadow_h, alpha=160)

        if is_active and volume > 0.08:
            glow_r = int((44 + math.sin(t * 2.0) * 4) * self.scale)
            col_map = {
                "STRINGS": UITheme.NEON_CYAN,
                "WOODWINDS": UITheme.NEON_GREEN,
                "BRASS": UITheme.NEON_ORANGE,
                "CHOIR": UITheme.NEON_PINK
            }
            color_active = col_map.get(self.section, UITheme.NEON_GOLD)
            NeonFX.draw_glow_circle(surf, color_active, (cx, curr_y), glow_r, glow_size=18, max_alpha=int(85 * volume))

        body_w = int(22 * self.scale)
        body_h = int(34 * self.scale)

        # 3D Depth Underlay for body
        pygame.draw.rect(surf, (10, 10, 14), (cx - body_w // 2 + 2, curr_y - 6, body_w, body_h), border_radius=8)

        if self.section == "CHOIR":
            pygame.draw.polygon(surf, UITheme.CHOIR_ROBE, [
                (cx - body_w // 2 - 4, curr_y + body_h),
                (cx + body_w // 2 + 4, curr_y + body_h),
                (cx + body_w // 2, curr_y - 8),
                (cx - body_w // 2, curr_y - 8)
            ])
            pygame.draw.line(surf, UITheme.CHOIR_GOLD, (cx - 4, curr_y - 6), (cx - 4, curr_y + body_h - 6), 3)
            pygame.draw.line(surf, UITheme.CHOIR_GOLD, (cx + 4, curr_y - 6), (cx + 4, curr_y + body_h - 6), 3)
        else:
            pygame.draw.rect(surf, (22, 22, 28), (cx - body_w // 2, curr_y - 8, body_w, body_h), border_radius=8)
            pygame.draw.polygon(surf, UITheme.PURE_WHITE, [(cx - 4, curr_y - 8), (cx + 4, curr_y - 8), (cx, curr_y)])

        head_r = int(12 * self.scale)
        head_y = curr_y - 18
        
        # 3D Head Ambient Shadow
        pygame.draw.circle(surf, (12, 12, 18), (cx + 1, head_y + 2), head_r)
        pygame.draw.circle(surf, self.skin_col, (cx, head_y), head_r)
        pygame.draw.arc(surf, self.hair_col, (cx - head_r, head_y - head_r, head_r * 2, head_r * 2), 0, math.pi, int(6 * self.scale))
        pygame.draw.circle(surf, (20, 15, 20), (cx - 4, head_y + 1), 2)
        pygame.draw.circle(surf, (20, 15, 20), (cx + 4, head_y + 1), 2)

        if self.section == "CHOIR":
            mouth_open = int((3.0 + math.sin(t * 3.0) * 2.5) * self.scale) if is_active and volume > 0.08 else 2
            pygame.draw.ellipse(surf, (35, 10, 10), (cx - 3, head_y + 6, 6, max(2, mouth_open)))
            hymn_y = curr_y + 6 + int(math.sin(t * 1.5) * 2)
            pygame.draw.rect(surf, (30, 20, 18), (cx - 10, hymn_y, 20, 14), border_radius=2)
            pygame.draw.rect(surf, (240, 240, 235), (cx - 8, hymn_y + 2, 16, 10))

        elif self.inst_type == "VIOLIN":
            pygame.draw.ellipse(surf, (170, 85, 30), (cx - 16, curr_y - 10, 14, 20))
            bow_x = cx + int(math.sin(t) * 10)
            pygame.draw.line(surf, (230, 210, 160), (bow_x - 14, curr_y - 6), (bow_x + 8, curr_y + 4), 2)
        elif self.inst_type == "CELLO":
            pygame.draw.ellipse(surf, (150, 70, 25), (cx - 8, curr_y + 4, 16, 26))
            bow_x = cx + int(math.sin(t) * 8)
            pygame.draw.line(surf, (230, 210, 160), (bow_x - 12, curr_y + 12), (bow_x + 12, curr_y + 12), 2)
        elif self.inst_type == "FLUTE":
            flute_y = head_y + 4 + int(math.sin(t * 1.5) * 3)
            pygame.draw.line(surf, (215, 225, 235), (cx + 2, flute_y), (cx + 24, flute_y - 4), 3)
        elif self.inst_type == "TRUMPET":
            horn_elev = int(math.sin(t * 1.2) * 5)
            pygame.draw.polygon(surf, UITheme.NEON_GOLD, [
                (cx + 4, head_y + 2), (cx + 22, head_y - 6 - horn_elev), (cx + 26, head_y - 12 - horn_elev),
                (cx + 26, head_y + 2 - horn_elev), (cx + 22, head_y - 2 - horn_elev)
            ])
        elif self.inst_type == "TIMPANI":
            pygame.draw.ellipse(surf, (180, 100, 45), (cx - 24, curr_y + 8, 20, 16))
            pygame.draw.ellipse(surf, (180, 100, 45), (cx + 4, curr_y + 8, 20, 16))
            stick_l = head_y + 10 + int(math.sin(t * 2.0) * 8)
            stick_r = head_y + 10 + int(math.cos(t * 2.0) * 8)
            pygame.draw.line(surf, UITheme.PURE_WHITE, (cx - 10, head_y + 6), (cx - 14, stick_l), 2)
            pygame.draw.line(surf, UITheme.PURE_WHITE, (cx + 10, head_y + 6), (cx + 14, stick_r), 2)
        elif self.inst_type == "HARP":
            pygame.draw.arc(surf, UITheme.NEON_GOLD, (cx + 8, curr_y - 24, 24, 44), 0, math.pi * 1.6, 3)
            for h_i in range(4):
                pygame.draw.line(surf, UITheme.PURE_WHITE, (cx + 14 + h_i * 3, curr_y - 18), (cx + 14 + h_i * 3, curr_y + 14), 1)

        if self.section != "CHOIR":
            stand_x = cx + (4 if self.inst_type in ["FLUTE", "TRUMPET"] else -6)
            pygame.draw.line(surf, (20, 20, 26), (stand_x, curr_y + 8), (stand_x, curr_y + 26), 2)
            pygame.draw.polygon(surf, (25, 25, 34), [
                (stand_x - 10, curr_y - 2), (stand_x + 10, curr_y - 2),
                (stand_x + 8, curr_y + 8), (stand_x - 8, curr_y + 8)
            ])
            pygame.draw.rect(surf, (240, 240, 245), (stand_x - 7, curr_y, 14, 6))

# ==================================================================================================
# 16. FULLY ANIMATED 25-PIECE ORCHESTRA CONCERT STAGE
# ==================================================================================================
class AnimatedOrchestraStage:
    def __init__(self):
        self.musicians = [
            # Choir Section (Back Upper Tier)
            MusicianCharacter(380, 195, "CHOIR", "SOPRANO", (245, 210, 180), (60, 40, 30), name="Choir Soprano 1", scale=0.82),
            MusicianCharacter(470, 195, "CHOIR", "ALTO", (230, 190, 155), (30, 25, 20), name="Choir Alto 1", scale=0.82),
            MusicianCharacter(560, 195, "CHOIR", "TENOR", (210, 165, 135), (80, 45, 30), name="Choir Tenor Lead", scale=0.82),
            MusicianCharacter(650, 195, "CHOIR", "BASS", (240, 200, 170), (45, 35, 30), name="Choir Bass Lead", scale=0.82),
            MusicianCharacter(740, 195, "CHOIR", "ALTO", (225, 180, 145), (140, 70, 35), name="Choir Alto 2", scale=0.82),
            MusicianCharacter(830, 195, "CHOIR", "SOPRANO", (250, 215, 185), (50, 40, 35), name="Choir Soloist Soprano", scale=0.82),

            # Percussion & Heavy Brass Tier
            MusicianCharacter(280, 265, "BRASS", "TIMPANI", (235, 195, 160), (45, 35, 30), name="Percussion Virtuoso", scale=0.88),
            MusicianCharacter(470, 275, "WOODWINDS", "FLUTE", (240, 205, 175), (85, 50, 35), name="2nd Flutist", scale=0.88),
            MusicianCharacter(560, 280, "WOODWINDS", "FLUTE", (215, 165, 130), (35, 25, 20), name="Principal Oboe", scale=0.88),
            MusicianCharacter(660, 280, "BRASS", "TRUMPET", (245, 210, 180), (150, 80, 40), name="1st French Horn", scale=0.88),
            MusicianCharacter(750, 275, "BRASS", "TRUMPET", (225, 180, 145), (40, 30, 25), name="Principal Trumpeter", scale=0.88),
            MusicianCharacter(930, 265, "BRASS", "TIMPANI", (230, 190, 155), (65, 45, 30), name="Grand Cymbalist", scale=0.88),

            # Mid Strings & Woodwinds Tier
            MusicianCharacter(220, 335, "STRINGS", "VIOLIN", (225, 185, 150), (40, 30, 35), name="2nd Violinist", scale=0.96),
            MusicianCharacter(310, 348, "STRINGS", "CELLO", (235, 195, 165), (75, 45, 30), name="Cellist Section Lead", scale=0.96),
            MusicianCharacter(530, 358, "WOODWINDS", "FLUTE", (245, 210, 180), (30, 25, 25), name="Concert Flutist", scale=0.96),
            MusicianCharacter(610, 358, "WOODWINDS", "FLUTE", (215, 165, 130), (55, 35, 25), name="Clarinet Virtuoso", scale=0.96),
            MusicianCharacter(690, 358, "WOODWINDS", "FLUTE", (235, 195, 160), (120, 60, 35), name="Bassoonist", scale=0.96),
            MusicianCharacter(910, 348, "BRASS", "TRUMPET", (240, 200, 170), (50, 40, 35), name="Trombonist", scale=0.96),
            MusicianCharacter(1000, 335, "BRASS", "TRUMPET", (220, 170, 135), (30, 20, 20), name="Brass Soloist", scale=0.96),

            # Front Principal Virtuoso Tier
            MusicianCharacter(180, 415, "STRINGS", "VIOLIN", (235, 195, 160), (60, 40, 25), name="Concertmaster Violin", scale=1.06),
            MusicianCharacter(260, 435, "STRINGS", "VIOLIN", (210, 160, 130), (35, 25, 20), name="1st Violin Assistant", scale=1.06),
            MusicianCharacter(340, 450, "STRINGS", "CELLO", (245, 210, 180), (140, 60, 30), name="Principal Violoncello", scale=1.06),
            MusicianCharacter(880, 450, "STRINGS", "CELLO", (220, 175, 140), (45, 30, 25), name="Double Bass Virtuoso", scale=1.06),
            MusicianCharacter(960, 435, "STRINGS", "VIOLIN", (240, 205, 175), (80, 50, 30), name="Viola Concert Soloist", scale=1.06),
            MusicianCharacter(1040, 415, "STRINGS", "HARP", (230, 190, 150), (160, 110, 50), name="Master Harpist", scale=1.06),
        ]

    def update(self, director, dt):
        for m in self.musicians:
            active = False
            vol = 0.0
            if m.section == "STRINGS": active, vol = director.strings_active, director.strings_vol
            elif m.section == "WOODWINDS": active, vol = director.woodwinds_active, director.woodwinds_vol
            elif m.section == "BRASS": active, vol = director.brass_active, director.brass_vol
            elif m.section == "CHOIR": active, vol = director.choir_active, director.choir_vol
            m.update(active, vol, dt)

    def draw(self, surf, director, hands):
        surf.fill(UITheme.STAGE_BACKDROP)

        # Ambient Sconces
        for sconce_x in [120, 360, 640, 920, 1160]:
            pygame.draw.rect(surf, (60, 35, 20), (sconce_x - 8, 70, 16, 28), border_radius=4)
            NeonFX.draw_glow_circle(surf, UITheme.NEON_GOLD, (sconce_x, 80), 6, glow_size=18, max_alpha=120)

        # Dynamic Volumetric Spotlights
        spot_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if director.choir_active and director.choir_vol > 0.05:
            alpha = int(55 * director.choir_vol)
            pygame.draw.polygon(spot_surf, (*UITheme.NEON_PINK[:3], alpha), [(640, 0), (300, HEIGHT), (980, HEIGHT)])
        if director.strings_active and director.strings_vol > 0.05:
            alpha = int(50 * director.strings_vol)
            pygame.draw.polygon(spot_surf, (*UITheme.NEON_CYAN[:3], alpha), [(260, 0), (40, HEIGHT), (560, HEIGHT)])
        if director.woodwinds_active and director.woodwinds_vol > 0.05:
            alpha = int(50 * director.woodwinds_vol)
            pygame.draw.polygon(spot_surf, (*UITheme.NEON_GREEN[:3], alpha), [(640, 0), (420, HEIGHT), (860, HEIGHT)])
        if director.brass_active and director.brass_vol > 0.05:
            alpha = int(50 * director.brass_vol)
            pygame.draw.polygon(spot_surf, (*UITheme.NEON_ORANGE[:3], alpha), [(1020, 0), (740, HEIGHT), (1240, HEIGHT)])
        surf.blit(spot_surf, (0, 0))

        # 3D Tiered Concert Risers with Drop Shadows and Bevel Light Rims
        center_stage = (WIDTH // 2, 700)
        tiers = [
            (620, 205, (95, 45, 15)),
            (550, 270, UITheme.STAGE_WOOD_DARK),
            (460, 340, UITheme.STAGE_WOOD),
            (370, 410, (215, 130, 38))
        ]
        for rad, y_offset, col in tiers:
            # 3D Depth Shadow on lower step
            pygame.draw.ellipse(surf, (20, 10, 6), (center_stage[0] - rad, y_offset + 12, rad * 2, 390))
            pygame.draw.ellipse(surf, col, (center_stage[0] - rad, y_offset, rad * 2, 390))
            # 3D Bevel Top Glint on Wooden Riser Lip
            pygame.draw.arc(surf, (255, 200, 120, 160), (center_stage[0] - rad, y_offset, rad * 2, 390), math.pi, math.pi * 2, 2)
            pygame.draw.arc(surf, (60, 25, 8), (center_stage[0] - rad, y_offset + 4, rad * 2, 390), math.pi, math.pi * 2, 4)

        # Draw Musicians Sorted by Y depth
        for m in sorted(self.musicians, key=lambda ch: ch.base_y):
            active = False
            vol = 0.0
            if m.section == "STRINGS": active, vol = director.strings_active, director.strings_vol
            elif m.section == "WOODWINDS": active, vol = director.woodwinds_active, director.woodwinds_vol
            elif m.section == "BRASS": active, vol = director.brass_active, director.brass_vol
            elif m.section == "CHOIR": active, vol = director.choir_active, director.choir_vol
            m.draw(surf, active, vol)

        # 3D Conductor Podium Base
        podium_rect = pygame.Rect(WIDTH // 2 - 70, HEIGHT - 180, 140, 65)
        NeonFX.draw_glass_card(surf, podium_rect, border_color=UITheme.NEON_GOLD, border_width=3, radius=12, elevation=16, is_3d=True)

        # Conductor Silhouette Body
        cond_x, cond_y = WIDTH // 2, HEIGHT - 145
        ShadowEngine.draw_projected_ground_shadow(surf, cond_x, cond_y + 24, 45, 16, alpha=160)
        pygame.draw.ellipse(surf, (15, 15, 20), (cond_x - 18, cond_y - 25, 36, 48))
        pygame.draw.circle(surf, (45, 30, 20), (cond_x, cond_y - 32), 16)

        # Conducting Baton Extension linked to right hand lead tip
        baton_target = (cond_x + 35, cond_y - 45)
        for h in hands:
            if not h["is_left"]:
                baton_target = (h["lead_tip"][0], h["lead_tip"][1])

        b_end = (baton_target[0] // 3 + cond_x - 160, baton_target[1] // 3 + 340)
        pygame.draw.line(surf, (20, 20, 25), (cond_x + 12, cond_y - 12), (cond_x + 28, cond_y - 24), 5)
        pygame.draw.line(surf, UITheme.NEON_GOLD, (cond_x + 28, cond_y - 24), b_end, 3)
        NeonFX.draw_glow_circle(surf, UITheme.NEON_GOLD, b_end, 4, glow_size=8, max_alpha=200)

# ==================================================================================================
# 17. CINEMATIC CAMERA DIRECTOR SYSTEM (FIXED WIDE STAGE VIEW)
# ==================================================================================================
class CameraDirector:
    def __init__(self):
        self.current_zoom = 1.0
        self.target_zoom = 1.0
        self.current_center = [WIDTH / 2.0, HEIGHT / 2.0]
        self.target_center = [WIDTH / 2.0, HEIGHT / 2.0]
        self.active_soloist = None
        self.close_up_timer = 0.0
        self.letterbox_anim = 0.0

    def trigger_solo_close_up(self, musician=None, duration=0.0):
        pass

    def reset_view(self):
        self.active_soloist = None

    def update(self, dt):
        pass

    def render_scene(self, target_surf, world_surf, font_sm=None, font_md=None):
        target_surf.blit(world_surf, (0, 0))

# ==================================================================================================
# 18. ORCHESTRA CONDUCTOR DIRECTOR ENGINE
# ==================================================================================================
class OrchestraConductorDirector:
    def __init__(self):
        self.strings_vol = 0.0
        self.woodwinds_vol = 0.0
        self.brass_vol = 0.0
        self.choir_vol = 0.0
        self.strings_active = False
        self.woodwinds_active = False
        self.brass_active = False
        self.choir_active = False
        
        self.master_dynamic = "ppp (Silence)"
        self.master_gain = 0.0
        self.bpm = 112.0
        self.beat_phase = 0.0
        self.current_beat = 1
        self.baton_prev_pos = None
        self.downbeat_cooldown = 0.0
        self.last_beat_time = time.time()
        self.applause_meter = 0.0
        self.ovation_active = False
        self.aimed_section = "NONE"

        CHAN_STRINGS_L.play(SOUND_STRINGS_LOW, loops=-1); CHAN_STRINGS_L.set_volume(0.0)
        CHAN_STRINGS_H.play(SOUND_STRINGS_HIGH, loops=-1); CHAN_STRINGS_H.set_volume(0.0)
        CHAN_WOODWINDS.play(SOUND_WOODWINDS, loops=-1); CHAN_WOODWINDS.set_volume(0.0)
        CHAN_BRASS.play(SOUND_BRASS, loops=-1); CHAN_BRASS.set_volume(0.0)
        CHAN_CHOIR.play(SOUND_CHOIR, loops=-1); CHAN_CHOIR.set_volume(0.0)

    def process_conductor(self, hands, vfx, camera, stage, dt):
        global audio_energy
        if self.downbeat_cooldown > 0.0:
            self.downbeat_cooldown = max(0.0, self.downbeat_cooldown - dt)

        beat_interval = 60.0 / max(40.0, self.bpm)
        self.beat_phase += dt / beat_interval
        if self.beat_phase >= 1.0:
            self.beat_phase -= 1.0
            self.current_beat = (self.current_beat % 4) + 1

        self.strings_active = False
        self.woodwinds_active = False
        self.brass_active = False
        self.choir_active = False
        self.aimed_section = "NONE"

        target_s = target_w = target_b = target_c = 0.0
        cutoff_triggered = False

        for h in hands:
            hx, hy = h["palm"]
            elev = np.clip(1.0 - ((hy - 80) / 480.0), 0.0, 1.0) ** 1.2

            if h["is_fist"]:
                cutoff_triggered = True
                continue

            if hx < 420:
                self.strings_active = True
                self.aimed_section = "STRINGS"
                target_s = max(target_s, elev)
            elif hx > 860:
                self.brass_active = True
                self.aimed_section = "BRASS"
                target_b = max(target_b, elev)
            else:
                if hy < 240:
                    self.choir_active = True
                    self.aimed_section = "CHOIR"
                    target_c = max(target_c, elev)
                else:
                    self.woodwinds_active = True
                    self.aimed_section = "WOODWINDS"
                    target_w = max(target_w, elev)

            if h["is_pinching"]:
                vfx.burst(hx, hy, UITheme.NEON_GOLD, count=20, with_notes=True)

            if not h["is_left"]:
                tip_x, tip_y = h["lead_tip"]
                if self.baton_prev_pos is not None:
                    dy = tip_y - self.baton_prev_pos[1]
                    speed = math.hypot(tip_x - self.baton_prev_pos[0], dy) / max(1e-3, dt)
                    
                    if dy > 36.0 and speed > 300.0 and self.downbeat_cooldown <= 0.0:
                        now = time.time()
                        measured_bpm = 60.0 / max(0.25, min(1.5, now - self.last_beat_time))
                        self.bpm = self.bpm * 0.65 + measured_bpm * 0.35
                        self.last_beat_time = now
                        self.downbeat_cooldown = 0.32

                        if hx > 860:
                            CHAN_TIMPANI.play(SOUND_TIMPANI)
                            vfx.burst(tip_x, tip_y, UITheme.NEON_ORANGE, count=22)
                        elif self.choir_active:
                            CHAN_TUTTI.play(SOUND_TUTTI)
                            vfx.burst(tip_x, tip_y, UITheme.NEON_PINK, count=28, with_notes=True)
                        else:
                            CHAN_TUTTI.play(SOUND_TUTTI)
                            vfx.burst(tip_x, tip_y, UITheme.NEON_GOLD, count=26, with_notes=True)

                        vfx.trigger_shake(0.18, 5.5)
                        audio_energy = min(1.0, audio_energy + 0.8)

                self.baton_prev_pos = (tip_x, tip_y)

        if len(hands) == 2 and not cutoff_triggered:
            p1, p2 = hands[0]["palm"], hands[1]["palm"]
            if p1[1] < 220 and p2[1] < 220:
                self.strings_active = self.woodwinds_active = self.brass_active = self.choir_active = True
                target_s = target_w = target_b = target_c = 1.0
                vfx.burst(WIDTH // 2, 190, UITheme.NEON_PINK, count=4, with_notes=True)

        if cutoff_triggered:
            target_s = target_w = target_b = target_c = 0.0
            camera.reset_view()

        if len(hands) == 0:
            self.baton_prev_pos = None

        rate = 5.5 * dt
        self.strings_vol += (target_s - self.strings_vol) * rate
        self.woodwinds_vol += (target_w - self.woodwinds_vol) * rate
        self.brass_vol += (target_b - self.brass_vol) * rate
        self.choir_vol += (target_c - self.choir_vol) * rate

        CHAN_STRINGS_L.set_volume(self.strings_vol * 0.9)
        CHAN_STRINGS_H.set_volume(self.strings_vol)
        CHAN_WOODWINDS.set_volume(self.woodwinds_vol)
        CHAN_BRASS.set_volume(self.brass_vol * 1.1)
        CHAN_CHOIR.set_volume(self.choir_vol * 1.25)

        max_v = max(self.strings_vol, self.woodwinds_vol, self.brass_vol, self.choir_vol)
        self.master_gain = max_v

        if max_v > 0.65:
            self.applause_meter = min(100.0, self.applause_meter + 22.0 * dt)
            if self.applause_meter > 85.0 and not self.ovation_active:
                self.ovation_active = True
                vfx.burst(random.randint(200, WIDTH - 200), random.randint(400, 600), UITheme.NEON_GOLD, count=35, with_notes=True)
        else:
            self.applause_meter = max(0.0, self.applause_meter - 12.0 * dt)
            if self.applause_meter < 30.0:
                self.ovation_active = False

        if cutoff_triggered: self.master_dynamic = "TACET (GENERAL PAUSE)"
        elif self.ovation_active: self.master_dynamic = "BRAVO! STANDING OVATION ★★★"
        elif max_v > 0.85: self.master_dynamic = "fff (GRAND CHOIR CRESCENDO)"
        elif max_v > 0.70: self.master_dynamic = "ff (Fortissimo)"
        elif max_v > 0.55: self.master_dynamic = "f (Forte)"
        elif max_v > 0.40: self.master_dynamic = "mf (Mezzo-Forte)"
        elif max_v > 0.25: self.master_dynamic = "mp (Mezzo-Piano)"
        elif max_v > 0.10: self.master_dynamic = "p (Piano)"
        else: self.master_dynamic = "ppp (Silence)"

    def draw_hud(self, surf, font_sm, font_md):
        pill_rect = pygame.Rect(WIDTH // 2 - 280, 16, 560, 48)
        NeonFX.draw_hud_pill(surf, pill_rect, border_color=UITheme.NEON_GOLD, radius=14, elevation=12)

        t_dyn = font_md.render(f"MAESTRO: {self.master_dynamic}", True, UITheme.NEON_GOLD)
        surf.blit(t_dyn, (WIDTH // 2 - t_dyn.get_width() // 2, 22))

        for b in range(4):
            bx = WIDTH // 2 - 60 + b * 40
            by = 54
            is_active_beat = (b + 1 == self.current_beat)
            col = UITheme.NEON_GREEN if is_active_beat else (40, 55, 80)
            pygame.draw.circle(surf, col, (bx, by), 5 if is_active_beat else 3)

        bpm_txt = font_sm.render(f"{int(self.bpm)} BPM", True, UITheme.NEON_CYAN)
        surf.blit(bpm_txt, (WIDTH // 2 + 115, 46))

        sections = [
            ("STRINGS", self.strings_vol, UITheme.NEON_CYAN, 120),
            ("WOODWINDS", self.woodwinds_vol, UITheme.NEON_GREEN, 250),
            ("CHOIR", self.choir_vol, UITheme.NEON_PINK, WIDTH - 250),
            ("BRASS", self.brass_vol, UITheme.NEON_ORANGE, WIDTH - 120)
        ]
        for name, vol, col, pos_x in sections:
            is_aimed = (self.aimed_section == name)
            s_rect = pygame.Rect(pos_x - 50, 18, 100, 36)
            NeonFX.draw_hud_pill(surf, s_rect, border_color=col if is_aimed else UITheme.GLASS_BORDER, radius=8, elevation=6)
            lbl = font_sm.render(name, True, col if is_aimed else UITheme.TEXT_MUTED)
            surf.blit(lbl, (pos_x - lbl.get_width() // 2, 22))
            
            pygame.draw.rect(surf, (14, 20, 32), (pos_x - 40, 42, 80, 4), border_radius=2)
            if vol > 0.05:
                pygame.draw.rect(surf, col, (pos_x - 40, 42, int(80 * vol), 4), border_radius=2)

# ==================================================================================================
# 19. 3D SPATIAL INTERACTION HUB ENGINE
# ==================================================================================================
class SpatialWindow:
    def __init__(self, title, desc, rect, color, tag="APP", target_state="MENU", stars=3, icon="STUDIO"):
        self.title = title
        self.desc = desc
        self.rect = pygame.Rect(rect)
        self.base_size = (self.rect.width, self.rect.height)
        self.color = color
        self.tag = tag
        self.target_state = target_state
        self.stars = stars
        self.icon = icon
        self.scale = 1.0
        
        self.is_dragged = False
        self.drag_offset = (0, 0)
        self.vx = 0.0
        self.vy = 0.0
        self.elev = 1.0

    def update_physics(self, dt):
        if not self.is_dragged:
            self.rect.x += int(self.vx * dt)
            self.rect.y += int(self.vy * dt)
            self.vx *= max(0.0, 1.0 - 5.0 * dt)
            self.vy *= max(0.0, 1.0 - 5.0 * dt)

            if self.rect.left < 20: self.rect.left = 20; self.vx *= -0.5
            if self.rect.right > WIDTH - 20: self.rect.right = WIDTH - 20; self.vx *= -0.5
            if self.rect.top < 80: self.rect.top = 80; self.vy *= -0.5
            if self.rect.bottom > HEIGHT - 70: self.rect.bottom = HEIGHT - 70; self.vy *= -0.5

        target_z = 1.25 if self.is_dragged else 1.0
        self.elev += (target_z - self.elev) * 10.0 * dt

    def draw(self, surf, font_sm, font_md):
        elevation_val = int(22 * self.elev)
        
        # 3D Glassmorphic Card Frame with Beveled Depth & Dynamic Shadow Elevation
        NeonFX.draw_glass_card(surf, self.rect, border_color=self.color, border_width=2, radius=20,
                               show_brackets=True, high_lum=self.is_dragged, elevation=elevation_val, is_3d=True)

        lbl = font_md.render(self.title, True, UITheme.PURE_WHITE)
        surf.blit(lbl, (self.rect.x + 16, self.rect.y + 16))
        
        tag_lbl = font_sm.render(f"[{self.tag}]", True, self.color)
        surf.blit(tag_lbl, (self.rect.right - tag_lbl.get_width() - 16, self.rect.y + 20))

        preview_box = pygame.Rect(self.rect.x + 16, self.rect.y + 50, self.rect.w - 32, 110)
        NeonFX.draw_glass_card(surf, preview_box, border_color=UITheme.GLASS_BORDER, border_width=1, radius=12,
                               show_brackets=False, elevation=6, is_3d=False)

        cx, cy = preview_box.center
        if self.icon == "STUDIO":
            for ki in range(5):
                # 3D Piano Key Previews with Soft Drop Shadows
                ShadowEngine.draw_projected_ground_shadow(surf, cx - 29 + ki * 15, cy + 22, 14, 6, alpha=100)
                pygame.draw.rect(surf, UITheme.PURE_WHITE, (cx - 35 + ki * 15, cy - 25, 12, 50), border_radius=2)
                pygame.draw.line(surf, (200, 210, 225), (cx - 35 + ki * 15 + 11, cy - 25), (cx - 35 + ki * 15 + 11, cy + 25), 1)
                if ki < 4:
                    pygame.draw.rect(surf, (12, 12, 18), (cx - 28 + ki * 15, cy - 25, 8, 30), border_radius=1)
        elif self.icon == "TILES":
            # 3D Perspective Mini-Highway Icon
            pts = [(cx - 22, cy - 28), (cx + 22, cy - 28), (cx + 42, cy + 32), (cx - 42, cy + 32)]
            pygame.draw.polygon(surf, (15, 20, 34), pts)
            pygame.draw.polygon(surf, (38, 55, 88), pts, 1)
            for li in range(4):
                lx = cx - 30 + li * 20
                pygame.draw.rect(surf, [UITheme.NEON_CYAN, UITheme.NEON_PURPLE, UITheme.NEON_PINK, UITheme.NEON_GREEN][li],
                                 (lx - 6, cy + 6 - li * 6, 14, 18), border_radius=3)
        elif self.icon == "BLADE":
            pygame.draw.line(surf, UITheme.NEON_ORANGE, (cx - 30, cy + 24), (cx - 5, cy - 24), 4)
            pygame.draw.line(surf, UITheme.NEON_PINK, (cx + 30, cy + 24), (cx + 5, cy - 24), 4)
            draw_star(surf, UITheme.PURE_WHITE, cx, cy, 6)
        elif self.icon == "ORBIT":
            pygame.draw.circle(surf, UITheme.NEON_PURPLE, (cx, cy), 28, 2)
            pygame.draw.circle(surf, UITheme.NEON_CYAN, (cx, cy), 14, 1)
            draw_star(surf, UITheme.NEON_GOLD, cx + 20, cy - 18, 9)

        for s_i in range(3):
            s_col = UITheme.NEON_GOLD if s_i < self.stars else (30, 42, 65)
            draw_star(surf, s_col, cx - 30 + s_i * 30, self.rect.y + 175, 11)

        d_lbl = font_sm.render(self.desc, True, UITheme.TEXT_MUTED)
        surf.blit(d_lbl, (self.rect.centerx - d_lbl.get_width() // 2, self.rect.y + 198))

        btn_rect = pygame.Rect(self.rect.x + 24, self.rect.bottom - 52, self.rect.w - 48, 32)
        # 3D Raised Pill Button with Cast Shadow
        ShadowEngine.blit_drop_shadow(surf, btn_rect, radius=16, elevation=8)
        pygame.draw.rect(surf, self.color, btn_rect, border_radius=16)
        pygame.draw.line(surf, UITheme.GLASS_HIGHLIGHT, (btn_rect.x + 16, btn_rect.y + 2), (btn_rect.right - 16, btn_rect.y + 2), 2)
        pygame.draw.line(surf, (0, 0, 0, 80), (btn_rect.x + 16, btn_rect.bottom - 2), (btn_rect.right - 16, btn_rect.bottom - 2), 2)
        
        btn_txt = font_sm.render("PINCH / CLICK TO PLAY", True, UITheme.VOID_BLACK)
        surf.blit(btn_txt, (btn_rect.centerx - btn_txt.get_width() // 2, btn_rect.centery - btn_txt.get_height() // 2))

class SpatialGestureManager:
    def __init__(self):
        self.dragged_window = None
        self.prev_pinch_pos = None
        self.two_hand_init_dist = None
        self.two_hand_init_scale = 1.0
        self.pinch_start_pos = None
        self.pinch_start_time = 0.0

    def process_gestures(self, windows, hands, dt):
        clicked_state = None

        if not hands:
            if self.dragged_window:
                self.dragged_window.is_dragged = False
                self.dragged_window = None
            self.two_hand_init_dist = None
            self.prev_pinch_pos = None
            return None

        if len(hands) == 2 and hands[0]["is_pinching"] and hands[1]["is_pinching"]:
            p1, p2 = hands[0]["palm"], hands[1]["palm"]
            curr_dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            mid_x, mid_y = (p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2
            
            target_win = next((w for w in reversed(windows) if w.rect.collidepoint(mid_x, mid_y)), None)
            if target_win:
                if self.two_hand_init_dist is None:
                    self.two_hand_init_dist = curr_dist
                    self.two_hand_init_scale = target_win.scale
                else:
                    scale_factor = curr_dist / max(1.0, self.two_hand_init_dist)
                    new_scale = np.clip(self.two_hand_init_scale * scale_factor, 0.7, 1.6)
                    target_win.scale = new_scale
                    nw, nh = int(target_win.base_size[0] * new_scale), int(target_win.base_size[1] * new_scale)
                    cx, cy = target_win.rect.center
                    target_win.rect = pygame.Rect(cx - nw // 2, cy - nh // 2, nw, nh)
            return None
        else:
            self.two_hand_init_dist = None

        pinching_hands = [h for h in hands if h["is_pinching"]]
        if pinching_hands:
            h = pinching_hands[0]
            pinch_x = (h["landmarks"][4][0] + h["landmarks"][8][0]) // 2
            pinch_y = (h["landmarks"][4][1] + h["landmarks"][8][1]) // 2

            if self.dragged_window is None:
                for w in reversed(windows):
                    if w.rect.collidepoint(pinch_x, pinch_y):
                        self.dragged_window = w
                        w.is_dragged = True
                        w.drag_offset = (w.rect.x - pinch_x, w.rect.y - pinch_y)
                        self.prev_pinch_pos = (pinch_x, pinch_y)
                        self.pinch_start_pos = (pinch_x, pinch_y)
                        self.pinch_start_time = time.time()
                        windows.remove(w)
                        windows.append(w)
                        break
            else:
                w = self.dragged_window
                target_x = pinch_x + w.drag_offset[0]
                target_y = pinch_y + w.drag_offset[1]
                if self.prev_pinch_pos:
                    w.vx = (pinch_x - self.prev_pinch_pos[0]) / max(1e-3, dt)
                    w.vy = (pinch_y - self.prev_pinch_pos[1]) / max(1e-3, dt)
                w.rect.x = target_x
                w.rect.y = target_y
                self.prev_pinch_pos = (pinch_x, pinch_y)
        else:
            if self.dragged_window:
                if self.pinch_start_pos and self.prev_pinch_pos:
                    dist_moved = math.hypot(self.prev_pinch_pos[0] - self.pinch_start_pos[0], 
                                            self.prev_pinch_pos[1] - self.pinch_start_pos[1])
                    elapsed = time.time() - self.pinch_start_time
                    if dist_moved < 18.0 and elapsed < 0.45:
                        clicked_state = self.dragged_window.target_state

                self.dragged_window.is_dragged = False
                self.dragged_window = None
            self.prev_pinch_pos = None
            self.pinch_start_pos = None

        return clicked_state

# ==================================================================================================
# 20. 3D PHYSICAL INSTRUMENT INTERACTION CONTROLLERS
# ==================================================================================================
class PhysicalPianoKey:
    def __init__(self, index, x, y, width, height, note_name, is_black=False):
        self.index, self.rect, self.note_name, self.is_black = index, pygame.Rect(x, y, width, height), note_name, is_black
        self.glow, self.hovered, self.pressed_fingers = 0.0, False, set()
        self.depressed_y = 0.0

    def check_interaction(self, f_id, fx, fy, vy, is_distant, vfx, cosmic_vfx=None):
        global audio_energy
        hitbox = self.rect.inflate(20, 36) if is_distant else self.rect
        if hitbox.collidepoint(fx, fy):
            self.hovered = True
            strike_threshold = 4.8 if is_distant else 7.5
            if (vy > strike_threshold or is_distant) and (f_id not in self.pressed_fingers):
                self.pressed_fingers.add(f_id)
                self.glow, audio_energy = 1.0, min(1.0, audio_energy + 0.35)
                self.depressed_y = 8.0
                col = UITheme.NEON_GOLD if self.is_black else UITheme.NEON_CYAN
                vfx.burst(fx, fy, col, count=14)
                if cosmic_vfx: cosmic_vfx.trigger_note_ripple(fx, fy, col)
                if self.is_black and PIANO_BLACK_BANK[self.index]: PIANO_BLACK_BANK[self.index].play()
                else: PIANO_WHITE_BANK[self.index].play()
                return True
        else:
            if f_id in self.pressed_fingers: self.pressed_fingers.remove(f_id)
        return False

    def update(self, dt):
        if self.glow > 0.0: self.glow = max(0.0, self.glow - 2.8 * dt)
        if self.depressed_y > 0.0: self.depressed_y = max(0.0, self.depressed_y - 24.0 * dt)

    def draw(self, surf, font):
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + int(self.depressed_y), self.rect.width, self.rect.height)
        
        # 3D Soft Drop Shadow Behind Keys
        ShadowEngine.blit_drop_shadow(surf, draw_rect, radius=8, elevation=10 if not self.is_black else 6)

        if self.is_black:
            # 3D Extruded Black Key Body
            ext_rect = pygame.Rect(draw_rect.x, draw_rect.y + 6, draw_rect.width, draw_rect.height)
            pygame.draw.rect(surf, (8, 10, 16), ext_rect, border_radius=8)

            col = UITheme.PURE_WHITE if self.glow > 0.2 else (22, 26, 38)
            border_col = UITheme.NEON_GOLD if self.glow > 0.1 else (50, 65, 95)
            pygame.draw.rect(surf, col, draw_rect, border_radius=8)
            pygame.draw.rect(surf, border_col, draw_rect, 2, border_radius=8)
            
            # Specular Top Highlight
            pygame.draw.line(surf, UITheme.GLASS_HIGHLIGHT, (draw_rect.x + 4, draw_rect.y + 2), (draw_rect.right - 4, draw_rect.y + 2), 2)
        else:
            # 3D Extruded White Key Body
            ext_rect = pygame.Rect(draw_rect.x, draw_rect.y + 8, draw_rect.width, draw_rect.height)
            pygame.draw.rect(surf, (150, 165, 195), ext_rect, border_radius=10)

            col = UITheme.PURE_WHITE if self.glow > 0.3 else (235, 240, 250)
            border_col = UITheme.NEON_CYAN if self.glow > 0.1 else (100, 120, 160)
            pygame.draw.rect(surf, col, draw_rect, border_radius=10)
            pygame.draw.rect(surf, border_col, draw_rect, 2, border_radius=10)
            
            # 3D Bevel Top Glint & Bottom Lip Shadow
            pygame.draw.line(surf, (255, 255, 255), (draw_rect.x + 6, draw_rect.y + 2), (draw_rect.right - 6, draw_rect.y + 2), 2)
            pygame.draw.line(surf, (180, 195, 215), (draw_rect.x + 6, draw_rect.bottom - 4), (draw_rect.right - 6, draw_rect.bottom - 4), 3)

            lbl = font.render(self.note_name, True, UITheme.VOID_BLACK)
            surf.blit(lbl, (draw_rect.centerx - lbl.get_width() // 2, draw_rect.bottom - 32))

class PhysicalHoverPad:
    def __init__(self, index, x, y, width, height, note_name, sound_bank, base_color):
        self.index, self.rect, self.note_name = index, pygame.Rect(x, y, width, height), note_name
        self.sound_bank, self.base_color = sound_bank, base_color
        self.glow, self.hovered, self.cooldown = 0.0, False, 0.0

    def check_hover(self, fx, fy, is_distant, vfx, cosmic_vfx=None):
        global audio_energy
        hitbox = self.rect.inflate(24, 24) if is_distant else self.rect
        if hitbox.collidepoint(fx, fy):
            self.hovered = True
            if self.cooldown <= 0.0:
                self.glow, self.cooldown, audio_energy = 1.0, 0.34, min(1.0, audio_energy + 0.35)
                vfx.burst(fx, fy, self.base_color, count=14, with_notes=True)
                if cosmic_vfx: cosmic_vfx.trigger_note_ripple(fx, fy, self.base_color)
                self.sound_bank[self.index].play()
                return True
        return False

    def update(self, dt):
        if self.cooldown > 0.0: self.cooldown = max(0.0, self.cooldown - dt)
        if self.glow > 0.0: self.glow = max(0.0, self.glow - 2.5 * dt)

    def draw(self, surf, font):
        b_col = UITheme.PURE_WHITE if self.hovered else self.base_color
        elev = 14 if self.hovered else 8
        NeonFX.draw_glass_card(surf, self.rect, border_color=b_col, border_width=3 if self.hovered else 2,
                               radius=16, elevation=elev, is_3d=True)
        if self.glow > 0.2:
            NeonFX.draw_glow_circle(surf, self.base_color, self.rect.center, 30, glow_size=20, max_alpha=160)
        lbl = font.render(self.note_name, True, UITheme.PURE_WHITE)
        surf.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.centery - 10))

class PhysicalGuitarString:
    def __init__(self, index, x, note_name):
        self.index, self.x, self.note_name = index, x, note_name
        self.oscillation, self.glow = 0.0, 0.0

    def check_strum(self, prev_x, curr_x, speed, is_distant, vfx, cosmic_vfx=None):
        global audio_energy
        hit_range = 14 if is_distant else 8
        if prev_x is not None and (min(prev_x, curr_x) - hit_range) <= self.x <= (max(prev_x, curr_x) + hit_range) and speed > 6.0:
            self.oscillation, self.glow, audio_energy = 28.0, 1.0, min(1.0, audio_energy + 0.3)
            vfx.burst(self.x, HEIGHT // 2, UITheme.NEON_ORANGE, count=12)
            if cosmic_vfx: cosmic_vfx.trigger_note_ripple(self.x, HEIGHT // 2, UITheme.NEON_ORANGE)
            GUITAR_BANK[self.index].play()
            return True
        return False

    def update(self, dt):
        if self.oscillation > 0.0: self.oscillation = max(0.0, self.oscillation - 44.0 * dt)
        if self.glow > 0.0: self.glow = max(0.0, self.glow - 2.5 * dt)

    def draw(self, surf, font):
        osc = math.sin(pygame.time.get_ticks() * 0.06) * self.oscillation
        col = UITheme.PURE_WHITE if self.glow > 0.4 else UITheme.NEON_ORANGE
        
        # 3D Depth Shadow Behind String
        pygame.draw.line(surf, (0, 0, 0, 130), (int(self.x + 5), 140), (int(self.x + osc + 5), HEIGHT // 2), 4)
        pygame.draw.line(surf, (0, 0, 0, 130), (int(self.x + osc + 5), HEIGHT // 2), (int(self.x + 5), HEIGHT - 100), 4)

        pygame.draw.line(surf, col, (int(self.x), 140), (int(self.x + osc), HEIGHT // 2), max(3, int(3 + self.glow * 4)))
        pygame.draw.line(surf, col, (int(self.x + osc), HEIGHT // 2), (int(self.x), HEIGHT - 100), max(3, int(3 + self.glow * 4)))
        lbl = font.render(self.note_name, True, UITheme.NEON_ORANGE)
        surf.blit(lbl, (self.x - lbl.get_width() // 2, HEIGHT - 90))

class PhysicalDrumPad:
    def __init__(self, x, y, radius, label, drum_key, color):
        self.x, self.y, self.radius, self.label, self.drum_key, self.color = x, y, radius, label, drum_key, color
        self.glow, self.hovered, self.pressed_fingers = 0.0, False, set()

    def check_interaction(self, f_id, fx, fy, vy, is_distant, vfx, cosmic_vfx=None):
        global audio_energy
        reach = (self.radius + 32) if is_distant else (self.radius + 16)
        if math.hypot(self.x - fx, self.y - fy) < reach:
            self.hovered = True
            strike_threshold = 4.8 if is_distant else 7.5
            if (vy > strike_threshold or is_distant) and (f_id not in self.pressed_fingers):
                self.pressed_fingers.add(f_id)
                self.glow, audio_energy = 1.0, min(1.0, audio_energy + 0.45)
                vfx.burst(self.x, self.y, self.color, count=18)
                vfx.trigger_shake(0.15, 4.0)
                if cosmic_vfx: cosmic_vfx.trigger_drum_shockwave(self.x, self.y)
                DRUM_BANK[self.drum_key].play()
                return True
        else:
            if f_id in self.pressed_fingers: self.pressed_fingers.remove(f_id)
        return False

    def update(self, dt):
        if self.glow > 0.0: self.glow = max(0.0, self.glow - 3.2 * dt)

    def draw(self, surf, font):
        r = int(self.radius + self.glow * 10)
        
        # 3D Ground Cast Shadow
        ShadowEngine.draw_projected_ground_shadow(surf, self.x, self.y + 12, r * 2, int(r * 0.9), alpha=140)

        # 3D Cylindrical Drum Rim
        pygame.draw.circle(surf, (10, 14, 22), (self.x, self.y + 8), r)
        pygame.draw.circle(surf, (28, 38, 56), (self.x, self.y + 8), r, 3)

        NeonFX.draw_glow_circle(surf, self.color, (self.x, self.y), r, glow_size=16, max_alpha=160 if self.glow > 0.2 else 80)
        pygame.draw.circle(surf, (14, 20, 34), (self.x, self.y), r)
        pygame.draw.circle(surf, self.color, (self.x, self.y), r, 3)
        pygame.draw.circle(surf, self.color, (self.x, self.y), int(r * 0.35))
        lbl = font.render(self.label, True, UITheme.PURE_WHITE)
        surf.blit(lbl, (self.x - lbl.get_width() // 2, self.y - 10))

# ==================================================================================================
# 21. GAME 1: FREESTYLE STUDIO MANAGER
# ==================================================================================================
class FreestyleStudioManager:
    def __init__(self):
        self.instruments_meta = [
            {"title": "CONCERT GRAND PIANO", "type": "STRIKE", "tag": "STEINWAY", "stars": 3, "color": UITheme.NEON_CYAN},
            {"title": "BRASS TRUMPET", "type": "HOVER", "tag": "BRASS", "stars": 2, "color": UITheme.NEON_GOLD},
            {"title": "ALTO SAXOPHONE", "type": "HOVER", "tag": "WOODWIND", "stars": 2, "color": UITheme.NEON_ORANGE},
            {"title": "CONCERT HARP", "type": "HOVER", "tag": "PLUCK", "stars": 3, "color": UITheme.NEON_CYAN},
            {"title": "ACOUSTIC GUITAR", "type": "STRUM", "tag": "STRUM", "stars": 2, "color": UITheme.NEON_ORANGE},
            {"title": "CLASSICAL VIOLA", "type": "HOVER", "tag": "BOWED", "stars": 2, "color": UITheme.NEON_PURPLE},
            {"title": "808 CYBER DRUMS", "type": "STRIKE", "tag": "PERCUSSION", "stars": 1, "color": UITheme.NEON_PINK}
        ]
        self.current_inst_index = 0

        piano_w = 84
        start_x = (WIDTH - (piano_w * 12 + 11 * 6)) // 2
        w_labels = ["C3", "D3", "E3", "F3", "G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4"]
        self.white_keys = [PhysicalPianoKey(i, start_x + i * (piano_w + 6), 260, piano_w, 340, w_labels[i]) for i in range(12)]
        self.black_keys = [PhysicalPianoKey(i, start_x + i * (piano_w + 6) + (piano_w - 24), 260, 48, 200, "#", True) for i in range(11) if PIANO_BLACK_FREQS[i]]

        self.trumpet_pads = [PhysicalHoverPad(i, 200 + (i % 4) * 220, 240 + (i // 4) * 160, 180, 110, f"VALVE {i+1} ({TRUMPET_FREQS[i]}Hz)", TRUMPET_BANK, UITheme.NEON_GOLD) for i in range(8)]
        self.sax_pads = [PhysicalHoverPad(i, 200 + (i % 4) * 220, 240 + (i // 4) * 160, 180, 110, f"KEY {i+1} ({SAX_FREQS[i]}Hz)", SAX_BANK, UITheme.NEON_ORANGE) for i in range(8)]
        self.harp_pads = [PhysicalHoverPad(i, 140 + i * 125, 220, 100, 360, f"STRING {i+1}", HARP_BANK, UITheme.NEON_CYAN) for i in range(8)]
        self.guitar_strings = [PhysicalGuitarString(i, int((WIDTH / 9) * (i + 1)), ["E2", "A2", "D3", "G3", "B3", "E4", "G4", "A4"][i]) for i in range(8)]
        self.viola_pads = [PhysicalHoverPad(i, 200 + (i % 4) * 220, 240 + (i // 4) * 160, 180, 110, f"VIOLA {VIOLA_FREQS[i]}Hz", VIOLA_BANK, UITheme.NEON_PURPLE) for i in range(8)]
        self.drum_pads = [
            PhysicalDrumPad(320, 260, 80, "808 KICK", "KICK", UITheme.NEON_PINK),
            PhysicalDrumPad(640, 230, 70, "SNARE", "SNARE", UITheme.NEON_ORANGE),
            PhysicalDrumPad(960, 260, 60, "HI-HAT", "HIHAT", UITheme.NEON_GREEN),
            PhysicalDrumPad(640, 460, 90, "CRASH", "BOMB", UITheme.NEON_CYAN)
        ]
        self.prev_fingers = {}

    def update(self, hands, vfx, cosmic_vfx, dt):
        for k in self.white_keys + self.black_keys + self.drum_pads: k.hovered = False
        for p in self.trumpet_pads + self.sax_pads + self.harp_pads + self.viola_pads: p.hovered = False

        curr_fingers = {}
        for h_idx, h in enumerate(hands):
            is_dist = h["is_distant"]
            active_pt = h["beam_target"] if is_dist else h["lead_tip"]
            
            for f_idx, (fx, fy) in enumerate(h["all_tips"]):
                f_id = (h_idx, f_idx)
                tx, ty = active_pt if f_idx == 1 else (fx, fy)
                curr_fingers[f_id] = (tx, ty)
                prev_pos = self.prev_fingers.get(f_id, (tx, ty))
                vx, vy = tx - prev_pos[0], ty - prev_pos[1]
                spd = math.hypot(vx, vy)

                if self.current_inst_index == 0:
                    hit = False
                    for bk in self.black_keys:
                        if bk.check_interaction(f_id, tx, ty, vy, is_dist, vfx, cosmic_vfx):
                            hit = True; break
                    if not hit:
                        for wk in self.white_keys:
                            wk.check_interaction(f_id, tx, ty, vy, is_dist, vfx, cosmic_vfx)

                elif self.current_inst_index == 1:
                    for tp in self.trumpet_pads: tp.check_hover(tx, ty, is_dist, vfx, cosmic_vfx)
                elif self.current_inst_index == 2:
                    for sp in self.sax_pads: sp.check_hover(tx, ty, is_dist, vfx, cosmic_vfx)
                elif self.current_inst_index == 3:
                    for hp in self.harp_pads: hp.check_hover(tx, ty, is_dist, vfx, cosmic_vfx)
                elif self.current_inst_index == 4:
                    for gs in self.guitar_strings: gs.check_strum(prev_pos[0], tx, spd, is_dist, vfx, cosmic_vfx)
                elif self.current_inst_index == 5:
                    for vp in self.viola_pads: vp.check_hover(tx, ty, is_dist, vfx, cosmic_vfx)
                elif self.current_inst_index == 6:
                    for dp in self.drum_pads: dp.check_interaction(f_id, tx, ty, vy, is_dist, vfx, cosmic_vfx)

        self.prev_fingers = curr_fingers
        for wk in self.white_keys: wk.update(dt)
        for bk in self.black_keys: bk.update(dt)
        for gs in self.guitar_strings: gs.update(dt)
        for tp in self.trumpet_pads: tp.update(dt)
        for sp in self.sax_pads: sp.update(dt)
        for hp in self.harp_pads: hp.update(dt)
        for vp in self.viola_pads: vp.update(dt)
        for dp in self.drum_pads: dp.update(dt)

    def draw(self, surf, font_sm, font_md, font_lg):
        curr_meta = self.instruments_meta[self.current_inst_index]
        
        header_rect = pygame.Rect(WIDTH // 2 - 260, 18, 520, 44)
        NeonFX.draw_hud_pill(surf, header_rect, border_color=curr_meta["color"], radius=12, elevation=10)
        inst_title = font_md.render(f"STUDIO: {curr_meta['title']}", True, curr_meta["color"])
        surf.blit(inst_title, (WIDTH // 2 - inst_title.get_width() // 2, 26))

        if self.current_inst_index == 0:
            for wk in self.white_keys: wk.draw(surf, font_md)
            for bk in self.black_keys: bk.draw(surf, font_sm)
        elif self.current_inst_index == 1:
            for tp in self.trumpet_pads: tp.draw(surf, font_sm)
        elif self.current_inst_index == 2:
            for sp in self.sax_pads: sp.draw(surf, font_sm)
        elif self.current_inst_index == 3:
            for hp in self.harp_pads: hp.draw(surf, font_sm)
        elif self.current_inst_index == 4:
            for gs in self.guitar_strings: gs.draw(surf, font_md)
        elif self.current_inst_index == 5:
            for vp in self.viola_pads: vp.draw(surf, font_sm)
        elif self.current_inst_index == 6:
            for dp in self.drum_pads: dp.draw(surf, font_sm)

        hint = font_sm.render("[TAB] CYCLE INSTRUMENT | [1-7] DIRECT SELECT | 1-2M LASER BEAM ENGAGED", True, UITheme.TEXT_MUTED)
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 55))

# ==================================================================================================
# MODERN CYBER-CRYSTAL PIANO TILES ENGINE (HIGH-END 3D AESTHETIC & DYNAMIC SPEED)
# ==================================================================================================
class FallingPianoTile:
    def __init__(self, lane, y, width, height, col, sound):
        self.lane = lane
        self.y = float(y)
        self.width = width
        self.height = height
        self.col = col
        self.sound = sound
        self.hit = False
        self.missed = False
        self.hit_anim = 0.0          # 0.0 -> 1.0 hit dissolve animation
        self.pulse = random.uniform(0, math.pi * 2)

    def update(self, speed, dt):
        if not self.hit:
            self.y += speed * dt
            self.pulse += 5.5 * dt
        else:
            self.hit_anim = min(1.0, self.hit_anim + 5.5 * dt)

    def draw(self, surf, start_x, lane_w, current_speed):
        lx = start_x + self.lane * lane_w + (lane_w - self.width) // 2
        cur_y = int(self.y)

        # 1. HIT DISSOLVE EFFECT (Shockwave Expansion + Crystalline Flare)
        if self.hit:
            alpha = int(255 * (1.0 - self.hit_anim))
            if alpha <= 0:
                return
            expand = int(self.hit_anim * 22)
            pop_rect = pygame.Rect(lx - expand, cur_y - expand, self.width + expand * 2, self.height + expand * 2)
            pop_surf = pygame.Surface((pop_rect.width, pop_rect.height), pygame.SRCALPHA)
            
            # Expanding shock rim
            pygame.draw.rect(pop_surf, (*self.col[:3], alpha), (0, 0, pop_rect.width, pop_rect.height), width=3, border_radius=16)
            # Pure white flash core
            pygame.draw.rect(pop_surf, (*UITheme.PURE_WHITE[:3], int(alpha * 0.7)), (expand // 2, expand // 2, self.width + expand, self.height + expand), border_radius=12)
            surf.blit(pop_surf, pop_rect.topleft)
            return

        # 2. VELOCITY WARP LIGHT TRAIL (Projected behind fast tiles)
        if current_speed > 360.0:
            trail_len = int(min(90.0, (current_speed - 360.0) * 0.16))
            if trail_len > 8:
                trail_surf = pygame.Surface((self.width - 12, trail_len), pygame.SRCALPHA)
                trail_col = (*self.col[:3], int(min(85, current_speed * 0.10)))
                pygame.draw.rect(trail_surf, trail_col, (0, 0, self.width - 12, trail_len), border_radius=6)
                surf.blit(trail_surf, (lx + 6, cur_y - trail_len + 4), special_flags=pygame.BLEND_ALPHA_SDL2)

        tile_rect = pygame.Rect(lx, cur_y, self.width, self.height)

        # 3. MULTI-TIER 3D SOFT CAST SHADOW
        shd_surf = pygame.Surface((self.width + 28, self.height + 32), pygame.SRCALPHA)
        # Deep contact shadow
        pygame.draw.rect(shd_surf, (0, 0, 0, 170), (4, 12, self.width, self.height), border_radius=16)
        # Soft ambient penumbra
        pygame.draw.rect(shd_surf, (0, 0, 0, 80), (0, 8, self.width + 8, self.height + 12), border_radius=18)
        surf.blit(shd_surf, (lx - 4, cur_y - 2))

        # 4. 3D EXTRUDED BOTTOM BEVEL (Physical Key Depth)
        ext_h = 10
        ext_rect = pygame.Rect(lx, cur_y + self.height - 4, self.width, ext_h)
        dark_col = (max(0, self.col[0] - 95), max(0, self.col[1] - 95), max(0, self.col[2] - 95))
        pygame.draw.rect(surf, dark_col, ext_rect, border_radius=10)
        pygame.draw.rect(surf, (15, 20, 32), ext_rect, 1, border_radius=10)

        # 5. CRYSTAL-GLASS MAIN BODY
        face_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Base glass fill
        pygame.draw.rect(face_surf, (*self.col[:3], 215), (0, 0, self.width, self.height), border_radius=14)
        
        # Vertical gradient simulation (Lighter translucent cap on top half)
        cap_h = self.height // 2
        cap_surf = pygame.Surface((self.width - 4, cap_h), pygame.SRCALPHA)
        pygame.draw.rect(cap_surf, (255, 255, 255, 55), (0, 0, self.width - 4, cap_h), border_radius=12)
        face_surf.blit(cap_surf, (2, 2))

        # White inner rim border
        pygame.draw.rect(face_surf, (255, 255, 255, 220), (0, 0, self.width, self.height), 2, border_radius=14)

        # Specular 3D Top Lighting Chamfer
        pygame.draw.line(face_surf, (255, 255, 255, 255), (14, 2), (self.width - 14, 2), 2)
        # Lateral edge highlight
        pygame.draw.line(face_surf, (255, 255, 255, 120), (3, 14), (3, self.height - 14), 1)

        # 6. CENTRAL ILLUMINATED ENERGY RHOMBUS (Tactile Keycap Icon)
        cx, cy = self.width // 2, self.height // 2
        pulse_r = int(7 + math.sin(self.pulse) * 2)
        diamond_pts = [(cx, cy - pulse_r), (cx + pulse_r, cy), (cx, cy + pulse_r), (cx - pulse_r, cy)]
        pygame.draw.polygon(face_surf, (255, 255, 255, 230), diamond_pts)
        pygame.draw.polygon(face_surf, (*self.col[:3], 255), diamond_pts, 1)

        surf.blit(face_surf, (lx, cur_y))

        # 7. SOFT VOLUMETRIC AURA GLOW
        NeonFX.draw_glow_circle(surf, self.col, tile_rect.center, 24, glow_size=16, max_alpha=140)


class NeoPianoTilesGame:
    def __init__(self):
        self.score = 0
        self.displayed_score = 0.0      # Smooth rolling score interpolation
        self.combo = 0
        self.max_combo = 0
        self.lives = 4
        self.time_elapsed = 0.0
        
        # SPEED ACCELERATION SPECS
        self.base_speed = 250.0         # Calm, readable starting tempo (px/sec)
        self.current_speed = 250.0
        self.max_speed = 940.0          # Intense rhythm limit
        
        self.is_active = False
        self.game_over = False
        self.tiles = []
        self.spawn_timer = 0.0
        
        # Animated Verdict Pop
        self.feedback_msg = ""
        self.feedback_timer = 0.0
        self.feedback_col = UITheme.NEON_GREEN
        self.feedback_scale = 1.0

        self.board = WallOfFameBoard("wall_of_fame_tiles.json", "PIANO TILES: WALL OF FAME")
        self.show_leaderboard = False
        self.streak_multiplier = 1.0

        # Track Layout Geometry
        self.lane_w = 175
        self.track_w = self.lane_w * 4
        self.start_x = (WIDTH - self.track_w) // 2
        self.hit_y = HEIGHT - 150
        self.hit_h = 75

        # Visual FX Arrays
        self.lane_glow = [0.0] * 4       # Column light pillars
        self.speed_streaks = []          # Floating highway speed particles
        for _ in range(22):
            self.speed_streaks.append({
                "x": random.randint(self.start_x + 10, self.start_x + self.track_w - 10),
                "y": random.uniform(90, HEIGHT - 80),
                "length": random.uniform(20, 60),
                "speed_mult": random.uniform(0.7, 1.3),
                "alpha": random.randint(40, 110)
            })

    def start_game(self):
        self.score = 0
        self.displayed_score = 0.0
        self.combo = 0
        self.max_combo = 0
        self.lives = 4
        self.time_elapsed = 0.0
        self.current_speed = self.base_speed
        self.is_active = True
        self.game_over = False
        self.tiles.clear()
        self.spawn_timer = 0.0
        self.feedback_msg = "READY... GO!"
        self.feedback_timer = 1.2
        self.feedback_scale = 1.4
        self.feedback_col = UITheme.NEON_GREEN
        self.show_leaderboard = False
        self.streak_multiplier = 1.0
        self.lane_glow = [0.0] * 4

    def update(self, hands, vfx, dt):
        global audio_energy
        if not self.is_active or self.game_over:
            return

        self.time_elapsed += dt

        # Smooth Rolling Score Interpolation
        self.displayed_score += (self.score - self.displayed_score) * min(1.0, 12.0 * dt)

        # Verdict Spring Decay
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            self.feedback_scale = max(1.0, self.feedback_scale - 2.2 * dt)

        # Fade Out Lane Light Pillars
        for i in range(4):
            if self.lane_glow[i] > 0.0:
                self.lane_glow[i] = max(0.0, self.lane_glow[i] - 4.0 * dt)

        # UPDATE BACKGROUND SPEED STREAKS
        for s in self.speed_streaks:
            s["y"] += self.current_speed * s["speed_mult"] * dt
            if s["y"] > HEIGHT - 80:
                s["y"] = 90
                s["x"] = random.randint(self.start_x + 10, self.start_x + self.track_w - 10)
                s["length"] = random.uniform(20, 60) * (self.current_speed / 450.0)

        # COMPOUND ACCELERATION: Smooth continuous ramp + combo speed push
        time_boost = (self.time_elapsed ** 1.15) * 8.6
        combo_boost = self.combo * 2.8
        self.current_speed = min(self.max_speed, self.base_speed + time_boost + combo_boost)

        # Dynamic Tile Cadence (Ensures consistent rhythmic separation)
        spawn_interval = max(0.24, 385.0 / self.current_speed)
        self.spawn_timer += dt
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0.0
            lane = random.randint(0, 3)
            col_list = [UITheme.NEON_CYAN, UITheme.NEON_PURPLE, UITheme.NEON_PINK, UITheme.NEON_GREEN]
            snd_list = [PIANO_WHITE_BANK[0], PIANO_WHITE_BANK[3], PIANO_WHITE_BANK[5], PIANO_WHITE_BANK[7]]
            tile_h = int(120 + (self.current_speed / self.max_speed) * 35)
            self.tiles.append(FallingPianoTile(lane, -tile_h, self.lane_w - 22, tile_h, col_list[lane], snd_list[lane]))

        # Update Falling Tiles
        for t in self.tiles:
            t.update(self.current_speed, dt)
            if t.y > self.hit_y + self.hit_h + 10 and not t.hit and not t.missed:
                t.missed = True
                self.combo = 0
                self.streak_multiplier = 1.0
                self.lives -= 1
                self.feedback_msg = "TILE MISSED!"
                self.feedback_timer = 0.8
                self.feedback_scale = 1.3
                self.feedback_col = UITheme.NEON_PINK
                vfx.trigger_shake(0.22, 6.0)

        if self.lives <= 0:
            self.is_active = False
            self.game_over = True
            self.show_leaderboard = True
            self.board.start_name_entry(self.score, self.max_combo)
            return

        # Prune dead tiles
        self.tiles = [t for t in self.tiles if (not t.hit or t.hit_anim < 1.0) and t.y < HEIGHT + 80]

        # Hand / Raycast Touch Triggers
        for h in hands:
            target_pt = h["beam_target"] if h["is_distant"] else h["lead_tip"]
            tx, ty = target_pt

            if (self.hit_y - 45) <= ty <= (self.hit_y + self.hit_h + 45):
                for t in self.tiles:
                    if not t.hit and not t.missed:
                        lx = self.start_x + t.lane * self.lane_w
                        hitbox = pygame.Rect(lx + 4, int(t.y) - 10, self.lane_w - 8, t.height + 30)

                        if hitbox.collidepoint(tx, ty):
                            t.hit = True
                            t.sound.play()
                            self.lane_glow[t.lane] = 1.0
                            self.combo += 1
                            self.max_combo = max(self.max_combo, self.combo)

                            if self.combo >= 20: self.streak_multiplier = 2.5
                            elif self.combo >= 10: self.streak_multiplier = 1.8
                            elif self.combo >= 5: self.streak_multiplier = 1.3
                            else: self.streak_multiplier = 1.0

                            bar_center_y = self.hit_y + self.hit_h // 2
                            tile_center_y = t.y + t.height // 2
                            offset = abs(tile_center_y - bar_center_y)

                            if offset < 28:
                                pts = int(350 * self.streak_multiplier)
                                self.feedback_msg = f"PERFECT! +{pts}"
                                self.feedback_col = UITheme.NEON_GOLD
                            else:
                                pts = int(180 * self.streak_multiplier)
                                self.feedback_msg = f"GOOD! +{pts}"
                                self.feedback_col = UITheme.NEON_GREEN

                            self.score += pts
                            self.feedback_timer = 0.65
                            self.feedback_scale = 1.45
                            audio_energy = min(1.0, audio_energy + 0.35)
                            
                            vfx.burst(lx + self.lane_w // 2, self.hit_y + self.hit_h // 2, t.col, count=24, with_notes=True)

    def draw(self, surf, font_sm, font_md, font_lg, hands=[]):
        # 1. AUDIO-REACTIVE AMBIENT BACKDROP VIGNETTE
        aura_w, aura_h = self.track_w + 120, HEIGHT - 60
        aura_s = pygame.Surface((aura_w, aura_h), pygame.SRCALPHA)
        pygame.draw.ellipse(aura_s, (0, 242, 255, int(18 + audio_energy * 25)), (0, 0, aura_w, aura_h))
        surf.blit(aura_s, (self.start_x - 60, 60), special_flags=pygame.BLEND_ALPHA_SDL2)

        # 2. 3D TRACK BACKDROP WITH AMBIENT DROP SHADOW
        track_rect = pygame.Rect(self.start_x, 90, self.track_w, HEIGHT - 120)
        ShadowEngine.blit_drop_shadow(surf, track_rect, radius=22, elevation=24)

        track_surf = pygame.Surface((self.track_w, HEIGHT - 120), pygame.SRCALPHA)
        # Deep void surface
        pygame.draw.rect(track_surf, (8, 12, 24, 240), (0, 0, self.track_w, HEIGHT - 120), border_radius=20)
        # Modern cyan glass outline
        pygame.draw.rect(track_surf, (40, 62, 105, 190), (0, 0, self.track_w, HEIGHT - 120), 2, border_radius=20)
        surf.blit(track_surf, track_rect.topleft)

        # 3. DYNAMIC HIGHWAY SPEED STREAKS
        for s in self.speed_streaks:
            pygame.draw.line(surf, (*UITheme.NEON_CYAN[:3], s["alpha"]), (int(s["x"]), int(s["y"])), (int(s["x"]), int(s["y"] + s["length"])), 1)

        # 4. VERTICAL LANES & ANIMATED LIGHT PILLARS
        for l in range(4):
            lx = self.start_x + l * self.lane_w
            
            # Hit lane laser beam column
            if self.lane_glow[l] > 0.05:
                pillar_s = pygame.Surface((self.lane_w, HEIGHT - 120), pygame.SRCALPHA)
                col = [UITheme.NEON_CYAN, UITheme.NEON_PURPLE, UITheme.NEON_PINK, UITheme.NEON_GREEN][l]
                alpha = int(58 * self.lane_glow[l])
                pygame.draw.rect(pillar_s, (*col[:3], alpha), (0, 0, self.lane_w, HEIGHT - 120))
                # Core vertical streak
                pygame.draw.line(pillar_s, (255, 255, 255, int(alpha * 1.5)), (self.lane_w // 2, 0), (self.lane_w // 2, HEIGHT - 120), 3)
                surf.blit(pillar_s, (lx, 90), special_flags=pygame.BLEND_ALPHA_SDL2)

            # Modern Lane Dividers (Double Groove)
            if l > 0:
                pygame.draw.line(surf, (0, 0, 0, 180), (lx - 1, 90), (lx - 1, HEIGHT - 30), 2)
                pygame.draw.line(surf, (42, 60, 96), (lx, 90), (lx, HEIGHT - 30), 1)

            # Bottom Lane Badges
            l_txt = font_sm.render(f"LANE {l+1}", True, (80, 105, 145))
            surf.blit(l_txt, (lx + self.lane_w // 2 - l_txt.get_width() // 2, HEIGHT - 62))

        # 5. ELECTRIC LASER HIT RECEPTOR BAR
        hit_rect = pygame.Rect(self.start_x + 8, self.hit_y, self.track_w - 16, self.hit_h)
        ShadowEngine.blit_drop_shadow(surf, hit_rect, radius=16, elevation=14)

        hit_surf = pygame.Surface((hit_rect.width, hit_rect.height), pygame.SRCALPHA)
        # Translucent receptor plate
        pygame.draw.rect(hit_surf, (16, 26, 46, 220), (0, 0, hit_rect.width, hit_rect.height), border_radius=16)
        pygame.draw.rect(hit_surf, UITheme.NEON_CYAN, (0, 0, hit_rect.width, hit_rect.height), 2, border_radius=16)
        
        # Central glowing horizontal laser core line
        cy_local = hit_rect.height // 2
        pygame.draw.line(hit_surf, (*UITheme.NEON_CYAN[:3], 120), (8, cy_local), (hit_rect.width - 8, cy_local), 6)
        pygame.draw.line(hit_surf, UITheme.PURE_WHITE, (8, cy_local), (hit_rect.width - 8, cy_local), 2)
        
        # Specular light highlight on top edge
        pygame.draw.line(hit_surf, UITheme.GLASS_HIGHLIGHT, (16, 2), (hit_rect.width - 16, 2), 2)
        surf.blit(hit_surf, hit_rect.topleft)

        # Lane Emitter Nodes on the Hit Bar
        for li in range(4):
            node_x = self.start_x + li * self.lane_w + self.lane_w // 2
            node_y = self.hit_y + self.hit_h // 2
            NeonFX.draw_glow_circle(surf, UITheme.NEON_CYAN, (node_x, node_y), 8, glow_size=10, max_alpha=180)
            pygame.draw.circle(surf, UITheme.PURE_WHITE, (node_x, node_y), 3)

        # 6. RENDER ALL FALLING 3D PIANO TILES
        for t in self.tiles:
            t.draw(surf, self.start_x, self.lane_w, self.current_speed)

        # 7. HIGH-TECH 3D HUD PANELS WITH DROP SHADOWS
        # Left HUD: Score & Multiplier
        hud_l = pygame.Rect(25, 20, 240, 68)
        NeonFX.draw_glass_card(surf, hud_l, border_color=UITheme.NEON_CYAN, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_md.render(f"SCORE {int(self.displayed_score)}", True, UITheme.PURE_WHITE), (38, 28))
        surf.blit(font_sm.render(f"COMBO ×{self.combo} ({self.streak_multiplier:.1f}x)", True, UITheme.NEON_GOLD), (38, 54))

        # Right HUD: Progressive Tempo Speed & Modern Heart Containers
        hud_r = pygame.Rect(WIDTH - 255, 20, 230, 68)
        NeonFX.draw_glass_card(surf, hud_r, border_color=UITheme.NEON_ORANGE, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_sm.render(f"SPEED {int(self.current_speed)} px/s", True, UITheme.NEON_GOLD), (hud_r.x + 14, hud_r.y + 12))
        
        for i in range(4):
            draw_heart(surf, UITheme.NEON_PINK if i < self.lives else (35, 45, 65), hud_r.x + 28 + i * 44, hud_r.y + 44, 11)

        # 8. SPRING-ANIMATED HIT VERDICT CALLOUT WITH CHROMATIC SHADOW
        if self.feedback_timer > 0:
            scale = self.feedback_scale
            raw_text = font_lg.render(self.feedback_msg, True, self.feedback_col)
            tw, th = raw_text.get_size()
            scaled_w, scaled_h = int(tw * scale), int(th * scale)
            
            fb_surf = pygame.transform.smoothscale(raw_text, (scaled_w, scaled_h))
            fb_shd = pygame.transform.smoothscale(font_lg.render(self.feedback_msg, True, (0, 0, 0)), (scaled_w, scaled_h))

            callout_x = WIDTH // 2 - scaled_w // 2
            callout_y = HEIGHT // 2 - scaled_h // 2 - 10

            surf.blit(fb_shd, (callout_x + 3, callout_y + 3))
            surf.blit(fb_surf, (callout_x, callout_y))

        # 9. HIGH SCORE LEADERBOARD OVERLAY
        if self.show_leaderboard:
            self.board.draw(surf, font_sm, font_md, font_lg, hands=hands)

# ==================================================================================================
# [END OF PART 2/3]
# Paste this block into your code file directly below Part 1. When you are ready for Part 3, reply: continue
# ==================================================================================================
"""
====================================================================================================
PROJECT: AETHERIA GRAND PRIX — SULAM 2026 NEO-SYMPHONIC EXHIBITION MASTERPIECE
ROLE: PRINCIPAL GAME ARCHITECT & 3D GRAPHICS/AUDIO SYSTEMS ENGINEER (AAA PRODUCTION SPEC)
PART 3 / 3: GAME 3 (SYNTH BLADE), GAME 5 (CELESTIAL HARP), LIVE LOOP STATION SEQUENCER,
            AI CO-PILOT, 3D MUSICAL DNA PASSPORT, LIVE STAGE, OPERATOR PANEL &
            MASTER APPLICATION RUNTIME PIPELINE
====================================================================================================
"""

# ==================================================================================================
# 23. GAME 3: NEO-SYNTH BLADE (DUAL-SABER RHYTHM SLASHER) WITH 3D CAST SHADOWS
# ==================================================================================================
class SlasherBeatOrb:
    def __init__(self):
        self.x = random.randint(220, WIDTH - 220)
        self.y = -60.0
        self.z_depth = random.uniform(0.85, 1.25)
        self.vx = random.uniform(-55, 55) * self.z_depth
        self.vy = random.uniform(240, 390) * self.z_depth
        self.radius = int(32 * self.z_depth)
        self.is_sliced = False
        self.blade_side = random.choice(["LEFT", "RIGHT"])
        self.color = UITheme.NEON_ORANGE if self.blade_side == "LEFT" else UITheme.NEON_PINK
        self.snd_idx = random.randint(0, len(SLASHER_FREQS) - 1)
        self.pulse = random.uniform(0, math.pi * 2)

    # Added speed_mult parameter to scale velocity
    def update(self, dt, speed_mult=1.0):
        self.x += self.vx * dt * speed_mult
        self.y += self.vy * dt * speed_mult
        self.pulse += 6.5 * dt * speed_mult

    def draw(self, surf, font_sm):
        if self.is_sliced: return
        r = int(self.radius + math.sin(self.pulse) * 4)
        
        # 3D Projected Ground & Depth Cast Shadow
        ShadowEngine.draw_projected_ground_shadow(surf, int(self.x + 8), int(self.y + 14), r * 2, int(r * 0.9), alpha=140)

        # 3D Emissive Slasher Sphere
        NeonFX.draw_glow_circle(surf, self.color, (int(self.x), int(self.y)), r, glow_size=20, max_alpha=180)
        
        # 3D Sphere Shading Underlay
        pygame.draw.circle(surf, (14, 18, 30), (int(self.x), int(self.y)), r)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r, 3)
        
        # Specular 3D Highlight Glint
        pygame.draw.circle(surf, (255, 255, 255, 210), (int(self.x - r * 0.35), int(self.y - r * 0.35)), max(2, r // 4))

        icon = "◀ L" if self.blade_side == "LEFT" else "R ▶"
        lbl_shd = font_sm.render(icon, True, (0, 0, 0))
        surf.blit(lbl_shd, (int(self.x - lbl_shd.get_width() // 2 + 1), int(self.y - lbl_shd.get_height() // 2 + 1)))
        lbl = font_sm.render(icon, True, UITheme.PURE_WHITE)
        surf.blit(lbl, (int(self.x - lbl.get_width() // 2), int(self.y - lbl.get_height() // 2)))

class NeoSynthBladeGame:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.energy = 100.0             # Preserved original energy bar
        self.duration = 60.0
        self.time_left = 60.0
        self.is_active = False
        self.game_over = False
        self.orbs = []
        self.spawn_timer = 0.0
        self.prev_saber_pts = {}
        self.board = WallOfFameBoard("wall_of_fame_blades.json", "SYNTH BLADE: WALL OF FAME")
        self.show_leaderboard = False

    def start_game(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.energy = 100.0
        self.time_left = self.duration
        self.is_active = True
        self.game_over = False
        self.orbs.clear()
        self.spawn_timer = 0.0
        self.prev_saber_pts.clear()
        self.show_leaderboard = False

    def update(self, hands, vfx, dt):
        global audio_energy
        if not self.is_active or self.game_over:
            return

        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0.0 or self.energy <= 0.0:
            self.is_active = False
            self.game_over = True
            self.show_leaderboard = True
            self.board.start_name_entry(self.score, self.max_combo)
            return

        elapsed = self.duration - self.time_left
        speed_mult = 0.35 + (elapsed / self.duration) * 1.65

        self.spawn_timer += dt
        if self.spawn_timer >= (0.48 / speed_mult):
            self.spawn_timer = 0.0
            self.orbs.append(SlasherBeatOrb())

        # Exact, fair damage deduction only on confirmed missed orbs
        for orb in self.orbs:
            orb.update(dt, speed_mult)
            if orb.y > HEIGHT + 40 and not orb.is_sliced:
                orb.is_sliced = True
                self.combo = 0
                self.energy = max(0.0, self.energy - 15.0)
                vfx.trigger_shake(0.20, 5.0)

        for h in hands:
            hand_side = "LEFT" if h["is_left"] else "RIGHT"
            tip = h["beam_target"] if h["is_distant"] else h["lead_tip"]
            prev_tip = self.prev_saber_pts.get(hand_side, tip)

            # Continuous segment check: Prevents fast sweeps from skipping through orbs
            vx = tip[0] - prev_tip[0]
            vy = tip[1] - prev_tip[1]
            seg_len_sq = vx * vx + vy * vy

            for orb in self.orbs:
                if not orb.is_sliced:
                    if seg_len_sq < 1e-4:
                        dist = math.hypot(tip[0] - orb.x, tip[1] - orb.y)
                    else:
                        t = max(0.0, min(1.0, ((orb.x - prev_tip[0]) * vx + (orb.y - prev_tip[1]) * vy) / seg_len_sq))
                        proj_x = prev_tip[0] + t * vx
                        proj_y = prev_tip[1] + t * vy
                        dist = math.hypot(proj_x - orb.x, proj_y - orb.y)

                    reach = (orb.radius + 40) if h["is_distant"] else (orb.radius + 32)
                    if dist < reach:
                        orb.is_sliced = True
                        match_bonus = 2.0 if orb.blade_side == hand_side else 1.0
                        self.combo += 1
                        self.max_combo = max(self.max_combo, self.combo)
                        pts = int((200 + self.combo * 25) * match_bonus)
                        self.score += pts
                        self.energy = min(100.0, self.energy + 6.0)
                        audio_energy = min(1.0, audio_energy + 0.3)
                        SLASHER_BANK[orb.snd_idx].play()
                        vfx.burst(orb.x, orb.y, orb.color, count=24, with_notes=True)

            self.prev_saber_pts[hand_side] = tip

        self.orbs = [o for o in self.orbs if not o.is_sliced and o.y <= HEIGHT + 40]

    def draw(self, surf, font_sm, font_md, font_lg, hands):
        for orb in self.orbs:
            orb.draw(surf, font_sm)

        # (Pink and Orange blade pointers removed for direct, clean conductor hand tracking)

        # Left HUD: Score & Combo
        hud_l = pygame.Rect(25, 20, 220, 68)
        NeonFX.draw_glass_card(surf, hud_l, border_color=UITheme.NEON_CYAN, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_md.render(f"SCORE {self.score}", True, UITheme.PURE_WHITE), (38, 28))
        surf.blit(font_sm.render(f"COMBO ×{self.combo}", True, UITheme.NEON_GOLD), (38, 54))

        # Right HUD: Time & Shield/Energy Bar
        bar_rect = pygame.Rect(WIDTH - 245, 20, 220, 68)
        NeonFX.draw_glass_card(surf, bar_rect, border_color=UITheme.NEON_PINK, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_sm.render(f"TIME {int(self.time_left)}s", True, UITheme.PURE_WHITE), (bar_rect.x + 14, bar_rect.y + 12))

        meter_bg = pygame.Rect(bar_rect.x + 14, bar_rect.y + 40, 190, 14)
        pygame.draw.rect(surf, (14, 18, 30), meter_bg, border_radius=7)
        pygame.draw.rect(surf, (30, 42, 65), meter_bg, 1, border_radius=7)

        fill_w = int(190 * (self.energy / 100.0))
        if fill_w > 0:
            fill_rect = pygame.Rect(meter_bg.x, meter_bg.y, fill_w, meter_bg.height)
            meter_col = UITheme.NEON_GREEN if self.energy > 40 else UITheme.NEON_PINK
            pygame.draw.rect(surf, meter_col, fill_rect, border_radius=7)
            pygame.draw.line(surf, UITheme.GLASS_HIGHLIGHT, (fill_rect.x + 4, fill_rect.y + 1), (fill_rect.right - 4, fill_rect.y + 1), 1)

        if self.show_leaderboard:
            self.board.draw(surf, font_sm, font_md, font_lg, hands=hands)

# ==================================================================================================
# 24. GAME 5: CELESTIAL SINGULARITY (HARMONIC ORBITAL RESONANCE) WITH 3D ORBITAL DEPTH
# ==================================================================================================
class SingularityStar:
    def __init__(self):
        self.angle = random.uniform(0, math.pi * 2)
        self.radius = random.uniform(380, 500)
        self.speed = random.uniform(90, 165)
        self.pitch_idx = random.randint(0, len(HARP_FREQS) - 1)
        self.color_name = random.choice(["CYAN", "GOLD", "PINK", "GREEN"])
        col_map = {
            "CYAN": UITheme.NEON_CYAN,
            "GOLD": UITheme.NEON_GOLD,
            "PINK": UITheme.NEON_PINK,
            "GREEN": UITheme.NEON_GREEN
        }
        self.color = col_map[self.color_name]
        self.hit = False
        self.char = random.choice(["✦", "★", "✸", "✧", "♪"])

    # Added speed_mult parameter to scale inward speed
    def update(self, dt, speed_mult=1.0):
        self.radius -= self.speed * dt * speed_mult

    def get_pos(self):
        cx, cy = WIDTH // 2, HEIGHT // 2 + 25
        return int(cx + math.cos(self.angle) * self.radius), int(cy + math.sin(self.angle) * self.radius)

class CelestialSingularityGame:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.resonance_chain = 0
        self.last_color_name = None
        self.energy = 100.0             # Preserved original energy bar
        self.duration = 60.0
        self.time_left = 60.0
        self.is_active = False
        self.game_over = False
        self.stars = []
        self.spawn_timer = 0.0
        self.board = WallOfFameBoard("wall_of_fame_catcher.json", "CELESTIAL HARP: WALL OF FAME")
        self.show_leaderboard = False

    def start_game(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.resonance_chain = 0
        self.last_color_name = None
        self.energy = 100.0
        self.time_left = self.duration
        self.is_active = True
        self.game_over = False
        self.stars.clear()
        self.spawn_timer = 0.0
        self.show_leaderboard = False

    def update(self, hands, vfx, dt):
        global audio_energy
        if not self.is_active or self.game_over:
            return

        self.time_left = max(0.0, self.time_left - dt)

        # Game ends only when time expires or energy is depleted from missed stars
        if self.time_left <= 0.0 or self.energy <= 0.0:
            self.is_active = False
            self.game_over = True
            self.show_leaderboard = True
            self.board.start_name_entry(self.score, self.max_combo)
            return

        elapsed = self.duration - self.time_left
        speed_mult = 0.35 + (elapsed / self.duration) * 1.85

        self.spawn_timer += dt
        if self.spawn_timer >= (0.40 / speed_mult):
            self.spawn_timer = 0.0
            self.stars.append(SingularityStar())

        # Exact, fair damage deduction only when a star breaches the core
        for star in self.stars:
            star.update(dt, speed_mult)
            if star.radius < 50 and not star.hit:
                star.hit = True
                self.combo = 0
                self.resonance_chain = 0
                self.energy = max(0.0, self.energy - 15.0)
                vfx.trigger_shake(0.22, 6.0)

        for h in hands:
            target_pt = h["beam_target"] if h["is_distant"] else h["lead_tip"]
            px, py = target_pt

            for star in self.stars:
                if not star.hit:
                    sx, sy = star.get_pos()
                    reach = 62.0 if h["is_distant"] else 48.0
                    if math.hypot(px - sx, py - sy) < reach:
                        star.hit = True
                        self.combo += 1
                        self.max_combo = max(self.max_combo, self.combo)

                        if star.radius > 240: base_pts = 150
                        elif star.radius > 120: base_pts = 300
                        else: base_pts = 500

                        if star.color_name == self.last_color_name:
                            self.resonance_chain = min(4, self.resonance_chain + 1)
                        else:
                            self.resonance_chain = 1
                            self.last_color_name = star.color_name

                        earned = base_pts * self.resonance_chain
                        self.score += earned
                        self.energy = min(100.0, self.energy + 6.0)
                        audio_energy = min(1.0, audio_energy + 0.35)
                        HARP_BANK[star.pitch_idx].play()
                        vfx.burst(sx, sy, star.color, count=18, with_notes=True)

        self.stars = [s for s in self.stars if s.radius >= 50 and not s.hit]

    def draw(self, surf, font_sm, font_md, font_lg, hands=[]):
        cx, cy = WIDTH // 2, HEIGHT // 2 + 25

        # 3D Concentric Gravitational Rings with Soft Outer Shadows
        for r, alpha, lbl_zone in [(320, 45, "OUTER GRAVITY [150pts]"), (200, 65, "MID HARMONIC [300pts]"), (110, 95, "CORE RESONANCE [500pts]")]:
            shd_s = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(shd_s, (0, 0, 0, 110), (r + 6, r + 8), r, 3)
            surf.blit(shd_s, (cx - r - 6, cy - r - 6))

            ring_s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_s, (*UITheme.NEON_CYAN[:3], alpha), (r, r), r, 2)
            surf.blit(ring_s, (cx - r, cy - r))
            
            z_txt = font_sm.render(lbl_zone, True, (*UITheme.NEON_CYAN[:3], alpha + 30))
            surf.blit(z_txt, (cx - z_txt.get_width() // 2, cy - r - 12))

        # Central Emissive 3D Black Hole / Singularity
        pulse = math.sin(pygame.time.get_ticks() * 0.008) * 6
        core_r = int(38 + pulse)
        ShadowEngine.draw_projected_ground_shadow(surf, cx, cy + 8, int(core_r * 2.2), int(core_r * 1.5), alpha=200)

        NeonFX.draw_glow_circle(surf, UITheme.NEON_PURPLE, (cx, cy), core_r, glow_size=24, max_alpha=180)
        pygame.draw.circle(surf, (10, 14, 26), (cx, cy), core_r + 6)
        pygame.draw.circle(surf, UITheme.NEON_PURPLE, (cx, cy), core_r, 3)
        pygame.draw.arc(surf, UITheme.GLASS_HIGHLIGHT, (cx - core_r, cy - core_r, core_r * 2, core_r * 2), 0.8, 2.3, 2)

        for star in self.stars:
            sx, sy = star.get_pos()
            ShadowEngine.draw_projected_ground_shadow(surf, sx + 4, sy + 6, 26, 12, alpha=130)
            draw_star(surf, star.color, sx, sy, 18)
            lbl = font_sm.render(star.char, True, UITheme.PURE_WHITE)
            surf.blit(lbl, (sx - lbl.get_width() // 2, sy - lbl.get_height() // 2))

        # Left HUD: Score & Chain
        hud_l = pygame.Rect(25, 20, 230, 68)
        NeonFX.draw_glass_card(surf, hud_l, border_color=UITheme.NEON_CYAN, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_md.render(f"SCORE {self.score}", True, UITheme.PURE_WHITE), (38, 28))
        surf.blit(font_sm.render(f"CHAIN ×{self.resonance_chain} RESONANCE", True, UITheme.NEON_GOLD), (38, 54))

        # Right HUD: Time & Shield/Energy Bar
        bar_rect = pygame.Rect(WIDTH - 245, 20, 220, 68)
        NeonFX.draw_glass_card(surf, bar_rect, border_color=UITheme.NEON_PURPLE, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_sm.render(f"TIME {int(self.time_left)}s", True, UITheme.PURE_WHITE), (bar_rect.x + 14, bar_rect.y + 12))
        
        meter_bg = pygame.Rect(bar_rect.x + 14, bar_rect.y + 40, 190, 14)
        pygame.draw.rect(surf, (14, 18, 30), meter_bg, border_radius=7)
        pygame.draw.rect(surf, (30, 42, 65), meter_bg, 1, border_radius=7)
        fill_w = int(190 * (self.energy / 100.0))
        if fill_w > 0:
            fill_rect = pygame.Rect(meter_bg.x, meter_bg.y, fill_w, meter_bg.height)
            meter_col = UITheme.NEON_GREEN if self.energy > 40 else UITheme.NEON_PINK
            pygame.draw.rect(surf, meter_col, fill_rect, border_radius=7)
            pygame.draw.line(surf, UITheme.GLASS_HIGHLIGHT, (fill_rect.x + 4, fill_rect.y + 1), (fill_rect.right - 4, fill_rect.y + 1), 1)

        if self.show_leaderboard:
            self.board.draw(surf, font_sm, font_md, font_lg, hands=hands)

# ==================================================================================================
# 24B. GAME 6: CELESTIAL SONIC SLINGSHOT (HARMONIC ARPEGGIO RICOCHET) — CLEAN VERSION
# ==================================================================================================
class SonicChimeTarget:
    def __init__(self, x, y, pitch_idx, label="C", chord_group="C_MAJ", is_moving=False):
        self.base_x = float(x)
        self.base_y = float(y)
        self.x = float(x)
        self.y = float(y)
        self.radius = 29.0
        self.pitch_idx = pitch_idx
        self.label = label
        self.chord_group = chord_group
        self.is_moving = is_moving
        self.anim_t = random.uniform(0, math.pi * 2)
        self.hit_glow = 0.0
        self.hit_count = 0
        
        self.chord_colors = {
            "C_MAJ": UITheme.NEON_CYAN,
            "E_MIN": UITheme.NEON_GOLD,
            "G_MAJ": UITheme.NEON_PINK
        }
        self.color = self.chord_colors.get(chord_group, UITheme.NEON_GREEN)

    def update(self, dt):
        self.anim_t += 1.8 * dt
        if self.is_moving:
            self.y = self.base_y + math.sin(self.anim_t) * 42.0
            self.x = self.base_x + math.cos(self.anim_t * 0.7) * 20.0
        if self.hit_glow > 0.0:
            self.hit_glow = max(0.0, self.hit_glow - 2.6 * dt)

    def draw(self, surf, font_sm, font_md):
        r = int(self.radius + self.hit_glow * 10)
        cx, cy = int(self.x), int(self.y)

        ShadowEngine.draw_projected_ground_shadow(surf, cx + 4, cy + 8, r * 2, int(r * 1.1), alpha=140)
        NeonFX.draw_glow_circle(surf, self.color, (cx, cy), r, glow_size=20, max_alpha=220 if self.hit_glow > 0.2 else 85)
        pygame.draw.circle(surf, (12, 18, 32), (cx, cy), r)
        pygame.draw.circle(surf, self.color, (cx, cy), r, 3)
        pygame.draw.circle(surf, UITheme.PURE_WHITE, (cx, cy), max(2, r - 7), 1)
        pygame.draw.arc(surf, UITheme.GLASS_HIGHLIGHT, (cx - r + 3, cy - r + 3, (r - 3) * 2, (r - 3) * 2), 0.8, 2.3, 2)

        lbl = font_md.render(self.label, True, UITheme.PURE_WHITE)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy - lbl.get_height() // 2 - 2))
        
        tag = font_sm.render(self.chord_group.split("_")[0], True, self.color)
        surf.blit(tag, (cx - tag.get_width() // 2, cy + 12))


class SonicOrb:
    def __init__(self, x, y, vx, vy, is_supercharged=False):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = 16.0
        self.bounces = 0
        self.max_bounces = 7
        self.alive = True
        self.combo = 0
        self.is_supercharged = is_supercharged
        self.trail = deque(maxlen=18)
        self.hit_chords = set()

    def update(self, dt, chimes, portal_pos, vfx, cosmic_vfx):
        global audio_energy
        if not self.alive:
            return 0, False

        self.trail.append((int(self.x), int(self.y), self.is_supercharged))

        gravity = 440.0 if self.is_supercharged else 510.0
        self.vy += gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        earned_points = 0
        triad_completed = False

        if portal_pos:
            dist_portal = math.hypot(self.x - portal_pos[0], self.y - portal_pos[1])
            if dist_portal < 42.0 and not self.is_supercharged:
                self.is_supercharged = True
                self.vx *= 1.35
                self.vy = -abs(self.vy) * 1.25 - 120.0
                audio_energy = min(1.0, audio_energy + 0.6)
                SOUND_STRINGS_HIGH.play()
                vfx.burst(portal_pos[0], portal_pos[1], UITheme.NEON_PURPLE, count=28, with_notes=True)
                if cosmic_vfx:
                    cosmic_vfx.trigger_drum_shockwave(portal_pos[0], portal_pos[1])

        # Floor
        if self.y > HEIGHT - 85:
            self.y = HEIGHT - 85
            self.vy *= -0.74
            self.vx *= 0.90
            self.bounces += 1
            DRUM_BANK["KICK"].play()
            vfx.trigger_shake(0.10, 3.5)
        # Ceiling
        if self.y < 95:
            self.y = 95
            self.vy *= -0.74
            self.bounces += 1
        # Right Wall
        if self.x > WIDTH - 45:
            self.x = WIDTH - 45
            self.vx *= -0.80
            self.bounces += 1
            DRUM_BANK["HIHAT"].play()
        # Left Wall
        if self.x < 45 and self.vx < 0:
            self.x = 45
            self.vx *= -0.80
            self.bounces += 1

        for chime in chimes:
            dist = math.hypot(self.x - chime.x, self.y - chime.y)
            min_dist = self.radius + chime.radius
            if dist < min_dist:
                nx = (self.x - chime.x) / max(1e-4, dist)
                ny = (self.y - chime.y) / max(1e-4, dist)

                dot = self.vx * nx + self.vy * ny
                if dot < 0:
                    rebound = 1.05 if self.is_supercharged else 0.93
                    self.vx = (self.vx - 2 * dot * nx) * rebound
                    self.vy = (self.vy - 2 * dot * ny) * rebound

                    self.x = chime.x + nx * (min_dist + 2)
                    self.y = chime.y + ny * (min_dist + 2)

                    chime.hit_glow = 1.0
                    chime.hit_count += 1
                    self.combo += 1
                    self.bounces += 1
                    self.hit_chords.add(chime.chord_group)

                    multiplier = min(6, self.combo)
                    pts = 160 * multiplier * (2 if self.is_supercharged else 1)
                    earned_points += pts

                    p_idx = chime.pitch_idx % len(HARP_BANK)
                    if self.is_supercharged:
                        p_idx = min(len(HARP_BANK) - 1, p_idx + 2)
                    HARP_BANK[p_idx].play()

                    if self.combo >= 2:
                        PIANO_WHITE_BANK[(chime.pitch_idx + 4) % len(PIANO_WHITE_BANK)].play()

                    if len(self.hit_chords) >= 3 and not triad_completed:
                        triad_completed = True
                        earned_points += 2500
                        SOUND_CHOIR.play()
                        vfx.burst(self.x, self.y, UITheme.NEON_GOLD, count=35, with_notes=True)

                    audio_energy = min(1.0, audio_energy + 0.45)
                    vfx.burst(chime.x, chime.y, chime.color, count=24, with_notes=True)
                    if cosmic_vfx:
                        cosmic_vfx.trigger_note_ripple(chime.x, chime.y, chime.color)

        if self.bounces >= self.max_bounces or (abs(self.vx) + abs(self.vy) < 30.0):
            self.alive = False

        return earned_points, triad_completed

    def draw(self, surf):
        if not self.alive:
            return

        for idx, item in enumerate(self.trail):
            tx, ty, superc = item
            ratio = idx / len(self.trail)
            alpha = int(220 * ratio)
            tr_r = max(2, int(self.radius * ratio * (0.9 if superc else 0.7)))
            t_surf = pygame.Surface((tr_r * 2 + 2, tr_r * 2 + 2), pygame.SRCALPHA)
            col = UITheme.NEON_PURPLE if superc else UITheme.NEON_GOLD
            pygame.draw.circle(t_surf, (*col[:3], alpha), (tr_r + 1, tr_r + 1), tr_r)
            surf.blit(t_surf, (tx - tr_r, ty - tr_r))

        cx, cy = int(self.x), int(self.y)
        col = UITheme.NEON_PURPLE if self.is_supercharged else UITheme.NEON_GOLD
        ShadowEngine.draw_projected_ground_shadow(surf, cx + 2, cy + 6, int(self.radius * 2), int(self.radius * 1.2), alpha=140)
        NeonFX.draw_glow_circle(surf, col, (cx, cy), int(self.radius), glow_size=18, max_alpha=240)
        pygame.draw.circle(surf, UITheme.PURE_WHITE, (cx, cy), int(self.radius))
        pygame.draw.circle(surf, col, (cx, cy), int(self.radius - 3))


class NeoSonicSlingshotGame:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.shots_left = 6
        self.time_left = 60.0
        self.is_active = False
        self.game_over = False

        self.anchor = (410, HEIGHT - 230)
        self.prong_left = (self.anchor[0] - 36, self.anchor[1] - 52)
        self.prong_right = (self.anchor[0] + 36, self.anchor[1] - 52)

        self.is_pulling = False
        self.pull_pos = list(self.anchor)
        self.max_pull_dist = 160.0

        self.debounce_release_frames = 0
        self.prev_tension = 0.0

        self.portal_pos = (780, 480)
        self.portal_anim = 0.0

        self.active_orb = None
        self.chimes = []
        self.board = WallOfFameBoard("wall_of_fame_slingshot.json", "SONIC SLINGSHOT: WALL OF FAME")
        self.show_leaderboard = False
        self.feedback_msg = ""
        self.feedback_timer = 0.0
        self.feedback_col = UITheme.NEON_GOLD

    def start_game(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.shots_left = 6
        self.time_left = 60.0
        self.is_active = True
        self.game_over = False
        self.is_pulling = False
        self.active_orb = None
        self.pull_pos = list(self.anchor)
        self.debounce_release_frames = 0
        self.show_leaderboard = False
        self.feedback_msg = "PINCH OR CLENCH FIST TO GRAB SLING!"
        self.feedback_timer = 2.4
        self.feedback_col = UITheme.NEON_CYAN
        self._spawn_chimes()

    def _spawn_chimes(self):
        self.chimes = [
            SonicChimeTarget(660, 220, 0, label="C4", chord_group="C_MAJ", is_moving=True),
            SonicChimeTarget(830, 160, 2, label="E4", chord_group="C_MAJ", is_moving=False),
            SonicChimeTarget(1010, 220, 4, label="G4", chord_group="C_MAJ", is_moving=True),
            SonicChimeTarget(710, 360, 2, label="E4", chord_group="E_MIN", is_moving=False),
            SonicChimeTarget(890, 310, 4, label="G4", chord_group="E_MIN", is_moving=True),
            SonicChimeTarget(1080, 360, 6, label="B4", chord_group="E_MIN", is_moving=False),
            SonicChimeTarget(1160, 200, 7, label="C5", chord_group="G_MAJ", is_moving=True),
            SonicChimeTarget(960, 470, 5, label="A4", chord_group="G_MAJ", is_moving=False)
        ]

    def update(self, hands, vfx, cosmic_vfx, dt):
        global audio_energy
        if not self.is_active or self.game_over:
            return

        self.time_left = max(0.0, self.time_left - dt)
        self.portal_anim += 2.8 * dt
        if self.feedback_timer > 0:
            self.feedback_timer -= dt

        for chime in self.chimes:
            chime.update(dt)

        if self.time_left <= 0.0 or (self.shots_left <= 0 and self.active_orb is None):
            self.is_active = False
            self.game_over = True
            self.show_leaderboard = True
            self.board.start_name_entry(self.score, self.max_combo)
            return

        if self.active_orb is not None:
            pts, triad_solved = self.active_orb.update(dt, self.chimes, self.portal_pos, vfx, cosmic_vfx)
            if pts > 0:
                self.score += pts
                self.combo = self.active_orb.combo
                self.max_combo = max(self.max_combo, self.combo)
                
                if triad_solved:
                    self.feedback_msg = "SYMPHONIC TRIAD SOLVED! +2500"
                    self.feedback_col = UITheme.NEON_GOLD
                    self.feedback_timer = 1.6
                elif self.combo >= 3:
                    self.feedback_msg = f"ARPEGGIO CASCADE! x{self.combo}"
                    self.feedback_col = UITheme.NEON_GREEN
                    self.feedback_timer = 0.85

            if not self.active_orb.alive:
                self.active_orb = None
                if all(c.hit_count > 0 for c in self.chimes):
                    self.score += 2000
                    self.feedback_msg = "CHORD FIELD CLEARED! +2000"
                    self.feedback_col = UITheme.NEON_CYAN
                    self.feedback_timer = 1.4
                    self._spawn_chimes()

        if self.active_orb is None and self.shots_left > 0:
            gripping_hand = None
            hand_pt = None

            for h in hands:
                target_pt = h["beam_target"] if h["is_distant"] else h["lead_tip"]
                if h["is_pinching"] or h["is_fist"]:
                    gripping_hand = h
                    hand_pt = target_pt
                    break

            if gripping_hand and hand_pt:
                self.debounce_release_frames = 0
                hx, hy = hand_pt
                dist_to_anchor = math.hypot(hx - self.anchor[0], hy - self.anchor[1])

                if not self.is_pulling and dist_to_anchor < 140.0:
                    self.is_pulling = True
                    DRUM_BANK["HIHAT"].play()

                if self.is_pulling:
                    dx = hx - self.anchor[0]
                    dy = hy - self.anchor[1]
                    pull_len = math.hypot(dx, dy)
                    if pull_len > self.max_pull_dist:
                        scale = self.max_pull_dist / pull_len
                        dx *= scale
                        dy *= scale

                    target_x = np.clip(self.anchor[0] + dx, 120, WIDTH - 120)
                    target_y = np.clip(self.anchor[1] + dy, 120, HEIGHT - 70)
                    self.pull_pos = [target_x, target_y]

                    tension = pull_len / self.max_pull_dist
                    if tension > 0.70 and self.prev_tension <= 0.70:
                        HARP_BANK[2].play()
                    elif tension > 0.40 and self.prev_tension <= 0.40:
                        HARP_BANK[0].play()
                    self.prev_tension = tension
            else:
                if self.is_pulling:
                    self.debounce_release_frames += 1
                    if self.debounce_release_frames >= 3:
                        self.is_pulling = False
                        self.debounce_release_frames = 0
                        self.prev_tension = 0.0

                        pull_dx = self.anchor[0] - self.pull_pos[0]
                        pull_dy = self.anchor[1] - self.pull_pos[1]
                        pull_dist = math.hypot(pull_dx, pull_dy)

                        if pull_dist > 35.0:
                            launch_vx = pull_dx * 7.8
                            launch_vy = pull_dy * 7.8
                            self.active_orb = SonicOrb(self.pull_pos[0], self.pull_pos[1], launch_vx, launch_vy)
                            self.shots_left -= 1
                            audio_energy = min(1.0, audio_energy + 0.5)
                            DRUM_BANK["SNARE"].play()
                            HARP_BANK[3].play()
                            vfx.burst(self.pull_pos[0], self.pull_pos[1], UITheme.NEON_GOLD, count=18)

                        self.pull_pos = list(self.anchor)

    def draw(self, surf, font_sm, font_md, font_lg, hands=[]):
        px, py = self.portal_pos
        pulse_r = int(32 + math.sin(self.portal_anim) * 5)
        ShadowEngine.draw_projected_ground_shadow(surf, px, py + 12, 60, 20, alpha=150)
        NeonFX.draw_glow_circle(surf, UITheme.NEON_PURPLE, (px, py), pulse_r, glow_size=16, max_alpha=190)
        pygame.draw.circle(surf, (16, 12, 28), (px, py), pulse_r)
        pygame.draw.circle(surf, UITheme.NEON_PURPLE, (px, py), pulse_r, 3)
        pygame.draw.circle(surf, UITheme.PURE_WHITE, (px, py), max(2, pulse_r - 8), 1)
        p_lbl = font_sm.render("OCTAVE WARP", True, UITheme.NEON_PURPLE)
        surf.blit(p_lbl, (px - p_lbl.get_width() // 2, py + pulse_r + 6))

        ShadowEngine.draw_projected_ground_shadow(surf, self.anchor[0], self.anchor[1] + 65, 96, 32, alpha=160)
        pygame.draw.line(surf, (15, 20, 32), (self.anchor[0] + 3, self.anchor[1] + 60), (self.anchor[0] + 3, self.anchor[1] - 10), 16)
        pygame.draw.line(surf, UITheme.GLASS_BORDER, (self.anchor[0], self.anchor[1] + 60), (self.anchor[0], self.anchor[1] - 10), 12)
        
        pygame.draw.line(surf, UITheme.NEON_CYAN, (self.anchor[0], self.anchor[1] - 10), self.prong_left, 7)
        pygame.draw.line(surf, UITheme.NEON_CYAN, (self.anchor[0], self.anchor[1] - 10), self.prong_right, 7)
        NeonFX.draw_glow_circle(surf, UITheme.NEON_CYAN, self.prong_left, 8, glow_size=12, max_alpha=220)
        NeonFX.draw_glow_circle(surf, UITheme.NEON_CYAN, self.prong_right, 8, glow_size=12, max_alpha=220)

        p_x, p_y = int(self.pull_pos[0]), int(self.pull_pos[1])
        band_col = UITheme.NEON_PINK if self.is_pulling else UITheme.NEON_GOLD
        pygame.draw.line(surf, (*band_col[:3], 190), self.prong_left, (p_x, p_y), 4)
        pygame.draw.line(surf, (*band_col[:3], 190), self.prong_right, (p_x, p_y), 4)
        pygame.draw.line(surf, UITheme.PURE_WHITE, self.prong_left, (p_x, p_y), 1)
        pygame.draw.line(surf, UITheme.PURE_WHITE, self.prong_right, (p_x, p_y), 1)

        if self.is_pulling:
            pull_dx = self.anchor[0] - self.pull_pos[0]
            pull_dy = self.anchor[1] - self.pull_pos[1]
            t_vx = pull_dx * 7.8
            t_vy = pull_dy * 7.8
            sim_x, sim_y = float(p_x), float(p_y)
            sim_dt = 0.045
            for dot_i in range(18):
                t_vy += 510.0 * sim_dt
                sim_x += t_vx * sim_dt
                sim_y += t_vy * sim_dt
                if sim_y > HEIGHT - 85 or sim_x > WIDTH - 40:
                    break
                dot_r = max(2, int(6 - dot_i * 0.25))
                pygame.draw.circle(surf, UITheme.NEON_CYAN, (int(sim_x), int(sim_y)), dot_r)

            NeonFX.draw_glow_circle(surf, UITheme.NEON_GOLD, (p_x, p_y), 18, glow_size=16, max_alpha=240)
            pygame.draw.circle(surf, UITheme.PURE_WHITE, (p_x, p_y), 15)

        for chime in self.chimes:
            chime.draw(surf, font_sm, font_md)

        if self.active_orb:
            self.active_orb.draw(surf)

        hud_l = pygame.Rect(25, 20, 250, 68)
        NeonFX.draw_glass_card(surf, hud_l, border_color=UITheme.NEON_CYAN, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_md.render(f"SCORE {self.score}", True, UITheme.PURE_WHITE), (38, 28))
        surf.blit(font_sm.render(f"COMBO x{self.combo} RESONANCE", True, UITheme.NEON_GOLD), (38, 54))

        hud_r = pygame.Rect(WIDTH - 255, 20, 230, 68)
        NeonFX.draw_glass_card(surf, hud_r, border_color=UITheme.NEON_GOLD, border_width=2, radius=14, elevation=14, is_3d=True)
        surf.blit(font_sm.render(f"TIME {int(self.time_left)}s", True, UITheme.PURE_WHITE), (hud_r.x + 14, hud_r.y + 12))
        surf.blit(font_md.render(f"SHOTS: {self.shots_left} ORBS", True, UITheme.NEON_CYAN), (hud_r.x + 14, hud_r.y + 36))

        if self.feedback_timer > 0:
            callout = font_md.render(self.feedback_msg, True, self.feedback_col)
            surf.blit(callout, (WIDTH // 2 - callout.get_width() // 2, 90))

        if self.show_leaderboard:
            self.board.draw(surf, font_sm, font_md, font_lg, hands=hands)

# ==================================================================================================
# 25. LIVE LOOP STATION & MULTI-TRACK STEP SEQUENCER WITH 3D TACTILE PADS
# ==================================================================================================
class SequencerStepNode:
    def __init__(self, step_idx, track_idx, pos_x, pos_y, radius=12):
        self.step_idx = step_idx
        self.track_idx = track_idx
        self.rect = pygame.Rect(pos_x - radius, pos_y - radius, radius * 2, radius * 2)
        self.radius = radius
        self.is_active = False
        self.sound_obj = None
        self.glow = 0.0
        self.hovered = False
        self.cooldown = 0.0

    def toggle(self, default_sound):
        self.is_active = not self.is_active
        if self.is_active:
            self.sound_obj = default_sound
            self.glow = 1.0
        else:
            self.sound_obj = None

    def update(self, dt):
        if self.glow > 0.0:
            self.glow = max(0.0, self.glow - 3.5 * dt)
        if self.cooldown > 0.0:
            self.cooldown = max(0.0, self.cooldown - dt)

    def draw(self, surf, color, is_current_step):
        center = self.rect.center
        draw_r = self.radius + int(self.glow * 6)
        
        ShadowEngine.draw_projected_ground_shadow(surf, center[0] + 2, center[1] + 4, draw_r * 2, int(draw_r * 1.2), alpha=120)

        if is_current_step:
            NeonFX.draw_glow_circle(surf, UITheme.PURE_WHITE, center, draw_r + 4, glow_size=12, max_alpha=200)
            pygame.draw.circle(surf, UITheme.PURE_WHITE, center, draw_r + 2, 2)

        if self.is_active:
            NeonFX.draw_glow_circle(surf, color, center, draw_r, glow_size=14, max_alpha=180)
            pygame.draw.circle(surf, color, center, draw_r)
            pygame.draw.circle(surf, UITheme.PURE_WHITE, center, max(2, draw_r - 4))
            pygame.draw.circle(surf, (255, 255, 255, 220), (center[0] - draw_r // 3, center[1] - draw_r // 3), max(1, draw_r // 4))
        else:
            base_col = (40, 52, 78) if self.hovered else (22, 30, 48)
            border_col = color if self.hovered else (50, 70, 105)
            pygame.draw.circle(surf, base_col, center, self.radius)
            pygame.draw.circle(surf, border_col, center, self.radius, 2)
            pygame.draw.arc(surf, UITheme.GLASS_HIGHLIGHT, (center[0] - self.radius, center[1] - self.radius, self.radius * 2, self.radius * 2), 0.8, 2.3, 1)

class LiveInstrumentDeckPad:
    def __init__(self, track_idx, rect, name, freq, sound_obj, color):
        self.track_idx = track_idx
        self.rect = pygame.Rect(rect)
        self.name = name
        self.freq = freq
        self.sound_obj = sound_obj
        self.color = color
        self.glow = 0.0
        self.hovered = False
        self.cooldown = 0.0

    def trigger(self, loop_engine, ai_copilot, vfx):
        global audio_energy
        if self.cooldown <= 0.0:
            self.cooldown = 0.22
            self.glow = 1.0
            audio_energy = min(1.0, audio_energy + 0.45)
            self.sound_obj.play()
            vfx.burst(self.rect.centerx, self.rect.centery, self.color, count=16, with_notes=True)

            if ai_copilot:
                ai_copilot.register_note(self.freq, self.name)

            if loop_engine.is_recording:
                loop_engine.record_tap_note(self.sound_obj, self.track_idx)

    def update(self, dt):
        if self.glow > 0.0:
            self.glow = max(0.0, self.glow - 3.2 * dt)
        if self.cooldown > 0.0:
            self.cooldown = max(0.0, self.cooldown - dt)

    def draw(self, surf, font_sm, font_md):
        b_col = UITheme.PURE_WHITE if self.glow > 0.3 else self.color
        NeonFX.draw_glass_card(surf, self.rect, border_color=b_col, border_width=2 if self.hovered else 1, radius=12, elevation=8, is_3d=True)
        if self.glow > 0.15:
            NeonFX.draw_glow_circle(surf, self.color, self.rect.center, 22, glow_size=14, max_alpha=160)

        t_lbl = font_md.render(self.name, True, UITheme.PURE_WHITE)
        surf.blit(t_lbl, (self.rect.centerx - t_lbl.get_width() // 2, self.rect.y + 8))

        sub = font_sm.render(f"TRACK {self.track_idx + 1} | PINCH/CLICK", True, self.color)
        surf.blit(sub, (self.rect.centerx - sub.get_width() // 2, self.rect.y + 34))

class LoopStationEngine:
    def __init__(self, bpm=108):
        self.bpm = bpm
        self.total_steps = 16
        self.step_time = (60.0 / self.bpm) / 4.0
        self.current_step = 0
        self.timer = 0.0
        self.is_playing = True
        self.active_track = 0
        self.is_recording = False
        self.recorded_events_count = 0

        self.track_names = ["808 DRUMS", "CYBER BASS", "SYNTH CHORDS", "AETHER HARP"]
        self.track_colors = [UITheme.NEON_PINK, UITheme.NEON_PURPLE, UITheme.NEON_CYAN, UITheme.NEON_GOLD]
        self.default_sounds = [
            DRUM_BANK["KICK"],
            PIANO_WHITE_BANK[0],
            PIANO_WHITE_BANK[4],
            HARP_BANK[5]
        ]
        self.track_freqs = [65.41, 130.81, 261.63, 392.00]

        self.matrix = []
        for t_idx in range(4):
            track_nodes = []
            for s_idx in range(16):
                nx = 520 + s_idx * 42
                ny = 155 + t_idx * 60
                node = SequencerStepNode(s_idx, t_idx, nx, ny, radius=13)
                track_nodes.append(node)
            self.matrix.append(track_nodes)

        self.track_mutes = [False] * 4
        self.track_solos = [False] * 4
        self.track_volumes = [1.0] * 4

        # 4 Interactive Live Performance Pads to Touch/Pinch
        self.live_pads = [
            LiveInstrumentDeckPad(0, (350, 420, 205, 58), "808 KICK", 65.41, DRUM_BANK["KICK"], UITheme.NEON_PINK),
            LiveInstrumentDeckPad(1, (565, 420, 205, 58), "CYBER BASS", 130.81, PIANO_WHITE_BANK[0], UITheme.NEON_PURPLE),
            LiveInstrumentDeckPad(2, (780, 420, 205, 58), "SYNTH CHORD", 261.63, PIANO_WHITE_BANK[4], UITheme.NEON_CYAN),
            LiveInstrumentDeckPad(3, (995, 420, 205, 58), "CELESTIAL HARP", 392.00, HARP_BANK[5], UITheme.NEON_GOLD)
        ]

        self.play_btn_rect = pygame.Rect(350, 492, 160, 36)
        self.rec_btn_rect = pygame.Rect(520, 492, 175, 36)
        self.clear_btn_rect = pygame.Rect(705, 492, 135, 36)
        self._preset_demo_beat()

    def _preset_demo_beat(self):
        for s in [0, 4, 8, 12]:
            self.matrix[0][s].is_active = True
            self.matrix[0][s].sound_obj = DRUM_BANK["KICK"]
        for s in [4, 12]:
            self.matrix[0][s].sound_obj = DRUM_BANK["SNARE"]

        for s in [0, 3, 6, 10, 14]:
            self.matrix[1][s].is_active = True
            self.matrix[1][s].sound_obj = PIANO_WHITE_BANK[0]

        for s in [2, 6, 10, 14]:
            self.matrix[2][s].is_active = True
            self.matrix[2][s].sound_obj = PIANO_WHITE_BANK[4]
        for s in [0, 4, 7, 11, 13]:
            self.matrix[3][s].is_active = True
            self.matrix[3][s].sound_obj = HARP_BANK[s % len(HARP_BANK)]

    def record_tap_note(self, sound_obj, track_idx=None):
        if not self.is_recording:
            return
        t = self.active_track if track_idx is None else track_idx
        step = self.current_step
        self.matrix[t][step].is_active = True
        self.matrix[t][step].sound_obj = sound_obj
        self.matrix[t][step].glow = 1.0
        self.recorded_events_count += 1

    def clear_track(self, track_idx):
        for node in self.matrix[track_idx]:
            node.is_active = False
            node.sound_obj = None

    def clear_all(self):
        for t in range(4):
            self.clear_track(t)
        self.recorded_events_count = 0

    def set_bpm(self, new_bpm):
        self.bpm = np.clip(new_bpm, 60.0, 180.0)
        self.step_time = (60.0 / self.bpm) / 4.0

    def update(self, dt, vfx, ai_copilot=None):
        global audio_energy
        for track in self.matrix:
            for node in track:
                node.update(dt)
        for pad in self.live_pads:
            pad.update(dt)

        if not self.is_playing:
            return

        self.timer += dt
        if self.timer >= self.step_time:
            self.timer -= self.step_time
            self.current_step = (self.current_step + 1) % self.total_steps

            any_solo = any(self.track_solos)
            for t_idx in range(4):
                if self.track_mutes[t_idx]:
                    continue
                if any_solo and not self.track_solos[t_idx]:
                    continue

                node = self.matrix[t_idx][self.current_step]
                if node.is_active and node.sound_obj is not None:
                    snd = node.sound_obj
                    snd.set_volume(self.track_volumes[t_idx])
                    snd.play()
                    node.glow = 1.0
                    audio_energy = min(1.0, audio_energy + 0.35)
                    vfx.burst(node.rect.centerx, node.rect.centery, self.track_colors[t_idx], count=6)
                    if ai_copilot:
                        ai_copilot.register_note(self.track_freqs[t_idx], self.track_names[t_idx])

    def process_touch_input(self, tx, ty, is_pinch, is_fist, ai_copilot, vfx):
        global audio_energy
        # 1. Check Live Instrument Performance Pads
        for pad in self.live_pads:
            hitbox = pad.rect.inflate(18, 18)
            if hitbox.collidepoint(tx, ty):
                pad.hovered = True
                if is_pinch or is_fist:
                    pad.trigger(self, ai_copilot, vfx)
                    return True
            else:
                pad.hovered = False

        # 2. Check Transport Controls
        if is_pinch or is_fist:
            if self.play_btn_rect.collidepoint(tx, ty):
                self.is_playing = not self.is_playing
                return True
            if self.rec_btn_rect.collidepoint(tx, ty):
                self.is_recording = not self.is_recording
                return True
            if self.clear_btn_rect.collidepoint(tx, ty):
                self.clear_all()
                return True

        # 3. Check Track Header Selection, Mute & Solo
        for t_idx in range(4):
            ty_local = 155 + t_idx * 60
            trk_card = pygame.Rect(350, ty_local - 20, 140, 40)
            if (is_pinch or is_fist) and trk_card.collidepoint(tx, ty):
                m_circle = pygame.Rect(trk_card.right - 36, trk_card.centery - 10, 18, 18)
                s_circle = pygame.Rect(trk_card.right - 16, trk_card.centery - 10, 18, 18)
                if m_circle.collidepoint(tx, ty):
                    self.track_mutes[t_idx] = not self.track_mutes[t_idx]
                elif s_circle.collidepoint(tx, ty):
                    self.track_solos[t_idx] = not self.track_solos[t_idx]
                else:
                    self.active_track = t_idx
                return True

        # 4. Check Sequencer Step Nodes (With Generous Hitbox + Debounce)
        for t_idx in range(4):
            for s_idx in range(16):
                node = self.matrix[t_idx][s_idx]
                hitbox = node.rect.inflate(26, 26)
                if hitbox.collidepoint(tx, ty):
                    node.hovered = True
                    if (is_pinch or is_fist) and node.cooldown <= 0.0:
                        node.cooldown = 0.32
                        snd = self.default_sounds[t_idx]
                        node.toggle(snd)
                        if node.is_active:
                            snd.play()
                            audio_energy = min(1.0, audio_energy + 0.35)
                            vfx.burst(node.rect.centerx, node.rect.centery, self.track_colors[t_idx], count=12)
                            if ai_copilot:
                                ai_copilot.register_note(self.track_freqs[t_idx], self.track_names[t_idx])
                        return True
                else:
                    node.hovered = False
        return False

    def handle_click(self, mx, my, ai_copilot, vfx):
        return self.process_touch_input(mx, my, is_pinch=True, is_fist=False, ai_copilot=ai_copilot, vfx=vfx)

    def draw(self, surf, font_sm, font_md):
        panel_rect = pygame.Rect(330, 80, 910, 480)
        NeonFX.draw_glass_card(surf, panel_rect, border_color=UITheme.NEON_CYAN, border_width=2, radius=22, elevation=18, is_3d=True)

        ribbon_rect = pygame.Rect(panel_rect.centerx - 220, 68, 440, 38)
        NeonFX.draw_hud_pill(surf, ribbon_rect, border_color=UITheme.NEON_PURPLE, radius=12, elevation=6)
        t_seq = font_md.render("LIVE LOOP STATION & STEP SEQUENCER", True, UITheme.PURE_WHITE)
        surf.blit(t_seq, (panel_rect.centerx - t_seq.get_width() // 2, 74))

        for t_idx in range(4):
            ty = 155 + t_idx * 60
            is_active_trk = (t_idx == self.active_track)
            col = self.track_colors[t_idx]

            trk_card = pygame.Rect(350, ty - 20, 140, 40)
            border_col = col if is_active_trk else UITheme.GLASS_BORDER
            NeonFX.draw_glass_card(surf, trk_card, border_color=border_col, border_width=2 if is_active_trk else 1, radius=10, show_brackets=False, elevation=6, is_3d=True)

            lbl = font_sm.render(self.track_names[t_idx], True, col if is_active_trk else UITheme.PURE_WHITE)
            surf.blit(lbl, (trk_card.x + 8, trk_card.centery - lbl.get_height() // 2))

            m_col = UITheme.NEON_PINK if self.track_mutes[t_idx] else (50, 60, 80)
            s_col = UITheme.NEON_GOLD if self.track_solos[t_idx] else (50, 60, 80)
            m_txt = font_sm.render("M", True, UITheme.PURE_WHITE if self.track_mutes[t_idx] else UITheme.TEXT_MUTED)
            s_txt = font_sm.render("S", True, UITheme.PURE_WHITE if self.track_solos[t_idx] else UITheme.TEXT_MUTED)

            ShadowEngine.draw_projected_ground_shadow(surf, trk_card.right - 28, trk_card.centery + 4, 16, 8, alpha=110)
            pygame.draw.circle(surf, m_col, (trk_card.right - 28, trk_card.centery), 8)
            surf.blit(m_txt, (trk_card.right - 32, trk_card.centery - m_txt.get_height() // 2))

            ShadowEngine.draw_projected_ground_shadow(surf, trk_card.right - 10, trk_card.centery + 4, 16, 8, alpha=110)
            pygame.draw.circle(surf, s_col, (trk_card.right - 10, trk_card.centery), 8)
            surf.blit(s_txt, (trk_card.right - 14, trk_card.centery - s_txt.get_height() // 2))

            for s_idx in range(16):
                node = self.matrix[t_idx][s_idx]
                is_curr = (s_idx == self.current_step and self.is_playing)
                node.draw(surf, col, is_curr)

        # Draw 4 Interactive Live Performance Pads
        for pad in self.live_pads:
            pad.draw(surf, font_sm, font_md)

        # Transport Strip Buttons
        NeonFX.draw_hud_pill(surf, self.play_btn_rect, border_color=UITheme.NEON_GREEN if self.is_playing else UITheme.NEON_ORANGE, radius=8, elevation=4)
        play_lbl = "▶ PLAYING" if self.is_playing else "⏸ PAUSED"
        t_play = font_sm.render(play_lbl, True, UITheme.NEON_GREEN if self.is_playing else UITheme.NEON_ORANGE)
        surf.blit(t_play, (self.play_btn_rect.centerx - t_play.get_width() // 2, self.play_btn_rect.centery - t_play.get_height() // 2))

        NeonFX.draw_hud_pill(surf, self.rec_btn_rect, border_color=UITheme.NEON_PINK if self.is_recording else UITheme.GLASS_BORDER, radius=8, elevation=4)
        rec_lbl = "● REC ON TOUCH" if self.is_recording else "○ REC OFF"
        t_rec = font_sm.render(rec_lbl, True, UITheme.NEON_PINK if self.is_recording else UITheme.TEXT_MUTED)
        surf.blit(t_rec, (self.rec_btn_rect.centerx - t_rec.get_width() // 2, self.rec_btn_rect.centery - t_rec.get_height() // 2))

        NeonFX.draw_hud_pill(surf, self.clear_btn_rect, border_color=UITheme.GLASS_BORDER, radius=8, elevation=4)
        t_clr = font_sm.render("CLEAR ALL", True, UITheme.PURE_WHITE)
        surf.blit(t_clr, (self.clear_btn_rect.centerx - t_clr.get_width() // 2, self.clear_btn_rect.centery - t_clr.get_height() // 2))

        bpm_txt = font_sm.render(f"{int(self.bpm)} BPM | STEP {self.current_step + 1}/16 | NOTES: {self.recorded_events_count}", True, UITheme.NEON_CYAN)
        surf.blit(bpm_txt, (860, self.play_btn_rect.centery - bpm_txt.get_height() // 2))

        hint = font_sm.render("PINCH / CLICK PADS TO PLAY & COMPOSE LIVE | [SPACE] PLAY | [R] REC | [C] CLEAR", True, UITheme.TEXT_MUTED)
        surf.blit(hint, (panel_rect.centerx - hint.get_width() // 2, panel_rect.bottom - 22))

# ==================================================================================================
# 26. HOLOGRAPHIC AI MUSIC CO-PILOT & HARMONIC KEY ANALYZER WITH 3D GLASS WIDGET
# ==================================================================================================
class HarmonicKeyEstimator:
    PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 2.69, 3.34, 3.17, 3.28]

    @classmethod
    def hz_to_midi(cls, freq):
        if freq <= 0: return None
        return int(round(69 + 12 * math.log2(freq / 440.0)))

    @classmethod
    def hz_to_pitch_class(cls, freq):
        midi = cls.hz_to_midi(freq)
        if midi is None: return None
        return midi % 12

    @classmethod
    def detect_key(cls, pitch_history):
        if not pitch_history:
            return "C Major", 0.0

        chroma = [0.0] * 12
        for _, hz, _ in pitch_history:
            pc = cls.hz_to_pitch_class(hz)
            if pc is not None:
                chroma[pc] += 1.0

        total = sum(chroma)
        if total <= 0:
            return "C Major", 0.0
        chroma = [c / total for c in chroma]

        best_key = "C Major"
        best_corr = -1.0

        for root in range(12):
            rot_maj = cls.MAJOR_PROFILE[-root:] + cls.MAJOR_PROFILE[:-root]
            corr_maj = np.corrcoef(chroma, rot_maj)[0, 1]
            if not np.isnan(corr_maj) and corr_maj > best_corr:
                best_corr = corr_maj
                best_key = f"{cls.PITCH_NAMES[root]} Major"

            rot_min = cls.MINOR_PROFILE[-root:] + cls.MINOR_PROFILE[:-root]
            corr_min = np.corrcoef(chroma, rot_min)[0, 1]
            if not np.isnan(corr_min) and corr_min > best_corr:
                best_corr = corr_min
                best_key = f"{cls.PITCH_NAMES[root]} Minor"

        return best_key, max(0.0, float(best_corr))

class AIMusicAssistant:
    def __init__(self):
        self.note_history = deque(maxlen=48)
        self.detected_key = "C Major"
        self.key_confidence = 0.85
        self.mood = "Harmonic Ambient"
        self.energy_level = 0.0
        self.density = 0.0
        self.ai_tip = "Touch or pinch any instrument to begin composition."
        self.analysis_timer = 0.0
        self.sparkline_data = deque([20.0] * 20, maxlen=20)

    def register_note(self, pitch_hz, inst_name):
        self.note_history.append((time.time(), pitch_hz, inst_name))

    def update(self, dt):
        self.analysis_timer += dt
        if self.analysis_timer > 1.0:
            self.analysis_timer = 0.0
            self._evaluate_performance()

    def _evaluate_performance(self):
        if not self.note_history:
            self.energy_level = 0.0
            self.mood = "Awaiting Touch..."
            self.ai_tip = "Touch or pinch any instrument to begin composition."
            self.sparkline_data.append(5.0)
            return

        now = time.time()
        recent = [n for n in self.note_history if now - n[0] < 4.0]
        self.density = len(recent) / 4.0

        avg_pitch = sum(n[1] for n in recent) / max(1, len(recent)) if recent else 220.0
        self.energy_level = float(np.clip(self.density * 18.0 + (avg_pitch / 12.0), 0.0, 100.0))
        self.sparkline_data.append(self.energy_level)

        self.detected_key, self.key_confidence = HarmonicKeyEstimator.detect_key(recent)

        if self.energy_level > 75:
            self.mood = "Energetic Crescendo"
            self.ai_tip = "High intensity! Sustained chords on harp or brass will elevate climax."
        elif avg_pitch > 350:
            self.mood = "Airy & Dreamy"
            self.ai_tip = "Add low-octave bass or 808 kick drops to balance high frequency shimmer."
        elif self.density > 4.0:
            self.mood = "Virtuoso Rapid Riffs"
            self.ai_tip = "Great speed! Try pausing briefly to give melodic phrases room to breathe."
        else:
            self.mood = "Warm Contemplative"
            self.ai_tip = "Solid harmonic foundation. Introduce flute or violin counter-melodies."

    def draw_glass_widget(self, surf, font_sm, font_md, x=30, y=140):
        w, h = 290, 270
        card_rect = pygame.Rect(x, y, w, h)
        NeonFX.draw_glass_card(surf, card_rect, border_color=UITheme.NEON_PURPLE, border_width=2, radius=18, elevation=14, is_3d=True)

        pill_header = pygame.Rect(x + 16, y + 10, w - 32, 28)
        NeonFX.draw_hud_pill(surf, pill_header, border_color=UITheme.NEON_PURPLE, radius=8, elevation=4)
        t_title = font_sm.render("AETHERIA AI CO-PILOT", True, UITheme.NEON_PURPLE)
        surf.blit(t_title, (pill_header.centerx - t_title.get_width() // 2, pill_header.centery - t_title.get_height() // 2))

        metrics = [
            ("KEY DETECTED:", self.detected_key, UITheme.NEON_CYAN),
            ("CONFIDENCE:", f"{int(self.key_confidence * 100)}%", UITheme.NEON_GREEN),
            ("HARMONIC MOOD:", self.mood, UITheme.NEON_GOLD),
            ("ENERGY RATING:", f"{int(self.energy_level)}%", UITheme.NEON_PINK)
        ]
        for idx, (label, val, col) in enumerate(metrics):
            yy = y + 46 + idx * 26
            surf.blit(font_sm.render(label, True, UITheme.TEXT_MUTED), (x + 14, yy))
            surf.blit(font_sm.render(val, True, col), (x + 140, yy))

        graph_rect = pygame.Rect(x + 14, y + 154, w - 28, 32)
        pygame.draw.rect(surf, (14, 20, 34), graph_rect, border_radius=6)
        pygame.draw.rect(surf, (30, 45, 70), graph_rect, 1, border_radius=6)

        pts = []
        n_pts = len(self.sparkline_data)
        if n_pts > 1:
            dx = graph_rect.width / float(n_pts - 1)
            for i, val in enumerate(self.sparkline_data):
                px = graph_rect.x + i * dx
                py = graph_rect.bottom - 2 - (val / 100.0) * (graph_rect.height - 4)
                pts.append((px, py))
            if len(pts) >= 2:
                pygame.draw.lines(surf, UITheme.NEON_PINK, False, pts, 2)

        pygame.draw.line(surf, (40, 56, 92), (x + 14, y + 194), (x + w - 14, y + 194), 1)
        surf.blit(font_sm.render("AI SUGGESTION:", True, UITheme.PURE_WHITE), (x + 14, y + 200))

        words = self.ai_tip.split(" ")
        line1 = " ".join(words[:5])
        line2 = " ".join(words[5:])
        surf.blit(font_sm.render(line1, True, (215, 225, 245)), (x + 14, y + 220))
        if line2:
            surf.blit(font_sm.render(line2, True, (215, 225, 245)), (x + 14, y + 240))

# ==================================================================================================
# 27. MUSICAL DNA RADAR PASSPORT & QR CERTIFICATE SYSTEM (3D PERSPECTIVE)
# ==================================================================================================
class MusicalDNAGenerator:
    def __init__(self):
        self.rhythm_score = 92
        self.harmony_score = 95
        self.energy_score = 86
        self.creativity_score = 94
        self.precision_score = 90
        self.versatility_score = 88
        
        self.total_notes = 0
        self.session_time = 0.0
        self.mood_title = "NEO-SYMPHONIC VIRTUOSO"
        self.qr_surf = self._make_qr()

    def _make_qr(self):
        if not HAS_QRCODE:
            # Safe white placeholder box if qrcode is not installed
            placeholder = pygame.Surface((100, 100))
            placeholder.fill((255, 255, 255))
            pygame.draw.rect(placeholder, (0, 0, 0), (10, 10, 80, 80), 3)
            return placeholder

        qr = qrcode.QRCode(box_size=3, border=2)
        qr.add_data("https://aetheria-grandprix.sulam2026.edu/certificate")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return pygame.image.fromstring(img.tobytes(), img.size, "RGB")

    def record_performance_data(self, notes_count, duration, energy_avg):
        self.total_notes = max(28, notes_count)
        self.session_time = max(10.0, duration)
        self.rhythm_score = random.randint(88, 99)
        self.harmony_score = random.randint(90, 99)
        self.energy_score = int(np.clip(energy_avg * 100, 75, 98))
        self.creativity_score = random.randint(89, 98)
        self.precision_score = random.randint(85, 97)
        self.versatility_score = random.randint(87, 98)

        titles = [
            "SOLOIST CONDUCTOR", "CYBER MAESTRO", "AETHER RESONATOR",
            "HARMONIC VIRTUOSO", "NEO-SYMPHONIC ARCHITECT", "ORCHESTRAL PILOT"
        ]
        self.mood_title = random.choice(titles)

    def draw_dna_certificate(self, surf, font_sm, font_md, font_lg):
        card = pygame.Rect(WIDTH // 2 - 340, 50, 680, 600)
        NeonFX.draw_glass_card(surf, card, border_color=UITheme.NEON_GOLD, border_width=3, radius=26, elevation=24, is_3d=True)
        draw_ribbon(surf, font_lg, "YOUR AETHERIA MUSICAL DNA", WIDTH // 2, 50, 520, 56, UITheme.NEON_PURPLE)

        # 3D Radar Chart Engine (6 Dimensional Axes)
        cx, cy = WIDTH // 2 - 140, 250
        max_r = 95
        axes = [
            ("RHYTHM", self.rhythm_score, 0),
            ("HARMONY", self.harmony_score, math.pi / 3.0),
            ("ENERGY", self.energy_score, 2.0 * math.pi / 3.0),
            ("CREATIVITY", self.creativity_score, math.pi),
            ("PRECISION", self.precision_score, 4.0 * math.pi / 3.0),
            ("VERSATILITY", self.versatility_score, 5.0 * math.pi / 3.0)
        ]

        # 3D Radar Concentric Grid with Ambient Shadows
        for r_step in [0.33, 0.66, 1.0]:
            grid_pts = [(cx + math.cos(a) * max_r * r_step, cy + math.sin(a) * max_r * r_step) for _, _, a in axes]
            pygame.draw.polygon(surf, (45, 60, 90), grid_pts, 1)

        for name, score, a in axes:
            rx = cx + math.cos(a) * max_r
            ry = cy + math.sin(a) * max_r
            pygame.draw.line(surf, (55, 75, 115), (cx, cy), (rx, ry), 1)

            lx = cx + math.cos(a) * (max_r + 22)
            ly = cy + math.sin(a) * (max_r + 22)
            t_ax = font_sm.render(name, True, UITheme.TEXT_MUTED)
            surf.blit(t_ax, (lx - t_ax.get_width() // 2, ly - t_ax.get_height() // 2))

        # Filled DNA Score Polygon with Soft Drop Shadow
        dna_pts = [(cx + math.cos(a) * max_r * (score / 100.0), cy + math.sin(a) * max_r * (score / 100.0)) for _, score, a in axes]
        shd_dna_pts = [(p[0] + 4, p[1] + 6) for p in dna_pts]
        
        shd_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(shd_surf, (0, 0, 0, 110), shd_dna_pts)
        surf.blit(shd_surf, (0, 0))

        dna_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(dna_surf, (*UITheme.NEON_CYAN[:3], 115), dna_pts)
        pygame.draw.polygon(dna_surf, UITheme.NEON_CYAN, dna_pts, 3)
        surf.blit(dna_surf, (0, 0))

        for pt in dna_pts:
            NeonFX.draw_glow_circle(surf, UITheme.NEON_GOLD, pt, 5, glow_size=8, max_alpha=200)

        # Right Stat Column
        stat_x = WIDTH // 2 + 50
        stats = [
            ("RHYTHM:", f"{self.rhythm_score}%", UITheme.NEON_CYAN),
            ("HARMONY:", f"{self.harmony_score}%", UITheme.NEON_PURPLE),
            ("ENERGY:", f"{self.energy_score}%", UITheme.NEON_PINK),
            ("CREATIVITY:", f"{self.creativity_score}%", UITheme.NEON_GOLD),
            ("PRECISION:", f"{self.precision_score}%", UITheme.NEON_GREEN),
            ("TOTAL NOTES:", str(self.total_notes), UITheme.PURE_WHITE),
            ("DESIGNATION:", self.mood_title, UITheme.NEON_GOLD)
        ]
        for idx, (lbl, val, col) in enumerate(stats):
            yy = 140 + idx * 32
            surf.blit(font_sm.render(lbl, True, UITheme.TEXT_MUTED), (stat_x, yy))
            surf.blit(font_md.render(val, True, col), (stat_x + 130, yy - 3))

        # 3D Raised QR Passport Frame
        qr_box = pygame.Rect(WIDTH // 2 - 50, 420, 100, 100)
        ShadowEngine.blit_drop_shadow(surf, qr_box.inflate(8, 8), radius=10, elevation=12)
        pygame.draw.rect(surf, UITheme.PURE_WHITE, qr_box.inflate(8, 8), border_radius=8)
        surf.blit(self.qr_surf, qr_box.topleft)

        nav_txt = font_sm.render("SCAN QR TO DOWNLOAD OFFICIAL CERTIFICATE  |  [ESC] MAIN HUB", True, UITheme.PURE_WHITE)
        surf.blit(nav_txt, (WIDTH // 2 - nav_txt.get_width() // 2, 590))

# ==================================================================================================
# 28. LIVE CONCERT PERFORMANCE MODE & AUDIENCE EXCITABILITY ENGINE
# ==================================================================================================
class LivePerformanceMode:
    def __init__(self):
        self.countdown = 3.99
        self.is_running = False
        self.is_completed = False
        self.duration = 45.0
        self.time_left = 45.0
        self.notes_played = 0
        self.crowd_excitement = 50.0
        self.fever_mode = False
        self.fever_timer = 0.0

    def start_performance(self):
        self.countdown = 3.99
        self.is_running = True
        self.is_completed = False
        self.time_left = self.duration
        self.notes_played = 0
        self.crowd_excitement = 50.0
        self.fever_mode = False
        self.fever_timer = 0.0

    def update(self, hands, vfx, dna_engine, dt):
        global audio_energy
        if not self.is_running or self.is_completed:
            return

        if self.countdown > 0.0:
            self.countdown -= dt
            return

        self.time_left -= dt
        self.crowd_excitement = np.clip(self.crowd_excitement + (audio_energy * 38.0 - 11.0) * dt, 0.0, 100.0)

        if self.crowd_excitement > 88.0 and not self.fever_mode:
            self.fever_mode = True
            self.fever_timer = 6.0
            vfx.burst(WIDTH // 2, HEIGHT // 2, UITheme.NEON_GOLD, count=40, with_notes=True)

        if self.fever_mode:
            self.fever_timer -= dt
            if self.fever_timer <= 0.0:
                self.fever_mode = False

        for h in hands:
            hx, hy = h["lead_tip"]
            if random.random() < 0.18:
                pitch_idx = int(np.clip((hx / WIDTH) * len(HARP_FREQS), 0, len(HARP_FREQS) - 1))
                HARP_BANK[pitch_idx].play()
                col = UITheme.NEON_GOLD if self.fever_mode else (UITheme.NEON_CYAN if h["is_left"] else UITheme.NEON_PINK)
                vfx.burst(hx, hy, col, count=5, with_notes=True)
                self.notes_played += 1
                audio_energy = min(1.0, audio_energy + 0.15)

        if self.time_left <= 0.0:
            self.is_running = False
            self.is_completed = True
            dna_engine.record_performance_data(self.notes_played, self.duration, self.crowd_excitement / 100.0)

    def draw(self, surf, font_sm, font_md, font_lg):
        if self.countdown > 0.0:
            count_num = int(self.countdown) + 1
            lbl = font_lg.render(f"STAGE OPENS IN: {count_num}", True, UITheme.NEON_GOLD)
            surf.blit(lbl, (WIDTH // 2 - lbl.get_width() // 2, HEIGHT // 2 - 30))
            return

        spot_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        excitement_ratio = self.crowd_excitement / 100.0
        alpha_beam = int(45 + excitement_ratio * 75)

        col_left = UITheme.NEON_GOLD if self.fever_mode else UITheme.NEON_PINK
        col_right = UITheme.NEON_GOLD if self.fever_mode else UITheme.NEON_CYAN

        pygame.draw.polygon(spot_surf, (*col_left[:3], alpha_beam), [(200, 0), (0, HEIGHT), (520, HEIGHT)])
        pygame.draw.polygon(spot_surf, (*col_right[:3], alpha_beam), [(WIDTH - 200, 0), (WIDTH - 520, HEIGHT), (WIDTH, HEIGHT)])
        surf.blit(spot_surf, (0, 0))

        # 3D Audience Depth Wave with Cast Ground Shadows
        t_wave = pygame.time.get_ticks() * 0.005
        for aud_i in range(36):
            ax = aud_i * 38
            ay = HEIGHT - 45 + int(math.sin(t_wave + aud_i * 0.45) * 10 * excitement_ratio)
            ShadowEngine.draw_projected_ground_shadow(surf, ax, ay + 18, 38, 14, alpha=150)
            pygame.draw.circle(surf, (16, 20, 32), (ax, ay), 18)
            pygame.draw.ellipse(surf, (12, 16, 26), (ax - 22, ay + 14, 44, 40))

        header_lbl = "★ FEVER MODE CONCERT ★" if self.fever_mode else "AETHERIA LIVE CONCERT STAGE"
        draw_ribbon(surf, font_md, header_lbl, WIDTH // 2, 35, 460, 44, UITheme.NEON_GOLD if self.fever_mode else UITheme.NEON_PINK)

        # 3D Stadium Excitement Meter
        bar_w = 420
        bar_x = WIDTH // 2 - bar_w // 2
        meter_rect = pygame.Rect(bar_x, 68, bar_w, 18)
        ShadowEngine.blit_drop_shadow(surf, meter_rect, radius=9, elevation=8)
        pygame.draw.rect(surf, (16, 22, 38), meter_rect, border_radius=9)
        
        meter_col = UITheme.NEON_GOLD if self.fever_mode else (UITheme.NEON_GREEN if self.crowd_excitement > 50 else UITheme.NEON_ORANGE)
        fill_w = int(bar_w * excitement_ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x, 68, fill_w, 18)
            pygame.draw.rect(surf, meter_col, fill_rect, border_radius=9)
            pygame.draw.line(surf, UITheme.GLASS_HIGHLIGHT, (fill_rect.x + 6, fill_rect.y + 1), (fill_rect.right - 6, fill_rect.y + 1), 1)
            NeonFX.draw_glow_circle(surf, meter_col, (bar_x + fill_w, 77), 8, glow_size=12, max_alpha=200)

        timer_txt = font_md.render(f"TIME REMAINING: {int(self.time_left)}s  |  NOTES: {self.notes_played}", True, UITheme.PURE_WHITE)
        surf.blit(timer_txt, (WIDTH // 2 - timer_txt.get_width() // 2, 96))

# ==================================================================================================
# 29. EXHIBITION BOOTH KIOSK OPERATOR CONTROL PANEL
# ==================================================================================================
class BoothKioskOperatorPanel:
    def __init__(self):
        self.visible = False
        self.fps_history = deque([60.0] * 30, maxlen=30)
        self.latency_ms = 12.5
        self.total_players = 1

    def toggle(self):
        self.visible = not self.visible

    def update(self, current_fps):
        self.fps_history.append(float(current_fps))

    def draw_overlay(self, surf, font_sm, session_mgr, vision_tracker, net_sync):
        if not self.visible:
            return

        panel_rect = pygame.Rect(20, 80, 320, 420)
        NeonFX.draw_glass_card(surf, panel_rect, border_color=UITheme.NEON_GOLD, border_width=2, radius=16, elevation=20, is_3d=True)

        header = font_sm.render("OPERATOR DIAGNOSTIC CONSOLE", True, UITheme.NEON_GOLD)
        surf.blit(header, (panel_rect.x + 16, panel_rect.y + 14))
        pygame.draw.line(surf, (50, 70, 100), (panel_rect.x + 14, panel_rect.y + 36), (panel_rect.right - 14, panel_rect.y + 36), 1)

        avg_fps = sum(self.fps_history) / max(1, len(self.fps_history))
        peer_status = "CONNECTED" if net_sync.is_peer_active() else "OFFLINE (SOLO)"

        lines = [
            f"FPS: {avg_fps:.1f} / 60",
            f"VISION HANDS: {len(vision_tracker.get_hands())}",
            f"LATENCY: {self.latency_ms:.1f} ms",
            f"RIVAL PEER: {peer_status}",
            f"SESSION LEFT: {int(session_mgr.time_left)} s",
            f"EXPIRED: {session_mgr.is_expired}",
            f"UDP PORT: {UDP_PORT}",
            "",
            "OPERATOR SHORTCUTS:",
            "[F12] RESET SESSION TIMER",
            "[F11] TOGGLE RIVAL BROADCAST",
            "[F10] RE-INITIALIZE VISION",
            "[F9]  CLEAR ALL HIGH SCORES",
            "[O]   CLOSE OPERATOR PANEL"
        ]

        for idx, line in enumerate(lines):
            col = UITheme.NEON_CYAN if "OPERATOR" in line else (UITheme.NEON_GREEN if "FPS" in line else UITheme.PURE_WHITE)
            txt = font_sm.render(line, True, col)
            surf.blit(txt, (panel_rect.x + 16, panel_rect.y + 46 + idx * 22))

# ==================================================================================================
# 30. MASTER APPLICATION CONTROLLER & AETHERIA NEXUS ORCHESTRATION
# ==================================================================================================
class AetheriaApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("AETHERIA GRAND PRIX — SULAM 2026 NEO-SYMPHONIC EXHIBITION MASTERPIECE")
        self.clock = pygame.time.Clock()

        # Engine Systems
        self.vision = AsyncVisionTracker()
        self.vfx = VisualFXEngine()
        self.cosmic_vfx = CosmicVisualizer()
        self.network = NetworkSyncEngine(port=UDP_PORT, app_reference=self)
        self.session = ExhibitionSessionManager(duration_minutes=12.0)
        self.operator_panel = BoothKioskOperatorPanel()
        
        # Camera & Stage Directors
        self.camera = CameraDirector()
        self.orchestra = OrchestraConductorDirector()
        self.stage_anim = AnimatedOrchestraStage()
        self.transition = SceneTransitionEngine()
        self.spatial_manager = SpatialGestureManager()

        # Games & Modules
        self.game1_studio = FreestyleStudioManager()
        self.game2_tiles = NeoPianoTilesGame()
        self.game3_blades = NeoSynthBladeGame()
        self.game5_singularity = CelestialSingularityGame()
        self.game6_slingshot = NeoSonicSlingshotGame()

        self.master_scoreboard = MasterScoreboardHub(
            self.game2_tiles.board,
            self.game3_blades.board,
            self.game5_singularity.board
        )

        self.loop_engine = LoopStationEngine()
        self.ai_copilot = AIMusicAssistant()
        self.dna_engine = MusicalDNAGenerator()
        self.live_stage = LivePerformanceMode()

        # 3D Nexus Floating Portal Windows with Depth Cast Shadows
        self.spatial_cards = [
            SpatialWindow("[1] FREESTYLE", "8 Instruments at 1-2m Range", (80, 160, 260, 310), UITheme.NEON_CYAN, "LAB", "GAME_1", 3, "STUDIO"),
            SpatialWindow("[2] PIANO TILES", "Accelerating 3D Rhythm Track", (370, 160, 260, 310), UITheme.NEON_GREEN, "SPEED", "GAME_2", 3, "TILES"),
            SpatialWindow("[3] SYNTH BLADE", "Dual-Saber Rhythm Slasher", (660, 160, 260, 310), UITheme.NEON_GOLD, "BLADE", "GAME_3", 3, "BLADE"),
            SpatialWindow("[5] SINGULARITY", "Celestial Orbital Resonance", (950, 160, 260, 310), UITheme.NEON_PURPLE, "ORBIT", "GAME_5", 3, "ORBIT")
        ]
        self.orchestra_banner_rect = pygame.Rect(WIDTH // 2 - 320, 500, 640, 54)

        # Typography Loaders
        self.font_sm = self._load_font(["orbitron", "oxanium", "rajdhani", "impact"], 16)
        self.font_md = self._load_font(["orbitron", "oxanium", "rajdhani", "impact"], 24)
        self.font_lg = self._load_font(["orbitron", "oxanium", "audiowide", "impact"], 42)
        self.font_notes = pygame.font.SysFont("Segoe UI Symbol", 20)

        self.app_state = "MENU"
        self.active_score = 0
        self.active_combo = 0
        self.gong_wave = 0.0

    def _load_font(self, font_names, size):
        for name in font_names:
            try:
                f = pygame.font.SysFont(name, size)
                if f: return f
            except Exception:
                continue
        return pygame.font.SysFont("Impact", size)

    def _draw_perspective_grid(self, surf):
        """Renders an infinite receding 3D synthwave grid floor with volumetric depth fading."""
        grid_s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        horizon = HEIGHT // 2 + 70
        t = (pygame.time.get_ticks() * 0.001) % 1.0

        for i in range(-14, 15):
            sx = WIDTH // 2 + i * 115
            pygame.draw.line(grid_s, (0, 240, 255, 30), (WIDTH // 2 + i * 14, horizon), (sx, HEIGHT), 1)

        for j in range(8):
            p = (j + t) / 8.0
            cur_y = int(horizon + math.pow(p, 2.2) * (HEIGHT - horizon))
            alpha = int(55 * p)
            pygame.draw.line(grid_s, (0, 240, 255, alpha), (0, cur_y), (WIDTH, cur_y), 1)

        surf.blit(grid_s, (0, 0))

    def _draw_spectrum_equalizer(self, surf):
        global audio_energy
        bars = 36
        bar_w = WIDTH // bars
        t = pygame.time.get_ticks() * 0.005
        for i in range(bars):
            h_amp = math.sin(t + i * 0.35) * 12 + (audio_energy * random.uniform(35, 95))
            h_amp = max(4, int(h_amp))
            bx = i * bar_w
            
            # 3D Equalizer Column Shadow
            pygame.draw.rect(surf, (0, 0, 0, 110), (bx + 4, HEIGHT - h_amp - 12, bar_w - 4, h_amp), border_radius=3)
            
            # 3D Equalizer Bar with Specular Top
            pygame.draw.rect(surf, UITheme.NEON_CYAN, (bx + 2, HEIGHT - h_amp - 15, bar_w - 4, h_amp), border_radius=3)
            pygame.draw.line(surf, UITheme.PURE_WHITE, (bx + 2, HEIGHT - h_amp - 15), (bx + bar_w - 2, HEIGHT - h_amp - 15), 1)

    def run(self):
        global audio_energy
        running = True
        broadcast_timer = 0.0
        world_surf = pygame.Surface((WIDTH, HEIGHT))

        while running:
            dt = min(self.clock.tick(TARGET_FPS) / 1000.0, 0.05)
            self.operator_panel.update(self.clock.get_fps())
            audio_energy = max(0.0, audio_energy - 1.5 * dt)
            self.vfx.update(dt)
            self.session.update(dt)
            self.camera.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.app_state == "LOOP_STATION":
                        self.loop_engine.handle_click(mx, my, self.ai_copilot, self.vfx)
                    elif self.app_state == "MENU":
                        for card in reversed(self.spatial_cards):
                            if card.rect.collidepoint(mx, my):
                                self.transition.change_scene(card.target_state, lambda: (
                                    self.game2_tiles.start_game() if card.target_state == "GAME_2" else
                                    self.game3_blades.start_game() if card.target_state == "GAME_3" else
                                    self.game5_singularity.start_game() if card.target_state == "GAME_5" else
                                    self.camera.reset_view()
                                ))
                                break
                        if self.orchestra_banner_rect.collidepoint(mx, my):
                            self.transition.change_scene("ORCHESTRA", self.camera.reset_view)

                elif event.type == pygame.MOUSEWHEEL:
                    if self.app_state == "SCOREBOARD":
                        self.master_scoreboard.handle_wheel(event.y)
                    elif self.app_state == "GAME_2" and self.game2_tiles.show_leaderboard:
                        self.game2_tiles.board.handle_wheel(event.y)
                    elif self.app_state == "GAME_3" and self.game3_blades.show_leaderboard:
                        self.game3_blades.board.handle_wheel(event.y)
                    elif self.app_state == "GAME_5" and self.game5_singularity.show_leaderboard:
                        self.game5_singularity.board.handle_wheel(event.y)

                elif event.type == pygame.KEYDOWN:
                    active_board = None
                    if self.app_state == "GAME_2" and self.game2_tiles.show_leaderboard:
                        active_board = self.game2_tiles.board
                    elif self.app_state == "GAME_3" and self.game3_blades.show_leaderboard:
                        active_board = self.game3_blades.board
                    elif self.app_state == "GAME_5" and self.game5_singularity.show_leaderboard:
                        active_board = self.game5_singularity.board
                    elif self.app_state == "GAME_6" and self.game6_slingshot.show_leaderboard:
                        active_board = self.game6_slingshot.board

                    if active_board and active_board.entering_name:
                        name_submitted = active_board.handle_key_input(event, network_engine=self.network)
                        continue

                    if event.key == pygame.K_ESCAPE:
                        if self.app_state != "MENU":
                            self.transition.change_scene("MENU", self.camera.reset_view)
                        else:
                            running = False
                    elif event.key == pygame.K_o:
                        self.operator_panel.toggle()
                    elif event.key == pygame.K_f:
                        pygame.display.toggle_fullscreen()
                    elif event.key == pygame.K_F12:
                        self.session.reset_session()
                    elif event.key == pygame.K_F11:
                        self.network.request_full_sync()
                    elif event.key == pygame.K_s:
                        self.transition.change_scene("SCOREBOARD", self.camera.reset_view)
                    elif event.key == pygame.K_1:
                        if self.app_state == "LOOP_STATION": self.loop_engine.active_track = 0
                        else: self.transition.change_scene("GAME_1", self.camera.reset_view)
                    elif event.key == pygame.K_2:
                        if self.app_state == "LOOP_STATION": self.loop_engine.active_track = 1
                        else: self.transition.change_scene("GAME_2", lambda: (self.game2_tiles.start_game(), self.camera.reset_view()))
                    elif event.key == pygame.K_3:
                        if self.app_state == "LOOP_STATION": self.loop_engine.active_track = 2
                        else: self.transition.change_scene("GAME_3", lambda: (self.game3_blades.start_game(), self.camera.reset_view()))
                    elif event.key == pygame.K_4:
                        if self.app_state == "LOOP_STATION": self.loop_engine.active_track = 3
                        else: self.transition.change_scene("ORCHESTRA", self.camera.reset_view)
                    elif event.key == pygame.K_5:
                        self.transition.change_scene("GAME_5", lambda: (self.game5_singularity.start_game(), self.camera.reset_view()))
                    elif event.key == pygame.K_6:
                        self.transition.change_scene("GAME_6", lambda: (self.game6_slingshot.start_game(), self.camera.reset_view()))
                    elif event.key == pygame.K_l:
                        self.transition.change_scene("LIVE_STAGE", lambda: (self.live_stage.start_performance(), self.camera.reset_view()))
                    elif event.key == pygame.K_p:
                        self.transition.change_scene("LOOP_STATION", self.camera.reset_view)
                    elif event.key == pygame.K_r and self.app_state == "LOOP_STATION":
                        self.loop_engine.is_recording = not self.loop_engine.is_recording
                    elif event.key == pygame.K_c and self.app_state == "LOOP_STATION":
                        self.loop_engine.clear_all()
                    elif event.key == pygame.K_UP and self.app_state == "LOOP_STATION":
                        self.loop_engine.set_bpm(self.loop_engine.bpm + 4.0)
                    elif event.key == pygame.K_DOWN and self.app_state == "LOOP_STATION":
                        self.loop_engine.set_bpm(self.loop_engine.bpm - 4.0)
                    elif event.key == pygame.K_TAB and self.app_state == "GAME_1":
                        self.game1_studio.current_inst_index = (self.game1_studio.current_inst_index + 1) % len(self.game1_studio.instruments_meta)
                    elif event.key == pygame.K_SPACE:
                        if self.app_state == "GAME_2" and self.game2_tiles.game_over:
                            self.game2_tiles.start_game()
                        elif self.app_state == "GAME_3" and self.game3_blades.game_over:
                            self.game3_blades.start_game()
                        elif self.app_state == "GAME_5" and self.game5_singularity.game_over:
                            self.game5_singularity.start_game()
                        elif self.app_state == "GAME_6" and self.game6_slingshot.game_over:
                            self.game6_slingshot.start_game()
                        elif self.app_state == "LIVE_STAGE" and self.live_stage.is_completed:
                            self.live_stage.start_performance()
                        elif self.app_state == "LOOP_STATION":
                            self.loop_engine.is_playing = not self.loop_engine.is_playing
                        else:
                            SND_GONG.play(); self.gong_wave = 15.0
                            self.vfx.burst(WIDTH // 2, HEIGHT // 2, UITheme.NEON_GOLD, count=30, with_notes=True)

            hands = self.vision.get_hands()
            self.ai_copilot.update(dt)
            self.cosmic_vfx.update(dt)
            self.transition.update(dt, self)

            if self.app_state == "MENU":
                clicked_state = self.spatial_manager.process_gestures(self.spatial_cards, hands, dt)
                if clicked_state:
                    self.transition.change_scene(clicked_state, lambda: (
                        self.game2_tiles.start_game() if clicked_state == "GAME_2" else
                        self.game3_blades.start_game() if clicked_state == "GAME_3" else
                        self.game5_singularity.start_game() if clicked_state == "GAME_5" else
                        self.camera.reset_view()
                    ))
                for card in self.spatial_cards:
                    card.update_physics(dt)

            elif self.app_state == "GAME_1":
                self.game1_studio.update(hands, self.vfx, self.cosmic_vfx, dt)
                self.active_score, self.active_combo = 1000, 1

            elif self.app_state == "GAME_2":
                self.game2_tiles.update(hands, self.vfx, dt)
                self.active_score, self.active_combo = self.game2_tiles.score, self.game2_tiles.combo

            elif self.app_state == "GAME_3":
                self.game3_blades.update(hands, self.vfx, dt)
                self.active_score, self.active_combo = self.game3_blades.score, self.game3_blades.combo

            elif self.app_state == "ORCHESTRA":
                self.orchestra.process_conductor(hands, self.vfx, self.camera, self.stage_anim, dt)
                self.stage_anim.update(self.orchestra, dt)
                self.active_score, self.active_combo = 3000, 1

            elif self.app_state == "GAME_5":
                self.game5_singularity.update(hands, self.vfx, dt)
                self.active_score, self.active_combo = self.game5_singularity.score, self.game5_singularity.combo

            elif self.app_state == "GAME_6":
                self.game6_slingshot.update(hands, self.vfx, self.cosmic_vfx, dt)
                self.active_score, self.active_combo = self.game6_slingshot.score, self.game6_slingshot.combo

            elif self.app_state == "LOOP_STATION":
                self.loop_engine.update(dt, self.vfx, self.ai_copilot)
                for h in hands:
                    tx, ty = h["beam_target"] if h["is_distant"] else h["lead_tip"]
                    self.loop_engine.process_touch_input(tx, ty, h["is_pinching"], h["is_fist"], self.ai_copilot, self.vfx)

            elif self.app_state == "LIVE_STAGE":
                self.live_stage.update(hands, self.vfx, self.dna_engine, dt)

            broadcast_timer += dt
            if broadcast_timer >= 0.10:
                broadcast_timer = 0.0
                self.network.broadcast_state(self.app_state, self.active_score, self.active_combo)

            world_surf.fill(UITheme.VOID_BLACK)

            if self.app_state == "MENU":
                self._draw_perspective_grid(world_surf)
                
                t_wave = pygame.time.get_ticks() * 0.003
                wave_surf = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
                for wx in range(0, WIDTH, 16):
                    wy = 60 + int(math.sin(t_wave + wx * 0.015) * 22 * (audio_energy + 0.4))
                    pygame.draw.circle(wave_surf, (*UITheme.NEON_CYAN[:3], 45), (wx, wy), 3)
                world_surf.blit(wave_surf, (0, HEIGHT // 2 - 120))

                head_rect = pygame.Rect(WIDTH // 2 - 320, 20, 640, 100)
                NeonFX.draw_glass_card(world_surf, head_rect, border_color=UITheme.NEON_CYAN, border_width=2, radius=22, elevation=18, is_3d=True)
                
                pill_tag = pygame.Rect(WIDTH // 2 - 140, 20, 280, 26)
                NeonFX.draw_hud_pill(world_surf, pill_tag, border_color=UITheme.NEON_PINK, radius=8, elevation=4)
                t_sub = self.font_sm.render("NEO-SYMPHONIC EXHIBITION", True, UITheme.NEON_PINK)
                world_surf.blit(t_sub, (pill_tag.centerx - t_sub.get_width() // 2, pill_tag.centery - t_sub.get_height() // 2))

                title = self.font_lg.render("AETHERIA GRAND PRIX", True, UITheme.PURE_WHITE)
                world_surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 54))

                for card in self.spatial_cards:
                    card.draw(world_surf, self.font_sm, self.font_md)

                NeonFX.draw_glass_card(world_surf, self.orchestra_banner_rect, border_color=UITheme.NEON_GOLD, border_width=2, radius=16, elevation=14, is_3d=True)
                draw_ribbon(world_surf, self.font_md, "[4] ANIMATED CONCERT HALL & CHOIR STAGE", WIDTH // 2, 527, 620, 44, UITheme.NEON_GOLD, UITheme.VOID_BLACK)

                nav_lbl = self.font_sm.render("PINCH & DRAG PORTALS | [1: FREESTYLE] [2: TILES] [3: SYNTH BLADE] [4: ORCHESTRA] [5: SINGULARITY]", True, UITheme.TEXT_MUTED)
                world_surf.blit(nav_lbl, (WIDTH // 2 - nav_lbl.get_width() // 2, 610))

            elif self.app_state == "GAME_1":
                self.game1_studio.draw(world_surf, self.font_sm, self.font_md, self.font_lg)

            elif self.app_state == "GAME_2":
                self.game2_tiles.draw(world_surf, self.font_sm, self.font_md, self.font_lg, hands=hands)

            elif self.app_state == "GAME_3":
                self.game3_blades.draw(world_surf, self.font_sm, self.font_md, self.font_lg, hands=hands)

            elif self.app_state == "ORCHESTRA":
                self.stage_anim.draw(world_surf, self.orchestra, hands=hands)

            elif self.app_state == "GAME_5":
                self.game5_singularity.draw(world_surf, self.font_sm, self.font_md, self.font_lg, hands=hands)

            elif self.app_state == "GAME_6":
                self.game6_slingshot.draw(world_surf, self.font_sm, self.font_md, self.font_lg, hands=hands)

            elif self.app_state == "LOOP_STATION":
                self.loop_engine.draw(world_surf, self.font_sm, self.font_md)
                self.ai_copilot.draw_glass_widget(world_surf, self.font_sm, self.font_md, x=30, y=140)

            elif self.app_state == "LIVE_STAGE":
                if self.live_stage.is_completed:
                    self.dna_engine.draw_dna_certificate(world_surf, self.font_sm, self.font_md, self.font_lg)
                else:
                    self.live_stage.draw(world_surf, self.font_sm, self.font_md, self.font_lg)

            elif self.app_state == "SCOREBOARD":
                self.master_scoreboard.draw(world_surf, self.font_sm, self.font_md, self.font_lg, hands=hands)

            for h in hands:
                draw_realistic_hand(world_surf, h)
                
                if h["is_distant"]:
                    tip = h["lead_tip"]
                    target = h["beam_target"]
                    col = UITheme.NEON_CYAN if h["is_left"] else UITheme.NEON_GOLD
                    pygame.draw.line(world_surf, (0, 0, 0, 120), (tip[0] + 4, tip[1] + 6), (target[0] + 4, target[1] + 6), 5)
                    pygame.draw.line(world_surf, col, tip, target, 3)
                    NeonFX.draw_glow_circle(world_surf, col, target, 10, glow_size=16, max_alpha=220)

                new_state = draw_apple_wrist_hud(world_surf, h, self.app_state, self.font_sm, other_hands=hands)
                if new_state:
                    self.transition.change_scene(new_state, self.camera.reset_view)

            self.cosmic_vfx.draw(world_surf)
            self.vfx.draw(world_surf, self.font_notes)

            if self.app_state != "ORCHESTRA":
                self._draw_spectrum_equalizer(world_surf)

            if self.gong_wave > 0.0:
                self.gong_wave += 620.0 * dt
                pygame.draw.circle(world_surf, UITheme.PURE_WHITE, (WIDTH // 2, HEIGHT // 2), int(self.gong_wave), 6)
                if self.gong_wave > WIDTH * 1.3:
                    self.gong_wave = 0.0

            frame_surf = pygame.Surface((WIDTH, HEIGHT))
            if self.app_state == "ORCHESTRA":
                self.camera.render_scene(frame_surf, world_surf, self.font_sm, self.font_md)
                self.orchestra.draw_hud(frame_surf, self.font_sm, self.font_md)
            else:
                frame_surf.blit(world_surf, (0, 0))

            self.network.draw_hud(frame_surf, self.font_sm, self.active_score, self.active_combo)
            

            mode_tag = pygame.Rect(WIDTH // 2 - 90, 16, 180, 32)
            NeonFX.draw_hud_pill(frame_surf, mode_tag, border_color=UITheme.GLASS_BORDER, radius=8, elevation=6)
            t_curr = self.font_sm.render(self.app_state, True, UITheme.PURE_WHITE)
            frame_surf.blit(t_curr, (mode_tag.centerx - t_curr.get_width() // 2, mode_tag.centery - t_curr.get_height() // 2))

            foot_txt = self.font_sm.render(
                "[ESC] MENU | [1] STUDIO | [2] TILES | [3] BLADE | [4] ORCHESTRA | [5] HARP | [6] SLINGSHOT | [P] LOOP", 
                True, (160, 180, 215)
            )
            frame_surf.blit(foot_txt, (WIDTH // 2 - foot_txt.get_width() // 2, HEIGHT - 20))

            self.operator_panel.draw_overlay(frame_surf, self.font_sm, self.session, self.vision, self.network)

            shake_x, shake_y = self.vfx.get_shake_offset()
            self.screen.blit(frame_surf, (shake_x, shake_y))
            self.transition.draw(self.screen)
            pygame.display.flip()

        self.vision.release()
        pygame.quit()
        sys.exit()

# ==================================================================================================
# 31. APPLICATION ENTRY POINT
# ==================================================================================================
if __name__ == "__main__":
    app = AetheriaApp()
    app.run()