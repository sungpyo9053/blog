from launch import LaunchDescription
from launch.actions import ExecuteProcess
import os
def generate_launch_description():
    kw = {"sigterm_timeout": "15", "sigkill_timeout": "15"} if os.environ.get("KW") else {}
    return LaunchDescription([ExecuteProcess(cmd=["python3", "-u", "/sd/n.py", "classic", os.environ.get("SLOW", "8")], output="screen", **kw)])
