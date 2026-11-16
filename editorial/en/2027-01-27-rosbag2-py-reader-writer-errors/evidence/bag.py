#!/usr/bin/env python3
# One rosbag2_py case per process: python3 bag.py <case> [args]
# Prints what happened; exceptions are printed as TYPE: message (never hidden).
import os, sys, time, signal, traceback
import rosbag2_py
from rclpy.serialization import serialize_message, deserialize_message
from std_msgs.msg import String
from rosidl_runtime_py.utilities import get_message

T = '/chatter'
TYPE = 'std_msgs/msg/String'


def err(tag, e):
    msg = str(e).strip().replace('\n', ' | ')
    print(f'{tag}: EXC {type(e).__module__}.{type(e).__name__}: {msg[:600]}')


def files(uri, tag=''):
    if not os.path.exists(uri):
        print(f'files{tag}: {uri} does not exist')
        return
    if os.path.isfile(uri):
        print(f'files{tag}: {uri} is a file, {os.path.getsize(uri)} bytes')
        return
    out = []
    for f in sorted(os.listdir(uri)):
        p = os.path.join(uri, f)
        out.append(f'{f}({os.path.getsize(p)})')
    print(f'files{tag}: ' + (' '.join(out) if out else '(empty dir)'))


def sopts(uri, sid):
    if sid == 'none':
        return rosbag2_py.StorageOptions(uri=uri)
    return rosbag2_py.StorageOptions(uri=uri, storage_id=sid)


def topic(name=T, typ=TYPE, fmt='cdr'):
    try:
        return rosbag2_py.TopicMetadata(name=name, type=typ, serialization_format=fmt)
    except TypeError:
        return rosbag2_py.TopicMetadata(id=0, name=name, type=typ, serialization_format=fmt)


def open_writer(uri, sid='none'):
    w = rosbag2_py.SequentialWriter()
    w.open(sopts(uri, sid), rosbag2_py.ConverterOptions('cdr', 'cdr'))
    w.create_topic(topic())
    return w


def write_n(w, n, t0=1_000_000_000):
    for i in range(n):
        w.write(T, serialize_message(String(data=f'msg {i}')), t0 + i * 10_000_000)


def open_reader(uri, sid='none'):
    r = rosbag2_py.SequentialReader()
    r.open(sopts(uri, sid), rosbag2_py.ConverterOptions('', ''))
    return r


def read_all(r):
    types = {t.name: t.type for t in r.get_all_topics_and_types()}
    n, first, last = 0, None, None
    while r.has_next():
        name, data, ts = r.read_next()
        m = deserialize_message(data, get_message(types[name]))
        if first is None:
            first = (m.data, ts)
        last = (m.data, ts)
        n += 1
    return types, n, first, last


case = sys.argv[1]
a = sys.argv[2:]

if case == 'info':
    print('rosbag2_py file:', rosbag2_py.__file__)
    so = rosbag2_py.StorageOptions(uri='x')
    print('StorageOptions(uri=x).storage_id =', repr(so.storage_id))
    print('TopicMetadata init doc:', (rosbag2_py.TopicMetadata.__init__.__doc__ or '').strip().replace('\n', ' | ')[:500])
    for cls in ('SequentialWriter', 'SequentialReader'):
        c = getattr(rosbag2_py, cls)
        print(f'{cls} has close: {hasattr(c, "close")}')
    for fn in ('get_registered_writers', 'get_registered_readers', 'get_default_storage_id'):
        f = getattr(rosbag2_py, fn, None)
        if f is None:
            print(f'{fn}: not in rosbag2_py')
        else:
            try:
                print(f'{fn}(): {f()}')
            except Exception as e:
                err(fn, e)
    print('SequentialWriter.write doc:', (rosbag2_py.SequentialWriter.write.__doc__ or '').strip().replace('\n', ' | ')[:400])

elif case == 'tm_positional':
    try:
        t = rosbag2_py.TopicMetadata(T, TYPE, 'cdr')
        print('positional (name, type, fmt): OK', t.name)
    except Exception as e:
        err('positional (name, type, fmt)', e)
    try:
        t = rosbag2_py.TopicMetadata(name=T, type=TYPE, serialization_format='cdr')
        print('keywords name/type/serialization_format: OK', t.name)
    except Exception as e:
        err('keywords name/type/serialization_format', e)
    try:
        t = rosbag2_py.TopicMetadata(id=0, name=T, type=TYPE, serialization_format='cdr')
        print('keywords id/name/type/serialization_format: OK', t.name)
    except Exception as e:
        err('keywords id/name/type/serialization_format', e)

elif case == 'write':  # uri sid n
    uri, sid, n = a[0], a[1], int(a[2])
    t = time.monotonic()
    try:
        w = open_writer(uri, sid)
    except Exception as e:
        err('open', e); files(uri); sys.exit(0)
    write_n(w, n)
    dt = time.monotonic() - t
    print(f'wrote {n} in {dt:.3f} s')
    files(uri, ' before del')
    mode = a[3] if len(a) > 3 else 'del'
    if mode == 'del':
        del w
        files(uri, ' after del')
    elif mode == 'close':
        try:
            w.close(); files(uri, ' after close()')
        except Exception as e:
            err('close', e)
    elif mode == 'exit':
        print('leaving writer alive, normal interpreter exit')
    elif mode == 'kill':
        print('SIGKILL self'); sys.stdout.flush()
        os.kill(os.getpid(), signal.SIGKILL)
    elif mode == 'osexit':
        print('os._exit(0)'); sys.stdout.flush()
        os._exit(0)

