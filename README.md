# SpeakDaily

A Windows desktop app for daily English speaking practice. Press Start and the app gives you a random question and a random speaking time between 1 and 10 minutes. It records your voice, then shows a reference answer and key phrases so you can compare. Questions live in a Google Sheet, so you can edit them from any device.

## Quick start

1. Open `dist\SpeakDaily.exe`. No install is needed.
2. Pick topics on the Practice screen (or leave "All topics").
3. Press **Start speaking**, read the question, and press **Start speaking** again when you are ready. The ring counts down and your voice is recorded.
4. When time is up (or you press **Finish**), play your answer, read the reference answer, rate yourself from 1 to 5 and press **Save and next question**.

Keyboard: `Space` starts or pauses a session.

The first time you open the exe, Windows SmartScreen may say "Windows protected your PC" because the exe is not code-signed. Click **More info**, then **Run anyway**.

## How the random choice works

- Time: a random value in half-minute steps between the question's `min_minutes` and `max_minutes`, always kept inside 1 to 10 minutes. "Quick 1–3 min" mode caps it at 3 minutes.
- Question: a shuffle bag. Every question in the chosen topics appears once before any question repeats. Questions you rated low (1 or 2) have a higher chance to come early in each round, and questions you rated 5 a lower chance.

## Questions in Google Drive

Your question sheet is already created in your Google Drive: **SpeakDaily Questions** (https://docs.google.com/spreadsheets/d/1Cc0Jd1B4xRWgJ_adBRDKSWCnCFgZ8oxviF0GED1C6UE/edit). It has 44 starter questions in 12 topics and a "How to use" tab. The app is set to use this sheet by default.

### Connect without login (default)

1. Open the sheet and click **Share**.
2. Under **General access**, choose **Anyone with the link**, role **Viewer**.
3. In the app, go to **Settings** and press **Save and sync**.

People with the link can read the questions but cannot change them. Only you can edit.

### Connect with Google sign-in (sheet stays private)

Use this if you do not want link sharing. It needs a one-time setup in Google Cloud:

1. Go to https://console.cloud.google.com/, create a project, and enable the **Google Drive API**.
2. Open **APIs and Services > OAuth consent screen**, choose External, and add your own Gmail address as a test user.
3. Open **Credentials > Create credentials > OAuth client ID**, choose **Desktop app**, and download the JSON file.
4. Rename it to `credentials.json` and put it in the app's data folder (Settings > **Open data folder**).
5. In Settings choose **Google sign-in** and press **Save and sync**. Your browser opens once to sign in. The app asks only for read-only access.

### Sheet columns

| Column | Required | Notes |
| --- | --- | --- |
| `id` | no | Keep it so your ratings stay linked to the question. Leave empty for new rows. |
| `topic` | no | Questions with the same topic are grouped. Empty means "General". |
| `question` | yes | The question to answer out loud. |
| `reference_answer` | no | A sample answer shown after you speak. |
| `key_phrases` | no | Separate with `;`. Shown as hints and after the session. |
| `difficulty` | no | `easy`, `medium` or `hard`. |
| `min_minutes`, `max_minutes` | no | 1 to 10. Empty means 1 and 10. |
| `tags` | no | Separate with `;`. |

The app reads the first tab. Header names are flexible: `answer`, `phrases`, `level`, `min` and `max` also work.

### Sync rules

- Sync runs when the app starts (you can turn this off) and when you press **Sync now**.
- After a successful sync, the sheet replaces the built-in starter questions. Questions you added inside the app ("Mine") are kept.
- Sheet questions are read-only inside the app. Edit them in the sheet and sync again, so the next sync does not overwrite your change.
- If there is no internet, the app keeps working with the questions from the last sync.

## Library

Search, filter by topic, practise one question directly, and add, edit or delete your own questions. **Export CSV** writes the current list in the same columns as the sheet, so you can paste it into Google Sheets. **Import CSV** reads the same format.

## Where your data is stored

Next to the exe, in a folder called `SpeakDaily_data` (if that folder cannot be written, the app uses `%APPDATA%\SpeakDaily`):

| File | Contents |
| --- | --- |
| `questions.json` | All questions (synced, built-in and your own) |
| `history.json` | Every session: question, planned and spoken time, rating, note |
| `settings.json` | Sheet link, sync mode and other settings |
| `recordings\*.wav` | Your recordings (16 kHz mono). Only the newest 60 are kept by default. |
| `credentials.json`, `token.json` | Only for Google sign-in mode |
| `error_log.txt` | Written only if the app crashes |

To move the app to another computer, copy the exe together with the `SpeakDaily_data` folder.

## Run from source

Needs Python 3.10 or newer on Windows.

```bat
run.bat
```

or by hand:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

When run from source, data goes to the `user_data` folder in the project.

## Build the exe

```bat
build.bat
```

This creates a virtual environment, installs the packages and PyInstaller, and runs `pyinstaller SpeakDaily.spec`. The result is `dist\SpeakDaily.exe`, a single file of about 26 MB with no console window.

## Tests

```bat
pip install pytest
python -m pytest tests
```

The 19 tests cover the random time range (always 1 to 10 minutes), the shuffle bag, rating weights, CSV parsing of sheet exports, Drive link parsing, the sync merge rules and the stats.

## Project structure

```
main.py                     entry point, shows a dialog if the app crashes
SpeakDaily.spec             PyInstaller recipe
build.bat / run.bat         build the exe / run from source
requirements.txt
speakdaily/
  storage.py                questions, history, settings, CSV import and export
  picker.py                 random question (shuffle bag) and random time
  drive_sync.py             Google Sheet download (shared link or sign-in)
  audio.py                  recording (sounddevice) and playback (winsound)
  paths.py                  data folder and bundled assets
  theme.py                  colours, fonts, topic icons
  ui/app.py                 main window, sidebar, background sync
  ui/practice.py            home, session and review screens
  ui/library.py             library and question editor
  ui/history.py             stats, 14-day chart, recent sessions
  ui/settings.py            settings screen
  assets/                   Lucide icons (ISC licence) and app icon
  data/starter_questions.csv    44 built-in questions
  data/default_settings.json    presets the sheet link for this build
tests/test_core.py
```

## Before publishing to other people

- Delete `speakdaily/data/default_settings.json` (or clear the link in it), so other users do not sync from your personal sheet. They can paste their own sheet link in Settings.
- Some starter reference answers mention my own background (game development, studying in Sydney). Replace them with neutral answers for a public version.
- Code-signing the exe removes the SmartScreen warning. Without it, users have to click "Run anyway".

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "Timer running without recording. No microphone found" | Plug in a microphone, then check Windows Settings > Privacy and security > Microphone > "Let desktop apps access your microphone". |
| "Google did not return the sheet" | The sheet is not shared. Follow "Connect without login" above, or switch to Google sign-in. |
| "No connection to Google Drive" | No internet or a firewall. The app keeps using the last synced questions. |
| The app closes on start | Open `SpeakDaily_data\error_log.txt` and check the last lines. |
