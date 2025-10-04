import pygame
import numpy as np
import random
import collections
import math

# Initialize Pygame
pygame.init()

# Screen
WIDTH, HEIGHT = 1000, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cosmic Canvas")
clock = pygame.time.Clock()

# Constants
G = 0.05
DT = 0.5
THROW_MULTIPLIER = 0.2
PHYSICS_SUB_STEPS = 5

# --- Star stage mass thresholds ---
RED_DWARF_MASS = 50000
STAR_MASS = 200000
RED_GIANT_MASS = 500000
BLUE_GIANT_MASS = 800000
CHANDRASEKHAR_LIMIT = 1400000
BLACK_HOLE_MASS = 2000000

# --- UI Classes ---
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text, self.font, self.color, self.hover_color = text, font, color, hover_color
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
        self.color, self.active_color, self.text_color = (100, 100, 100), (150, 150, 150), (255, 255, 255)
        self.font, self.text, self.property_name, self.is_active = font, text, property_name, False
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.is_active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.is_active:
            if event.key == pygame.K_RETURN: return 'enter'
            elif event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            elif event.unicode in '0123456789.-': self.text += event.unicode
        return None
    def draw(self, screen):
        current_color = self.active_color if self.is_active else self.color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=5)
        text_surface = self.font.render(self.text, True, self.text_color)
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))
        label_surface = self.font.render(self.property_name.replace('_', ' ').title(), True, (200, 200, 200))
        screen.blit(label_surface, (self.rect.x - 85, self.rect.y + 5))

# --- Camera and Pan Variables ---
camera_zoom, camera_offset = 1.0, np.array([WIDTH / 2.0, HEIGHT / 2.0])
is_panning, pan_start_pos = False, None

# --- Coordinate Conversion Functions ---
def screen_to_world(screen_pos):
    return (np.array(screen_pos) - np.array([WIDTH/2, HEIGHT/2])) / camera_zoom + camera_offset
def world_to_screen(world_pos):
    return (np.array(world_pos) - camera_offset) * camera_zoom + np.array([WIDTH/2, HEIGHT/2])

