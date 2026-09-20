"""Purpose-built arithmetic checks; not robot or simulator execution."""
import math
import json
results = []
value = (1*0.02)
assert math.isclose(value, 0.02, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '1배속에서 20ms 지연', "actual": value})
value = (10*0.02)
assert math.isclose(value, 0.2, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '10배속에서 같은 20ms 지연', "actual": value})
value = (50*0.02)
assert math.isclose(value, 1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '50배속에서 같은 20ms 지연', "actual": value})
value = (10*0.01)
assert math.isclose(value, 0.1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '10배속에서 지연을 10ms로 감소', "actual": value})
value = (0*0.02)
assert math.isclose(value, 0, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '일시정지 경계에서 20ms 지연', "actual": value})
value = (0.1/0.02)
assert math.isclose(value, 5, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '허용 차이 0.1초일 때 최대 배속 후보', "actual": value})
print(json.dumps(results, ensure_ascii=False))
