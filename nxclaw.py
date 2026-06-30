#!/usr/bin/env python3
"""
NXClaw - A hacker-style CLI AI Agent.
Supports Ollama, OpenAI, and Claude. Built on standard libraries.
"""

import os
import re
import sys
import json
import time
import shutil
import signal
import platform
import subprocess
import urllib.request
import urllib.error
import urllib.parse
import getpass
import threading
import itertools
import io
import contextlib
import traceback
import difflib
from datetime import datetime

# --------------------------------------------------------------------------
# Globals / constants
# --------------------------------------------------------------------------

CONFIG_FILENAME = ".nxclaw_config.json"
VERSION = "3.0.0"

IS_WINDOWS = platform.system().lower().startswith("win")
IS_MACOS = platform.system().lower() == "darwin"
IS_LINUX = platform.system().lower() == "linux"

DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai": "https://api.openai.com/v1",
    "claude": "https://api.anthropic.com/v1",
}

FALLBACK_CLAUDE_MODELS = [
    "claude-fable-5",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-latest",
    "claude-3-opus-latest",
]

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/(\s|$)", r"rm\s+-rf\s+/\*", r"rm\s+-rf\s+~(\s|$)",
    r"rm\s+-rf\s+--no-preserve-root", r":\(\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r"mkfs\.", r"dd\s+.*of=/dev/(sd|hd|nvme|disk)", r">\s*/dev/(sd|hd|nvme|disk)[a-z0-9]*\s*$",
    r"chmod\s+-R\s+000\s+/(\s|$)", r"chown\s+-R\s+.*\s+/(\s|$)", r"format\s+[a-z]:\s*/y", r"diskpart"
]

DEFAULT_PERMISSIONS = {
    "read_file": "auto", "write_file": "ask", "patch_file": "ask",
    "run_command": "ask", "python_eval": "ask", "browse_web": "auto",
    "os_automation": "ask", "search_web": "auto"
}

# --------------------------------------------------------------------------
# UI Color Themes (Themes) - Defined above NXClawUI to prevent NameError
# --------------------------------------------------------------------------

THEMES = {
    "black": {
        "GREEN": "\033[38;5;46m", "BRIGHT_GREEN": "\033[38;5;82m",
        "CYAN": "\033[38;5;51m", "BRIGHT_CYAN": "\033[38;5;87m",
        "RED": "\033[38;5;196m", "YELLOW": "\033[38;5;220m",
        "GRAY": "\033[38;5;240m", "WHITE": "\033[38;5;231m",
        "MAGENTA": "\033[38;5;201m"
    },
    "gray": {
        "GREEN": "\033[38;5;108m", "BRIGHT_GREEN": "\033[38;5;150m",
        "CYAN": "\033[38;5;109m", "BRIGHT_CYAN": "\033[38;5;152m",
        "RED": "\033[38;5;167m", "YELLOW": "\033[38;5;214m",
        "GRAY": "\033[38;5;244m", "WHITE": "\033[38;5;223m",
        "MAGENTA": "\033[38;5;175m"
    },
    "white": {
        "GREEN": "\033[38;5;22m", "BRIGHT_GREEN": "\033[38;5;28m",
        "CYAN": "\033[38;5;25m", "BRIGHT_CYAN": "\033[38;5;31m",
        "RED": "\033[38;5;88m", "YELLOW": "\033[38;5;130m",
        "GRAY": "\033[38;5;244m", "WHITE": "\033[38;5;235m",
        "MAGENTA": "\033[38;5;90m"
    }
}

# --- Concise Multi-Language CLI Locales ---
LOCALES = {
    "en": {
        "status_model": "Model", "status_sandbox": "Sandbox", "status_confirm": "Permissions",
        "prompt_task": "Enter task, or /help. Ctrl+C twice to stop stream.",
        "empty_reply": "Warning: Received an empty response from the AI model.\nVerify your configuration.",
        "terminated": "[NXClaw] Session terminated. Goodbye.",
        "cancelled": "[cancelled] Interrupted by user.",
        "menu_nav": "Arrows to select, Enter to confirm, Q/Esc to go back.",
        "enter_for": "Enter for",
        "warning_tool_calling": "WARNING: Model MUST support structured tool calling.",
        "warning_tool_calling_sub": "If not, the agent may loop endlessly."
    },
    "zh": {
        "status_model": "模型", "status_sandbox": "沙箱", "status_confirm": "授權矩陣",
        "prompt_task": "請輸入任務指令，或輸入 /help。連擊 Ctrl+C 可停止串流。",
        "empty_reply": "警告：收到來自 AI 模型的空回覆。\n請確認連線與 API 金鑰配置是否正確。",
        "terminated": "[NXClaw] 對話結束。再見。",
        "cancelled": "[已取消] 使用者中斷執行。",
        "menu_nav": "方向鍵選擇，Enter鍵確認，Q/Esc鍵返回。",
        "enter_for": "Enter 預設為",
        "warning_tool_calling": "【注意】所選模型必須支援結構化工具呼叫功能。",
        "warning_tool_calling_sub": "若不支援，代理人可能會無限循環且無法改檔。"
    },
    "ja": {
        "status_model": "モデル", "status_sandbox": "領域", "status_confirm": "権限",
        "prompt_task": "タスクを入力、または /help。Ctrl+C連打でストリーム停止。",
        "empty_reply": "警告：AIモデルから空の応答を受信しました。\n設定を確認してください。",
        "terminated": "[NXClaw] セッション終了。さようなら。",
        "cancelled": "[キャンセル] ユーザーが中断しました。",
        "menu_nav": "矢印キーで選択、Enterで確定、Q/Escで戻る。",
        "enter_for": "Enterで",
        "warning_tool_calling": "【注意】選択するモデルはFunction Callingをサポートする必要があります。",
        "warning_tool_calling_sub": "非サポートの場合、無限ループに陥る可能性があります。"
    }
}

# --- Concise Interactive Academy Text cards ---
ACADEMY_TEXTS = {
    "en": {
        "title": "NXClaw Academy",
        "card1": "🌟 '@' Context Marker\n  Type @filename to load file context.\n  The '@' is stripped on file writes.",
        "card2": "🛡️ Unified Color Diffs\n  All file edits automatically show Git-style diffs.\n  Added shows in green (+), deleted in red (-).",
        "card3": "⚙️ Permission Matrix\n  Modify individual tools to run automatically (auto) or ask (ask).\n  Safely automate read operations.",
        "card4": "🚀 Desktop Automation\n  Generates AppleScripts (macOS) or PowerShell COM (Windows).\n  Automate Chrome, Outlook, and system Finder.",
        "card5": "🔍 Native Search Engine\n  Queries DuckDuckGo HTML directly through urllib.\n  Perform live searches without API keys."
    },
    "zh": {
        "title": "NXClaw 實戰技能學院",
        "card1": "🌟 「@」檔案標記\n  對話中輸入 @檔名 可在背景將檔案全文載入上下文。\n  AI 修改或建立該檔時，會自動去標記，不影響命名。",
        "card2": "🛡️ Unified 紅綠 Diffs\n  檔案寫入與修補完成後，會印出比對線。\n  綠色（+）代表新增代碼，紅色（-）代表被取代舊代碼。",
        "card3": "⚙️ 獨立工具授權矩陣\n  您可以針對個別工具指派直接執行（auto）或詢問許可（ask）。\n  建議放行讀檔，但對終端指令維持嚴格提示詢問。",
        "card4": "🚀 系統與桌面自動化\n  模型可生成 AppleScript 或 Windows PowerShell COM 代碼。\n  控制 Outlook、Chrome 或檔案管理器的自動化操作。",
        "card5": "🔍 原生免金鑰搜尋\n  導入 DuckDuckGo 原生搜尋，不依賴任何外部套件或 API Key。\n  AI 遇到未知資訊時，會主動抓取最新全球技術說明。"
    },
    "ja": {
        "title": "NXClaw アカデミー",
        "card1": "🌟 @ ファイル指定\n  @ファイル名 を指定すると、ファイル内容をコンテキストに追加します。\n  ツール実行時には @ は自動的に取り除かれます。",
        "card2": "🛡️ Unified Diffs\n  ファイルの書き込みやパッチ修正が完了すると、差分がカラー表示されます。\n  追加は緑色（+）、削除は赤色（-）です。",
        "card3": "⚙️ 権限マトリクス\n  各ツールについて、「自動実行（auto）」か「確認（ask）」を個別に設定可能。\n  読み取りは自動化、コマンド実行は確認が推奨されます。",
        "card4": "🚀 OS & アプリ自動化\n  OSを判別し、AppleScript（Mac）やPowerShell COM（Win）を生成。\n  Outlookメール操作や、Finder・Chromeコントロールが可能です。",
        "card5": "🔍 ネイティブWeb検索\n  urllibのみを使用し、DuckDuckGo HTMLバージョンから直接結果を取得。\n  APIキーや追加のライブラリなしで検索可能です。"
    }
}