# Planet class
class Planet:
    def __init__(self, x, y, vx, vy, mass, color=None, radius=None, stage="PLANET"):
        self.pos, self.vel, self.mass = np.array([float(x), float(y)]), np.array([float(vx), float(vy)]), float(mass)
        self.stage, self.color, self.trail = stage, color, []
        self.radius = int(radius if radius is not None else (self.mass/1)**(1/3.0))
        self.supernova_timer = 0
        if self.color is None:
            self.set_stage_color()

    def set_stage_color(self):
        if self.stage == "PLANET":
            if self.color is None: # Only assign random color if no color exists
                self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        elif self.stage == "RED_DWARF": self.color = (255, 100, 50)
        elif self.stage == "STAR": self.color = (255, 255, 200)
        elif self.stage == "RED_GIANT": self.color = (255, 69, 0)
        elif self.stage == "BLUE_GIANT": self.color = (170, 220, 255)
        elif self.stage == "WHITE_DWARF": self.color = (240, 240, 255)
        elif self.stage == "NEUTRON_STAR": self.color = (200, 220, 255)
        elif self.stage == "BLACK_HOLE": self.color = (0, 0, 0)

    def set_stage(self, new_stage):
        self.stage = new_stage
        self.set_stage_color()

    def trigger_evolution_check(self):
        if self.stage == "BLUE_GIANT" and self.mass >= BLACK_HOLE_MASS: self.go_supernova()
        elif self.stage == "WHITE_DWARF" and self.mass >= CHANDRASEKHAR_LIMIT: self.go_supernova()
        elif self.stage == "NEUTRON_STAR" and self.mass >= BLACK_HOLE_MASS: self.set_stage("BLACK_HOLE")
        elif self.stage == "PLANET" and self.mass >= RED_DWARF_MASS: self.set_stage("RED_DWARF")
        elif self.stage == "RED_DWARF" and self.mass >= STAR_MASS: self.set_stage("STAR")
        elif self.stage == "STAR" and self.mass >= RED_GIANT_MASS: self.set_stage("RED_GIANT")
        elif self.stage == "RED_GIANT" and self.mass >= BLUE_GIANT_MASS: self.set_stage("BLUE_GIANT")
        
    def go_supernova(self):
        self.supernova_timer = 120
        self.mass *= 0.8
        if self.mass >= BLACK_HOLE_MASS:
            self.set_stage("BLACK_HOLE")
        else:
            self.set_stage("NEUTRON_STAR")
            self.radius = 10

    def update(self, planets, dt):
        if dragging_planet == self or self.supernova_timer > 0: return

        total_force = np.array([0.0, 0.0])
        for other in planets:
            if other != self:
                r_vec, r_mag = other.pos - self.pos, np.linalg.norm(other.pos - self.pos)
                if self.stage == "BLACK_HOLE" and r_mag < self.radius:
                    self.mass += other.mass; self.radius = int((self.mass / 1)**(1/3.0))
                    if other in planets: planets.remove(other); continue
                if r_mag > 0: total_force += (G * self.mass * other.mass / r_mag**3) * r_vec
                if r_mag > 0 and r_mag < self.radius + other.radius:
                    if self.mass >= other.mass and other in planets:
                        new_mass = self.mass + other.mass
                        self.radius = int((self.radius**3 + other.radius**3)**(1/3.0))
                        self.vel = (self.vel * self.mass + other.vel * other.mass) / new_mass
                        self.pos = (self.pos * self.mass + other.pos * other.mass) / new_mass
                        self.mass = new_mass
                        self.trigger_evolution_check()
                        planets.remove(other)

        self.vel += total_force / self.mass * dt
        self.pos += self.vel * dt
        self.trail.append(tuple(self.pos))
        if len(self.trail) > 500: self.trail.pop(0)

    def draw(self, screen, selected=False):
        screen_pos = world_to_screen(self.pos).astype(int)
        screen_radius = max(2, int(self.radius * camera_zoom))

        if self.supernova_timer > 0:
            self.supernova_timer -= 1; progress = (120 - self.supernova_timer)/120
            size = int(progress * 500 * camera_zoom); alpha = int((1 - progress**2) * 200)
            if size>0 and alpha>0:
                glow_surface = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (255,255,255,alpha), (size,size), size)
                screen.blit(glow_surface, (screen_pos[0]-size, screen_pos[1]-size))
        
        if self.stage in ["RED_DWARF", "STAR", "RED_GIANT", "BLUE_GIANT", "WHITE_DWARF"]:
            glow_map = {"RED_DWARF":1.5, "STAR":2.5, "RED_GIANT":3.5, "BLUE_GIANT":3.0, "WHITE_DWARF":2.0}
            color_map = {"RED_DWARF":(255,100,50,80), "STAR":(255,255,200,50), "RED_GIANT":(255,69,0,70), "BLUE_GIANT":(170,220,255,70), "WHITE_DWARF":(240,240,255,40)}
            if self.stage == "RED_GIANT": screen_radius = int(screen_radius * 2.0)
            if self.stage == "BLUE_GIANT": screen_radius = int(screen_radius * 1.5)
            glow_radius = int(screen_radius * glow_map.get(self.stage, 1.0))
            glow_surface = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, color_map[self.stage], (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surface, (screen_pos[0]-glow_radius, screen_pos[1]-glow_radius))
        elif self.stage == "BLACK_HOLE": pygame.draw.circle(screen, (255,165,0), screen_pos, screen_radius + 5, 3)
        elif self.stage == "NEUTRON_STAR":
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 4
            pygame.draw.circle(screen, (200,220,255,150), screen_pos, screen_radius + int(pulse), 1)

        if len(self.trail)>1:
            trail_color = (138,43,226) if self.stage == "BLACK_HOLE" else self.color
            pygame.draw.lines(screen, trail_color, False, [tuple(world_to_screen(p)) for p in self.trail], 1)
        
        pygame.draw.circle(screen, self.color, screen_pos, screen_radius)
        if selected: pygame.draw.circle(screen, (255,255,255), screen_pos, screen_radius + 4, 2)

def circular_velocity(m, d): return np.sqrt(G * m / d) if d > 0 else 0

planets = []
selected_planet, dragging_planet = None, None
drag_positions = collections.deque(maxlen=10)
font = pygame.font.SysFont('Arial', 24)
button_font = pygame.font.SysFont('segoeuisymbol, dejavusans, arial', 22, bold=True)
is_paused, menu_open, spawn_menu_active = False, False, False
current_scenario, spawn_menu_buttons, spawn_menu_panel_rect, spawn_pos_world = "", [], None, None

