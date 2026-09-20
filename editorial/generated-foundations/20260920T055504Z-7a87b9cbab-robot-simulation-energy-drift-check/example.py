"""Purpose-built arithmetic checks; not robot or simulator execution."""
import math
import json
results = []
value = (4.0 + 6.0)
assert math.isclose(value, 10, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '초기 총에너지', "actual": value})
value = (6.5 + 3.4)
assert math.isclose(value, 9.9, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '큰 시간 간격에서 나중 총에너지', "actual": value})
value = (((6.5 + 3.4) - (4.0 + 6.0)) / (4.0 + 6.0) * 100)
assert math.isclose(value, -1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '큰 시간 간격의 초기값 대비 변화율', "actual": value})
value = (((6.5 + 3.48) - (4.0 + 6.0)) / (4.0 + 6.0) * 100)
assert math.isclose(value, -0.2, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '작은 시간 간격의 초기값 대비 변화율', "actual": value})
value = (((5.0 + 4.5) - (4.0 + 6.0)) / (4.0 + 6.0) * 100)
assert math.isclose(value, -5, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '마찰을 포함한 경계 사례의 변화율', "actual": value})
print(json.dumps(results, ensure_ascii=False))
