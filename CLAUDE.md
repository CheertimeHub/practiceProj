# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Pygame practice project for learning game development with character movement controls.

## Development Environment
- Language: Python 3.x
- Main dependency: pygame

## Setup and Installation
Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Game
```bash
python main.py
```

## Code Architecture
The project uses object-oriented design:
- **Character class**: Handles player movement, collision detection with screen boundaries
- **Game loop**: 60 FPS with pygame clock
- **Controls**: Arrow keys or WASD for 4-directional movement
- **Screen**: 800x600 window with white background

## Key Features
- Free 4-directional character movement
- Screen boundary collision detection
- Dual control schemes (Arrow keys / WASD)
- ESC key to quit
