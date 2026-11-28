import tempfile
import unittest
from pathlib import Path

from scripts.style_score import is_question, main, score, sentences, tone

FP = ["2026년 MRI 건강보험 수가", "2026년 치석제거·진찰료 단가", "매도 손익과 손익분기 매도가",
      "청소년 드림·힘내라 청춘·온라인 특가", "할인가·할인율 역산·할인 전 정가", "가입 조건 4가지",
      "구청 공영주차장은 1~5급지", "비정품 배터리 메시지", "시외노선 우등 할인과 프리미엄 마일리지",
      "연간 지원 시간 한도와 중복 금지", "환불 기준과 연간 중도 해지", "의무가입기간 3년과 중도해지",
      "지니뮤직 요금제 개요", "지급일과 신청"]
TP = ["eSIM과 유심, 무엇이 다른가", "심야 요금은 얼마나 비싼가", "1평은 몇 ㎡인가",
      "2026년 기초연금은 누가, 얼마나 받나", "사다리타기는 공정할까", "배당기준일과 언제까지 사야 받는지",
      "본인부담은 몇 퍼센트인가요?", "내 본인부담금은 얼마일까요? (계산기)",
      "금 시세는 어디서 보나: KRX 원/g", "비교 기준: 어떤 요금제를 골랐나"]
OLD_EN = ('<pre>err</pre><p>Intro line here.</p><p>Short answer: pin the version.</p><h2>FAQ</h2>'
          + '"@type":"Question"' * 5)


class StyleScoreTest(unittest.TestCase):
    def test_question_headings(self) -> None:
        self.assertEqual([h for h in FP if is_question(h)], [])
        self.assertEqual([h for h in TP if not is_question(h)], [])

    def test_tone(self) -> None:
        self.assertEqual(tone("재료만으로 54,700원까지 벌어지는 셈입니다(중간값 재료면 457,700원)."), "hapnida")
        self.assertEqual(tone("요금은 현장 안내판으로 다시 확인하자."), "haera")
        self.assertEqual(tone('공지에는 이렇게 적혀 있다”.'), "haera")
        self.assertEqual(tone("지니뮤직 요금제 개요"), "other")
        self.assertEqual(tone("받아요."), "haeyo")

    def test_date_does_not_split_sentence(self) -> None:
        self.assertEqual(sentences(["목록(2026.1.1. 기준)으로 확인했습니다. 다음 문장이다."]),
                         ["목록(2026.1.1. 기준)으로 확인했습니다.", "다음 문장이다."])

    def test_faq_no_double_penalty(self) -> None:
        for n in (7, 8):
            r = score("A", "<h2>얼마인가</h2>" + '"@type":"Question"' * n)
            self.assertEqual((r["parts"]["faq"], r["parts"]["rules"]), (0, 40))

    def test_rules_not_floored_early(self) -> None:
        five = "<h2>30초 핵심 요약</h2><h2>자주 묻는 질문</h2><h2>같이 보면 좋은 글</h2><p>자료 확인일</p>"
        four = five.replace("<h2>같이 보면 좋은 글</h2>", "")
        self.assertGreater(score("A", four)["parts"]["rules"], score("A", five)["parts"]["rules"])
        self.assertGreater(score("A", five)["parts"]["rules"], 0)

    def test_en_opener_after_pre(self) -> None:
        r = score("EN", OLD_EN)
        self.assertIn("opener", r["flags"])
        self.assertIn("faq_block:5", r["flags"])

    def test_min_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            old, clean = Path(d, "old.html"), Path(d, "clean.html")
            old.write_text(OLD_EN, encoding="utf-8")
            clean.write_text("<h2>pip fails on 3.13</h2><p>I didn't test Windows, and the wheel built fine on macOS here.</p>",
                             encoding="utf-8")
            self.assertEqual(main(["EN", str(old)]), 0)  # no threshold: never blocks
            self.assertEqual(main(["--min", "80", "EN", str(old)]), 1)
            self.assertEqual(main(["--min", "80", "EN", str(clean)]), 0)


if __name__ == "__main__":
    unittest.main()
