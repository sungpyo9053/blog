# tf2 Humble 0.25.22 vs 0.25.23: waitForTransform/setTransform stress (2026-10-08)

Environment: Lightsail runner (2 vCPU, 3 GB), Docker `ubuntu:22.04`, ROS 2 Humble pinned from the
official ROS snapshot repository (`snapshots.ros.org/humble/2026-08-07` → tf2_ros 0.25.22-1jammy.20260804.155840,
`snapshots.ros.org/humble/2026-09-14` → tf2_ros 0.25.23-1jammy.20260907.224752). rmw: default (Fast DDS).

`race.cpp`: one thread calls `Buffer::waitForTransform(map, base, t_i, 50 ms, callback)` for increasing stamps,
another calls `setTransform` for the same stamps. A watchdog prints DEADLOCK if neither counter moves for 3 s,
otherwise OK after 20 s.

Build: `docker build --build-arg SNAP=2026-08-07 -t tf2race:22 .` (and `SNAP=2026-09-14 -t tf2race:23`).
Run: `docker run --rm tf2race:22` five times per version.

| version | run 1 | run 2 | run 3 | run 4 | run 5 |
|---|---|---|---|---|---|
| 0.25.22 | OK 20 s, waits=15920 sets=14738 callbacks=13624 | OK 20 s, 42763 / 34245 / 41035 | OK 20 s, 37044 / 29545 / 36713 | OK 20 s, 14968 / 14288 / 12414 | OK 20 s, 31407 / 22507 / 31122 |
| 0.25.23 | DEADLOCK at 0.1 s, waits=1 sets=0 | DEADLOCK at 0.1 s, 68 / 0 / 0 | DEADLOCK at 0.1 s, 33 / 4 / 4 | DEADLOCK at 0.1 s, 37 / 1 / 1 | DEADLOCK at 0.1 s, 34 / 1 / 1 |

Interpretation (not measured): 0.25.23 (geometry2 commit 50af68fa, "Fix waitForTransform race condition (#966) (#974)")
holds `timer_to_request_map_mutex_` while calling `addTransformableRequest`, while `setTransform` →
`testTransformableRequests` runs the request callback that takes the same mutex — a lock-order inversion.
Matches ros2/geometry2#992 and #995. Not yet confirmed with a debugger backtrace.

More measured ROS 2 troubleshooting: [HuntLab ROS 2 troubleshooting guide](https://huntlab.app/ros-2-troubleshooting-guide/) · [all experiments](../)
