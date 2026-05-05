import tkinter as tk
import subprocess
import threading

client = None

def add_message(text):
    chat_box.config(state="normal")
    chat_box.insert(tk.END, text)
    chat_box.see(tk.END)
    chat_box.config(state="disabled")

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

    connect_button.config(state="disabled")
    disconnect_button.config(state="normal")
    entry.config(state="normal")
    send_button.config(state="normal")

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

    connect_button.config(state="normal")
    disconnect_button.config(state="disabled")
    entry.config(state="disabled")
    send_button.config(state="disabled")

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
root.title("Chat Client GUI")

# connection controls
connection_frame = tk.Frame(root)
connection_frame.pack(pady=5)

tk.Label(connection_frame, text="IP:").pack(side=tk.LEFT)
ip_entry = tk.Entry(connection_frame, width=15)
ip_entry.insert(0, "127.0.0.1")
ip_entry.pack(side=tk.LEFT)

tk.Label(connection_frame, text="Port:").pack(side=tk.LEFT)
port_entry = tk.Entry(connection_frame, width=8)
port_entry.insert(0, "10008")
port_entry.pack(side=tk.LEFT)

connect_button = tk.Button(connection_frame, text="Connect", command=connect_client)
connect_button.pack(side=tk.LEFT)

disconnect_button = tk.Button(connection_frame, text="Disconnect", command=disconnect_client)
disconnect_button.pack(side=tk.LEFT)

# chat + scrollbar frame
chat_frame = tk.Frame(root)
chat_frame.pack()

scrollbar = tk.Scrollbar(chat_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

chat_box = tk.Text(
    chat_frame,
    height=20,
    width=60,
    state="disabled",
    yscrollcommand=scrollbar.set
)
chat_box.pack(side=tk.LEFT)

scrollbar.config(command=chat_box.yview)

# input area
input_frame = tk.Frame(root)
input_frame.pack(pady=5)

entry = tk.Entry(input_frame, width=50)
entry.pack(side=tk.LEFT)
entry.bind("<Return>", lambda event: send_message())

send_button = tk.Button(input_frame, text="Send", command=send_message)
send_button.pack(side=tk.RIGHT)

# initial button/input state
disconnect_button.config(state="disabled")
entry.config(state="disabled")
send_button.config(state="disabled")

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()