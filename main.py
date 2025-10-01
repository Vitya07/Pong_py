import pygame
import sys
import math
import random

# ==============================
# ИНИЦИАЛИЗАЦИЯ
# ==============================
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Экран — Full HD
WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neon Pong Pro")

# Цвета
BACKGROUND = (8, 5, 20)
PADDLE_COLOR = (255, 85, 120)      # Неоново-розовый
BALL_COLOR = (100, 200, 255)       # Голубой неон
ACCENT = (255, 255, 255)
GLOW_COLOR = (100, 180, 255, 180)  # Полупрозрачный (для эффектов)

# FPS и часы
FPS = 60
clock = pygame.time.Clock()

# Шрифты
try:
    font_large = pygame.font.Font(None, 160)
    font_medium = pygame.font.Font(None, 100)
    font_small = pygame.font.Font(None, 60)
except:
    font_large = pygame.font.SysFont('Arial', 160, bold=True)
    font_medium = pygame.font.SysFont('Arial', 100, bold=True)
    font_small = pygame.font.SysFont('Arial', 60, bold=True)

# ==============================
# ЗВУКИ (генерация простых тонов, если нет файлов)
# ==============================
def make_sound(frequency, duration=0.1):
    sample_rate = 22050
    n_samples = int(round(duration * sample_rate))
    buf = numpy.zeros((n_samples, 2), dtype=numpy.int16)
    max_sample = 2 ** (16 - 1) - 1
    for s in range(n_samples):
        t = float(s) / sample_rate
        buf[s][0] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
        buf[s][1] = buf[s][0]
    sound = pygame.sndarray.make_sound(buf)
    return sound

# Попытка создать звуки (если установлен numpy)
sound_paddle = None
sound_score = None
sound_wall = None

try:
    import numpy
    sound_paddle = make_sound(400, 0.05)
    sound_wall = make_sound(300, 0.05)
    sound_score = make_sound(200, 0.3)
except ImportError:
    pass  # Без звуков, если нет numpy

# ==============================
# КЛАССЫ
# ==============================

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, 4)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 30
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.1)
        return self.life > 0

    def draw(self, surface):
        alpha = min(255, self.life * 8)
        color_with_alpha = (*self.color[:3], alpha)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color_with_alpha, (self.size, self.size), self.size)
        surface.blit(s, (self.x - self.size, self.y - self.size))

class Paddle:
    def __init__(self, x, is_left):
        self.x = x
        self.y = HEIGHT // 2 - 100
        self.width = 20
        self.height = 200
        self.speed = 10
        self.is_left = is_left
        self.trail = []

    def move(self, dy):
        self.y += dy
        self.y = max(0, min(HEIGHT - self.height, self.y))
        # Добавляем точку в трейл
        if len(self.trail) > 10:
            self.trail.pop(0)
        self.trail.append((self.x + (0 if self.is_left else self.width), self.y + self.height // 2))

    def draw(self, surface):
        # Основная ракетка
        pygame.draw.rect(surface, PADDLE_COLOR, (self.x, self.y, self.width, self.height), border_radius=12)
        # Неоновый контур
        pygame.draw.rect(surface, ACCENT, (self.x, self.y, self.width, self.height), 2, border_radius=12)

        # Трейл (след)
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)))
            size = max(2, 10 * (i / len(self.trail)))
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*PADDLE_COLOR, alpha), (size, size), size)
            surface.blit(s, (tx - size, ty - size))

class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        angle = random.uniform(math.pi / 4, 3 * math.pi / 4)
        if random.choice([True, False]):
            angle += math.pi
        speed = 10
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.radius = 25
        self.glow_size = self.radius + 20
        self.pulse = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.pulse = (self.pulse + 0.1) % (2 * math.pi)

    def draw(self, surface):
        pulse_offset = math.sin(self.pulse) * 3
        glow_radius = self.glow_size + pulse_offset

        # Свечение
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*BALL_COLOR, 60), (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surf, (self.x - glow_radius, self.y - glow_radius))

        # Основной мяч
        pygame.draw.circle(surface, BALL_COLOR, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, ACCENT, (int(self.x), int(self.y)), self.radius, 2)

# ==============================
# ИГРОВАЯ ЛОГИКА
# ==============================

# Объекты
ball = Ball()
paddle_left = Paddle(50, True)
paddle_right = Paddle(WIDTH - 70, False)
particles = []

score_left = 0
score_right = 0

# Состояния игры
STATE_PLAYING = 0
STATE_COUNTDOWN = 1
STATE_GOAL = 2
game_state = STATE_COUNTDOWN
countdown_timer = 180  # 3 секунды при 60 FPS
goal_timer = 60        # 1 секунда
winner = None

