@echo off
echo Installing Python dependencies.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Python install failed.
    exit /b %errorlevel%
)

echo Installing frontend dependencies.
cd frontend
npm install
if %errorlevel% neq 0 (
    echo npm install failed.
    exit /b %errorlevel%
)

echo Setup complete.