# --------------------------------------------------------------------------
# Keyboard Interactive Selection Engine
# --------------------------------------------------------------------------

def get_key():
    if IS_WINDOWS:
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b'\x00', b'\xe0'):
            ch2 = msvcrt.getch()
            if ch2 == b'H': return "up"
            if ch2 == b'P': return "down"
            if ch2 == b'K': return "left"
            if ch2 == b'M': return "right"
        if ch in (b'\r', b'\n'):
            return "enter"
        if ch in (b'q', b'Q', b'\x1b'):
            return "quit"
        return None
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A': return "up"
                    if ch3 == 'B': return "down"
                    if ch3 == 'D': return "left"
                    if ch3 == 'C': return "right"
            elif ch in ('\r', '\n'):
                return "enter"
            elif ch in ('q', 'Q', '\x1b'):
                return "quit"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None


def interactive_menu(title, options, ui, current_index=0, lang="en"):
    while True:
        ui.clear()
        print(ui.c(f"╭─ {title} ─" + "─" * max(0, 50 - len(title)) + "╮", ui.CYAN))
        print()
        for idx, opt in enumerate(options):
            if idx == current_index:
                print(ui.c(f"  > {opt}", ui.BRIGHT_GREEN + ui.BOLD))
            else:
                print(ui.c(f"    {opt}", ui.GRAY))
        print()
        print(ui.c("╰" + "─" * 53 + "╯", ui.CYAN))
        print(ui.c(f"  {LOCALES[lang]['menu_nav']}", ui.GRAY))
        
        key = get_key()
        if key == "up":
            current_index = (current_index - 1) % len(options)
        elif key == "down":
            current_index = (current_index + 1) % len(options)
        elif key == "enter":
            return current_index
        elif key == "quit":
            return -1


# --------------------------------------------------------------------------
# Version Check & Auto-Updater Utilities
# --------------------------------------------------------------------------

def get_remote_version():
    url = "https://raw.githubusercontent.com/NeuralNexusLab-nh/NXClaw/main/version.txt"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NXClaw-Updater"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            remote_ver = resp.read().decode("utf-8").strip()
            if remote_ver and not remote_ver.startswith("<") and len(remote_ver) < 20:
                return remote_ver
    except Exception:
        pass
    return None


def trigger_auto_update(config, ui):
    is_exe = getattr(sys, "frozen", False)
    current_file = sys.executable if is_exe else __file__
    
    ui.clear()
    ui.info_box("UPDATER ACTIVE", "Downloading the latest version from official NeuralNexusLab repository...")
    
    base_url = "https://raw.githubusercontent.com/NeuralNexusLab-nh/NXClaw/main"
    try:
        if is_exe:
            target_url = f"{base_url}/nxclaw.exe"
            temp_file = os.path.join(os.path.dirname(current_file), "nxclaw_new.exe")
            with urllib.request.urlopen(target_url, timeout=30) as resp:
                with open(temp_file, "wb") as f:
                    f.write(resp.read())
        else:
            py_url = f"{base_url}/nxclaw.py"
            sh_url = f"{base_url}/nxclaw.sh"
            temp_py = os.path.join(os.path.dirname(current_file), "nxclaw_new.py")
            temp_sh = os.path.join(os.path.dirname(current_file), "nxclaw_new.sh")
            
            with urllib.request.urlopen(py_url, timeout=30) as resp:
                with open(temp_py, "wb") as f:
                    f.write(resp.read())
            try:
                with urllib.request.urlopen(sh_url, timeout=30) as resp:
                    with open(temp_sh, "wb") as f:
                        f.write(resp.read())
            except Exception:
                pass
    except Exception as e:
        ui.error_box("DOWNLOAD FAILED", f"Could not retrieve updates: {e}")
        return

    ui.info_box("INSTALLING UPDATE", "Spawning background installer process. NXClaw will restart...")
    time.sleep(1)

    if IS_WINDOWS:
        bat_path = os.path.join(os.path.dirname(current_file), "update_temp.bat")
        if is_exe:
            bat_lines = [
                "@echo off",
                "timeout /t 1 > nul",
                f'del "{current_file}"',
                f'ren "{temp_file}" "{os.path.basename(current_file)}"',
                f'start "" "{current_file}"',
                'del "%~f0"'
            ]
        else:
            bat_lines = [
                "@echo off",
                "timeout /t 1 > nul",
                f'del "{current_file}"',
                f'ren "{temp_py}" "{os.path.basename(current_file)}"',
                f'python "{current_file}"',
                'del "%~f0"'
            ]
        # Windows batch requires \r\n line breaks
        bat_content = "\r\n".join(bat_lines) + "\r\n"
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        subprocess.Popen(["cmd.exe", "/c", bat_path], shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        sh_path = os.path.join(os.path.dirname(current_file), "update_temp.sh")
        if is_exe:
            sh_lines = [
                "#!/bin/sh",
                "sleep 1",
                f'rm -f "{current_file}"',
                f'mv "{temp_file}" "{current_file}"',
                f'chmod +x "{current_file}"',
                f'"{current_file}" &',
                'rm -f "$0"'
            ]
        else:
            sh_lines = [
                "#!/bin/sh",
                "sleep 1",
                f'rm -f "{current_file}"',
                f'mv "{temp_py}" "{current_file}"',
                'if [ -f "' + temp_sh + '" ]; then',
                '    rm -f "nxclaw.sh"',
                '    mv "' + temp_sh + '" "nxclaw.sh"',
                '    chmod +x "nxclaw.sh"',
                'fi',
                f'python3 "{current_file}" &',
                'rm -f "$0"'
            ]
        # Unix shells require standard \n line breaks
        sh_content = "\n".join(sh_lines) + "\n"
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write(sh_content)
        subprocess.Popen(["/bin/sh", sh_path], start_new_session=True)

    sys.exit(0)


# --------------------------------------------------------------------------
# UI Color Themes (Themes)
# --------------------------------------------------------------------------

def apply_theme_palette(theme_name):
    palette = THEMES.get(theme_name.lower(), THEMES["black"])
    for k, v in palette.items():
        setattr(NXClawUI, k, v)


# --- Helper methods ---

def open_file_in_editor(file_path):
    try:
        if IS_WINDOWS:
            try:
                os.startfile(file_path)
            except AttributeError:
                escaped = file_path.replace('"', '\\"')
                subprocess.run(f'start "" "{escaped}"', shell=True)
        elif IS_MACOS:
            subprocess.run(["open", file_path], check=True)
        else:
            try:
                subprocess.run(["xdg-open", file_path], check=True)
            except Exception:
                editor = os.environ.get("EDITOR", "nano")
                subprocess.run([editor, file_path])
    except Exception as e:
        raise OSError(f"Failed to open editor: {e}")


def process_file_attachments(user_input, tools_instance):
    matches = re.findall(r"@([a-zA-Z0-9_\-\.\/]+)", user_input)
    if not matches:
        return user_input
    
    unique_matches = list(dict.fromkeys(matches))
    appended_context = ""
    for filename in unique_matches:
        try:
            safe_path = tools_instance._resolve_safe_path(filename)
            if os.path.isfile(safe_path):
                with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                appended_context += f"\n\n=== ATTACHED FILE CONTENT: {filename} ===\n{content}\n================================="
        except Exception:
            pass
            
    if appended_context:
        return user_input + "\n" + appended_context
    return user_input


def generate_diff_view(old_content, new_content, file_path, ui):
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
        n=3
    )
    
    colored_lines = []
    for line in diff:
        clean_line = line.rstrip('\r\n')
        if clean_line.startswith('+') and not clean_line.startswith('+++'):
            colored_lines.append(ui.c(clean_line, ui.GREEN))
        elif clean_line.startswith('-') and not clean_line.startswith('---'):
            colored_lines.append(ui.c(clean_line, ui.RED))
        elif clean_line.startswith('@@'):
            colored_lines.append(ui.c(clean_line, ui.CYAN))
        else:
            colored_lines.append(ui.c(clean_line, ui.GRAY))
            
    return "\n".join(colored_lines)


