# ROS 2 Troubleshooting Guide — outline (draft 0, 2026-10-07)

Status: demand check. Waitlist form is live on every /en/ post and the English hub
(`deploy/mu-plugins/huntlab-guide-waitlist.php`). Write the full guide only after the first sign-ups.
Every claim comes from an existing measured post or its `experiments/<slug>` data; nothing new is asserted.

Format: English PDF + the reproduction scripts (zip). Price to be decided by the owner ($19–29).

## Chapters → source posts

1. **Start here: the 60-second triage.** Which symptom family you are in (no messages / wrong values /
   stale transforms / slow builds). Built from the hub groups in `huntlab-hub.php`.
2. **"Message Filter dropping message" and extrapolation errors.** One subtraction to find the
   mismatched clock; sign tells which node is wrong.
   Sources: ros2-message-filter-laser-stamp-clock-mismatch, /en/ros2-message-filter-dropping-message-clock-mismatch.
3. **When `map -> odom` stops after an upgrade.** Bisecting apt upgrades with `dpkg-query` diff;
   case study: Humble tf2 0.25.22 → 0.25.23 (ROBOTIS-GIT/turtlebot3#1155, ros2/geometry2#995).
   Needs our own reproduction before it ships (measured section rule).
4. **Topic exists but no data arrives: QoS.** Compatibility before queue depth; deadline period rules;
   transient_local late joiners.
   Sources: ros2-qos-compatibility-before-queue-depth, ros2-qos-deadline-period-compatibility,
   ros2-transient-local-late-joiner-sample-age-lifespan, /en/ros2-transient-local-late-joiner-lifespan.
5. **Is the sensor dead or just quiet? Liveliness vs deadline.**
   Sources: ros2-liveliness-lease-duration-vs-deadline-topic-stall, /en/ros2-liveliness-vs-deadline-detect-stopped-sensor-topic.
6. **Simulation time traps.** Time 0 before /clock, backward jumps, real-time-factor latency.
   Sources: ros2-sim-time-zero-uninitialized-first-dt-spike, ros2-simulation-time-backward-jump-timer,
   ros2-sim-time-real-time-factor-latency-budget.
7. **Frames and units.** Optical frames, compass bearing → ENU yaw, covariance index, mm/s vs m/s.
   Sources: ros-camera-optical-frame-axis-mapping-check, compass-bearing-to-ros-enu-yaw,
   ros-pose-covariance-row-major-index, ros-velocity-unit-boundary-test.
8. **colcon builds that freeze or crawl.** `--executor sequential` still runs make -jN; overlays,
   COLCON_IGNORE, --symlink-install measured.
   Sources: colcon-build-executor-sequential-memory-budget, colcon-build-slow-overlay-colcon-ignore-symlink-install-order,
   /en/colcon-build-executor-sequential-makeflags-memory-time, /en/colcon-build-slow-overlay-colcon-ignore-symlink-install-measured.

## Owner decisions before selling
- Payment platform account (Gumroad or Lemon Squeezy) and seller name.
- Price.
- Launch email: send from which address (one email to the waitlist, then delete the list on request).
