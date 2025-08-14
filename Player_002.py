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
LEFT_BG = "#000000"   # Black panel
RIGHT_BG = "#00FF00"  # Green panel
TEXT_WHITE = "white"
TEXT_BLACK = "black"

# --- Initialize mixer ---
pygame.mixer.init()
current_song = None
paused = False
start_time = 0
song_length = 0  # seconds

# --- Formatting helper ---
def format_song_title(filename):
    name = os.path.splitext(filename)[0]
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
    play_pause_button.config(text="Pause ▶")
    update_time_label()

def toggle_play_pause():
    global paused, start_time
    if pygame.mixer.music.get_busy() and not paused:
        pygame.mixer.music.pause()
        paused = True
        play_pause_button.config(text="Play ▶")
    elif paused:
        pygame.mixer.music.unpause()
        paused = False
        start_time = time.time() - (seek_bar.get() / 100) * song_length
        play_pause_button.config(text="Pause ▶")

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
        time_label.config(text=f"{format_time(elapsed)}/{format_time(song_length)}")

def update_seek_bar():
    if song_length > 0:
        if not paused and pygame.mixer.music.get_busy():
            elapsed = time.time() - start_time
            percent = (elapsed / song_length) * 100
            seek_bar.set(percent)
        elif not paused and current_song and not pygame.mixer.music.get_busy():
            # Song ended - auto next in folder
            play_next_in_folder()
    update_time_label()
    root.after(500, update_seek_bar)

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
            # Handle top-level folders that have no parent
            if parent_key == "." or parent_key == "":
                parent_id = ""
            else:
                parent_id = folder_nodes.get(parent_key, "")

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
    item_id = tree.selection()[0]
    fullpath, depth, index = tree.item(item_id, "values")
    index = int(index)
    if index == -1:  # folder clicked
        children = tree.get_children(item_id)
        for child in children:
            _, cdepth, cindex = tree.item(child, "values")
            if int(cindex) >= 0:  # song found
                tree.selection_set(child)
                play_song_from_path(tree.item(child, "values")[0])
                return
    else:
        play_song_from_path(fullpath)

def find_path_of_current_selection():
    sel = tree.selection()
    if not sel:
        return None
    fullpath, depth, index = tree.item(sel[0], "values")
    if int(index) >= 0:
        return fullpath
    return None

# --- Folder navigation ---
def play_next_in_folder():
    sel = tree.selection()
    if not sel:
        return
    item_id = sel[0]
    parent = tree.parent(item_id)
    siblings = tree.get_children(parent)
    cur_pos = siblings.index(item_id)
    if cur_pos + 1 < len(siblings):
        _, d2, idx2 = tree.item(siblings[cur_pos+1], "values")
        if int(idx2) >= 0:
            tree.selection_set(siblings[cur_pos+1])
            play_song_from_path(tree.item(siblings[cur_pos+1], "values")[0])

def play_prev_in_folder():
    sel = tree.selection()
    if not sel:
        return
    item_id = sel[0]
    parent = tree.parent(item_id)
    siblings = tree.get_children(parent)
    cur_pos = siblings.index(item_id)
    if cur_pos - 1 >= 0:
        _, d2, idx2 = tree.item(siblings[cur_pos-1], "values")
        if int(idx2) >= 0:
            tree.selection_set(siblings[cur_pos-1])
            play_song_from_path(tree.item(siblings[cur_pos-1], "values")[0])

# --- Key press handler ---
def on_key_press_tree(event):
    key = event.keysym.lower()
    if key == "s":  # next song in folder
        play_next_in_folder()
    elif key == "w":  # previous song in folder
        play_prev_in_folder()
    elif key == "space":
        toggle_play_pause()
    elif key == "a":  # rewind 5 sec
        if current_song and song_length > 0:
            seek(-5)
    elif key == "d":  # forward 5 sec
        if current_song and song_length > 0:
            seek(5)
    elif key == "r":
        randomize_and_play()

# --- Random play ---
def randomize_and_play():
    all_songs = []
    for songs in folder_structure.values():
        all_songs.extend(songs)
    if all_songs:
        song = random.choice(all_songs)
        play_song_from_path(song)

# --- Close ---
def on_close():
    pygame.mixer.music.stop()
    root.destroy()

# --- UI Setup ---
root = tk.Tk()
root.title("Music Player")
root.geometry("600x400")
root.configure(bg=LEFT_BG)
root.protocol("WM_DELETE_WINDOW", on_close)

main_frame = tk.Frame(root, bg=LEFT_BG)
main_frame.pack(fill="both", expand=True)

# Left
left_frame = tk.Frame(main_frame, bg=LEFT_BG, width=300)
left_frame.pack(side="left", fill="both")

song_title_label = tk.Label(left_frame, text="No song playing", fg=TEXT_WHITE, bg=LEFT_BG, font=("Arial", 14))
song_title_label.pack(pady=20)

play_pause_button = tk.Button(left_frame, text="Play ▶", command=toggle_play_pause,
                              bg=LEFT_BG, fg=TEXT_BLACK, font=("Arial", 12), relief="flat")
play_pause_button.pack(pady=10)

time_label = tk.Label(left_frame, text="0:00/0:00", font=("Arial", 10), bg=LEFT_BG, fg=TEXT_WHITE)
time_label.pack()

style = ttk.Style()
style.theme_use("default")
style.configure("TScale", background=LEFT_BG, troughcolor="#222222")

seek_bar = ttk.Scale(left_frame, from_=0, to=100, orient="horizontal")
seek_bar.pack(fill="x", padx=20, pady=10)
seek_bar.bind("<ButtonRelease-1>", on_seek)

# Right
right_frame = tk.Frame(main_frame, bg=RIGHT_BG)
right_frame.pack(side="right", fill="both", expand=True)

tree = ttk.Treeview(right_frame, columns=("fullpath", "depth", "index"), show="tree")
tree.pack(expand=True, fill="both", padx=10, pady=10)
scan_music_directory(PATH)

randomize_button = tk.Button(right_frame, text="Randomize", command=randomize_and_play,
                             bg=RIGHT_BG, fg=TEXT_BLACK, relief="flat")
randomize_button.pack(side="bottom", pady=10, padx=10, anchor="e")

# Bindings
tree.bind("<<TreeviewSelect>>", on_tree_select)
root.bind("w", on_key_press_tree)
root.bind("s", on_key_press_tree)
root.bind("a", on_key_press_tree)
root.bind("d", on_key_press_tree)
root.bind("<space>", on_key_press_tree)
root.bind("r", on_key_press_tree)

update_seek_bar()
root.mainloop()
