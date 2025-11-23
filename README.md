# The Echoes of Blackwood Manor (Master Edition)

A psychological horror text adventure set in the haunted Blackwood Manor. Explore, survive, and escape as you unravel the secrets of the manor and face its supernatural dangers.

---

## Game Overview
**The Echoes of Blackwood Manor** is a story-driven, object-oriented text adventure game. You play as a lone explorer trapped in a cursed mansion, where every decision affects your survival. The game blends classic adventure mechanics with procedural horror, sanity management, and a dynamic enemy.

---

## Goals & Objectives
- **Escape the Manor:** Explore rooms, collect items, solve puzzles.
- **Survive the Phantom:** Avoid or stun the supernatural enemy.
- **Manage Sanity & Battery:** Keep your sanity and flashlight battery charged.
- **Discover Secrets:** Find hidden rooms, clues, and the rare Star Sapphire for a special ending.

---

## Challenges
- **Sanity Drain:** Low sanity causes hallucinations and distorts game text.
- **Battery Management:** Your flashlight is essential in dark rooms.
- **Inventory Limits:** Carry up to 5 items.
- **Locked Rooms & Puzzles:** Find keys and solve puzzles to progress.
- **The Phantom:** Moves unpredictably and can attack.
- **Procedural Events:** Random events and fuzzy command matching.

---

## Key Features
- Interactive tutorial at the start
- Fuzzy command matching (typos are understood)
- Difficulty selection: Story, Normal, Hardcore
- Combat system: Use `flash` to stun the Phantom
- Sound effects: Use `mute` or `unmute`
- Undo system: Type `undo` to rewind time
- Procedural horror: Sanity rewrites game text

---

## Installation & Setup
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python adventure_game.py
```

---

## How to Play
1. **Start the Game**
   - Run `python adventure_game.py` in your terminal.
   - Select your difficulty: Story, Normal, or Hardcore.
2. **Basic Controls**
   - Use commands like `go north`, `take iron key`, `look`, `use flashlight`.
   - Fuzzy matching allows for minor typos.
3. **Objective**
   - Escape by exploring, solving puzzles, and avoiding the Phantom.
   - Collect items, unlock doors, and manage your sanity and battery levels.
4. **Combat & Survival**
   - Use `flash` to stun the Phantom.
   - Listen for danger with `listen`.
   - Recharge battery with spare batteries, restore sanity with the amulet.
5. **Inventory & Items**
   - Carry up to 5 items.
   - Use `inventory` to view, `drop <item>` to drop.
6. **Saving & Loading**
   - Use `save`, `load`, and `undo` for progress management.
7. **Map & Journal**
   - Use `map` and `journal` for navigation and clues.
8. **Winning & Losing**
   - Win by escaping to the garden; lose if sanity or battery runs out, or the Phantom attacks.

---

## System Requirements
- Python 3.8 or newer
- macOS, Windows, or Linux

---

## Troubleshooting
- If you see a missing library error, run: `pip install -r requirements.txt`
- For sound issues, use `mute` or `unmute` in-game.
- For permission errors, run the terminal as administrator or use a virtual environment.

---

## Complete Example Gameplay
```
$ python adventure_game.py
SELECT DIFFICULTY
1. Story
2. Normal
3. Hardcore
Choice (1-3): 2

PROLOGUE
You are at the Manor Gate. Get inside.
Try: look, take iron key, unlock gate.

> look
Rain lashes down. A massive gate blocks North. An old Iron Key sits in the mud.
Items:
Iron Key
Exits:
NORTH

> take iron key
Taken: Iron Key

> go north
Unlocked Foyer.

> look
Grand entrance. Dust everywhere.
Items:
Flashlight
Exits:
NORTH, EAST, WEST, SOUTH

> take flashlight
Taken: Flashlight

> go east
You enter the Kitchen. Smells of rot.
Items:
Crumpled Note, Spare Batteries
Exits:
WEST, DOWN

> take note
Taken: Crumpled Note

> look note
Code: 472

> go down
Locked.

> go west
You return to the Foyer.

> go north
You enter the Library. Quiet rows of books.
Items:
Safe, Grand Piano
Exits:
SOUTH, UP

> unlock safe
Code: 472
Safe opens!
Silver Key added to the room.

> take silver key
Taken: Silver Key

> go up
You enter the Attic. Cobwebs and memories.
Exits:
DOWN

> listen
Silence.

> go down
You return to the Library.

> play piano
Notes: DAD
A hidden door slides open to the East!

> go east
You enter the Secret Study. A hidden room.
Items:
Star Sapphire
Exits:
WEST

> take star sapphire
Taken: Star Sapphire

> go west
You return to the Library.

> go south
You return to the Foyer.

> go south
You return to the Manor Gate.

> go north
You enter the Foyer.

> go west
You enter the Master Bedroom. Moonlight hits the mirror.
Items:
Jade Amulet
Exits:
EAST

> take amulet
Taken: Jade Amulet

> use amulet
Sanity restored.

> inventory
Inventory:
- Iron Key
- Flashlight
- Crumpled Note
- Silver Key
- Star Sapphire
- Jade Amulet

> map
[Shows explored map]

> save
Saved.

> quit
```

---

## Credits & License
- Author: Devansh Mehrotra
- License: MIT

## Contact & Support
- For issues or suggestions, open an issue on the GitHub repository: https://github.com/DevanshM1211/The-Echoes-of-Blackwood-Manor
- For direct contact: devanshmehrotra@gmail.com

---