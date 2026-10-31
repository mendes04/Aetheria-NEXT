# AETHERIA NEXT — Motion Arcade Edition

A desktop Python/Pygame game hub that preserves the original **Aetheria Grand Prix** exhibition game and adds a modern home page, game catalogue, settings, and **four playable arcade games**. Includes MediaPipe camera-based gesture control, mouse/keyboard support, local best scores and LAN score syncing.

> **Status:** Source-level upgrade and headless game-logic tests completed. Actual visual performance, camera-tracking accuracy, audio output and two-laptop networking have **not yet been tested on a physical Windows system**. See `TEST_REPORT.md`.

## What's included

The original code lives in `aetheria_synth.py` (extended, not rewritten). The original copy is preserved in `archive/aetheria_synth_original.py` for comparison. The 8 existing activities remain available in the **Game Library** and the original floating-card screen is still accessible using **Legacy Hub** (`K`).

| Existing modes (preserved) | Added modes |
| --- | --- |
| Freestyle Studio (instruments) | **Block Nova:** 8×8 block-placement puzzler with row/column clears, combos and a three-piece tray |
| Piano Tiles | **Neon Reactor:** time-limited reflex grid with target orbs, decoys, health and streak scoring |
| Synth Blade | **Echo Matrix:** increasing Simon-style memory sequence with pattern playback |
| Grand Orchestra / Choir | **Star Pilot:** hand-steered ship, incoming pickups and hazards, score streaks and shields |
| Celestial Singularity | |
| Sonic Slingshot | |
| Loop Station / AI Music Assistant | |
| Live Performance / Musical DNA | |

Original local **Wall of Fame** boards, perspective visual effects, orchestration, generated sounds, wrist HUD, operator panel, exhibition session timer, and UDP peer score syncing are kept. The four new games also have persistent personal bests and share these bests over UDP in the existing peer heartbeat. The original master leaderboard remains the master board for legacy games; new bests appear on game cards.

## Install & run on Windows

Recommended: **64-bit Python 3.11 or 3.12**, webcam for hand input, and Windows 10/11.

1. Unzip the archive and open the `Aetheria_Arcade_Upgrade` folder.
2. Double-click **`run_windows.bat`**. On the first run it creates `.venv` and installs packages from `requirements.txt`.
3. On first camera launch, the official **MediaPipe Hand Landmarker** `.task` asset is fetched from Google and stored next to `aetheria_synth.py`. An internet connection is needed once. It is not included in the ZIP.
4. If no camera or model is available, the launcher continues in **mouse fallback** mode. New games and menus work with mouse/keyboard, and the original modes offer basic mouse-as-hand emulation.

Manual installation:

```powershell
cd Aetheria_Arcade_Upgrade
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python aetheria_synth.py
```

If PowerShell blocks activation, directly run `.\.venv\Scripts\python.exe aetheria_synth.py`.

## Control guide

| Key / Input | Action |
| --- | --- |
| **Pinch** thumb and index finger, then release | Select a menu item / activate a new-game target |
| **Move hand / index fingertip** | Hover or steer Star Pilot |
| **Mouse left-click** | Select and tap; original game mouse-adapter pinch |
| **Mouse right-click** | Fist in original mouse-adapter modes |
| **Shift + mouse** | Left-hand designation for Synth Blade mouse-adapter mode |
| **G** | Game library |
| **T** | Settings |
| **H** | Help / instructions |
| **K** | Original floating portal hub |
| **1–6** | Original freestyle, tiles, blade, orchestra, singularity, slingshot |
| **7–0** | Block Nova, Neon Reactor, Echo Matrix, Star Pilot |
| **P / L / S** | Original Loop Station / Live Performance / leaderboard |
| **Q / W / E** | Block Nova shape-tray selection |
| **1–4** (while Echo Matrix is open) | Memory pad input |
| **Left / Right arrows** | Star Pilot keyboard steering |
| **SPACE** | Retry finished new-game run; original per-mode interaction |
| **ESC** | Back to home (ESC on home exits); unpause to home |
| **F1** | Pause / resume |
| **F** | Toggle fullscreen |
| **O / F11 / F12** | Original kiosk panel / request LAN sync / reset session timer |

## Accuracy tuning

Open **Settings** and choose an input mode: `CAMERA` (hands only), `HYBRID` (hands and mouse fallback), or `MOUSE` (no webcam). `CAMERA QUALITY` trades processing speed for fingertip definition: **FAST** at 320×240, **BALANCED** at 480×360, or **PRECISE** at 640×480. `PINCH SENSITIVITY` controls thumb-index closure thresholds relative to palm width. The new latching logic holds a recognized pinch for two consecutive frames and uses a separate opening threshold to reduce jitter. Existing One Euro landmark smoothing remains enabled, and dropped hand detections expire to avoid ghost clicks.

The model accuracy gains are design improvements, **not a measured benchmark**. Real results depend on lighting, camera, distance, hardware and frame-rate. For best results, use a bright room with a plain background, keep both hands visible, avoid backlighting, and tune sensitivity gradually. Test under the same 1–2 m booth setup planned for your exhibition.

## Multiplayer / LAN

Both computers must be on the same trusted local network and allow **UDP port 37020** in Windows Defender Firewall. Start Aetheria on both laptops; the existing peer link and scoreboard continue to work. The four new game bests are carried in LAN heartbeat/sync packets; personal bests are also persisted locally.

**Privacy:** Webcam frames are processed locally by the MediaPipe model; the application does not upload camera video. LAN broadcasts exchange player IDs, current game and score, and leaderboard/best-score data. Use only on a trusted LAN.

## Project files

- `aetheria_synth.py` — original game engine, retained and extended to integrate menus, new modes and vision changes.
- `arcade_expansion.py` — modern Pygame screens, settings, score persistence and four game UIs.
- `arcade_logic.py` — unit-testable Block Nova rules, Simon sequence engine and gesture debounce/hysteresis.
- `tests/` — game-rule and headless rendering-contract tests.
- `archive/aetheria_synth_original.py` — byte-for-byte reference copy of the attached original.
- `requirements.txt`, `run_windows.bat`, `.gitignore`, `TEST_REPORT.md` — setup and verification assets.

To run tests (after installing pytest, no camera required):

```powershell
python -m pip install pytest
python -m pytest -q tests
```

## GitHub repository

Source repository: https://github.com/mendes04/Aetheria-NEXT

The full game is intended to be committed at the repository root. The original source is preserved under `archive/`.