# --------------------------------------------------------------------------
# Stream Printing Filter
# --------------------------------------------------------------------------

class StreamFilter:
    def __init__(self, callback):
        self.callback = callback
        self.buffer = ""
        self.in_tool_call = False

    def feed(self, chunk):
        for char in chunk:
            self.buffer += char
            
            if not self.in_tool_call:
                if self.buffer.startswith("<"):
                    target = "<tool_call"
                    if len(self.buffer) <= len(target):
                        if target.startswith(self.buffer):
                            continue
                        else:
                            self.callback(self.buffer)
                            self.buffer = ""
                    else:
                        if self.buffer.startswith("<tool_call"):
                            self.in_tool_call = True
                            continue
                        else:
                            self.callback(self.buffer)
                            self.buffer = ""
                else:
                    self.callback(self.buffer)
                    self.buffer = ""
            else:
                end_tag = "</tool_call>"
                if self.buffer.endswith(end_tag):
                    self.buffer = ""
                    self.in_tool_call = False
                    self.callback("\n\n[NXClaw Intercepted Tool Call...]\n")
                else:
                    continue

    def flush(self):
        if self.buffer and not self.in_tool_call:
            self.callback(self.buffer)
            self.buffer = ""


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

class NXClawConfig:
    def __init__(self, workspace=None):
        self.workspace = workspace or os.path.join(os.path.expanduser("~"), "NXClaw")
        self.path = os.path.join(self.workspace, CONFIG_FILENAME)
        self.data = {}
        self.load_error = None

    def exists(self):
        return os.path.isfile(self.path)

    def load(self):
        self.load_error = None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            self.data = {}
            self.load_error = f"Could not read config file: {e}"
            return False

        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Config content is not a valid JSON object.")
            self.data = parsed
            return True
        except (json.JSONDecodeError, ValueError) as e:
            self.load_error = f"Config file corrupted: {e}"
            try:
                backup_path = self.path + ".bak"
                shutil.copy2(self.path, backup_path)
            except OSError:
                pass
            self.data = {}
            return False

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
            return True
        except OSError as e:
            print(f"[!] Saving config failed: {e}")
            return False

    def set_workspace(self, workspace):
        self.workspace = workspace
        self.path = os.path.join(self.workspace, CONFIG_FILENAME)

    @property
    def provider(self):
        return self.data.get("provider", "ollama")

    @property
    def endpoint(self):
        return self.data.get("endpoint", DEFAULT_ENDPOINTS["ollama"])

    @property
    def api_key(self):
        return self.data.get("api_key", "")

    @property
    def model(self):
        return self.data.get("model", "")

    @model.setter
    def model(self, value):
        self.data["model"] = value

    @property
    def permissions(self):
        if "permissions" not in self.data or not isinstance(self.data["permissions"], dict):
            self.data["permissions"] = dict(DEFAULT_PERMISSIONS)
        return self.data["permissions"]

    @property
    def lang(self):
        return self.data.get("lang", "en")

    @lang.setter
    def lang(self, value):
        self.data["lang"] = value

    @property
    def theme(self):
        return self.data.get("theme", "black")

    @theme.setter
    def theme(self, value):
        self.data["theme"] = value

    @property
    def tutorial_completed(self):
        return bool(self.data.get("tutorial_completed", False))

    @tutorial_completed.setter
    def tutorial_completed(self, value):
        self.data["tutorial_completed"] = bool(value)


# --------------------------------------------------------------------------
# UI: Layout and Themes
# --------------------------------------------------------------------------

class NXClawUI:
    _ansi_ready = False
    _color_enabled = True

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = ""
    BRIGHT_GREEN = ""
    CYAN = ""
    BRIGHT_CYAN = ""
    RED = ""
    YELLOW = ""
    GRAY = ""
    WHITE = ""
    MAGENTA = ""

    THEMES = THEMES

    BANNER = r"""
 _   ___   __ _____ _                 
| \ | \ \ / //  __ \ |                
|  \| |\ V / | /  \/ |     __ _ _      __
| . ` |/   \ | |   | |    / _` \ \ /\ / /
| |\  / /^\ \| \__/\ |___| (_| |\ V  V / 
|_| \_\/   \/ \____/\____/\__,_| \_/\_/ ©

"""

    @classmethod
    def enable_ansi(cls):
        if cls._ansi_ready:
            return
        cls._ansi_ready = True

        try:
            if not sys.stdout.isatty():
                cls._color_enabled = False
                return
        except (AttributeError, ValueError):
            cls._color_enabled = False
            return

        if IS_WINDOWS:
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetStdHandle(-11)
                if handle == 0 or handle == -1:
                    cls._color_enabled = False
                    return
                mode = ctypes.c_uint32()
                if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    cls._color_enabled = False
                    return
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                if not kernel32.SetConsoleMode(handle, new_mode):
                    cls._color_enabled = False
                    return
                cls._color_enabled = True
            except Exception:
                cls._color_enabled = False
        else:
            cls._color_enabled = True

    @classmethod
    def clear(cls):
        if cls._color_enabled:
            sys.stdout.write("\033[H\033[2J\033[3J")
            sys.stdout.flush()
        else:
            try:
                os.system("cls" if IS_WINDOWS else "clear")
            except Exception:
                print("\n" * 50)

    @classmethod
    def c(cls, text, color):
        if not cls._color_enabled:
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def banner(cls):
        cls.clear()
        print(cls.c(cls.BANNER, cls.BRIGHT_GREEN))
        sub = "  >> Autonomous Terminal Agent <<"
        print(cls.c(sub, ui.CYAN))
        print(cls.c(f"  v{VERSION}  |  {platform.system()}", cls.GRAY))
        print()

    @classmethod
    def boot_sequence(cls):
        steps = [
            "Initializing NXClaw Core...",
            "Loading Neural Link...",
            "Calibrating ANSI render pipeline...",
            "Detecting local environment... OK",
            "Mounting workspace sandbox...",
            "Spinning up REPL kernel...",
        ]
        for step in steps:
            sys.stdout.write(cls.c("  [boot] ", cls.GREEN) + cls.c(step, cls.GRAY) + "\n")
            sys.stdout.flush()
            time.sleep(0.5 / len(steps) * 1.6)
        print()

    @staticmethod
    def _display_width(text):
        import unicodedata
        width = 0
        for ch in text:
            if unicodedata.east_asian_width(ch) in ("W", "F"):
                width += 2
            else:
                width += 1
        return width

    @classmethod
    def _wrap_by_width(cls, text, max_width):
        if cls._display_width(text) <= max_width:
            return [text]
        lines = []
        current = ""
        current_width = 0
        for ch in text:
            ch_width = 2 if __import__("unicodedata").east_asian_width(ch) in ("W", "F") else 1
            if current_width + ch_width > max_width:
                lines.append(current)
                current = ch
                current_width = ch_width
            else:
                current += ch
                current_width += ch_width
        if current:
            lines.append(current)
        return lines

    @classmethod
    def hr(cls, char="─", width=None, color=None):
        width = width or shutil.get_terminal_size((80, 20)).columns
        color = color or cls.GRAY
        print(cls.c(char * width, color))

    @classmethod
    def box(cls, title, body, color=None, width=None):
        color = color or cls.CYAN
        term_width = shutil.get_terminal_size((80, 20)).columns
        width = width or min(term_width - 2, 100)
        inner_width = width - 4

        lines = []
        for raw_line in body.split("\n"):
            if raw_line == "":
                lines.append("")
                continue
            lines.extend(cls._wrap_by_width(raw_line, inner_width))

        title_width = cls._display_width(title)
        top = "╭─ " + title + " " + "─" * max(0, width - title_width - 4) + "╮"
        bottom = "╰" + "─" * (width - 2) + "╯"

        print(cls.c(top, color))
        for line in lines:
            pad = inner_width - cls._display_width(line)
            print(cls.c("│ ", color) + line + (" " * max(0, pad)) + cls.c(" │", color))
        print(cls.c(bottom, color))

    @classmethod
    def error_box(cls, title, body):
        cls.box(title, body, color=cls.RED)

    @classmethod
    def success_box(cls, title, body):
        cls.box(title, body, color=cls.BRIGHT_GREEN)

    @classmethod
    def info_box(cls, title, body):
        cls.box(title, body, color=cls.CYAN)


