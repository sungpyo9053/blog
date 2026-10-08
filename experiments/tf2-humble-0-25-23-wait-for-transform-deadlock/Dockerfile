FROM ubuntu:22.04
ARG SNAP
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends gnupg ca-certificates dirmngr g++ \
 && gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys 4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA \
 && gpg --export 4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA > /usr/share/keyrings/ros-snapshots.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/ros-snapshots.gpg] http://snapshots.ros.org/humble/${SNAP}/ubuntu jammy main" > /etc/apt/sources.list.d/ros-snap.list \
 && apt-get update && apt-get install -y --no-install-recommends ros-humble-tf2-ros ros-humble-rclcpp \
 && rm -rf /var/lib/apt/lists/*
COPY race.cpp /race.cpp
RUN bash -c 'source /opt/ros/humble/setup.bash && g++ -O1 -std=c++17 /race.cpp -o /race $(for d in /opt/ros/humble/include/*/; do echo -n "-I$d "; done) -L/opt/ros/humble/lib -ltf2_ros -ltf2 -lrclcpp -lrcl -lrcutils -lrmw -lrcpputils -ltracetools -llibstatistics_collector -lmessage_filters -pthread -Wl,-rpath,/opt/ros/humble/lib'
CMD ["bash", "-c", "source /opt/ros/humble/setup.bash && dpkg-query -W -f='${Version}\\n' ros-humble-tf2-ros && /race"]
