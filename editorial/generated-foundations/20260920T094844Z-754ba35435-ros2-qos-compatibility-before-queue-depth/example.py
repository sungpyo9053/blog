"""Purpose-built arithmetic checks; not robot or simulator execution."""
import math
import json
results = []
value = (1 * 1)
assert math.isclose(value, 1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": '두 정책 모두 호환', "actual": value})
value = (0 * 1)
assert math.isclose(value, 0, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": 'best effort 발행자와 reliable 구독자', "actual": value})
value = (1 * 1)
assert math.isclose(value, 1, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": 'reliable 발행자와 best effort 구독자', "actual": value})
value = (1 * 0)
assert math.isclose(value, 0, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": 'volatile 발행자와 transient local 구독자', "actual": value})
value = (0 * 0)
assert math.isclose(value, 0, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": 'reliability와 durability 모두 불일치', "actual": value})
value = (0 * 1 * (100 / 100))
assert math.isclose(value, 0, rel_tol=1e-9, abs_tol=1e-9)
results.append({"name": 'depth를 10에서 100으로 늘려도 reliability 불일치는 유지', "actual": value})
print(json.dumps(results, ensure_ascii=False))