class Spinner:
    FRAMES = ["⠇", "⠋", "⠙", "⠸", "⠴", "⠦"]

    def __init__(self, message="Thinking", color=None):
        self.message = message
        self.color = color or NXClawUI.CYAN
        self._stop_event = threading.Event()
        self._thread = None

    def _spin(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop_event.is_set():
                break
            sys.stdout.write(
                NXClawUI.c(f"{frame} {self.message}...", self.color) + "   "
                if NXClawUI._color_enabled
                else f"{frame} {self.message}...   "
            )
            sys.stdout.write("\r")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self.message) + 14) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)


class TaskCancelled(Exception):
    pass


class InterruptibleCall:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._done = threading.Event()
        self._result = None
        self._exception = None

    def _runner(self):
        try:
            self._result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self._exception = e
        finally:
            self._done.set()

    def run(self, poll_interval=0.1):
        thread = threading.Thread(target=self._runner, daemon=True)
        thread.start()
        
        ctrl_c_pressed = False
        last_press_time = 0
        
        while not self._done.is_set():
            try:
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                now = time.time()
                if not ctrl_c_pressed:
                    ctrl_c_pressed = True
                    last_press_time = now
                    sys.stderr.write(
                        NXClawUI.c("\n[!] Press Ctrl+C again to confirm stopping output...\n", NXClawUI.YELLOW)
                    )
                    sys.stderr.flush()
                else:
                    if now - last_press_time <= 2.5:
                        raise TaskCancelled("Cancelled by user (double Ctrl+C).")
                    else:
                        last_press_time = now
                        sys.stderr.write(
                            NXClawUI.c("\n[!] Press Ctrl+C again to confirm stopping output...\n", NXClawUI.YELLOW)
                        )
                        sys.stderr.flush()
            
            if ctrl_c_pressed and (time.time() - last_press_time > 2.5):
                ctrl_c_pressed = False

        if self._exception is not None:
            raise self._exception
        return self._result


# --------------------------------------------------------------------------
# API Client with Streaming Support
# --------------------------------------------------------------------------

class APIError(Exception):
    pass


