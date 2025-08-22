# main.py
import os
import sys
import random
import asyncio
import traceback
import pygame

# --------- Quality & env hints (set BEFORE pygame.init) ----------
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "2")  # smoother scaling if available
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

IS_WEB = (sys.platform == "emscripten")

# --------------------- Init pygame -------------------------------
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER_COLOR = (255, 224, 189)
BODY_COLOR = (0, 128, 255)
LEAF_COLOR = (34, 139, 34)
TREE_COLOR = (0, 100, 0)
CLOUD_COLOR = (105, 105, 105)
FACTORY_COLOR = (80, 80, 80)
FACTORY_GREEN_COLOR = (60, 179, 113)
BACKGROUND_COLOR = (135, 206, 235)
GROUND_COLOR = (85, 107, 47)

# Player properties
PLAYER_WIDTH = 60
PLAYER_HEIGHT = 80
PLAYER_SPEED = 5

# Leaf properties
LEAF_WIDTH = 20
LEAF_HEIGHT = 40
LEAF_SPEED = 7

# Tree properties
TREE_WIDTH = 40
TREE_HEIGHT = 60
GROWTH_TIME = 3000  # ms
TREE_SHOOT_INTERVAL = 3000  # ms

# Pollution cloud properties
CLOUD_WIDTH = 40
CLOUD_HEIGHT = 30
CLOUD_SPEED = 3
CLOUD_SPAWN_RATE = 30

# Factory properties
FACTORY_WIDTH = 60
FACTORY_HEIGHT = 150
FACTORY_X = SCREEN_WIDTH - FACTORY_WIDTH
FACTORY_Y = SCREEN_HEIGHT - 50 - FACTORY_HEIGHT

# Initial number of pollution clouds
INITIAL_CLOUDS = 5

# ----------------- Display (avoid SCALED on web) -----------------
display_flags = 0
# SCALED can cause blank canvas on some web combos; keep it desktop-only.
if not IS_WEB and hasattr(pygame, "SCALED"):
    display_flags |= pygame.SCALED

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), display_flags)
pygame.display.set_caption("Eco Defender")

# Timing
clock = pygame.time.Clock()

# Fonts
pygame.font.init()
# SysFont("Arial") can be missing on web; fallback to default if needed.
def _pick_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

font = _pick_font("Arial", 24)
title_font = _pick_font("Arial", 48, bold=True)
small_font = _pick_font("Arial", 20)


# ------------------------- Drawing -------------------------------
def draw_coalition(surface, x, y):
    for dx, dy in [(-20, 0), (0, 0), (20, 0)]:
        draw_player(surface, x + dx, y + dy)

def draw_player(surface, x, y):
    head_radius = 10
    head_x = x + PLAYER_WIDTH // 2 - 20
    head_y = y + head_radius
    pygame.draw.circle(surface, PLAYER_COLOR, (head_x, head_y), head_radius)
    body_rect = pygame.Rect(head_x - 5, y + 2 * head_radius, 10, 20)
    pygame.draw.rect(surface, BODY_COLOR, body_rect)
    pygame.draw.line(surface, BODY_COLOR, (head_x, y + 2 * head_radius + 5), (head_x - 10, y + 2 * head_radius + 15), 3)
    pygame.draw.line(surface, BODY_COLOR, (head_x, y + 2 * head_radius + 5), (head_x + 10, y + 2 * head_radius + 15), 3)
    pygame.draw.line(surface, BODY_COLOR, (head_x, y + 2 * head_radius + 20), (head_x - 5, y + PLAYER_HEIGHT - 10), 3)
    pygame.draw.line(surface, BODY_COLOR, (head_x, y + 2 * head_radius + 20), (head_x + 5, y + PLAYER_HEIGHT - 10), 3)

def draw_leaf(surface, x, y):
    pygame.draw.ellipse(surface, LEAF_COLOR, (x, y, LEAF_WIDTH, LEAF_HEIGHT))

