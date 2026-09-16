---
name: security-news-digest
description: 보안뉴스(boannews.com)와 KISA 보호나라 보안공지를 수집해서 한국어 데일리 다이제스트로 요약하고 이메일로 발송하는 전체 워크플로우를 조율한다. "보안뉴스 요약", "KISA 공지 확인", "오늘의 보안 소식", "보안 다이제스트", "보안뉴스/보안공지 다시 수집", "다이제스트 재작성", "보안 소식 업데이트", "다이제스트 메일 다시 보내줘" 등 관련 요청 시 반드시 이 스킬을 사용한다. 매일 08:00 KST 스케줄 실행에서도 이 스킬이 진입점이다.
---

# 보안뉴스 데일리 다이제스트 오케스트레이터

## 실행 모드

**서브 에이전트 패턴** (수집 → 요약 순차 파이프라인). 두 단계 사이에 실시간 조율이나 토론이 필요 없고 "결과 파일 전달"만으로 충분하므로 팀 통신 오버헤드 없이 `Agent` 도구로 순차 호출한다.

## Phase 0: 컨텍스트 확인

작업 디렉토리 기준으로 다음을 확인한다:

- `_workspace/security-news/state.json` 존재 여부
  - **없음** → 초기 실행. 최근 1일치만 수집.
  - **있음** → 이후 실행. 상태 파일 기준 신규 항목만 수집.
- 오늘 날짜(`{YYYY-MM-DD}`)의 `_workspace/security-news/{날짜}_collected.json`이 이미 있는지 확인하고, 있으면 내용도 읽는다:
  - **있고 적어도 한 출처가 `"status": "ok"`** → GitHub Actions(`.github/workflows/fetch-security-news.yml`)가 이미 수집을 끝낸 것이다. **Phase 1을 완전히 건너뛴다** (Agent 호출도 하지 않는다 — 토큰을 쓸 필요가 없다). 바로 Phase 2로 진행한다.
  - **있지만 두 출처 모두 `"status": "failed"`** → GitHub Actions도 실패했거나 아직 못 돌았다는 뜻. Phase 1을 실행해서 LLM 기반 폴백(WebFetch) 수집을 한 번 더 시도한다.
  - **없음** → 아직 GitHub Actions 사전수집이 안 된 것. Phase 1부터 정상 실행 (LLM 기반 수집 시도).
  - 사용자가 "다시 요약"/"톤 수정"만 요청 → Phase 2만 재실행, Phase 1 건너뜀 (위 판단과 무관하게 사용자 요청이 우선).
  - 사용자가 "다시 수집"/특정 소스 재수집을 명시적으로 요청 → 위 판단과 무관하게 Phase 1을 강제 실행.

## Phase 1: 수집 (GitHub Actions 사전수집 실패/누락 시에만 실행)

이 Phase는 Phase 0에서 "실행 필요"로 판단됐을 때만 진행한다. 조건을 만족하지 않으면(=GitHub Actions가 이미 성공) 이 섹션 전체를 건너뛰고 Phase 2로 간다.

`Agent` 도구로 호출한다 (`subagent_type: "general-purpose"`, `model: "haiku"` 명시 — 목록 추출·필터링은 고급 추론이 필요 없는 기계적 작업이라 가장 저렴한 모델로 충분하다). 이 환경의 Agent 도구는 커스텀 이름을 `subagent_type`으로 직접 받지 않으므로, 프롬프트 안에서 에이전트 정의 파일과 스킬 파일을 먼저 읽고 그 역할을 따르도록 명시해야 한다:

- 먼저 읽을 파일: `.claude/agents/security-news-collector.md` (역할 정의), `.claude/skills/security-news-collect/SKILL.md` (수집 절차 — GitHub Actions 사전수집 확인 로직 포함)
- 프롬프트에 실행 날짜(오늘, KST 기준)를 명시한다.
- 부분 재수집 요청이면 프롬프트에 "보안뉴스만" 또는 "KISA만" 재수집하라고 범위를 명시한다.
- 결과: `_workspace/security-news/{날짜}_collected.json`, `_workspace/security-news/state.json` 갱신.

