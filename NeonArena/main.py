import os
import math
import random
import pygame

# -------------------------
# Basic setup
# -------------------------
WIDTH, HEIGHT = 960, 640
FPS = 60

# Zones / levels based on score
LEVEL_THRESHOLDS = [0, 100, 250, 450]  # Lv1, Lv2, Lv3, Lv4+
ZONE_NAMES = ["Calm Zone", "Hazard Zone", "Chaos Zone", "Overdrive"]

# Difficulty presets
DIFFICULTY_PRESETS = {
    "Easy": {
        "enemy_speed_mul": 0.9,
        "enemy_spawn_mul": 0.9,
        "max_enemies": 12,
    },
    "Normal": {
        "enemy_speed_mul": 1.0,
        "enemy_spawn_mul": 1.0,
        "max_enemies": 16,
    },
    "Hard": {
        "enemy_speed_mul": 1.15,
        "enemy_spawn_mul": 1.15,
        "max_enemies": 22,
    },
}

# Colors
NEON_BG_CALM = (10, 6, 30)
NEON_BG_HAZARD = (18, 6, 35)
NEON_BG_CHAOS = (22, 4, 24)
NEON_BG_OVERDRIVE = (30, 4, 22)

NEON_PINK = (255, 120, 210)
NEON_PINK_SOFT = (232, 160, 220)
NEON_BLUE = (140, 190, 255)
NEON_BLUE_SOFT = (170, 205, 255)
NEON_YELLOW = (255, 245, 130)
NEON_GREEN = (160, 255, 190)
NEON_WHITE = (240, 240, 255)
NEON_RED = (250, 90, 90)
NEON_PURPLE = (200, 120, 255)
NEON_ORANGE = (255, 180, 120)

HUD_BG = (16, 16, 40)
HUD_BORDER = (90, 110, 180)

# Orb values by color key
ORB_VALUES = {
    "yellow": 10,
    "blue": 15,
    "green": 20,
    "pink": 30,
}

# Player constants
PLAYER_RADIUS = 16
PLAYER_SPEED = 260
PLAYER_MAX_HP = 3
PLAYER_MAX_SHIELD = 2

DASH_SPEED = 600
DASH_DURATION = 0.18
DASH_COOLDOWN = 1.0

# Enemy constants
ENEMY_BASE_SPEED = 80
ENEMY_MAX_SPEED = 160
ENEMY_SPAWN_INTERVAL_START = 1.1
ENEMY_SPAWN_INTERVAL_MIN = 0.35

# Frenzy & combo
COMBO_TIMEOUT = 3.0
FRENZY_COMBO_THRESHOLD = 5
FRENZY_DURATION = 6.0

# Starfield
STAR_COUNT = 80

pygame.init()
SOUND_ENABLED = True
try:
    pygame.mixer.init()
except Exception:
    SOUND_ENABLED = False

# Screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neon Arena")
clock = pygame.time.Clock()

# -------------------------
# Fonts
# -------------------------
def load_fonts():
    font_path = os.path.join("assets", "NeonTubes.ttf")
    if os.path.exists(font_path):
        title_font = pygame.font.Font(font_path, 64)
        big_font = pygame.font.Font(font_path, 42)
        medium_font = pygame.font.Font(font_path, 26)
        small_font = pygame.font.Font(font_path, 20)
    else:
        base = pygame.font.match_font("couriernew", "consolas", "monospace")
        title_font = pygame.font.Font(base, 56)
        big_font = pygame.font.Font(base, 32)
        medium_font = pygame.font.Font(base, 22)
        small_font = pygame.font.Font(base, 18)
    return title_font, big_font, medium_font, small_font


TITLE_FONT, BIG_FONT, MEDIUM_FONT, SMALL_FONT = load_fonts()

# -------------------------
# Sound helpers
# -------------------------
def load_sound(name):
    if not SOUND_ENABLED:
        return None
    path = os.path.join("assets", name)
    if not os.path.exists(path):
        return None
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None


SFX = {
    "dash": load_sound("sfx_dash.wav"),
    "orb": load_sound("sfx_orb.wav"),
    "hit": load_sound("sfx_hit.wav"),
    "death": load_sound("sfx_death.wav"),
    "levelup": load_sound("sfx_levelup.wav"),
    "frenzy": load_sound("sfx_frenzy.wav"),
}


def play_sfx(key):
    snd = SFX.get(key)
    if snd:
        snd.play()


