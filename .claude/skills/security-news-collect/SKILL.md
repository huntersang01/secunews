---
name: security-news-collect
description: 보안뉴스(boannews.com)와 KISA 보호나라 보안공지 게시판에서 최신 항목을 WebFetch로 수집하고 구조화된 JSON으로 저장하는 절차. security-news-collector 에이전트가 수집 작업을 할 때 반드시 이 스킬을 사용한다. "보안뉴스 수집", "KISA 공지 수집", "보안 소식 모아줘" 같은 요청에도 적용한다.
---

# 보안뉴스/KISA 공지 수집 절차

## 우선 확인: GitHub Actions가 이미 수집해뒀는가

클라우드 루틴 환경은 외부 웹 접속(WebFetch/curl)이 egress 정책으로 차단될 수 있다 (2026-09-16부터 확인된 이슈, CLAUDE.md 참고). 이를 우회하기 위해 `.github/workflows/fetch-security-news.yml`이 매일 07:40 KST에 GitHub Actions에서 `scripts/fetch_security_news.py`를 실행해 두 사이트를 미리 수집하고, `_workspace/security-news/{오늘날짜}_collected.json`과 `state.json`을 직접 커밋해둔다 (LLM 호출 없이 순수 스크립트라 토큰도 안 쓴다).

**이 에이전트가 호출되면 가장 먼저 할 일**: `_workspace/security-news/{오늘날짜}_collected.json`이 이미 존재하고, 적어도 한 출처가 `"status": "ok"`인지 확인한다.
- **있으면** (GitHub Actions가 정상적으로 미리 수집해둔 경우) — 아래의 WebFetch 수집 절차는 전부 건너뛴다. 그 파일을 그대로 최종 결과로 인정하고, 각 출처의 상태/건수만 요약해서 보고한 뒤 종료한다. state.json도 이미 그 스크립트가 갱신해뒀으므로 손댈 필요 없다.
- **없거나, 있어도 두 출처 모두 `"status": "failed"`인 경우** (GitHub Actions가 아직 안 돌았거나 실패한 경우) — 아래 WebFetch 기반 절차로 직접 수집을 시도한다 (환경에 따라 여전히 막힐 수 있다 — 막히면 정직하게 실패로 기록한다).

## 왜 이런 절차가 필요한가 (WebFetch 폴백 경로)

두 사이트 모두 목록 페이지가 서버 렌더링 HTML이라 WebFetch로 직접 읽을 수 있다. 하지만 매일 반복 수집하는 작업이므로, 매번 전체 목록을 다시 요약해 넘기면 중복이 쌓이고 다음 단계(요약 에이전트)의 컨텍스트가 낭비된다. 그래서 "이전 실행 이후의 신규 항목만" 걸러내는 상태 관리가 핵심이다.

## 출처 1: 보안뉴스 (boannews.com)

- 목록 URL: `https://www.boannews.com/news/articleList.html?view_type=sm`
- 이 URL은 전체 카테고리의 최신 기사를 시간순으로 보여준다 (하루 약 15~30건).
- 기사 상세 URL 패턴: `https://www.boannews.com/news/articleView.html?idxno={숫자}` — idxno가 클수록 최신 기사다.
- WebFetch 프롬프트에 "최신 기사 목록을 제목 | URL(idxno 포함 전체 URL) | 게시 날짜시간 | 카테고리 | 한 줄 요약 형식으로 최대한 많이 나열해줘"라고 명시한다. idxno가 없는 링크는 절대 만들어내지 않는다 — 실제 페이지에 없는 값은 비워둔다.
- 날짜 형식은 보통 `MM-DD HH:MM`이다. 연도가 없으면 실행 시점(오늘)의 연도를 붙인다.

## 출처 2: KISA 보호나라 보안공지

- 목록 URL: `https://www.boho.or.kr/kr/bbs/list.do?menuNo=205020&bbsId=B0000133`
- 게시글 상세 URL 패턴: `https://www.boho.or.kr/kr/bbs/view.do?menuNo=205020&bbsId=B0000133&nttId={숫자}` — nttId가 클수록 최신 글이다.
- 이 게시판은 "OO 제품 보안 업데이트 권고", "OO 주의 권고/안내" 류의 공지가 대부분이며, 매일 새 글이 올라오지는 않는다. 신규 글이 없는 날도 정상이다.
- WebFetch 프롬프트에 "최신 게시글을 제목 | 실제 href 링크(nttId 파라미터 포함) | 게시일 형식으로 나열해줘"라고 명시한다.

## 신규 항목 필터링 (중복 방지)

1. `_workspace/security-news/state.json`을 읽는다. 없으면 최초 실행으로 간주한다.
   ```json
   {
     "boannews_last_idxno": 0,
     "kisa_last_nttid": 0,
     "last_run_at": null
   }
   ```
2. 수집한 목록에서 `idxno`(또는 `nttId`)가 저장된 값보다 큰 항목만 "신규"로 채택한다.
3. 최초 실행이거나 상태 파일 값이 0이면, 최근 1일 이내 게시된 항목만 채택한다 (전체 이력을 한 번에 쏟아내지 않는다).
4. 신규 항목이 하나도 없으면 빈 배열로 두고 계속 진행한다 — 에러가 아니다.

## 출력 스키마

`_workspace/security-news/{YYYY-MM-DD}_collected.json`:

```json
{
  "run_date": "2026-09-14",
  "sources": {
    "boannews": {
      "status": "ok",
      "items": [
        {
          "title": "제목",
          "url": "https://www.boannews.com/news/articleView.html?idxno=145811",
          "idxno": 145811,
          "published_at": "2026-09-14 09:31",
          "category": "사건사고",
          "snippet": "한 줄 요약"
        }
      ],
      "error": null
    },
    "kisa_boho": {
      "status": "ok",
      "items": [
        {
          "title": "제목",
          "url": "https://www.boho.or.kr/kr/bbs/view.do?menuNo=205020&bbsId=B0000133&nttId=72185",
          "nttId": 72185,
          "published_at": "2026-09-10",
          "snippet": null
        }
      ],
      "error": null
    }
  }
}
```

- 출처가 실패하면 `"status": "failed"`, `"items": []`, `"error": "실패 사유"`로 기록한다.
- 파일은 Write 도구로 저장하거나, JSON을 구성한 뒤 Bash의 heredoc으로 저장해도 된다.

## 상태 파일 갱신

수집 완료 후 `_workspace/security-news/state.json`을 이번 실행에서 확인한 각 출처의 **가장 큰 idxno/nttId**로 갱신한다 (실패한 출처는 갱신하지 않는다 — 다음 실행에서 재시도할 수 있도록).

```json
{
  "boannews_last_idxno": 145811,
  "kisa_last_nttid": 72185,
  "last_run_at": "2026-09-14T08:00:00+09:00"
}
```
