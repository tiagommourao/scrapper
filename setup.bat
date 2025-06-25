@echo off

echo.
echo 🧹 Configurando o Scrapper com Deep Scraping...
echo.

REM Criar diretorios necessários
echo 📁 Criando diretórios...
if not exist "user_data" mkdir user_data
if not exist "user_scripts" mkdir user_scripts

REM Verificar se Docker está instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker não encontrado. Instale o Docker Desktop primeiro.
    echo https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM Verificar se Docker Compose está instalado
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose não encontrado. Instale o Docker Compose primeiro.
    pause
    exit /b 1
)

echo ✅ Setup concluído!
echo.
echo 🚀 Para iniciar o Scrapper, execute:
echo    docker-compose up --build
echo.
echo 🌐 O Scrapper estará disponível em:
echo    • Interface Web: http://localhost:3000
echo    • API Article: http://localhost:3000/api/article
echo    • API Links: http://localhost:3000/api/links
echo    • API Deep Scrape: http://localhost:3000/api/deep-scrape
echo    • Swagger Docs: http://localhost:3000/docs
echo.
echo 🎯 Para testar o Deep Scraping, acesse:
echo    http://localhost:3000/deep-scrape
echo.
pause 