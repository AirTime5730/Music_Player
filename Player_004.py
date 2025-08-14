import os
import random
import time
import re
import tkinter as tk
from tkinter import ttk
import pygame
from mutagen.mp3 import MP3
from collections import defaultdict

# --- Settings ---
PATH = input("Enter the path to your music folder here: ")

# Color palette
DARK_BG = "#1E1E2E"
PANEL_BG = "#2A2A40"
ACCENT_COLOR = "#4ADE80"
TEXT_COLOR = "#F5F5F5"
SECONDARY_TEXT = "#A0A0B0"
BUTTON_HOVER = "#3FCF6D"

# --- Initialize mixer ---
pygame.mixer.init()
current_song = None
paused = False
start_time = 0
song_length = 0  # seconds

# Queue system
play_queue = []
queue_origin = None  # (folder_path, index_in_folder) of the song before queue started

# --- Formatting helper ---
def format_song_title(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    name = re.sub(r"(?<!^)([A-Z])", r" \1", name)
    name = name.replace("_", " ").replace("-", " ")
    return name.title()

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def get_song_length(path):
    audio = MP3(path)
    return audio.info.length

# --- Core playback ---
def play_song_from_path(path, position=0):
    global current_song, paused, start_time, song_length
    current_song = os.path.basename(path)
    song_length = get_song_length(path)
    pygame.mixer.music.load(path)
    pygame.mixer.music.play(start=position)
    paused = False
    start_time = time.time() - position
    display_name = format_song_title(current_song)
    song_title_label.config(text=display_name)
    play_pause_button.config(text="⏸ Pause")
    update_time_label()

def toggle_play_pause():
    global paused, start_time
    if pygame.mixer.music.get_busy() and not paused:
        pygame.mixer.music.pause()
        paused = True
        play_pause_button.config(text="▶ Play")
    elif paused:
        pygame.mixer.music.unpause()
        paused = False
        start_time = time.time() - (seek_bar.get() / 100) * song_length
        play_pause_button.config(text="⏸ Pause")

def seek(seconds_delta):
    if current_song and song_length > 0:
        elapsed = time.time() - start_time if not paused else (seek_bar.get() / 100) * song_length
        new_pos = max(0, min(elapsed + seconds_delta, song_length))
        path = find_path_of_current_selection()
        if path:
            play_song_from_path(path, position=new_pos)

def on_seek(event):
    path = find_path_of_current_selection()
    if path and song_length > 0:
        percent = seek_bar.get()
        new_pos = (percent / 100) * song_length
        play_song_from_path(path, position=new_pos)

def update_time_label():
    if song_length > 0:
        if paused:
            elapsed = (seek_bar.get() / 100) * song_length
        else:
            elapsed = time.time() - start_time
        elapsed = max(0, min(elapsed, song_length))
        time_label.config(text=f"{format_time(elapsed)} / {format_time(song_length)}")

def update_seek_bar():
    if song_length > 0:
        if not paused and pygame.mixer.music.get_busy():
            elapsed = time.time() - start_time
            percent = (elapsed / song_length) * 100
            seek_bar.set(percent)
        elif not paused and current_song and not pygame.mixer.music.get_busy():
            handle_song_end()
    update_time_label()
    root.after(500, update_seek_bar)

# --- Queue handling ---
def handle_song_end():
    global play_queue, queue_origin
    if play_queue:
        next_song = play_queue.pop(0)
        update_queue_view()
        play_song_from_path(next_song)
    elif queue_origin:
        folder, idx = queue_origin
        if folder in folder_structure and idx + 1 < len(folder_structure[folder]):
            play_song_from_path(folder_structure[folder][idx + 1])
        queue_origin = None
    else:
        play_next_in_folder()

def update_queue_view():
    queue_tree.delete(*queue_tree.get_children())
    for song_path in play_queue:
        queue_tree.insert("", "end", text=format_song_title(song_path), values=(song_path,))

# --- Tree building ---
folder_structure = defaultdict(list)
folder_nodes = {}

def scan_music_directory(base_path):
    for root_dir, dirs, files_in_dir in os.walk(base_path):
        rel_dir = os.path.relpath(root_dir, base_path)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        if rel_dir == ".":
            parent_id = ""
        else:
            parent_key = os.path.dirname(rel_dir)
            parent_id = "" if parent_key in (".", "") else folder_nodes.get(parent_key, "")

        folder_display = os.path.basename(root_dir) if rel_dir != "." else os.path.basename(base_path)
        folder_id = tree.insert(parent_id, "end", text=folder_display, values=(root_dir, depth, -1))
        folder_nodes[rel_dir] = folder_id

        song_index = 0
        for file in sorted(files_in_dir):
            if file.endswith(".mp3"):
                full_path = os.path.join(root_dir, file)
                folder_structure[root_dir].append(full_path)
                tree.insert(folder_id, "end", text=format_song_title(file),
                            values=(full_path, depth + 1, song_index))
                song_index += 1

# --- Tree selection ---
def on_tree_select(event):
    pass

def find_path_of_current_selection():
    sel = tree.selection()
    if not sel:
        return None
    fullpath, _, index = tree.item(sel[0], "values")
    return fullpath if int(index) >= 0 else None

def play_selected_song():
    path = find_path_of_current_selection()
    if path:
        play_song_from_path(path)

# --- Queue add/remove ---
def add_to_queue():
    global queue_origin
    sel_path = find_path_of_current_selection()
    if not sel_path:
        return
    if current_song and not queue_origin:
        for folder, songs in folder_structure.items():
            for idx, song_path in enumerate(songs):
                if os.path.basename(song_path) == current_song:
                    queue_origin = (folder, idx)
                    break
    play_queue.append(sel_path)
    update_queue_view()

def remove_from_queue():
    sel = queue_tree.selection()
    if not sel:
        return
    for item_id in sel:
        song_path = queue_tree.item(item_id, "values")[0]
        if song_path in play_queue:
            play_queue.remove(song_path)
    update_queue_view()

# --- Folder navigation based on current playing song ---
def play_next_in_folder():
    if not current_song:
        return
    for folder, songs in folder_structure.items():
        for idx, song_path in enumerate(songs):
            if os.path.basename(song_path) == current_song:
                if idx + 1 < len(songs):
                    play_song_from_path(songs[idx + 1])
                return

def play_prev_in_folder():
    if not current_song:
        return
    for folder, songs in folder_structure.items():
        for idx, song_path in enumerate(songs):
            if os.path.basename(song_path) == current_song:
                if idx - 1 >= 0:
                    play_song_from_path(songs[idx - 1])
                return

# --- Navigation keys for selection ---
def move_selection(direction):
    sel = tree.selection()
    if not sel:
        return
    item_id = sel[0]
    siblings = tree.get_children(tree.parent(item_id))
    cur_pos = siblings.index(item_id)
    new_pos = cur_pos + direction
    if 0 <= new_pos < len(siblings):
        tree.selection_set(siblings[new_pos])
        tree.see(siblings[new_pos])

# --- Key press handler ---
def on_key_press_tree(event):
    key = event.keysym.lower()
    if key == "s":
        move_selection(1)
    elif key == "w":
        move_selection(-1)
    elif key == "space":
        toggle_play_pause()
    elif key == "a":
        seek(-5)
    elif key == "d":
        seek(5)
    elif key == "r":
        randomize_and_play()
    elif key == "p":
        play_selected_song()
    elif key == "q":
        add_to_queue()
    elif key == "x":
        remove_from_queue()

# --- Random play ---
def randomize_and_play():
    all_songs = sum(folder_structure.values(), [])
    if all_songs:
        play_song_from_path(random.choice(all_songs))

# --- Close ---
def on_close():
    pygame.mixer.music.stop()
    root.destroy()

# --- UI Setup ---
root = tk.Tk()
root.title("🎵 Music Player")
root.geometry("750x550")
root.configure(bg=DARK_BG)
root.protocol("WM_DELETE_WINDOW", on_close)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview", background=PANEL_BG, fieldbackground=PANEL_BG,
                foreground=TEXT_COLOR, rowheight=25, borderwidth=0)