def draw_tree(surface, x, y):
    trunk_width = 10
    trunk_height = TREE_HEIGHT - 30
    trunk_rect = pygame.Rect(x + (TREE_WIDTH - trunk_width) // 2, y + 30, trunk_width, trunk_height)
    pygame.draw.rect(surface, (139, 69, 19), trunk_rect)
    pygame.draw.circle(surface, TREE_COLOR, (x + TREE_WIDTH // 2, y + 30), 20)

def draw_cloud(surface, x, y):
    pygame.draw.circle(surface, CLOUD_COLOR, (x + 20, y + 10), 15)
    pygame.draw.circle(surface, CLOUD_COLOR, (x + 30, y + 20), 15)
    pygame.draw.circle(surface, CLOUD_COLOR, (x + 10, y + 20), 15)

def draw_factory(surface, pollution_level):
    color = FACTORY_GREEN_COLOR if pollution_level <= 0 else FACTORY_COLOR
    factory_rect = pygame.Rect(FACTORY_X, FACTORY_Y, FACTORY_WIDTH, FACTORY_HEIGHT)
    pygame.draw.rect(surface, color, factory_rect)
    factory_text = font.render("Factory", True, WHITE)
    text_rect = factory_text.get_rect(center=(FACTORY_X + FACTORY_WIDTH // 2, FACTORY_Y + FACTORY_HEIGHT + 20))
    surface.blit(factory_text, text_rect)


# -------------------- UX: instructions screen --------------------
async def show_instructions():
    waiting = True
    blink = 0
    frames = 0
    while waiting:
        clock.tick(60)
        blink = (blink + 1) % 60
        frames += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                waiting = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False

        # auto-start after ~4s to survive focus issues
        if frames > 240:
            waiting = False

        screen.fill(BACKGROUND_COLOR)
        title = title_font.render("Eco Defender", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 120))

        lines = [
            "How to Play:",
            "• Use the ARROW KEYS to move your group.",
            "• Press SPACE to throw leaves.",
            "• Leaves destroy pollution clouds.",
            "• Plant leaves to grow trees that auto-shoot leaves.",
            "• Make the factory carbon neutral 10 times to win!"
        ]
        y = 210
        for text in lines:
            surf = font.render(text, True, WHITE)
            screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, y))
            y += 36

        hint = small_font.render("Click inside the game if keys don't work", True, WHITE)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 110))
        if blink < 40:
            press = small_font.render("Press ENTER/SPACE or click to start", True, WHITE)
            screen.blit(press, (SCREEN_WIDTH // 2 - press.get_width() // 2, SCREEN_HEIGHT - 80))

        pygame.display.flip()
        await asyncio.sleep(0)

    return True


# ------------------ Victory screen (async wait) ------------------
async def victory(surface):
    surface.fill(BACKGROUND_COLOR)
    message_text = font.render("You've made the factory carbon neutral!", True, WHITE)
    surface.blit(message_text, (SCREEN_WIDTH // 2 - message_text.get_width() // 2, SCREEN_HEIGHT // 2))
    pygame.display.flip()
    await asyncio.sleep(5)


# --------------- Debug: draw exceptions on canvas ----------------
def draw_exception(e_text: str):
    """Draw an exception traceback on-screen so web doesn't look blank."""
    screen.fill((50, 0, 0))
    header = title_font.render("Error occurred", True, WHITE)
    screen.blit(header, (20, 20))
    y = 100
    for line in e_text.splitlines()[-15:]:  # last lines fit better
        s = small_font.render(line, True, WHITE)
        screen.blit(s, (20, y))
        y += 22
    pygame.display.flip()


# ---------------------------- Game loop --------------------------
async def game_loop():
    # Player start
    player_x = SCREEN_WIDTH // 2 - PLAYER_WIDTH // 2
    player_y = SCREEN_HEIGHT - PLAYER_HEIGHT - 50

    leaves, trees, clouds = [], [], []

    clouds_destroyed = 0
    times_factory_neutral = 0
    game_started = False

    ground_rect = pygame.Rect(0, SCREEN_HEIGHT - 50, SCREEN_WIDTH, 50)

    # initial clouds
    for _ in range(INITIAL_CLOUDS):
        cloud_x = FACTORY_X - CLOUD_WIDTH
        cloud_y = FACTORY_Y - CLOUD_HEIGHT
        clouds.append({'rect': pygame.Rect(cloud_x, cloud_y, CLOUD_WIDTH, CLOUD_HEIGHT)})

    running = True
    neutral_message_time = 0
    show_neutral_message = False

    while running:
        clock.tick(60)
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                leaf_x = player_x + PLAYER_WIDTH // 2 - LEAF_WIDTH // 2
                leaf_y = player_y
                leaves.append({'rect': pygame.Rect(leaf_x, leaf_y, LEAF_WIDTH, LEAF_HEIGHT),
                               'falling': False, 'planted': False})

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player_x - PLAYER_SPEED > 0:
            player_x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] and player_x + PLAYER_SPEED < SCREEN_WIDTH - PLAYER_WIDTH:
            player_x += PLAYER_SPEED
        if keys[pygame.K_UP] and player_y - PLAYER_SPEED > 0:
            player_y -= PLAYER_SPEED
        if keys[pygame.K_DOWN] and player_y + PLAYER_SPEED < SCREEN_HEIGHT - PLAYER_HEIGHT - 50:
            player_y += PLAYER_SPEED

        # Leaves update
        for leaf in leaves[:]:
            if not leaf['falling']:
                leaf['rect'].y -= LEAF_SPEED
                if leaf['rect'].y <= 0:
                    leaf['falling'] = True
            else:
                leaf['rect'].y += LEAF_SPEED
                if leaf['rect'].colliderect(ground_rect) and not leaf['planted']:
                    leaf['planted'] = True
                    leaf['rect'].y = ground_rect.top - LEAF_HEIGHT
                    leaf['plant_time'] = pygame.time.get_ticks()
                    leaf['last_shoot_time'] = pygame.time.get_ticks()
                for cloud in clouds[:]:
                    if leaf['rect'].colliderect(cloud['rect']):
                        clouds.remove(cloud)
                        clouds_destroyed += 1
                        if leaf in leaves:
                            leaves.remove(leaf)
                        break

        # Grow trees
        for leaf in leaves[:]:
            if leaf.get('planted'):
                current_time = pygame.time.get_ticks()
                if current_time - leaf['plant_time'] >= GROWTH_TIME:
                    tree_x = leaf['rect'].x - (TREE_WIDTH - LEAF_WIDTH) // 2
                    tree_y = ground_rect.top - TREE_HEIGHT
                    trees.append({'rect': pygame.Rect(tree_x, tree_y, TREE_WIDTH, TREE_HEIGHT),
                                  'last_shoot_time': pygame.time.get_ticks()})
                    leaves.remove(leaf)

        # Trees shoot
        current_time = pygame.time.get_ticks()
        for tree in trees:
            if current_time - tree['last_shoot_time'] >= TREE_SHOOT_INTERVAL:
                leaf_x = tree['rect'].x + TREE_WIDTH // 2 - LEAF_WIDTH // 2
                leaf_y = tree['rect'].y
                leaves.append({'rect': pygame.Rect(leaf_x, leaf_y, LEAF_WIDTH, LEAF_HEIGHT),
                               'falling': False, 'planted': False})
                tree['last_shoot_time'] = current_time

        # Clouds spawn & move
        if random.randint(1, CLOUD_SPAWN_RATE) == 1:
            cloud_x = FACTORY_X - CLOUD_WIDTH
            cloud_y = FACTORY_Y - CLOUD_HEIGHT
            clouds.append({'rect': pygame.Rect(cloud_x, cloud_y, CLOUD_WIDTH, CLOUD_HEIGHT)})
            game_started = True

        for cloud in clouds[:]:
            cloud['rect'].x -= CLOUD_SPEED
            cloud['rect'].y += random.randint(-1, 1)
            if cloud['rect'].x + CLOUD_WIDTH < 0 or cloud['rect'].y > SCREEN_HEIGHT:
                clouds.remove(cloud)
            else:
                for tree in trees:
                    if cloud['rect'].colliderect(tree['rect']):
                        if cloud in clouds:
                            clouds.remove(cloud)
                        clouds_destroyed += 1
                        break
                for leaf in leaves[:]:
                    if not leaf['falling'] and leaf['rect'].colliderect(cloud['rect']):
                        if cloud in clouds:
                            clouds.remove(cloud)
                        clouds_destroyed += 1
                        if leaf in leaves:
                            leaves.remove(leaf)
                        break

        # Status & victory
        pollution = len(clouds)
        if game_started and pollution == 0:
            times_factory_neutral += 1
            neutral_message_time = pygame.time.get_ticks()
            show_neutral_message = True
            game_started = False
        elif show_neutral_message and pygame.time.get_ticks() - neutral_message_time > 2000:
            show_neutral_message = False

        if times_factory_neutral >= 10:
            await victory(screen)
            running = False

        # Render
        screen.fill(BACKGROUND_COLOR)
        pygame.draw.rect(screen, GROUND_COLOR, (0, SCREEN_HEIGHT - 50, SCREEN_WIDTH, 50))
        draw_factory(screen, pollution)
        draw_coalition(screen, player_x, player_y)
        for leaf in leaves:
            draw_leaf(screen, leaf['rect'].x, leaf['rect'].y)
        for tree in trees:
            draw_tree(screen, tree['rect'].x, tree['rect'].y)
        for cloud in clouds:
            draw_cloud(screen, cloud['rect'].x, cloud['rect'].y)

        pollution_text = font.render(f"Pollution Level: {pollution}", True, WHITE)
        times_neutral_text = font.render(f"Factory Neutral Count: {times_factory_neutral}", True, WHITE)
        screen.blit(pollution_text, (10, 10))
        screen.blit(times_neutral_text, (10, 40))

        if pollution > 0:
            message_text = font.render("Destroy pollution to make factory carbon neutral", True, WHITE)
            screen.blit(message_text, (SCREEN_WIDTH // 2 - message_text.get_width() // 2, SCREEN_HEIGHT - 30))

        if show_neutral_message:
            neutral_text = font.render("Factory is temporarily carbon neutral!", True, WHITE)
            screen.blit(neutral_text, (SCREEN_WIDTH // 2 - neutral_text.get_width() // 2, SCREEN_HEIGHT - 30))

        pygame.display.flip()

    pygame.quit()


async def main():
    try:
        ok = await show_instructions()
        if not ok:
            return
        await game_loop()
    except Exception:
        # Draw traceback on screen so you can see it in the browser
        tb = traceback.format_exc()
        print(tb)  # also goes to browser console
        draw_exception(tb)
        # keep the error visible for a bit
        for _ in range(600):  # ~10s at 60fps
            clock.tick(60)
            await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
