# SimpleLine 디지털 명함 (공용 QR 명함 시스템)

QR을 찍으면 **양면 디지털 명함**(한글 앞면 + 영문 뒷면)이 열립니다.
명함 데이터(JSON)만 추가하면 누구든 같은 방식으로 명함 + QR이 자동 생성됩니다.

## 새 명함 추가하는 법

1. `cards/<영문약자>.json` 파일을 만든다 (기존 `cards/kjh.json` 복사 후 값만 교체)
2. 생성기 실행:

   ```
   python build_card.py cards/<약자>.json --base-url https://aacbal22.github.io/simpleline-cards
   ```

   전체 일괄 생성:
   ```
   python build_card.py cards/*.json --base-url https://aacbal22.github.io/simpleline-cards
   ```

3. `git add -A && git commit -m "card: <약자>" && git push` → 1~2분 뒤 GitHub Pages 반영

## 산출물

| 경로 | 설명 |
|------|------|
| `docs/card/<약자>/index.html` | QR이 가리키는 디지털 명함 페이지 (한글/영문 탭 + 연락처 저장) |
| `docs/qr/<약자>.png` | 인쇄·공유용 QR 이미지 |

## 명함 주소 / QR

- 페이지: `https://aacbal22.github.io/simpleline-cards/card/<약자>/`
- 예) 김준형 실장 → `.../card/kjh/`

## 데이터 형식 (cards/*.json)

- `front` : 한글 앞면 (이름·직함·부서·전화·이메일·주소·웹)
- `back` : 영문 뒷면 (영문 이름·직함·전화·주소·웹)
- `vcard` : "연락처 저장" 버튼이 만드는 폰 연락처(vCard 3.0) 정보

## 연락처 셀프 수정 (V1.2.0~)

직원이 폰에서 명함의 **"✎ 내 연락처 수정"** → 휴대폰 뒷4자리 → 전화·이메일·한글주소를 직접 수정.
사진 셀프수정과 같은 구조(Cloudflare Worker + KV `contact:<slug>`).

- 직책·부서·이름은 **관리자 전용**(셀프수정 불가). 영문 뒷면 주소도 자동변환 부정확으로 유지.
- 전화는 한국식(010-…) 입력 → 뒷면·vCard의 +82 표기는 자동 변환.
- 셀프수정값은 KV에만 쌓이므로, **관리자 재빌드 전 반드시 동기화** 실행:

  ```
  python sync_contacts.py            # KV 셀프수정값 → cards/*.json 되돌려쓰기
  python build_card.py cards/*.json --base-url https://aacbal22.github.io/simpleline-cards
  git add -A && git commit && git push
  ```

  (생략하면 다음 재빌드 때 셀프수정이 사라짐 → 원본 이원화 방지 규칙)

- Worker 코드(`photo-worker/`) 변경 시 배포: `cd photo-worker && wrangler deploy` (먼저 `wrangler login`)

> ⚠️ 이 저장소는 **공개(public)** 입니다. 명함에 인쇄되는 공개 연락처만 넣고,
> 내부·민감 정보는 절대 커밋하지 마세요.
