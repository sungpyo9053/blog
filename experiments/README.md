# Measured experiments

Reproduction code and raw results behind the HuntLab Physical AI / ROS 2 lessons.
Each folder runs in a pinned Docker image (ROS 2 versions fixed, usually 5 runs) so anyone can re-check the numbers.

Write-ups that explain each result, and what to do about it:

- English: [ROS 2 troubleshooting guide](https://huntlab.app/ros-2-troubleshooting-guide/)
- 한국어: [ROS 2 문제 해결 모음](https://huntlab.app/ros2-troubleshooting/)

| experiment | write-up |
|---|---|
| [`colcon-build-executor-sequential-memory-budget`](colcon-build-executor-sequential-memory-budget/) | [article](https://huntlab.app/colcon-build-executor-sequential-memory-budget/) |
| [`colcon-build-slow-overlay-colcon-ignore-symlink-install-order`](colcon-build-slow-overlay-colcon-ignore-symlink-install-order/) | [article](https://huntlab.app/colcon-build-slow-overlay-colcon-ignore-symlink-install-order/) |
| [`gymnasium-reset-seed-every-episode-evaluation-variance`](gymnasium-reset-seed-every-episode-evaluation-variance/) | write-up coming |
| [`gymnasium-step-observation-buffer-reuse-replay-aliasing`](gymnasium-step-observation-buffer-reuse-replay-aliasing/) | write-up coming |
| [`physical-ai-observation-action-feedback`](physical-ai-observation-action-feedback/) | [article](https://huntlab.app/physical-ai-observation-action-feedback/) |
| [`ros2-deadline-qos-average-rate-vs-max-interval`](ros2-deadline-qos-average-rate-vs-max-interval/) | write-up coming |
| [`ros2-distro-choice-iron-humble-remaining-support-months`](ros2-distro-choice-iron-humble-remaining-support-months/) | write-up coming |
| [`ros2-docker-discovery-range-static-peers-combinations`](ros2-docker-discovery-range-static-peers-combinations/) | write-up coming |
| [`ros2-liveliness-lease-duration-sensor-monitoring`](ros2-liveliness-lease-duration-sensor-monitoring/) | write-up coming |
| [`ros2-liveliness-lease-duration-vs-deadline-topic-stall`](ros2-liveliness-lease-duration-vs-deadline-topic-stall/) | [article](https://huntlab.app/ros2-liveliness-lease-duration-vs-deadline-topic-stall/) |
| [`ros2-local-setup-vs-setup-bash-fresh-terminal-package-count`](ros2-local-setup-vs-setup-bash-fresh-terminal-package-count/) | write-up coming |
| [`ros2-message-filter-laser-stamp-clock-mismatch`](ros2-message-filter-laser-stamp-clock-mismatch/) | [article](https://huntlab.app/ros2-message-filter-laser-stamp-clock-mismatch/) |
| [`ros2-nested-message-array-vs-primitive-arrays-serialization`](ros2-nested-message-array-vs-primitive-arrays-serialization/) | write-up coming |
| [`ros2-real-time-factor-vs-real-time-computing-deadline`](ros2-real-time-factor-vs-real-time-computing-deadline/) | [article](https://huntlab.app/ros2-real-time-factor-vs-real-time-computing-deadline/) |
| [`ros2-transient-local-late-joiner-sample-age-lifespan`](ros2-transient-local-late-joiner-sample-age-lifespan/) | [article](https://huntlab.app/ros2-transient-local-late-joiner-sample-age-lifespan/) |
| [`ros2-wifi-ip-fragment-buffer-ipfrag-time-budget`](ros2-wifi-ip-fragment-buffer-ipfrag-time-budget/) | write-up coming |
| [`tf-frame-offset-transform-direction-double-error`](tf-frame-offset-transform-direction-double-error/) | write-up coming |
| [`tf2-humble-0-25-23-wait-for-transform-deadlock`](tf2-humble-0-25-23-wait-for-transform-deadlock/) | write-up coming |

Articles are drafted with AI assistance; measurements come from the harness in each folder, and every number
in a write-up's measured section is checked against these results. Found a mistake? Open an issue.