def load_scenario(name):
    global planets, selected_planet, camera_zoom, camera_offset, dragging_planet, current_scenario
    planets.clear(); selected_planet, dragging_planet = None, None
    camera_zoom, camera_offset = 1.0, np.array([WIDTH/2.0, HEIGHT/2.0])
    center_pos = [WIDTH/2.0, HEIGHT/2.0]; current_scenario = name
    if name == "Playground": return
    if name == "Dying Star":
        camera_zoom=1.2; giant = Planet(center_pos[0]-100, center_pos[1], 0, 0.5, RED_GIANT_MASS, stage="RED_GIANT")
        wd = Planet(center_pos[0]+250, center_pos[1], 0, -1.5, CHANDRASEKHAR_LIMIT*0.9, stage="WHITE_DWARF", radius=15); planets.extend([giant, wd])
    elif name == "Solar System":
        camera_zoom = 0.4; sun = Planet(center_pos[0], center_pos[1], 0, 0, 450000, stage="STAR"); planets.append(sun)
        p_data = [(160,5,(169,169,169)), (220,10,(218,165,32)), (290,12,(0,191,255)), (380,8,(255,69,0)), (600,500,(210,180,140)), (800,300,(240,230,140)),(1000,100,(173,216,230)),(1150,90,(0,0,205))]
        for i, (dist, mass, color) in enumerate(p_data):
            angle=random.uniform(0,2*np.pi); vel=circular_velocity(sun.mass, dist)
            px,py,vx,vy = center_pos[0]+dist*np.cos(angle),center_pos[1]+dist*np.sin(angle),-vel*np.sin(angle),vel*np.cos(angle)
            planets.append(Planet(px,py,vx,vy,mass,color))
    elif name == "Binary Star System":
        camera_zoom=0.5; m1,m2 = 300000,200000; total_mass,dist = m1+m2,400
        r1,r2 = dist*m2/total_mass, dist*m1/total_mass; vel_base = np.sqrt(G/(dist*total_mass)); v1,v2=m2*vel_base, m1*vel_base
        planets.extend([Planet(center_pos[0]-r1, center_pos[1], 0, v1, m1, stage="STAR"), Planet(center_pos[0]+r2, center_pos[1], 0, -v2, m2, stage="STAR")])
        p_data = [(700,500,(173,216,230)), (850,800,(144,238,144)), (1000,600,(218,112,214))]
        for i, (dist_p, mass_p, color_p) in enumerate(p_data):
            angle=(2*np.pi/len(p_data))*i; vel=circular_velocity(total_mass, dist_p)
            px,py,vx,vy = center_pos[0]+dist_p*np.cos(angle), center_pos[1]+dist_p*np.sin(angle),-vel*np.sin(angle),vel*np.cos(angle)
            planets.append(Planet(px,py,vx,vy,mass_p,color_p))
    elif name == "Black Hole Center":
        camera_zoom=0.6; bh=Planet(center_pos[0],center_pos[1],0,0,2000000,stage="BLACK_HOLE"); planets.append(bh)
        p_data = [(200,300,(255,69,0)),(350,500,(221,160,221)),(500,400,(100,149,237)),(600,100,(240,230,140)),(750,800,(32,178,170))]
        for i, (dist, mass, color) in enumerate(p_data):
            angle=(2*np.pi/len(p_data))*i; vel=circular_velocity(bh.mass, dist)
            px,py,vx,vy = center_pos[0]+dist*np.cos(angle),center_pos[1]+dist*np.sin(angle),-vel*np.sin(angle),vel*np.cos(angle)
            planets.append(Planet(px,py,vx,vy,mass,color))
    elif name == "Binary Black Holes":
        camera_zoom=1.0; mass,distance = 2000000,400; orbital_v = np.sqrt((G*mass)/(2*distance))
        planets.extend([Planet(center_pos[0]-distance/2,center_pos[1],0,orbital_v,mass,stage="BLACK_HOLE"), Planet(center_pos[0]+distance/2,center_pos[1],0,-orbital_v,mass,stage="BLACK_HOLE")])
load_scenario("Solar System")

pause_button = Button(WIDTH-110, 10, 100, 30, "Pause", button_font, (100,100,100), (150,150,150))
hamburger_button = Button(10, 10, 40, 30, "☰", button_font, (100,100,100), (150,150,150))
menu_panel_rect = pygame.Rect(10, 50, 200, 260)
menu_buttons = [ Button(20, 60+40*i, 180, 30, name, button_font, (50,50,50),(80,80,80)) for i, name in enumerate(["Playground", "Solar System", "Binary Star System", "Black Hole Center", "Binary Black Holes", "Dying Star"])]
input_boxes, last_selected_planet_for_boxes = [], None

