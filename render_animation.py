import os
import math
import numpy as np
import imageio

# Force headless SDL video driver for GitHub Actions / CI
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

# --- CONFIGURATION ---
INTERNAL_WIDTH = 320
INTERNAL_HEIGHT = 180
SCALE = 4
OUT_WIDTH = INTERNAL_WIDTH * SCALE    # 1280
OUT_HEIGHT = INTERNAL_HEIGHT * SCALE  # 720
FPS = 30
TOTAL_SECONDS = 17
TOTAL_FRAMES = TOTAL_SECONDS * FPS
OUTPUT_FILENAME = "moon_mystery.mp4"

# --- PALETTE (Sci-Fi Retro 16-Color) ---
PALETTE = {
    "VOID": (7, 6, 15),
    "SPACE_BLUE": (17, 18, 36),
    "STAR_WHITE": (220, 225, 235),
    "EARTH_BLUE": (29, 75, 143),
    "EARTH_GREEN": (46, 125, 50),
    "EARTH_CLOUD": (215, 235, 248),
    "REGOLITH_LIGHT": (140, 151, 154),
    "REGOLITH_MID": (86, 90, 99),
    "REGOLITH_DARK": (43, 43, 54),
    "REGOLITH_SHADOW": (18, 18, 24),
    "HULL_LIGHT": (160, 168, 179),
    "HULL_DARK": (75, 85, 99),
    "FIRE_ORANGE": (245, 120, 20),
    "FIRE_YELLOW": (250, 204, 21),
    "VISOR_GOLD": (234, 179, 8),
    "CYAN_NEON": (6, 182, 212),
    "RED_ALERT": (239, 68, 68),
    "BLACK": (0, 0, 0),
}

# --- INITIALIZE SURFACES ---
pygame.init()
canvas = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
upscaled = pygame.Surface((OUT_WIDTH, OUT_HEIGHT))

# Deterministic starfield
np.random.seed(42)
stars = [
    (np.random.randint(0, INTERNAL_WIDTH), np.random.randint(0, 100), np.random.choice([1, 2]))
    for _ in range(70)
]

# --- RENDER HELPERS ---
def draw_stars(surface):
    for x, y, size in stars:
        surface.fill(PALETTE["STAR_WHITE"], (x, y, 1, 1))

def draw_earth(surface, x, y, radius=16):
    # Base blue planet
    pygame.draw.circle(surface, PALETTE["EARTH_BLUE"], (x, y), radius)
    # Continents & clouds (procedural pixels)
    pygame.draw.ellipse(surface, PALETTE["EARTH_GREEN"], (x - 6, y - 8, 10, 6))
    pygame.draw.ellipse(surface, PALETTE["EARTH_GREEN"], (x - 2, y + 1, 12, 7))
    pygame.draw.arc(surface, PALETTE["EARTH_CLOUD"], (x - 14, y - 14, 28, 28), 0.2, 2.0, 2)
    # Shadow crescent
    shadow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (0, 0, 0, 160), (radius + 4, radius), radius)
    surface.blit(shadow, (x - radius, y - radius))

def draw_lunar_terrain(surface, offset_x=0):
    # Horizon 1 (Distant)
    for i in range(INTERNAL_WIDTH):
        h = int(105 + 8 * math.sin((i + offset_x * 0.2) * 0.03))
        surface.fill(PALETTE["REGOLITH_DARK"], (i, h, 1, INTERNAL_HEIGHT - h))
    # Horizon 2 (Mid-ground craters)
    for i in range(INTERNAL_WIDTH):
        h = int(125 + 10 * math.sin((i + offset_x * 0.5) * 0.04) + 4 * math.cos((i) * 0.09))
        surface.fill(PALETTE["REGOLITH_MID"], (i, h, 1, INTERNAL_HEIGHT - h))
    # Foreground Flat Basin
    surface.fill(PALETTE["REGOLITH_LIGHT"], (0, 145, INTERNAL_WIDTH, INTERNAL_HEIGHT - 145))
    # Dithered foreground texture
    for i in range(0, INTERNAL_WIDTH, 4):
        surface.fill(PALETTE["REGOLITH_DARK"], (i + (i % 3), 150 + (i % 7), 2, 1))

def draw_ship(surface, x, y, landing_gear_deployed=True):
    # Hull
    pygame.draw.polygon(surface, PALETTE["HULL_LIGHT"], [
        (x, y - 24), (x + 12, y), (x - 12, y)
    ])
    pygame.draw.polygon(surface, PALETTE["HULL_DARK"], [
        (x, y - 24), (x, y), (x - 12, y)
    ])
    # Thruster engine block
    pygame.draw.rect(surface, PALETTE["HULL_DARK"], (x - 8, y, 16, 4))
    if landing_gear_deployed:
        # Left & Right landing legs
        pygame.draw.line(surface, PALETTE["HULL_DARK"], (x - 8, y + 4), (x - 16, y + 16), 1)
        pygame.draw.line(surface, PALETTE["HULL_DARK"], (x + 8, y + 4), (x + 16, y + 16), 1)
        # Footpads
        surface.fill(PALETTE["HULL_LIGHT"], (x - 19, y + 16, 6, 2))
        surface.fill(PALETTE["HULL_LIGHT"], (x + 13, y + 16, 6, 2))

