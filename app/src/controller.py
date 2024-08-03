import screen_brightness_control as sbc

# returns list of integers
# brightnesses of all monitors
def get(option=0):
    out = 50
    match option:
        case 1:
            out = max(sbc.get_brightness())
        case 2:
            out = min(sbc.get_brightness())
        case 0 | _:
            out = sbc.get_brightness()[0]
    return out

# sets the brightness of all monitors
def set(val=10):
    sbc.set_brightness(int(val))

# returns list of monitors
def get_displays():
    return sbc.list_monitors()
