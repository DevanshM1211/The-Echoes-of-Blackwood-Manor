import time
import sys
import os
import random
import json
import argparse
import unittest
import platform
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set, Callable

# --- Dependencies Check ---
REQUIRED_LIBS = [("rich", "rich"), ("pyfiglet", "pyfiglet"), ("thefuzz", "thefuzz")]
missing = []

for lib, pip_name in REQUIRED_LIBS:
    try:
        __import__(lib)
    except ImportError:
        missing.append(pip_name)

if missing:
    print(f"Error: Missing dependencies: {', '.join(missing)}")
    print(f"Run: pip install {' '.join(missing)}")
    sys.exit(1)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.align import Align
from thefuzz import process
import pyfiglet

# --- Configuration ---
GAME_TITLE = "BLACKWOOD"
VERSION = "1.0.0"

# Inventory
MAX_INV_SLOTS = 5

# Resources & Costs
STARTING_SANITY = 100
STARTING_BATTERY = 100
BATTERY_RESTORE = 40
SANITY_RESTORE_AMULET = 25

# Drain Rates
DRAIN_MOVE = 1
DRAIN_DARKNESS = 5
DRAIN_WRONG_CODE = 3
DRAIN_HINT = 5
DRAIN_PHANTOM_ATTACK = 15

# Battery Consumption
BAT_DRAIN_NORMAL = 2
BAT_DRAIN_DARK = 5
BAT_COST_FLASH = 20

# Probabilities & Thresholds
CHANCE_EVENT = 0.15
CHANCE_PHANTOM_MOVE = 0.45
THRESH_HALLUCINATE = 60
THRESH_BROKEN = 30
FUZZY_CONFIDENCE = 80

# --- Audio / Visual Engine ---

class SoundEngine:
    enabled = True

    @staticmethod
    def play(freq=440, duration=100):
        if not SoundEngine.enabled: return
        
        def _beep():
            try:
                if platform.system() == "Windows":
                    import winsound
                    winsound.Beep(freq, duration)
                else:
                    # Fallback for *nix
                    print('\a', end='', flush=True)
            except Exception:
                pass # Silent fail if audio drivers issue
        
        threading.Thread(target=_beep, daemon=True).start()

    @staticmethod
    def pickup(): SoundEngine.play(800, 100)
    @staticmethod
    def error(): SoundEngine.play(150, 300)
    @staticmethod
    def danger(): SoundEngine.play(100, 500)
    @staticmethod
    def success(): 
        SoundEngine.play(600, 100)
        time.sleep(0.1)
        SoundEngine.play(800, 200)

class VisualFX:
    @staticmethod
    def shake(console: Console, intensity=3):
        """Simulates screen shake effect."""
        for _ in range(intensity):
            console.print("\n" * random.randint(1, 2))
            time.sleep(0.05)
            os.system('cls' if os.name == 'nt' else 'clear')

# --- Data Structures ---

@dataclass
class Item:
    id: str
    name: str
    desc: str
    takeable: bool = True
    interactable: bool = False
    hidden_text: Optional[str] = None
    value: int = 0

@dataclass
class Room:
    id: str
    name: str
    desc: str
    exits: Dict[str, str] = field(default_factory=dict) 
    items: List[Item] = field(default_factory=list)
    dark: bool = False
    locked: bool = False
    key_id: Optional[str] = None

@dataclass
class Player:
    room_id: str
    inventory: List[Item] = field(default_factory=list)
    visited: Set[str] = field(default_factory=set)
    journal: List[str] = field(default_factory=list)
    sanity: int = STARTING_SANITY
    battery: int = STARTING_BATTERY
    turns: int = 0
    alive: bool = True
    escaped: bool = False
    tutorial_done: bool = False
    difficulty: str = "normal"

@dataclass
class Phantom:
    room_id: str
    active: bool = False 
    stun_timer: int = 0

# --- Core Game Logic ---

