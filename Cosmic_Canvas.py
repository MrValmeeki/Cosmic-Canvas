import pygame
import numpy as np
import random
import collections

# Initialize Pygame
pygame.init()

# Screen
WIDTH, HEIGHT = 1000, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Interactive Chaotic Planets")
clock = pygame.time.Clock()

# Constants
G = 0.05
DT = 0.5
THROW_MULTIPLIER = 0.2

# --- Star stage mass thresholds ---
BROWN_DWARF_MASS = 80000
STAR_MASS = 200000
GIANT_STAR_MASS = 800000
BLACK_HOLE_MASS = 2000000

# --- UI Classes (Button and InputBox) ---
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False

    def draw(self, screen):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=8)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def update_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered

class InputBox:
    def __init__(self, x, y, w, h, font, text='', property_name=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = (100, 100, 100)
        self.active_color = (150, 150, 150)
        self.text_color = (255, 255, 255)
        self.font = font
        self.text = text
        self.property_name = property_name
        self.is_active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.is_active = self.rect.collidepoint(event.pos)
        
        if event.type == pygame.KEYDOWN and self.is_active:
            if event.key == pygame.K_RETURN:
                return 'enter'
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if event.unicode in '0123456789.-':
                    self.text += event.unicode
        return None

    def draw(self, screen):
        current_color = self.active_color if self.is_active else self.color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=5)
        text_surface = self.font.render(self.text, True, self.text_color)
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))
        
        label_surface = self.font.render(self.property_name.replace('_', ' ').title(), True, (200, 200, 200))
        screen.blit(label_surface, (self.rect.x - 70, self.rect.y + 5))

# --- Camera and Pan Variables ---
camera_zoom = 1.0
camera_offset = np.array([WIDTH / 2.0, HEIGHT / 2.0])
is_panning = False
pan_start_pos = None

# --- Coordinate Conversion Functions ---
def screen_to_world(screen_pos):
    screen_center = np.array([WIDTH / 2, HEIGHT / 2])
    return (np.array(screen_pos) - screen_center) / camera_zoom + camera_offset

def world_to_screen(world_pos):
    screen_center = np.array([WIDTH / 2, HEIGHT / 2])
    return (np.array(world_pos) - camera_offset) * camera_zoom + screen_center

