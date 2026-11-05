#!/usr/bin/env python3
# Reads a bag with rosbag2_py and reports count, first missing sequence number and the gaps.
import sys, json, rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image
uri, n = sys.argv[1], int(sys.argv[2])
info = rosbag2_py.Info().read_metadata(uri, '')
r = rosbag2_py.SequentialCompressionReader() if info.compression_mode else rosbag2_py.SequentialReader()
r.open(rosbag2_py.StorageOptions(uri=uri, storage_id=info.storage_identifier), rosbag2_py.ConverterOptions('', ''))
seen = []
while r.has_next():
    data = r.read_next()[1]   # (topic, data, timestamp[, ...]) depending on distro
    seen.append(int(deserialize_message(data, Image).header.frame_id))
s = set(seen); missing = [i for i in range(n) if i not in s]
gaps = []
for m in missing:
    if gaps and gaps[-1][1] == m - 1: gaps[-1][1] = m
    else: gaps.append([m, m])
print(json.dumps({'storage': info.storage_identifier, 'compression': info.compression_mode or 'none', 'metadata_count': info.message_count, 'recorded': len(seen), 'unique': len(s), 'missing': len(missing),
                  'first_missing': missing[0] if missing else None, 'n_gaps': len(gaps), 'gaps_head': gaps[:6],
                  'out_of_order': sum(1 for a, b in zip(seen, seen[1:]) if b < a), 'bag_bytes': info.bag_size}))
