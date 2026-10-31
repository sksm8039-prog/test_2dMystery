import os
import math
import random
import numpy as np
import imageio

# Ensure headless operation for GitHub Actions CI
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

# --- CONFIGURATION ---
WIDTH = 1280
HEIGHT = 720
FPS = 30
TOTAL_SECONDS = 32
TOTAL_FRAMES = TOTAL_SECONDS * FPS
OUTPUT_FILENAME = "moon_mystery.mp4"

pygame.init()
screen = pygame.Surface((WIDTH, HEIGHT))

# --- COLOR PALETTE ---
PALETTE = {
    "SPACE_DEEP": (5, 6, 12),
    "SPACE_MID": (12, 14, 26),
    "EARTH_GLOW": (40, 110, 220, 60),
    "EARTH_OCEAN": (22, 65, 138),
    "EARTH_LAND": (45, 120, 58),
    "EARTH_CLOUD": (225, 238, 248),
    "HORIZON_FAR": (25, 28, 42),
    "HORIZON_MID": (46, 50, 66),
    "HORIZON_NEAR": (75, 82, 98),
    "REGOLITH": (135, 144, 156),
    "REGOLITH_SHADOW": (20, 22, 30),
    "HULL_WHITE": (220, 226, 235),
    "HULL_SHADOW": (100, 108, 122),
    "ENGINE_CORE": (255, 245, 210),
    "ENGINE_FIRE": (255, 120, 25),
    "ENGINE_SMOKE": (160, 150, 140),
    "VISOR_GOLD": (245, 190, 35),
    "NEON_CYAN": (14, 220, 245),
    "NEON_AMBER": (255, 160, 20),
    "ALERT_RED": (240, 50, 50),
}

# --- EASING FUNCTIONS (Disney Curves) ---
def ease_in_out(t):
    return t * t * (3.0 - 2.0 * t)

def ease_out_quad(t):
    return 1.0 - (1.0 - t) * (1.0 - t)

def ease_out_bounce(t):
    """Elastic landing recoil for suspension"""
    if t < (1 / 2.75):
        return 7.5625 * t * t
    elif t < (2 / 2.75):
        t -= (1.5 / 2.75)
        return 7.5625 * t * t + 0.75
    elif t < (2.5 / 2.75):
        t -= (2.25 / 2.75)
        return 7.5625 * t * t + 0.9375
    else:
        t -= (2.625 / 2.75)
        return 7.5625 * t * t + 0.984375

def ease_out_back(t, s=1.70158):
    """Overshoot & snap back for mechanical parts"""
    t -= 1.0
    return t * t * ((s + 1.0) * t + s) + 1.0

# --- SEEDED STARS & CRATERS ---
np.random.seed(1337)
random.seed(1337)
STARS = [
    (random.randint(0, WIDTH), random.randint(0, 480), random.choice([1, 1, 2]), random.uniform(0.3, 1.0))
    for _ in range(160)
]

# --- LIGHTING & DRAWING HELPERS ---
def draw_gradient_background(surface):
    for y in range(0, 480, 4):
        interp = y / 480.0
        c = [int(PALETTE["SPACE_DEEP"][i] * (1 - interp) + PALETTE["SPACE_MID"][i] * interp) for i in range(3)]
        pygame.draw.rect(surface, c, (0, y, WIDTH, 4))

def draw_starfield(surface, t):
    for x, y, size, alpha in STARS:
        twinkle = 0.7 + 0.3 * math.sin(t * 3.0 + x)
        col = [min(255, int(220 * alpha * twinkle))] * 3
        surface.fill(col, (x, y, size, size))

