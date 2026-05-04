# 🏠 PyScript Home Assistant Automation Suite

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-PyScript-41BDF5.svg)](https://github.com/custom-components/pyscript)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained-Yes-green.svg)](https://github.com/LFTPadilla/pyscript-homeassitant)

A comprehensive Python automation suite for Home Assistant using PyScript, providing intelligent home automation with advanced features including smart sleep management, adaptive lighting, climate control, and emergency safety systems.

## ✨ Key Features

### 🌙 Advanced Sleep & Wake Management
- **Smart Alarm with Sleep Cycle Optimization**: Calculates optimal wake times based on 90-minute sleep cycles
- **4-Phase Gentle Wake-Up Sequence**: Pre-wake → Light wake → Audio wake → Full wake
- **Natural Wake Detection**: Automatically cancels alarm if you wake up naturally
- **Smart Morning Routine**: Triggered by motion sensors with time-based conditions

### 💡 Intelligent Lighting System
- **Motion-Activated Lighting**: Automatic lights in all rooms with 5-second smooth fade-out transitions
- **Time-Adaptive Brightness**: Different brightness and color temperature based on time of day
- **House Mode Integration**: Respects quiet modes (Sleep, Cinema) for optimal ambiance
- **Advanced Transition Services**: Smooth fade effects and customizable lighting scenes

### 🏡 Smart House Modes
- **8 Intelligent Modes**: Sleep, Away, Day, Night, Cinema, Friends, Reading, Meditation
- **Context-Aware Automation**: Each mode optimizes lighting, climate, and device behavior
- **Smart Arrival Detection**: Automatic mode restoration with intelligent door sensor integration
- **Audio Feedback**: Welcome messages and mode confirmations

### 🌡️ Advanced Climate Control
- **Smart Air Purifier**: PM2.5-based control with house mode speed limits
- **Intelligent Bathroom Humidity**: Hysteresis control with post-shower detection
- **Automatic Dehumidifier Plug**: Activates above 75% humidity and powers down below 70%
- **Energy Optimization**: Occupancy-based adjustments and power management
- **Emergency Response**: Automatic ventilation during smoke alarm events

### 🎛️ Smart Controls & Automation
- **ZHA Knob Integration**: Physical controls for brightness, temperature, and music
- **Comprehensive Motion Sensors**: Kitchen, living room, bedroom, closet, bathroom coverage
- **Smart Appliance Control**: Vacuum robot, fans, pumps with intelligent scheduling
- **Media Integration**: Google Speaker control and entertainment system automation

### 🚨 Emergency & Safety Systems
- **Smoke Alarm Response**: Automatic maximum lighting and dangerous appliance shutdown
- **Emergency Evacuation Support**: Audio alerts and safety system coordination
- **Recovery Mode**: Gradual return to normal operations when emergency clears

## 📁 Project Structure

### Core System Files
```
house_modes.py          # Central house mode management with smart arrival detection
system_routines.py      # Time-based scheduled operations and automated routines
common_utils.py         # Enhanced TTS service with async patterns and error handling
```

### Sleep & Wake Management
```
smart_alarm.py          # Comprehensive smart alarm with sleep cycle optimization
smart_alarm_config.yaml # Required Home Assistant entity configurations
```

### Lighting System
```
lighting_motion.py      # Motion-triggered lighting with smooth transitions
lighting_services.py    # Advanced lighting utilities and fade services
```

### Device Controls
```
knob_controllers.py     # ZHA knob controllers for brightness and temperature
media_control.py        # Google Speaker music control automation
desktop_automation.py   # Desktop environment automation with air quality monitoring
```

### Climate & Environment
```
climate_control.py      # Advanced climate management with PM2.5 and humidity control
vacuum_robot.py         # Smart vacuum robot with battery management
```

### Safety & Emergency
```
emergency_safety.py     # Emergency smoke alarm response with safety measures
```

### Configuration Files
```
services.yaml           # Home Assistant service definitions
requirements.txt        # Python dependencies
```

## 🚀 Installation

### Prerequisites
- [Home Assistant](https://www.home-assistant.io/) installed and running
- [PyScript](https://github.com/custom-components/pyscript) custom component installed
- Python 3.8+ (handled by Home Assistant)

### Step 1: Install PyScript
1. Install PyScript via HACS or manually
2. Add to your `configuration.yaml`:
```yaml
pyscript:
  allow_all_imports: true
  hass_is_global: true
```

### Step 2: Clone Repository
```bash
cd /config/pyscript
git clone https://github.com/LFTPadilla/pyscript-homeassitant.git
```

### Step 3: Configure Home Assistant Entities
Add these entities to your `configuration.yaml`:

```yaml
# Smart Alarm System
input_datetime:
  sleep_start_time:
    name: "Sleep Start Time"
    has_date: true
    has_time: true
  smart_alarm_wake_time:
    name: "Smart Alarm Wake Time"
    has_date: true
    has_time: true

input_boolean:
  morning_routine_executed:
    name: "Morning Routine Executed"
    initial: false
  smart_alarm_enabled:
    name: "Smart Alarm Enabled"
    initial: true

# House Mode System
input_select:
  house_mode:
    name: "House Mode"
    options:
      - Sleep
      - Away
      - Day
      - Night
      - Cinema
      - Friends
      - Reading
      - Meditation
    initial: Day
```

### Step 4: Copy Service Definitions
Copy `services.yaml` to your Home Assistant configuration directory and add to your `configuration.yaml`:
```yaml
homeassistant:
  packages: !include_dir_named packages
```

### Step 5: Restart and Reload
1. Restart Home Assistant
2. Go to Developer Tools → Services
3. Call `pyscript.reload` to load all scripts

## 🔧 Configuration

### Required Entities
 The system expects these entity types to be available:
 - **Lights**: `light.kitchen_light`, `light.bedroom_light`, `light.bathroom_light`, `light.bathroom_fan_dimmer`, etc.
 - **Motion Sensors**: `binary_sensor.kitchen_motion_sensor`, `binary_sensor.bedroom_motion`, etc.
 - **Switches**: `switch.air_purifier_plug`, etc.
 - **Door Sensors**: `binary_sensor.main_door_sensor`, `binary_sensor.livingroom_door_sensor`
 - **Safety Sensors**: `binary_sensor.wifi_smoke_alarm_smoke`

### Entity Discovery
Use the Home Assistant API to discover available entities:
```bash
# List all lights
curl "http://YOUR_HA_IP:8123/api/states" | grep "light\."

# List all motion sensors  
curl "http://YOUR_HA_IP:8123/api/states" | grep "binary_sensor.*motion"
```

### Customization
Edit the Python files to match your specific entity names and customize behavior:
- Modify entity names in each automation file
- Adjust timing values and thresholds
- Configure house mode behaviors
- Customize TTS messages and announcements

## 📱 Usage Examples

### House Mode Control
```python
# Set house mode via service call
service: input_select.select_option
target:
  entity_id: input_select.house_mode
data:
  option: "Cinema"
```

### Smart Alarm Setup
```python
# Set bedtime
service: input_datetime.set_datetime
target:
  entity_id: input_datetime.sleep_start_time
data:
  datetime: "2024-01-01 22:30:00"
```

### Manual Light Control
```python
# Fade all lights off smoothly
service: pyscript.fade_all_lights_off
```

### Scheduled Light Automation
```python
# At 6:00 PM daily, turn on the desktop strip light with warm white (2700 K)
@time_trigger("cron(00 18 * * *)")
def turn_on_desktop_strip_light():
    light.turn_on(entity_id="light.desktop_strip_light", kelvin=2700)
```

### Climate Control
The system automatically manages:
- Air purifier based on PM2.5 levels
- Bathroom fan based on humidity
- House mode appropriate settings

## 🏠 House Modes Explained

| Mode | Purpose | Key Features |
|------|---------|--------------|
| **Sleep** | Nighttime rest | Dim lighting, quiet devices, alarm activation |
| **Away** | House empty | Security mode, cleaning routines, air quality management |
| **Day** | Active daytime | Bright lighting, all devices active, productivity focus |
| **Night** | Evening relaxation | Warm lighting, reduced timeouts, comfort optimization |
| **Cinema** | Movie watching | Theater lighting, projector control, silence mode |
| **Friends** | Social gatherings | Bright welcoming lights, fragrance activation |
| **Reading** | Focused reading | Optimal task lighting, minimal distractions |
| **Meditation** | Peaceful environment | Minimal lighting, serene atmosphere |

## 🔍 Advanced Features

### Sleep Cycle Science
- **90-minute cycle optimization** for natural wake windows
- **Circadian rhythm support** with time-based lighting
- **4-phase wake sequence** to minimize sleep inertia
- **Sleep quality tracking** with duration metrics

### Smart Lighting
- **Motion-activated** with 5-second smooth fade-out
- **Time-adaptive** brightness and color temperature
- **Context-aware** behavior based on house modes
- **Energy-efficient** with occupancy detection

### Climate Intelligence
- **PM2.5 monitoring** with automatic air purifier control
- **Humidity management** with hysteresis control
- **House mode integration** for noise-sensitive operations
- **Emergency response** with safety system coordination

## 🛠️ Development

### PyScript Best Practices
- **Async/await patterns** for non-blocking operations
- **Task management** with `task.unique()` decorators
- **Error handling** with graceful degradation
- **Cross-module calls** with proper `pyscript.` prefixes

### Code Quality
- **Comprehensive error handling** throughout
- **Extensive logging** with appropriate levels
- **State validation** and safe defaults
- **Type casting** for Home Assistant compatibility

### Testing & Debugging
```bash
# Validate Python syntax
python3 -m py_compile *.py

# Check Home Assistant logs
tail -f /config/home-assistant.log | grep pyscript

# Reload scripts after changes
# Developer Tools → Services → pyscript.reload
```

## 🔒 Security & Safety

This automation suite is designed for **defensive home automation purposes only**:
- **Energy management** and efficiency optimization
- **Safety systems** with emergency response
- **Convenience features** for daily living
- **Security monitoring** with appropriate alerts

All code includes:
- **Comprehensive error handling** to prevent system failures
- **Safe defaults** to ensure graceful degradation
- **State validation** to prevent unintended behavior
- **Emergency protocols** for safety-critical situations

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test thoroughly with your Home Assistant setup
4. Submit a pull request with detailed description

### Development Setup
1. Set up a Home Assistant development environment
2. Install PyScript in development mode
3. Use the provided entity discovery tools
4. Test all automations before committing

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) - The amazing home automation platform
- [PyScript](https://github.com/custom-components/pyscript) - Python scripting for Home Assistant
- [ZHA](https://www.home-assistant.io/integrations/zha/) - Zigbee Home Automation integration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/LFTPadilla/pyscript-homeassitant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/LFTPadilla/pyscript-homeassitant/discussions)
- **Documentation**: [Home Assistant PyScript Docs](https://github.com/custom-components/pyscript)

---

⭐ **Star this repository if you find it useful!**
