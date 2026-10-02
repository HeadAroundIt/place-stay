from __future__ import annotations

from pathlib import Path

# Friendly labels for apps this desktop is likely to see. Unknown programs fall
# back to the file name, lightly cleaned up.
_PRETTY = {
    "brave.exe": "Brave",
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "opera.exe": "Opera",
    "cursor.exe": "Cursor",
    "code.exe": "VS Code",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "steam.exe": "Steam",
    "steamwebhelper.exe": "Steam",
    "explorer.exe": "File Explorer",
    "notepad.exe": "Notepad",
    "notepad++.exe": "Notepad++",
    "windowsterminal.exe": "Terminal",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell",
    "obs64.exe": "OBS",
    "obs32.exe": "OBS",
    "slack.exe": "Slack",
    "teams.exe": "Teams",
    "outlook.exe": "Outlook",
    "winword.exe": "Word",
    "excel.exe": "Excel",
    "powerpnt.exe": "PowerPoint",
    "notion.exe": "Notion",
    "figma.exe": "Figma",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "vlc.exe": "VLC",
    "hush.exe": "Hush",
    "applicationframehost.exe": "Windows",
}


def app_name(process: str, title: str) -> str:
    key = (process or "").lower()
    title = (title or "").strip()
    if key in {"python.exe", "pythonw.exe"} and title:
        return title.split(" - ")[0][:48]
    if key in _PRETTY:
        return _PRETTY[key]
    stem = Path(process).stem if process else ""
    if not stem:
        return title[:48] or "Window"
    if stem.isupper() and len(stem) <= 4:
        return stem
    cleaned = stem.replace("_", " ").replace("-", " ")
    return cleaned[:1].upper() + cleaned[1:]
