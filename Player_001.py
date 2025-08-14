import os
import random
import time
import re
import tkinter as tk
from tkinter import ttk
import pygame
from mutagen.mp3 import MP3

# --- Settings ---
PATH = input("Enter your path to your music folder here: ")
LEFT_BG = "#000000"   # Black panel
RIGHT_BG = "#00FF00"  # Green panel
TEXT_WHITE = "white"
TEXT_BLACK = "black"

# --- Load MP3 files ---
files = [f for f in os.listdir(PATH) if f.endswith(".mp3")]

# --- Initialize mixer ---
pygame.mixer.init()
current_song = None
paused = False
start_time = 0
song_length = 0  # seconds
current_index = 0


# --- Formatting helper ---
def format_song_title(filename):
    # Remove extension
    name = os.path.splitext(filename)[0]

    # Insert space before capital letters (except first char)
    name = re.sub(r"(?<!^)([A-Z])", r" \1", name)

    # Replace underscores and hyphens with spaces
    name = name.replace("_", " ").replace("-", " ")

    # Title case
    return name.title()


# --- Functions ---
def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def get_song_length(song):
    audio = MP3(os.path.join(PATH, song))
    return audio.info.length


def play_song(song=None, position=0):
    global current_song, paused, start_time, song_length, current_index
    if song is None:
        song = song_listbox.get(tk.ACTIVE)
    current_song = song
    current_index = files.index(song)
    song_length = get_song_length(song)
    pygame.mixer.music.load(os.path.join(PATH, song))
    pygame.mixer.music.play(start=position)
    paused = False
    start_time = time.time() - position

    display_name = format_song_title(song)
    song_title_label.config(text=display_name)
    play_pause_button.config(text="Pause ▶")
    update_time_label()


def load_song_paused(song=None):
    global current_song, paused, start_time, song_length, current_index
    if song is None:
        song = song_listbox.get(tk.ACTIVE)
    current_song = song
    current_index = files.index(song)
    song_length = get_song_length(song)
    pygame.mixer.music.load(os.path.join(PATH, song))
    pygame.mixer.music.play()
    pygame.mixer.music.pause()
    paused = True
    start_time = time.time()
    display_name = format_song_title(song)
    song_title_label.config(text=display_name)
    play_pause_button.config(text="Play ▶")
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
    else:
        play_song()


def randomize_and_play():
    global files, current_index
    random.shuffle(files)
    refresh_listbox()
    current_index = 0
    song_listbox.selection_clear(0, tk.END)
    song_listbox.selection_set(0)
    song_listbox.activate(0)
    play_song(files[0])


def refresh_listbox():
    song_listbox.delete(0, tk.END)
    for song in files:
        song_listbox.insert(tk.END, song)


def on_seek(event):
    if current_song and song_length > 0:
        percent = seek_bar.get()
        new_pos = (percent / 100) * song_length
        play_song(current_song, position=new_pos)


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
            # Song ended - play next
            play_next()
    update_time_label()
    root.after(500, update_seek_bar)


def get_current_index():
    selection = song_listbox.curselection()
    if selection:
        return selection[0]
    else:
        return None  # No selection

def play_next():
    old_index = get_current_index()
    if old_index is None:
        return  # No current song selected

    new_index = old_index + 1
    if new_index >= song_listbox.size():
        new_index = song_listbox.size() - 1  # clamp

    diff = new_index - old_index

    if diff == 2:
        new_index = old_index + 1  # correction (though this can't happen in this case)
    elif diff != 1:
        return  # if diff not 1, do nothing

    # Update selection and play
    song_listbox.selection_clear(0, tk.END)
    song_listbox.selection_set(new_index)
    song_listbox.activate(new_index)
    play_song(song_listbox.get(new_index))


def play_previous():
    old_index = get_current_index()
    if old_index is None:
        return  # No current song selected

    new_index = old_index - 1
    if new_index < 0:
        new_index = 0  # clamp to start

    diff = new_index - old_index

    if diff == -2:
        new_index = old_index - 1  # correction (though this can't happen here)
    elif diff != -1:
        return  # if diff not -1, do nothing

    # Update selection and play
    song_listbox.selection_clear(0, tk.END)
    song_listbox.selection_set(new_index)
    song_listbox.activate(new_index)
    play_song(song_listbox.get(new_index))

def seek(seconds_delta):
    if current_song and song_length > 0:
        elapsed = time.time() - start_time if not paused else (seek_bar.get() / 100) * song_length
        new_pos = max(0, min(elapsed + seconds_delta, song_length))
        play_song(current_song, position=new_pos)


def on_close():
    pygame.mixer.music.stop()
    root.destroy()


def on_song_select(event):
    global current_index
    if not song_listbox.curselection():
        return
    idx = song_listbox.curselection()[0]
    if idx != current_index:
        current_index = idx
        selected_song = song_listbox.get(idx)
        if paused:
            load_song_paused(selected_song)
        else:
            play_song(selected_song)


def on_key_press(event):
    key = event.keysym.lower()
    if key == "space":
        toggle_play_pause()
    elif key == "up":
        song_listbox.selection_clear(0, tk.END)
        play_previous()
    elif key == "down":
        song_listbox.selection_clear(0, tk.END)
        play_next()
    elif key == "left":
        seek(-5)
    elif key == "right":
        seek(5)
    elif key == "r":
        randomize_and_play()


# --- UI Setup ---
root = tk.Tk()
root.title("Music Player")
root.geometry("600x400")
root.configure(bg=LEFT_BG)
root.protocol("WM_DELETE_WINDOW", on_close)

main_frame = tk.Frame(root, bg=LEFT_BG)
main_frame.pack(fill="both", expand=True)

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

right_frame = tk.Frame(main_frame, bg=RIGHT_BG)
right_frame.pack(side="right", fill="both", expand=True)

song_listbox = tk.Listbox(right_frame, bg=RIGHT_BG, fg=TEXT_BLACK,
                          selectbackground="white", selectforeground="black")
song_listbox.pack(expand=True, fill="both", padx=10, pady=10)
for song in files:
    song_listbox.insert(tk.END, song)

if song_listbox.size() > 0:
    song_listbox.selection_set(0)
    song_listbox.activate(0)

song_listbox.bind("<<ListboxSelect>>", on_song_select)

randomize_button = tk.Button(right_frame, text="Randomize", command=randomize_and_play,
                             bg=RIGHT_BG, fg=TEXT_BLACK, relief="flat")
randomize_button.pack(side="bottom", pady=10, padx=10, anchor="e")

root.bind("<space>", on_key_press)
root.bind("<Up>", on_key_press)
root.bind("<Down>", on_key_press)
root.bind("<Left>", on_key_press)
root.bind("<Right>", on_key_press)
root.bind("r", on_key_press)

update_seek_bar()

root.mainloop()
