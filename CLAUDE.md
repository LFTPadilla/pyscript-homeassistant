# PyScript Home Assistant Automation Suite

## Project Overview
This project contains Python scripts for Home Assistant automation using PyScript. It provides comprehensive home automation covering lighting, climate control, sleep management, smart routines, and multimedia management with advanced AI-driven optimizations.

## Files Structure

### Core System Management
- **`house_modes.py`** - Central house mode state management (Sleep, Away, Day, Night, Cinema, etc.) with smart arrival detection
- **`system_routines.py`** - Time-based scheduled operations and automated routines

### Advanced Sleep & Wake Management
- **`smart_alarm.py`** - Comprehensive smart alarm system with sleep cycle optimization, gentle 4-phase wake-up sequences, and automatic morning routines
- **`smart_alarm_config.yaml`** - Required Home Assistant entity configurations for smart alarm system

### Lighting System
- **`lighting_motion.py`** - Motion-triggered lighting automation for all rooms with 5-second smooth fade-out transitions
- **`lighting_services.py`** - Advanced lighting utilities including smooth transitions, brightness/temperature controls, and fade services

### Device Controls & Interfaces
- **`knob_controllers.py`** - ZHA knob controllers for brightness and temperature adjustment with mode switching
- **`media_control.py`** - Google Speaker music control automation using ZHA knob events
- **`desktop_automation.py`** - Desktop environment automation including fan control based on PM2.5 levels

### Climate & Environment
- **`climate_control.py`** - Advanced climate management with smart air purifier control, intelligent bathroom humidity management with hysteresis
- **`vacuum_robot.py`** - Smart vacuum robot control with battery management and house mode integration

### Infrastructure & Utilities
- **`common_utils.py`** - Enhanced TTS service with async patterns and comprehensive error handling
- **`appliance_automation.py`** - Washing machine and other appliance controls (legacy/disabled)

### Emergency & Safety Systems
- **`emergency_safety.py`** - Emergency smoke alarm response with automatic safety measures

### Placeholders for Future Development
- **`notification.py`** - Notification service (empty placeholder)
- **`proxmox.py`** - Proxmox integration (empty placeholder)
- **`tests.py`** - Test utilities (empty placeholder)

### Configuration
- **`services.yaml`** - Home Assistant service definitions for light fading functionality
- **`requirements.txt`** - Python dependencies (currently empty)
- **`README.md`** - Basic project description

## Key Features

### Advanced Sleep & Wake System
- **Smart Alarm with Sleep Cycle Optimization**: Calculates optimal wake times between 8-8.5 hours based on 90-minute sleep cycles
- **4-Phase Gentle Wake-Up Sequence**:
  - Pre-wake preparation (very dim lighting, soft sounds)
  - Light wake-up (gradual brightness increase)
  - Audio wake-up (gentle announcements)
  - Full wake-up (Day mode transition)
- **Smart Morning Routine**: Triggered by closet motion sensor with time-based conditions (5:30-8:00 AM)
- **Natural Wake Detection**: Automatically cancels alarm if user wakes up naturally
- **Sleep Quality Tracking**: Provides sleep duration and quality assessments

### Enhanced Lighting System
- **Motion-activated lights** in kitchen, living room, bedroom, closet, and bathroom with **5-second smooth fade-out transitions**
- **Time-adaptive lighting**: Different brightness and color temperature based on time of day
- **Smooth transition services**: `fade_light_off`, `fade_all_lights_off`, and advanced `smooth_transition` function
- **House mode integration**: Respects quiet modes (Sleep, Cinema) for noise control
- **Energy-saving features** with timeout adjustments

### Smart Arrival & Departure Detection
- **Intelligent door-based mode restoration** with 5-minute buffer to prevent false triggers
- **Context-aware lighting**: Automatically turns on entry lights for evening arrivals
- **Audio feedback**: Welcome messages with mode confirmation

### House Modes with Enhanced Logic
- **Sleep**: Comprehensive sleep preparation with device shutdown and alarm activation
- **Away**: Smart cleaning routine with security measures and air quality management
- **Day**: Optimized daytime settings with device activation and appropriate lighting
- **Night**: Warm, dim lighting for evening comfort with reduced timeouts
- **Cinema**: Theater mode with projector control, ambient lighting, and silence optimization
- **Friends**: Bright, welcoming atmosphere with fragrance dispenser activation
- **Reading**: Focused lighting for reading activities
- **Meditation**: Minimal lighting for peaceful environment