# Фон — звёзды
stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.2, 1.0)) for _ in range(200)]

# ==============================
# ОСНОВНОЙ ЦИКЛ
# ==============================
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # Обработка событий
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if game_state == STATE_PLAYING and event.key == pygame.K_SPACE:
                # Пауза можно добавить
                pass

    # Управление
    keys = pygame.key.get_pressed()
    if game_state == STATE_PLAYING:
        if keys[pygame.K_w]:
            paddle_left.move(-paddle_left.speed)
        if keys[pygame.K_s]:
            paddle_left.move(paddle_left.speed)
        if keys[pygame.K_UP]:
            paddle_right.move(-paddle_right.speed)
        if keys[pygame.K_DOWN]:
            paddle_right.move(paddle_right.speed)

    # Обновление состояния
    if game_state == STATE_COUNTDOWN:
        countdown_timer -= 1
        if countdown_timer <= 0:
            game_state = STATE_PLAYING
    elif game_state == STATE_GOAL:
        goal_timer -= 1
        if goal_timer <= 0:
            game_state = STATE_COUNTDOWN
            countdown_timer = 180
            ball.reset()
    elif game_state == STATE_PLAYING:
        ball.update()

        # Отскок от стен
        if ball.y - ball.radius <= 0 or ball.y + ball.radius >= HEIGHT:
            ball.vy = -ball.vy
            if sound_wall:
                sound_wall.play()

        # Отскок от ракеток
        # Левая
        if (ball.x - ball.radius <= paddle_left.x + paddle_left.width and
            paddle_left.y <= ball.y <= paddle_left.y + paddle_left.height and ball.vx < 0):
            ball.vx = -ball.vx * 1.05
            ball.vy += (ball.y - (paddle_left.y + paddle_left.height // 2)) / 30
            if sound_paddle:
                sound_paddle.play()
            # Частицы
            for _ in range(15):
                particles.append(Particle(ball.x, ball.y, PADDLE_COLOR))

        # Правая
        if (ball.x + ball.radius >= paddle_right.x and
            paddle_right.y <= ball.y <= paddle_right.y + paddle_right.height and ball.vx > 0):
            ball.vx = -ball.vx * 1.05
            ball.vy += (ball.y - (paddle_right.y + paddle_right.height // 2)) / 30
            if sound_paddle:
                sound_paddle.play()
            for _ in range(15):
                particles.append(Particle(ball.x, ball.y, PADDLE_COLOR))

        # Голы
        if ball.x < 0:
            score_right += 1
            game_state = STATE_GOAL
            goal_timer = 60
            winner = "RIGHT"
            if sound_score:
                sound_score.play()
        elif ball.x > WIDTH:
            score_left += 1
            game_state = STATE_GOAL
            goal_timer = 60
            winner = "LEFT"
            if sound_score:
                sound_score.play()

    # Обновление частиц
    particles = [p for p in particles if p.update()]

    # ==============================
    # ОТРИСОВКА
    # ==============================
    screen.fill(BACKGROUND)

    # Движущийся звёздный фон (параллакс)
    for i, (x, y, speed) in enumerate(stars):
        x -= speed
        if x < 0:
            x = WIDTH
            y = random.randint(0, HEIGHT)
        stars[i] = (x, y, speed)
        brightness = int(100 * speed)
        pygame.draw.circle(screen, (brightness, brightness, brightness), (int(x), int(y)), 1)

    # Ракетки
    paddle_left.draw(screen)
    paddle_right.draw(screen)

    # Мяч
    if game_state != STATE_GOAL:
        ball.draw(screen)

    # Частицы
    for p in particles:
        p.draw(screen)

    # Центральная линия
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (60, 60, 100), (WIDTH // 2, y), (WIDTH // 2, y + 20), 3)

    # Счёт
    score_text = font_large.render(f"{score_left}    {score_right}", True, ACCENT)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 50))

    # Анимации состояний
    if game_state == STATE_COUNTDOWN:
        num = str((countdown_timer // 60) + 1)
        if countdown_timer % 60 < 30:
            text = font_medium.render(num, True, BALL_COLOR)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 50))
    elif game_state == STATE_GOAL:
        text = font_medium.render("GOAL!", True, BALL_COLOR)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 50))
        if winner == "LEFT":
            win_text = font_small.render("Player 1 scores!", True, PADDLE_COLOR)
        else:
            win_text = font_small.render("Player 2 scores!", True, PADDLE_COLOR)
        screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 + 30))

    # Подсказка
    hint = font_small.render("W/S — Left | ↑/↓ — Right | ESC — Quit", True, (100, 100, 150))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 80))

    pygame.display.flip()

# Завершение
pygame.quit()
sys.exit()
