#!/usr/bin/env python3
"""쿼터니언 성분 순서(x,y,z,w vs w,x,y,z)를 섞었을 때 tf2가 실제로 돌려주는 자세를 잰다.

ROS 2 Jazzy ros-base 컨테이너(네트워크 없음)에서 실행한다.
- 설치 상태: tf_transformations, transforms3d가 ros-base에 있는지 import와 dpkg로 확인한다.
- 회전 결과: geometry_msgs/TransformStamped를 tf2_ros.Buffer에 넣고 lookup_transform으로 다시
  꺼낸 뒤, 전방축(1,0,0)·좌측축(0,1,0)·상방축(0,0,1)을 그 변환으로 돌려 회전 행렬을 얻는다.
  정상 순서와 순서 실수의 회전 행렬 사이 각도를 tf2 출력에서 계산한다.
- 예측식 2*acos(|sin(theta)|/2)는 비교 대상으로만 계산하며 결과값을 미리 적지 않는다.
각 측정은 JSON 한 줄로 출력한다.
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
import time

from geometry_msgs.msg import Quaternion, TransformStamped
import rclpy.time
import tf2_ros

YAWS_DEG = [0, 30, 45, 90, 135, 180, -90, -150]


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def module_status(name, deb):
    spec = importlib.util.find_spec(name)
    probe = subprocess.run(["dpkg-query", "-W", "-f=${Status} ${Version}", deb],
                           capture_output=True, text=True)
    return {"module": name, "importable": spec is not None, "deb": deb,
            "dpkg": probe.stdout.strip() if probe.returncode == 0 else "not-installed"}


# transforms3d가 이미지에 있으면 실제 함수를, 없으면 같은 정의(축 'sxyz', 반환 w,x,y,z)의 yaw 식을 쓴다.
_T3D = None
if importlib.util.find_spec("transforms3d") is not None:
    try:
        import transforms3d.euler as _T3D
    except Exception as exc:  # 버전 조합 문제(np.float 등)도 측정 결과로 남긴다.
        emit("transforms3d_import_error", error=repr(exc))
        _T3D = None


def w_first_from_yaw(theta):
    """transforms3d.euler.euler2quat(0, 0, theta)와 같은 순서 (w, x, y, z)."""
    if _T3D is not None:
        return [float(v) for v in _T3D.euler2quat(0.0, 0.0, theta)], "transforms3d.euler.euler2quat"
    return [math.cos(theta / 2), 0.0, 0.0, math.sin(theta / 2)], "w_first_yaw_formula(emulated)"


def x_last_from_yaw(theta):
    """ROS 2 / tf_transformations 순서 (x, y, z, w)."""
    return [0.0, 0.0, math.sin(theta / 2), math.cos(theta / 2)]


class Tf2Probe:
    """쿼터니언 메시지를 tf2 Buffer에 넣고 다시 꺼내 축 벡터를 회전시킨다."""

    def __init__(self):
        self.buffer = tf2_ros.Buffer()
        self.count = 0

    def store(self, quat):
        self.count += 1
        child = f"probe_{self.count}"
        msg = TransformStamped()
        msg.header.frame_id = "base_link"
        msg.child_frame_id = child
        msg.transform.rotation = quat
        self.buffer.set_transform_static(msg, "experiment")
        try:
            return self.buffer.lookup_transform("base_link", child, rclpy.time.Time())
        except tf2_ros.TransformException as exc:
            return repr(exc)

    def matrix(self, quat):
        """(tf2가 돌려준 쿼터니언 x,y,z,w, 회전 행렬, 오류) — 행렬 열은 tf2 결과로 돌린 x·y·z축."""
        got = self.store(quat)
        if isinstance(got, str):
            return None, None, got
        q = got.transform.rotation
        cols = [rotate((q.x, q.y, q.z, q.w), axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        return [q.x, q.y, q.z, q.w], [[cols[c][r] for c in range(3)] for r in range(3)], None


def rotate(q, v):
    """tf2 lookup 결과 쿼터니언(x,y,z,w)으로 벡터를 회전: v' = q v q*."""
    x, y, z, w = q
    vx, vy, vz = v
    # t = 2 * cross(q.xyz, v); v' = v + w t + cross(q.xyz, t)
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def angle_between(r1, r2):
    trace = sum(r1[k][i] * r2[k][i] for i in range(3) for k in range(3))
    return math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1) / 2))))


def heading_deg(r):
    return math.degrees(math.atan2(r[1][0], r[0][0]))


def r6(v):
    return round(v, 6) + 0.0  # -0.0 표기 제거


def msg_from_index(arr):
    """흔한 실수 지점: 리스트 인덱스로 메시지를 채운다 (x=q[0] ... w=q[3])."""
    return Quaternion(x=arr[0], y=arr[1], z=arr[2], w=arr[3])