### Advanced Climate Control
- **Smart Air Purifier**: PM2.5-based control with house mode speed limits (Silent in Sleep/Cinema, variable speeds for Day/Night/Away)
- **Intelligent Bathroom Humidity Control**:
  - Hysteresis control to prevent oscillation
  - Post-shower detection with extended runtime
  - Progressive timing based on humidity levels
  - Manual override support
- **House mode integration** for noise-sensitive operations

### Smart Controls & Automation
- **ZHA knob integration** for brightness/temperature control and music playback with mode switching
- **Motion sensors** throughout the house with enhanced error handling and fallback mechanisms
- **Energy-saving features** with occupancy-based adjustments
- **Vacuum robot automation** with adaptive fan speeds and battery management

### Device Integration
- **Google Speaker control** for media playback and TTS announcements
- **Smart switches** for appliances (pumps, fans, monitors) with sequential activation
- **Curtain control** for automated privacy and lighting management
- **Projector and entertainment system** automation with ambient optimization
- **Emergency smoke alarm** integration with automatic safety response

### Emergency & Safety Features
- **Smoke alarm emergency response**: Automatic maximum lighting, dangerous appliance shutdown, ventilation activation
- **Emergency evacuation support**: Audio alerts, camera recording, safety system coordination
- **Recovery mode**: Gradual return to normal operations when emergency clears

## Technology Stack
- **PyScript** - Python automation platform for Home Assistant with async/await patterns
- **ZHA (Zigbee)** - Device communication protocol for sensors and controllers
- **Home Assistant** - Core automation platform with advanced entity management
- **Motion Sensors** - Various PIR and vibration sensors with comprehensive coverage
- **Smart Switches** - Power management and device control with energy optimization
- **Environmental Sensors** - PM2.5, humidity, and other air quality monitoring

## Advanced Features

### Error Handling & Reliability
- **Comprehensive error handling** with graceful degradation
- **Sensor availability checks** with fallback mechanisms
- **Task management** with `task.unique()` decorators to prevent conflicts
- **Extensive logging** with appropriate log levels (debug, info, warning, error)
- **State validation** and safe defaults throughout

### PyScript Best Practices Implementation
- **Proper async/await patterns** for non-blocking operations
- **Cross-module function calls** with correct `pyscript.` prefixes
- **Standardized state access** using `state.get()` and `state.getattr()`
- **Task management** for concurrent operations
- **Enhanced TTS service** with robust error handling

### Sleep Cycle Science
- **90-minute sleep cycle optimization** for natural wake windows
- **Circadian rhythm considerations** with time-based lighting adjustments
- **Sleep quality metrics** with duration and quality assessments
- **Gradual wake-up sequences** to minimize sleep inertia

## Development Status
- **Core lighting and mode management**: **Complete and Active** with smooth transitions
- **Smart alarm and morning routines**: **Complete and Active** with sleep cycle optimization
- **Climate control systems**: **Complete and Active** with advanced PM2.5 and humidity management
- **Music control system**: **Complete and Active** with ZHA integration
- **Desktop environment automation**: **Complete and Active** with air quality monitoring
- **Smart arrival detection**: **Complete and Active** with context-aware logic
- **Washing machine automation**: **Disabled/Legacy**
- **Notification and Proxmox modules**: **Placeholders for future development**

## Usage Notes
- **PyScript reloading**: Use `pyscript.reload` in Home Assistant Developer Tools after code changes
- **Error monitoring**: Check Home Assistant logs for debugging information
- **Task uniqueness**: System prevents automation conflicts with unique task IDs
- **State management**: Robust state access patterns with fallback mechanisms
- **Function calls**: Cross-module functions require `pyscript.` prefix

## Configuration Requirements
To use the smart alarm system, add these entities to your Home Assistant `configuration.yaml`:

```yaml
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
```

## Testing & Debugging
- **Syntax validation**: All Python files pass `python3 -m py_compile` checks
- **Function call testing**: Cross-module function calls verified with correct prefixes
- **Error simulation**: Graceful handling of sensor failures and missing entities
- **State trigger validation**: Proper PyScript trigger syntax throughout
- **Async pattern verification**: Correct async/await usage in all applicable functions

## Security
This is a home automation system designed for defensive/monitoring purposes only. All code is for legitimate smart home functionality including lighting control, energy management, sleep optimization, and convenience features. The system includes comprehensive error handling and safe defaults to prevent unintended behavior.

