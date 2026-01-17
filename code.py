# main.py

import sys
import random
from pathlib import Path
import pygame

# =============================
# CONFIG
# =============================
SCREEN_W = 1200
SCREEN_H = 720
FPS = 60

# Win after passing level 5 (i.e. reaching score 1200)
WIN_SCORE = 1200

# Background tiles
ASSETS_BG_1 = Path("bg1.png")
ASSETS_BG_2 = Path("bg2.png")

# Ship
ASSETS_SHIP = Path("ship.png")
SHIP_X = 110
SHIP_SPEED_PX_PER_SEC = 420
SHIP_SCALE_H = 35  # <-- ship size

# Ship bullet
ASSETS_BULLET = Path("bullet1.png")
BULLET_SPEED_PX_PER_SEC = 900
BULLET_COOLDOWN = 0.12
BULLET_SCALE_H = 18

# Tunnel
ASSETS_WALL = Path("wall.png")
BLOCK = 24
SCROLL_SPEED_PX_PER_SEC = 180
WALL_BAND_THICKNESS = 3  # thin band so outside stays visible
TUNNEL_INSIDE_COLOR = (10, 15, 40)  # dark navy

# Corridor
MIN_CORRIDOR_H = 12
MAX_CORRIDOR_H = 16

# Base wobble (will increase with level)
CENTER_DRIFT = 1
WIDTH_DRIFT = 1

SPAWN_GRACE = 1.0

# Planets (immobile)
PLANET_PATHS = [Path(f"planet{i}.png") for i in range(1, 8)]
PLANET_SPAWN_CHANCE_PER_COLUMN = 0.18
PLANET_MIN_GAP_COLS = 6
PLANET_SCALE_H = 40
PLANET_SAFE_MARGIN_PX = 10

# Asteroids (mobile) - crash animation frames
ASTEROID_FRAMES = [Path(f"asteroids_{i}.png") for i in range(1, 7)]  # 1..6
ASTEROID_EXPLODE_FPS = 18   # speed of crash animation
ASTEROID_SPAWN_CHANCE_PER_COLUMN = 0.08   # <- fewer asteroids
ASTEROID_MIN_GAP_COLS = 10                # <- more spacing
ASTEROID_SCALE_H_MIN = 26
ASTEROID_SCALE_H_MAX = 55
ASTEROID_VX_MIN = 80
ASTEROID_VX_MAX = 220
ASTEROID_VY_MAX = 55
ASTEROID_SAFE_MARGIN_PX = 12

# UFOs (enemy) - PNG
ASSETS_UFO = Path("ufo.png")
UFO_SPAWN_CHANCE_PER_COLUMN = 0.11
UFO_MIN_GAP_COLS = 12
UFO_SCALE_H = 34

UFO_VX_MIN = 40
UFO_VX_MAX = 140
UFO_VY_MAX = 45

UFO_FIRE_CHANCE_PER_SEC = 0.6
UFO_BULLET_SPEED = 520
UFO_BULLET_RADIUS = 4
UFO_BULLET_COLOR = (80, 255, 120)

# Heart pickup (simple drawn shape)
HEART_PICKUP_SPAWN_CHANCE_PER_COLUMN = 0.06
HEART_PICKUP_MIN_GAP_COLS = 18
HEART_PICKUP_SIZE = (18, 14)

# HP / damage (half-heart units)
MAX_HEARTS = 5
MAX_HP_UNITS = MAX_HEARTS * 2  # 10
DMG_HALF = 1                   # -0.5 heart
DMG_FULL = 2                   # -1.0 heart
INVULN_TIME = 0.55

# Level transition
LEVEL_BANNER_TIME = 2.2  # seconds


