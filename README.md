Cosmic Canvas
Cosmic Canvas is an interactive 2D gravity simulator where you can create, destroy, and manipulate your own planetary systems. Watch as planets merge and evolve into massive stars and black holes, or load pre-built scenarios like a realistic Solar System, a chaotic binary star system, and more.
## Features
Interactive Sandbox: Create planets with a simple click, or take direct control by selecting, dragging, and throwing celestial bodies to alter their orbits.

Stellar Evolution: Watch as planets merge and grow. Accumulate enough mass to evolve from a simple planet to a Brown Dwarf, a bright Star, a massive Giant, and finally into a space-devouring Black Hole, each with unique visual properties.

Black Hole Physics: Black holes feature a unique consumption mechanic, absorbing any object that crosses their "event horizon" (represented by their radius) and adding its mass to their own.

Precision Editing: Pause the simulation to become a cosmic architect. Select any body and fine-tune its properties by directly editing its mass, position (x,y), and velocity (v 
x
​
 ,v 
y
​
 ).

Dynamic Camera: Explore your creation with a fully featured camera system, including zooming with the mouse wheel and panning by dragging with the middle mouse button.

Pre-built Scenarios: Load a variety of presets from the menu, including a stable Solar System, a chaotic Binary Star System, a system orbiting a supermassive Black Hole, or two Black Holes locked in a gravitational dance.

Playground Mode: Start with a completely empty universe and follow the on-screen instructions to build your own system from the ground up.

## Requirements
Python 3.x

Pygame: pip install pygame

NumPy: pip install numpy

## How to Run
Make sure you have Python and the required libraries installed.

Save the simulation code as a Python file (e.g., cosmic_canvas.py).

Run the file from your terminal:

python cosmic_canvas.py
## Controls
### Mouse Controls
Left-Click: Select a celestial body.

Left-Click + Drag: Move a body.

Release Drag: Throw a body with velocity.

Right-Click: Spawn a new planet at the cursor (with zero initial velocity).

Middle-Click + Drag: Pan the camera view.

Mouse Wheel: Zoom in and out.

### Keyboard Controls
Spacebar: Pause or play the simulation.

Delete: Delete the currently selected body.

Up Arrow (while running): Increase the mass of the selected planet.

Down Arrow (while running): Decrease the mass of the selected planet.

### UI Controls
☰ (Menu Button): Open or close the scenario loader menu.

Pause/Play Button: Toggles the simulation state.

Input Boxes (while paused & a body is selected): Click a box to activate it, type a new value, and press Enter to confirm the change.
