## 하네스: 보안뉴스 데일리 다이제스트

**목표:** 보안뉴스(boannews.com)와 KISA 보호나라 보안공지를 매일 08:00(KST) 자동 수집·요약해 데일리 다이제스트로 제공하고 이메일로 발송한다.

**트리거:** 보안뉴스/KISA 보안공지 수집·요약·다이제스트 관련 요청 시 `security-news-digest` 스킬을 사용하라. 단순 질문(예: "이 다이제스트 형식이 뭐야")은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-09-14 | 초기 구성 (수집 에이전트, 요약 에이전트, 오케스트레이터 스킬) | 전체 | 매일 08시 보안뉴스/KISA 공지 자동 수집·요약 요청 |
| 2026-09-14 | GitHub(huntersang01/secunews)에 하네스 push, 매일 08:00 KST 클라우드 예약 작업(trig_011gHfUYBToLDb4ow7W1SMm8) 등록. 저장소는 Claude Code GitHub 연동이 private repo에 접근하지 못해 Public으로 전환 | 배포/스케줄 | 로컬 세션 없이도 매일 자동 실행되도록 클라우드 루틴 필요 |
| 2026-09-14 | 토큰 절감을 위해 수집 에이전트 model opus→haiku, 요약 에이전트 opus→sonnet으로 다운그레이드 | agents/*.md, skills/security-news-digest | 하루 실행당 opus 8만 토큰 소모 확인 후 사용자 요청으로 비용 절감 |
| 2026-09-14 | 이메일 발송을 클라우드 루틴이 아닌 GitHub Actions(`.github/workflows/send-digest-email.yml`)로 이전. Gmail 앱 비밀번호는 GitHub Environment "MAILSECU"의 Secrets(GMAIL_USER/GMAIL_APP_PASSWORD/DIGEST_RECIPIENT)에 저장, `reports/security-digest/**.md` push를 트리거로 `scripts/send_digest_email.py` 실행 | .github/workflows, skills/security-news-digest | Claude Code 클라우드 루틴에 시크릿(환경변수) 저장 기능이 없어, 공개 저장소에 비밀번호 노출 없이 자동 발송하려면 GitHub Secrets가 필요했음 |
| 2026-09-15 | 이메일 발송 실제 검증 완료 (sinyeong.lee@lsmaterials.co.kr 수신 확인). 다이제스트 형식을 불릿 목록 → 마크다운 표로 변경, `send_digest_email.py`가 표를 실제 HTML `<table>`로 렌더링해서 발송(plain 파트도 함께 첨부) | skills/security-news-summarize, skills/security-news-digest/scripts | 이메일 클라이언트에서 표로 보이길 원하는 사용자 요청. GitHub Environment 이름/시크릿 이름 관련 시행착오는 MAILSECU + GMAIL_USER/GMAIL_APP_PASSWORD/DIGEST_RECIPIENT 조합으로 최종 확정 |
