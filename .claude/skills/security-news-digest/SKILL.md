---
name: security-news-digest
description: 보안뉴스(boannews.com)와 KISA 보호나라 보안공지를 수집해서 한국어 데일리 다이제스트로 요약하는 전체 워크플로우를 조율한다. "보안뉴스 요약", "KISA 공지 확인", "오늘의 보안 소식", "보안 다이제스트", "보안뉴스/보안공지 다시 수집", "다이제스트 재작성", "보안 소식 업데이트" 등 관련 요청 시 반드시 이 스킬을 사용한다. 매일 08:00 KST 스케줄 실행에서도 이 스킬이 진입점이다.
---

# 보안뉴스 데일리 다이제스트 오케스트레이터

## 실행 모드

**서브 에이전트 패턴** (수집 → 요약 순차 파이프라인). 두 단계 사이에 실시간 조율이나 토론이 필요 없고 "결과 파일 전달"만으로 충분하므로 팀 통신 오버헤드 없이 `Agent` 도구로 순차 호출한다.

## Phase 0: 컨텍스트 확인

작업 디렉토리 기준으로 다음을 확인한다:

- `_workspace/security-news/state.json` 존재 여부
  - **없음** → 초기 실행. 최근 1일치만 수집.
  - **있음** → 이후 실행. 상태 파일 기준 신규 항목만 수집.
- 오늘 날짜(`{YYYY-MM-DD}`)의 `_workspace/security-news/{날짜}_collected.json`이 이미 있는지 확인
  - **있고, 사용자가 "다시 요약"/"톤 수정" 등 요약만 재요청** → Phase 2(요약)만 재실행, Phase 1(수집) 건너뜀
  - **있고, 사용자가 "다시 수집"/특정 소스 재수집 요청** → 해당 소스만 Phase 1 재실행 후 Phase 2 재실행
  - **없음** → Phase 1부터 정상 실행

## Phase 1: 수집

`Agent` 도구로 호출한다 (`subagent_type: "general-purpose"`, `model: "opus"` 명시). 이 환경의 Agent 도구는 커스텀 이름을 `subagent_type`으로 직접 받지 않으므로, 프롬프트 안에서 에이전트 정의 파일과 스킬 파일을 먼저 읽고 그 역할을 따르도록 명시해야 한다:

- 먼저 읽을 파일: `.claude/agents/security-news-collector.md` (역할 정의), `.claude/skills/security-news-collect/SKILL.md` (수집 절차)
- 프롬프트에 실행 날짜(오늘, KST 기준)를 명시한다.
- 부분 재수집 요청이면 프롬프트에 "보안뉴스만" 또는 "KISA만" 재수집하라고 범위를 명시한다.
- 결과: `_workspace/security-news/{날짜}_collected.json`, `_workspace/security-news/state.json` 갱신.

## Phase 2: 요약

`Agent` 도구로 호출한다 (`subagent_type: "general-purpose"`, `model: "opus"` 명시), 마찬가지로 프롬프트에서 정의 파일을 먼저 읽게 한다:

- 먼저 읽을 파일: `.claude/agents/security-news-summarizer.md` (역할 정의), `.claude/skills/security-news-summarize/SKILL.md` (작성 절차)
- 프롬프트에 Phase 1에서 생성된 `_collected.json` 경로를 전달한다.
- 결과: `reports/security-digest/{날짜}.md` + 다이제스트 본문 텍스트 반환.

## Phase 3: 결과 전달

- 요약 에이전트가 반환한 다이제스트 본문을 사용자(또는 스케줄 실행 로그)에게 그대로 보여준다.
- 저장된 파일 경로(`reports/security-digest/{날짜}.md`)를 함께 안내한다.
- 한쪽 출처라도 수집 실패였다면, 다이제스트 상단 경고 문구가 포함되어 있는지 확인하고 별도로도 한 줄 언급한다.

## 데이터 전달 프로토콜

| 단계 | 방식 |
|------|------|
| 오케스트레이터 → 수집 에이전트 | 반환값 기반 (Agent 호출 결과) + 파일 기반 (`_collected.json`) |
| 수집 에이전트 → 요약 에이전트 | 파일 기반 (`_collected.json`), 오케스트레이터가 파일 경로를 다음 Agent 호출 프롬프트에 명시 |
| 요약 에이전트 → 사용자 | 반환값 기반 (다이제스트 본문) + 파일 기반 (`reports/security-digest/{날짜}.md`) |

## 에러 핸들링

- 수집 에이전트가 한 출처만 실패해도 계속 진행한다 (수집 에이전트 자체 원칙과 동일). 두 출처 모두 실패하면 요약 단계를 생략하지 않고, 요약 에이전트가 "수집 실패" 안내문을 작성하도록 그대로 호출한다 — 사용자가 상황을 알아야 한다.
- 수집 에이전트 호출 자체가 실패(예: 도구 오류)하면 1회 재시도 후, 재실패 시 사용자에게 실패 사실과 사유를 알리고 중단한다.

## 후속 작업 지원

다음 요청은 모두 이 스킬이 처리한다:
- "오늘 보안뉴스 요약해줘" → 전체 실행
- "KISA 공지만 다시 확인해줘" → Phase 1 부분 재실행(KISA만) + Phase 2
- "다이제스트 톤 좀 더 간결하게 다시 써줘" → Phase 2만 재실행
- 매일 08:00 KST 스케줄 트리거 → 전체 실행 (상태 파일 기준 자동으로 신규분만 처리)

## 테스트 시나리오

**정상 흐름:** state.json 없음 → 수집 에이전트가 최근 1일치 boannews/KISA 항목 수집 → collected.json 생성 → 요약 에이전트가 심각도순 다이제스트 작성 → reports/security-digest/{오늘}.md 저장 및 본문 반환.

**에러 흐름:** KISA 사이트 접속 실패(네트워크 오류) → 수집 에이전트가 boannews만 성공으로 채워 반환(`kisa_boho.status: "failed"`) → 요약 에이전트가 다이제스트 최상단에 "⚠️ KISA 보호나라 수집 실패" 경고를 포함해 나머지(boannews) 항목으로 정상 다이제스트 작성 → 사용자에게 실패 사실 별도 안내.
