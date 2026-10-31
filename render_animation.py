import os
import math
import random
import numpy as np
import imageio

# Ensure headless operation for GitHub Actions CI
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

# --- CINEMATIC CONSTANTS ---
WIDTH = 1280
HEIGHT = 720
FPS = 30
TOTAL_SECONDS = 30
TOTAL_FRAMES = TOTAL_SECONDS * FPS
OUTPUT_FILENAME = "moon_mystery.mp4"

pygame.init()
render_surface = pygame.Surface((WIDTH, HEIGHT))

# --- COLOR BIBLE (Teal, Amber, & Deep Space Chiaroscuro) ---
COLOR_DEEP_VOID   = (3, 4, 8)
COLOR_SPACE_INDIGO= (10, 12, 22)
COLOR_HAZE_BLUE   = (28, 38, 58)
COLOR_CRATER_FAR  = (18, 20, 30)
COLOR_CRATER_MID  = (32, 36, 48)
COLOR_CRATER_NEAR = (52, 58, 72)
COLOR_REGOLITH    = (82, 90, 106)
COLOR_REGOLITH_HI = (120, 130, 148)
COLOR_SHIP_DARK   = (24, 28, 36)
COLOR_SHIP_MID    = (48, 54, 68)
COLOR_SHIP_HILITE = (160, 172, 190)
COLOR_GOLD_VISOR  = (240, 185, 30)
COLOR_PLASMA_CORE = (255, 255, 240)
COLOR_PLASMA_AMBER= (255, 130, 20)
COLOR_CYAN_LIGHT  = (30, 225, 240)
COLOR_AMBER_LIGHT = (255, 170, 30)

# --- DISNEY EASING SUITE ---
def smoothstep(edge0, edge1, x):
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

def ease_out_elastic(t):
    p = 0.3
    return pow(2, -10 * t) * math.sin((t - p / 4) * (2 * math.pi) / p) + 1

# --- PRE-RENDERED HIGH-RES ASSETS ---
print("⚙️  Baking photorealistic atmospheric assets...")

# 1. Atmospheric Earth (Pre-baked with multilayer atmosphere halo)
EARTH_SIZE = 180
earth_surface = pygame.Surface((EARTH_SIZE, EARTH_SIZE), pygame.SRCALPHA)
ec = EARTH_SIZE // 2
er = 60
# Outer Rayleigh scattering glow
for r in range(er + 24, er, -1):
    alpha = int(45 * (1.0 - (r - er) / 24.0)**1.5)
    pygame.draw.circle(earth_surface, (60, 140, 255, alpha), (ec, ec), r)