# =============================
# LEVEL SYSTEM
# =============================
def get_level(score: int) -> int:
    # show up to 5, WIN is separate (score >= 1200)
    return min(5, 1 + (score // 300))


def level_multipliers(level: int):
    ship_mul = 1.0
    scroll_mul = 1.0
    if level >= 2:
        ship_mul = 1.12
        scroll_mul = 1.12
    if level >= 4:
        ship_mul = 1.25
        scroll_mul = 1.25
    if level >= 5:
        ship_mul = 1.35
        scroll_mul = 1.35
    return ship_mul, scroll_mul


def level_wobble(level: int):
    # more wobble + harder after L3/L4/L5
    c = CENTER_DRIFT
    w = WIDTH_DRIFT
    if level >= 3:
        c += 1
    if level >= 4:
        c += 1
        w += 1
    if level >= 5:
        c += 1
        w += 1
    return c, w


def level_text(level: int):
    if level == 1:
        now = "Now: Planets only"
        nxt = "Next (500): + Asteroids + faster"
    elif level == 2:
        now = "Now: Asteroids unlocked + faster"
        nxt = "Next (1000): + UFOs + heart pickups"
    elif level == 3:
        now = "Now: UFOs + heart pickups"
        nxt = "Next (1500): Faster + more wobble"
    elif level == 4:
        now = "Now: Faster + more wobble"
        nxt = "Next (2000): Even faster + more wobble"
    else:
        now = "Now: Max speed + max wobble"
        nxt = f"Next ({WIN_SCORE}): YOU WIN"
    return now, nxt


# =============================
# HELPERS
# =============================
def load_img(path: Path, alpha=False) -> pygame.Surface:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    img = pygame.image.load(path)
    return img.convert_alpha() if alpha else img.convert()


def scale_to_height(img: pygame.Surface, target_h: int) -> pygame.Surface:
    ratio = target_h / img.get_height()
    target_w = int(img.get_width() * ratio)
    return pygame.transform.smoothscale(img, (target_w, target_h))


def clamp(v, a, b):
    return max(a, min(b, v))


# =============================
# TUNNEL LOGIC
# =============================
def make_tunnel_column(center_row: int, corridor_h: int, rows_in_blocks: int):
    top = center_row - corridor_h // 2
    top = clamp(top, 0, rows_in_blocks - corridor_h)
    bottom = top + corridor_h
    return top, bottom


def next_tunnel_params(center_row: int, corridor_h: int, rows_in_blocks: int, drift_c: int, drift_w: int):
    center_row += random.randint(-drift_c, drift_c)
    corridor_h += random.randint(-drift_w, drift_w)

    corridor_h = clamp(corridor_h, MIN_CORRIDOR_H, MAX_CORRIDOR_H)
    half = corridor_h // 2
    center_row = clamp(center_row, half, rows_in_blocks - 1 - half)
    return center_row, corridor_h


def corridor_bounds_px_for_x(tunnel_cols, tunnel_scroll_x, screen_x: float):
    col_idx = int((screen_x + tunnel_scroll_x) // BLOCK)
    col_idx = clamp(col_idx, 0, len(tunnel_cols) - 1)
    top, bottom = tunnel_cols[col_idx]
    return top * BLOCK, bottom * BLOCK


# =============================
# DRAW: TUNNEL WALL (wall.png tiled)
# =============================
def draw_tunnel_blocks(screen, tunnel_cols, tunnel_scroll_x, rows_in_blocks, wall_tile: pygame.Surface):
    for i, (top, bottom) in enumerate(tunnel_cols):
        x = i * BLOCK - tunnel_scroll_x

        start_top = max(0, top - WALL_BAND_THICKNESS)
        for rr in range(start_top, top):
            screen.blit(wall_tile, (x, rr * BLOCK))

        end_bot = min(rows_in_blocks, bottom + WALL_BAND_THICKNESS)
        for rr in range(bottom, end_bot):
            screen.blit(wall_tile, (x, rr * BLOCK))


# =============================
# UI: HEARTS + PICKUP
# =============================
def draw_hearts(screen: pygame.Surface, hp_units: int):
    x0, y0 = 12, 64
    spacing = 26
    for i in range(MAX_HEARTS):
        units_here = hp_units - i * 2
        r = pygame.Rect(x0 + i * spacing, y0, 20, 16)
        pygame.draw.rect(screen, (40, 40, 40), r, border_radius=4)
        pygame.draw.rect(screen, (200, 200, 200), r, 1, border_radius=4)

        if units_here >= 2:
            pygame.draw.rect(screen, (255, 80, 90), r.inflate(-4, -4), border_radius=4)
        elif units_here == 1:
            half = r.inflate(-4, -4)
            half.width //= 2
            pygame.draw.rect(screen, (255, 80, 90), half, border_radius=4)



def draw_heart_pickup(screen, rect: pygame.Rect):
    pygame.draw.rect(screen, (255, 100, 130), rect, border_radius=4)
    pygame.draw.rect(screen, (255, 210, 220), rect, 2, border_radius=4)


def draw_center_banner(screen: pygame.Surface, big_font, font, title: str, line1: str, line2: str):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 165))
    screen.blit(overlay, (0, 0))

    t = big_font.render(title, True, (240, 240, 240))
    l1 = font.render(line1, True, (220, 220, 220))
    l2 = font.render(line2, True, (220, 220, 220))

    screen.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 50)))
    screen.blit(l1, l1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 5)))
    screen.blit(l2, l2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 35)))


