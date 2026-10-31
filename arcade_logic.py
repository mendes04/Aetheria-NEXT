"""Pure, deterministic-ish game rules and gesture stabilization for Aetheria Arcade.

No graphics, camera or audio dependency: easy to test and tune off-camera.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
import random
from typing import Sequence

BLOCK_SHAPES = (
    ((0,0),), ((0,0),(1,0)), ((0,0),(0,1)),
    ((0,0),(1,0),(2,0)), ((0,0),(0,1),(0,2)),
    ((0,0),(1,0),(0,1),(1,1)),
    ((0,0),(1,0),(2,0),(3,0)), ((0,0),(0,1),(0,2),(0,3)),
    ((0,0),(1,0),(2,0),(1,1)),
    ((0,0),(0,1),(1,1)), ((1,0),(0,1),(1,1)),
    ((0,0),(1,0),(1,1)), ((0,0),(1,0),(0,1)),
    ((0,0),(1,0),(2,0),(0,1),(1,1),(2,1)),
    ((0,0),(0,1),(0,2),(1,2)),
)

@dataclass
class BlockBoard:
    size: int = 8
    grid: list[list[int]] = field(default_factory=list)
    score: int = 0
    combo: int = 0
    moves: int = 0
    game_over: bool = False
    tray: list[tuple[tuple[int,int], ...] | None] = field(default_factory=list)
    def __post_init__(self):
        if not self.grid:
            self.grid = [[0] * self.size for _ in range(self.size)]
        if not self.tray:
            self.refill()
    def refill(self, rng=None):
        rng = rng or random
        self.tray = [rng.choice(BLOCK_SHAPES) for _ in range(3)]
        self.game_over = not self.can_play_any()
    def can_place(self, shape, x, y):
        return bool(shape) and all(0 <= x+dx < self.size and 0 <= y+dy < self.size
                                   and not self.grid[y+dy][x+dx] for dx,dy in shape)
    def valid_positions(self, shape):
        return [(x,y) for y in range(self.size) for x in range(self.size)
                if self.can_place(shape,x,y)]
    def can_play_any(self):
        return any(self.valid_positions(shape) for shape in self.tray if shape)
    def place(self, slot: int, x: int, y: int):
        if self.game_over or not 0 <= slot < len(self.tray):
            return None
        shape = self.tray[slot]
        if not self.can_place(shape,x,y):
            return None
        for dx,dy in shape:
            self.grid[y+dy][x+dx] = slot+1
        lines = set()
        for i in range(self.size):
            if all(self.grid[i][j] for j in range(self.size)):
                lines.add(('row',i))
            if all(self.grid[j][i] for j in range(self.size)):
                lines.add(('col',i))
        for kind,i in lines:
            if kind == 'row':
                self.grid[i] = [0]*self.size
            else:
                for row in self.grid: row[i] = 0
        if lines:
            self.combo += 1
        else:
            self.combo = 0
        gained = len(shape)*10 + len(lines)*120*(1+min(self.combo,8))
        self.score += gained
        self.moves += 1
        self.tray[slot] = None
        if all(shape is None for shape in self.tray):
            self.refill()
        else:
            self.game_over = not self.can_play_any()
        return {'points': gained, 'lines': len(lines), 'combo': self.combo}

@dataclass
class SimonEngine:
    sequence: list[int] = field(default_factory=list)
    level: int = 0
    score: int = 0
    phase: str = 'preview'
    cursor: int = 0
    preview_index: int = -1
    phase_time: float = 0.0
    lives: int = 3
    def reset(self):
        self.sequence=[]; self.level=0; self.score=0; self.lives=3; self._next_round()
    def _next_round(self, rng=None):
        self.level+=1
        self.sequence.append((rng or random).randrange(4))
        self.phase='preview'; self.cursor=0; self.preview_index=-1; self.phase_time=0.0
    def update(self, dt):
        if self.phase != 'preview': return
        self.phase_time += dt
        step_len = max(0.48, 0.85-self.level*0.025)
        self.preview_index = int(self.phase_time/step_len)
        if self.preview_index >= len(self.sequence):
            self.phase='input'; self.preview_index=-1
    def press(self, tile):
        if self.phase != 'input' or not 0<=tile<=3: return 'ignored'
        if self.sequence[self.cursor] != tile:
            self.lives -= 1
            if self.lives<=0:
                self.phase='over'
            else:
                self.phase='preview'; self.phase_time=0; self.preview_index=-1; self.cursor=0
            return 'wrong'
        self.cursor+=1; self.score+=25*self.level
        if self.cursor==len(self.sequence):
            self.score+=100*self.level
            self._next_round()
            return 'level'
        return 'correct'

@dataclass
class GestureLatch:
    """Temporal hysteresis and stale-hand timeout; pixel-distance independent.

    ``update`` receives the thumb-index distance normalized by palm span.
    """
    close_ratio: float = 0.33
    open_ratio: float = 0.48
    stable_frames: int = 2
    state: bool = False
    candidate: bool = False
    frames: int = 0
    def update(self, ratio: float):
        requested = ratio < (self.open_ratio if self.state else self.close_ratio)
        if requested != self.candidate:
            self.candidate=requested; self.frames=1
        else:
            self.frames+=1
        if self.frames>=max(1,self.stable_frames):
            self.state=self.candidate
        return self.state
    def reset(self):
        self.state=False; self.candidate=False; self.frames=0

class PointDebouncer:
    """One event per press, and sustained hold cannot retrigger targets."""
    def __init__(self, cooldown=.14):
        self.last=0.0; self.active=False; self.cooldown=cooldown
    def edge(self, pressed, now):
        if not pressed: self.active=False; return False
        if not self.active and now-self.last>=self.cooldown:
            self.active=True; self.last=now; return True
        return False


def distance(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])
