@echo off
rem ============================================================================
rem  tarik.cmd - tarik perubahan terbaru dari GitHub ke salinan Windows ini.
rem
rem  Klik dua kali berkas ini setelah Claude (di server) mengirim perubahan.
rem  Aman dijalankan kapan saja: bila ada perubahan lokal yang belum di-commit,
rem  berkas ini TIDAK menimpanya - ia menyimpan dulu (stash), menarik, lalu
rem  mengembalikannya. Bila terjadi konflik, ia berhenti dan memberi tahu.
rem ============================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === PREDIKSI PRESISI - tarik perubahan terbaru ===
echo Folder: %CD%
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo [GAGAL] Git tidak ditemukan. Pasang Git for Windows lebih dulu.
    goto :selesai
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo [GAGAL] Folder ini bukan salinan Git. Letakkan berkas ini di folder siintel hasil clone.
    goto :selesai
)

for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set CABANG=%%b
echo Cabang: %CABANG%

rem --- perubahan lokal yang belum di-commit? simpan sementara ---
set ADA_LOKAL=0
for /f "delims=" %%s in ('git status --porcelain') do set ADA_LOKAL=1
if "%ADA_LOKAL%"=="1" (
    echo.
    echo Ada perubahan lokal yang belum di-commit. Disimpan sementara ^(stash^)...
    git stash push --include-untracked -m "tarik.cmd %DATE% %TIME%"
    if errorlevel 1 (
        echo [GAGAL] Tidak dapat menyimpan perubahan lokal. Tidak ada yang diubah.
        goto :selesai
    )
)

echo.
echo Menarik dari GitHub...
git pull --ff-only origin %CABANG%
set HASIL=%ERRORLEVEL%

if "%ADA_LOKAL%"=="1" (
    echo.
    echo Mengembalikan perubahan lokal...
    git stash pop
    if errorlevel 1 (
        echo.
        echo [PERHATIAN] Perubahan lokal Anda bentrok dengan yang ditarik.
        echo Buka Android Studio ^> Git ^> Resolve Conflicts, atau beri tahu Claude.
        goto :selesai
    )
)

if not "%HASIL%"=="0" (
    echo.
    echo [GAGAL] Penarikan tidak berhasil. Biasanya: tidak ada internet, atau cabang
    echo lokal punya commit yang belum di-push. Jalankan "git status" untuk melihatnya,
    echo atau beri tahu Claude.
    goto :selesai
)

echo.
echo Sudah terbaru. Lima perubahan terakhir:
git log --oneline -5
echo.
echo Android Studio akan memuat ulang berkasnya sendiri. Bila berkas build berubah,
echo tekan "Sync Now" yang muncul di bagian atas Android Studio.

:selesai
echo.
pause
endlocal
