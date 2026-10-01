@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="
if defined HOTEL_PYTHON if exist "%HOTEL_PYTHON%" set "PYTHON_EXE=%HOTEL_PYTHON%"
if not defined PYTHON_EXE if exist "%LocalAppData%\Python\bin\python.exe" set "PYTHON_EXE=%LocalAppData%\Python\bin\python.exe"
if not defined PYTHON_EXE for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do if exist "%%~fD\python.exe" set "PYTHON_EXE=%%~fD\python.exe"
if not defined PYTHON_EXE for /f "delims=" %%P in ('where python 2^>nul') do if /i not "%%~dpP"=="%LocalAppData%\Microsoft\WindowsApps\" set "PYTHON_EXE=%%~fP"

if not defined PYTHON_EXE (
  echo [LOI] Khong tim thay Python that tren may.
  echo Hay cai Python 3.11 tro len hoac dat bien HOTEL_PYTHON tro den python.exe.
  pause
  exit /b 1
)

"%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [LOI] Can Python 3.11 tro len. Dang tim thay: %PYTHON_EXE%
  pause
  exit /b 1
)

set "VENV_DIR=.venv"
if exist "%VENV_DIR%\Scripts\python.exe" (
  "%VENV_DIR%\Scripts\python.exe" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo [1/4] .venv thuoc may khac, se tao .venv-local moi...
    set "VENV_DIR=.venv-local"
  )
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [1/4] Dang tao moi truong ao...
  "%PYTHON_EXE%" -m venv "%VENV_DIR%" || goto :error
)

if exist "%VENV_DIR%\.requirements-ok" (
  fc /b requirements.txt "%VENV_DIR%\.requirements-ok" >nul 2>nul
  if errorlevel 1 del "%VENV_DIR%\.requirements-ok"
)
if not exist "%VENV_DIR%\.requirements-ok" (
  echo [2/4] Dang cai thu vien...
  "%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
  copy /y requirements.txt "%VENV_DIR%\.requirements-ok" >nul
) else (
  echo [2/4] Thu vien da san sang.
)

if not exist ".env" (
  echo [3/4] Dang tao cau hinh local...
  >.env echo APP_NAME=Lotus Hotel AI
  >>.env echo SECRET_KEY=local-development-secret-change-me
  >>.env echo DATABASE_URL=sqlite:///./data/hotel.db
  >>.env echo OLLAMA_URL=http://localhost:11434
  >>.env echo OLLAMA_MODEL=qwen2.5
  >>.env echo ACCESS_TOKEN_EXPIRE_MINUTES=480
)

echo [4/4] Dang chay kiem thu...
"%VENV_DIR%\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :testerror

echo.
echo Lotus Hotel AI: http://127.0.0.1:8000
echo Tai khoan: admin / Admin@123
start "" "http://127.0.0.1:8000"
"%VENV_DIR%\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
exit /b 0

:testerror
echo.
echo [LOI] Kiem thu chua dat, ung dung khong duoc khoi dong de tranh che mat loi.
pause
exit /b 1

:error
echo.
echo [LOI] Khong the hoan tat. Hay gui anh man hinh nay cho Codex.
pause
exit /b 1