def draw_atmospheric_earth(surface, center_x, center_y, radius=52):
    # Outer atmospheric bloom
    halo = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    for r in range(radius + 18, radius, -2):
        a = int(35 * (1.0 - (r - radius) / 18.0))
        pygame.draw.circle(halo, (50, 130, 255, a), (radius * 2, radius * 2), r)
    surface.blit(halo, (center_x - radius * 2, center_y - radius * 2), special_flags=pygame.BLEND_ADD)

    # Ocean Base
    pygame.draw.circle(surface, PALETTE["EARTH_OCEAN"], (center_x, center_y), radius)

    # Continent masses
    pygame.draw.ellipse(surface, PALETTE["EARTH_LAND"], (center_x - 30, center_y - 25, 34, 22))
    pygame.draw.ellipse(surface, PALETTE["EARTH_LAND"], (center_x - 10, center_y + 4, 38, 28))
    pygame.draw.ellipse(surface, PALETTE["EARTH_LAND"], (center_x + 12, center_y - 32, 22, 18))

    # Swirling Weather Clouds
    pygame.draw.arc(surface, PALETTE["EARTH_CLOUD"], (center_x - 44, center_y - 40, 88, 80), 0.5, 2.2, 4)
    pygame.draw.arc(surface, PALETTE["EARTH_CLOUD"], (center_x - 38, center_y - 15, 76, 50), 3.4, 5.2, 3)

    # Curved Shadow Terminator
    shadow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (4, 5, 10, 180), (radius + 16, radius), radius + 2)
    surface.blit(shadow, (center_x - radius, center_y - radius))

def draw_lunar_landscape(surface, cam_x=0):
    # Distant peaks
    pts1 = [(0, 480)]
    for x in range(0, WIDTH + 40, 40):
        y = 390 + 25 * math.sin((x + cam_x * 0.1) * 0.007) + 12 * math.cos(x * 0.02)
        pts1.append((x, int(y)))
    pts1.extend([(WIDTH, 480), (0, 480)])
    pygame.draw.polygon(surface, PALETTE["HORIZON_FAR"], pts1)

    # Midground craters
    pts2 = [(0, 560)]
    for x in range(0, WIDTH + 20, 20):
        y = 470 + 20 * math.sin((x + cam_x * 0.3) * 0.012) + 8 * math.sin(x * 0.04)
        pts2.append((x, int(y)))
    pts2.extend([(WIDTH, 560), (0, 560)])
    pygame.draw.polygon(surface, PALETTE["HORIZON_MID"], pts2)

    # Foreground plain
    pygame.draw.rect(surface, PALETTE["REGOLITH"], (0, 540, WIDTH, HEIGHT - 540))
    # Crater indentations
    for cx, cy, rw, rh in [(220, 580, 70, 16), (680, 620, 110, 24), (1050, 565, 85, 18)]:
        pygame.draw.ellipse(surface, PALETTE["REGOLITH_SHADOW"], (cx, cy, rw, rh))
        pygame.draw.ellipse(surface, PALETTE["REGOLITH"], (cx, cy - 2, rw, rh - 2))

def draw_volumetric_light(surface, start_x, start_y, angle, length, spread, color):
    light_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    p1 = (start_x, start_y)
    p2 = (start_x + length * math.cos(angle - spread), start_y + length * math.sin(angle - spread))
    p3 = (start_x + length * math.cos(angle + spread), start_y + length * math.sin(angle + spread))
    pygame.draw.polygon(light_surf, color, [p1, p2, p3])
    surface.blit(light_surf, (0, 0), special_flags=pygame.BLEND_ADD)

# Particle system storage
dust_particles = []
def spawn_dust(x, y, count=25, speed=3.0):
    for _ in range(count):
        ang = random.uniform(math.pi * 0.75, math.pi * 1.25) if random.random() > 0.5 else random.uniform(-0.25 * math.pi, 0.25 * math.pi)
        vel = random.uniform( speed * 0.4, speed)
        dust_particles.append({
            "x": x + random.uniform(-10, 10),
            "y": y + random.uniform(-4, 4),
            "vx": math.cos(ang) * vel,
            "vy": -abs(math.sin(ang) * vel * 0.6), # low-gravity upward puff
            "life": 1.0,
            "decay": random.uniform(0.012, 0.025),
            "size": random.randint(3, 7)
        })

def update_and_draw_dust(surface):
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for p in dust_particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.04 # Low lunar gravity
        p["vx"] *= 0.985 # Vacuum drift
        p["life"] -= p["decay"]
        if p["life"] <= 0:
            dust_particles.remove(p)
            continue
        alpha = int(140 * p["life"])
        sz = int(p["size"] * (0.8 + 0.4 * (1.0 - p["life"])))
        pygame.draw.circle(surf, (*PALETTE["ENGINE_SMOKE"], alpha), (int(p["x"]), int(p["y"])), sz)
    surface.blit(surf, (0, 0))

# --- VIDEO WRITER SETUP ---
print(f"🎬 Rendering High-Fidelity Cinematic: {WIDTH}x{HEIGHT} @ {FPS}fps ({TOTAL_SECONDS}s)")
writer = imageio.get_writer(OUTPUT_FILENAME, fps=FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=1)