# =============================
# MAIN
# =============================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Tunnel Shooter (Levels + Transitions)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Arial", 20)
    big_font = pygame.font.SysFont("Arial", 54, bold=True)

    # background
    bg1 = load_img(ASSETS_BG_1, alpha=False)
    bg2 = load_img(ASSETS_BG_2, alpha=False)
    bg_tiles = [bg1, bg2]
    TILE_W, TILE_H = bg1.get_size()

    # wall tile
    wall_raw = load_img(ASSETS_WALL, alpha=True)
    wall_tile = pygame.transform.smoothscale(wall_raw, (BLOCK, BLOCK))

    # ship
    ship = load_img(ASSETS_SHIP, alpha=True)
    ship = scale_to_height(ship, SHIP_SCALE_H)

    # ship bullet
    bullet_img = load_img(ASSETS_BULLET, alpha=True)
    bullet_img = scale_to_height(bullet_img, BULLET_SCALE_H)

    # planets
    planet_imgs = []
    for p in PLANET_PATHS:
        img = load_img(p, alpha=True)
        img = scale_to_height(img, PLANET_SCALE_H)
        planet_imgs.append(img)

    # asteroid frames (raw)
    asteroid_raw_frames = [load_img(p, alpha=True) for p in ASTEROID_FRAMES]

    # ufo png
    ufo_img = load_img(ASSETS_UFO, alpha=True)
    ufo_img = scale_to_height(ufo_img, UFO_SCALE_H)

    # background grid (random once, no flicker)
    bg_cols = SCREEN_W // TILE_W + 3
    bg_rows = SCREEN_H // TILE_H + 3
    bg_grid = [[random.choice(bg_tiles) for _ in range(bg_cols)] for _ in range(bg_rows)]
    bg_scroll_x = 0.0

    # tunnel
    rows_in_blocks = SCREEN_H // BLOCK
    cols_in_blocks = SCREEN_W // BLOCK + 3
    tunnel_scroll_x = 0.0

    center_row = rows_in_blocks // 2
    corridor_h = (MIN_CORRIDOR_H + MAX_CORRIDOR_H) // 2
    tunnel_cols = []

    def rebuild_tunnel(level_now: int):
        nonlocal center_row, corridor_h, tunnel_cols
        drift_c, drift_w = level_wobble(level_now)
        center_row = rows_in_blocks // 2
        corridor_h = (MIN_CORRIDOR_H + MAX_CORRIDOR_H) // 2
        tunnel_cols.clear()
        for _ in range(cols_in_blocks):
            center_row, corridor_h = next_tunnel_params(center_row, corridor_h, rows_in_blocks, drift_c, drift_w)
            tunnel_cols.append(make_tunnel_column(center_row, corridor_h, rows_in_blocks))

    # entities
    ship_y = SCREEN_H // 2
    bullets = []        # {"x","y","rect"}
    planets = []        # {"x","y","img","rect"}
    asteroids = []      # {"x","y","vx","vy","frames","frame_i","frame_t","exploding","rect"}
    ufos = []           # {"x","y","vx","vy","img","rect"}
    ufo_bullets = []    # {"x","y","vx","vy"}
    heart_pickups = []  # {"x","y","rect"}

    cols_since_last_planet = 999
    cols_since_last_asteroid = 999
    cols_since_last_ufo = 999
    cols_since_last_heart = 999

    score = 0
    game_over = False
    game_won = False

    alive_time = 0.0
    shoot_cd = 0.0

    hp = MAX_HP_UNITS
    invuln = 0.0

    # level transition state
    current_level = 1
    transition_timer = LEVEL_BANNER_TIME
    in_transition = True  # show L1 at start

    def damage(amount_units: int):
        nonlocal hp, invuln
        if invuln > 0.0:
            return
        hp = max(0, hp - amount_units)
        invuln = INVULN_TIME

    def heal_one_heart():
        nonlocal hp
        hp = min(MAX_HP_UNITS, hp + 2)

    def restart():
        nonlocal ship_y, bg_scroll_x, tunnel_scroll_x
        nonlocal bullets, planets, asteroids, ufos, ufo_bullets, heart_pickups
        nonlocal cols_since_last_planet, cols_since_last_asteroid, cols_since_last_ufo, cols_since_last_heart
        nonlocal score, game_over, game_won, alive_time, shoot_cd, hp, invuln
        nonlocal current_level, transition_timer, in_transition

        ship_y = SCREEN_H // 2
        bg_scroll_x = 0.0
        tunnel_scroll_x = 0.0

        bullets.clear()
        planets.clear()
        asteroids.clear()
        ufos.clear()
        ufo_bullets.clear()
        heart_pickups.clear()

        cols_since_last_planet = 999
        cols_since_last_asteroid = 999
        cols_since_last_ufo = 999
        cols_since_last_heart = 999

        score = 0
        game_over = False
        game_won = False
        alive_time = 0.0
        shoot_cd = 0.0

        hp = MAX_HP_UNITS
        invuln = 0.0

        current_level = 1
        transition_timer = LEVEL_BANNER_TIME
        in_transition = True

        rebuild_tunnel(current_level)

    rebuild_tunnel(current_level)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                restart()

        keys = pygame.key.get_pressed()

        # WIN check
        if not game_won and score >= WIN_SCORE:
            game_won = True
            in_transition = False

        # Level + speeds
        level = get_level(score)
        ship_mul, scroll_mul = level_multipliers(level)
        ship_speed_now = SHIP_SPEED_PX_PER_SEC * ship_mul
        scroll_speed_now = SCROLL_SPEED_PX_PER_SEC * scroll_mul

        # Level transition trigger
        if (not game_over) and (not game_won) and (level != current_level):
            current_level = level
            transition_timer = LEVEL_BANNER_TIME
            in_transition = True

        # UPDATE (pause gameplay during transition or end states)
        if not game_over and not game_won and not in_transition:
            alive_time += dt
            shoot_cd = max(0.0, shoot_cd - dt)
            invuln = max(0.0, invuln - dt)

            # ship move
            if keys[pygame.K_UP]:
                ship_y -= ship_speed_now * dt
            if keys[pygame.K_DOWN]:
                ship_y += ship_speed_now * dt

            ship_rect = ship.get_rect(center=(SHIP_X, ship_y))
            ship_y = clamp(ship_y, ship_rect.height // 2, SCREEN_H - ship_rect.height // 2)
            ship_rect = ship.get_rect(center=(SHIP_X, ship_y))

            # shoot
            if keys[pygame.K_SPACE] and shoot_cd <= 0.0:
                shoot_cd = BULLET_COOLDOWN
                bx = ship_rect.right + 6
                by = ship_rect.centery - bullet_img.get_height() // 2
                brect = bullet_img.get_rect(topleft=(bx, by))
                bullets.append({"x": float(bx), "y": float(by), "rect": brect})

            # wobble based on level
            drift_c, drift_w = level_wobble(level)

            # scroll
            bg_scroll_x = (bg_scroll_x + scroll_speed_now * dt * 0.35) % TILE_W
            tunnel_scroll_x += scroll_speed_now * dt

            # move ship bullets right
            for b in bullets:
                b["x"] += BULLET_SPEED_PX_PER_SEC * dt
                b["rect"].topleft = (int(b["x"]), int(b["y"]))
            bullets[:] = [b for b in bullets if b["x"] < SCREEN_W + 120]

            # move planets left
            for pl in planets:
                pl["x"] -= scroll_speed_now * dt
                pl["rect"].topleft = (int(pl["x"]), int(pl["y"]))
            planets[:] = [pl for pl in planets if pl["x"] + pl["rect"].width > -120]

            # move heart pickups left (level 3+)
            for h in heart_pickups:
                h["x"] -= scroll_speed_now * dt
                h["rect"].topleft = (int(h["x"]), int(h["y"]))
            heart_pickups[:] = [h for h in heart_pickups if h["x"] + h["rect"].width > -120]

            # move asteroids (level 2+)
            if level >= 2:
                for a in asteroids:
                    if not a["exploding"]:
                        a["x"] -= (scroll_speed_now + a["vx"]) * dt
                        a["y"] += a["vy"] * dt

                        top_px, bot_px = corridor_bounds_px_for_x(tunnel_cols, tunnel_scroll_x, a["x"] + a["rect"].width * 0.5)
                        y_min = top_px + ASTEROID_SAFE_MARGIN_PX
                        y_max = bot_px - a["rect"].height - ASTEROID_SAFE_MARGIN_PX
                        if y_max > y_min:
                            if a["y"] < y_min:
                                a["y"] = y_min
                                a["vy"] *= -1
                            elif a["y"] > y_max:
                                a["y"] = y_max
                                a["vy"] *= -1

                        a["rect"].topleft = (int(a["x"]), int(a["y"]))
                    else:
                        # play crash animation
                        a["frame_t"] += dt
                        step = 1.0 / max(1, ASTEROID_EXPLODE_FPS)
                        while a["frame_t"] >= step:
                            a["frame_t"] -= step
                            a["frame_i"] += 1

                # remove when offscreen OR animation finished
                asteroids[:] = [
                    a for a in asteroids
                    if (a["x"] + a["rect"].width > -240) and (not (a["exploding"] and a["frame_i"] >= len(a["frames"])))
                ]
            else:
                asteroids.clear()

            # move UFOs + shoot (level 3+)
            if level >= 3:
                for u in ufos:
                    u["x"] -= (scroll_speed_now + u["vx"]) * dt
                    u["y"] += u["vy"] * dt

                    top_px, bot_px = corridor_bounds_px_for_x(tunnel_cols, tunnel_scroll_x, u["x"] + u["rect"].width * 0.5)
                    y_min = top_px + 8
                    y_max = bot_px - u["rect"].height - 8
                    if y_max > y_min:
                        if u["y"] < y_min:
                            u["y"] = y_min
                            u["vy"] *= -1
                        elif u["y"] > y_max:
                            u["y"] = y_max
                            u["vy"] *= -1

                    u["rect"].topleft = (int(u["x"]), int(u["y"]))

                    if random.random() < UFO_FIRE_CHANCE_PER_SEC * dt:
                        bx = u["rect"].left - 2
                        by = u["rect"].centery
                        ufo_bullets.append({"x": float(bx), "y": float(by), "vx": -UFO_BULLET_SPEED, "vy": 0.0})

                ufos[:] = [u for u in ufos if u["x"] + u["rect"].width > -240]
            else:
                ufos.clear()
                ufo_bullets.clear()

            # move UFO bullets left
            for ub in ufo_bullets:
                ub["x"] += ub["vx"] * dt
                ub["y"] += ub["vy"] * dt
            ufo_bullets[:] = [ub for ub in ufo_bullets if -60 < ub["x"] < SCREEN_W + 60]

            # advance tunnel by columns + spawns
            while tunnel_scroll_x >= BLOCK:
                tunnel_scroll_x -= BLOCK
                score += 1

                tunnel_cols.pop(0)
                center_row, corridor_h = next_tunnel_params(center_row, corridor_h, rows_in_blocks, drift_c, drift_w)
                tunnel_cols.append(make_tunnel_column(center_row, corridor_h, rows_in_blocks))

                cols_since_last_planet += 1
                cols_since_last_asteroid += 1
                cols_since_last_ufo += 1
                cols_since_last_heart += 1

                # planets spawn (all levels)
                if cols_since_last_planet >= PLANET_MIN_GAP_COLS and random.random() < PLANET_SPAWN_CHANCE_PER_COLUMN:
                    spawn_top, spawn_bottom = tunnel_cols[-1]
                    corridor_top_px = spawn_top * BLOCK
                    corridor_bot_px = spawn_bottom * BLOCK

                    img = random.choice(planet_imgs)
                    w, h = img.get_size()

                    y_min = corridor_top_px + PLANET_SAFE_MARGIN_PX
                    y_max = corridor_bot_px - h - PLANET_SAFE_MARGIN_PX
                    if y_max > y_min:
                        y = random.randint(int(y_min), int(y_max))
                        x = SCREEN_W + 30
                        rect = img.get_rect(topleft=(x, y))
                        planets.append({"x": float(x), "y": float(y), "img": img, "rect": rect})
                        cols_since_last_planet = 0

                # asteroids spawn (level 2+)
                if level >= 2:
                    if cols_since_last_asteroid >= ASTEROID_MIN_GAP_COLS and random.random() < ASTEROID_SPAWN_CHANCE_PER_COLUMN:
                        spawn_top, spawn_bottom = tunnel_cols[-1]
                        corridor_top_px = spawn_top * BLOCK
                        corridor_bot_px = spawn_bottom * BLOCK

                        target_h = random.randint(ASTEROID_SCALE_H_MIN, ASTEROID_SCALE_H_MAX)
                        frames = [scale_to_height(fr, target_h) for fr in asteroid_raw_frames]
                        w, h = frames[0].get_size()

                        y_min = corridor_top_px + ASTEROID_SAFE_MARGIN_PX
                        y_max = corridor_bot_px - h - ASTEROID_SAFE_MARGIN_PX
                        if y_max > y_min:
                            y = random.randint(int(y_min), int(y_max))
                            x = SCREEN_W + random.randint(80, 260)
                            vx = random.uniform(ASTEROID_VX_MIN, ASTEROID_VX_MAX)
                            vy = random.uniform(-ASTEROID_VY_MAX, ASTEROID_VY_MAX)
                            rect = frames[0].get_rect(topleft=(int(x), int(y)))
                            asteroids.append({
                                "x": float(x), "y": float(y),
                                "vx": vx, "vy": vy,
                                "frames": frames,
                                "frame_i": 0,
                                "frame_t": 0.0,
                                "exploding": False,
                                "rect": rect,
                            })
                            cols_since_last_asteroid = 0

                # UFO spawn (level 3+)
                if level >= 3:
                    if cols_since_last_ufo >= UFO_MIN_GAP_COLS and random.random() < UFO_SPAWN_CHANCE_PER_COLUMN:
                        spawn_top, spawn_bottom = tunnel_cols[-1]
                        corridor_top_px = spawn_top * BLOCK
                        corridor_bot_px = spawn_bottom * BLOCK

                        uw, uh = ufo_img.get_size()
                        y_min = corridor_top_px + 10
                        y_max = corridor_bot_px - uh - 10
                        if y_max > y_min:
                            y = random.randint(int(y_min), int(y_max))
                            x = SCREEN_W + random.randint(90, 280)
                            vx = random.uniform(UFO_VX_MIN, UFO_VX_MAX)
                            vy = random.uniform(-UFO_VY_MAX, UFO_VY_MAX)
                            rect = ufo_img.get_rect(topleft=(int(x), int(y)))
                            ufos.append({"x": float(x), "y": float(y), "vx": vx, "vy": vy, "img": ufo_img, "rect": rect})
                            cols_since_last_ufo = 0

                # Heart pickup spawn (level 3+, only if not full hp)
                if level >= 3 and hp < MAX_HP_UNITS:
                    if cols_since_last_heart >= HEART_PICKUP_MIN_GAP_COLS and random.random() < HEART_PICKUP_SPAWN_CHANCE_PER_COLUMN:
                        spawn_top, spawn_bottom = tunnel_cols[-1]
                        corridor_top_px = spawn_top * BLOCK
                        corridor_bot_px = spawn_bottom * BLOCK

                        w, h = HEART_PICKUP_SIZE
                        y_min = corridor_top_px + 10
                        y_max = corridor_bot_px - h - 10
                        if y_max > y_min:
                            y = random.randint(int(y_min), int(y_max))
                            x = SCREEN_W + 40
                            rect = pygame.Rect(x, y, w, h)
                            heart_pickups.append({"x": float(x), "y": float(y), "rect": rect})
                            cols_since_last_heart = 0

            # BULLETS HIT (destroy / explode)
            for b in bullets[:]:
                hit = False

                # planets: instantly removed
                for pl in planets[:]:
                    if b["rect"].colliderect(pl["rect"]):
                        planets.remove(pl)
                        score += 10
                        hit = True
                        break
                if hit:
                    bullets.remove(b)
                    continue

                # asteroids: start crash animation (don’t delete instantly)
                for a in asteroids:
                    if (not a["exploding"]) and b["rect"].colliderect(a["rect"]):
                        a["exploding"] = True
                        a["vx"] = 0.0
                        a["vy"] = 0.0
                        a["frame_i"] = 0
                        a["frame_t"] = 0.0
                        score += 15
                        hit = True
                        break
                if hit:
                    bullets.remove(b)
                    continue

                # ufos: removed
                for u in ufos[:]:
                    if b["rect"].colliderect(u["rect"]):
                        ufos.remove(u)
                        score += 25
                        hit = True
                        break
                if hit:
                    bullets.remove(b)

            # DAMAGE / COLLISIONS
            if alive_time > SPAWN_GRACE:
                ship_rect = ship.get_rect(center=(SHIP_X, ship_y))

                # wall (-0.5) + push back inside
                corridor_top_px, corridor_bot_px = corridor_bounds_px_for_x(tunnel_cols, tunnel_scroll_x, SHIP_X)
                if ship_rect.top < corridor_top_px:
                    damage(DMG_HALF)
                    ship_y = corridor_top_px + ship_rect.height // 2 + 1
                elif ship_rect.bottom > corridor_bot_px:
                    damage(DMG_HALF)
                    ship_y = corridor_bot_px - ship_rect.height // 2 - 1

                ship_rect = ship.get_rect(center=(SHIP_X, ship_y))

                # planet (-0.5)
                if invuln <= 0.0:
                    for pl in planets:
                        if ship_rect.colliderect(pl["rect"]):
                            damage(DMG_HALF)
                            break

                # asteroid (-0.5) only if NOT exploding
                if invuln <= 0.0:
                    for a in asteroids:
                        if (not a["exploding"]) and ship_rect.colliderect(a["rect"]):
                            damage(DMG_HALF)
                            break

                # ufo bullet (-0.5)
                if invuln <= 0.0:
                    for ub in ufo_bullets:
                        if ship_rect.collidepoint(int(ub["x"]), int(ub["y"])):
                            damage(DMG_HALF)
                            break

                # crash UFO (-1)
                if invuln <= 0.0:
                    hit_u = None
                    for u in ufos:
                        if ship_rect.colliderect(u["rect"]):
                            hit_u = u
                            break
                    if hit_u:
                        damage(DMG_FULL)
                        ufos.remove(hit_u)

                # heart pickup (+1 heart)
                for h in heart_pickups[:]:
                    if ship_rect.colliderect(h["rect"]):
                        heart_pickups.remove(h)
                        heal_one_heart()
                        break

                if hp <= 0:
                    game_over = True

        # Transition countdown (runs even while paused)
        if in_transition and not game_over and not game_won:
            transition_timer -= dt
            if transition_timer <= 0.0:
                in_transition = False

        # DRAW
        screen.fill((0, 0, 0))

        # background
        for r in range(bg_rows):
            for c in range(bg_cols):
                x = c * TILE_W - bg_scroll_x
                y = r * TILE_H
                screen.blit(bg_grid[r][c], (x, y))# --- dark navy inside the tunnel (corridor fill) ---
        for i, (top, bottom) in enumerate(tunnel_cols):
                x = i * BLOCK - tunnel_scroll_x
                y = top * BLOCK
                h = (bottom - top) * BLOCK

                rect = pygame.Rect(x, y, BLOCK, h)
                pygame.draw.rect(screen, TUNNEL_INSIDE_COLOR, rect)





        # tunnel walls
        draw_tunnel_blocks(screen, tunnel_cols, tunnel_scroll_x, rows_in_blocks, wall_tile)

        # planets
        for pl in planets:
            screen.blit(pl["img"], pl["rect"].topleft)

        # asteroids (frame based on state)
        for a in asteroids:
            fi = a["frame_i"]
            if fi < 0:
                fi = 0
            if fi >= len(a["frames"]):
                fi = len(a["frames"]) - 1
            screen.blit(a["frames"][fi], a["rect"].topleft)

        # ufos + their bullets
        for u in ufos:
            screen.blit(u["img"], u["rect"].topleft)
        for ub in ufo_bullets:
            pygame.draw.circle(screen, UFO_BULLET_COLOR, (int(ub["x"]), int(ub["y"])), UFO_BULLET_RADIUS)

        # heart pickups
        for h in heart_pickups:
            draw_heart_pickup(screen, h["rect"])

        # ship bullets
        for b in bullets:
            screen.blit(bullet_img, b["rect"].topleft)

        # ship (blink on invuln)
        ship_rect = ship.get_rect(center=(SHIP_X, ship_y))
        if invuln <= 0.0 or int(invuln * 20) % 2 == 0:
            screen.blit(ship, ship_rect.topleft)

        # UI
        lvl = get_level(score)
        screen.blit(font.render(f"Score: {score}   Level: {lvl}/5", True, (230, 230, 230)), (12, 10))
        screen.blit(font.render("UP/DOWN move | SPACE shoot | R restart", True, (200, 200, 200)), (12, 34))
        draw_hearts(screen, hp)

        if alive_time < SPAWN_GRACE and not game_over and not game_won:
            screen.blit(font.render("Grace: no collision yet", True, (180, 220, 180)), (12, 92))

        # Level banner
        if in_transition and not game_over and not game_won:
            now, nxt = level_text(current_level)
            draw_center_banner(
                screen, big_font, font,
                f"LEVEL {current_level}",
                now,
                nxt
            )

        # Game Over
        if game_over:
            draw_center_banner(
                screen, big_font, font,
                "GAME OVER",
                "Press R to restart",
                ""
            )

        # Win
        if game_won:
            draw_center_banner(
                screen, big_font, font,
                "YOU WIN!",
                f"Final score: {score}",
                "Press R to play again"
            )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
