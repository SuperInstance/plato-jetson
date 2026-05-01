# SonarVision ↔ plato-jetson Integration

## Status
Active — deployed to plato-jetson world/

## How it works
1. SonarVisionRoom extends Evennia MUD Room with underwater physics
2. Rooms auto-generate descriptions from sonar pings
3. Fish, seabed features, temperature, and visibility respond to depth
4. `sonarping` command re-simulates and updates room description

## Room Chain
```
Coral Shallows (2m) -> Kelp Forest (10m) -> Open Water (25m) -> Deep Shelf (50m) -> Seabed Canyon (80m)
```

## Data Source
Simulated sonar physics (matching marine-gpu-edge bridge), not live sensor data.
Live sensor mode available when Jetson AGX Orin is online.

## Dependencies
- Evennia MUD server (runs on plato-jetson)
- SonarVision physics engine (from sonar-vision repo)
- marine-gpu-edge bridge (for real sensor data)

## See Also
- holodeck-rust/src/sonar_vision.rs (Rust equivalent)
- sonar-vision/sonar_vision/physics/underwater.py