# =========================================================================
# MAIN CINEMATIC TIMELINE
# =========================================================================
for frame in range(TOTAL_FRAMES):
    screen.fill(PALETTE["SPACE_DEEP"])
    t = frame / FPS

    # ---------------------------------------------------------------------
    # ACT I: THE DESCENT & SUSPENSION TOUCHDOWN (0.0s -> 8.0s)
    # ---------------------------------------------------------------------
    if t < 8.0:
        local_t = t / 8.0
        draw_gradient_background(screen)
        draw_starfield(screen, t)
        draw_atmospheric_earth(screen, 1020, 140, radius=56)
        draw_lunar_landscape(screen)

        # Ship Trajectory with Anticipation Easing
        final_y = 510
        if local_t < 0.75:
            # Descending with thruster braking
            desc_t = local_t / 0.75
            ship_y = -80 + ease_in_out(desc_t) * (final_y - (-80))
            compression = 0.0
        else:
            # Touchdown: Suspension Squashes and Bounces (Disney Principle #1)
            bounce_t = (local_t - 0.75) / 0.25
            ship_y = final_y
            compression = (1.0 - ease_out_bounce(bounce_t)) * 14.0 # 14px cushion bounce

        ship_x = 420
        actual_ship_y = ship_y - compression

        # Thrusters & Regolith Billowing Plumes
        if local_t < 0.78:
            flame_scale = 1.0 if local_t < 0.65 else (0.78 - local_t) / 0.13
            flame_h = int((65 + 15 * math.sin(frame * 1.8)) * flame_scale)
            # Additive plasma core
            glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(glow_surf, (*PALETTE["ENGINE_FIRE"], 180), [
                (ship_x - 22, actual_ship_y + 10), (ship_x + 22, actual_ship_y + 10),
                (ship_x, actual_ship_y + 10 + flame_h)
            ])
            pygame.draw.polygon(glow_surf, (*PALETTE["ENGINE_CORE"], 230), [
                (ship_x - 10, actual_ship_y + 10), (ship_x + 10, actual_ship_y + 10),
                (ship_x, actual_ship_y + 10 + int(flame_h * 0.55))
            ])
            screen.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_ADD)

            if local_t > 0.45:
                spawn_dust(ship_x, 545, count=6, speed=4.5)

        update_and_draw_dust(screen)

        # Ship Chassis (High Detail Vector)
        pygame.draw.polygon(screen, PALETTE["HULL_WHITE"], [
            (ship_x, actual_ship_y - 90), (ship_x + 48, actual_ship_y), (ship_x - 48, actual_ship_y)
        ])
        pygame.draw.polygon(screen, PALETTE["HULL_SHADOW"], [
            (ship_x, actual_ship_y - 90), (ship_x, actual_ship_y), (ship_x - 48, actual_ship_y)
        ])
        # Cockpit Visor Strip
        pygame.draw.polygon(screen, PALETTE["VISOR_GOLD"], [
            (ship_x + 8, actual_ship_y - 50), (ship_x + 30, actual_ship_y - 25), (ship_x + 8, actual_ship_y - 25)
        ])

        # Hydraulic Landing Struts with Real Compression
        strut_drop = 35 - compression
        # Left leg
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x - 35, actual_ship_y), (ship_x - 65, actual_ship_y + strut_drop), 5)
        pygame.draw.line(screen, PALETTE["HULL_WHITE"], (ship_x - 78, actual_ship_y + strut_drop), (ship_x - 52, actual_ship_y + strut_drop), 4)
        # Right leg
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x + 35, actual_ship_y), (ship_x + 65, actual_ship_y + strut_drop), 5)
        pygame.draw.line(screen, PALETTE["HULL_WHITE"], (ship_x + 52, actual_ship_y + strut_drop), (ship_x + 78, actual_ship_y + strut_drop), 4)

        # Searchlight snapping on after touchdown
        if local_t > 0.85:
            draw_volumetric_light(screen, ship_x + 30, actual_ship_y - 20, math.radians(35), 280, math.radians(22), (220, 245, 255, 35))

    # ---------------------------------------------------------------------
    # ACT II: DEPRESSURIZATION & THE DESCENT (8.0s -> 15.0s)
    # ---------------------------------------------------------------------
    elif t < 15.0:
        local_t = (t - 8.0) / 7.0
        draw_gradient_background(screen)
        draw_starfield(screen, t)
        draw_atmospheric_earth(screen, 1020, 140, radius=56)
        draw_lunar_landscape(screen)

        ship_x, ship_y = 420, 510
        # Draw landed ship
        pygame.draw.polygon(screen, PALETTE["HULL_WHITE"], [(ship_x, ship_y - 90), (ship_x + 48, ship_y), (ship_x - 48, ship_y)])
        pygame.draw.polygon(screen, PALETTE["HULL_SHADOW"], [(ship_x, ship_y - 90), (ship_x, ship_y), (ship_x - 48, ship_y)])
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x - 35, ship_y), (ship_x - 65, ship_y + 35), 5)
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x + 35, ship_y), (ship_x + 65, ship_y + 35), 5)

        # Volumetric Cabin Floodlight casting onto the terrain
        draw_volumetric_light(screen, ship_x + 25, ship_y - 25, math.radians(35), 320, math.radians(25), (200, 235, 255, 45))

        # Steam venting event (Anticipation before hatch opens)
        if 0.05 < local_t < 0.35:
            spawn_dust(ship_x + 22, ship_y - 30, count=4, speed=2.0)
        update_and_draw_dust(screen)

        # Ramp Lowers Smoothly
        ramp_progress = ease_out_quad(min(1.0, local_t * 2.8))
        ramp_x = ship_x + int(70 * ramp_progress)
        ramp_y = ship_y + int(35 * ramp_progress)
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x + 15, ship_y - 5), (ramp_x, ramp_y), 4)

        # Scout Steps Out with Deliberate Low-Gravity Weight
        if local_t > 0.35:
            walk_t = (local_t - 0.35) / 0.65
            walk_progress = ease_in_out(walk_t)
            scout_x = ship_x + 20 + walk_progress * 190
            # Low g bounce stride
            scout_y = (ship_y - 5) + min(walk_progress * 1.6, 1.0) * 40 - abs(math.sin(walk_progress * math.pi * 3.5)) * 8

            # Stamped Footprint trail
            for fx in [470, 520, 570]:
                if scout_x > fx:
                    pygame.draw.ellipse(screen, PALETTE["REGOLITH_SHADOW"], (fx, 545, 10, 4))

            # Astronaut (Smooth articulated figure)
            # Life support pack
            pygame.draw.rect(screen, PALETTE["HULL_SHADOW"], (scout_x - 12, scout_y - 32, 8, 20), border_radius=3)
            # Body & Limbs
            pygame.draw.rect(screen, PALETTE["HULL_WHITE"], (scout_x - 6, scout_y - 34, 15, 22), border_radius=4)
            # Helmet & Glowing Gold Visor
            pygame.draw.circle(screen, PALETTE["HULL_WHITE"], (scout_x + 2, scout_y - 42), 11)
            pygame.draw.circle(screen, PALETTE["VISOR_GOLD"], (scout_x + 7, scout_y - 42), 6)

    # ---------------------------------------------------------------------
    # ACT III: CINEMATIC VISOR CLOSE-UP (15.0s -> 21.0s)
    # ---------------------------------------------------------------------
    elif t < 21.0:
        local_t = (t - 15.0) / 6.0
        screen.fill(PALETTE["SPACE_DEEP"])
        draw_starfield(screen, t)

        # Macro Profile Helmet
        center_hx, center_hy = 480, 360
        # Suit Collar & Outer Carbon Shell
        pygame.draw.circle(screen, PALETTE["HORIZON_MID"], (center_hx, center_hy), 290)
        pygame.draw.circle(screen, PALETTE["HULL_WHITE"], (center_hx, center_hy), 260)
        pygame.draw.rect(screen, PALETTE["HORIZON_FAR"], (0, 0, 300, HEIGHT))

        # Huge Curved Visor Bubble
        visor_rect = (center_hx - 40, center_hy - 200, 320, 400)
        pygame.draw.ellipse(screen, PALETTE["VISOR_GOLD"], visor_rect)

        # Visor Glare & Curvature Shading
        glare_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(glare_surf, (255, 255, 255, 45), (center_hx - 10, center_hy - 180, 260, 360), 12)
        screen.blit(glare_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Spherical Mirror Reflection of Earth inside the Visor
        # Earth slowly pans across the glass curvature
        earth_rx = 540 + int(30 * math.sin(local_t * 1.5))
        earth_ry = 320
        draw_atmospheric_earth(screen, earth_rx, earth_ry, radius=75)

        # Micro HUD Display pulsing in the corner of the visor
        hud_alpha = int(180 + 75 * math.sin(t * 8.0))
        hud_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(hud_surf, (*PALETTE["ALERT_RED"], hud_alpha), (center_hx + 110, center_hy + 80, 18, 6))
        pygame.draw.rect(hud_surf, (*PALETTE["NEON_CYAN"], hud_alpha), (center_hx + 110, center_hy + 94, 70, 4))
        pygame.draw.rect(hud_surf, (*PALETTE["NEON_CYAN"], hud_alpha), (center_hx + 110, center_hy + 104, 45, 4))
        screen.blit(hud_surf, (0, 0), special_flags=pygame.BLEND_ADD)

    # ---------------------------------------------------------------------
    # ACT IV: BASE DEPLOYMENT & UNCORING (21.0s -> 27.0s)
    # ---------------------------------------------------------------------
    elif t < 27.0:
        local_t = (t - 21.0) / 6.0
        draw_gradient_background(screen)
        draw_starfield(screen, t)
        draw_atmospheric_earth(screen, 1020, 140, radius=56)
        draw_lunar_landscape(screen)

        # Distant Ship
        ship_x, ship_y = 240, 510
        pygame.draw.polygon(screen, PALETTE["HULL_WHITE"], [(ship_x, ship_y - 70), (ship_x + 35, ship_y), (ship_x - 35, ship_y)])
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x - 25, ship_y), (ship_x - 45, ship_y + 35), 4)
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (ship_x + 25, ship_y), (ship_x + 45, ship_y + 35), 4)

        # Scout standing by observing the setup
        scout_x, scout_y = 610, 540
        pygame.draw.rect(screen, PALETTE["HULL_WHITE"], (scout_x - 6, scout_y - 34, 15, 22), border_radius=4)
        pygame.draw.circle(screen, PALETTE["HULL_WHITE"], (scout_x + 2, scout_y - 42), 11)
        pygame.draw.circle(screen, PALETTE["VISOR_GOLD"], (scout_x + 7, scout_y - 42), 6)

        # OUTPOST EXPANSION (Origami Petal Unfolding + Dome Inflation)
        base_x, base_y = 820, 545
        deploy_t = ease_out_back(min(1.0, local_t * 1.3))

        # 1. Central Core Pod
        pygame.draw.rect(screen, PALETTE["HULL_SHADOW"], (base_x - 20, base_y - 30, 40, 30), border_radius=5)

        # 2. Inflatable Pressurized Dome (Expands with dynamic pneumatic curve)
        dome_w = int(140 * min(1.0, deploy_t))
        dome_h = int(85 * min(1.0, deploy_t))
        if dome_w > 10:
            dome_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.ellipse(dome_surf, (*PALETTE["HULL_WHITE"], 240), (base_x - dome_w // 2, base_y - dome_h, dome_w, dome_h * 2))
            screen.blit(dome_surf, (0, 0))
            # Clip bottom half into lunar regolith
            pygame.draw.rect(screen, PALETTE["REGOLITH"], (0, base_y, WIDTH, HEIGHT - base_y))

        # 3. Solar Array Wings Gliding Outward
        wing_span = int(110 * deploy_t)
        pygame.draw.line(screen, PALETTE["NEON_CYAN"], (base_x - 30, base_y - 20), (base_x - 30 - wing_span, base_y - 35), 4)
        pygame.draw.line(screen, PALETTE["NEON_CYAN"], (base_x + 30, base_y - 20), (base_x + 30 + wing_span, base_y - 35), 4)

        # 4. Neon Energy Conduits Pulsing Onward Across the Soil
        if local_t > 0.5:
            glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            conduit_len = int(180 * (local_t - 0.5) / 0.5)
            pygame.draw.line(glow_surf, (*PALETTE["NEON_CYAN"], 220), (base_x, base_y), (base_x + conduit_len, base_y + 15), 3)
            pygame.draw.line(glow_surf, (*PALETTE["NEON_CYAN"], 220), (base_x, base_y), (base_x - conduit_len, base_y + 15), 3)
            # Perimeter Beacon Stakes
            pygame.draw.circle(glow_surf, (*PALETTE["NEON_AMBER"], 255), (base_x - 140, base_y - 6), 6)
            pygame.draw.circle(glow_surf, (*PALETTE["NEON_AMBER"], 255), (base_x + 140, base_y - 6), 6)
            screen.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_ADD)

    # ---------------------------------------------------------------------
    # ACT V: THE MYSTERY HOOK (27.0s -> 32.0s)
    # ---------------------------------------------------------------------
    else:
        local_t = (t - 27.0) / 5.0
        draw_gradient_background(screen)
        draw_starfield(screen, t)
        draw_atmospheric_earth(screen, 1020, 140, radius=56)
        draw_lunar_landscape(screen)

        base_x, base_y = 820, 545
        # Fully constructed base
        pygame.draw.ellipse(screen, PALETTE["HULL_WHITE"], (base_x - 70, base_y - 85, 140, 170))
        pygame.draw.rect(screen, PALETTE["REGOLITH"], (0, base_y, WIDTH, HEIGHT - base_y))
        pygame.draw.line(screen, PALETTE["NEON_CYAN"], (base_x - 30, base_y - 20), (base_x - 140, base_y - 35), 4)
        pygame.draw.line(screen, PALETTE["NEON_CYAN"], (base_x + 30, base_y - 20), (base_x + 140, base_y - 35), 4)

        # Antenna Mast
        pygame.draw.line(screen, PALETTE["HULL_SHADOW"], (base_x, base_y - 85), (base_x, base_y - 130), 4)

        # Antenna Dish: Rotates with mechanical ease away from Earth into dark lunar chasm
        turn_t = ease_in_out(min(1.0, local_t * 1.5))
        current_angle = math.radians(190 - turn_t * 155)  # Turns toward the dark right trench
        dish_dx = 24 * math.cos(current_angle)
        dish_dy = 24 * math.sin(current_angle)
        dish_pos = (base_x, base_y - 130)
        pygame.draw.line(screen, PALETTE["NEON_AMBER"], dish_pos, (dish_pos[0] + dish_dx, dish_pos[1] + dish_dy), 6)

        # The Mystery Ping: Concentric sonar wave radiating into the deep darkness
        if local_t > 0.45:
            ping_t = (local_t - 0.45) / 0.55
            ping_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for ring in range(3):
                ring_rad = int((ping_t * 300) - ring * 45)
                if ring_rad > 5:
                    alpha = max(0, int(220 * (1.0 - ring_rad / 300.0)))
                    pygame.draw.arc(
                        ping_surf, (*PALETTE["NEON_AMBER"], alpha),
                        (dish_pos[0] + dish_dx - ring_rad, dish_pos[1] + dish_dy - ring_rad, ring_rad * 2, ring_rad * 2),
                        -0.45, 0.45, 3
                    )
            screen.blit(ping_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Scout turns and stares into the distance
        scout_x, scout_y = 610, 540
        pygame.draw.rect(screen, PALETTE["HULL_WHITE"], (scout_x - 6, scout_y - 34, 15, 22), border_radius=4)
        pygame.draw.circle(screen, PALETTE["HULL_WHITE"], (scout_x + 2, scout_y - 42), 11)
        pygame.draw.circle(screen, PALETTE["VISOR_GOLD"], (scout_x + 7, scout_y - 42), 6)

        # Cinematic Fade-Out to Black at the end
        if local_t > 0.8:
            fade_alpha = int(255 * ((local_t - 0.8) / 0.2))
            fade_surf = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(fade_alpha)
            screen.blit(fade_surf, (0, 0))

    # --- 2.39:1 ANAMORPHIC WIDESCREEN LETTERBOXING ---
    pygame.draw.rect(screen, (0, 0, 0), (0, 0, WIDTH, 54))
    pygame.draw.rect(screen, (0, 0, 0), (0, HEIGHT - 54, WIDTH, 54))

    # Convert surface to frame array for MP4 encoding
    frame_array = pygame.surfarray.array3d(screen)
    frame_array = np.transpose(frame_array, (1, 0, 2))
    writer.append_data(frame_array)

    if frame % 90 == 0:
        print(f"  🎬 Rendering frame {frame}/{TOTAL_FRAMES} ({(frame/TOTAL_FRAMES)*100:.1f}%)")

writer.close()
pygame.quit()
print(f"✨ Production finish complete! Video saved as: {OUTPUT_FILENAME}")