# -------------------------
# Utility classes
# -------------------------
class Star:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.length = random.uniform(25, 120)
        self.speed = random.uniform(15, 60)
        self.thickness = random.randint(1, 2)
        self.offset = random.uniform(0, math.pi * 2)

    def update(self, dt, zone_index):
        speed_mul = 1.0 + zone_index * 0.25
        self.x -= self.speed * speed_mul * dt
        if self.x + self.length < 0:
            self.x = WIDTH + random.uniform(0, 100)
            self.y = random.uniform(0, HEIGHT)

    def draw(self, surface, color):
        end_x = self.x + self.length
        pygame.draw.line(surface, color, (self.x, self.y), (end_x, self.y), self.thickness)


class Sparkle:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.radius = random.uniform(1, 2)
        self.alpha = random.uniform(0.2, 0.9)
        self.speed_y = random.uniform(-20, -5)

    def update(self, dt):
        self.y += self.speed_y * dt
        self.alpha += random.uniform(-0.5, 0.5) * dt
        if self.y < -10 or self.alpha < 0.1:
            self.reset()
            self.y = HEIGHT + 5

    def draw(self, surface, color):
        a = max(0, min(1, self.alpha))
        c = (int(color[0] * a), int(color[1] * a), int(color[2] * a))
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), int(self.radius))


class Particle:
    def __init__(self, x, y, color, radius, lifetime, vel=None):
        self.x = x
        self.y = y
        self.color = color
        self.radius = radius
        self.lifetime = lifetime
        self.age = 0.0
        if vel is None:
            angle = random.uniform(0, math.tau)
            speed = random.uniform(40, 160)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
        else:
            self.vx, self.vy = vel

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def alive(self):
        return self.age < self.lifetime

    def draw(self, surface):
        t = 1.0 - (self.age / self.lifetime)
        if t <= 0:
            return
        r = max(1, int(self.radius * t))
        c = (
            int(self.color[0] * t + 20 * (1 - t)),
            int(self.color[1] * t + 20 * (1 - t)),
            int(self.color[2] * t + 30 * (1 - t)),
        )
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), r)


class FloatingText:
    def __init__(self, text, x, y, color, font, lifetime=0.8):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.font = font
        self.lifetime = lifetime
        self.age = 0.0
        self.dy = -30

    def update(self, dt):
        self.age += dt
        self.y += self.dy * dt

    def alive(self):
        return self.age < self.lifetime

    def draw(self, surface):
        alpha = max(0, 1.0 - self.age / self.lifetime)
        c = (
            int(self.color[0] * alpha),
            int(self.color[1] * alpha),
            int(self.color[2] * alpha),
        )
        surf = self.font.render(self.text, True, c)
        rect = surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(surf, rect)


# -------------------------
# Player, enemy, orb
# -------------------------
class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = WIDTH * 0.5
        self.y = HEIGHT * 0.6
        self.vx = 0.0
        self.vy = 0.0
        self.hp = PLAYER_MAX_HP
        self.shield = 1
        self.radius = PLAYER_RADIUS
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.is_dashing = False
        self.invuln_timer = 0.0
        self.trail = []

    def update(self, dt, keys):
        speed = PLAYER_SPEED
        move_x = 0
        move_y = 0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_y += 1

        mag = math.hypot(move_x, move_y)
        if mag > 0:
            move_x /= mag
            move_y /= mag

        dash_active = self.is_dashing

        if dash_active:
            cur_speed = DASH_SPEED
        else:
            cur_speed = speed

        self.vx = move_x * cur_speed
        self.vy = move_y * cur_speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        self.x = max(self.radius + 6, min(WIDTH - self.radius - 6, self.x))
        self.y = max(self.radius + 6, min(HEIGHT - self.radius - 6, self.y))

        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.invuln_timer = max(0.0, self.invuln_timer - dt)

        if dash_active:
            self.trail.append((self.x, self.y, 0.18))
        for i in range(len(self.trail)):
            x, y, t = self.trail[i]
            self.trail[i] = (x, y, t - dt)
        self.trail = [p for p in self.trail if p[2] > 0]

        if self.dash_timer <= 0 and self.is_dashing:
            self.is_dashing = False

    def try_dash(self):
        if self.dash_cooldown <= 0.0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = DASH_DURATION
            self.dash_cooldown = DASH_COOLDOWN
            self.invuln_timer = DASH_DURATION * 0.75
            play_sfx("dash")

    def draw(self, surface):
        # Trail ghosts
        for x, y, t in self.trail:
            alpha = t / 0.18
            c = (
                int(NEON_YELLOW[0] * alpha),
                int(NEON_YELLOW[1] * alpha),
                int(NEON_YELLOW[2] * alpha),
            )
            pygame.draw.circle(surface, c, (int(x), int(y)), self.radius + 2, 1)

        # Main body
        body_color = NEON_YELLOW
        pygame.draw.circle(surface, body_color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, NEON_WHITE, (int(self.x), int(self.y)), self.radius, 2)

        # Shield ring
        if self.shield > 0:
            r = self.radius + 7
            pygame.draw.circle(surface, NEON_BLUE_SOFT, (int(self.x), int(self.y)), r, 2)

        # Hit flash / invulnerability
        if self.invuln_timer > 0:
            if int(self.invuln_timer * 20) % 2 == 0:
                pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius + 3, 2)


