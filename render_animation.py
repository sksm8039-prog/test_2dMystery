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
    pygame.draw.line(surface, COLOR_CRATER_MID, (x - 28, strut_y), (x - 70, pad_y), 7)
    pygame.draw.line(surface, COLOR_SHIP_HILITE, (x - 22, strut_y + 4), (x - 52, pad_y - 8), 3) # Piston rod
    pygame.draw.line(surface, COLOR_SHIP_DARK, (x - 85, pad_y), (x - 55, pad_y), 6) # Footpad
    # Right Arm
    pygame.draw.line(surface, COLOR_CRATER_MID, (x + 28, strut_y), (x + 70, pad_y), 7)
    pygame.draw.line(surface, COLOR_SHIP_HILITE, (x + 22, strut_y + 4), (x + 52, pad_y - 8), 3) # Piston rod
    pygame.draw.line(surface, COLOR_SHIP_DARK, (x + 55, pad_y), (x + 85, pad_y), 6) # Footpad

# --- VIDEO WRITER SETUP ---
print(f"🎬 Compiling Cinematic Masterpiece: {WIDTH}x{HEIGHT} @ {FPS}fps ({TOTAL_SECONDS}s)")
writer = imageio.get_writer(OUTPUT_FILENAME, fps=FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=1)

# =========================================================================
# CINEMATIC DIRECTOR PIPELINE
# =========================================================================
for frame in range(TOTAL_FRAMES):
    render_surface.fill(COLOR_DEEP_VOID)
    t = frame / FPS

    # ---------------------------------------------------------------------
    # SCENE 1: THE MONUMENTAL DESCENT (0.0s -> 7.5s)
    # Camera: Slow smooth tilt-up, tracking the fiery retro-burn touchdown
    # ---------------------------------------------------------------------
    if t < 7.5:
        scene_t = t / 7.5
        # Camera Pan & Shake
        cam_shake = math.sin(frame * 1.5) * max(0.0, 1.8 * (0.8 - scene_t))
        cam_y = ease_in_out_cubic(scene_t) * 120 + cam_shake
        
        # Starfield Parallax
        for sx, sy, sz, sa in STARFIELD:
            render_surface.fill([int(220 * sa)] * 3, (sx, int(sy - cam_y * 0.15) % HEIGHT, sz, sz))
            
        # Glowing Earth in Upper Horizon
        render_surface.blit(earth_surface, (940, int(80 - cam_y * 0.25)))
        
        # Parallax Lunar Horizon
        for lx in range(0, WIDTH + 40, 30):
            hy = int(520 - cam_y + 24 * math.sin(lx * 0.008) + 8 * math.cos(lx * 0.02))
            pygame.draw.rect(render_surface, COLOR_CRATER_FAR, (lx, hy, 32, HEIGHT - hy))
        pygame.draw.rect(render_surface, COLOR_REGOLITH, (0, int(610 - cam_y), WIDTH, HEIGHT))

        # Ship Descent with Cushioned Landing (Squash & Stretch)
        ground_y = 570
        if scene_t < 0.70:
            ship_norm = scene_t / 0.70
            ship_y = -80 + ease_in_out_cubic(ship_norm) * (ground_y - (-80))
            suspension = 0.0
            burn = 1.0
        else:
            settle_t = (scene_t - 0.70) / 0.30
            ship_y = ground_y
            suspension = (1.0 - ease_out_elastic(settle_t)) * 18.0
            burn = max(0.0, 1.0 - settle_t * 3.5)

        ship_x = 480
        act_y = ship_y - cam_y

        # Volumetric Plasma Flare
        if burn > 0.01:
            flame_len = (85 + 20 * math.sin(frame * 1.8)) * burn
            glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(glow, (*COLOR_PLASMA_AMBER, int(180 * burn)), [
                (ship_x - 26, act_y + 15), (ship_x + 26, act_y + 15), (ship_x, act_y + 15 + flame_len)
            ])
            pygame.draw.polygon(glow, (*COLOR_PLASMA_CORE, int(240 * burn)), [
                (ship_x - 12, act_y + 15), (ship_x + 12, act_y + 15), (ship_x, act_y + 15 + flame_len * 0.6)
            ])
            render_surface.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
            emit_dust(ship_x, int(ground_y + 40), count=6, speed=4.5)

        render_dust(render_surface, 0, cam_y)
        draw_industrial_lander(render_surface, ship_x, act_y, suspension)

    # ---------------------------------------------------------------------
    # SCENE 2: THE DEPRESSURIZATION & FIRST STEP (7.5s -> 14.0s)
    # Camera: Low-angle dramatic pedestal shot looking up at the hatch
    # ---------------------------------------------------------------------
    elif t < 14.0:
        scene_t = (t - 7.5) / 6.5
        # Slow cinematic push-in
        zoom = 1.0 + scene_t * 0.08
        draw_industrial_lander(render_surface, 480, 500)
        
        # Volumetric Floodlight cutting through darkness
        draw_light_cone(render_surface, 510, 470, math.radians(40), 450, math.radians(24), (200, 240, 255, 45))

        # High-Pressure Steam Venting (Anticipation)
        if 0.08 < scene_t < 0.40:
            emit_dust(510, 480, count=4, speed=2.5, spread=0.4)
        render_dust(render_surface, 0, 0)

        # Hydraulic Ramp lowers
        ramp_prog = smoothstep(0.15, 0.45, scene_t)
        rx = 480 + 20 + int(75 * ramp_prog)
        ry = 500 + 10 + int(42 * ramp_prog)
        pygame.draw.line(render_surface, COLOR_SHIP_DARK, (500, 505), (rx, ry), 5)
        pygame.draw.line(render_surface, COLOR_SHIP_HILITE, (500, 505), (rx, ry), 1)

        # Scout Steps Out into the Vacuum
        if scene_t > 0.40:
            walk_t = (scene_t - 0.40) / 0.60
            walk_progress = ease_in_out_cubic(walk_t)
            scout_x = 510 + walk_progress * 180
            scout_y = 510 + min(walk_progress * 1.5, 1.0) * 42 - abs(math.sin(walk_progress * math.pi * 4.0)) * 5
            cycle = walk_progress * math.pi * 8.0
            
            # Ground dust on impact
            if int(walk_progress * 8) % 2 == 1:
                emit_dust(scout_x, scout_y + 45, count=1, speed=1.2)
                
            draw_detailed_scout(render_surface, scout_x, scout_y, walk_cycle=cycle, direction=1)

    # ---------------------------------------------------------------------
    # SCENE 3: MACRO VISOR CHOP — THE ABYSS GAZE (14.0s -> 20.0s)
    # Camera: Intimate macro lens, curved reflection in 24k gold visor
    # ---------------------------------------------------------------------
    elif t < 20.0:
        scene_t = (t - 14.0) / 6.0
        render_surface.fill(COLOR_DEEP_VOID)

        # Subtle handheld camera breathing
        breathe = math.sin(t * 1.8) * 4.0
        hx, hy = 420, 360 + breathe

        # Giant Cinematic Helmet Shell
        pygame.draw.circle(render_surface, COLOR_CRATER_FAR, (int(hx), int(hy)), 310)
        pygame.draw.circle(render_surface, COLOR_SHIP_DARK, (int(hx), int(hy)), 280)
        pygame.draw.circle(render_surface, COLOR_SHIP_HILITE, (int(hx), int(hy)), 280, 3)

        # Curved Spherical Visor
        visor_rect = (int(hx - 20), int(hy - 190), 380, 380)
        pygame.draw.ellipse(render_surface, COLOR_GOLD_VISOR, visor_rect)

        # Earth Reflection (Slow Pan across glass)
        earth_refl_x = int(hx + 100 + scene_t * 40)
        earth_refl_y = int(hy - 40)
        render_surface.blit(earth_surface, (earth_refl_x, earth_refl_y))

        # Visor Fresnel Glare & Horizon Shadow
        glare = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(glare, (255, 255, 255, 60), (hx + 40, hy - 170, 280, 340), 16)
        # Deep mystery trench reflected in the lower hemisphere of visor
        pygame.draw.polygon(glare, (8, 10, 16, 210), [
            (hx, hy + 40), (hx + 360, hy - 10), (hx + 360, hy + 190), (hx, hy + 190)
        ])
        render_surface.blit(glare, (0, 0), special_flags=pygame.BLEND_ADD)

        # HUD Alert: Incoming Coordinate Signal
        if int(t * 6.0) % 2 == 0:
            hud = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(hud, (240, 60, 60, 220), (hx + 80, hy + 80, 22, 6))
            pygame.draw.rect(hud, (*COLOR_CYAN_LIGHT, 180), (hx + 80, hy + 94, 90, 4))
            render_surface.blit(hud, (0, 0), special_flags=pygame.BLEND_ADD)

    # ---------------------------------------------------------------------
    # SCENE 4: DEPLOYING OUTPOST ZERO (20.0s -> 25.5s)
    # Camera: Wide cinematic master tracking shot, mechanical expansion
    # ---------------------------------------------------------------------
    elif t < 25.5:
        scene_t = (t - 20.0) / 5.5
        # Background elements
        render_surface.blit(earth_surface, (980, 70))
        for lx in range(0, WIDTH + 40, 40):
            hy = int(500 + 20 * math.sin(lx * 0.01))
            pygame.draw.rect(render_surface, COLOR_CRATER_FAR, (lx, hy, 42, HEIGHT - hy))
        pygame.draw.rect(render_surface, COLOR_REGOLITH, (0, 580, WIDTH, HEIGHT))

        # Distant Ship Silhouette
        draw_industrial_lander(render_surface, 220, 530)
        draw_detailed_scout(render_surface, 640, 565, walk_cycle=0.0, direction=1)

        # Mechanical Modular Outpost Deployment
        base_x, base_y = 860, 580
        deploy_prog = ease_in_out_cubic(min(1.0, scene_t * 1.4))

        # 1. Pneumatic Foundation Anchors
        pygame.draw.rect(render_surface, COLOR_SHIP_DARK, (base_x - 30, base_y - 35, 60, 35), border_radius=4)
        
        # 2. Geodesic Pressurized Habitat (Expands with pneumatic tension)
        dome_rad = int(85 * deploy_prog)
        if dome_rad > 8:
            dome_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(dome_surf, (*COLOR_SHIP_MID, 255), (base_x, base_y), dome_rad)
            pygame.draw.circle(dome_surf, (*COLOR_SHIP_HILITE, 120), (base_x, base_y), dome_rad, 3)
            # Clip base into ground
            render_surface.blit(dome_surf, (0, 0))
            pygame.draw.rect(render_surface, COLOR_REGOLITH, (0, base_y, WIDTH, HEIGHT - base_y))

        # 3. Solar Truss Arrays Folding Outward
        wing_w = int(140 * deploy_prog)
        pygame.draw.line(render_surface, COLOR_CYAN_LIGHT, (base_x - 20, base_y - 25), (base_x - 20 - wing_w, base_y - 45), 4)
        pygame.draw.line(render_surface, COLOR_CYAN_LIGHT, (base_x + 20, base_y - 25), (base_x + 20 + wing_w, base_y - 45), 4)

        # 4. Energy Lines tracing neon blue through the soil
        if scene_t > 0.45:
            conduit = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            line_len = int(220 * (scene_t - 0.45) / 0.55)
            pygame.draw.line(conduit, (*COLOR_CYAN_LIGHT, 230), (base_x, base_y + 4), (base_x + line_len, base_y + 12), 3)
            pygame.draw.line(conduit, (*COLOR_CYAN_LIGHT, 230), (base_x, base_y + 4), (base_x - line_len, base_y + 12), 3)
            render_surface.blit(conduit, (0, 0), special_flags=pygame.BLEND_ADD)

    # ---------------------------------------------------------------------
    # SCENE 5: THE MYSTERY TRANSMISSION (25.5s -> 30.0s)
    # Camera: Slow dolly out framing the scout against the unknown abyss
    # ---------------------------------------------------------------------
    else:
        scene_t = (t - 25.5) / 4.5
        render_surface.blit(earth_surface, (980, 70))
        pygame.draw.rect(render_surface, COLOR_REGOLITH, (0, 580, WIDTH, HEIGHT))

        base_x, base_y = 860, 580
        # Fully constructed base
        pygame.draw.circle(render_surface, COLOR_SHIP_MID, (base_x, base_y), 85)
        pygame.draw.rect(render_surface, COLOR_REGOLITH, (0, base_y, WIDTH, HEIGHT - base_y))
        pygame.draw.line(render_surface, COLOR_CYAN_LIGHT, (base_x - 20, base_y - 25), (base_x - 160, base_y - 45), 4)
        pygame.draw.line(render_surface, COLOR_CYAN_LIGHT, (base_x + 20, base_y - 25), (base_x + 160, base_y - 45), 4)

        # Comms Array Mast
        pygame.draw.line(render_surface, COLOR_SHIP_HILITE, (base_x, base_y - 85), (base_x, base_y - 145), 4)
        
        # Dish Antenna: Rotates away from Earth toward the dark unexplored trench
        dish_turn = ease_in_out_cubic(min(1.0, scene_t * 1.6))
        dish_angle = math.radians(205 - dish_turn * 170)
        dish_pos = (base_x, base_y - 145)
        dish_end = (dish_pos[0] + 32 * math.cos(dish_angle), dish_pos[1] + 32 * math.sin(dish_angle))
        pygame.draw.line(render_surface, COLOR_AMBER_LIGHT, dish_pos, dish_end, 7)

        # Concentric Signal Pings Radiating into the Abyss
        if scene_t > 0.40:
            ping_t = (scene_t - 0.40) / 0.60
            ping_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for ring in range(3):
                rad = int((ping_t * 420) - ring * 65)
                if rad > 10:
                    alpha = max(0, int(230 * (1.0 - rad / 420.0)))
                    pygame.draw.arc(
                        ping_surf, (*COLOR_AMBER_LIGHT, alpha),
                        (dish_end[0] - rad, dish_end[1] - rad, rad * 2, rad * 2),
                        -0.45, 0.45, 4
                    )
            render_surface.blit(ping_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Scout Turns Away from Earth, staring into the dark
        draw_detailed_scout(render_surface, 640, 565, walk_cycle=0.0, direction=1)

        # Cinematic Fade to Black
        if scene_t > 0.75:
            fade_a = int(255 * ((scene_t - 0.75) / 0.25))
            black_veil = pygame.Surface((WIDTH, HEIGHT))
            black_veil.fill((0, 0, 0))
            black_veil.set_alpha(fade_a)
            render_surface.blit(black_veil, (0, 0))

    # =====================================================================
    # POST-PROCESSING STACK: VIGNETTE, FILM GRAIN & ANAMORPHIC BARS
    # =====================================================================
    # 1. Subtle Radial Lens Vignette
    render_surface.blit(vignette_mask, (0, 0))

    # 2. Dynamic 35mm Film Grain (Eliminates flat computer look)
    grain_raw = np.random.randint(-12, 12, (HEIGHT // 2, WIDTH // 2), dtype=np.int16)
    grain_surf = pygame.surfarray.make_surface(grain_raw.repeat(2, axis=0).repeat(2, axis=1))
    grain_surf.set_alpha(38)
    render_surface.blit(grain_surf, (0, 0), special_flags=pygame.BLEND_ADD)

    # 3. True 2.39:1 Anamorphic Widescreen Letterbox Bars
    pygame.draw.rect(render_surface, (0, 0, 0), (0, 0, WIDTH, 64))
    pygame.draw.rect(render_surface, (0, 0, 0), (0, HEIGHT - 64, WIDTH, 64))

    # Convert to NumPy array for H.264 MP4 encoder
    frame_array = pygame.surfarray.array3d(render_surface)
    frame_array = np.transpose(frame_array, (1, 0, 2))
    writer.append_data(frame_array)

    if frame % 90 == 0:
        print(f"  📽️ Rendered frame {frame}/{TOTAL_FRAMES} ({(frame/TOTAL_FRAMES)*100:.1f}%)")

writer.close()
pygame.quit()
print(f"✨ Master render finished! Output file: {OUTPUT_FILENAME}")
