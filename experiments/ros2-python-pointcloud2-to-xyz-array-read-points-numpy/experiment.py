#!/usr/bin/env python3
"""PointCloud2 -> xyz 배열 실측 (ROS 2 Jazzy, sensor_msgs_py).

합성 클라우드를 만들어 rclpy publish->subscribe로 한 번 왕복시킨 뒤,
받은 메시지에서 점 개수·바이트 위치·skip_nans/is_dense·타입 검사·inf·reshape·uvs·row_step
동작을 실행 중에 재서 JSON 줄로 출력한다. 결과 값은 코드에 적지 않고 모두 계산·관측한다.
"""
import json
import struct
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
from numpy.lib import recfunctions as rfn

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2 as pc2
from ament_index_python.packages import get_package_share_directory

DEADLINE = 50.0
T0 = time.monotonic()

# 입력 조건 (research.md 자체 예제와 같은 설명용 가정)
WIDTH, HEIGHT, POINT_STEP = 640, 480, 16
NAN_POINTS = 40000
PROBE_INDICES = [0, 1000, WIDTH * HEIGHT - 1]
SEED = 23782


def _finite(value):
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite(v) for v in value]
    return value


def emit(name, **values):
    print(json.dumps(_finite({"measure": name, **values}), ensure_ascii=False, allow_nan=False), flush=True)


def outcome(fn):
    """함수를 실행해 결과 shape/dtype 또는 예외 종류·문구를 돌려준다."""
    try:
        arr = fn()
        return {"ok": True, "shape": list(arr.shape), "dtype": str(arr.dtype)}
    except Exception as exc:  # noqa: BLE001 - 예외 종류 자체가 측정 대상
        return {"ok": False, "error": type(exc).__name__, "message": str(exc)[:160]}


def make_cloud(fields, point_step, width, height, data, is_dense, row_step=None):
    msg = PointCloud2()
    msg.header.frame_id = "camera"
    msg.height, msg.width = height, width
    msg.fields = [PointField(name=n, offset=o, datatype=t, count=1) for n, o, t in fields]
    msg.is_bigendian = sys.byteorder != "little"
    msg.point_step = point_step
    msg.row_step = row_step if row_step is not None else point_step * width
    msg.data = bytes(data)
    msg.is_dense = is_dense
    return msg


F32, U16 = PointField.FLOAT32, PointField.UINT16
XYZ_FIELDS = [("x", 0, F32), ("y", 4, F32), ("z", 8, F32)]


