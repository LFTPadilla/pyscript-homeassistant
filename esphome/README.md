# ESPHome Scripts

This folder contains ESPHome configurations used by the home setup.

## Files

- `espdesktop.yml`: Desktop environment sensor node.
- `desktop-table.yml`: Dedicated desk controller node (`desktop-table`).

## Desktop table preset switches (`desktop-table.yml`)

In `desktop-table.yml`, table presets are configured as GPIO switches with `restore_mode: ALWAYS_ON` and an `on_turn_off` automation.

How it works:
- The relay stays **ON** as the normal idle state.
- When Home Assistant turns the switch **OFF**, ESPHome sends a short pulse (`100ms`) to simulate a button press.
- After the pulse, ESPHome turns the relay **ON** again automatically.

This is why the switch appears ON most of the time, and quickly returns to ON after being turned OFF.

## Automation safety note

Turning OFF `Desktop table position 2 stand` or `Desktop table position 3 top` triggers desk movement. Any automation that calls `switch.turn_off` on those entities will activate the corresponding preset.

For vacuum automations, do not toggle this desk preset unless the intent is to move the desk.
