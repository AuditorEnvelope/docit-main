@echo off
REM Script to run all database migrations in order (Windows)
REM Usage: run_all_migrations.bat

setlocal enabledelayedexpansion

REM Configuration
set DB_NAME=lekhak_ai
set DB_USER=postgres
set DB_HOST=localhost
set DB_PORT=5432

echo ==========================================
echo Lekhak AI Database Migration Script
echo ==========================================
echo.

REM Check if psql is available
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] psql command not found
    echo Please install PostgreSQL and ensure psql is in your PATH
    exit /b 1
)

REM Check if database exists
echo Checking if database exists...
psql -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -lqt | findstr /C:"%DB_NAME%" >nul
if %errorlevel% neq 0 (
    echo Database '%DB_NAME%' not found. Creating...
    createdb -U %DB_USER% -h %DB_HOST% -p %DB_PORT% %DB_NAME%
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create database
        exit /b 1
    )
    echo [OK] Database created
) else (
    echo [OK] Database exists
)

echo.
echo Running migrations...
echo.

REM Run each migration in order
set MIGRATIONS[0]=migrations\001_auth_and_billing.sql
set MIGRATIONS[1]=migrations\002_multi_org_support.sql
set MIGRATIONS[2]=migrations\003_org_registrations.sql
set MIGRATIONS[3]=migrations\004_repo_sync_state.sql
set MIGRATIONS[4]=migrations\005_stripe_subscription_management.sql

for /L %%i in (0,1,4) do (
    set "migration=!MIGRATIONS[%%i]!"
    if not exist "!migration!" (
        echo [ERROR] Migration file not found: !migration!
        exit /b 1
    )
    
    echo Running: !migration!
    psql -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -f "!migration!" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to run !migration!
        echo Run manually to see error details:
        echo   psql -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -f "!migration!"
        exit /b 1
    )
    echo [OK] !migration! completed
)

echo.
echo [OK] All migrations completed successfully!
echo.
echo Verifying setup...
echo.

REM Verify tables exist
for /f %%a in ('psql -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"') do set TABLE_COUNT=%%a
echo Tables created: !TABLE_COUNT!

REM Verify plans
for /f %%a in ('psql -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -t -c "SELECT COUNT(*) FROM plans;"') do set PLAN_COUNT=%%a
echo Plans created: !PLAN_COUNT!

if !PLAN_COUNT! geq 4 (
    echo [OK] Database setup complete!
) else (
    echo [WARNING] Expected 4+ plans, found !PLAN_COUNT!
)

echo.
echo Next steps:
echo 1. Set DATABASE_URL in .env file
echo 2. Configure Stripe keys (if using payments)
echo 3. Start backend: python src/main.py

endlocal