## Phase 2: 요약

`Agent` 도구로 호출한다 (`subagent_type: "general-purpose"`, `model: "sonnet"` 명시 — 심각도 판단과 원문 요약에는 어느 정도의 추론이 필요하지만 opus 수준까지는 필요 없다), 마찬가지로 프롬프트에서 정의 파일을 먼저 읽게 한다:

- 먼저 읽을 파일: `.claude/agents/security-news-summarizer.md` (역할 정의), `.claude/skills/security-news-summarize/SKILL.md` (작성 절차)
- 프롬프트에 Phase 1에서 생성된 `_collected.json` 경로를 전달한다.
- 결과: `reports/security-digest/{날짜}.md` + 다이제스트 본문 텍스트 반환.

## Phase 3: 커밋 및 push (이메일 발송 트리거)

이메일 발송은 이 오케스트레이터가 직접 하지 않는다. 클라우드 루틴 환경에는 시크릿(비밀번호) 저장 기능이 없어서, `GMAIL_APP_PASSWORD`를 여기서 다루면 저장소(Public)나 실행 로그에 노출될 위험이 있다. 대신 **GitHub Actions**(`.github/workflows/send-digest-email.yml`)가 이메일 비밀번호를 GitHub Secrets(암호화 저장)로 관리하고 발송을 전담한다.

오케스트레이터가 할 일은 다음 파일을 커밋하고 `origin main`에 push하는 것뿐이다:
- `_workspace/security-news/state.json`
- `_workspace/security-news/{날짜}_collected.json`
- `reports/security-digest/{날짜}.md`

`reports/security-digest/` 아래 파일이 push되는 순간 GitHub Actions가 자동으로 감지해 이메일을 보낸다 (LLM 호출 없이 GitHub 워크플로우 러너에서 `scripts/send_digest_email.py`를 직접 실행 — 토큰을 전혀 쓰지 않는다). git 커밋 identity가 없다는 오류가 나면 `git config user.email "secunews-bot@users.noreply.github.com"`과 `git config user.name "SecuNews Bot"`을 로컬로 설정한 뒤 다시 커밋한다.

## Phase 4: 결과 전달

- 요약 에이전트가 반환한 다이제스트 본문을 사용자(또는 스케줄 실행 로그)에게 그대로 보여준다.
- 저장된 파일 경로(`reports/security-digest/{날짜}.md`)를 함께 안내한다.
- 한쪽 출처라도 수집 실패였다면, 다이제스트 상단 경고 문구가 포함되어 있는지 확인하고 별도로도 한 줄 언급한다.
- push가 성공했으면 "이메일은 GitHub Actions가 자동 발송합니다"라고 안내한다 (실제 발송 성공 여부는 이 세션에서 확인할 수 없다 — 확인이 필요하면 GitHub Actions 탭을 보라고 안내한다).

## 데이터 전달 프로토콜

| 단계 | 방식 |
|------|------|
| 오케스트레이터 → 수집 에이전트 | 반환값 기반 (Agent 호출 결과) + 파일 기반 (`_collected.json`) |
| 수집 에이전트 → 요약 에이전트 | 파일 기반 (`_collected.json`), 오케스트레이터가 파일 경로를 다음 Agent 호출 프롬프트에 명시 |
| 요약 에이전트 → 이메일 발송 | 파일 기반 (`reports/security-digest/{날짜}.md`를 git push) → GitHub Actions가 push 이벤트로 트리거되어 발송 |
| 요약 에이전트 → 사용자 | 반환값 기반 (다이제스트 본문) + 파일 기반 (`reports/security-digest/{날짜}.md`) |

## 에러 핸들링

