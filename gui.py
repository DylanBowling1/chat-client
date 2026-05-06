import tkinter as tk
import subprocess
import threading
import re
import os

client = None
username = os.environ.get("USER", "")

# UI colors
BG_COLOR = "#1e1e1e"
PANEL_COLOR = "#252526"
TEXT_COLOR = "white"
SYSTEM_COLOR = "#9ca3af"
ERROR_COLOR = "#ff6b6b"
MENTION_COLOR = "#ffd166"

CONNECT_COLOR = "#3b82f6"
CONNECT_DISABLED = "#374151"
DISCONNECT_COLOR = "#ef4444"
DISCONNECT_DISABLED = "#374151"
SEND_COLOR = "#22c55e"
SEND_DISABLED = "#374151"

def clean_text(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)

def add_message(text):
    text = clean_text(text)

    chat_box.config(state="normal")

    mention = f"@{username}" if username else ""

    if text.startswith("[SYSTEM]") or "[SYSTEM]" in text:
        chat_box.insert(tk.END, text, "system")

    elif text.startswith("[ERR]"):
        chat_box.insert(tk.END, text, "error")

    elif mention and mention in text:
        start = 0

        while True:
            index = text.find(mention, start)

            if index == -1:
                chat_box.insert(tk.END, text[start:], "normal")
                break

            chat_box.insert(tk.END, text[start:index], "normal")
            chat_box.insert(tk.END, mention, "mention")

            start = index + len(mention)

    else:
        chat_box.insert(tk.END, text, "normal")

    chat_box.see(tk.END)
    chat_box.config(state="disabled")

def set_connected_state(is_connected):
    if is_connected:
        connect_button.config(bg=CONNECT_DISABLED, fg="#9ca3af")
        disconnect_button.config(bg=DISCONNECT_COLOR, fg="white")
        send_button.config(bg=SEND_COLOR, fg="white")
        entry.config(state="normal")
    else:
        connect_button.config(bg=CONNECT_COLOR, fg="white")
        disconnect_button.config(bg=DISCONNECT_DISABLED, fg="#9ca3af")
        send_button.config(bg=SEND_DISABLED, fg="#9ca3af")
        entry.config(state="disabled")

def read_output():
    global client

    while client is not None:
        line = client.stdout.readline()
        if line:
            add_message(line)
        else:
            break

def read_errors():
    global client

    while client is not None:
        line = client.stderr.readline()
        if line:
            add_message("[ERR] " + line)
        else:
            break

def connect_client():
    global client

    if client is not None:
        add_message("[GUI] Already connected.\n")
        return

    host = ip_entry.get()
    port = port_entry.get()

    client = subprocess.Popen(
        ["./client", "--ip", host, "--port", port],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    add_message(f"[GUI] Connected to {host}:{port}\n")
    set_connected_state(True)

    threading.Thread(target=read_output, daemon=True).start()
    threading.Thread(target=read_errors, daemon=True).start()

def disconnect_client():
    global client

    if client is None:
        add_message("[GUI] Not connected.\n")
        return

    client.terminate()
    client = None

    add_message("[GUI] Disconnected.\n")
    set_connected_state(False)

def send_message():
    global client

    if client is None:
        add_message("[GUI] Connect before sending a message.\n")
        return

    msg = entry.get()

    if msg.strip() == "":
        return

    client.stdin.write(msg + "\n")
    client.stdin.flush()
    entry.delete(0, tk.END)

def on_close():
    global client

    if client is not None:
        try:
            client.terminate()
        except Exception:
            pass

    root.destroy()

root = tk.Tk()
root.title("Peak Server")
root.configure(bg=BG_COLOR)
root.minsize(700, 500)

root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)

connection_frame = tk.Frame(root, pady=8, bg=BG_COLOR)
connection_frame.grid(row=0, column=0, sticky="ew")

tk.Label(
    connection_frame,
    text="IP:",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    font=("Menlo", 13, "bold")
).pack(side=tk.LEFT, padx=5)

ip_entry = tk.Entry(
    connection_frame,
    width=15,
    bg=PANEL_COLOR,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR,
    relief="flat",
    font=("Menlo", 13)
)
ip_entry.insert(0, "127.0.0.1")
ip_entry.pack(side=tk.LEFT)

tk.Label(
    connection_frame,
    text="Port:",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    font=("Menlo", 13, "bold")
).pack(side=tk.LEFT, padx=5)

port_entry = tk.Entry(
    connection_frame,
    width=8,
    bg=PANEL_COLOR,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR,
    relief="flat",
    font=("Menlo", 13)
)
port_entry.insert(0, "10008")
port_entry.pack(side=tk.LEFT)

connect_button = tk.Label(
    connection_frame,
    text="Connect",
    bg=CONNECT_COLOR,
    fg=TEXT_COLOR,
    font=("Menlo", 12, "bold"),
    padx=14,
    pady=7,
    cursor="hand2"
)
connect_button.pack(side=tk.LEFT, padx=8)
connect_button.bind("<Button-1>", lambda event: connect_client())

disconnect_button = tk.Label(
    connection_frame,
    text="Disconnect",
    bg=DISCONNECT_DISABLED,
    fg="#9ca3af",
    font=("Menlo", 12, "bold"),
    padx=14,
    pady=7,
    cursor="hand2"
)
disconnect_button.pack(side=tk.LEFT)
disconnect_button.bind("<Button-1>", lambda event: disconnect_client())

chat_frame = tk.Frame(root, bg=BG_COLOR)
chat_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

chat_frame.grid_rowconfigure(0, weight=1)
chat_frame.grid_columnconfigure(0, weight=1)

scrollbar = tk.Scrollbar(chat_frame)
scrollbar.grid(row=0, column=1, sticky="ns")

chat_box = tk.Text(
    chat_frame,
    state="disabled",
    wrap="word",
    yscrollcommand=scrollbar.set,
    bg=PANEL_COLOR,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR,
    relief="flat",
    padx=10,
    pady=10,
    font=("Menlo", 14)
)

chat_box.grid(row=0, column=0, sticky="nsew")

chat_box.tag_config("normal", foreground=TEXT_COLOR)
chat_box.tag_config("system", foreground=SYSTEM_COLOR)
chat_box.tag_config("error", foreground=ERROR_COLOR)
chat_box.tag_config("mention", foreground=MENTION_COLOR)

scrollbar.config(command=chat_box.yview)

input_frame = tk.Frame(root, pady=10, bg=BG_COLOR)
input_frame.grid(row=2, column=0, sticky="ew")

input_frame.grid_columnconfigure(0, weight=1)

entry = tk.Entry(
    input_frame,
    bg=PANEL_COLOR,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR,
    relief="flat",
    font=("Menlo", 13)
)

entry.grid(row=0, column=0, sticky="ew", padx=10)
entry.bind("<Return>", lambda event: send_message())

send_button = tk.Label(
    input_frame,
    text="Send",
    bg=SEND_DISABLED,
    fg="#9ca3af",
    font=("Menlo", 12, "bold"),
    padx=14,
    pady=7,
    cursor="hand2"
)
send_button.grid(row=0, column=1, padx=10)
send_button.bind("<Button-1>", lambda event: send_message())

set_connected_state(False)

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()