import pygame

from simulation.simulation import Simulation
from simulation.autopilot import Autopilot
from rendering.renderer import Renderer
from gui.hud import Hud
from gui.menu import Menu, MenuAction
from gui.orbit_editor import OrbitEditor
from core.camera import Camera
from input.input_state import InputState
from utils.config import (
    SIMULATION_SPEED_STEPS, DEFAULT_SIMULATION_SPEED_INDEX,
    BASE_SIMULATION_SPEED, MANUAL_IMPULSE_MS
)
from states import AppState, FlightMode


class Game:
    """Owns all game objects and coordinates update + draw each frame"""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.running = True

        # core objects
        self.sim = Simulation()
        self.autopilot = Autopilot()
        self.camera = Camera(*screen.get_size())

        # rendering
        self.renderer = Renderer(screen, self.camera)
        self.hud = Hud(screen)
        self.menu = Menu(screen)
        self.editor = OrbitEditor(screen)

        # state
        self.app_state = AppState.PLAYING
        self.flight_mode = FlightMode.IDLE
        self.hud_visible = True
        self._speed_idx = DEFAULT_SIMULATION_SPEED_INDEX

    @property
    def sim_speed(self) -> float:
        return SIMULATION_SPEED_STEPS[self._speed_idx] * BASE_SIMULATION_SPEED

    @property
    def _manual_allowed(self) -> bool:
        return self.flight_mode in (FlightMode.IDLE, FlightMode.MANUAL)

    @property
    def _autopilot_allowed(self) -> bool:
        return self.flight_mode in (FlightMode.IDLE, FlightMode.AUTOPILOT)

    # ------------------ Update ------------------------
    def update(self, input_state: InputState, dt: float):
        if input_state.quit:
            self.running = False
            return

        self._handle_global(input_state)

        if self.app_state == AppState.MENU:
            self._update_menu(input_state)
        elif self.app_state == AppState.EDITOR:
            self._update_editor(input_state, dt)
        elif self.app_state == AppState.PLAYING:
            self._update_playing(input_state, dt)

    # ------------------ Draw ----------------------
    def draw(self, dt: float):
        self.renderer.update(dt)

        if self.app_state == AppState.EDITOR:
            self.renderer.draw(
                self.sim,
                override_start=self.editor.preview_start_orbit,
                override_target=self.editor.preview_target_orbit,
            )
        else:
            self.renderer.draw(self.sim)

        self.hud.draw(self.sim, self.sim_speed, self.autopilot, self.flight_mode, self.hud_visible)

        if self.app_state == AppState.MENU:
            self.menu.draw()
        elif self.app_state == AppState.EDITOR:
            self.editor.draw()

    # Global inputs (active in all states)
    def _handle_global(self, input_state: InputState):
        # Camera
        if input_state.scroll_delta:
            self.camera.zoom_at(input_state.scroll_pos, input_state.scroll_delta)
        if input_state.pan_delta != (0, 0):
            self.camera.pan(input_state.pan_delta)
        if input_state.c_pressed:
            self.camera.reset()

        # HUD + sim speed
        if input_state.h_pressed:
            self.hud_visible = not self.hud_visible
        if input_state.plus_pressed:
            self._speed_idx = min(self._speed_idx + 1, len(SIMULATION_SPEED_STEPS) - 1)
        if input_state.minus_pressed:
            self._speed_idx = max(self._speed_idx - 1, 0)

    # ------------------ Per-state update ------------------------
    def _update_menu(self, input_state: InputState):
        # Feed raw mouse events to menu
        action = self.menu.handle_events(input_state.events)

        if action == MenuAction.RESUME or input_state.escape_pressed:
            self.app_state = AppState.PLAYING
        elif action == MenuAction.EDIT_ORBITS:
            self.editor.open(self.sim.start_orbit, self.sim.target_orbit)
            self.app_state = AppState.EDITOR
        elif action == MenuAction.RESET:
            self._reset()
            self.app_state = AppState.PLAYING
        elif action == MenuAction.QUIT:
            self.running = False

    def _update_editor(self, input_state: InputState, dt: float):
        result = self.editor.handle_events(input_state.events)

        if result == 'apply':
            self.sim.start_orbit = self.editor.start_orbit
            self.sim.target_orbit = self.editor.target_orbit
            self._reset()
            self.app_state = AppState.PLAYING
        elif result == 'cancel' or input_state.escape_pressed:
            self.app_state = AppState.PLAYING

    def _update_playing(self, input_state: InputState, dt: float):
        prev_dv = self.sim.ship.total_delta_v

        if input_state.escape_pressed:
            self.app_state = AppState.MENU
            return

        if input_state.r_pressed:
            self._reset()
            return

        if input_state.a_pressed and self._autopilot_allowed:
            self.autopilot.start(self.sim)
            self.flight_mode = FlightMode.AUTOPILOT

        # Manual thrust
        if self._manual_allowed:
            if input_state.thrust_up:
                self.sim.ship.apply_impulse_tangential(+MANUAL_IMPULSE_MS)
                self.flight_mode = FlightMode.MANUAL
            if input_state.thrust_down:
                self.sim.ship.apply_impulse_tangential(-MANUAL_IMPULSE_MS)
                self.flight_mode = FlightMode.MANUAL

        # Advance simulation
        self.autopilot.update(self.sim, dt * self.sim_speed)
        self.sim.update(dt * self.sim_speed)

        if self.sim.ship.total_delta_v > prev_dv:
            self.renderer.notify_impulse(self.sim.ship)

    # ------------ Helpers -----------------
    def _reset(self):
        self.sim.reset_ship()
        self.autopilot.reset()
        self.flight_mode = FlightMode.IDLE
        self.renderer.particles.clear()

