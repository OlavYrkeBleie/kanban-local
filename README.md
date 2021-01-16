# kanban-local

local kanban board with json sharing and screenshot export.
runs as standalone .exe - no install needed.

## features
- to do / in progress / done columns
- cards with notes and @mentions
- card status colours (grey/green/yellow/red) - click to cycle
- multiple named boards (sidebar)
- autosave to ~/.kanban-local/data.json
- export board as json to clipboard
- import json from clipboard (merges cards, no duplicates)
- screenshot → saves png to desktop (paste into discord/teams)
- calendar with per-day notes and events

## run from source
```
pip install pillow
python kanban.py
```

## build .exe
```
pip install pyinstaller
build.bat
```
the exe ends up in dist/kanban.exe - copy anywhere and run.

## json sharing
export json on your machine → send to someone → they import json.
cards appear alongside theirs. works like a simple board sync.

MIT License
