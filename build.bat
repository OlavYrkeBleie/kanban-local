@echo off
pyinstaller --onefile --windowed --name kanban --icon=NONE kanban.py
echo.
echo build done. exe is in dist/kanban.exe
pause
