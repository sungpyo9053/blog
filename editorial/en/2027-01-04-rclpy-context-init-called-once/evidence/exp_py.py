"""rclpy init-twice experiments. Each case runs in a fresh interpreter (see repro.sh)."""
import sys, time, os, runpy, tempfile, traceback, unittest, io
import rclpy
from rclpy.context import Context

case = sys.argv[1]


def err(e):
    return f'{type(e).__module__}.{type(e).__name__}: {e}'


def report(label, fn):
    try:
        r = fn()
        print(f'{label}: OK{"" if r is None else " -> " + str(r)}')
    except BaseException as e:
        print(f'{label}: RAISED {err(e)}')


if case == 'twice':
    rclpy.init()
    report('second rclpy.init()', rclpy.init)
    print('rclpy.ok() after failed init:', rclpy.ok())
    def use():
        n = rclpy.create_node('after_fail')
        p = n.create_publisher(__import__('std_msgs.msg', fromlist=['String']).String, 'chatter', 10)
        p.publish(__import__('std_msgs.msg', fromlist=['String']).String(data='x'))
        n.destroy_node()
        return 'node created and published'
    report('use default context after failed init', use)
    report('rclpy.shutdown()', rclpy.shutdown)

elif case == 'reinit':
    rclpy.init(); rclpy.shutdown()
    report('init after shutdown', rclpy.init)
    report('create_node after re-init', lambda: rclpy.create_node('re').get_name())
    report('shutdown again', rclpy.shutdown)

elif case == 'guard':
    rclpy.init()
    def guarded():
        if not rclpy.ok():
            rclpy.init()
            return 'init called'
        return 'skipped, already ok'
    report('guarded second init', guarded)
    rclpy.shutdown()
    report('guarded init after shutdown', guarded)
    rclpy.try_shutdown()

elif case == 'try_shutdown':
    rclpy.init()
    report('try_shutdown #1', rclpy.try_shutdown)
    report('try_shutdown #2', rclpy.try_shutdown)
    report('init after try_shutdown', rclpy.init)
    rclpy.try_shutdown()

elif case == 'ctxmgr':
    def one():
        with rclpy.init():
            return rclpy.create_node('cm').get_name()
    report('with rclpy.init() #1', one)
    report('with rclpy.init() #2', one)
    print('rclpy.ok() at end:', rclpy.ok())

elif case == 'context':
    rclpy.init()
    ctx = Context()
    report('rclpy.init(context=ctx) while default is up', lambda: rclpy.init(context=ctx))
    report('node on ctx', lambda: rclpy.create_node('on_ctx', context=ctx).get_name())
    report('second rclpy.init(context=ctx)', lambda: rclpy.init(context=ctx))
    rclpy.shutdown(context=ctx); rclpy.shutdown()

elif case == 'rerun':
    # simulates re-running a notebook cell / runpy twice in one interpreter
    d = tempfile.mkdtemp()
    bad = os.path.join(d, 'bad.py'); good = os.path.join(d, 'good.py')
    open(bad, 'w').write(
        'import rclpy\nrclpy.init()\nn = rclpy.create_node("cell")\n'
        'raise KeyboardInterrupt  # stands in for an interrupted spin\n'
        'rclpy.shutdown()\n')
    open(good, 'w').write(
        'import rclpy\nrclpy.init()\ntry:\n    n = rclpy.create_node("cell")\n'
        '    raise KeyboardInterrupt\nfinally:\n    rclpy.try_shutdown()\n')
    for name, path in (('no finally', bad), ('try/finally try_shutdown', good)):
        for i in (1, 2):
            report(f'{name} run {i}', lambda: runpy.run_path(path))
        print(f'rclpy.ok() after the two {name} runs:', rclpy.ok())
        rclpy.try_shutdown()  # reset between the two groups

elif case == 'unittest':
    class NoTeardown(unittest.TestCase):
        def setUp(self): rclpy.init()
        def test_a(self): rclpy.create_node('a').destroy_node()
        def test_b(self): rclpy.create_node('b').destroy_node()
        def test_c(self): rclpy.create_node('c').destroy_node()

    class WithTeardown(unittest.TestCase):
        def setUp(self): rclpy.init()
        def tearDown(self): rclpy.shutdown()
        def test_a(self): rclpy.create_node('a').destroy_node()
        def test_b(self): rclpy.create_node('b').destroy_node()
        def test_c(self): rclpy.create_node('c').destroy_node()

    class ClassLevel(unittest.TestCase):
        @classmethod
        def setUpClass(cls): rclpy.init()
        @classmethod
        def tearDownClass(cls): rclpy.shutdown()
        def test_a(self): rclpy.create_node('a').destroy_node()
        def test_b(self): rclpy.create_node('b').destroy_node()
        def test_c(self): rclpy.create_node('c').destroy_node()

    for cls in (NoTeardown, WithTeardown, ClassLevel):
        buf = io.StringIO()
        res = unittest.TextTestRunner(stream=buf, verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        msgs = sorted({tb.strip().splitlines()[-1] for _, tb in res.errors})
        print(f'{cls.__name__}: ran={res.testsRun} errors={len(res.errors)} failures={len(res.failures)} {msgs}')
        rclpy.try_shutdown()

elif case == 'timing':
    N = 50
    t0 = time.perf_counter()
    for _ in range(N):
        rclpy.init(); rclpy.shutdown()
    t1 = time.perf_counter()
    for _ in range(N):
        rclpy.init(); n = rclpy.create_node('t'); n.destroy_node(); rclpy.shutdown()
    t2 = time.perf_counter()
    print(f'init+shutdown x{N}: {1000*(t1-t0)/N:.2f} ms each')
    print(f'init+create_node+destroy+shutdown x{N}: {1000*(t2-t1)/N:.2f} ms each')

elif case == 'uncaught':
    rclpy.init()
    rclpy.init()
