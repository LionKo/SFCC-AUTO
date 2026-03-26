# SFCC CM Debug

## Start

From `E:\SFCC\sfcc_CM`:

```bat
start_debug.bat
```

If you want to pass the game exe path explicitly:

```bat
start_debug.bat "E:\SteamLibrary\steamapps\common\SegaFCC\FootballClubChampions.exe"
```

If you want to run Python directly:

```bat
python cm_bot.py --log-level DEBUG
```

## Stop

```bat
stop_bot.bat
```

## Current template layout

- `templates/login`: restart-only login flow
- `templates/main`: creative mode main loop
- `templates/new_season`: new season flow
- `templates/common`: common buttons and popups

## Current flow layout

- `flows/bootstrap_flow.py`: login -> main menu -> create entrance -> save selection
- `flows/main_flow.py`: speed, special training, advance schedule
- `flows/new_season_flow.py`: club transfers -> level -> SP join -> final confirm
- `flows/common_flow.py`: ok, continue, skip, retry, close

## Smoke test status

The script now:

- starts from both repo root and `sfcc_CM`
- loads templates from `templates/`
- passes `py_compile`
- can attach to the game window and enter the main loop

## Debug notes

- Logs are written to `sfcc_CM/logs/`
- If recognition is wrong, check the latest `cm_bot_*.log`
- OCR-based screens now replace several deleted title templates, so the first debug pass should focus on:
  - special training screen entry
  - club transfers screen detection
  - SP join screen detection
  - final confirm detection
