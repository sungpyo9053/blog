"""Purpose-built arithmetic checks; not robot or simulator execution."""
import math
import json
results = []
value = (0/2)
assert math.isclose(value, 0, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '정지 목표 경계', "actual": value})
value = (0.2/2)
assert math.isclose(value, 0.1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '기준 추종', "actual": value})
value = (0.4/2)
assert math.isclose(value, 0.2, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '목표 속도 두 배', "actual": value})
value = (0.2/4)
assert math.isclose(value, 0.05, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '이득 두 배', "actual": value})
value = (0.2/1)
assert math.isclose(value, 0.2, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '낮은 이득', "actual": value})
value = (0.4/4)
assert math.isclose(value, 0.1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '같은 비율의 다른 조합', "actual": value})
print(json.dumps(results, ensure_ascii=False))