style.map("Treeview", background=[("selected", ACCENT_COLOR)],
          foreground=[("selected", DARK_BG)])
style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8,
                relief="flat", background=ACCENT_COLOR, foreground=DARK_BG)
style.map("TButton", background=[("active", BUTTON_HOVER)])
style.configure("TScale", background=DARK_BG, troughcolor="#444", sliderthickness=14)

main_frame = tk.Frame(root, bg=DARK_BG)
main_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Left panel
left_frame = tk.Frame(main_frame, bg=PANEL_BG, width=300, relief="flat", bd=0)
left_frame.pack(side="left", fill="both", padx=(0, 10))

song_title_label = tk.Label(left_frame, text="No song playing", fg=TEXT_COLOR,
                            bg=PANEL_BG, font=("Segoe UI", 14, "bold"), wraplength=280)
song_title_label.pack(pady=20)

play_pause_button = ttk.Button(left_frame, text="▶ Play", command=toggle_play_pause)
play_pause_button.pack(pady=10)

time_label = tk.Label(left_frame, text="0:00 / 0:00", font=("Segoe UI", 10),
                      bg=PANEL_BG, fg=SECONDARY_TEXT)
time_label.pack()

seek_bar = ttk.Scale(left_frame, from_=0, to=100, orient="horizontal")
seek_bar.pack(fill="x", padx=20, pady=10)
seek_bar.bind("<ButtonRelease-1>", on_seek)

# Right panel
right_frame = tk.Frame(main_frame, bg=PANEL_BG)
right_frame.pack(side="right", fill="both", expand=True)

# Song list
tree = ttk.Treeview(right_frame, columns=("fullpath", "depth", "index"), show="tree")
tree.pack(expand=True, fill="both", padx=10, pady=(10, 5))
scan_music_directory(PATH)

# Queue list
queue_tree = ttk.Treeview(right_frame, columns=("fullpath",), show="tree", height=6)
queue_tree.pack(fill="x", padx=10, pady=(0, 10))

randomize_button = ttk.Button(right_frame, text="🔀 Random", command=randomize_and_play)
randomize_button.pack(side="bottom", pady=10, padx=10, anchor="e")

# Bindings
tree.bind("<<TreeviewSelect>>", on_tree_select)
root.bind("w", on_key_press_tree)
root.bind("s", on_key_press_tree)
root.bind("a", on_key_press_tree)
root.bind("d", on_key_press_tree)
root.bind("<space>", on_key_press_tree)
root.bind("r", on_key_press_tree)
root.bind("p", on_key_press_tree)
root.bind("q", on_key_press_tree)
root.bind("x", on_key_press_tree)

update_seek_bar()
root.mainloop()
