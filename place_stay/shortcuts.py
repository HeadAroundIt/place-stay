"""Shortcuts for sign-in startup, the desktop, and a double-click launcher."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from place_stay.brand import APP_NAME, LEGACY_SHORTCUT_STEM, SHORTCUT_STEM
from place_stay.paths import app_home, frozen, launch_args, launch_exe


def project_root() -> Path:
    return app_home()


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _desktop_dir() -> Path:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            raw, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(raw))
    except OSError:
        return Path.home() / "Desktop"


def startup_lnk() -> Path:
    return Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup" / f"{SHORTCUT_STEM}.lnk"


def desktop_lnk() -> Path:
    return _desktop_dir() / f"{SHORTCUT_STEM}.lnk"


def _legacy_startup_lnk() -> Path:
    return Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup" / f"{LEGACY_SHORTCUT_STEM}.lnk"


def _legacy_desktop_lnk() -> Path:
    return _desktop_dir() / f"{LEGACY_SHORTCUT_STEM}.lnk"


def _icon_location() -> str:
    from place_stay.iconimg import icon_file

    target = launch_exe()
    if frozen() and target.exists():
        return str(target) + ",0"
    return str(icon_file()) + ",0"


def _write_lnk(path: Path, args: str, window_style: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = "\n".join(
        [
            "$s = New-Object -ComObject WScript.Shell",
            f"$lnk = $s.CreateShortcut({_ps_quote(str(path))})",
            f"$lnk.TargetPath = {_ps_quote(str(launch_exe()))}",
            f"$lnk.Arguments = {_ps_quote(args)}",
            f"$lnk.WorkingDirectory = {_ps_quote(str(app_home()))}",
            f"$lnk.WindowStyle = {window_style}",
            f"$lnk.IconLocation = {_ps_quote(_icon_location())}",
            f"$lnk.Description = {_ps_quote(APP_NAME)}",
            "$lnk.Save()",
        ]
    )
    _run_hidden_powershell(script)


def _run_hidden_powershell(script: str) -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    subprocess.run(
        [
            str(powershell if powershell.exists() else "powershell"),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-Command",
            script,
        ],
        check=True,
        capture_output=True,
        text=True,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )


def ensure_startup(enabled: bool) -> None:
    path = startup_lnk()
    _legacy_startup_lnk().unlink(missing_ok=True)
    if not enabled:
        path.unlink(missing_ok=True)
        return
    _write_lnk(path, launch_args(background=True), 7)


def desktop_shortcut_exists() -> bool:
    return desktop_lnk().exists()


def create_desktop_shortcut() -> str:
    path = desktop_lnk()
    _legacy_desktop_lnk().unlink(missing_ok=True)
    _write_lnk(path, launch_args(background=False), 1)
    return str(path)


def refresh_shortcut_icons() -> None:
    """Point shortcuts that already exist at the app icon."""
    if _legacy_startup_lnk().exists() or startup_lnk().exists():
        _legacy_startup_lnk().unlink(missing_ok=True)
        _write_lnk(startup_lnk(), launch_args(background=True), 7)
    if _legacy_desktop_lnk().exists() or desktop_lnk().exists():
        _legacy_desktop_lnk().unlink(missing_ok=True)
        _write_lnk(desktop_lnk(), launch_args(background=False), 1)


def write_folder_launcher() -> None:
    if frozen():
        return
    root = app_home()
    target = launch_exe()
    vbs = root / "Open Place Stay.vbs"
    current = str(root).replace('"', '""')
    exe = str(target).replace('"', '""')
    vbs.write_text(
        "\r\n".join(
            [
                'Set sh = CreateObject("Wscript.Shell")',
                f'sh.CurrentDirectory = "{current}"',
                f'sh.Run """{exe}"" -m place_stay", 0, False',
                "",
            ]
        ),
        encoding="utf-8",
    )
