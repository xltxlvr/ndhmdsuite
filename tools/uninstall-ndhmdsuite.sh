#!/bin/sh
# ndhmdSuite (macOS) 제거 스크립트
# 지우는 것: ndhmdWriter.app, ndhmd4tex 설정 폴더, /usr/local/bin 의 변환 도구,
#            ksruncltex(래퍼·TeXShop 엔진·TEXMFHOME 스크립트), ndhmdWriter 환경설정.
# 원고·글꼴·TeX 배포판은 건드리지 않는다.

# 경로가 비었을 때 엉뚱한 곳(/scripts/... 등)을 지우지 않도록, 비어 있으면 건너뛴다.
rm_path() {                       # rm_path [sudo] 경로...
    SUDO=""
    if [ "$1" = "sudo" ]; then SUDO="sudo"; shift; fi
    for p in "$@"; do
        [ -n "$p" ] || continue
        if [ -e "$p" ] || [ -L "$p" ]; then
            echo "삭제: $p"
            $SUDO rm -rf -- "$p"
        fi
    done
}

echo "ndhmdSuite 를 제거합니다. (일부 항목은 관리자 암호가 필요합니다)"
printf "계속할까요? [y/N] "
read ans
case "$ans" in y|Y|yes|YES) ;; *) echo "취소했습니다."; exit 0 ;; esac

# TeX 도구가 PATH 에 없을 수 있으니 MacTeX 위치를 더한다.
PATH="$PATH:/Library/TeX/texbin:/usr/local/bin:/opt/homebrew/bin"

# 실행 중이면 먼저 닫는다(종료 때 환경설정을 다시 쓰기 때문).
pkill -x ndhmdWriter 2>/dev/null
sleep 1

# 앱 (사용자 폴더와 시스템 폴더 양쪽)
rm_path "$HOME/Applications/ndhmdWriter.app"
rm_path sudo "/Applications/ndhmdWriter.app"

# ndhmd4tex 설정·mapping 폴더
rm_path "$HOME/Library/ndhmd4tex"

# 변환 도구
rm_path sudo /usr/local/bin/ndhmd4tex /usr/local/bin/ndhmd2html /usr/local/bin/ndhmdsync \
             /usr/local/bin/_internal /usr/local/bin/ndhmd-default.nmd

# ksruncltex
rm_path "$HOME/Library/TeXShop/Engines/ksRunCluttex.engine"
KSR=$(command -v ksruncltex 2>/dev/null)
rm_path sudo "$KSR"
if command -v kpsewhich >/dev/null 2>&1; then
    rm_path "$(kpsewhich ksruncltex.lua 2>/dev/null)"
    TMH=$(kpsewhich -var-value=TEXMFHOME 2>/dev/null)
    [ -n "$TMH" ] && rm_path "$TMH/scripts/ksruncltex"
else
    echo "kpsewhich 를 찾지 못해 TEXMFHOME 의 ksruncltex 는 건너뜁니다."
fi

# 환경설정 — plist 파일과 cfprefsd 캐시 둘 다 지운다.
defaults delete org.ktug.ndhmdWriter 2>/dev/null
rm_path "$HOME/Library/Preferences/org.ktug.ndhmdWriter.plist"
rm_path "$HOME/Library/Saved Application State/org.ktug.ndhmdWriter.savedState"
killall cfprefsd 2>/dev/null

echo "끝났습니다."