# Planet class
class Planet:
    def __init__(self, x, y, vx, vy, mass, color, radius=None):
        self.pos = np.array([float(x), float(y)], dtype=float)
        self.vel = np.array([float(vx), float(vy)], dtype=float)
        self.mass = float(mass)
        self.radius = int(radius if radius is not None else (self.mass/1)**(1/3.0))
        self.color = color
        self.trail = []
        self.stage = "PLANET"
        self.update_stage()

    def update_stage(self):
        if self.mass >= BLACK_HOLE_MASS and self.stage != "BLACK_HOLE":
            self.stage = "BLACK_HOLE"
            self.color = (0, 0, 0)
        elif self.mass >= GIANT_STAR_MASS and self.stage not in ["GIANT", "BLACK_HOLE"]:
            self.stage = "GIANT"
            self.color = (255, 140, 0)
        elif self.mass >= STAR_MASS and self.stage not in ["STAR", "GIANT", "BLACK_HOLE"]:
            self.stage = "STAR"
            self.color = (255, 255, 200)
        elif self.mass >= BROWN_DWARF_MASS and self.stage == "PLANET":
            self.stage = "BROWN_DWARF"
            self.color = (139, 69, 19)

    def update(self, planets):
        if dragging_planet == self:
            self.vel = np.array([0.0, 0.0], dtype=float)
            return

        total_force = np.array([0.0, 0.0], dtype=float)
        for other in planets:
            if other != self:
                r_vec = other.pos - self.pos
                r_mag = np.linalg.norm(r_vec)
                
                if self.stage == "BLACK_HOLE" and r_mag < self.radius:
                    self.mass += other.mass
                    self.radius = int((self.mass / 1) ** (1 / 3.0))
                    if other in planets: planets.remove(other)
                    continue

                if r_mag > 0:
                    force_mag = G * self.mass * other.mass / r_mag**2
                    force_vec = force_mag * r_vec / r_mag
                    total_force += force_vec

                if r_mag > 0 and r_mag < self.radius + other.radius:
                    if self.mass >= other.mass and other in planets:
                        new_mass = self.mass + other.mass
                        self.radius = int((self.radius**3 + other.radius**3)**(1/3.0))
                        new_vel = (self.vel * self.mass + other.vel * other.mass) / new_mass
                        new_pos = (self.pos * self.mass + other.pos * other.mass) / new_mass
                        self.mass = new_mass
                        self.vel = new_vel
                        self.pos = new_pos
                        self.update_stage()
                        planets.remove(other)

        self.vel += total_force / self.mass * DT
        self.pos += self.vel * DT

        self.trail.append(tuple(self.pos))
        if len(self.trail) > 500:
            self.trail.pop(0)

    def draw(self, screen, selected=False):
        screen_pos = world_to_screen(self.pos).astype(int)
        screen_radius = max(2, int(self.radius * camera_zoom))

        if self.stage == "BROWN_DWARF":
            glow_radius = int(screen_radius * 1.5)
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (139, 69, 19, 80), (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surface, (screen_pos[0] - glow_radius, screen_pos[1] - glow_radius))
        elif self.stage == "STAR":
            glow_radius = int(screen_radius * 2.5)
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (255, 255, 200, 50), (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surface, (screen_pos[0] - glow_radius, screen_pos[1] - glow_radius))
        elif self.stage == "GIANT":
            screen_radius = int(screen_radius * 1.5)
            glow_radius = int(screen_radius * 2.0)
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (255, 140, 0, 70), (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surface, (screen_pos[0] - glow_radius, screen_pos[1] - glow_radius))
        elif self.stage == "BLACK_HOLE":
            pygame.draw.circle(screen, (255, 165, 0), screen_pos, screen_radius + 5, 3)

        if len(self.trail) > 1:
            trail_color = self.color
            if self.stage == "BLACK_HOLE":
                trail_color = (138, 43, 226)
            screen_trail = [tuple(world_to_screen(p)) for p in self.trail]
            pygame.draw.lines(screen, trail_color, False, screen_trail, 1)
        
        pygame.draw.circle(screen, self.color, screen_pos, screen_radius)
        
        if selected:
            pygame.draw.circle(screen, (255,255,255), screen_pos, screen_radius + 4, 2)

def circular_velocity(mass_central, distance):
    if distance <= 0: return 0
    return np.sqrt(G * mass_central / distance)

planets = []
selected_planet = None
dragging_planet = None
drag_positions = collections.deque(maxlen=10)
font = pygame.font.SysFont('Arial', 24)
# UPDATED FONT DEFINITION
button_font = pygame.font.SysFont('segoeuisymbol, dejavusans, arial', 22, bold=True)
is_paused = False
menu_open = False
current_scenario = ""