def draw_instructions(screen):
    inst_font = pygame.font.SysFont('Arial', 20)
    lines = ["--- Playground Mode ---", "", "Controls:", "- Right-Click: Open spawn menu", "- Left-Click: Select Planet", "- Drag & Release: Throw Planet", "- Middle-Click Drag: Pan View", "- Mouse Wheel: Zoom View", "- Spacebar: Pause / Play", "- Delete: Delete Selected Planet", "", "Select a planet and pause to edit its properties." ]
    for i, line in enumerate(lines):
        text_surf = inst_font.render(line, True, (180,180,180)); text_rect = text_surf.get_rect(center=(WIDTH/2, HEIGHT/2 - (len(lines)*25)/2 + i*25)); screen.blit(text_surf, text_rect)
def draw_ui():
    if selected_planet and not is_paused:
        info = f"Type: {selected_planet.stage.replace('_', ' ').title()} | Mass: {selected_planet.mass:.1f}"
        text = font.render(info, True, (255,255,255)); screen.blit(text, (10,50))
    if is_paused:
        pause_font = pygame.font.SysFont('Arial', 72); pause_text = pause_font.render("PAUSED", True, (255,255,255)); text_rect = pause_text.get_rect(center=(WIDTH/2, HEIGHT/2)); screen.blit(pause_text, text_rect)