class Game:
    def __init__(self, console: Console, seed: Optional[str] = None):
        if seed is None:
            seed = str(random.randint(1000, 9999))
        self.seed = seed
        random.seed(self.seed)
        
        self.console = console
        self.rooms: Dict[str, Room] = {}
        self.player = Player(room_id="gate") 
        self.phantom = Phantom(room_id="attic")
        
        self.safe_code = str(random.randint(100, 999))
        self.piano_solved = False
        self.history: List[str] = [] 
        
        # Command routing
        self.cmds: Dict[str, Callable[[str], None]] = {
            "go": self.move, "move": self.move, "walk": self.move,
            "look": self.look, "inspect": self.look, "read": self.look,
            "take": self.take, "get": self.take, "grab": self.take,
            "drop": self.drop, "use": self.use,
            "inv": self.show_inv, "i": self.show_inv, "inventory": self.show_inv,
            "map": self.show_map, "journal": self.show_journal, "j": self.show_journal,
            "save": self.save_state, "load": self.load_state,
            "help": self.show_help, "unlock": self.unlock, "play": self.play_piano,
            "undo": self.undo, "hint": self.hint,
            "listen": self.listen, "flash": self.flash,
            "mute": self.mute, "unmute": self.unmute
        }
        
        self._init_world()

    def _init_world(self):
        # Items
        flashlight = Item("flashlight", "Flashlight", "Rugged and heavy.")
        silver_key = Item("silver_key", "Silver Key", "Small key with a skull motif.")
        note = Item("note", "Crumpled Note", "Hastily scrawled numbers.", interactable=True, hidden_text=f"Code: {self.safe_code}")
        golden_key = Item("golden_key", "Golden Key", "Heavy gold key.", value=50)
        safe = Item("safe", "Safe", "Needs a 3-digit code.", takeable=False)
        piano = Item("piano", "Grand Piano", "Elegant keys covered in dust.", takeable=False)
        amulet = Item("amulet", "Jade Amulet", "Warm to the touch.", value=0)
        batteries = Item("batteries", "Spare Batteries", "Standard voltage.", value=10)
        sapphire = Item("sapphire", "Star Sapphire", "A brilliant gem worth a fortune.", value=500)
        gate_key = Item("gate_key", "Iron Key", "Rusty but solid.", value=0)
        
        # Map Layout
        self.rooms = {
            "gate": Room("gate", "Manor Gate", "Rain lashes down. A massive gate blocks North. An old [yellow]Iron Key[/] sits in the mud.",
                        exits={"north": "foyer"}, items=[gate_key]),
            "foyer": Room("foyer", "Foyer", "Grand entrance. Dust everywhere.", locked=True, key_id="gate_key",
                         exits={"north": "library", "east": "kitchen", "west": "bedroom", "south": "gate"},
                         items=[flashlight]),
            "kitchen": Room("kitchen", "Kitchen", "Smells of rot.", 
                           exits={"west": "foyer", "down": "basement"},
                           items=[note, batteries]),
            "library": Room("library", "Library", "Quiet rows of books.", 
                           exits={"south": "foyer", "up": "attic"},
                           items=[safe, piano]),
            "bedroom": Room("bedroom", "Master Bedroom", "Moonlight hits the mirror.", 
                           exits={"east": "foyer"},
                           items=[amulet]),
            "basement": Room("basement", "Basement", "Damp and cold.", dark=True, locked=True, key_id="silver_key",
                            exits={"up": "kitchen"},
                            items=[golden_key]),
            "attic": Room("attic", "Attic", "Cobwebs and memories.", 
                         exits={"down": "library"}),
            "garden": Room("garden", "Freedom", "Fresh air!", locked=True, key_id="golden_key",
                          exits={"north": "foyer"}),
            "study": Room("study", "Secret Study", "A hidden room.",
                         exits={"west": "library"}, items=[sapphire])
        }
        self.player.visited.add("gate")

    def _diff_mult(self):
        if self.player.difficulty == "story": return 0.5
        if self.player.difficulty == "hard": return 1.5
        return 1.0

    # --- Save/Undo System ---
    
    def _snapshot(self) -> str:
        """Serialize state for history/save."""
        # Convert objects to dicts
        player_dict = asdict(self.player)
        player_dict["visited"] = list(self.player.visited)
        data = {
            "player": player_dict,
            "phantom": asdict(self.phantom),
            "seed": self.seed, "safe_code": self.safe_code, "piano_solved": self.piano_solved,
            "rooms": {
                rid: {
                    "locked": r.locked, 
                    "items": [asdict(i) for i in r.items], 
                    "exits": r.exits
                } for rid, r in self.rooms.items()
            }
        }
        return json.dumps(data)

    def _restore(self, json_str: str):
        data = json.loads(json_str)
        self.seed = data["seed"]
        self.safe_code = data["safe_code"]
        self.piano_solved = data.get("piano_solved", False)
        
        # Restore Player
        self.player = Player(**data["player"])
        self.player.inventory = [Item(**i) for i in data["player"]["inventory"]]
        self.player.visited = set(data["player"].get("visited", []))
        
        # Restore Phantom
        self.phantom = Phantom(**data["phantom"])
        
        # Restore World
        for rid, r_data in data["rooms"].items():
            if rid in self.rooms:
                self.rooms[rid].locked = r_data["locked"]
                self.rooms[rid].items = [Item(**i) for i in r_data["items"]]
                self.rooms[rid].exits = r_data["exits"]

    def _record_action(self):
        """Push state to history stack."""
        self.history.append(self._snapshot())
        if len(self.history) > 10: self.history.pop(0)

    # --- Helpers ---
    
    def _room(self, rid: str = None) -> Room:
        return self.rooms[rid if rid else self.player.room_id]

    def _has(self, item_id: str) -> bool:
        return any(i.id == item_id for i in self.player.inventory)

    def _process_text(self, text: str) -> str:
        """Inject horror elements into text if sanity is low."""
        if self.player.sanity > THRESH_HALLUCINATE: return text
        
        swaps = {
            "dust": "ash", "quiet": "whispering", "shadows": "monsters", 
            "smell": "stench", "old": "ancient", "piano": "coffin", 
            "battery": "lifeline", "light": "hope", "safe": "vault"
        }
        
        words = text.split()
        out = []
        for w in words:
            clean = w.strip(".,!?:").lower()
            if clean in swaps and random.random() < 0.4:
                new_w = swaps[clean]
                if w[0].isupper(): new_w = new_w.capitalize()
                out.append(f"[bold magenta]{new_w}[/]")
            else:
                out.append(w)
        return " ".join(out)

    # --- Enemy AI ---

    def _update_phantom(self):
        # Stun check
        if self.phantom.stun_timer > self.player.turns: return
        
        # Activation logic
        if self.player.turns > 8 and not self.phantom.active and self.player.tutorial_done:
            self.phantom.active = True
            self.console.print("[bold magenta]Something has awakened in the house...[/]")
            SoundEngine.danger()

        if not self.phantom.active: return

        # Attack logic
        if self.phantom.room_id == self.player.room_id:
            VisualFX.shake(self.console)
            self.console.print(Panel("[bold red]THE PHANTOM SCREAMS![/]\n[italic]Your mind begins to fracture![/]", border_style="red"))
            SoundEngine.danger()
            dmg = int(DRAIN_PHANTOM_ATTACK * self._diff_mult())
            self.player.sanity -= dmg

        # Move logic
        if random.random() < CHANCE_PHANTOM_MOVE:
            current_r = self._room(self.phantom.room_id)
            if current_r.exits:
                self.phantom.room_id = random.choice(list(current_r.exits.values()))

    # --- Action Handlers ---

    def mute(self, _):
        SoundEngine.enabled = False
        self.console.print("[yellow]Audio Muted.[/]")

    def unmute(self, _):
        SoundEngine.enabled = True
        self.console.print("[green]Audio Enabled.[/]")
        SoundEngine.success()

    def flash(self, _):
        self._record_action()
        if not self._has("flashlight"):
            self.console.print("[red]No flashlight![/]")
            return
        
        cost = int(BAT_COST_FLASH * self._diff_mult())
        if self.player.battery < cost:
            self.console.print("[red]Battery too low![/]")
            SoundEngine.error()
            return

        self.player.battery -= cost
        self.console.print(f"[bold white]You unleash a blinding burst! (Battery -{cost})[/]")
        SoundEngine.play(1000, 200)

        # Check hit
        if self.phantom.room_id == self.player.room_id:
            self.console.print("[bold green]The Phantom shrieks and flees![/]")
            self.phantom.stun_timer = self.player.turns + 3
            # Teleport phantom away
            curr_phantom_room = self._room(self.phantom.room_id)
            if curr_phantom_room.exits:
                self.phantom.room_id = random.choice(list(curr_phantom_room.exits.values()))
            SoundEngine.success()
        else:
            self.console.print("[italic]Nothing but dust moths.[/]")

    def listen(self, _):
        self._record_action()
        self.console.print("[italic]Listening...[/]")
        
        curr = self._room()
        if self.phantom.room_id == curr.id:
            self.console.print("[bold red]IT IS HERE![/]")
            return
        
        is_near = any(self.phantom.room_id == exit_id for exit_id in curr.exits.values())
        
        if is_near:
            self.console.print("[bold yellow]You hear shuffling nearby.[/]")
        else:
            self.console.print("[dim]Silence.[/]")

    def move(self, direction: str):
        self._record_action()
        curr = self._room()
        
        if direction not in curr.exits:
            self.console.print(f"[yellow]Can't go '{direction}'.[/]")
            SoundEngine.error()
            return

        dest = self._room(curr.exits[direction])

        if dest.locked:
            if dest.key_id and self._has(dest.key_id):
                self.console.print(f"[green]Unlocked {dest.name}.[/]")
                dest.locked = False
                SoundEngine.success()
                if dest.id == "foyer": 
                    self.player.tutorial_done = True
            else:
                self.console.print(f"[red]Locked.[/]")
                SoundEngine.error()
                return

        self.player.room_id = dest.id
        self.player.visited.add(dest.id)
        self.player.turns += 1
        
        self._update_status()
        self._update_phantom()

        # Light check
        if dest.dark:
            if not self._has("flashlight"):
                self.console.print("[bold red]Darkness consumes you.[/]")
                self.player.alive = False
            elif self.player.battery <= 0:
                self.console.print("[bold red]Flashlight dead. You die.[/]")
                self.player.alive = False

    def take(self, target: str):
        self._record_action()
        target = target.replace("up ", "")
        room = self._room()
        
        # Find item
        item = next((i for i in room.items if i.name.lower() == target or i.id == target), None)
        
        if not item or not item.takeable:
            self.console.print(f"[yellow]Can't take '{target}'.[/]")
            return
        
        if len(self.player.inventory) >= MAX_INV_SLOTS:
            self.console.print("[red]Inventory full![/]")
            return

        room.items.remove(item)
        self.player.inventory.append(item)
        self.console.print(f"[green]Taken: {item.name}[/]")
        SoundEngine.pickup()

    def use(self, target: str):
        self._record_action()
        # Fuzzy check for item names
        if "battery" in target or "batteries" in target:
            bat = next((i for i in self.player.inventory if i.id == "batteries"), None)
            if bat:
                self.player.inventory.remove(bat)
                self.player.battery = min(100, self.player.battery + BATTERY_RESTORE)
                self.console.print(f"[green]Recharged. Battery: {self.player.battery}%[/]")
                SoundEngine.success()
            else:
                self.console.print("[red]No batteries.[/]")
                
        elif "amulet" in target:
            amu = next((i for i in self.player.inventory if i.id == "amulet"), None)
            if amu:
                self.player.inventory.remove(amu)
                self.player.sanity = min(100, self.player.sanity + SANITY_RESTORE_AMULET)
                self.console.print(f"[green]Sanity restored.[/]")
                SoundEngine.success()
            else:
                self.console.print("[red]No amulet.[/]")
        else:
            self.console.print(f"[yellow]Can't use '{target}' directly.[/]")

    def unlock(self, target: str):
        self._record_action()
        # Specific puzzle: Library Safe
        if "safe" in target and self.player.room_id == "library":
            code = input("Code: ")
            if code == self.safe_code:
                self.console.print("[green]Safe opens![/]")
                self._room().items.append(Item("silver_key", "Silver Key", "Small key.", value=0))
                SoundEngine.success()
            else:
                self.console.print("[red]Wrong.[/]")
                self.player.sanity -= int(DRAIN_WRONG_CODE * self._diff_mult())
                SoundEngine.error()
        else:
            self.console.print("[yellow]Nothing to unlock.[/]")

    def play_piano(self, target: str):
        self._record_action()
        if "piano" in target and self.player.room_id == "library":
            if self.piano_solved:
                self.console.print("Already solved.")
                return
            
            notes = input("Notes: ").strip().upper()
            if notes in ["DAD", "D-A-D"]:
                self.console.print("[cyan]A hidden door slides open to the East![/]")
                self.rooms["library"].exits["east"] = "study"
                self.piano_solved = True
                SoundEngine.success()
            else:
                self.console.print("[red]Discordant noise![/]")
                self.player.sanity -= 2
                SoundEngine.error()
        else:
            self.console.print("[yellow]No piano.[/]")

    def look(self, target: str):
        if not target or target in ["room", "around"]: return
        
        # Check inventory + room items
        all_items = self.player.inventory + self._room().items
        for item in all_items:
            if item.name.lower() == target or item.id == target:
                desc = self._process_text(item.desc)
                self.console.print(Panel(desc, title=item.name, border_style="cyan"))
                
                if item.interactable and item.hidden_text:
                    self.console.print(f"[italic] > {item.hidden_text}[/]")
                    if item.hidden_text not in self.player.journal:
                        self.player.journal.append(f"{item.name}: {item.hidden_text}")
                return
        self.console.print(f"[yellow]Can't see '{target}'.[/]")

    def undo(self, _):
        if not self.history:
            self.console.print("[red]Nothing to undo.[/]")
            return
        
        prev = self.history.pop()
        self._restore(prev)
        self.console.print("[bold yellow]⏪ Time Rewind.[/]")
        SoundEngine.play(300, 300)

    def hint(self, _):
        self._record_action()
        cost = int(DRAIN_HINT * self._diff_mult())
        self.player.sanity -= cost
        
        rid = self.player.room_id
        hint = "Explore."
        
        # Contextual Hints
        if rid == "gate": hint = "Unlock the North door with the key."
        elif rid == "foyer": 
            if self.rooms["garden"].locked: hint = "Golden Key is in the Basement."
        elif rid == "kitchen" and not any(i.id == "note" for i in self.player.inventory): hint = "Take the note."
        
        self.console.print(Panel(hint, title="HINT", border_style="magenta"))

    def drop(self, target: str):
        self._record_action()
        found = next((i for i in self.player.inventory if i.name.lower() == target), None)
        if found:
            self.player.inventory.remove(found)
            self._room().items.append(found)
            self.console.print(f"[yellow]Dropped: {found.name}[/]")
        else:
            self.console.print("[red]Not carrying that.[/]")

    def show_inv(self, _):
        t = Table(title="Inventory", box=box.SIMPLE)
        t.add_column("Item"); t.add_column("Desc")
        for i in self.player.inventory: t.add_row(i.name, i.desc)
        self.console.print(t)

    def show_journal(self, _): 
        c = "\n".join([f"- {e}" for e in self.player.journal]) if self.player.journal else "Empty."
        self.console.print(Panel(c, title="Journal", border_style="blue"))

    def show_map(self, _):
        def r(rid, l): 
            if rid == self.player.room_id: return "[bold red on white] YOU [/]"
            if rid in self.player.visited: return f"[green][{l[:3]}][/]"
            return "[dim][?][/]"
        
        study = f"{r('study','Std')}" if "study" in self.player.visited else "   "
        m = f"      {r('attic','Att')}\n        |\n      {r('library','Lib')}-{study}\n        |\n{r('bedroom','Bed')}-{r('foyer','Foy')}-{r('kitchen','Kit')}\n        |      |\n      {r('garden','Gar')}  {r('basement','Bas')}"
        self.console.print(Panel(m, title="Map", border_style="blue", width=40))

    def save_state(self, _): 
        with open("save.json", "w") as f: f.write(self._snapshot())
        self.console.print("[green]Saved.[/]")

    def load_state(self, _):
        if os.path.exists("save.json"): 
            with open("save.json", "r") as f: self._restore(f.read())
            self.console.print("[green]Loaded.[/]")

    def show_help(self, _):
        t = Table(title="Commands")
        t.add_column("Cmd"); t.add_column("Desc")
        t.add_row("go", "Move"); t.add_row("take", "Pickup"); t.add_row("use", "Action")
        t.add_row("flash", "Stun Phantom"); t.add_row("listen", "Detect Danger")
        self.console.print(t)

    def _update_status(self):
        mult = self._diff_mult()
        self.player.sanity -= int(DRAIN_MOVE * mult)
        
        if self._room().dark and self._has("flashlight"):
            self.player.battery = max(0, self.player.battery - int(BAT_DRAIN_DARK * mult))
        elif self._has("flashlight"):
             self.player.battery = max(0, self.player.battery - int(BAT_DRAIN_NORMAL * mult))

    def _render_ui(self):
        san = max(0, self.player.sanity)
        bat = max(0, self.player.battery)
        
        s_col = "green" if san > 70 else "red"
        b_col = "green" if bat > 50 else "red"
        
        def bar(v, c): 
            blocks = int(v/10)
            return f"[{c}]{'█'*blocks}{'░'*(10-blocks)}[/] {v}%"
        
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1); grid.add_column(ratio=1)
        grid.add_row(f"Sanity: {bar(san, s_col)}", f"Battery: {bar(bat, b_col)}")
        self.console.print(Panel(grid, style="white", box=box.ROUNDED))

    def _select_difficulty(self):
        self.console.print(Panel("SELECT DIFFICULTY\n1. Story\n2. Normal\n3. Hardcore", title="SETUP"))
        while True:
            c = input("Choice (1-3): ").strip()
            if c == "1": return "story"
            if c == "2": return "normal"
            if c == "3": return "hard"

    def start(self):
        self.console.clear()
        title = pyfiglet.figlet_format(GAME_TITLE, font="small")
        self.console.print(Panel(Align.center(f"[bold white]{title}[/]\n[dim]Seed: {self.seed}[/]"), border_style="cyan"))
        
        self.player.difficulty = self._select_difficulty()
        self.console.clear()
        
        # Tutorial
        self.console.print(Panel("[bold yellow]PROLOGUE[/]\nYou are at the Manor Gate. Get inside.\nTry: [bold white]look[/], [bold white]take iron key[/], [bold white]unlock gate[/].", border_style="yellow"))

        while self.player.alive and not self.player.escaped:
            if self.player.room_id == "garden":
                self.player.escaped = True
                break

            self._render_ui()
            
            room = self._room()
            has_light = self._has("flashlight")
            
            if room.dark and not has_light:
                self.console.print(Panel("[red]It is pitch black.[/]", title="???", border_style="red"))
            else:
                desc = self._process_text(room.desc)
                vis_items = ", ".join([f"[yellow]{i.name}[/]" for i in room.items])
                if vis_items: desc += f"\n\n[bold]Items:[/]\n{vis_items}"
                desc += f"\n\n[bold]Exits:[/]\n{', '.join(room.exits.keys()).upper()}"
                
                # Tutorial hint overlay
                if not self.player.tutorial_done and room.id == "gate":
                    desc += "\n\n[bold white on blue] TUTORIAL: Type 'take iron key' then 'go north'. [/]"

                style = "magenta" if self.player.sanity < THRESH_BROKEN else "cyan"
                self.console.print(Panel(desc, title=room.name, border_style=style))

            try: inp = input("\n> ").strip().lower()
            except EOFError: break
            if not inp: continue

            parts = inp.split()
            cmd = parts[0]
            arg = " ".join(parts[1:])

            # Fuzzy matching execution
            if cmd in self.cmds:
                self.cmds[cmd](arg)
            else:
                best, score = process.extractOne(cmd, self.cmds.keys())
                if score >= FUZZY_CONFIDENCE:
                    self.console.print(f"[dim italic]Did you mean '{best}'?[/]")
                    self.cmds[best](arg)
                else:
                    self.console.print("[dim]Unknown command.[/]")
                    SoundEngine.error()
            
            if self.player.sanity <= 0:
                self.console.print("[red]Your mind shatters.[/]")
                self.player.alive = False

        self._game_over()

    def _game_over(self):
        if self.player.escaped:
            score = self.player.sanity * 10 - self.player.turns * 2 + sum(i.value for i in self.player.inventory)
            
            has_gem = self._has("sapphire")
            title = "WEALTHY SURVIVOR" if has_gem else "ESCAPED"
            color = "gold1" if has_gem else "green"
            
            txt = pyfiglet.figlet_format(title, font="small")
            self.console.print(Panel(f"[bold {color}]{txt}[/]\nScore: {score}", border_style=color))
            SoundEngine.success()
        else:
            txt = pyfiglet.figlet_format("DIED")
            self.console.print(Panel(f"[bold red]{txt}[/]", border_style="red"))
            SoundEngine.danger()

# --- Entry Point ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=str)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    
    if args.test:
        # Basic integrity tests
        sys.argv = [sys.argv[0]]
        unittest.main()
    else:
        game = Game(Console(no_color=args.no_color), seed=args.seed)
        game.start()