# Ocean base
pygame.draw.circle(earth_surface, (20, 55, 130), (ec, ec), er)
# Continents
pygame.draw.ellipse(earth_surface, (38, 105, 50), (ec - 28, ec - 35, 45, 30))
pygame.draw.ellipse(earth_surface, (45, 115, 60), (ec - 10, ec + 5, 48, 35))
pygame.draw.ellipse(earth_surface, (55, 130, 70), (ec + 15, ec - 30, 30, 22))
# Swirling Cloud Formations
cloud_surf = pygame.Surface((EARTH_SIZE, EARTH_SIZE), pygame.SRCALPHA)
for angle, rad, w, h in [(0.4, 35, 55, 18), (1.8, 42, 65, 22), (3.6, 30, 70, 25)]:
    cx = ec + int(rad * math.cos(angle))
    cy = ec + int(rad * math.sin(angle))
    pygame.draw.ellipse(cloud_surf, (230, 242, 255, 160), (cx - w//2, cy - h//2, w, h))
earth_surface.blit(cloud_surf, (0, 0))
# Shadow Terminator
terminator = pygame.Surface((EARTH_SIZE, EARTH_SIZE), pygame.SRCALPHA)
pygame.draw.circle(terminator, (4, 6, 12, 205), (ec + 22, ec), er + 4)
earth_surface.blit(terminator, (0, 0))

# 2. Cinematic Vignette Mask
vignette_mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for radius in range(WIDTH // 2 + 100, WIDTH // 3, -8):
    a = int(140 * (1.0 - (radius - WIDTH // 3) / (WIDTH // 2 + 100 - WIDTH // 3)))
    pygame.draw.ellipse(vignette_mask, (0, 0, 0, max(0, min(140, a))), 
                        (WIDTH//2 - radius, HEIGHT//2 - int(radius*0.6), radius*2, int(radius*1.2)))

# 3. Deterministic Deep-Sky Stars
np.random.seed(42)
STARFIELD = [
    (np.random.randint(0, WIDTH), np.random.randint(0, HEIGHT), np.random.choice([1, 1, 1, 2]), np.random.uniform(0.3, 0.9))
    for _ in range(220)
]

# --- VOLUMETRIC LIGHT & PARTICLE SYSTEMS ---
dust_particles = []
def emit_dust(x, y, count=15, speed=2.5, spread=0.6):
    for _ in range(count):
        angle = -math.pi / 2 + np.random.uniform(-spread, spread)
        vel = np.random.uniform(0.4 * speed, speed)
        dust_particles.append({
            "x": x + np.random.uniform(-12, 12),
            "y": y + np.random.uniform(-4, 4),
            "vx": math.sin(angle) * vel * 1.8,
            "vy": math.cos(angle) * vel * 0.4 - np.random.uniform(0.5, 1.8),
            "life": 1.0,
            "decay": np.random.uniform(0.015, 0.035),
            "size": np.random.randint(4, 9)
        })

def render_dust(surface, cam_x, cam_y):
    dust_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for p in dust_particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.03  # Low lunar gravity
        p["vx"] *= 0.985
        p["life"] -= p["decay"]
        if p["life"] <= 0:
            dust_particles.remove(p)
            continue
        alpha = int(110 * p["life"])
        sz = int(p["size"] * (0.6 + 0.6 * (1.0 - p["life"])))
        px, py = int(p["x"] - cam_x), int(p["y"] - cam_y)
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            pygame.draw.circle(dust_layer, (140, 150, 165, alpha), (px, py), sz)
    surface.blit(dust_layer, (0, 0))

def draw_light_cone(surface, origin_x, origin_y, target_angle, length, spread_angle, color_rgba):
    cone_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    p1 = (origin_x, origin_y)
    p2 = (origin_x + length * math.cos(target_angle - spread_angle), origin_y + length * math.sin(target_angle - spread_angle))
    p3 = (origin_x + length * math.cos(target_angle + spread_angle), origin_y + length * math.sin(target_angle + spread_angle))
    pygame.draw.polygon(cone_surf, color_rgba, [p1, p2, p3])
    surface.blit(cone_surf, (0, 0), special_flags=pygame.BLEND_ADD)

# --- DETAILED CHARACTER & VEHICLE DRAWING ---
def draw_detailed_scout(surface, x, y, walk_cycle=0.0, direction=1):
    """Draws an anatomically proportioned silhouette astronaut with lit highlights."""
    scout_surf = pygame.Surface((80, 120), pygame.SRCALPHA)
    cx, cy = 40, 60
    
    # Stride leg angles
    hip_swing = math.sin(walk_cycle) * 14.0
    
    # Back Leg
    pygame.draw.line(scout_surf, COLOR_CRATER_MID, (cx - 2, cy + 10), (cx - 2 - hip_swing * 0.8, cy + 28), 6)
    pygame.draw.line(scout_surf, COLOR_CRATER_FAR, (cx - 2 - hip_swing * 0.8, cy + 28), (cx - 2 - hip_swing, cy + 46), 5)
    
    # Front Leg
    pygame.draw.line(scout_surf, COLOR_SHIP_MID, (cx + 2, cy + 10), (cx + 2 + hip_swing * 0.8, cy + 28), 7)
    pygame.draw.line(scout_surf, COLOR_SHIP_DARK, (cx + 2 + hip_swing * 0.8, cy + 28), (cx + 2 + hip_swing, cy + 46), 6)
    
    # Torso & Heavy Life-Support Backpack
    pygame.draw.rect(scout_surf, COLOR_CRATER_FAR, (cx - 16 * direction, cy - 18, 12, 28), border_radius=3)
    pygame.draw.rect(scout_surf, COLOR_SHIP_DARK, (cx - 8, cy - 20, 18, 32), border_radius=5)
    # Chest Harness / Rim-Light
    pygame.draw.line(scout_surf, COLOR_SHIP_HILITE, (cx - 2, cy - 16), (cx + 6 * direction, cy + 4), 2)
    
    # Helmet & Golden Visor
    pygame.draw.circle(scout_surf, COLOR_SHIP_DARK, (cx + 2 * direction, cy - 30), 13)
    pygame.draw.ellipse(scout_surf, COLOR_GOLD_VISOR, (cx + (2 if direction == 1 else -12), cy - 34, 11, 10))
    
    # Shoulder Beacon Pulsing
    pygame.draw.circle(scout_surf, COLOR_CYAN_LIGHT, (cx - 8 * direction, cy - 16), 2)
    
    surface.blit(scout_surf, (x - 40, y - 60))

def draw_industrial_lander(surface, x, y, suspension_comp=0.0):
    """Draws a cinematic, angular scout spacecraft with heat shield tiling and mechanical gear."""
    # Main Cabin Silhouette
    hull_pts = [
        (x, y - 110),
        (x + 46, y - 55),
        (x + 55, y - 10),
        (x + 35, y + 15),
        (x - 35, y + 15),
        (x - 55, y - 10),
        (x - 46, y - 55)
    ]
    pygame.draw.polygon(surface, COLOR_SHIP_DARK, hull_pts)
    pygame.draw.polygon(surface, COLOR_SHIP_MID, [(x, y - 110), (x + 46, y - 55), (x, y - 10), (x - 46, y - 55)])
    pygame.draw.polygon(surface, COLOR_SHIP_HILITE, [(x - 10, y - 105), (x + 10, y - 105), (x + 35, y - 60), (x - 35, y - 60)], 2)

    # Cockpit Angled Slit
    pygame.draw.polygon(surface, COLOR_GOLD_VISOR, [(x + 8, y - 75), (x + 32, y - 48), (x + 10, y - 48)])

    # Heavy Hydraulic Landing Struts with Real Compression
    strut_y = y + 15
    pad_y = y + 55 - suspension_comp
    # Left Arm
    pygame.draw.line(surface, COLOR_
