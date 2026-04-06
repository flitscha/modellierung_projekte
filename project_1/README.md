# Hohmann Transfer Simulator

An interactive orbital mechanics simulator built for the course **PS Modellierung** (Summer Semester 2026).
The simulator visualises the Hohmann transfer — the optimal 2-impulse manoeuvre to move a spaceship between two circular orbits.


## Team
- Noah Bichler
- Felix Campidell
- Aylin Postal


## Key bindings

| Key | Action |
|---|---|
| `+` / `-` | Increase / decrease simulation speed |
| `ESC` | enter pause menu |
| `R` | Reset simulation |
| `H` | Toggle HUD |
| `A` | enable autopilot |
| `UP` / `DOWN` | manual thrust in tangential direction |
| Scroll wheel | Zoom in / out (centered on mouse cursor) |
| Right-click + drag | Pan camera |
| `C` | reset camera |


## Features
 
- Numerical orbit simulation using `scipy.integrate.odeint`
- Autopilot that computes and executes the optimal Hohmann transfer between two circular orbits
- Manual flight mode
- Interactive orbit editor


## AI Usage

AI tools (in particular Claude by Anthropic) were used during development.

It was especially useful for the visual parts (HUD panels, pause menu, orbit editor, particle effects).

We did not just copy generated code. All suggestions were understood, checked and adapted - especially for the physics and simulation parts.

