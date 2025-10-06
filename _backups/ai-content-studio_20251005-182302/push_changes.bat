@echo off
cd /d G:\ai-content-studio\ai_content_studio_pipeline_plus
git add .
git commit -m "Auto update"
git pull origin main --rebase
git push origin main
pause