- 수집 에이전트가 한 출처만 실패해도 계속 진행한다 (수집 에이전트 자체 원칙과 동일). 두 출처 모두 실패하면 요약 단계를 생략하지 않고, 요약 에이전트가 "수집 실패" 안내문을 작성하도록 그대로 호출한다 — 사용자가 상황을 알아야 한다.
- 수집 에이전트 호출 자체가 실패(예: 도구 오류)하면 1회 재시도 후, 재실패 시 사용자에게 실패 사실과 사유를 알리고 중단한다.
- push 자체가 실패하면(권한/충돌 등) 재시도 1회 후 사용자에게 알린다 — push가 안 되면 이메일도 발송되지 않는다는 점을 함께 알린다.
- 이메일 발송 성패는 GitHub Actions 로그(저장소의 Actions 탭)에서만 확인 가능하다. SMTP 인증 실패 등은 GitHub Secrets(`GMAIL_APP_PASSWORD` 등) 값을 사용자가 직접 점검해야 한다.

## 후속 작업 지원

다음 요청은 모두 이 스킬이 처리한다:
- "오늘 보안뉴스 요약해줘" → 전체 실행
- "KISA 공지만 다시 확인해줘" → Phase 1 부분 재실행(KISA만) + Phase 2, 3
- "다이제스트 톤 좀 더 간결하게 다시 써줘" → Phase 2만 재실행 후 다시 push (재push되면 GitHub Actions가 다시 발송한다는 점을 사용자에게 안내)
- "다이제스트 메일 다시 보내줘" → 오늘자 파일을 아주 살짝 수정(예: 타임스탬프 주석 추가) 후 재커밋/재push해서 Actions를 재트리거하거나, GitHub Actions 탭에서 "Re-run job"을 안내
- 매일 08:00 KST 스케줄 트리거 → 전체 실행 (상태 파일 기준 자동으로 신규분만 처리)

## 테스트 시나리오

**정상 흐름 (평상시, GitHub Actions 사전수집 성공):** GitHub Actions가 07:40 KST에 `scripts/fetch_security_news.py`로 이미 오늘자 `_collected.json`(status: ok)과 `state.json`을 커밋해둔 상태 → 08:00 KST 루틴 실행 시 Phase 0에서 이를 감지 → Phase 1(수집 Agent 호출) 완전히 건너뜀 → 요약 에이전트(sonnet)가 바로 심각도순 다이제스트 작성 → reports/security-digest/{오늘}.md 저장 및 본문 반환 → 커밋/push → GitHub Actions가 push 감지, `send_digest_email.py` 실행해 이메일 발송.

**정상 흐름 (GitHub Actions 사전수집 실패 시 폴백):** state.json 없음 또는 오늘자 collected.json이 두 출처 모두 실패 → 수집 에이전트(haiku)가 최근 1일치 boannews/KISA 항목 WebFetch로 직접 수집 시도 → collected.json 생성 → 이후 동일.

**에러 흐름 1 (수집 실패):** KISA 사이트 접속 실패(네트워크 오류) → 수집 에이전트가 boannews만 성공으로 채워 반환(`kisa_boho.status: "failed"`) → 요약 에이전트가 다이제스트 최상단에 "⚠️ KISA 보호나라 수집 실패" 경고를 포함해 나머지(boannews) 항목으로 정상 다이제스트 작성 → push → 이메일은 정상 발송(GitHub Actions) → 사용자에게 수집 실패 사실 별도 안내.

**에러 흐름 2 (발송 실패):** 다이제스트는 정상 push됐으나 GitHub Secrets의 `GMAIL_APP_PASSWORD`가 만료 → GitHub Actions의 `send_digest_email.py`가 SMTP 인증 오류로 종료(이 세션은 이 실패를 알 수 없음) → 사용자가 이메일을 못 받았다고 문의하면, 저장소 Actions 탭에서 실패 로그를 확인하도록 안내하고 GitHub Secrets 값을 재확인/재발급하도록 안내한다.