class Enemy:
    def __init__(self, enemy_type, x, y, speed_mul=1.0):
        self.enemy_type = enemy_type
        self.x = x
        self.y = y
        self.base_speed = random.uniform(ENEMY_BASE_SPEED, ENEMY_MAX_SPEED) * speed_mul
        self.angle = random.uniform(0, math.tau)
        self.radius = 16
        self.laser_cooldown = random.uniform(1.5, 3.0)
        self.dash_charge = 0.0
        self.face_rotation = random.uniform(0, math.tau)

    def update(self, dt, player):
        if self.enemy_type == "chaser":
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy) + 1e-5
            self.x += (dx / dist) * self.base_speed * dt
            self.y += (dy / dist) * self.base_speed * dt

        elif self.enemy_type == "orbiter":
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy) + 1e-5
            self.x += (dx / dist) * self.base_speed * 0.3 * dt
            self.y += (dy / dist) * self.base_speed * 0.3 * dt
            normx = dx / dist
            normy = dy / dist
            tangent_x = -normy
            tangent_y = normx
            self.x += tangent_x * self.base_speed * 0.8 * dt
            self.y += tangent_y * self.base_speed * 0.8 * dt

        elif self.enemy_type == "sniper":
            dx = player.x - self.x
            self.x += math.copysign(self.base_speed * 0.4 * dt, dx)
            self.laser_cooldown -= dt
            if self.laser_cooldown <= 0:
                self.laser_cooldown = random.uniform(2.5, 4.0)

        elif self.enemy_type == "dasher":
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy) + 1e-5
            self.x += (dx / dist) * self.base_speed * 0.35 * dt
            self.y += (dy / dist) * self.base_speed * 0.35 * dt
            self.dash_charge += dt
            if self.dash_charge > 2.0 and dist < 200:
                self.x += (dx / dist) * self.base_speed * 2.4 * dt
                self.y += (dy / dist) * self.base_speed * 2.4 * dt
                self.dash_charge = 0.0

        self.x = max(-80, min(WIDTH + 80, self.x))
        self.y = max(-80, min(HEIGHT + 80, self.y))

    def draw(self, surface):
        if self.enemy_type == "chaser":
            base_color = NEON_RED
        elif self.enemy_type == "orbiter":
            base_color = NEON_PURPLE
        elif self.enemy_type == "sniper":
            base_color = NEON_BLUE
        else:
            base_color = NEON_ORANGE

        pos = (int(self.x), int(self.y))
        pygame.draw.circle(surface, base_color, pos, self.radius)
        pygame.draw.circle(surface, (30, 10, 20), pos, self.radius, 2)

        eye_offset_y = -4
        pygame.draw.circle(surface, NEON_WHITE, (pos[0] - 5, pos[1] + eye_offset_y), 3)
        pygame.draw.circle(surface, NEON_WHITE, (pos[0] + 5, pos[1] + eye_offset_y), 3)
        pygame.draw.circle(surface, (20, 20, 40), (pos[0] - 5, pos[1] + eye_offset_y), 1)
        pygame.draw.circle(surface, (20, 20, 40), (pos[0] + 5, pos[1] + eye_offset_y), 1)

        pygame.draw.arc(
            surface,
            (20, 0, 0),
            (pos[0] - 8, pos[1] + 2, 16, 10),
            math.pi * 0.1,
            math.pi * 0.9,
            2,
        )

        sword_len = 28
        sword_angle = -math.pi / 4
        sx1 = pos[0] + math.cos(sword_angle) * 6
        sy1 = pos[1] + math.sin(sword_angle) * 6
        sx2 = pos[0] + math.cos(sword_angle) * (6 + sword_len)
        sy2 = pos[1] + math.sin(sword_angle) * (6 + sword_len)
        pygame.draw.line(surface, NEON_BLUE_SOFT, (sx1, sy1), (sx2, sy2), 3)
        pygame.draw.circle(surface, NEON_WHITE, (int(sx2), int(sy2)), 3)


