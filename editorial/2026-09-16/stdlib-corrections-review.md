# 698·699 실행 준비 최소화 — 독립 Reviewer

status: APPROVED
manifest_sha256: 5d9ed1c38e7a6d27f68bf3195317bbae71d86f32047bbadbf2d9b8e2ce093d07

`content-stdlib-corrections.json`의 두 기존 글 본문만 승인한다. 작성자와 분리된
AI Reviewer 검수이며 사람의 검수나 새 글 발행 승인이 아니다.

| existing_post_id | 기존 제목 | 기존 slug | Category ID | after SHA-256 |
| --- | --- | --- | --- | --- |
| 698 | HTTP 200인데 WordPress REST 발행이 실패한 이유 | wordpress-rest-html-200-validation | 309 | 9fd0ab206f8a42f2ee9c13fe3e6a67b8253981cceb54503cf110cfc96df1c5b0 |
| 699 | noindex 글이 sitemap에 남는 배포 불일치 잡기 | wordpress-noindex-sitemap-consistency | 311 | 15d3671cc4acbadb7a0982cdfc91b8111a94b004d9d35821e787321d8ed19495 |

## 승인 근거

변경은 앞서 공개 반영한 각 글의 실행 준비 aside에 한정된다. HTML/JSON 및 sitemap
격리 실험에 불필요한 운영용 전체 requirements 설치를 제거했다. 기존 가상환경을
자동 보존한다는 인상을 줄 수 있던 주석은 실제 독자가 생성 명령을 생략하도록 고쳤다.
역사 근거·출력·진단 명령·링크·제목·slug·이미지는 바꾸지 않는다.

Reviewer는 Python 3.12.9에서 `venv --without-pip`로 새 환경을 생성하고 외부 패키지
설치 없이 다음 두 실행기를 직접 실행했다. 결과 파일은 서로 다른 임시 경로를 사용했다.

```text
rest-html-200-response: exit_code=0 status=READY wordpress_writes=0
noindex-sitemap-consistency: exit_code=0 status=READY wordpress_writes=0
```

이는 통제 실험과 진단 회귀 테스트가 표준 라이브러리만으로 실행된 증거다.
실제 사이트의 인증·발행·색인 성공을 의미하지 않는다.

`2026-09-15T17:22:32.514115+00:00`의 인증 GET inventory는 공개 9/초안 113,
complete/full_content=true이며 앞선 5편 반영을 포함한다. 두 before가 그 raw와
정확히 일치함을 확인했고, 두 after를 함께 반영한 예상 최종 상태에서 각각 자신의
ID만 제외한 122편 전체 본문 검사를 통과했다. 180자 이상 동일 산문·챗봇 잔재·목록
유효성 실패가 없다. 같은 글의 준비 단계 마찰을 줄이는 수정이므로 새 검색 의도를
만들지 않는다.

Publisher는 별도 receipt 디렉터리를 사용하고 최신 raw와 before SHA를 다시 대조한다.
모든 사전검사와 원문 백업 후 body-only 갱신·read-back·공개 확인을 수행한다.
카테고리·제목·slug·원래 발행 날짜·미디어·기타 메타데이터는 보존한다.
manifest나 HTML이 바뀌면 재검토한다. Reviewer의 WordPress 쓰기는 0회다.
