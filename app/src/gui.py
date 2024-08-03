import tkinter as tk
import controller
from options import *

# root window
root = tk.Tk()
root.geometry("400x200")
root.title("Screen Brightness")
root.resizable(height=False, width=False)

# app label
label = tk.Label(root, text="Brightness", font=('Franklin Gothic Heavy', 18))
label.pack(padx=20, pady=10)

# slider function
def update(*args):
    controller.set(val.get())

# brightness slider
val = tk.DoubleVar()
slider = tk.Scale(root, variable=val, from_=1, to=100,orient=tk.HORIZONTAL, font=('consolas', 8), length=380, width=30, command=update)


# main monitor brightness
brightness = controller.get(GetOptions.SIMPLE)

slider.set(brightness)

slider.pack()

root.mainloop()