class NXClawAPIClient:
    def __init__(self, provider, endpoint, api_key, model, timeout=120):
        self.provider = provider
        self.endpoint = (endpoint or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout

    def _get(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            raise APIError(f"HTTP {e.code} from {url}")
        except urllib.error.URLError as e:
            raise APIError(f"Connection error reaching {url}: {e.reason}")
        except json.JSONDecodeError as e:
            raise APIError(f"Could not parse JSON response from {url}: {e}")

    def chat(self, system_prompt, messages, on_chunk_cb=None):
        if self.provider == "ollama":
            return self._chat_ollama(system_prompt, messages, on_chunk_cb)
        elif self.provider == "openai":
            return self._chat_openai(system_prompt, messages, on_chunk_cb)
        elif self.provider == "claude":
            return self._chat_claude(system_prompt, messages, on_chunk_cb)
        else:
            raise APIError(f"Unknown provider: {self.provider}")

    def _chat_ollama(self, system_prompt, messages, on_chunk_cb=None):
        url = f"{self.endpoint}/api/chat"
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
        }
        headers = {"Content-Type": "application/json"}
        full_text = []
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for line_bytes in _iter_lines(resp):
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_text.append(content)
                            if on_chunk_cb:
                                on_chunk_cb(content)
                        if chunk.get("done") is True:
                            break
                    except Exception:
                        pass
            return "".join(full_text)
        except Exception:
            url2 = f"{self.endpoint}/v1/chat/completions"
            payload2 = {
                "model": self.model,
                "messages": full_messages,
                "stream": True,
            }
            data2 = json.dumps(payload2).encode("utf-8")
            req2 = urllib.request.Request(url2, data=data2, headers=headers, method="POST")
            full_text = []
            with urllib.request.urlopen(req2, timeout=self.timeout) as resp:
                for line_bytes in _iter_lines(resp):
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                full_text.append(content)
                                if on_chunk_cb:
                                    on_chunk_cb(content)
                        except Exception:
                            pass
            return "".join(full_text)

    def _chat_openai(self, system_prompt, messages, on_chunk_cb=None):
        url = f"{self.endpoint}/chat/completions"
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        full_text = []
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for line_bytes in _iter_lines(resp):
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            full_text.append(content)
                            if on_chunk_cb:
                                on_chunk_cb(content)
                    except Exception:
                        pass
        return "".join(full_text)

    def _chat_claude(self, system_prompt, messages, on_chunk_cb=None):
        url = f"{self.endpoint}/messages"
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
            "stream": True,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        full_text = []
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for line_bytes in _iter_lines(resp):
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        event_type = chunk.get("type")
                        if event_type == "content_block_delta":
                            text = chunk.get("delta", {}).get("text", "")
                            if text:
                                full_text.append(text)
                                if on_chunk_cb:
                                    on_chunk_cb(text)
                        elif event_type == "message_stop":
                            break
                    except Exception:
                        pass
        return "".join(full_text)

    def list_models(self):
        if self.provider == "ollama":
            try:
                data = self._get(f"{self.endpoint}/api/tags")
                models = data.get("models", [])
                names = [m.get("name") for m in models if m.get("name")]
                if names:
                    return names
            except APIError:
                pass
            data = self._get(f"{self.endpoint}/v1/models")
            items = data.get("data", [])
            return [m.get("id") for m in items if m.get("id")]

        elif self.provider == "openai":
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            data = self._get(f"{self.endpoint}/models", headers=headers)
            items = data.get("data", [])
            names = [m.get("id") for m in items if m.get("id")]
            if not names:
                raise APIError("No models returned.")
            return names

        elif self.provider == "claude":
            return list(FALLBACK_CLAUDE_MODELS)

        else:
            raise APIError(f"Unknown provider: {self.provider}")


# --------------------------------------------------------------------------
# Agent: tool-call protocol, system prompt, ReAct loop
# --------------------------------------------------------------------------

def build_system_prompt(workspace_root, os_name):
    return f"""You are NXClaw, an autonomous, highly proactive terminal coding agent operating inside a sandboxed workspace at: {workspace_root}
The host system is running: {os_name}

YOUR PRIMARY DIRECTIVE:
You must be heavily biased towards action. If a task can be accomplished or verified using a tool, you MUST use that tool immediately rather than writing long prose or explaining hypothetical scenarios. Your name is Claw — use your tools!

To make edits, create scripts, inspect structures, or run tests, issue tool calls immediately. Do not explain your code in conversational text; instead, write or patch the code directly into files using your tools and summarize what was accomplished in brief sentences.

THE "@" SYMBOL FILENAME RULE:
The "@" symbol is an indicator prefix used by users in conversational prompts to reference or mark files (e.g., "Review @main.py"). 
It is NOT part of the physical file path or filename on disk. When you construct paths for your tools, you must always omit the leading "@" (e.g., use "main.py", not "@main.py").

To call a tool, output ONLY a tool_call XML block, exactly in this format (no markdown fences, no extra commentary mixed into the tag):

<tool_call name="TOOL_NAME">
    <param_name>value</param_name>
</tool_call>

You may include normal text before or after a tool call, but the tool_call block itself must be well-formed XML with no nested unescaped '<' or '>' inside parameter values.

Available tools:

1. run_command (run shell commands, test code, inspect environment)
   <tool_call name="run_command">
       <command>shell command here</command>
   </tool_call>

2. write_file (creates or overwrites a file; cannot escape the workspace root)
   <tool_call name="write_file">
       <path>relative/or/absolute/path.ext</path>
       <content>full file content here</content>
   </tool_call>

3. read_file (read file content to gain context)
   <tool_call name="read_file">
       <path>relative/or/absolute/path.ext</path>
   </tool_call>

4. patch_file (search_block must match EXACTLY ONCE in the file, including whitespace)
   <tool_call name="patch_file">
       <path>relative/or/absolute/path.ext</path>
       <search_block>exact text to find</search_block>
       <replace_block>replacement text</replace_block>
   </tool_call>

5. python_eval (runs Python in-process and returns stdout/stderr; use for quick computation)
   <tool_call name="python_eval">
       <code>print("hello")</code>
   </tool_call>

6. browse_web (fetches a URL and returns cleaned, readable text, up to 3000 chars)
   <tool_call name="browse_web">
       <url>https://example.com</url>
   </tool_call>

7. os_automation (runs standard PowerShell/AppleScript/Bash code to operate system level features or third party desktop apps like Chrome, File managers or Outlook)
   <tool_call name="os_automation">
       <script_code>script commands here</script_code>
   </tool_call>

8. search_web (queries DuckDuckGo HTML layout securely and outputs top results, urls and summaries)
   <tool_call name="search_web">
       <query>search term</query>
   </tool_call>

Rules:
- Issue ONE tool call at a time. Wait for the result before deciding the next step.
- When the task is fully complete, respond with a normal text summary and DO NOT include any tool_call block.
- All file paths are relative to the workspace root unless absolute; absolute paths outside the workspace will be rejected.
- Minimize conversational output. Let your tool actions speak for themselves.
- If a tool call fails, analyze the error and immediately try an alternative tool action to correct it. Do not give up or ask the user for permission to try another path — just try it.
"""


class ParsedToolCall:
    def __init__(self, name, params, raw_match):
        self.name = name
        self.params = params
        self.raw_match = raw_match


def parse_tool_call(llm_text):
    match = TOOL_CALL_RE.search(llm_text)
    if not match:
        return llm_text.strip(), None

    tool_name = match.group(1).strip()
    inner = match.group(2)
    text_before = llm_text[: match.start()].strip()

    params = {}
    for pmatch in PARAM_RE.finditer(inner):
        key, value = pmatch.group(1), pmatch.group(2)
        params[key] = _unescape_param(value)

    return text_before, ParsedToolCall(tool_name, params, match.group(0))


def _unescape_param(value):
    value = value.strip("\n")
    replacements = {
        "&lt;": "<", "&gt;": ">", "&amp;": "&",
        "&quot;": '"', "&apos;": "'",
    }
    for ent, repl in replacements.items():
        value = value.replace(ent, repl)
    # Debug: Resolve search_block spacing exceptions by converting literal string escapes
    value = value.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    return value


class NXClawAgent:
    def __init__(self, config: NXClawConfig, ui: NXClawUI):
        self.config = config
        self.ui = ui
        self.tools = NXClawTools(config.workspace)
        self.client = NXClawAPIClient(
            provider=config.provider,
            endpoint=config.endpoint,
            api_key=config.api_key,
            model=config.model,
        )
        self.history = []
        self._load_agent_guidelines()
        self.last_diff = None

    def _load_agent_guidelines(self):
        """Builds system prompt, appending custom rules from workspace's agent.md if present."""
        os_desc = f"{platform.system()} {platform.release()} ({platform.machine()})"
        base_prompt = build_system_prompt(self.tools.workspace_root, os_desc)
        
        custom_rules = ""
        for name in ("agent.md", ".agent_rules.md"):
            rules_path = os.path.join(self.tools.workspace_root, name)
            if os.path.isfile(rules_path):
                try:
                    with open(rules_path, "r", encoding="utf-8", errors="replace") as f:
                        custom_rules = f.read().strip()
                    break
                except Exception:
                    pass
        
        if custom_rules:
            self.system_prompt = base_prompt + f"\n\n=== USER-DEFINED GUIDELINES (agent.md) ===\n{custom_rules}\n========================================="
        else:
            self.system_prompt = base_prompt

    def refresh_client(self):
        self.tools = NXClawTools(self.config.workspace)
        self.client = NXClawAPIClient(
            provider=self.config.provider,
            endpoint=self.config.endpoint,
            api_key=self.config.api_key,
            model=self.config.model,
        )
        self._load_agent_guidelines()

    def clear_history(self):
        self.history = []

    def _trim_history(self):
        if len(self.history) > MAX_HISTORY_MESSAGES:
            overflow = len(self.history) - MAX_HISTORY_MESSAGES
            self.history = self.history[overflow:]

    def _ask_confirmation(self, tool_call: ParsedToolCall):
        ui = self.ui
        print()
        ui.box(
            f"TOOL REQUEST: {tool_call.name}",
            self._format_params_preview(tool_call),
            color=ui.YELLOW,
        )
        if tool_call.name == "run_command" and self.tools.is_dangerous_command(
            tool_call.params.get("command", "")
        ):
            ui.error_box(
                "DANGER WARNING",
                "This command matches a known catastrophic pattern "
                "(e.g., recursive deletion, disk wipe, or fork bomb).",
            )
        try:
            answer = input(
                ui.c("  Allow this action? [y/N]: ", ui.MAGENTA)
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")

    @staticmethod
    def _format_params_preview(tool_call: ParsedToolCall):
        lines = []
        for key, value in tool_call.params.items():
            preview = value if len(value) <= 400 else value[:400] + " ... [truncated]"
            lines.append(f"{key}:\n{preview}")
        return "\n\n".join(lines) if lines else "(no parameters)"

    def _execute_tool(self, tool_call: ParsedToolCall):
        name = tool_call.name
        params = tool_call.params
        expected = TOOL_SPECS.get(name)

        if expected is None:
            return f"[error] Unknown tool '{name}'. Available: {', '.join(TOOL_SPECS)}."

        missing = [p for p in expected if p not in params]
        if missing:
            return f"[error] Tool '{name}' missing required parameter(s): {', '.join(missing)}."

        if name == "run_command" and self.config.permissions.get("run_command") == "auto":
            if self.tools.is_dangerous_command(params["command"]):
                return (
                    "[blocked] This command matches a known dangerous pattern "
                    "and was blocked even though auto-confirm is enabled."
                )

        # Print cyan tool logging before execution
        log_line = f"[NXClaw] Executing Tool: {name}"
        if name == "run_command":
            log_line += f" -> command: \"{params.get('command')}\""
        elif name == "read_file":
            log_line += f" -> path: \"{params.get('path')}\""
        elif name == "write_file":
            content_len = len(params.get('content', ''))
            log_line += f" -> path: \"{params.get('path')}\" ({content_len} characters)"
        elif name == "patch_file":
            log_line += f" -> path: \"{params.get('path')}\""
        elif name == "python_eval":
            code_len = len(params.get('code', ''))
            log_line += f" -> code length: {code_len} characters"
        elif name == "browse_web":
            log_line += f" -> url: \"{params.get('url')}\""
        elif name == "os_automation":
            script_len = len(params.get('script_code', ''))
            log_line += f" -> script length: {script_len} characters"
        elif name == "search_web":
            log_line += f" -> query: \"{params.get('query')}\""
            
        print(self.ui.c(log_line, self.ui.CYAN))

        old_content = None
        target_path = None
        if name in ("write_file", "patch_file") and "path" in params:
            try:
                target_path = self.tools._resolve_safe_path(params["path"])
                if os.path.isfile(target_path):
                    with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                        old_content = f.read()
            except Exception:
                pass

        # Perform check against the dynamic config permissions matrix
        perm_rule = self.config.permissions.get(name, "ask")
        if perm_rule == "ask":
            allowed = self._ask_confirmation(tool_call)
            if not allowed:
                return "[denied] The user declined to execute this tool call."

        try:
            if name == "run_command":
                result = self.tools.run_command(params["command"])
            elif name == "write_file":
                result = self.tools.write_file(params["path"], params["content"])
            elif name == "read_file":
                result = self.tools.read_file(params["path"])
            elif name == "patch_file":
                result = self.tools.patch_file(
                    params["path"], params["search_block"], params["replace_block"]
                )
            elif name == "python_eval":
                result = self.tools.python_eval(params["code"])
            elif name == "browse_web":
                result = self.tools.browse_web(params["url"])
            elif name == "os_automation":
                result = self.tools.os_automation(params["script_code"])
            elif name == "search_web":
                result = self.tools.search_web(params["query"])
        except Exception as e:
            return f"[error] Tool '{name}' raised unexpected exception: {e}"

        # Capture post-modification state and compile diff output
        if name in ("write_file", "patch_file") and target_path and not result.startswith("[error]"):
            try:
                new_content = ""
                if os.path.isfile(target_path):
                    with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                        new_content = f.read()
                
                rel_path = os.path.relpath(target_path, self.tools.workspace_root)
                diff_view = generate_diff_view(old_content, new_content, rel_path, self.ui)
                if diff_view.strip():
                    self.last_diff = diff_view
                else:
                    self.last_diff = None
            except Exception:
                self.last_diff = None
        else:
            self.last_diff = None

        return result

    def _print_api_error(self, error: "APIError"):
        ui = self.ui
        msg = str(error)
        hints = []

        if "Connection error" in msg or "Errno 111" in msg or "refused" in msg.lower():
            hints.append(
                "Could not connect to the API. Verify that:\n"
                f"  1) The Endpoint is correct (Current: {self.config.endpoint})\n"
                "  2) Your local provider (like Ollama) is actively running.\n"
                "  3) No firewall, VPN, or proxy is blocking the port."
            )
        elif "HTTP 401" in msg or "HTTP 403" in msg:
            hints.append(
                "Access was denied (401/403). Use /settings to check your API key."
            )
        elif "HTTP 404" in msg:
            hints.append(
                "Endpoint or Model not found (404). Check both endpoint and model name."
            )
        elif "HTTP 429" in msg:
            hints.append("Rate limit reached (429). Please wait before requesting again.")
        elif "HTTP 5" in msg:
            hints.append("Remote server error (5xx). This is likely temporary.")

        body = msg
        if hints:
            body += "\n\n" + "\n\n".join(hints)
        ui.error_box("API ERROR", body)

    def run_task(self, user_input):
        ui = self.ui
        lang = self.config.lang
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        max_iterations = self.config.data.get("max_iterations", 100)
        for iteration in range(max_iterations):
            try:
                print(ui.c(f"\n[NXClaw] Thinking (Iteration {iteration + 1}/{max_iterations})", ui.BRIGHT_GREEN))
                
                # Active character filter that suppresses raw <tool_call> tags while streaming
                filter_stream = StreamFilter(lambda text: (sys.stdout.write(text), sys.stdout.flush()))

                def on_chunk(text):
                    filter_stream.feed(text)

                call = InterruptibleCall(self.client.chat, self.system_prompt, self.history, on_chunk_cb=on_chunk)
                reply = call.run()
                filter_stream.flush()
                print()  # Final newline after stream completes
            except TaskCancelled:
                ui.box(
                    "CANCELLED",
                    "Interrupted waiting for AI response.\n"
                    "Background connections have been abandoned.",
                    color=ui.YELLOW,
                )
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return
            except APIError as e:
                self._print_api_error(e)
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return
            except Exception as e:
                ui.error_box(
                    "UNEXPECTED ERROR",
                    f"{type(e).__name__}: {e}\n\n"
                    f"{traceback.format_exc(limit=3)}",
                )
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return

            # Silent exit mitigation checks
            if not reply or not reply.strip():
                print()
                ui.error_box("API WARNING", LOCALES[lang]["empty_reply"])
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return

            text_before, tool_call = parse_tool_call(reply)

            if tool_call is None:
                self.history.append({"role": "assistant", "content": reply})
                self._trim_history()
                return

            self.history.append({"role": "assistant", "content": reply})

            try:
                result = self._execute_tool(tool_call)
            except KeyboardInterrupt:
                result = "[cancelled] Tool action terminated by user."
                ui.box("CANCELLED", "Tool execution aborted.", color=ui.YELLOW)

            self._print_tool_result(tool_call, result)

            tool_feedback = f"[tool_result name=\"{tool_call.name}\"]\n{result}\n[/tool_result]"
            self.history.append({"role": "user", "content": tool_feedback})
            self._trim_history()
        else:
            ui.error_box(
                "ITERATION LIMIT EXCEEDED",
                f"Aborted after {max_iterations} recursive loops to avoid runaway charges."
            )

    def _print_tool_result(self, tool_call, result):
        ui = self.ui
        is_error = isinstance(result, str) and (
            result.startswith("[error]") or result.startswith("[blocked]") or result.startswith("[denied]")
        )
        color = ui.RED if is_error else ui.BRIGHT_CYAN
        title = f"RESULT: {tool_call.name}"

        # Clean display management on tool completions
        if tool_call.name == "read_file" and not is_error:
            line_count = len(result.splitlines())
            char_count = len(result)
            summary_msg = f"[ok] File '{tool_call.params.get('path')}' successfully loaded ({line_count} lines, {char_count} characters)."
            ui.box(title, summary_msg, color=color)
        elif tool_call.name in ("write_file", "patch_file") and not is_error and self.last_diff:
            ui.box(title, self.last_diff, color=color)
        else:
            ui.box(title, result if result else "(empty)", color=color)


# --------------------------------------------------------------------------
# Settings & Configuration Menus
# --------------------------------------------------------------------------

def run_granular_settings(config: NXClawConfig, ui: NXClawUI):
    """Arrow-key driven granular configuration. Allows editing single parameters recursively."""
    lang = config.lang
    options = [
        "1. Backend Provider",
        "2. API Endpoint URL",
        "3. API Key",
        "4. Model Name",
        "5. Workspace Sandbox Path",
        "6. Maximum Tool Iterations Limit",
        "7. Permissions Matrix",
        "8. Display Language",
        "9. Theme Style",
        "10. Save & Exit"
    ]
    
    while True:
        idx = interactive_menu("NXClaw Settings Workspace", options, ui, current_index=0, lang=lang)
        if idx == -1 or idx == 9:
            config.save()
            break
            
        elif idx == 0:
            prov_opts = ["1) Ollama (Local)", "2) OpenAI-compatible API", "3) Claude Native API"]
            sub = interactive_menu("Select Backend Provider", prov_opts, ui, current_index=0, lang=lang)
            if sub != -1:
                config.data["provider"] = ["ollama", "openai", "claude"][sub]
                config.data["endpoint"] = DEFAULT_ENDPOINTS[config.provider]
                
        elif idx == 1:
            ui.clear()
            url = prompt_text("Enter API Endpoint URL", default=config.endpoint, ui=ui)
            config.data["endpoint"] = url.rstrip("/")
            
        elif idx == 2:
            ui.clear()
            key = prompt_secret("Enter API Key (Masked Input)", ui=ui)
            config.data["api_key"] = key
            
        elif idx == 3:
            ui.clear()
            model = fetch_model_interactively(config.provider, config.endpoint, config.api_key, ui)
            if not model:
                model = prompt_text("Enter Model Name", default=config.model, ui=ui)
            config.data["model"] = model
            
        elif idx == 4:
            ui.clear()
            while True:
                path_raw = prompt_text("Enter Workspace Sandbox Path", default=config.workspace, ui=ui)
                ok, result = _validate_workspace_path(path_raw, ui)
                if ok:
                    config.set_workspace(result)
                    break
                ui.error_box("INVALID PATH", result)
                
        elif idx == 5:
            ui.clear()
            while True:
                max_iter_str = prompt_text("Enter Maximum Tool Iterations Limit", default=str(config.data.get("max_iterations", 100)), ui=ui)
                if max_iter_str.isdigit() and int(max_iter_str) > 0:
                    config.data["max_iterations"] = int(max_iter_str)
                    break
                ui.error_box("INVALID LIMIT", "Please enter a positive integer.")
                
        elif idx == 6:
            # Submenu to toggle granular permissions matrix
            while True:
                matrix = config.permissions
                perm_items = []
                perm_keys = list(matrix.keys())
                for pk in perm_keys:
                    status = "AutoConfirm" if matrix[pk] == "auto" else "Prompt Ask"
                    perm_items.append(f"{pk}: [{status}]")
                perm_items.append("Save & Go Back")
                
                sub_p = interactive_menu("Permissions Config Matrix", perm_items, ui, current_index=0, lang=lang)
                if sub_p == -1 or sub_p == len(perm_keys):
                    break
                target_key = perm_keys[sub_p]
                matrix[target_key] = "auto" if matrix[target_key] == "ask" else "ask"
                config.data["permissions"] = matrix
                
        elif idx == 7:
            langs = ["1) English", "2) 繁體中文", "3) 日本語"]
            sub_l = interactive_menu("Select Display Language", langs, ui, current_index=0, lang=lang)
            if sub_l != -1:
                config.lang = ["en", "zh", "ja"][sub_l]
                lang = config.lang
                
        elif idx == 8:
            themes = ["1) Black (Default)", "2) Gray (Soft Contrast)", "3) White (Bright Contrast)"]
            sub_t = interactive_menu("Select Theme Style", themes, ui, current_index=0, lang=lang)
            if sub_t != -1:
                config.theme = ["black", "gray", "white"][sub_t]
                apply_theme_palette(config.theme)


# --- Setup wizard for first launch ---

def run_setup_menu_initial(config: NXClawConfig, ui: NXClawUI):
    ui.clear()
    ui.banner()
    ui.hr(color=ui.GREEN)
    print(ui.c("  INITIAL SETUP SYSTEM", ui.BOLD + ui.BRIGHT_GREEN))
    ui.hr(color=ui.GREEN)
    print()

    print(ui.c("  Select your AI Backend provider:", ui.WHITE))
    print(ui.c("    1) Ollama (Local open-source models)", ui.CYAN))
    print(ui.c("    2) OpenAI-compatible API (DeepSeek, OpenRouter, etc.)", ui.CYAN))
    print(ui.c("    3) Claude-compatible API (Anthropic Official Endpoints)", ui.CYAN))
    print()
    choice = prompt_choice("  Backend Choice", ["1", "2", "3"], ui, default="1")
    provider = PROVIDER_NAMES[choice]
    config.data["provider"] = provider

    print()
    print(ui.c(f"  >> Setting up: {PROVIDER_LABELS[provider]}", ui.BRIGHT_CYAN))

    default_endpoint = DEFAULT_ENDPOINTS[provider]
    endpoint = prompt_text("  API Endpoint URL", default=default_endpoint, ui=ui)
    config.data["endpoint"] = endpoint.rstrip("/")

    if provider == "ollama":
        print(ui.c("  (Ollama rarely requires an API key; press Enter to skip)", ui.GRAY))
        api_key = prompt_text("  API Key (Optional)", default="", ui=ui, allow_empty=True)
    else:
        api_key = prompt_secret("  API Key (Masked Input)", ui=ui)
        if not api_key:
            print(ui.c("  [!] Warning: Missing API key, subsequent API requests might fail.", ui.YELLOW))
    config.data["api_key"] = api_key

    print()
    print(ui.c("  Choose model selection method:", ui.WHITE))
    print(ui.c("    1) Manually enter model identifier", ui.CYAN))
    print(ui.c("    2) Auto-discover active models from Endpoint", ui.CYAN))
    model_choice = prompt_choice("  Selection method", ["1", "2"], ui, default="2")

    model = None
    if model_choice == "2":
        model = fetch_model_interactively(provider, endpoint, api_key, ui)

    if not model:
        default_model_hint = {
            "ollama": "qwen2.5-coder:7b",
            "openai": "gpt-4o",
            "claude": "claude-3-5-sonnet-latest",
        }[provider]
        print()
        print(ui.c("  WARNING: The chosen model MUST support structured tool calling (function calling).", ui.YELLOW))
        print(ui.c("           If it does not, the agent may run endlessly or only reply in plain text.", ui.YELLOW))
        print()
        model = prompt_text("  Model ID name", default=default_model_hint, ui=ui)

    config.data["model"] = model

    print()
    workspace_default = config.workspace or os.path.join(os.path.expanduser("~"), "NXClaw")
    while True:
        workspace_raw = prompt_text("  Workspace Sandbox Path", default=workspace_default, ui=ui)
        ok, result = _validate_workspace_path(workspace_raw, ui)
        if ok:
            workspace = result
            break
        ui.error_box("INVALID PATH", result)

    config.data["max_iterations"] = 100
    config.data["permissions"] = dict(DEFAULT_PERMISSIONS)
    config.data["lang"] = "en"
    config.data["theme"] = "black"
    config.save()


def fetch_model_interactively(provider, endpoint, api_key, ui):
    print(ui.c("  [*] Connecting to list remote models...", ui.GRAY))
    try:
        client = NXClawAPIClient(provider, endpoint, api_key, model="")
        with Spinner("Fetching active models", color=ui.CYAN):
            call = InterruptibleCall(client.list_models)
            models = call.run()
    except TaskCancelled:
        ui.box("CANCELLED", "Model fetching interrupted. Defaulting to manual naming.", color=ui.YELLOW)
        return None
    except APIError as e:
        ui.error_box(
            "DISCOVERY FAILED",
            f"{e}\n\n"
            "Double check Endpoint status and verification tokens."
        )
        return None
    except Exception as e:
        ui.error_box(
            "DISCOVERY FAILED",
            f"Error: {type(e).__name__}: {e}\n\nSwitching to manual selection."
        )
        return None

    if not models:
        ui.error_box("EMPTY RESPONSE", "No active models were returned. Defaulting to manual input.")
        return None

    print()
    print(ui.c(f"  Discovered {len(models)} model targets:", ui.BRIGHT_GREEN))
    for i, m in enumerate(models, 1):
        print(ui.c(f"    {i}) {m}", ui.CYAN))
    print()
    print(ui.c("  WARNING: The chosen model MUST support structured tool calling (function calling).", ui.YELLOW))
    print(ui.c("           If it does not, the agent may run endlessly or only reply in plain text.", ui.YELLOW))
    print()

    valid = [str(i) for i in range(1, len(models) + 1)]
    choice = prompt_choice("  Enter index to select model (or Enter to bypass)", valid + [""], ui, default="")
    if choice == "" or choice not in valid:
        return None
    return models[int(choice) - 1]


# --------------------------------------------------------------------------
# Interactive Academy Course Room
# --------------------------------------------------------------------------

def run_academy_tutorial(config: NXClawConfig, ui: NXClawUI):
    lang = config.lang
    text_data = ACADEMY_TEXTS.get(lang, ACADEMY_TEXTS["en"])
    
    options = [
        "1. Skill_01: The '@' Context Marker",
        "2. Skill_02: Unified Color Diffs",
        "3. Skill_03: Granular Permission Matrix",
        "4. Skill_04: Desktop OS Automation",
        "5. Skill_05: Native Search Engine",
        "6. Exit Academy"
    ]
    
    while True:
        idx = interactive_menu(text_data["title"], options, ui, current_index=0, lang=lang)
        if idx == -1 or idx == 5:
            break
            
        ui.clear()
        card_key = f"card{idx + 1}"
        ui.info_box(f"Skill Card {idx + 1}", text_data[card_key])
        
        # Press Enter to return to main Academy room
        print(ui.c("\n  Press Enter to continue...", ui.GRAY))
        try: input()
        except (EOFError, KeyboardInterrupt): break


# --------------------------------------------------------------------------
# Main Program Loop
# --------------------------------------------------------------------------

def run_model_selection_command(config: NXClawConfig, agent: NXClawAgent, ui: NXClawUI):
    run_granular_settings(config, ui)
    agent.refresh_client()


def handle_slash_command(cmd, config: NXClawConfig, agent: NXClawAgent, ui: NXClawUI):
    cmd_strip = cmd.strip()
    cmd_lower = cmd_strip.lower()

    if cmd_lower in ("/exit", "/quit"):
        print(ui.c(f"\n  {LOCALES[config.lang]['terminated']}\n", ui.GREEN))
        return False

    elif cmd_lower == "/settings":
        run_granular_settings(config, ui)
        agent.refresh_client()

    elif cmd_lower == "/model":
        run_granular_settings(config, ui)
        agent.refresh_client()

    elif cmd_lower == "/auto-confirm":
        current_state = config.permissions.get("run_command", "ask")
        new_val = "auto" if current_state == "ask" else "ask"
        for k in config.permissions:
            config.permissions[k] = new_val
        config.save()
        color = ui.RED if new_val == "auto" else ui.GREEN
        ui.box("AUTO-CONFIRM MATRIX", f"All permissions updated dynamically to: {new_val}", color=color)

    elif cmd_lower == "/clear":
        agent.clear_history()
        ui.success_box("HISTORY PURGED", "Session memory has been reset to empty context.")

    elif cmd_lower == "/course":
        run_academy_tutorial(config, ui)

    elif cmd_lower == "/ls":
        try:
            files = os.listdir(agent.tools.workspace_root)
            if not files:
                ui.info_box("WORKSPACE", "Workspace directory is empty.")
            else:
                lines = []
                for f in sorted(files):
                    if f == CONFIG_FILENAME:
                        continue
                    full_path = os.path.join(agent.tools.workspace_root, f)
                    if os.path.isdir(full_path):
                        lines.append(ui.c(f + "/", ui.CYAN + ui.BOLD))
                    else:
                        lines.append(ui.c(f, ui.GRAY))
                ui.box("WORKSPACE FILES", "\n".join(lines) if lines else "No public files found.")
        except Exception as e:
            ui.error_box("ERROR", f"Could not list directory: {e}")

    elif cmd_lower.startswith("/rm "):
        target_file = cmd_strip[4:].strip()
        if target_file.startswith('@'):
            target_file = target_file[1:]
        if not target_file:
            ui.error_box("ERROR", "Please specify a path. E.g., /rm script.py")
        else:
            try:
                safe_path = agent.tools._resolve_safe_path(target_file)
                if os.path.exists(safe_path):
                    if os.path.isdir(safe_path):
                        shutil.rmtree(safe_path)
                        ui.success_box("REMOVED", f"Folder '{target_file}' was successfully removed.")
                    else:
                        os.remove(safe_path)
                        ui.success_box("REMOVED", f"File '{target_file}' was successfully removed.")
                else:
                    ui.error_box("NOT FOUND", f"File '{target_file}' does not exist inside the workspace.")
            except Exception as e:
                ui.error_box("ERROR", f"Could not remove target: {e}")

    elif cmd_lower.startswith("/open "):
        file_to_open = cmd_strip[6:].strip()
        if file_to_open.startswith('@'):
            file_to_open = file_to_open[1:]
        if not file_to_open:
            ui.error_box("ERROR", "Provide a file path. E.g., /open main.py")
        else:
            try:
                safe_path = agent.tools._resolve_safe_path(file_to_open)
                if os.path.exists(safe_path):
                    ui.box("OPENING FILE", f"Opening {file_to_open} in the system default text editor...")
                    open_file_in_editor(safe_path)
                else:
                    ui.error_box("NOT FOUND", f"File '{file_to_open}' does not exist inside the workspace sandbox.")
            except Exception as e:
                ui.error_box("ERROR", f"Could not launch file editor: {e}")

    elif cmd_lower == "/update":
        trigger_auto_update(config, ui)

    elif cmd_lower in ("/help", "/?"):
        print_help(ui)

    else:
        ui.error_box("UNKNOWN COMMAND", f"'{cmd_strip}' is not recognized. Type /help for available commands.")

    return True


def prompt_choice(prompt_text_, valid, ui, default=None):
    while True:
        suffix = f" [Enter for {default}]" if default else ""
        try:
            raw = input(ui.c(f"{prompt_text_}{suffix}: ", ui.CYAN)).strip()
        except EOFError:
            print()
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            sys.exit(0)
        if not raw and default is not None:
            return default
        if raw in valid:
            return raw
        print(ui.c(f"  [!] Invalid entry. Options: {', '.join(valid)}", ui.YELLOW))


def prompt_text(prompt_text_, default=None, ui=NXClawUI, allow_empty=False):
    suffix = f" [Enter for {default}]" if default else ""
    while True:
        try:
            raw = input(ui.c(f"{prompt_text_}{suffix}: ", ui.CYAN)).strip()
        except EOFError:
            print()
            sys.exit(1)
        except KeyboardInterrupt:
            print()
            sys.exit(0)

        if raw:
            return raw
        if default is not None:
            return default
        if allow_empty:
            return ""
        print(ui.c("  [!] Field cannot be empty.", ui.YELLOW))


def prompt_secret(prompt_text_, ui=NXClawUI):
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=getpass.GetPassWarning)
            return getpass.getpass(ui.c(f"{prompt_text_}: ", ui.CYAN)).strip()
    except EOFError:
        print()
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except Exception:
        print(ui.c("  [!] Command line masking failed. API key will display visibly.", ui.YELLOW))
        try:
            return input(ui.c(f"{prompt_text_}: ", ui.CYAN)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)


def _validate_workspace_path(raw_path, ui):
    try:
        abs_path = os.path.abspath(os.path.expanduser(raw_path))
    except Exception as e:
        return False, f"Could not parse path format: {e}"

    try:
        os.makedirs(abs_path, exist_ok=True)
    except OSError as e:
        return False, f"Could not create folder '{abs_path}': {e}"

    if not os.path.isdir(abs_path):
        return False, f"'{abs_path}' is not a directory."

    test_file = os.path.join(abs_path, ".nxclaw_write_test.tmp")
    try:
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
    except OSError as e:
        return False, f"Directory lacks write permissions: {e}"

    return True, abs_path


def main():
    NXClawUI.enable_ansi()
    ui = NXClawUI

    ui.banner()
    ui.boot_sequence()

    workspace_guess = os.path.join(os.path.expanduser("~"), "NXClaw")
    config = NXClawConfig(workspace=workspace_guess)

    if config.exists():
        config.load()
        if not config.data.get("workspace"):
            config.data["workspace"] = workspace_guess
        config.set_workspace(config.data.get("workspace", workspace_guess))
        if config.exists():
            config.load()
        
        apply_theme_palette(config.theme)
        
        ui.success_box(
            "CONFIGURATION RETRIEVED",
            f"Provider:  {PROVIDER_LABELS.get(config.provider, config.provider)}\n"
            f"Model:     {config.model}\n"
            f"Workspace: {config.workspace}",
        )
    else:
        config.data["workspace"] = workspace_guess
        run_setup_menu_initial(config, ui)
        config.data["workspace"] = config.workspace
        config.save()
        apply_theme_palette("black")

    # Dynamic startup remote version check warning
    remote_ver = get_remote_version()
    if remote_ver and remote_ver != VERSION:
        ui.error_box(
            "NEW UPDATE AVAILABLE",
            f"A newer version of NXClaw has been found: v{remote_ver} (Current: v{VERSION})\n"
            "Please run the '/update' command to synchronize your files immediately."
        )

    # Automatically guide users through the tutorial on first launch
    if not config.tutorial_completed:
        run_academy_tutorial(config, ui)
        config.data["tutorial_completed"] = True
        config.save()

    agent = NXClawAgent(config, ui)

    print()
    ui.hr(color=ui.GREEN)
    print(ui.c(LOCALES[config.lang]["prompt_task"], ui.GRAY))
    ui.hr(color=ui.GREEN)
    print()

    def sigint_handler(signum, frame):
        print(ui.c("\n\n  [!] Interrupted. Type /exit to close, or continue inputting.\n", ui.YELLOW))

    signal.signal(signal.SIGINT, sigint_handler)

    while True:
        print()
        # Setup active status bar on session iterations
        auto = "ON" if config.permissions.get("run_command", "ask") == "auto" else "OFF"
        auto_color = ui.RED if auto == "ON" else ui.GRAY
        line = (
            f"{ui.c('[NXClaw]', ui.BRIGHT_GREEN)} "
            f"{ui.c('[' + LOCALES[config.lang]['status_model'] + ': ' + (config.model or 'None') + ']', ui.CYAN)} "
            f"{ui.c('[' + LOCALES[config.lang]['status_sandbox'] + ': ' + config.workspace + ']', ui.GRAY)} "
            f"{ui.c('[' + LOCALES[config.lang]['status_confirm'] + ': ' + auto + ']', auto_color)}"
        )
        print(line)
        try:
            user_input = input(ui.c("> ", ui.BRIGHT_GREEN + ui.BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            print(ui.c(f"\n  {LOCALES[config.lang]['terminated']}\n", ui.GREEN))
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            should_continue = handle_slash_command(user_input, config, agent, ui)
            if not should_continue:
                break
            continue

        processed_input = process_file_attachments(user_input, agent.tools)

        try:
            agent.run_task(processed_input)
        except KeyboardInterrupt:
            print(ui.c(f"\n  {LOCALES[config.lang]['cancelled']}\n", ui.YELLOW))
        except Exception as e:
            ui.error_box("AGENT TERMINATION EXCEPTION", f"{e}\n{traceback.format_exc(limit=3)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  [NXClaw] Session terminated. Goodbye.\n")
        sys.exit(0)