class Orb:
    def __init__(self, x, y, color_key):
        self.x = x
        self.y = y
        self.color_key = color_key
        self.radius = 9
        if color_key == "yellow":
            self.color = NEON_YELLOW
        elif color_key == "blue":
            self.color = NEON_BLUE_SOFT
        elif color_key == "green":
            self.color = NEON_GREEN
        else:
            self.color = NEON_PINK_SOFT

        self.pulse = random.uniform(0, math.tau)

    def update(self, dt):
        self.pulse += dt * 4

    def draw(self, surface):
        r = self.radius + math.sin(self.pulse) * 1.5
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(r))
        pygame.draw.circle(surface, NEON_WHITE, (int(self.x), int(self.y)), int(r), 1)


# -------------------------
# High score storage
# -------------------------
HIGHSCORE_FILE = "highscores.txt"
MAX_SCORES = 5


def load_highscores():
    scores = []
    if os.path.exists(HIGHSCORE_FILE):
        with open(HIGHSCORE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    scores.append(int(line))
    scores.sort(reverse=True)
    return scores[:MAX_SCORES]


def save_highscore(score):
    scores = load_highscores()
    scores.append(score)
    scores.sort(reverse=True)
    scores = scores[:MAX_SCORES]
    with open(HIGHSCORE_FILE, "w") as f:
        for s in scores:
            f.write(str(s) + "\n")


# -------------------------
# Helper functions
# -------------------------
def get_level_and_zone(score):
    if score < LEVEL_THRESHOLDS[1]:
        return 1, 0
    elif score < LEVEL_THRESHOLDS[2]:
        return 2, 1
    elif score < LEVEL_THRESHOLDS[3]:
        return 3, 2
    else:
        return 4, 3


def get_zone_background(zone_index):
    if zone_index == 0:
        return NEON_BG_CALM
    elif zone_index == 1:
        return NEON_BG_HAZARD
    elif zone_index == 2:
        return NEON_BG_CHAOS
    else:
        return NEON_BG_OVERDRIVE


def circle_collision(ax, ay, ar, bx, by, br):
    dx = ax - bx
    dy = ay - by
    dist_sq = dx * dx + dy * dy
    r = ar + br
    return dist_sq <= r * r


# -------------------------
# Game loop
# -------------------------
def main():
    stars = [Star() for _ in range(50)]
    sparkles = [Sparkle() for _ in range(STAR_COUNT)]

    running = True
    state = "menu"
    difficulty_mode = "Easy"
    score = 0
    combo = 1
    combo_timer = 0.0
    frenzy_timer = 0.0
    frenzy_active = False

    enemy_spawn_timer = 0.0
    orb_spawn_timer = 0.0

    player = Player()
    enemies = []
    orbs = []
    particles = []
    texts = []

    paused = False

    highscores = load_highscores()

    help_page = False

    while running:
        dt = clock.tick(FPS) / 1000.0
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == "menu":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        help_page = False
                        state = "playing"
                        score = 0
                        combo = 1
                        combo_timer = 0.0
                        frenzy_timer = 0.0
                        frenzy_active = False
                        player.reset()
                        enemies.clear()
                        orbs.clear()
                        particles.clear()
                        texts.clear()
                        enemy_spawn_timer = 0.5
                        orb_spawn_timer = 0.4
                    elif event.key == pygame.K_h:
                        help_page = not help_page
                    elif event.key == pygame.K_1:
                        difficulty_mode = "Easy"
                    elif event.key == pygame.K_2:
                        difficulty_mode = "Normal"
                    elif event.key == pygame.K_3:
                        difficulty_mode = "Hard"

            elif state == "playing":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        player.try_dash()
                    elif event.key == pygame.K_p:
                        paused = not paused
                    elif event.key == pygame.K_ESCAPE:
                        state = "menu"
                        paused = False

            elif state == "game_over":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        state = "menu"

        level, zone_index = get_level_and_zone(score)
        bg_color = get_zone_background(zone_index)

        # Update starfield / sparkles (always)
        for s in stars:
            s.update(dt, zone_index)
        for sp in sparkles:
            sp.update(dt)

        # -------------------------
        # MENU STATE
        # -------------------------
        if state == "menu":
            screen.fill(bg_color)

            for s in stars:
                s.draw(screen, (50 + zone_index * 20, 70, 120 + zone_index * 20))
            for sp in sparkles:
                sp.draw(screen, (255, 120 + zone_index * 40, 220))

            sig1 = SMALL_FONT.render("Created by: Akber Elci", True, NEON_BLUE_SOFT)
            sig2 = SMALL_FONT.render("Neon Arena Project – 2025", True, NEON_BLUE_SOFT)
            screen.blit(sig1, (20, 20))
            screen.blit(sig2, (20, 42))

            title_surf = TITLE_FONT.render("NEON ARENA", True, NEON_PINK)
            title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 5))
            screen.blit(title_surf, title_rect)

            line1 = "Move with WASD / Arrow keys and use SPACE to dash."
            line2 = "Collect neon orbs, avoid devil enemies and lasers."
            text1 = MEDIUM_FONT.render(line1, True, NEON_BLUE_SOFT)
            text2 = MEDIUM_FONT.render(line2, True, NEON_BLUE_SOFT)
            screen.blit(text1, text1.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 20)))
            screen.blit(text2, text2.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 50)))

            start_text = BIG_FONT.render("Press ENTER to start", True, NEON_BLUE_SOFT)
            help_text = MEDIUM_FONT.render("Press H for help", True, NEON_BLUE_SOFT)
            screen.blit(start_text, start_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            screen.blit(help_text, help_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))

            diff_line = f"Difficulty:  [1] Easy   [2] Normal   [3] Hard    (Current: {difficulty_mode})"
            diff_surf = MEDIUM_FONT.render(diff_line, True, NEON_PINK_SOFT)
            screen.blit(diff_surf, diff_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 90)))

            panel_rect = pygame.Rect(24, HEIGHT - 190, 260, 150)
            pygame.draw.rect(screen, HUD_BG, panel_rect, border_radius=18)
            pygame.draw.rect(screen, HUD_BORDER, panel_rect, 2, border_radius=18)

            header = SMALL_FONT.render("LEVEL & ZONE", True, NEON_BLUE_SOFT)
            screen.blit(header, (panel_rect.x + 16, panel_rect.y + 12))

            lv_lines = [
                "Lv 1: 0–99    -> Calm",
                "Lv 2: 100–249 -> Hazard",
                "Lv 3: 250–449 -> Chaos",
                "Lv 4+: 450+   -> Overdrive",
            ]
            for i, ln in enumerate(lv_lines):
                surf = SMALL_FONT.render(ln, True, NEON_WHITE)
                screen.blit(surf, (panel_rect.x + 16, panel_rect.y + 36 + i * 22))

            orb_panel = pygame.Rect(WIDTH - 260 - 24, HEIGHT - 190, 260, 150)
            pygame.draw.rect(screen, HUD_BG, orb_panel, border_radius=18)
            pygame.draw.rect(screen, HUD_BORDER, orb_panel, 2, border_radius=18)

            header2 = SMALL_FONT.render("ORB VALUES", True, NEON_BLUE_SOFT)
            screen.blit(header2, (orb_panel.x + 16, orb_panel.y + 12))

            orb_rows = [
                ("yellow", ORB_VALUES["yellow"]),
                ("blue", ORB_VALUES["blue"]),
                ("green", ORB_VALUES["green"]),
                ("pink", ORB_VALUES["pink"]),
            ]
            y_off = orb_panel.y + 40
            for color_key, val in orb_rows:
                if color_key == "yellow":
                    c = NEON_YELLOW
                elif color_key == "blue":
                    c = NEON_BLUE_SOFT
                elif color_key == "green":
                    c = NEON_GREEN
                else:
                    c = NEON_PINK_SOFT
                pygame.draw.circle(screen, c, (orb_panel.x + 24, y_off + 4), 6)
                surf = SMALL_FONT.render(f"{val} points", True, NEON_WHITE)
                screen.blit(surf, (orb_panel.x + 40, y_off - 6))
                y_off += 26

            hs_title = SMALL_FONT.render("Top Scores:", True, NEON_YELLOW)
            screen.blit(hs_title, (WIDTH // 2 - 40, HEIGHT - 170))
            for i, sc in enumerate(highscores[:5]):
                txt = SMALL_FONT.render(f"{i+1}. {sc}", True, NEON_WHITE)
                screen.blit(txt, (WIDTH // 2 - 40, HEIGHT - 150 + i * 22))

            if help_page:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((5, 5, 25, 210))
                screen.blit(overlay, (0, 0))
                help_lines = [
                    "HELP",
                    "",
                    "- Move to collect orbs and survive as long as possible.",
                    "- Each zone increases enemy speed and spawn rate.",
                    "- Combo increases if you keep collecting orbs quickly.",
                    "- Frenzy mode triggers at high combo and boosts scoring.",
                    "- Level up grants an extra heart and shield.",
                    "- Different enemy types have unique movement patterns.",
                ]
                for i, line in enumerate(help_lines):
                    font = BIG_FONT if i == 0 else SMALL_FONT
                    color = NEON_PINK if i == 0 else NEON_WHITE
                    surf = font.render(line, True, color)
                    screen.blit(surf, surf.get_rect(center=(WIDTH // 2, 140 + i * 32)))

            pygame.display.flip()
            continue

        # -------------------------
        # PLAYING STATE
        # -------------------------
        if state == "playing":
            if paused:
                screen.fill(bg_color)
                for s in stars:
                    s.draw(screen, (50 + zone_index * 20, 70, 120 + zone_index * 20))
                for sp in sparkles:
                    sp.draw(screen, (255, 120 + zone_index * 40, 220))

                pause_text = BIG_FONT.render("PAUSED", True, NEON_PINK)
                info_text = SMALL_FONT.render("Press P to resume", True, NEON_BLUE_SOFT)
                screen.blit(pause_text, pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
                screen.blit(info_text, info_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
                pygame.display.flip()
                continue

            diff_cfg = DIFFICULTY_PRESETS.get(difficulty_mode, DIFFICULTY_PRESETS["Normal"])

            screen.fill(bg_color)
            for s in stars:
                s.draw(screen, (50 + zone_index * 20, 70, 120 + zone_index * 20))
            for sp in sparkles:
                sp.draw(screen, (255, 120 + zone_index * 40, 220))

            # Frenzy overlay + banner
            if frenzy_active:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((255, 70, 160, 90))
                screen.blit(overlay, (0, 0))

                frenzy_text = BIG_FONT.render("FRENZY MODE – SCORE x2!", True, NEON_PINK)
                screen.blit(frenzy_text, frenzy_text.get_rect(center=(WIDTH // 2, 60)))

            player.update(dt, keys)

            # Enemy spawn
            enemy_spawn_timer -= dt
            base_interval = max(
                ENEMY_SPAWN_INTERVAL_MIN,
                ENEMY_SPAWN_INTERVAL_START - level * 0.1,
            )
            interval = base_interval / diff_cfg["enemy_spawn_mul"]

            if enemy_spawn_timer <= 0 and len(enemies) < diff_cfg["max_enemies"]:
                side = random.choice(["left", "right", "top", "bottom"])
                if side == "left":
                    ex, ey = -40, random.uniform(0, HEIGHT)
                elif side == "right":
                    ex, ey = WIDTH + 40, random.uniform(0, HEIGHT)
                elif side == "top":
                    ex, ey = random.uniform(0, WIDTH), -40
                else:
                    ex, ey = random.uniform(0, WIDTH), HEIGHT + 40

                enemy_type = random.choices(
                    ["chaser", "orbiter", "sniper", "dasher"],
                    weights=[0.45, 0.25, 0.15, 0.15],
                )[0]
                e = Enemy(enemy_type, ex, ey, speed_mul=diff_cfg["enemy_speed_mul"] * (1 + level * 0.08))
                enemies.append(e)
                enemy_spawn_timer = interval

            # Orb spawn
            orb_spawn_timer -= dt
            orb_interval = 0.6
            if orb_spawn_timer <= 0:
                ox = random.uniform(50, WIDTH - 50)
                oy = random.uniform(80, HEIGHT - 50)
                color_key = random.choices(
                    ["yellow", "blue", "green", "pink"],
                    weights=[0.5, 0.3, 0.15, 0.05],
                )[0]
                orbs.append(Orb(ox, oy, color_key))
                orb_spawn_timer = orb_interval

            # Update enemies (slower during Frenzy)
            enemy_dt = dt * (0.75 if frenzy_active else 1.0)
            for e in enemies:
                e.update(enemy_dt, player)

            # Update orbs
            for orb in orbs:
                orb.update(dt)

            # Particles / texts
            for p in particles:
                p.update(dt)
            particles = [p for p in particles if p.alive()]
            for t in texts:
                t.update(dt)
            texts = [t for t in texts if t.alive()]

            # Combo / Frenzy timers
            if combo > 1:
                combo_timer -= dt
                if combo_timer <= 0:
                    combo = 1
                    frenzy_active = False
                    frenzy_timer = 0.0

            if frenzy_active:
                frenzy_timer -= dt
                if frenzy_timer <= 0:
                    frenzy_active = False

            # Player vs orbs
            collected_indices = []
            for idx, orb in enumerate(orbs):
                if circle_collision(player.x, player.y, player.radius + 2, orb.x, orb.y, orb.radius):
                    collected_indices.append(idx)
                    base_value = ORB_VALUES.get(orb.color_key, 10)
                    level_bonus = (level - 1) * 3
                    gain = base_value + level_bonus
                    if frenzy_active:
                        gain *= 2
                    score += gain

                    combo += 1
                    combo_timer = COMBO_TIMEOUT

                    for _ in range(7):
                        particles.append(Particle(orb.x, orb.y, orb.color, 5, 0.5))
                    texts.append(
                        FloatingText(
                            f"+{gain}",
                            orb.x,
                            orb.y - 10,
                            NEON_YELLOW,
                            SMALL_FONT,
                        )
                    )

                    play_sfx("orb")

                    if combo >= FRENZY_COMBO_THRESHOLD and not frenzy_active:
                        frenzy_active = True
                        frenzy_timer = FRENZY_DURATION
                        texts.append(
                            FloatingText(
                                "FRENZY!",
                                WIDTH / 2,
                                80,
                                NEON_PINK,
                                BIG_FONT,
                                1.2,
                            )
                        )
                        play_sfx("frenzy")

            for index in sorted(collected_indices, reverse=True):
                orbs.pop(index)

            # Level-up reward
            new_level, new_zone_index = get_level_and_zone(score)
            if new_level > level:
                if player.hp < PLAYER_MAX_HP + 2:
                    player.hp += 1
                if player.shield < PLAYER_MAX_SHIELD:
                    player.shield += 1
                texts.append(
                    FloatingText(
                        f"LEVEL {new_level} - {ZONE_NAMES[new_zone_index]}",
                        WIDTH / 2,
                        HEIGHT / 2,
                        NEON_PINK,
                        BIG_FONT,
                        1.8,
                    )
                )
                play_sfx("levelup")
                level, zone_index = new_level, new_zone_index
                bg_color = get_zone_background(zone_index)

            # Player vs enemies
            if player.invuln_timer <= 0:
                hit_any = False
                for e in enemies:
                    if circle_collision(player.x, player.y, player.radius, e.x, e.y, e.radius):
                        hit_any = True
                        break
                if hit_any:
                    if player.shield > 0:
                        player.shield -= 1
                        texts.append(
                            FloatingText(
                                "Shield hit!",
                                player.x,
                                player.y - 26,
                                NEON_BLUE_SOFT,
                                SMALL_FONT,
                                0.9,
                            )
                        )
                    else:
                        player.hp -= 1
                        texts.append(
                            FloatingText(
                                "-1 HP",
                                player.x,
                                player.y - 26,
                                NEON_RED,
                                SMALL_FONT,
                                0.9,
                            )
                        )
                    for _ in range(20):
                        particles.append(Particle(player.x, player.y, NEON_RED, 6, 0.65))
                    player.invuln_timer = 1.0
                    play_sfx("hit")

            if player.hp <= 0:
                play_sfx("death")
                save_highscore(score)
                highscores = load_highscores()
                state = "game_over"

            # Draw orbs
            for orb in orbs:
                orb.draw(screen)

            # Draw enemies
            for e in enemies:
                e.draw(screen)

            # Draw player
            player.draw(screen)

            for p in particles:
                p.draw(screen)
            for t in texts:
                t.draw(screen)

            # HUD
            hud_rect = pygame.Rect(20, 20, 220, 120)
            pygame.draw.rect(screen, HUD_BG, hud_rect, border_radius=16)
            pygame.draw.rect(screen, HUD_BORDER, hud_rect, 2, border_radius=16)

            score_surf = SMALL_FONT.render(f"Score: {score}", True, NEON_WHITE)
            lvl_surf = SMALL_FONT.render(f"Level: {level}  ({ZONE_NAMES[zone_index].upper()})", True, NEON_WHITE)
            screen.blit(score_surf, (hud_rect.x + 14, hud_rect.y + 10))
            screen.blit(lvl_surf, (hud_rect.x + 14, hud_rect.y + 34))

            heart_x = hud_rect.x + 14
            heart_y = hud_rect.y + 62
            for i in range(player.hp):
                pygame.draw.circle(screen, NEON_RED, (heart_x + i * 18, heart_y), 5)

            shield_y = heart_y + 20
            for i in range(player.shield):
                pygame.draw.circle(screen, NEON_BLUE_SOFT, (heart_x + i * 18, shield_y), 5, 1)

            if combo > 1:
                combo_surf = SMALL_FONT.render(f"Combo x{combo}", True, NEON_YELLOW)
                screen.blit(combo_surf, (hud_rect.x + 120, hud_rect.y + 62))

            if frenzy_active:
                bar_w = 120
                bar_h = 10
                bar_x = hud_rect.x + 14
                bar_y = hud_rect.y + 96
                pygame.draw.rect(screen, (30, 10, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
                frac = max(0.0, min(1.0, frenzy_timer / FRENZY_DURATION))
                pygame.draw.rect(
                    screen,
                    NEON_PINK,
                    (bar_x, bar_y, int(bar_w * frac), bar_h),
                    border_radius=6,
                )
                label = SMALL_FONT.render("Frenzy", True, NEON_PINK_SOFT)
                screen.blit(label, (bar_x + bar_w + 10, bar_y - 4))

            dash_label = SMALL_FONT.render("Dash", True, NEON_WHITE)
            dash_bar_w = 140
            dash_bar_h = 14
            dash_x = WIDTH - dash_bar_w - 40
            dash_y = 24
            screen.blit(dash_label, (dash_x, dash_y - 18))

            ready_frac = 1.0 - (player.dash_cooldown / DASH_COOLDOWN) if DASH_COOLDOWN > 0 else 1
            ready_frac = max(0.0, min(1.0, ready_frac))
            pygame.draw.rect(screen, HUD_BG, (dash_x, dash_y, dash_bar_w, dash_bar_h), border_radius=8)
            pygame.draw.rect(
                screen,
                NEON_BLUE_SOFT,
                (dash_x, dash_y, int(dash_bar_w * ready_frac), dash_bar_h),
                border_radius=8,
            )
            pygame.draw.rect(screen, HUD_BORDER, (dash_x, dash_y, dash_bar_w, dash_bar_h), 2, border_radius=8)

            sig = SMALL_FONT.render("Created by: Akber Elci", True, NEON_BLUE_SOFT)
            screen.blit(sig, (20, HEIGHT - 26))

            pygame.display.flip()
            continue

        # -------------------------
        # GAME OVER
        # -------------------------
        if state == "game_over":
            screen.fill(bg_color)
            for s in stars:
                s.draw(screen, (50 + zone_index * 20, 70, 120 + zone_index * 20))
            for sp in sparkles:
                sp.draw(screen, (255, 120 + zone_index * 40, 220))

            title = TITLE_FONT.render("GAME OVER", True, NEON_PINK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3)))

            score_text = BIG_FONT.render(f"Your Score: {score}", True, NEON_BLUE_SOFT)
            screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))

            hs = load_highscores()
            best = hs[0] if hs else 0
            hs_text = SMALL_FONT.render(f"High Score: {best}", True, NEON_YELLOW)
            screen.blit(hs_text, hs_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 28)))

            info_text = SMALL_FONT.render("Press ENTER to return to menu.", True, NEON_BLUE_SOFT)
            screen.blit(info_text, info_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))

            sig = SMALL_FONT.render("Created by: Akber Elci – Neon Arena Project 2025", True, NEON_BLUE_SOFT)
            screen.blit(sig, sig.get_rect(center=(WIDTH // 2, HEIGHT - 40)))

            pygame.display.flip()
            continue

    pygame.quit()


if __name__ == "__main__":
    main()