# --- Scenario Loading Function ---
def load_scenario(name):
    global planets, selected_planet, camera_zoom, camera_offset, dragging_planet, current_scenario
    planets.clear()
    selected_planet = None
    dragging_planet = None
    camera_zoom = 1.0
    camera_offset = np.array([WIDTH / 2.0, HEIGHT / 2.0])
    center_pos = [WIDTH / 2.0, HEIGHT / 2.0]
    current_scenario = name

    if name == "Playground":
        return

    if name == "Solar System":
        camera_zoom = 0.8
        sun = Planet(center_pos[0], center_pos[1], 0, 0, 500000, (255, 255, 0))
        planets.append(sun)
        p_data = [
            (80, 5, (169,169,169)), (120, 10, (218,165,32)), (160, 12, (0,191,255)),
            (200, 8, (255,69,0)), (300, 500, (210,180,140)), (400, 300, (240,230,140)),
            (500, 100, (173,216,230)), (580, 90, (0,0,205)) ]
        for i, (dist, mass, color) in enumerate(p_data):
            angle = random.uniform(0, 2 * np.pi)
            vel = circular_velocity(sun.mass, dist)
            px, py = center_pos[0] + dist * np.cos(angle), center_pos[1] + dist * np.sin(angle)
            vx, vy = -vel * np.sin(angle), vel * np.cos(angle)
            planets.append(Planet(px, py, vx, vy, mass, color))
    
    elif name == "Binary Star System":
        camera_zoom = 0.5
        m1, m2 = 300000, 200000
        total_mass = m1 + m2
        dist = 400
        r1, r2 = dist * m2 / total_mass, dist * m1 / total_mass
        vel_base = np.sqrt(G / (dist * total_mass))
        v1, v2 = m2 * vel_base, m1 * vel_base
        s1 = Planet(center_pos[0] - r1, center_pos[1], 0, v1, m1, (255, 255, 200))
        s2 = Planet(center_pos[0] + r2, center_pos[1], 0, -v2, m2, (255, 165, 100))
        planets.extend([s1, s2])
        p_data = [ (700, 500, (173, 216, 230)), (850, 800, (144, 238, 144)), (1000, 600, (218,112,214)) ]
        for i, (dist_p, mass_p, color_p) in enumerate(p_data):
            angle = (2 * np.pi / len(p_data)) * i
            vel = circular_velocity(total_mass, dist_p)
            px, py = center_pos[0] + dist_p * np.cos(angle), center_pos[1] + dist_p * np.sin(angle)
            vx, vy = -vel * np.sin(angle), vel * np.cos(angle)
            planets.append(Planet(px, py, vx, vy, mass_p, color_p))

    elif name == "Black Hole Center":
        camera_zoom = 0.6
        bh = Planet(center_pos[0], center_pos[1], 0, 0, 2000000, (0,0,0))
        planets.append(bh)
        p_data = [ (200, 300, (255, 69, 0)), (350, 500, (221, 160, 221)), (500, 400, (100, 149, 237)),
                   (600, 100, (240,230,140)), (750, 800, (32,178,170)) ]
        for i, (dist, mass, color) in enumerate(p_data):
            angle = (2 * np.pi / len(p_data)) * i
            vel = circular_velocity(bh.mass, dist)
            px, py = center_pos[0] + dist * np.cos(angle), center_pos[1] + dist * np.sin(angle)
            vx, vy = -vel * np.sin(angle), vel * np.cos(angle)
            planets.append(Planet(px, py, vx, vy, mass, color))

    elif name == "Binary Black Holes":
        camera_zoom = 1.0
        mass = 2000000
        distance = 400
        orbital_v = np.sqrt((G * mass) / (2 * distance))
        bh1 = Planet(center_pos[0] - distance / 2, center_pos[1], 0, orbital_v, mass, (0,0,0))
        bh2 = Planet(center_pos[0] + distance / 2, center_pos[1], 0, -orbital_v, mass, (0,0,0))
        planets.extend([bh1, bh2])

load_scenario("Solar System")

# --- UI Instances ---
pause_button = Button(WIDTH - 110, 10, 100, 30, "Pause", button_font, (100, 100, 100), (150, 150, 150))
hamburger_button = Button(10, 10, 40, 30, "☰", button_font, (100, 100, 100), (150, 150, 150))
menu_panel_rect = pygame.Rect(10, 50, 200, 220)
menu_buttons = [
    Button(20, 60, 180, 30, "Playground", button_font, (50, 50, 50), (80, 80, 80)),
    Button(20, 100, 180, 30, "Solar System", button_font, (50, 50, 50), (80, 80, 80)),
    Button(20, 140, 180, 30, "Binary Star System", button_font, (50, 50, 50), (80, 80, 80)),
    Button(20, 180, 180, 30, "Black Hole Center", button_font, (50, 50, 50), (80, 80, 80)),
    Button(20, 220, 180, 30, "Binary Black Holes", button_font, (50, 50, 50), (80, 80, 80)),
]

