## 하네스: 보안뉴스 데일리 다이제스트

**목표:** 보안뉴스(boannews.com)와 KISA 보호나라 보안공지를 매일 08:00(KST) 자동 수집·요약해 데일리 다이제스트로 제공하고 이메일로 발송한다.

**트리거:** 보안뉴스/KISA 보안공지 수집·요약·다이제스트 관련 요청 시 `security-news-digest` 스킬을 사용하라. 단순 질문(예: "이 다이제스트 형식이 뭐야")은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-09-14 | 초기 구성 (수집 에이전트, 요약 에이전트, 오케스트레이터 스킬) | 전체 | 매일 08시 보안뉴스/KISA 공지 자동 수집·요약 요청 |
| 2026-09-14 | GitHub(huntersang01/secunews)에 하네스 push, 매일 08:00 KST 클라우드 예약 작업(trig_011gHfUYBToLDb4ow7W1SMm8) 등록. 저장소는 Claude Code GitHub 연동이 private repo에 접근하지 못해 Public으로 전환 | 배포/스케줄 | 로컬 세션 없이도 매일 자동 실행되도록 클라우드 루틴 필요 |
| 2026-09-14 | 토큰 절감을 위해 수집 에이전트 model opus→haiku, 요약 에이전트 opus→sonnet으로 다운그레이드. Phase 3 이메일 발송 단계 추가 (Gmail SMTP, `scripts/send_digest_email.py` 번들 스크립트, LLM 호출 없이 Bash로 직접 실행) | agents/*.md, skills/security-news-digest | 하루 실행당 opus 8만 토큰 소모 확인 후 사용자 요청으로 비용 절감 + 자동 이메일 수신 요청 |
