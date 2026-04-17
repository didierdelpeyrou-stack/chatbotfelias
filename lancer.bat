@echo off
echo ============================================================
echo   ELISFA - Assistant Juridique CCN ALISFA v2.0
echo ============================================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR : Python n'est pas installe.
    echo Telechargez-le sur https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    pause
    exit /b
)

REM Charger .env si présent
if exist .env (
    echo Chargement de la configuration .env...
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        echo %%a | findstr /r "^#" >nul || set "%%a=%%b"
    )
)

REM Installer les dépendances
echo Installation des dependances...
pip install -r requirements.txt --quiet

echo.
echo ============================================================
echo   Demarrage du chatbot...
echo   Chatbot    : http://localhost:5000
echo   Admin      : http://localhost:5000/admin
echo   API Health : http://localhost:5000/api/health
echo   MCP Config : http://localhost:5000/api/mcp/config
echo ============================================================
echo   Pour arreter : appuyez sur Ctrl+C
echo ============================================================
echo.

python app.py
pause