def main():
    started = time.monotonic()
    emit("environment", ros_distro=os.environ.get("ROS_DISTRO", ""), python=sys.version.split()[0],
         rosdistro_var_set="ROSDISTRO" in os.environ)
    for name, deb in (("tf_transformations", f"ros-{os.environ.get('ROS_DISTRO', '')}-tf-transformations"),
                      ("transforms3d", "python3-transforms3d"), ("numpy", "python3-numpy")):
        emit("package", **module_status(name, deb))

    # README 설치 명령의 변수명($ROSDISTRO)과 ROS 2 설정 변수($ROS_DISTRO)를 셸에서 그대로 확장해 본다.
    env = {k: v for k, v in os.environ.items() if k != "ROSDISTRO"}
    for template in ("ros-$ROSDISTRO-tf-transformations", "ros-${ROS_DISTRO}-tf-transformations"):
        out = subprocess.run(["bash", "-c", f"echo {template}"], env=env, capture_output=True, text=True)
        emit("install_name_expansion", template=template, expanded=out.stdout.strip())

    probe = Tf2Probe()
    caught_by_norm = 0
    for deg in YAWS_DEG:
        theta = math.radians(deg)
        good_arr = x_last_from_yaw(theta)
        wfirst_arr, producer = w_first_from_yaw(theta)
        _, r_good, e1 = probe.matrix(msg_from_index(good_arr))
        # 실수 A: w,x,y,z 배열을 인덱스로 x,y,z,w 메시지에 넣음 (transforms3d -> geometry_msgs)
        _, r_a, e2 = probe.matrix(msg_from_index(wfirst_arr))
        # 실수 B: x,y,z,w 배열을 w,x,y,z 소비자처럼 읽음 (w=arr[0], x=arr[1], ...)
        _, r_b, e3 = probe.matrix(Quaternion(x=good_arr[1], y=good_arr[2], z=good_arr[3], w=good_arr[0]))
        if None in (r_good, r_a, r_b):
            emit("yaw_case_error", yaw_deg=deg, errors=[e1, e2, e3])
            continue
        predicted = math.degrees(2 * math.acos(min(1.0, abs(math.sin(theta)) / 2)))
        norm_mistake = sum(c * c for c in wfirst_arr)
        caught_by_norm += abs(norm_mistake - 1) > 1e-6
        err_a, err_b = angle_between(r_good, r_a), angle_between(r_good, r_b)
        # 접두어: ok=정상 순서, A=w,x,y,z를 x,y,z,w로 넣음, B=x,y,z,w를 w,x,y,z로 읽음
        emit("yaw_case", yaw_deg=deg, producer=producer, norm_sq_A=r6(norm_mistake),
             heading_deg={"ok": r6(heading_deg(r_good)), "A": r6(heading_deg(r_a)), "B": r6(heading_deg(r_b))},
             up_z={"ok": r6(r_good[2][2]), "A": r6(r_a[2][2]), "B": r6(r_b[2][2])},
             error_deg={"A": r6(err_a), "B": r6(err_b)}, predicted_deg=r6(predicted),
             match=abs(err_a - predicted) < 1e-6 and abs(err_b - predicted) < 1e-6)

    # 대조군: 크기가 1이 아닌 쿼터니언을 tf2에 넣으면 무엇이 저장되는지 (정규화 검사는 크기만 본다)
    q_bad, r_bad, err_bad = probe.matrix(Quaternion(x=0.0, y=0.0, z=1.0, w=1.0))
    emit("denormalized_control", sent_xyzw=[0, 0, 1, 1], returned_xyzw=q_bad and [r6(v) for v in q_bad],
         heading_deg=r_bad and r6(heading_deg(r_bad)), error=err_bad)

    # 반례: 한 칸 순환해도 같은 회전이 되는 입력은 순서 실수를 잡지 못한다.
    for name, arr in (("all_equal", [0.5, 0.5, 0.5, 0.5]), ("alternating_sign", [0.5, -0.5, 0.5, -0.5]),
                      ("yaw180", [0.0, 0.0, 1.0, 0.0]), ("identity", [0.0, 0.0, 0.0, 1.0]),
                      ("yaw90", [0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5)])):
        shifted = arr[1:] + arr[:1]  # w,x,y,z 소비자가 x,y,z,w 배열을 읽었을 때의 자리 이동과 같다
        _, r_orig, _ = probe.matrix(msg_from_index(arr))
        _, r_shift, _ = probe.matrix(msg_from_index(shifted))
        comp_diff = sum((a - b) ** 2 for a, b in zip(arr, shifted))
        rot_diff = angle_between(r_orig, r_shift)
        emit("test_input", name=name, xyzw=[r6(v) for v in arr], shifted=[r6(v) for v in shifted],
             comp_diff_sq=r6(comp_diff), rot_diff_deg=r6(rot_diff),
             fwd=[r6(r_orig[i][0]) for i in range(3)], left=[r6(r_orig[i][1]) for i in range(3)],
             caught=rot_diff > 1e-6)

    emit("summary", yaw_cases=len(YAWS_DEG), mistakes_caught_by_norm_check=caught_by_norm,
         transforms_stored=probe.count, elapsed_s=round(time.monotonic() - started, 3))


if __name__ == "__main__":
    main()
