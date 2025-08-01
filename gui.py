import tkinter as tk
from controller import *
from options import *

# root window
root = tk.Tk()
root.geometry("400x200")
root.title("Screen Brightness")
root.resizable(height=False, width=False)

# section
sec = tk.Frame(root, padx=0, pady=0)

# app label
label = tk.Label(sec, text="Brightness", font=('Franklin Gothic Heavy', 18))
label.pack(padx=20, pady=10)

# slider function
def update(*args):
    set(val.get())

# brightness slider
val = tk.DoubleVar()
slider = tk.Scale(sec, variable=val, from_=1, to=100,orient=tk.HORIZONTAL, font=('consolas', 8), length=380, width=30, command=update)


# main monitor brightness
brightness = get(GetOptions.SIMPLE)
slider.set(brightness)

def hide_widget(widget):
    # This will remove the widget from toplevel
    widget.pack_forget()


def show_widget(widget):
    # This will recover the widget from toplevel
    widget.pack()

slider.pack()
sec.pack()
