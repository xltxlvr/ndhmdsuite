## 구조

- `index.html` — 홈(다운로드, 구성 요소, 최근 변경, 설치, 문서 링크)
- `docs/` — **생성된** 문서 쪽(손대지 마세요; `docs.css`, `docs.js` 만 직접 고치는 파일)
- `docs-src/` — 문서 원고(markdown). 여기를 고치고 아래 명령으로 다시 만듭니다.
- `tools/build_docs.py` — 원고 → `docs/*.html` 변환 스크립트

## 문서 다시 만들기

필요: Python 3, [pandoc](https://pandoc.org)(변경 이력용), `ndhmd2html.py`(+ PyYAML, Pillow)

```
python3 tools/build_docs.py --n2h /경로/ndhmd2html.py
```

설명서의 raw LaTeX 표(`tblr`)는 변환 전에 자동으로 파이프 표로 바꿉니다(원고는 그대로).
새 문서를 더하려면 `tools/build_docs.py` 위쪽의 `DOCS`, `CARDS` 목록에 한 줄 추가하세요.