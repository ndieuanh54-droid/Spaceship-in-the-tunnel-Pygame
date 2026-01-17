# Spaceship-in-the-tunnel-Pygame
# Tunnel Shooter (Python / Pygame)

Tunnel Shooter is a 2D scrolling arcade game made with **Python** and **Pygame**.
The player controls a spaceship inside a procedurally generated tunnel and must survive by avoiding obstacles and shooting enemies.

## 🎮 Gameplay
- The tunnel scrolls continuously from right to left.
- The player moves up and down to stay inside the corridor.
- Obstacles and enemies appear depending on the current level.

## ⭐ Features
- Procedural tunnel generation (random corridor)
- Scrolling space background with tiled textures
- Obstacles:
  - Planets (static)
  - Asteroids (moving + crash animation)
  - UFO enemies (shoot green bullets)
- Shooting system (spaceship bullets)
- Health system with **5 hearts**
  - Wall / planet / asteroid hit → -0.5 heart
  - UFO bullet hit → -0.5 heart
  - Crash into UFO → -1 heart
- Level system based on score (difficulty increases automatically)

## 🕹 Controls
- **UP / DOWN** → Move the spaceship
- **SPACE** → Shoot
- **R** → Restart the game

## 📈 Levels
Levels increase automatically based on score:
- **Level = 1 + score // 300** (max 5)

Example:
- Level 1: Planets only
- Level 2: Adds asteroids + faster speed
- Level 3: Adds UFOs + heart pickups
- Level 4: Faster
- Level 5: Fastest / hardest


```bash
pip inst