running = True
while running:
    clock.tick(60)
    mouse_pos = pygame.mouse.get_pos()
    
    for btn in [pause_button, hamburger_button] + (menu_buttons if menu_open else []) + (spawn_menu_buttons if spawn_menu_active else []): btn.update_hover(mouse_pos)

    if is_paused and selected_planet and selected_planet is not last_selected_planet_for_boxes:
        input_boxes = [InputBox(95, 10+35*i, 140, 30, font, text, prop) for i, (text, prop) in enumerate([ (selected_planet.stage.replace('_', ' '), "stage"), (f"{selected_planet.mass:.1f}","mass"), (f"{selected_planet.pos[0]:.1f}","pos_x"), (f"{selected_planet.pos[1]:.1f}","pos_y"), (f"{selected_planet.vel[0]:.2f}","vel_x"), (f"{selected_planet.vel[1]:.2f}","vel_y")])]
        last_selected_planet_for_boxes = selected_planet
    elif not (is_paused and selected_planet): input_boxes.clear(); last_selected_planet_for_boxes = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        active_box_handled_key = False
        if is_paused and selected_planet:
            for box in input_boxes:
                if box.is_active and event.type == pygame.KEYDOWN: active_box_handled_key = True
                if box.handle_event(event) == 'enter':
                    try:
                        prop, new_val = box.property_name, float(box.text)
                        if prop=='mass': selected_planet.mass=new_val if new_val>0 else 1; selected_planet.radius=max(2,int((selected_planet.mass/1)**(1/3.0))); selected_planet.trigger_evolution_check()
                        elif prop=='pos_x': selected_planet.pos[0]=new_val
                        elif prop=='pos_y': selected_planet.pos[1]=new_val
                        elif prop=='vel_x': selected_planet.vel[0]=new_val
                        elif prop=='vel_y': selected_planet.vel[1]=new_val
                        last_selected_planet_for_boxes = None
                    except ValueError: last_selected_planet_for_boxes = None
        
        if pause_button.is_clicked(event): is_paused=not is_paused; pause_button.text = "Play" if is_paused else "Pause"
        elif hamburger_button.is_clicked(event): menu_open=not menu_open; spawn_menu_active=False
        elif menu_open:
            for button in menu_buttons:
                if button.is_clicked(event): load_scenario(button.text); menu_open=False; break
        elif spawn_menu_active:
            clicked_button_text = next((btn.text for btn in spawn_menu_buttons if btn.is_clicked(event)), None)
            if clicked_button_text:
                types = {"Planet":(random.uniform(200,800),None,"PLANET"), "Red Dwarf":(RED_DWARF_MASS,None,"RED_DWARF"), "Star":(STAR_MASS,None,"STAR"), "Red Giant":(RED_GIANT_MASS,None,"RED_GIANT"), "Blue Giant":(BLUE_GIANT_MASS,None,"BLUE_GIANT"), "White Dwarf":(CHANDRASEKHAR_LIMIT*0.8,None,"WHITE_DWARF"), "Neutron Star":(BLACK_HOLE_MASS*0.9,None,"NEUTRON_STAR"), "Black Hole":(BLACK_HOLE_MASS,None,"BLACK_HOLE")}
                mass, color, stage = types.get(clicked_button_text); radius = 15 if stage=="WHITE_DWARF" else (10 if stage=="NEUTRON_STAR" else None)
                planets.append(Planet(spawn_pos_world[0],spawn_pos_world[1],0,0,mass,color,stage=stage,radius=radius))
                spawn_menu_active = False
            elif event.type == pygame.MOUSEBUTTONDOWN: spawn_menu_active = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in [4, 5]:
                world_pos_before = screen_to_world(mouse_pos); camera_zoom *= 1.1 if event.button == 4 else 1/1.1; camera_offset += world_pos_before - screen_to_world(mouse_pos)
            elif event.button==2: is_panning, pan_start_pos = True, np.array(mouse_pos)
            elif event.button==1:
                if not any(b.is_active for b in input_boxes):
                    if menu_open and not menu_panel_rect.collidepoint(mouse_pos): menu_open = False
                    else:
                        selected_planet, dragging_planet = None, None
                        for p in planets:
                            if np.linalg.norm(world_to_screen(p.pos) - np.array(mouse_pos)) < p.radius*camera_zoom + 5:
                                selected_planet, dragging_planet = p, p; drag_positions.clear(); drag_positions.append(mouse_pos); break
            elif event.button==3:
                spawn_menu_active, menu_open, spawn_pos_world = True, False, screen_to_world(event.pos)
                mx, my = event.pos; spawn_menu_panel_rect = pygame.Rect(mx,my, 160, 290)
                spawn_menu_buttons = [Button(mx+5, my+5+35*i, 150, 30, name, button_font, (50,50,50),(80,80,80)) for i, name in enumerate(["Planet", "Red Dwarf", "Star", "Red Giant", "Blue Giant", "White Dwarf", "Neutron Star", "Black Hole"])]
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button==1 and dragging_planet:
                if len(drag_positions)>1: dragging_planet.vel = (screen_to_world(drag_positions[-1])-screen_to_world(drag_positions[0]))*THROW_MULTIPLIER*5
                dragging_planet = None
            elif event.button==2: is_panning = False
        elif event.type == pygame.KEYDOWN and not active_box_handled_key:
            if event.key == pygame.K_SPACE: is_paused = not is_paused; pause_button.text = "Play" if is_paused else "Pause"
            if selected_planet:
                if event.key == pygame.K_DELETE: planets.remove(selected_planet); selected_planet = None
                elif event.key == pygame.K_UP:
                    selected_planet.mass*=1.1; selected_planet.radius=int((selected_planet.mass/1)**(1/3.0)); selected_planet.trigger_evolution_check(); last_selected_planet_for_boxes=None
                elif event.key == pygame.K_DOWN:
                    selected_planet.mass*=0.9; selected_planet.radius=max(2,int((selected_planet.mass/1)**(1/3.0))); last_selected_planet_for_boxes=None

    if is_panning: camera_offset += (pan_start_pos-np.array(mouse_pos))/camera_zoom; pan_start_pos=np.array(mouse_pos)
    if dragging_planet: dragging_planet.pos=screen_to_world(mouse_pos); drag_positions.append(mouse_pos)
    
    if not is_paused:
        sub_dt = DT / PHYSICS_SUB_STEPS
        for _ in range(PHYSICS_SUB_STEPS):
            for p in planets[:]:
                try: p.update(planets, sub_dt)
                except Exception:
                    if p in planets: planets.remove(p)

    screen.fill((0,0,0))
    for p in planets: p.draw(screen, selected=p==selected_planet)
    if current_scenario=="Playground" and not planets: draw_instructions(screen)
    draw_ui()
    
    if menu_open: pygame.draw.rect(screen, (30, 30, 30), menu_panel_rect, border_radius=8)
    if spawn_menu_active: pygame.draw.rect(screen, (30, 30, 30), spawn_menu_panel_rect, border_radius=8)
        
    for btn in [pause_button, hamburger_button] + (menu_buttons if menu_open else []) + (spawn_menu_buttons if spawn_menu_active else []): btn.draw(screen)
    for box in input_boxes: box.draw(screen)
        
    pygame.display.flip()

pygame.quit()