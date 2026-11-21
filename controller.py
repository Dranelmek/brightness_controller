"""Monitor discovery and brightness control.

All functions here talk to hardware (DDC/CI or WMI) and can be slow: a monitor
that doesn't answer DDC/CI reads takes ~7 s to time out. Call them from a
background thread, never from the Tk main loop.
"""
from dataclasses import dataclass

import screen_brightness_control as sbc


@dataclass(frozen=True)
class Monitor:
    key: str    # stable identity across rescans (EDID based)
    index: int  # sbc display index from the latest scan; may change on hotplug
    name: str   # human readable label


def _edid_model_name(edid):
    """Return the model name from the EDID's display-name descriptor, if any."""
    try:
        data = bytes.fromhex(edid)
    except (TypeError, ValueError):
        return None
    # Four 18-byte descriptors start at offset 54. A display-name descriptor
    # begins 00 00 00 FC 00, followed by up to 13 bytes of text ending in 0x0A.
    for offset in (54, 72, 90, 108):
        block = data[offset:offset + 18]
        if len(block) == 18 and block[:4] == b"\x00\x00\x00\xfc":
            name = block[5:].split(b"\x0a")[0].decode("ascii", "ignore").strip()
            if name:
                return name
    return None


def _display_name(info):
    maker = info.get("manufacturer") or info.get("manufacturer_id") or ""
    model = _edid_model_name(info.get("edid")) or info.get("model") or "Monitor"
    return f"{maker} {model}".strip()


def list_monitors():
    """Enumerate connected monitors. Fast (~0.1 s); safe to poll."""
    monitors = []
    seen = {}
    for info in sbc.list_monitors_info():
        base = info.get("edid") or info.get("serial") or info.get("name") or "monitor"
        # Two identical monitors without serials can share an EDID.
        count = seen.get(base, 0)
        seen[base] = count + 1
        key = base if count == 0 else f"{base}#{count}"
        monitors.append(Monitor(key, info["index"], _display_name(info)))
    return monitors


def get_brightness(monitor):
    """Current brightness 0-100, or None if the monitor can't report it."""
    try:
        values = sbc.get_brightness(display=monitor.index)
    except Exception:
        return None
    return values[0] if values else None


def set_brightness(monitor, value):
    """Set brightness 0-100. Raises if the monitor rejects the command."""
    sbc.set_brightness(int(value), display=monitor.index, no_return=True)
