import pygame
from collections import deque
import random
import time
import math
import os

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)

WIDTH, HEIGHT = 800, 640
TILE = 40
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pac-Man AI BFS Ghosts")

# ----------------- Maze -----------------
maze = [
    "####################",
    "#........#.........#",
    "#.######.#.######..#",
    "#.#......#......#..#",
    "#.#.####.####.#.#..#",
    "#.#...........#.#..#",
    "#.##.#########..#..#",
    "#.................#",
    "#.####.######.#####",
    "#........#.........#",
    "#.######.#.######..#",
    "#........#.........#",
    "####################"
]

COLS = max(len(row) for row in maze)
maze = [row.ljust(COLS, "#") for row in maze]
ROWS = len(maze)

SPEED = 2
FPS = 60

# ----------------- Helper -----------------
def valid_move(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS and maze[r][c] != "#"

def bfs_next_step(start, goal):
    queue = deque([start])
    visited = {tuple(start): None}
    while queue:
        r, c = queue.popleft()
        if [r, c] == goal:
            break
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r + dr, c + dc
            if valid_move(nr, nc) and (nr, nc) not in visited:
                visited[(nr, nc)] = (r, c)
                queue.append([nr, nc])
    cur = tuple(goal)
    if cur not in visited:
        return start
    while visited[cur] != tuple(start):
        cur = visited[cur]
    return list(cur)

# ----------------- Entities -----------------
class Entity:
    def __init__(self, r, c, color):
        self.row = r
        self.col = c
        self.x = c * TILE + TILE // 2
        self.y = r * TILE + TILE // 2
        self.color = color
        self.target_tile = [r, c]
        self.last_tile = [r, c]

    def draw(self, bob=0):
        pygame.draw.circle(WIN, self.color, (int(self.x), int(self.y + bob)), 15)

    def update_position(self):
        tx = self.target_tile[1] * TILE + TILE // 2
        ty = self.target_tile[0] * TILE + TILE // 2
        dx = tx - self.x
        dy = ty - self.y

        if abs(dx) < SPEED:
            self.x = tx
        else:
            self.x += SPEED if dx > 0 else -SPEED

        if abs(dy) < SPEED:
            self.y = ty
        else:
            self.y += SPEED if dy > 0 else -SPEED

        self.row = int(self.y // TILE)
        self.col = int(self.x // TILE)

    def set_target(self, r, c):
        if valid_move(r, c) and [r, c] != self.last_tile:
            self.last_tile = self.target_tile
            self.target_tile = [r, c]

class PacMan(Entity):
    def __init__(self, r, c, color=(255,255,0)):
        super().__init__(r, c, color)
        self.mouth_open = True
        self.mouth_timer = 0

    def draw(self, bob=0):
        self.mouth_timer += 1
        if self.mouth_timer > 10:
            self.mouth_open = not self.mouth_open
            self.mouth_timer = 0

        dx = self.target_tile[1] - self.col
        dy = self.target_tile[0] - self.row
        angle = 0
        if dx == -1: angle = 180
        elif dy == -1: angle = 90
        elif dy == 1: angle = -90

        center = (int(self.x), int(self.y + bob))
        radius = 14
        if self.mouth_open:
            mouth_deg = 40
            start_angle = math.radians(-mouth_deg/2 + angle)
            end_angle   = math.radians(mouth_deg/2 + angle)
            pygame.draw.circle(WIN, self.color, center, radius)
            p1 = center
            p2 = (center[0] + int(radius*math.cos(start_angle)), center[1] + int(radius*math.sin(start_angle)))
            p3 = (center[0] + int(radius*math.cos(end_angle)), center[1] + int(radius*math.sin(end_angle)))
            pygame.draw.polygon(WIN, (0,0,0), [p1,p2,p3])
        else:
            pygame.draw.circle(WIN, self.color, center, radius)

class Ghost(Entity):
    def __init__(self, r, c, color):
        super().__init__(r, c, color)
        self.bob_phase = random.random()*2*math.pi

    def draw(self, bob=0):
        bob_y = int(math.sin(self.bob_phase + pygame.time.get_ticks()/300.0) * 4)
        center = (int(self.x), int(self.y + bob_y))
        pygame.draw.circle(WIN, self.color, (center[0], center[1]-4), 14)
        pygame.draw.rect(WIN, self.color, (center[0]-14, center[1]-4, 28, 14))
        eye_x = 6
        pygame.draw.circle(WIN, (255,255,255), (center[0]-eye_x, center[1]-6), 4)
        pygame.draw.circle(WIN, (255,255,255), (center[0]+eye_x, center[1]-6), 4)
        pygame.draw.circle(WIN, (0,0,0), (center[0]-eye_x, center[1]-6), 2)
        pygame.draw.circle(WIN, (0,0,0), (center[0]+eye_x, center[1]-6), 2)

# ----------------- Initial State -----------------
def make_initial_state():
    pac = PacMan(1, 1)
    gs = {
        "red": Ghost(11, 18, (255, 0, 0)),
        "pink": Ghost(1, 18, (255, 100, 200)),
        "cyan": Ghost(6, 10, (0, 255, 255)),
    }
    pellets_set = {(r, c) for r in range(ROWS) for c in range(COLS) if maze[r][c] == "."}
    return pac, gs, pellets_set

# ----------------- Globals -----------------
pacman, ghosts, pellets = make_initial_state()
score = 0
high_score = 0
lives = 3
start_time = time.time()
game_over = False
you_win = False
pacman_direction = [0, 0]
game_state = "menu"

# ----------------- Sounds -----------------
bg_music_path = "bg_music.mp3"
death_sound_path = "death.wav"
bg_music_loaded = False
death_sound = None

try:
    if os.path.exists(bg_music_path):
        pygame.mixer.music.load(bg_music_path)
        pygame.mixer.music.set_volume(0.4)
        bg_music_loaded = True
    if os.path.exists(death_sound_path):
        death_sound = pygame.mixer.Sound(death_sound_path)
        death_sound.set_volume(0.6)
except Exception as e:
    print("Sound load failed:", e)
    bg_music_loaded = False
    death_sound = None

# ----------------- Drawing -----------------
def draw_grid():
    for r in range(ROWS):
        for c in range(COLS):
            if maze[r][c] == "#":
                pygame.draw.rect(WIN, (0, 0, 200), (c*TILE, r*TILE, TILE, TILE))

def draw_pellets():
    for (r, c) in pellets:
        pygame.draw.circle(WIN, (255, 255, 255), (c*TILE + TILE//2, r*TILE + TILE//2), 4)

def draw_top_ui():
    font = pygame.font.SysFont(None, 28)
    elapsed_time = int(time.time() - start_time)
    text = font.render(f"Score: {score}  High Score: {high_score}  Lives: {lives}  Time: {elapsed_time}s  Pellets: {len(pellets)}", True, (255,255,255))
    WIN.blit(text, (10, 8))
    for i in range(lives):
        pygame.draw.circle(WIN, (255,0,0), (WIDTH - 30 - i*30, 20), 10)

def draw():
    WIN.fill((0,0,0))
    draw_grid()
    draw_pellets()
    for g in ghosts.values():
        g.draw()
    pacman.draw()
    draw_top_ui()
    if game_state == "game_over":
        draw_popup("GAME OVER", f"Score: {score}", "Press R to Restart")
    elif game_state == "win":
        draw_popup("YOU WIN!", f"Score: {score}", "Press R to Play Again")
    pygame.display.flip()

def draw_centered_button(text, rect, hover=False):
    color = (180,180,180) if hover else (200,200,200)
    pygame.draw.rect(WIN, (40,40,40), rect, border_radius=8)
    pygame.draw.rect(WIN, color, rect, 3, border_radius=8)
    f = pygame.font.SysFont(None, 40)
    txt = f.render(text, True, (255,255,255))
    WIN.blit(txt, (rect[0] + rect[2]//2 - txt.get_width()//2, rect[1] + rect[3]//2 - txt.get_height()//2))

def draw_popup(title, line, bottom):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0,0,0))
    WIN.blit(overlay, (0,0))
    box_w, box_h = 420, 260
    box_x = WIDTH//2 - box_w//2
    box_y = HEIGHT//2 - box_h//2
    pygame.draw.rect(WIN, (30,30,30), (box_x, box_y, box_w, box_h), border_radius=12)
    pygame.draw.rect(WIN, (200,200,200), (box_x, box_y, box_w, box_h), 3, border_radius=12)
    big = pygame.font.SysFont(None, 68)
    medium = pygame.font.SysFont(None, 36)
    t = big.render(title, True, (255,50,50) if title=="GAME OVER" else (50,255,50))
    WIN.blit(t, (box_x + box_w//2 - t.get_width()//2, box_y + 30))
    m = medium.render(line, True, (255,255,255))
    WIN.blit(m, (box_x + box_w//2 - m.get_width()//2, box_y + 120))
    b = pygame.font.SysFont(None, 30).render(bottom, True, (200,200,200))
    WIN.blit(b, (box_x + box_w//2 - b.get_width()//2, box_y + 180))

# ----------------- Restart -----------------
def restart_game(full_reset=True):
    global pacman, ghosts, pellets, score, start_time, game_over, you_win, pacman_direction, game_state, lives, high_score
    if full_reset:
        if score > high_score:
            high_score = score
        lives = 3
        score = 0
    pacman, ghosts, pellets = make_initial_state()
    pacman_direction = [0,0]
    game_over = False
    you_win = False
    game_state = "playing"
    start_time = time.time()
    pygame.event.clear()
    pygame.time.wait(80)
    if bg_music_loaded:
        try:
            pygame.mixer.music.play(-1)
        except:
            pass

# ----------------- Pause on Life Lost -----------------
# ----------------- Pause on Life Lost -----------------
def life_lost_pause():
    global pacman, pacman_direction
    paused = True
    title_font = pygame.font.SysFont(None, 64)
    msg_font = pygame.font.SysFont(None, 32)
    small_font = pygame.font.SysFont(None, 24)

    while paused:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:  # Continue on Enter
                    paused = False

        WIN.fill((0,0,0))
        draw_grid()
        draw_pellets()
        for g in ghosts.values():
            g.draw()
        pacman.draw()
        draw_top_ui()

        # Draw popup box
        box_w, box_h = 480, 180
        box_x = WIDTH//2 - box_w//2
        box_y = HEIGHT//2 - box_h//2
        pygame.draw.rect(WIN, (30,30,30), (box_x, box_y, box_w, box_h), border_radius=12)
        pygame.draw.rect(WIN, (200,200,200), (box_x, box_y, box_w, box_h), 3, border_radius=12)

        # Title
        title = title_font.render("Life Lost!", True, (255,50,50))
        WIN.blit(title, (box_x + box_w//2 - title.get_width()//2, box_y + 20))

        # Remaining lives
        lives_text = msg_font.render(f"Lives Remaining: {lives}", True, (255,200,0))
        WIN.blit(lives_text, (box_x + box_w//2 - lives_text.get_width()//2, box_y + 90))

        # Instruction
        inst_text = small_font.render("Press Enter to continue...", True, (200,200,200))
        WIN.blit(inst_text, (box_x + box_w//2 - inst_text.get_width()//2, box_y + 140))

        pygame.display.flip()
        pygame.time.Clock().tick(10)


# ----------------- Main Loop -----------------
def main():
    global pacman, score, game_over, you_win, pacman_direction, game_state, lives, high_score
    clock = pygame.time.Clock()
    running = True
    play_rect = (WIDTH//2 - 120, HEIGHT//2 - 40, 240, 80)

    while running:
        clock.tick(FPS)
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and game_state in ("game_over", "win"):
                    restart_game()
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
                    pygame.mixer.music.stop()
            if event.type == pygame.MOUSEBUTTONDOWN and game_state == "menu":
                if play_rect[0] <= mx <= play_rect[0]+play_rect[2] and play_rect[1] <= my <= play_rect[1]+play_rect[3]:
                    restart_game()

        # ----------------- Menu -----------------
        if game_state == "menu":
            WIN.fill((5,5,20))
            title_font = pygame.font.SysFont(None, 72)
            subtitle_font = pygame.font.SysFont(None, 28)
            t = title_font.render("Pac-Man AI ", True, (255,240,100))
            s = subtitle_font.render("Use arrow keys to move. Ghosts use BFS pathfinding.", True, (200,200,200))
            WIN.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 160))
            WIN.blit(s, (WIDTH//2 - s.get_width()//2, HEIGHT//2 - 100))
            hover = play_rect[0] <= mx <= play_rect[0]+play_rect[2] and play_rect[1] <= my <= play_rect[1]+play_rect[3]
            draw_centered_button("Play", play_rect, hover)
            pygame.display.flip()
            continue

        # ----------------- Playing -----------------
        if game_state == "playing":
            keys = pygame.key.get_pressed()
            move = [0,0]
            if keys[pygame.K_UP]: move = [-1,0]
            elif keys[pygame.K_DOWN]: move = [1,0]
            elif keys[pygame.K_LEFT]: move = [0,-1]
            elif keys[pygame.K_RIGHT]: move = [0,1]

            if move != [0,0]:
                pacman_direction = move

            nr = pacman.row + pacman_direction[0]
            nc = pacman.col + pacman_direction[1]

            if valid_move(nr,nc):
                pacman.set_target(nr,nc)

            pacman.update_position()

            # Collect pellet
            if (pacman.row, pacman.col) in pellets:
                score += 10
                pellets.remove((pacman.row, pacman.col))

            if len(pellets) == 0:
                game_state = "win"
                pygame.mixer.music.stop()

            # Ghost AI
            for g in ghosts.values():
                if random.randint(0,1) == 0:
                    next_step = bfs_next_step([g.row, g.col], [pacman.row, pacman.col])
                    g.set_target(*next_step)
                g.update_position()

                if g.row == pacman.row and g.col == pacman.col:
                    lives -= 1
                    if lives <= 0:
                        game_state = "game_over"
                        pygame.mixer.music.stop()
                        try:
                            if death_sound: death_sound.play()
                        except: pass
                    else:
                        pacman = PacMan(1,1)
                        pacman_direction = [0,0]
                        life_lost_pause()  # pause until Enter pressed

            draw()

        elif game_state in ("game_over","win"):
            draw()

    pygame.quit()

if __name__ == "__main__":
    main()