def xyz_buffer(xyz, point_step):
    """(N,3) float32를 point_step 간격(남는 바이트는 0 패딩)의 바이트열로 만든다."""
    dt = np.dtype({"names": ["x", "y", "z"], "formats": ["<f4"] * 3,
                   "offsets": [0, 4, 8], "itemsize": point_step})
    buf = np.zeros(len(xyz), dtype=dt)
    buf["x"], buf["y"], buf["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    return buf.tobytes()


def package_version(name):
    root = ET.parse(get_package_share_directory(name) + "/package.xml").getroot()
    return root.findtext("version")


emit("environment", sensor_msgs_py=package_version("sensor_msgs_py"),
     numpy=np.__version__, python=sys.version.split()[0], byteorder=sys.byteorder)

# ---------------------------------------------------------------- 0. 원본 클라우드 생성
rng = np.random.default_rng(SEED)
n_points = WIDTH * HEIGHT
v, u = np.divmod(np.arange(n_points), WIDTH)
xyz = np.stack([u * 0.01, v * 0.01, 1.0 + (np.arange(n_points) % 97) * 0.001], axis=1).astype(np.float32)
nan_idx = rng.choice(n_points, NAN_POINTS, replace=False)
xyz_nan = xyz.copy()
xyz_nan[nan_idx, rng.integers(0, 3, NAN_POINTS)] = np.nan  # 점마다 x/y/z 중 한 칸만 NaN
sent = make_cloud(XYZ_FIELDS, POINT_STEP, WIDTH, HEIGHT, xyz_buffer(xyz_nan, POINT_STEP), is_dense=False)

# ---------------------------------------------------------------- 1. rclpy 왕복
rclpy.init()
node = Node("pointcloud2_xyz_probe")
received = []
node.create_subscription(PointCloud2, "probe_cloud", received.append, 1)
pub = node.create_publisher(PointCloud2, "probe_cloud", 1)
attempts = 0
while not received and time.monotonic() - T0 < 20.0:
    if pub.get_subscription_count() > 0:
        pub.publish(sent)
        attempts += 1
    rclpy.spin_once(node, timeout_sec=0.2)
emit("roundtrip", received=bool(received), publish_attempts=attempts,
     seconds_to_receive=round(time.monotonic() - T0, 3))
if not received:
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(1)
cloud = received[0]
node.destroy_node()
rclpy.shutdown()

z_field = next(f for f in cloud.fields if f.name == "z")
emit("received_layout", width=cloud.width, height=cloud.height, point_step=cloud.point_step,
     row_step=cloud.row_step, is_dense=cloud.is_dense, data_len=len(cloud.data),
     fields=[[f.name, f.offset, f.datatype, f.count] for f in cloud.fields],
     data_type=type(cloud.data).__name__,
     points_width_x_height=cloud.width * cloud.height,
     data_len_equals_w_h_step=len(cloud.data) == cloud.width * cloud.height * cloud.point_step,
     padding_bytes_total=cloud.width * cloud.height * (cloud.point_step - 4 * len(cloud.fields)))

# ---------------------------------------------------------------- 2. 바이트 위치 검산
raw = bytes(cloud.data)
arr_all = pc2.read_points_numpy(cloud, field_names=["x", "y", "z"], skip_nans=False)
probes = []
for i in PROBE_INDICES:
    pos = i * cloud.point_step + z_field.offset
    z_struct = struct.unpack_from("<f", raw, pos)[0]
    probes.append({"index": i, "z_byte_start": pos, "row": i // cloud.width, "col": i % cloud.width,
                   "z_struct": z_struct, "z_read_points_numpy": float(arr_all[i, 2]),
                   "equal": bool(z_struct == float(arr_all[i, 2]) or (np.isnan(z_struct) and np.isnan(arr_all[i, 2])))})
z_strided = np.ndarray((n_points,), dtype="<f4", buffer=raw, offset=z_field.offset, strides=(cloud.point_step,))
both_nan = np.isnan(z_strided) & np.isnan(arr_all[:, 2])
emit("byte_position", probes=probes,
     all_points_compared=int(n_points),
     z_mismatches=int(np.count_nonzero(~((z_strided == arr_all[:, 2]) | both_nan))),
     xyz_array_shape=list(arr_all.shape), xyz_array_dtype=str(arr_all.dtype), xyz_array_nbytes=int(arr_all.nbytes))

cols = pc2.read_points_numpy(cloud, field_names=["z", "x"], skip_nans=False)
emit("field_order", requested=["z", "x"], first_row=[float(c) for c in cols[1]],
     matches_z_then_x=bool(cols[1, 0] == arr_all[1, 2] and cols[1, 1] == arr_all[1, 0]))

# ---------------------------------------------------------------- 3. skip_nans vs is_dense
nan_rows_in_input = int(np.isnan(arr_all).any(axis=1).sum())
res = {}
for dense in (False, True):
    cloud.is_dense = dense
    out = pc2.read_points_numpy(cloud, field_names=["x", "y", "z"], skip_nans=True)
    res[str(dense)] = {"rows": int(out.shape[0]), "rows_with_nan": int(np.isnan(out).any(axis=1).sum())}
cloud.is_dense = False
emit("skip_nans_vs_is_dense", input_rows=int(n_points), input_rows_with_nan=nan_rows_in_input,
     is_dense_false=res["False"], is_dense_true=res["True"],
     manual_isfinite_rows=int(np.isfinite(arr_all).all(axis=1).sum()))

# ---------------------------------------------------------------- 4. 같은 타입 검사 (Jazzy: fields[0] 기준)
LIDAR_STEP, N_L = 32, 16
lidar_dt = np.dtype({"names": ["x", "y", "z", "intensity", "ring"],
                     "formats": ["<f4", "<f4", "<f4", "<f4", "<u2"],
                     "offsets": [0, 4, 8, 12, 16], "itemsize": LIDAR_STEP})
lidar = np.zeros(N_L, dtype=lidar_dt)
lidar["x"], lidar["y"], lidar["z"] = np.arange(N_L), np.arange(N_L) * 2, np.arange(N_L) * 3
lidar["intensity"], lidar["ring"] = np.arange(N_L) * 0.5, np.arange(N_L) % 4 + 100
lidar_cloud = make_cloud([("x", 0, F32), ("y", 4, F32), ("z", 8, F32), ("intensity", 12, F32), ("ring", 16, U16)],
                         LIDAR_STEP, N_L, 1, lidar.tobytes(), is_dense=True)
ring_pos = 10 * LIDAR_STEP + 16
emit("type_check_A_first_x_select_xyz",
     result=outcome(lambda: pc2.read_points_numpy(lidar_cloud, field_names=["x", "y", "z"])),
     ring10_byte_start=ring_pos, ring10_struct=struct.unpack_from("<H", lidar_cloud.data, ring_pos)[0],
     ring10_read_points=int(pc2.read_points(lidar_cloud, field_names=["ring"])["ring"][10]))
emit("type_check_B_all_fields", result=outcome(lambda: pc2.read_points_numpy(lidar_cloud)))
emit("type_check_B_x_ring", result=outcome(lambda: pc2.read_points_numpy(lidar_cloud, field_names=["x", "ring"])))

c_dt = np.dtype({"names": ["ring", "x", "y", "z"], "formats": ["<u2", "<f4", "<f4", "<f4"],
                 "offsets": [0, 4, 8, 12], "itemsize": 16})
c_buf = np.zeros(N_L, dtype=c_dt)
c_buf["ring"], c_buf["x"], c_buf["y"], c_buf["z"] = 7, np.arange(N_L), 1.0, 2.0
c_cloud = make_cloud([("ring", 0, U16), ("x", 4, F32), ("y", 8, F32), ("z", 12, F32)], 16, N_L, 1,
                     c_buf.tobytes(), is_dense=True)
emit("type_check_C_first_u16_select_xyz",
     read_points_numpy=outcome(lambda: pc2.read_points_numpy(c_cloud, field_names=["x", "y", "z"])),
     read_points_plus_structured_to_unstructured=outcome(
         lambda: rfn.structured_to_unstructured(pc2.read_points(c_cloud, field_names=["x", "y", "z"]))))

# ---------------------------------------------------------------- 5. inf는 skip_nans로 걸러지는가
small = np.array([[1, 2, 3], [np.inf, 0, 1], [np.nan, 0, 1], [4, 5, -np.inf], [6, 7, 8]], dtype=np.float32)
inf_cloud = make_cloud(XYZ_FIELDS, 16, len(small), 1, xyz_buffer(small, 16), is_dense=False)
out = pc2.read_points_numpy(inf_cloud, field_names=["x", "y", "z"], skip_nans=True)
emit("inf_with_skip_nans", input_rows=len(small), input_rows_with_inf=int(np.isinf(small).any(axis=1).sum()),
     input_rows_with_nan=int(np.isnan(small).any(axis=1).sum()), output_rows=int(out.shape[0]),
     output_rows_with_inf=int(np.isinf(out).any(axis=1).sum()),
     isfinite_mask_rows=int(np.isfinite(small).all(axis=1).sum()))

# ---------------------------------------------------------------- 6. reshape_organized_cloud 축 순서
H2, W3 = 2, 3
grid = np.array([[c, r, 0] for r in range(H2) for c in range(W3)], dtype=np.float32)  # x=열, y=행
org = make_cloud(XYZ_FIELDS, 16, W3, H2, xyz_buffer(grid, 16), is_dense=False)
shaped = pc2.read_points(org, field_names=["x", "y", "z"], reshape_organized_cloud=True)
rows_col_row = [[[int(p["x"]), int(p["y"])] for p in row] for row in shaped]
manual = pc2.read_points_numpy(org, field_names=["x", "y", "z"]).reshape(org.height, org.width, 3)
emit("reshape_organized", height=org.height, width=org.width, shape=list(shaped.shape),
     rows_col_row=rows_col_row,
     rows_spanning_two_image_rows=sum(len({r for _, r in row}) > 1 for row in rows_col_row),
     manual_reshape_shape=list(manual.shape),
     manual_rows_spanning_two_image_rows=int(sum(len(set(row[:, 1].tolist())) > 1 for row in manual)))
grid_nan = grid.copy()
grid_nan[4, 0] = np.nan
org_nan = make_cloud(XYZ_FIELDS, 16, W3, H2, xyz_buffer(grid_nan, 16), is_dense=False)
emit("reshape_after_skip_nans",
     result=outcome(lambda: pc2.read_points(org_nan, field_names=["x", "y", "z"], skip_nans=True,
                                            reshape_organized_cloud=True)))

# ---------------------------------------------------------------- 7. uvs는 NaN 제거 뒤 인덱싱
ids = np.array([[np.nan, 0, 0]] + [[0, k, 0] for k in range(1, 5)], dtype=np.float32)  # y = 원래 인덱스, 점 0의 x만 NaN
uv_cloud = make_cloud(XYZ_FIELDS, 16, len(ids), 1, xyz_buffer(ids, 16), is_dense=False)
got = pc2.read_points(uv_cloud, field_names=["x", "y"], skip_nans=True, uvs=[0])
got_raw = pc2.read_points(uv_cloud, field_names=["x", "y"], skip_nans=False, uvs=[0])
emit("uvs_after_skip_nans", requested_uvs=[0], skip_nans_true_original_index=[int(p["y"]) for p in got],
     skip_nans_false_original_index=[int(p["y"]) for p in got_raw])

# ---------------------------------------------------------------- 8. row_step 행 끝 패딩
ROW_PAD = 8
pad_xyz = np.array([[c + 10 * r, r, 0] for r in range(H2) for c in range(W3)], dtype=np.float32)
rows = xyz_buffer(pad_xyz, 16)
padded = b"".join(rows[r * W3 * 16:(r + 1) * W3 * 16] + bytes(ROW_PAD) for r in range(H2))
pad_cloud = make_cloud(XYZ_FIELDS, 16, W3, H2, padded, is_dense=False, row_step=W3 * 16 + ROW_PAD)
pad_out = pc2.read_points_numpy(pad_cloud, field_names=["x", "y", "z"])
row1_start = pad_cloud.row_step * 1
emit("row_step_padding", width=W3, height=H2, point_step=16, row_step=pad_cloud.row_step,
     data_len=len(pad_cloud.data), width_x_height_x_step=W3 * H2 * 16,
     row1_col0_true_x=struct.unpack_from("<f", padded, row1_start)[0],
     row1_col0_read_points_numpy_x=float(pad_out[W3, 0]),
     row1_col0_byte_by_row_step=row1_start, row1_col0_byte_assumed=W3 * 16,
     rows_mismatched=int(np.count_nonzero((pad_out[:, 0] != pad_xyz[:, 0]).reshape(H2, W3).any(axis=1))))
short_cloud = make_cloud(XYZ_FIELDS, 16, W3, H2, rows[:-16], is_dense=False)
emit("data_too_short", data_len=len(short_cloud.data), needed=W3 * H2 * 16,
     result=outcome(lambda: pc2.read_points_numpy(short_cloud, field_names=["x", "y", "z"])))

emit("done", elapsed_seconds=round(time.monotonic() - T0, 3), within_deadline=time.monotonic() - T0 < DEADLINE)