## Entity Discovery & Verification

### **Verified Entities via Home Assistant API**
**Lights (6 entities):**
- `light.bathroom_light` ✅
- `light.bedroom_light` ✅ (fixed from incorrect `light.bedroom_light_light`)
- `light.closet_strip_light` ✅
- `light.kitchen_light` ✅
- `light.kitchen_strip_light` ✅
- `light.livingroom_light` ✅

**Motion Sensors (7 entities):**
- `binary_sensor.bathroom_motion_sensor` ✅
- `binary_sensor.bedroom_motion` ✅
- `binary_sensor.closet_motion_sensor` ✅
- `binary_sensor.kitchen_motion_sensor` ✅
- `binary_sensor.espkitchen_kitchen_motion_pir_sensor` ✅
- `binary_sensor.espdesktop_pir_sensor` ✅
- `binary_sensor.desktop_vibration_chair` ✅

**Safety Sensors:**
- `binary_sensor.wifi_smoke_alarm_smoke` ✅
- `binary_sensor.main_door_sensor` ✅
- `binary_sensor.livingroom_door_sensor` ✅
- `binary_sensor.fridge_door_sensor` ✅

**Smart Switches (50+ entities):**
- Essential appliances: `switch.water_heater_plug`, `switch.washer_machine_plug`
- Desktop power strips: `switch.desktop_strip_plug_socket_1-5`
- Ventilation: `light.bathroom_fan_dimmer`, `switch.fan_stractor_kitchen`, `switch.fan_closet_plug`
- Entertainment: `switch.projector_plug_socket`
- And many more for comprehensive home automation

## Home Assistant API Integration

### **Using the REST API (Recommended for Development)**

**Basic Authentication (No Token Needed for Local Development):**
```bash
# Simple entity state check
curl "http://YOUR_HA_IP:8123/api/states/light.kitchen_light"

# Get all entities of a domain
curl "http://YOUR_HA_IP:8123/api/states" | grep '"entity_id":"light\.'
```

**With Long-lived Access Token (For Production):**
```bash
# Create token: Profile → Security → Long-lived access tokens
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://YOUR_HA_IP:8123/api/states"
```

**Entity Discovery Commands:**
```bash
# List all lights
curl -s "http://YOUR_HA_IP:8123/api/states" | grep -o '"entity_id":"[^"]*"' | grep "light\." | sort

# List all motion sensors
curl -s "http://YOUR_HA_IP:8123/api/states" | grep -o '"entity_id":"[^"]*"' | grep "binary_sensor\." | sort

# List all switches
curl -s "http://YOUR_HA_IP:8123/api/states" | grep -o '"entity_id":"[^"]*"' | grep "switch\." | sort

# Check specific entity state
curl "http://YOUR_HA_IP:8123/api/states/input_select.house_mode"
```

**Alternative Methods (No Token Required):**
- **Home Assistant UI**: Developer Tools → States (browse all entities)
- **Local Network Access**: Direct API calls when on same network
- **File Analysis**: Review existing PyScript code for entity references

### **API Benefits for Development:**
- ✅ **Real-time entity verification** - confirm entities exist and are accessible
- ✅ **State monitoring** - see current values, last_changed timestamps
- ✅ **Entity discovery** - find available devices and sensors
- ✅ **Debugging assistance** - verify automation triggers and states
- ✅ **Code accuracy** - write automations using verified entity names

## Recent Enhancements (Latest Session)
- ✅ **5-second smooth fade-out transitions** applied to all motion lighting
- ✅ **Smart alarm system** with sleep cycle optimization and 4-phase wake-up
- ✅ **Smart morning routine** triggered by closet motion with time conditions
- ✅ **Smart arrival detection** with 5-minute buffer for door sensor
- ✅ **Enhanced climate control** with PM2.5 air purifier management
- ✅ **Emergency smoke alarm system** with automatic safety response
- ✅ **8 PM evening lighting adjustment** for automatic dim and warm settings
- ✅ **Entity verification via API** - confirmed all automation targets exist
- ✅ **PyScript best practices** implementation throughout codebase
- ✅ **Comprehensive error handling** and logging standardization
- ✅ **Cross-module function call fixes** with proper `pyscript.` prefixes
- ✅ **Brightness type casting** fixed at source for HA compatibility
- ✅ **Async pattern improvements** for non-blocking operations

## Notes and Best Practices
- Do not leave empty spacer and leave a new line at the end of all files