input_boxes = []
last_selected_planet_for_boxes = None

def draw_instructions(screen):
    inst_font = pygame.font.SysFont('Arial', 20)
    lines = [
        "--- Playground Mode ---", "", "Controls:",
        "- Right-Click: Spawn Planet", "- Left-Click: Select Planet", "- Drag & Release: Throw Planet",
        "- Middle-Click Drag: Pan View", "- Mouse Wheel: Zoom View", "- Spacebar: Pause / Play",
        "- Delete: Delete Selected Planet", "", "Select a planet and pause to edit its properties." ]
    y_offset = HEIGHT / 2 - (len(lines) * 25) / 2
    for i, line in enumerate(lines):
        text_surf = inst_font.render(line, True, (180, 180, 180))
        text_rect = text_surf.get_rect(center=(WIDTH / 2, y_offset + i * 25))
        screen.blit(text_surf, text_rect)

def draw_ui():
    if selected_planet and not (is_paused):
        info = f"Type: {selected_planet.stage.title()} | Mass: {selected_planet.mass:.1f}"
        text = font.render(info, True, (255,255,255))
        screen.blit(text, (10,50))
    if is_paused:
        pause_font = pygame.font.SysFont('Arial', 72)
        pause_text = pause_font.render("PAUSED", True, (255, 255, 255))
        text_rect = pause_text.get_rect(center=(WIDTH/2, HEIGHT/2))
        screen.blit(pause_text, text_rect)

