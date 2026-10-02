"""Win32 window and monitor calls. Coordinates are physical pixels."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

_DPI_READY = False

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
SW_MAXIMIZE = 3
SW_SHOW = 5
SW_SHOWMINNOACTIVE = 7
SW_RESTORE = 9
ERROR_ALREADY_EXISTS = 183
WM_POWERBROADCAST = 0x0218
WM_WTSSESSION_CHANGE = 0x02B1
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
WS_POPUP = 0x80000000
WS_EX_NOACTIVATE = 0x08000000
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
DWMWA_CLOAKED = 14
DWMWA_EXTENDED_FRAME_BOUNDS = 9
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
LSFW_LOCK = 1
LSFW_UNLOCK = 2

SKIP_CLASS = {
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "NotifyIconOverflowWindow",
    "TopLevelWindowForOverflowXamlIsland",
    "DummyDWMListenerWindow",
    "Windows.UI.Core.CoreWindow",
}
SKIP_PROCESS = {
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "textinputhost.exe",
    "lockapp.exe",
    "placestay.exe",
    "stickydesktop.exe",
}


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", POINT),
        ("ptMaxPosition", POINT),
        ("rcNormalPosition", RECT),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
)


def _bind() -> None:
    user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), MONITORENUMPROC, wintypes.LPARAM]
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.IsZoomed.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
    user32.GetWindowPlacement.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.LockSetForegroundWindow.argtypes = [wintypes.UINT]
    user32.LockSetForegroundWindow.restype = wintypes.BOOL
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.LoadImageW.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
    dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long


_bind()


def enable_dpi_awareness() -> None:
    global _DPI_READY
    if _DPI_READY:
        return
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    _DPI_READY = True


def set_app_id() -> None:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PlaceStay.App")


def mouse_left_down() -> bool:
    return bool(user32.GetAsyncKeyState(0x01) & 0x8000)


def _process_name(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(520)
        buf = ctypes.create_unicode_buffer(520)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return buf.value.rsplit("\\", 1)[-1]
    finally:
        kernel32.CloseHandle(handle)


def _title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _cloaked(hwnd: int) -> bool:
    value = wintypes.DWORD()
    hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(value), ctypes.sizeof(value))
    return hr == 0 and bool(value.value)


def list_monitors() -> list[dict]:
    found: list[dict] = []

    @MONITORENUMPROC
    def _each(hmon, _hdc, _rect, _data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            return True
        rect = info.rcMonitor
        work = info.rcWork
        found.append(
            {
                "device": info.szDevice,
                "left": int(rect.left),
                "top": int(rect.top),
                "width": int(rect.right - rect.left),
                "height": int(rect.bottom - rect.top),
                "workLeft": int(work.left),
                "workTop": int(work.top),
                "workRight": int(work.right),
                "workBottom": int(work.bottom),
                "primary": bool(info.dwFlags & 1),
            }
        )
        return True

    user32.EnumDisplayMonitors(None, None, _each, 0)
    return found


def list_windows(skip_pid: int | None = None) -> list[dict]:
    found: list[dict] = []
    own = os.getpid() if skip_pid is None else skip_pid

    @WNDENUMPROC
    def _each(hwnd, _lparam):
        try:
            _consider(int(hwnd), own, found)
        except Exception:
            return True
        return True

    user32.EnumWindows(_each, 0)
    return found


def _consider(hwnd: int, skip_pid: int, found: list[dict]) -> None:
    if not user32.IsWindowVisible(hwnd):
        return
    if user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
        return
    if _cloaked(hwnd):
        return
    class_name = _class_name(hwnd)
    if class_name in SKIP_CLASS:
        return
    title = _title(hwnd).strip()
    if not title:
        return
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if int(pid.value) == skip_pid:
        return
    process = _process_name(int(pid.value))
    if process.lower() in SKIP_PROCESS:
        return
    if title in {"Place. Stay.", "Sticky Desktop"} and process.lower() in {
        "python.exe",
        "pythonw.exe",
        "placestay.exe",
        "stickydesktop.exe",
    }:
        return

    minimized = bool(user32.IsIconic(hwnd))
    maximized = bool(user32.IsZoomed(hwnd))
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return
    left, top = int(rect.left), int(rect.top)
    width, height = int(rect.right - rect.left), int(rect.bottom - rect.top)

    if minimized:
        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(WINDOWPLACEMENT)
        if not user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            return
        normal = placement.rcNormalPosition
        left, top = int(normal.left), int(normal.top)
        width = int(normal.right - normal.left)
        height = int(normal.bottom - normal.top)
        maximized = False

    if not minimized and width < 48 and height < 48:
        return
    if width <= 0 or height <= 0:
        return

    vis_left, vis_top, vis_width, vis_height = left, top, width, height
    if not minimized:
        vis_left, vis_top, vis_width, vis_height = _visible_frame(hwnd, left, top, width, height)

    found.append(
        {
            "hwnd": hwnd,
            "pid": int(pid.value),
            "process": process,
            "title": title[:180],
            "className": class_name,
            "x": left,
            "y": top,
            "width": width,
            "height": height,
            "visX": vis_left,
            "visY": vis_top,
            "visWidth": vis_width,
            "visHeight": vis_height,
            "maximized": maximized,
            "minimized": minimized,
        }
    )


def _visible_frame(hwnd: int, left: int, top: int, width: int, height: int) -> tuple[int, int, int, int]:
    rect = RECT()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    if hr != 0:
        return left, top, width, height
    vis_left, vis_top = int(rect.left), int(rect.top)
    vis_width = int(rect.right - rect.left)
    vis_height = int(rect.bottom - rect.top)
    if vis_width <= 0 or vis_height <= 0:
        return left, top, width, height
    return vis_left, vis_top, vis_width, vis_height


def place_window(hwnd: int, x: int, y: int, w: int, h: int, *, maximized: bool, minimize: bool) -> tuple[bool, str]:
    handle = wintypes.HWND(hwnd)
    if not user32.IsWindow(handle):
        return False, "That window already closed."
    user32.LockSetForegroundWindow(LSFW_LOCK)
    try:
        if user32.IsIconic(handle) or user32.IsZoomed(handle):
            user32.ShowWindow(handle, SW_RESTORE)
        ok = user32.SetWindowPos(
            handle,
            wintypes.HWND(0),
            int(x),
            int(y),
            int(w),
            int(h),
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        if not ok:
            err = ctypes.get_last_error()
            if err == 5:
                return False, "Windows blocked the move. If that app is running as administrator, Place. Stay. can't move it."
            return False, f"Windows wouldn't move that window ({err})."
        if maximized:
            user32.ShowWindow(handle, SW_MAXIMIZE)
        elif minimize:
            user32.ShowWindow(handle, SW_SHOWMINNOACTIVE)
    finally:
        user32.LockSetForegroundWindow(LSFW_UNLOCK)
    return True, ""


def find_titled(title: str) -> int:
    hwnd = user32.FindWindowW(None, title)
    return int(hwnd) if hwnd else 0


def style_frame(hwnd: int, *, dark: bool) -> None:
    if not hwnd:
        return
    handle = wintypes.HWND(hwnd)
    use_dark = ctypes.c_int(1 if dark else 0)
    dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(use_dark), ctypes.sizeof(use_dark))
    if dark:
        caption = 0x000E0F12  # #12100E in COLORREF
        text = 0x00E0E7F3
    else:
        caption = 0x00D6E0E6  # #E6E0D6
        text = 0x0016191C
    cap = wintypes.DWORD(caption)
    fg = wintypes.DWORD(text)
    dwmapi.DwmSetWindowAttribute(handle, 35, ctypes.byref(cap), ctypes.sizeof(cap))
    dwmapi.DwmSetWindowAttribute(handle, 36, ctypes.byref(fg), ctypes.sizeof(fg))


_instance_mutex = None
_shell_proc = None
_shell_hwnd = None


def claim_single_instance(title: str) -> bool:
    """Keep one copy running. A second launch opens the window that is already there."""
    global _instance_mutex
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, "Local\\PlaceStay.SingleInstance")
    if not handle:
        return True
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        reveal_window(find_titled(title))
        return False
    _instance_mutex = handle
    user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
    user32.AllowSetForegroundWindow.restype = wintypes.BOOL
    user32.AllowSetForegroundWindow(0xFFFFFFFF)
    return True


def reveal_window(hwnd: int) -> None:
    if not hwnd:
        return
    handle = wintypes.HWND(hwnd)
    user32.ShowWindow(handle, SW_RESTORE if user32.IsIconic(handle) else SW_SHOW)
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    foreground = user32.GetForegroundWindow()
    other = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    this = kernel32.GetCurrentThreadId()
    attached = bool(other and other != this and user32.AttachThreadInput(this, other, True))
    user32.SetForegroundWindow(handle)
    user32.BringWindowToTop(handle)
    if attached:
        user32.AttachThreadInput(this, other, False)


def watch_shell_events(on_recover, stop) -> None:
    """Put the tray icon back after sleep, unlock, or a restarted taskbar."""
    global _shell_proc
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")

    wndproc_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    def _proc(hwnd, msg, wparam, lparam):
        resume = msg == WM_POWERBROADCAST and int(wparam) in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC)
        unlock = msg == WM_WTSSESSION_CHANGE and int(wparam) in (1, 8)
        if msg == taskbar_created or resume or unlock:
            try:
                on_recover()
            except Exception:
                pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    _shell_proc = wndproc_type(_proc)

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", wndproc_type),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HANDLE),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HANDLE),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HANDLE),
        ]

    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    user32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.c_void_p]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
    user32.DispatchMessageW.restype = ctypes.c_ssize_t
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

    class_name = "PlaceStayShellWatch"
    info = WNDCLASSEXW()
    info.cbSize = ctypes.sizeof(WNDCLASSEXW)
    info.lpfnWndProc = _shell_proc
    info.hInstance = kernel32.GetModuleHandleW(None)
    info.lpszClassName = class_name
    if not user32.RegisterClassExW(ctypes.byref(info)):
        return
    hwnd = user32.CreateWindowExW(
        WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        class_name,
        "PlaceStayShellWatch",
        WS_POPUP,
        -32000,
        -32000,
        1,
        1,
        None,
        None,
        info.hInstance,
        None,
    )
    if not hwnd:
        return
    global _shell_hwnd
    _shell_hwnd = hwnd
    try:
        ctypes.WinDLL("wtsapi32", use_last_error=True).WTSRegisterSessionNotification(hwnd, 0)
    except Exception:
        pass

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", POINT),
        ]

    message = MSG()
    while not stop.is_set():
        if user32.GetMessageW(ctypes.byref(message), None, 0, 0) <= 0:
            break
        user32.TranslateMessage(ctypes.byref(message))
        user32.DispatchMessageW(ctypes.byref(message))


def stop_shell_watch() -> None:
    hwnd = _shell_hwnd
    if not hwnd:
        return
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.PostMessageW(hwnd, 0x0012, 0, 0)


def apply_window_icon(hwnd: int, ico_path: str) -> None:
    if not hwnd or not os.path.exists(ico_path):
        return
    LR_LOADFROMFILE = 0x00000010
    IMAGE_ICON = 1
    big = user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
    small = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    handle = wintypes.HWND(hwnd)
    if big:
        user32.SendMessageW(handle, 0x0080, 1, big)
    if small:
        user32.SendMessageW(handle, 0x0080, 0, small)
