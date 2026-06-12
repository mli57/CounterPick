@REM @echo off
@REM echo Step 1: Pulling matches from Riot API: uncomment to pull fresh data from RIOT (requires your own API key)
@REM python src\backend\pull_matches.py
@REM if %errorlevel% neq 0 (
@REM     echo pull_matches.py failed.
@REM     exit /b %errorlevel%
@REM )

echo Step 2: Normalizing roles
python src\backend\normalize_roles.py --db test.db
if %errorlevel% neq 0 (
    echo normalize_roles.py failed.
    exit /b %errorlevel%
)

echo Step 3: Deriving champion tags
python src\backend\derive_tags.py --db test.db
if %errorlevel% neq 0 (
    echo derive_tags.py failed.
    exit /b %errorlevel%
)

echo Step 4: Building features
python src\backend\build_features.py --db test.db
if %errorlevel% neq 0 (
    echo build_features.py failed.
    exit /b %errorlevel%
)

echo Step 5: Training model
python src\backend\train_model.py
if %errorlevel% neq 0 (
    echo train_model.py failed.
    exit /b %errorlevel%
)

echo Pipeline complete.