elif case == 'reopen':  # open a writer on an existing uri
    uri, sid = a[0], a[1]
    try:
        w = open_writer(uri, sid)
        print('open on existing dir: OK')
    except Exception as e:
        err('open on existing dir', e)

elif case == 'no_create':
    uri = a[0]
    w = rosbag2_py.SequentialWriter()
    w.open(sopts(uri, 'none'), rosbag2_py.ConverterOptions('cdr', 'cdr'))
    try:
        w.write('/never_created', serialize_message(String(data='x')), 1_000_000_000)
        print('write to uncreated topic: OK')
    except Exception as e:
        err('write to uncreated topic', e)
    del w
    files(uri)

elif case == 'bad_write_args':
    uri = a[0]
    w = open_writer(uri, 'none')
    from rclpy.clock import Clock
    from rclpy.time import Time
    tests = [
        ('timestamp float 1.5', lambda: w.write(T, serialize_message(String(data='x')), 1.5)),
        ('timestamp rclpy Time', lambda: w.write(T, serialize_message(String(data='x')), Time(seconds=1))),
        ('timestamp Time.nanoseconds', lambda: w.write(T, serialize_message(String(data='x')), Time(seconds=2).nanoseconds)),
        ('message object, not bytes', lambda: w.write(T, String(data='x'), 3_000_000_000)),
        ('wrong type bytes (Int32 into String topic)', None),
        ('topic name without slash', lambda: w.write('chatter', serialize_message(String(data='x')), 4_000_000_000)),
    ]
    for name, fn in tests:
        if fn is None:
            from std_msgs.msg import Int32
            fn = lambda: w.write(T, serialize_message(Int32(data=7)), 5_000_000_000)
        try:
            fn(); print(f'{name}: OK')
        except Exception as e:
            err(name, e)
    del w
    try:
        r = open_reader(uri)
        types = {t.name: t.type for t in r.get_all_topics_and_types()}
        print('topics after:', types)
        while r.has_next():
            name, data, ts = r.read_next()
            try:
                m = deserialize_message(data, get_message(types[name]))
                print(f'  read {name} ts={ts} len={len(data)} data={m.data!r}')
            except Exception as e:
                err(f'  deserialize {name} ts={ts} len={len(data)}', e)
    except Exception as e:
        err('read back', e)

elif case == 'read':  # uri sid
    uri, sid = a[0], a[1]
    t = time.monotonic()
    try:
        r = open_reader(uri, sid)
    except Exception as e:
        err(f'open reader sid={sid}', e); sys.exit(0)
    try:
        types, n, first, last = read_all(r)
        print(f'read sid={sid}: topics={types} count={n} first={first} last={last} in {time.monotonic()-t:.3f} s')
        try:
            md = r.get_metadata()
            print(f'  metadata: storage_identifier={md.storage_identifier} message_count={md.message_count} files={[f.path if hasattr(f, "path") else f for f in md.files] if hasattr(md, "files") else "n/a"}')
        except Exception as e:
            err('  get_metadata', e)
    except Exception as e:
        err('read loop', e)

elif case == 'read_after_end':
    r = open_reader(a[0])
    while r.has_next():
        r.read_next()
    try:
        x = r.read_next()
        print('read_next after end: returned', type(x).__name__, x if not isinstance(x, tuple) else len(x))
    except Exception as e:
        err('read_next after end', e)

elif case == 'read_filter':
    r = open_reader(a[0])
    print('topics:', [t.name for t in r.get_all_topics_and_types()])
    for flt in (['/chatter'], ['/other']):
        r.set_filter(rosbag2_py.StorageFilter(topics=flt))
        try:
            r.seek(0)
        except Exception as e:
            err('seek(0)', e)
        n = 0
        while r.has_next():
            r.read_next(); n += 1
        print(f'with StorageFilter(topics={flt}):', n)
    r.reset_filter()
    try:
        r.seek(0)
    except Exception as e:
        err('seek(0)', e)
    n = 0
    while r.has_next():
        r.read_next(); n += 1
    print('after reset_filter + seek(0):', n)

elif case == 'concurrent':  # reader opened while the writer is still alive
    uri = a[0]
    w = open_writer(uri, a[1])
    write_n(w, 50)
    files(uri, ' writer alive')
    try:
        r = open_reader(uri, a[1])
        types, n, first, last = read_all(r)
        print(f'reader while writer alive: count={n}')
    except Exception as e:
        err('reader while writer alive', e)
    del w
    files(uri, ' after del writer')
    try:
        r = open_reader(uri, a[1])
        types, n, first, last = read_all(r)
        print(f'reader after del writer: count={n}')
    except Exception as e:
        err('reader after del writer', e)

elif case == 'node':  # rclpy node that records /chatter from a timer; finalize mode in a[1]
    import rclpy
    from rclpy.node import Node
    uri, mode = a[0], a[1]
    rclpy.init()
    n = Node('bag_writer_node')
    w = open_writer(uri, a[2] if len(a) > 2 else 'none')
    cnt = [0]

    def tick():
        w.write(T, serialize_message(String(data=f'tick {cnt[0]}')), n.get_clock().now().nanoseconds)
        cnt[0] += 1
    n.create_timer(0.05, tick)
    print('node spinning', flush=True)
    try:
        rclpy.spin(n)
    except BaseException as e:
        print(f'spin ended with {type(e).__module__}.{type(e).__name__} after {cnt[0]} writes: {str(e)[:300]}', flush=True)
    finally:
        if mode == 'del':
            del w
            print('finally: del writer', flush=True)
        else:
            print('finally: writer left alone', flush=True)
    files(uri, ' at end of script')
