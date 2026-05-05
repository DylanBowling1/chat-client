import tkinter as tk
import subprocess
import threading

# start the C client process
client = subprocess.Popen(
    ["./client", "--ip", "127.0.0.1", "--port", "10008"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

def add_message(text):
    chat_box.config(state="normal")
    chat_box.insert(tk.END, text)
    chat_box.see(tk.END)
    chat_box.config(state="disabled")

def read_output():
    while True:
        line = client.stdout.readline()
        if line:
            add_message(line)

def send_message():
    msg = entry.get()

    if msg.strip() == "":
        return

    client.stdin.write(msg + "\n")
    client.stdin.flush()
    entry.delete(0, tk.END)

root = tk.Tk()
root.title("Chat Client GUI")

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
entry = tk.Entry(root, width=50)
entry.pack(side=tk.LEFT)
entry.bind("<Return>", lambda event: send_message())

send_button = tk.Button(root, text="Send", command=send_message)
send_button.pack(side=tk.RIGHT)

# thread to read messages from client
threading.Thread(target=read_output, daemon=True).start()

root.mainloop()