def draw_astronaut(surface, x, y, direction=1):
    # Torso/Backpack
    surface.fill(PALETTE["HULL_DARK"], (x - 2 * direction, y - 10, 4, 7))
    # Legs
    surface.fill(PALETTE["REGOLITH_DARK"], (x - 2, y - 3, 2, 4))
    surface.fill(PALETTE["REGOLITH_DARK"], (x + 1, y - 3, 2, 4))
    # Head & Visor
    surface.fill(PALETTE["HULL_LIGHT"], (x - 3, y - 16, 6, 6))
    visor_x = x + (1 if direction == 1 else -3)
    surface.fill(PALETTE["VISOR_GOLD"], (visor_x, y - 14, 3, 3))

# --- VIDEO WRITER SETUP ---
print(f"🎬 Initializing renderer: {OUT_WIDTH}x{OUT_HEIGHT} @ {FPS}fps")
writer = imageio.get_writer(
    OUTPUT_FILENAME,
    fps=FPS,
    codec="libx264",
    pixelformat="yuv420p",
    macro_block_size=1
)

# --- MAIN ANIMATION PIPELINE ---
for frame in range(TOTAL_FRAMES):
    canvas.fill(PALETTE["VOID"])
    t = frame / FPS

    # ========================================================
    # SHOT 1: THE DESCENT & LANDING (0.0s - 4.0s)
    # ========================================================
    if t < 4.0:
        local_t = t / 4.0
        draw_stars(canvas)
        draw_earth(canvas, 270, 35, 14)
        draw_lunar_terrain(canvas)

        ship_y = int(-30 + local_t * (130 - (-30)))
        ship_x = 100

        # Thruster pulse (stopping right as it touches down)
        if local_t < 0.92:
            flame_len = int(8 + 6 * math.sin(frame * 1.5))
            pygame.draw.polygon(canvas, PALETTE["FIRE_YELLOW"], [
                (ship_x - 5, ship_y + 4), (ship_x + 5, ship_y + 4),
                (ship_x, ship_y + 4 + flame_len)
            ])
            # Dust puff near ground
            if local_t > 0.6:
                for d in range(8):
                    dx = int(ship_x + (d - 4) * 8 * (local_t - 0.6) * 4)
                    dy = int(150 - (d % 3) * 2)
                    canvas.fill(PALETTE["REGOLITH_LIGHT"], (dx, dy, 2, 2))

        draw_ship(canvas, ship_x, ship_y, landing_gear_deployed=True)

    # ========================================================
    # SHOT 2: THE HATCH & FOOTSTEPS (4.0s - 7.5s)
    # ========================================================
    elif t < 7.5:
        local_t = (t - 4.0) / 3.5
        draw_stars(canvas)
        draw_earth(canvas, 270, 35, 14)
        draw_lunar_terrain(canvas)
        draw_ship(canvas, 100, 130)

        # Ramp extends
        ramp_progress = min(1.0, local_t * 3.0)
        ramp_end_x = 100 + int(24 * ramp_progress)
        ramp_end_y = 130 + int(18 * ramp_progress)
        pygame.draw.line(canvas, PALETTE["HULL_DARK"], (106, 130), (ramp_end_x, ramp_end_y), 2)

        # Scout descends and steps out
        if local_t > 0.35:
            walk_progress = (local_t - 0.35) / 0.65
            scout_x = int(112 + walk_progress * 55)
            scout_y = int(136 + min(walk_progress * 2.0, 1.0) * 12)
            # Boot imprints
            if walk_progress > 0.4:
                canvas.fill(PALETTE["REGOLITH_SHADOW"], (140, 149, 3, 1))
            if walk_progress > 0.7:
                canvas.fill(PALETTE["REGOLITH_SHADOW"], (155, 149, 3, 1))
            draw_astronaut(canvas, scout_x, scout_y, direction=1)

    # ========================================================
    # SHOT 3: VISOR PROFILE CUT-IN (7.5s - 10.5s)
    # ========================================================
    elif t < 10.5:
        local_t = (t - 7.5) / 3.0
        # Dark cinematic cockpit/close-up background
        canvas.fill(PALETTE["SPACE_BLUE"])

        # Giant Side-Profile Helmet
        pygame.draw.circle(canvas, PALETTE["HULL_LIGHT"], (90, 90), 65)
        pygame.draw.rect(canvas, PALETTE["HULL_DARK"], (30, 90, 60, 60))

        # Visor
        pygame.draw.ellipse(canvas, PALETTE["VISOR_GOLD"], (95, 55, 50, 70))
        # Visor Reflection of Crescent Earth
        draw_earth(canvas, 120, 85, radius=12)

        # HUD Blink: "NO SIGNAL" / "SILENT EARTH"
        if int(frame * 0.15) % 2 == 0:
            canvas.fill(PALETTE["RED_ALERT"], (105, 110, 4, 2))
            canvas.fill(PALETTE["RED_ALERT"], (112, 110, 4, 2))
            canvas.fill(PALETTE["RED_ALERT"], (119, 110, 4, 2))

    # ========================================================
    # SHOT 4: BASE EXPANSION (10.5s - 14.0s)
    # ========================================================
    elif t < 14.0:
        local_t = (t - 10.5) / 3.5
        draw_stars(canvas)
        draw_earth(canvas, 270, 35, 14)
        draw_lunar_terrain(canvas)
        draw_ship(canvas, 60, 130)

        # Astronaut standing beside base site
        draw_astronaut(canvas, 175, 148, direction=1)

        # Base Deployment Mechanics
        base_x = 210
        base_y = 148

        # Dome expanding upward & outward
        dome_w = int(min(36, local_t * 40))
        dome_h = int(min(22, local_t * 26))
        if dome_w > 4:
            pygame.draw.ellipse(
                canvas,
                PALETTE["HULL_LIGHT"],
                (base_x - dome_w // 2, base_y - dome_h, dome_w, dome_h * 2)
            )
            # Clip bottom half of dome under soil
            canvas.fill(PALETTE["REGOLITH_LIGHT"], (0, base_y, INTERNAL_WIDTH, 32))

        # Solar fins unfurling
        fin_len = int(min(16, local_t * 20))
        pygame.draw.line(canvas, PALETTE["CYAN_NEON"], (base_x - 18, base_y - 4), (base_x - 18 - fin_len, base_y - 10), 2)
        pygame.draw.line(canvas, PALETTE["CYAN_NEON"], (base_x + 18, base_y - 4), (base_x + 18 + fin_len, base_y - 10), 2)

        # Perimeter warning stakes snap on (cyan glow)
        if local_t > 0.6:
            canvas.fill(PALETTE["CYAN_NEON"], (base_x - 30, base_y - 6, 2, 6))
            canvas.fill(PALETTE["CYAN_NEON"], (base_x + 30, base_y - 6, 2, 6))

    # ========================================================
    # SHOT 5: THE MYSTERY HOOK - ANTENNA TURNS (14.0s - 17.0s)
    # ========================================================
    else:
        local_t = (t - 14.0) / 3.0
        draw_stars(canvas)
        draw_earth(canvas, 270, 35, 14)
        draw_lunar_terrain(canvas)
        draw_ship(canvas, 60, 130)

        base_x, base_y = 210, 148
        # Deployed Dome
        pygame.draw.ellipse(canvas, PALETTE["HULL_LIGHT"], (base_x - 18, base_y - 22, 36, 44))
        canvas.fill(PALETTE["REGOLITH_LIGHT"], (0, base_y, INTERNAL_WIDTH, 32))
        canvas.fill(PALETTE["CYAN_NEON"], (base_x - 30, base_y - 6, 2, 6))
        canvas.fill(PALETTE["CYAN_NEON"], (base_x + 30, base_y - 6, 2, 6))

        # Antenna mast
        pygame.draw.line(canvas, PALETTE["HULL_DARK"], (base_x, base_y - 22), (base_x, base_y - 34), 1)

        # Antenna dish rotating away from Earth toward deep trench (facing right/down)
        angle = math.radians(180 - min(130, local_t * 150))
        dish_dx = int(8 * math.cos(angle))
        dish_dy = int(8 * math.sin(angle))
        pygame.draw.line(canvas, PALETTE["FIRE_YELLOW"], (base_x, base_y - 34), (base_x + dish_dx, base_y - 34 + dish_dy), 2)

        # Ping wave towards the dark edge
        if local_t > 0.5:
            ping_dist = int((local_t - 0.5) * 60)
            pygame.draw.arc(canvas, PALETTE["FIRE_YELLOW"], (base_x + ping_dist, base_y - 45, 16, 20), -0.8, 0.8, 1)

        # Scout facing the darkness
        draw_astronaut(canvas, 175, 148, direction=1)

    # --- LETTERBOX BARS (Cinematic 21:9 Framing) ---
    canvas.fill(PALETTE["BLACK"], (0, 0, INTERNAL_WIDTH, 14))
    canvas.fill(PALETTE["BLACK"], (0, INTERNAL_HEIGHT - 14, INTERNAL_WIDTH, 14))

    # --- UPSCALE 4X (320x180 -> 1280x720) ---
    pygame.transform.scale(canvas, (OUT_WIDTH, OUT_HEIGHT), upscaled)

    # Convert Pygame surface to NumPy RGB frame
    frame_array = pygame.surfarray.array3d(upscaled)
    frame_array = np.transpose(frame_array, (1, 0, 2))  # (W, H, C) -> (H, W, C)
    writer.append_data(frame_array)

    if frame % 60 == 0:
        print(f"  -> Processed {frame}/{TOTAL_FRAMES} frames ({(frame/TOTAL_FRAMES)*100:.1f}%)")

writer.close()
pygame.quit()
print(f" Rendering complete! Saved to {OUTPUT_FILENAME}")