running = True
while running:
    clock.tick(60)
    mouse_pos = pygame.mouse.get_pos()
    
    pause_button.update_hover(mouse_pos)
    hamburger_button.update_hover(mouse_pos)
    if menu_open:
        for button in menu_buttons:
            button.update_hover(mouse_pos)

    if is_paused and selected_planet:
        if selected_planet is not last_selected_planet_for_boxes:
            box_y_start = 10
            input_boxes = [InputBox(80, box_y_start + 35 * i, 140, 30, font, text, prop) for i, (text, prop) in enumerate([
                (selected_planet.stage, "stage"), (f"{selected_planet.mass:.1f}", "mass"),
                (f"{selected_planet.pos[0]:.1f}", "pos_x"), (f"{selected_planet.pos[1]:.1f}", "pos_y"),
                (f"{selected_planet.vel[0]:.2f}", "vel_x"), (f"{selected_planet.vel[1]:.2f}", "vel_y")])]
            last_selected_planet_for_boxes = selected_planet
    else:
        input_boxes = []
        last_selected_planet_for_boxes = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        active_box_handled_key = False
        if is_paused and selected_planet:
            for box in input_boxes:
                result = box.handle_event(event)
                if box.is_active and event.type == pygame.KEYDOWN: active_box_handled_key = True
                if result == 'enter':
                    try:
                        prop = box.property_name
                        if prop != 'stage':
                            new_val = float(box.text)
                            if prop == 'mass':
                                selected_planet.mass = new_val if new_val > 0 else selected_planet.mass
                                selected_planet.radius = max(2, int((selected_planet.mass/1)**(1/3.0)))
                                selected_planet.update_stage()
                            elif prop == 'pos_x': selected_planet.pos[0] = new_val
                            elif prop == 'pos_y': selected_planet.pos[1] = new_val
                            elif prop == 'vel_x': selected_planet.vel[0] = new_val
                            elif prop == 'vel_y': selected_planet.vel[1] = new_val
                        last_selected_planet_for_boxes = None
                    except ValueError: last_selected_planet_for_boxes = None
        
        if pause_button.is_clicked(event):
            is_paused = not is_paused
            pause_button.text = "Play" if is_paused else "Pause"
        
        elif hamburger_button.is_clicked(event):
            menu_open = not menu_open

        elif menu_open:
            for button in menu_buttons:
                if button.is_clicked(event):
                    load_scenario(button.text)
                    menu_open = False
                    break
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                world_pos_before_zoom = screen_to_world(mouse_pos)
                camera_zoom *= 1.1
                camera_offset += world_pos_before_zoom - screen_to_world(mouse_pos)
            elif event.button == 5:
                world_pos_before_zoom = screen_to_world(mouse_pos)
                camera_zoom /= 1.1
                camera_offset += world_pos_before_zoom - screen_to_world(mouse_pos)
            elif event.button == 2:
                is_panning = True
                pan_start_pos = np.array(mouse_pos)
            elif event.button == 1:
                if not any(box.is_active for box in input_boxes):
                    if menu_open and not menu_panel_rect.collidepoint(mouse_pos):
                        menu_open = False
                    else:
                        selected_planet = None
                        dragging_planet = None
                        for p in planets:
                            p_screen_pos = world_to_screen(p.pos)
                            p_screen_radius = p.radius * camera_zoom
                            if np.linalg.norm(p_screen_pos - np.array(mouse_pos)) < p_screen_radius + 5:
                                selected_planet = p
                                dragging_planet = p
                                drag_positions.clear()
                                drag_positions.append(mouse_pos)
                                break
            elif event.button == 3:
                world_mx, world_my = screen_to_world(mouse_pos)
                mass = random.uniform(200,500)
                planets.append(Planet(world_mx, world_my, 0, 0, mass,
                                    (random.randint(50,255), random.randint(50,255), random.randint(50,255))))
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and dragging_planet:
                if len(drag_positions) > 1:
                    start_pos_screen = drag_positions[0]
                    end_pos_screen = drag_positions[-1]
                    vel_vec = (screen_to_world(end_pos_screen) - screen_to_world(start_pos_screen)) * THROW_MULTIPLIER * 5
                    dragging_planet.vel = vel_vec
                dragging_planet = None
            elif event.button == 2:
                is_panning = False
                pan_start_pos = None
        
        elif event.type == pygame.KEYDOWN and not active_box_handled_key:
            if event.key == pygame.K_SPACE:
                is_paused = not is_paused
                pause_button.text = "Play" if is_paused else "Pause"
            if selected_planet:
                if event.key == pygame.K_DELETE:
                    planets.remove(selected_planet)
                    selected_planet = None
                elif event.key == pygame.K_UP and not is_paused:
                    selected_planet.mass *= 1.1
                    selected_planet.radius = int((selected_planet.mass/1)**(1/3.0))
                    selected_planet.update_stage()
                elif event.key == pygame.K_DOWN and not is_paused:
                    selected_planet.mass *= 0.9
                    selected_planet.radius = max(2, int((selected_planet.mass/1)**(1/3.0)))
                    selected_planet.update_stage()

    if is_panning:
        pan_current_pos = np.array(mouse_pos)
        delta = pan_start_pos - pan_current_pos
        camera_offset += delta / camera_zoom
        pan_start_pos = pan_current_pos

    if dragging_planet:
        dragging_planet.pos = screen_to_world(mouse_pos)
        drag_positions.append(mouse_pos)
    
    if not is_paused:
        for p in planets[:]:
            try:
                p.update(planets)
            except Exception as e:
                if p in planets: planets.remove(p)

    screen.fill((0,0,0))
    for p in planets:
        p.draw(screen, selected=(p==selected_planet))

    if current_scenario == "Playground" and not planets:
        draw_instructions(screen)
        
    draw_ui()
    pause_button.draw(screen)
    hamburger_button.draw(screen)

    if menu_open:
        pygame.draw.rect(screen, (30, 30, 30), menu_panel_rect, border_radius=8)
        for button in menu_buttons:
            button.draw(screen)

    for box in input_boxes:
        box.draw(screen)
        
    pygame.display.flip()

pygame.quit()