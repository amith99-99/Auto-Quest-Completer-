import sys
import time
import json
import random
import re
import base64
from datetime import datetime, timezone
 
import requests
 
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QScrollArea,
    QCheckBox, QFrame, QSizePolicy, QProgressBar,
)
 
API_BASE           = "https://discord.com/api/v9"
HEARTBEAT_INTERVAL = 20
 
SUPPORTED_TASKS = [
    "WATCH_VIDEO", "PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP",
    "PLAY_ACTIVITY", "WATCH_VIDEO_ON_MOBILE",
]
 
TASK_LABELS = {
    "WATCH_VIDEO":           "Watch Video",
    "WATCH_VIDEO_ON_MOBILE": "Watch Video",
    "PLAY_ON_DESKTOP":       "Play Game",
    "STREAM_ON_DESKTOP":     "Stream",
    "PLAY_ACTIVITY":         "Activity",
}
 
TASK_COLORS = {
    "WATCH_VIDEO":           "#e44d7b",
    "WATCH_VIDEO_ON_MOBILE": "#e44d7b",
    "PLAY_ON_DESKTOP":       "#3ba55d",
    "STREAM_ON_DESKTOP":     "#9b59b6",
    "PLAY_ACTIVITY":         "#f0b232",
}
 
C = {
    "bg":       "#0f1012",
    "surface":  "#17181c",
    "panel":    "#1c1e23",
    "card":     "#212329",
    "card_h":   "#272930",
    "border":   "#2a2d35",
    "border_h": "#3a3e4a",
    "accent":   "#5865f2",
    "accent_h": "#4752c4",
    "success":  "#3ba55d",
    "warning":  "#f0b232",
    "error":    "#ed4245",
    "text":     "#d8dadf",
    "subtext":  "#9499a3",
    "muted":    "#6a6f7a",
    "white":    "#ffffff",
}
 
STYLE = f"""
* {{
    font-family: 'Segoe UI', 'SF Pro Text', sans-serif;
    font-size: 13px;
    color: {C['text']};
}}
QMainWindow {{ background: {C['bg']}; }}
QWidget {{ background: transparent; }}
 
QLineEdit {{
    background: {C['panel']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {C['white']};
    font-size: 13px;
}}
QLineEdit:focus {{ border-color: {C['accent']}; background: {C['card']}; }}
 
QPushButton {{
    background: {C['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0 18px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover  {{ background: {C['accent_h']}; }}
QPushButton:pressed {{ background: #3a40aa; }}
QPushButton:disabled {{ background: {C['border']}; color: {C['muted']}; }}
QPushButton#ghost {{
    background: transparent;
    color: {C['subtext']};
    border: 1.5px solid {C['border']};
}}
QPushButton#ghost:hover {{ background: {C['panel']}; color: {C['text']}; border-color: {C['border_h']}; }}
QPushButton#danger {{ background: {C['error']}; }}
QPushButton#danger:hover {{ background: #c93b3e; }}
QPushButton#danger:disabled {{ background: {C['border']}; color: {C['muted']}; }}
 
QTextEdit {{
    background: {C['panel']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 8px 10px;
    color: {C['text']};
    font-family: 'Consolas', monospace;
    font-size: 12px;
}}
 
QScrollBar:vertical {{
    background: transparent; width: 6px;
}}
QScrollBar::handle:vertical {{
    background: {C['border_h']}; border-radius: 3px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
 
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 2px solid {C['border_h']};
    border-radius: 4px;
    background: {C['panel']};
}}
QCheckBox::indicator:checked {{
    background: {C['accent']}; border-color: {C['accent']};
}}
QCheckBox::indicator:hover {{ border-color: {C['accent']}; }}
 
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
 
QProgressBar {{
    background: transparent; border: none;
    border-radius: 0px; height: 4px;
}}
QProgressBar::chunk {{ background: {C['accent']}; border-radius: 0px; }}
"""
 
 
def fetch_latest_build_number() -> int:
    FALLBACK = 504649
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        r = requests.get("https://discord.com/app", headers={"User-Agent": ua}, timeout=15)
        if r.status_code != 200:
            return FALLBACK
        for asset_hash in re.findall(r'/assets/([a-f0-9]+)\.js', r.text)[-5:]:
            try:
                ar = requests.get(f"https://discord.com/assets/{asset_hash}.js",
                                  headers={"User-Agent": ua}, timeout=15)
                m = re.search(r'buildNumber["\s:]+["\s]*(\d{5,7})', ar.text)
                if m:
                    return int(m.group(1))
            except Exception:
                continue
        return FALLBACK
    except Exception:
        return FALLBACK
 
 
def make_super_properties(build_number: int) -> str:
    obj = {
        "os": "Windows", "browser": "Discord Client",
        "release_channel": "stable", "client_version": "1.0.9175",
        "os_version": "10.0.26100", "os_arch": "x64", "app_arch": "x64",
        "system_locale": "en-US",
        "browser_user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 "
            "Electron/32.2.7 Safari/537.36"
        ),
        "browser_version": "32.2.7",
        "client_build_number": build_number,
        "native_build_number": 59498,
        "client_event_source": None,
    }
    return base64.b64encode(json.dumps(obj).encode()).decode()
 
 
def _kget(d, *keys):
    if not d:
        return None
    for k in keys:
        if k in d:
            return d[k]
    return None
 
 
def get_task_config(q):
    return _kget(q.get("config", {}), "taskConfig", "task_config", "taskConfigV2", "task_config_v2")
 
def get_quest_name(q):
    cfg  = q.get("config", {})
    msgs = cfg.get("messages", {})
    for k in ("questName", "quest_name", "gameTitle", "game_title"):
        v = msgs.get(k)
        if v:
            return v.strip()
    app = cfg.get("application", {}).get("name")
    return app or f"Quest#{q.get('id','?')}"
 
def get_expires_at(q):
    return _kget(q.get("config", {}), "expiresAt", "expires_at")
 
def get_user_status(q):
    us = _kget(q, "userStatus", "user_status")
    return us if isinstance(us, dict) else {}
 
def is_completable(q):
    exp = get_expires_at(q)
    if exp:
        try:
            if datetime.fromisoformat(exp.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                return False
        except Exception:
            pass
    tc = get_task_config(q)
    if not tc or "tasks" not in tc:
        return False
    return any(tc["tasks"].get(t) is not None for t in SUPPORTED_TASKS)
 
def is_enrolled(q):
    return bool(_kget(get_user_status(q), "enrolledAt", "enrolled_at"))
 
def is_completed(q):
    return bool(_kget(get_user_status(q), "completedAt", "completed_at"))
 
def get_task_type(q):
    tc = get_task_config(q)
    if not tc or "tasks" not in tc:
        return None
    for t in SUPPORTED_TASKS:
        if tc["tasks"].get(t) is not None:
            return t
    return None
 
def get_seconds_needed(q):
    tc = get_task_config(q)
    tt = get_task_type(q)
    if not tc or not tt:
        return 0
    return tc["tasks"][tt].get("target", 0)
 
def get_seconds_done(q):
    tt = get_task_type(q)
    if not tt:
        return 0
    return (get_user_status(q).get("progress") or {}).get(tt, {}).get("value", 0)
 
def get_enrolled_at(q):
    return _kget(get_user_status(q), "enrolledAt", "enrolled_at")
 
 
class DiscordAPI:
    def __init__(self, token, build_number):
        self.token   = token
        self.session = requests.Session()
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 "
            "Electron/32.2.7 Safari/537.36"
        )
        self.session.headers.update({
            "Authorization":      token,
            "Content-Type":       "application/json",
            "User-Agent":         ua,
            "X-Super-Properties": make_super_properties(build_number),
            "X-Discord-Locale":   "en-US",
            "X-Discord-Timezone": "Asia/Ho_Chi_Minh",
            "Origin":             "https://discord.com",
            "Referer":            "https://discord.com/channels/@me",
        })
 
    def get(self, path):
        return self.session.get(f"{API_BASE}{path}")
 
    def post(self, path, payload=None):
        return self.session.post(f"{API_BASE}{path}", json=payload)
 
    def validate_token(self):
        try:
            r = self.get("/users/@me")
            return (True, r.json()) if r.status_code == 200 else (False, None)
        except Exception:
            return False, None
 
    def fetch_quests(self):
        try:
            r = self.get("/quests/@me")
            if r.status_code == 200:
                data = r.json()
                return data.get("quests", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            return []
        except Exception:
            return []
 
    def enroll_quest(self, quest):
        qid = quest["id"]
        for _ in range(3):
            try:
                r = self.post(f"/quests/{qid}/enroll", {
                    "location": 11, "is_targeted": False,
                    "metadata_raw": None, "metadata_sealed": None,
                    "traffic_metadata_raw":    quest.get("traffic_metadata_raw"),
                    "traffic_metadata_sealed": quest.get("traffic_metadata_sealed"),
                })
                if r.status_code == 429:
                    time.sleep(r.json().get("retry_after", 5) + 1)
                    continue
                return r.status_code in (200, 201, 204)
            except Exception:
                return False
        return False
 
 
class LoginWorker(QThread):
    result   = pyqtSignal(bool, object, int)
    progress = pyqtSignal(str)
 
    def __init__(self, token):
        super().__init__()
        self.token = token
 
    def run(self):
        self.progress.emit("Fetching build number...")
        bn = fetch_latest_build_number()
        self.progress.emit(f"Build: {bn}")
        api = DiscordAPI(self.token, bn)
        self.progress.emit("Validating token...")
        ok, user = api.validate_token()
        self.result.emit(ok, user, bn)
 
 
class FetchQuestsWorker(QThread):
    result = pyqtSignal(list)
 
    def __init__(self, api):
        super().__init__()
        self.api = api
 
    def run(self):
        self.result.emit(self.api.fetch_quests())
 
 
class QuestWorker(QThread):
    log_sig      = pyqtSignal(str, str)
    progress_sig = pyqtSignal(str, float, float)
    done_sig     = pyqtSignal(str)
    stopped_sig  = pyqtSignal()
 
    def __init__(self, api, quests):
        super().__init__()
        self.api    = api
        self.quests = quests
        self._stop  = False
        self._mx    = QMutex()
 
    def stop(self):
        self._mx.lock(); self._stop = True; self._mx.unlock()
 
    def is_stopped(self):
        self._mx.lock(); v = self._stop; self._mx.unlock(); return v
 
    def run(self):
        for quest in self.quests:
            if self.is_stopped():
                break
            name = get_quest_name(quest)
            qid  = quest.get("id")
 
            if not is_enrolled(quest):
                self.log_sig.emit(f"Enrolling: {name}", "info")
                if not self.api.enroll_quest(quest):
                    self.log_sig.emit(f"Failed to enroll: {name}", "error")
                    continue
                time.sleep(2)
                updated = self.api.fetch_quests()
                quest = next((q for q in updated if q.get("id") == qid), quest)
 
            tt = get_task_type(quest)
            if not tt:
                continue
            self.log_sig.emit(f"Starting: {name}", "info")
 
            if tt in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"):
                self._video(quest)
            elif tt in ("PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP"):
                self._heartbeat(quest)
            elif tt == "PLAY_ACTIVITY":
                self._activity(quest)
 
            if not self.is_stopped():
                self.done_sig.emit(qid)
        self.stopped_sig.emit()
 
    def _video(self, quest):
        name   = get_quest_name(quest)
        qid    = quest["id"]
        needed = get_seconds_needed(quest)
        done   = get_seconds_done(quest)
        ea     = get_enrolled_at(quest)
        enr_ts = datetime.fromisoformat(ea.replace("Z", "+00:00")).timestamp() if ea else time.time()
        speed  = 7
 
        while done < needed and not self.is_stopped():
            if (time.time() - enr_ts) + 10 - done >= speed:
                try:
                    r = self.api.post(f"/quests/{qid}/video-progress",
                                      {"timestamp": min(needed, done + speed + random.random())})
                    if r.status_code == 200:
                        body = r.json()
                        if body.get("completed_at"):
                            self.progress_sig.emit(qid, needed, needed)
                            self.log_sig.emit(f"Completed: {name}", "ok")
                            return
                        done = min(needed, done + speed)
                        self.progress_sig.emit(qid, done, needed)
                    elif r.status_code == 429:
                        time.sleep(r.json().get("retry_after", 5) + 1)
                        continue
                except Exception as e:
                    self.log_sig.emit(f"Error: {e}", "error")
            if done + speed >= needed:
                break
            time.sleep(1)
 
        try:
            self.api.post(f"/quests/{qid}/video-progress", {"timestamp": needed})
        except Exception:
            pass
        self.progress_sig.emit(qid, needed, needed)
        self.log_sig.emit(f"Completed: {name}", "ok")
 
    def _heartbeat(self, quest):
        name   = get_quest_name(quest)
        qid    = quest["id"]
        tt     = get_task_type(quest)
        needed = get_seconds_needed(quest)
        done   = get_seconds_done(quest)
        pid    = random.randint(1000, 30000)
 
        while done < needed and not self.is_stopped():
            try:
                r = self.api.post(f"/quests/{qid}/heartbeat",
                                  {"stream_key": f"call:0:{pid}", "terminal": False})
                if r.status_code == 200:
                    body = r.json()
                    pd = body.get("progress", {})
                    if pd and tt in pd:
                        done = pd[tt].get("value", done)
                    self.progress_sig.emit(qid, done, needed)
                    if body.get("completed_at") or done >= needed:
                        break
                elif r.status_code == 429:
                    time.sleep(r.json().get("retry_after", 10) + 1)
                    continue
            except Exception as e:
                self.log_sig.emit(f"Error: {e}", "error")
            if not self.is_stopped():
                time.sleep(HEARTBEAT_INTERVAL)
 
        try:
            self.api.post(f"/quests/{qid}/heartbeat",
                          {"stream_key": f"call:0:{pid}", "terminal": True})
        except Exception:
            pass
        self.progress_sig.emit(qid, needed, needed)
        self.log_sig.emit(f"Completed: {name}", "ok")
 
    def _activity(self, quest):
        name   = get_quest_name(quest)
        qid    = quest["id"]
        needed = get_seconds_needed(quest)
        done   = get_seconds_done(quest)
        sk     = "call:0:1"
 
        while done < needed and not self.is_stopped():
            try:
                r = self.api.post(f"/quests/{qid}/heartbeat",
                                  {"stream_key": sk, "terminal": False})
                if r.status_code == 200:
                    body = r.json()
                    pd = body.get("progress", {})
                    if pd and "PLAY_ACTIVITY" in pd:
                        done = pd["PLAY_ACTIVITY"].get("value", done)
                    self.progress_sig.emit(qid, done, needed)
                    if body.get("completed_at") or done >= needed:
                        break
                elif r.status_code == 429:
                    time.sleep(r.json().get("retry_after", 10) + 1)
                    continue
            except Exception as e:
                self.log_sig.emit(f"Error: {e}", "error")
            if not self.is_stopped():
                time.sleep(HEARTBEAT_INTERVAL)
 
        try:
            self.api.post(f"/quests/{qid}/heartbeat",
                          {"stream_key": sk, "terminal": True})
        except Exception:
            pass
        self.progress_sig.emit(qid, needed, needed)
        self.log_sig.emit(f"Completed: {name}", "ok")
 
 
class HLine(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {C['border']}; border: none;")
 
 
class VLine(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(1)
        self.setStyleSheet(f"background: {C['border']}; border: none;")
 
 
class QuestCard(QFrame):
    def __init__(self, quest, parent=None):
        super().__init__(parent)
        self.quest = quest
        self.qid   = quest.get("id")
        self._build()
 
    def _build(self):
        self.setFixedHeight(62)
        self._default_style()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 12, 0)
        layout.setSpacing(8)
 
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
 
        info = QVBoxLayout()
        info.setSpacing(3)
        info.setContentsMargins(0, 0, 0, 0)
 
        name = get_quest_name(self.quest)
        self.name_lbl = QLabel(name)
        self.name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.name_lbl.setStyleSheet(f"color: {C['white']}; font-weight: 600;")
        self.name_lbl.setMaximumWidth(360)
        info.addWidget(self.name_lbl)
 
        meta = QHBoxLayout()
        meta.setSpacing(5)
        meta.setContentsMargins(0, 0, 0, 0)
 
        tt   = get_task_type(self.quest)
        tlbl = TASK_LABELS.get(tt, "Unknown")
        tcol = TASK_COLORS.get(tt, C['accent'])
 
        badge = QLabel(tlbl)
        badge.setStyleSheet(f"color: {tcol}; font-size: 10px; font-weight: 700;")
        meta.addWidget(badge)
 
        secs = get_seconds_needed(self.quest)
        if secs:
            dur = QLabel(f"{secs // 60} min")
            dur.setStyleSheet(f"color: {C['muted']}; font-size: 10px;")
            meta.addWidget(dur)
 
        exp = get_expires_at(self.quest)
        if exp:
            try:
                days = (datetime.fromisoformat(exp.replace("Z", "+00:00")) - datetime.now(timezone.utc)).days
                if days >= 0:
                    col = C['error'] if days < 2 else (C['warning'] if days < 5 else C['muted'])
                    el  = QLabel(f"· {days}d left")
                    el.setStyleSheet(f"color: {col}; font-size: 10px;")
                    meta.addWidget(el)
            except Exception:
                pass
 
        meta.addStretch()
        info.addLayout(meta)
        layout.addLayout(info)
        layout.addStretch()
 
        right = QVBoxLayout()
        right.setSpacing(4)
        right.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        right.setContentsMargins(0, 0, 0, 0)
 
        self.status_lbl = QLabel("Pending")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 10px;")
        right.addWidget(self.status_lbl)
 
        self.pbar = QProgressBar()
        self.pbar.setFixedWidth(96)
        self.pbar.setFixedHeight(4)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self.pbar.setTextVisible(False)
        right.addWidget(self.pbar)
 
        layout.addLayout(right)
 
    def _default_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['card']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                background: {C['card_h']};
                border-color: {C['border_h']};
            }}
        """)
 
    def set_running(self):
        self.status_lbl.setText("Running...")
        self.status_lbl.setStyleSheet(f"color: {C['warning']}; font-size: 10px;")
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['card']};
                border: 1.5px solid {C['warning']}88;
                border-radius: 8px;
            }}
        """)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ background: transparent; border: none; border-radius: 0px; }}
            QProgressBar::chunk {{ background: {C['warning']}; border-radius: 0px; }}
        """)
 
    def set_done(self):
        self.status_lbl.setText("Completed")
        self.status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 10px;")
        self.pbar.setValue(100)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['card']};
                border: 1.5px solid {C['success']}66;
                border-radius: 8px;
            }}
        """)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ background: transparent; border: none; border-radius: 0px; }}
            QProgressBar::chunk {{ background: {C['success']}; border-radius: 0px; }}
        """)
        self.checkbox.setChecked(False)
        self.checkbox.setEnabled(False)
 
    def update_progress(self, done, total):
        if total > 0:
            self.pbar.setValue(int(done / total * 100))
            self.status_lbl.setText(f"{int(done)}/{int(total)}s")
 
 
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api         = None
        self.worker      = None
        self.quest_cards = {}
        self.all_quests  = []
 
        self.setWindowTitle("Discord Quest Completer")
        self.setMinimumSize(860, 680)
        self.resize(900, 720)
        self.setStyleSheet(STYLE)
 
        root_w = QWidget()
        root_w.setStyleSheet(f"background: {C['bg']};")
        self.setCentralWidget(root_w)
 
        vbox = QVBoxLayout(root_w)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
 
        vbox.addWidget(self._titlebar())
        vbox.addWidget(HLine())
 
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
 
        body.addWidget(self._left_panel())
        body.addWidget(VLine())
        body.addWidget(self._right_panel(), 1)
 
        body_w = QWidget()
        body_w.setStyleSheet(f"background: {C['bg']};")
        body_w.setLayout(body)
        vbox.addWidget(body_w, 1)
 
        vbox.addWidget(HLine())
        vbox.addWidget(self._statusbar())
 
    def _titlebar(self):
        bar = QWidget()
        bar.setFixedHeight(54)
        bar.setStyleSheet(f"background: {C['surface']};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(0)
 
        title = QLabel("Discord Quest Completer")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C['white']};")
        h.addWidget(title)
        h.addStretch()
 
        self.user_pill = QLabel("Not connected")
        self.user_pill.setFixedHeight(28)
        self.user_pill.setStyleSheet(f"""
            color: {C['muted']}; font-size: 12px;
            background: {C['panel']}; border: 1px solid {C['border']};
            border-radius: 14px; padding: 0 12px;
        """)
        h.addWidget(self.user_pill)
        return bar
 
    def _left_panel(self):
        panel = QWidget()
        panel.setFixedWidth(256)
        panel.setStyleSheet(f"background: {C['surface']};")
 
        v = QVBoxLayout(panel)
        v.setContentsMargins(16, 18, 16, 18)
        v.setSpacing(10)
 
        def section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {C['muted']}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
            return lbl
 
        v.addWidget(section_label("TOKEN"))
 
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your token here...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setFixedHeight(38)
        v.addWidget(self.token_input)
 
        btns = QHBoxLayout()
        btns.setSpacing(8)
 
        self.show_btn = QPushButton("Show")
        self.show_btn.setObjectName("ghost")
        self.show_btn.setFixedHeight(34)
        self.show_btn.clicked.connect(self._toggle_token)
        btns.addWidget(self.show_btn)
 
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedHeight(34)
        self.connect_btn.clicked.connect(self._on_connect)
        btns.addWidget(self.connect_btn)
        v.addLayout(btns)
 
        v.addSpacing(6)
        v.addWidget(HLine())
        v.addSpacing(6)
 
        v.addWidget(section_label("STATISTICS"))
        v.addSpacing(2)
 
        def stat(label):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['subtext']}; font-size: 12px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {C['white']}; font-size: 12px; font-weight: 600;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            return row, val
 
        self._s_total = stat("Total quests")
        self._s_avail = stat("Available")
        self._s_done  = stat("Completed")
 
        for row, _ in (self._s_total, self._s_avail, self._s_done):
            v.addLayout(row)
 
        v.addStretch()
        v.addWidget(HLine())
        v.addSpacing(6)
 
        v.addWidget(section_label("SELECTION"))
        v.addSpacing(4)
 
        sel_row = QHBoxLayout()
        sel_row.setSpacing(6)
 
        self.sel_all_btn = QPushButton("Select All")
        self.sel_all_btn.setObjectName("ghost")
        self.sel_all_btn.setFixedHeight(32)
        self.sel_all_btn.clicked.connect(self._select_all)
        sel_row.addWidget(self.sel_all_btn)
 
        self.desel_btn = QPushButton("Clear")
        self.desel_btn.setObjectName("ghost")
        self.desel_btn.setFixedHeight(32)
        self.desel_btn.clicked.connect(self._deselect_all)
        sel_row.addWidget(self.desel_btn)
        v.addLayout(sel_row)
 
        self.refresh_btn = QPushButton("Refresh Quests")
        self.refresh_btn.setObjectName("ghost")
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.clicked.connect(self._on_refresh)
        v.addWidget(self.refresh_btn)
 
        return panel
 
    def _right_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"background: {C['bg']};")
 
        v = QVBoxLayout(panel)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)
 
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        self.quest_hdr_lbl = QLabel("QUESTS")
        self.quest_hdr_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
        hdr.addWidget(self.quest_hdr_lbl)
        hdr.addStretch()
        v.addLayout(hdr)
 
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
 
        self.quest_container = QWidget()
        self.quest_container.setStyleSheet("background: transparent;")
        self.quest_layout = QVBoxLayout(self.quest_container)
        self.quest_layout.setSpacing(5)
        self.quest_layout.setContentsMargins(0, 0, 6, 0)
 
        self.empty_lbl = QLabel("Connect and refresh to load quests.")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 13px; padding: 40px;")
        self.quest_layout.addWidget(self.empty_lbl)
        self.quest_layout.addStretch()
 
        scroll.setWidget(self.quest_container)
        v.addWidget(scroll, 1)
 
        v.addWidget(HLine())
 
        log_hdr = QHBoxLayout()
        log_hdr.setContentsMargins(0, 0, 0, 0)
        log_lbl = QLabel("LOG")
        log_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
        log_hdr.addWidget(log_lbl)
        log_hdr.addStretch()
        v.addLayout(log_hdr)
 
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(150)
        v.addWidget(self.log_output)
 
        return panel
 
    def _statusbar(self):
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setStyleSheet(f"background: {C['surface']};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(10)
 
        self.status_dot  = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {C['muted']}; font-size: 9px;")
        h.addWidget(self.status_dot)
 
        self.status_text = QLabel("Idle")
        self.status_text.setStyleSheet(f"color: {C['muted']}; font-size: 12px;")
        h.addWidget(self.status_text)
        h.addStretch()
 
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setObjectName("ghost")
        self.clear_btn.setFixedSize(88, 36)
        self.clear_btn.clicked.connect(self.log_output.clear)
        h.addWidget(self.clear_btn)
 
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setFixedSize(72, 36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        h.addWidget(self.stop_btn)
 
        self.start_btn = QPushButton("Run Selected")
        self.start_btn.setFixedSize(114, 36)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start)
        h.addWidget(self.start_btn)
 
        return bar
 
    def _toggle_token(self):
        hidden = self.token_input.echoMode() == QLineEdit.EchoMode.Password
        self.token_input.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password
        )
        self.show_btn.setText("Hide" if hidden else "Show")
 
    def _set_status(self, text, color=None):
        c = color or C['muted']
        self.status_dot.setStyleSheet(f"color: {c}; font-size: 9px;")
        self.status_text.setStyleSheet(f"color: {c}; font-size: 12px;")
        self.status_text.setText(text)
 
    def _log(self, msg, level="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        col = {"ok": C['success'], "error": C['error'], "warn": C['warning']}.get(level, C['text'])
        self.log_output.append(
            f'<span style="color:{C["muted"]};font-size:11px">{ts}</span>&nbsp;'
            f'<span style="color:{col}">{msg}</span>'
        )
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)
 
    def _on_connect(self):
        token = self.token_input.text().strip()
        if not token:
            self._log("Token is empty.", "error")
            return
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        self._set_status("Connecting...", C['warning'])
        self._lw = LoginWorker(token)
        self._lw.progress.connect(lambda m: self._log(m))
        self._lw.result.connect(self._on_login_result)
        self._lw.start()
 
    def _on_login_result(self, ok, user, build_number):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        if ok and user:
            uname = user.get("username", "?")
            uid   = user.get("id", "")
            self._log(f"Logged in as {uname} ({uid})", "ok")
            self.user_pill.setText(f"  {uname}  ")
            self.user_pill.setStyleSheet(f"""
                color: {C['success']}; font-size: 12px; font-weight: 600;
                background: {C['success']}15; border: 1px solid {C['success']}40;
                border-radius: 14px; padding: 0 12px;
            """)
            self._set_status("Connected", C['success'])
            self.api = DiscordAPI(self.token_input.text().strip(), build_number)
            self._on_refresh()
        else:
            self._log("Invalid token or connection failed.", "error")
            self._set_status("Connection failed", C['error'])
 
    def _on_refresh(self):
        if not self.api:
            self._log("Not connected.", "warn")
            return
        self.refresh_btn.setEnabled(False)
        self._set_status("Loading quests...", C['warning'])
        self._fw = FetchQuestsWorker(self.api)
        self._fw.result.connect(self._on_quests_loaded)
        self._fw.start()
 
    def _on_quests_loaded(self, quests):
        self.refresh_btn.setEnabled(True)
        self.all_quests = quests
        total     = len(quests)
        completed = sum(1 for q in quests if is_completed(q))
        available = [q for q in quests if not is_completed(q) and is_completable(q)]
 
        self._s_total[1].setText(str(total))
        self._s_avail[1].setText(str(len(available)))
        self._s_done[1].setText(str(completed))
 
        self._render_quests(available)
        self._set_status(f"Ready — {len(available)} available", C['success'])
        self.start_btn.setEnabled(bool(available))
 
    def _render_quests(self, quests):
        while self.quest_layout.count():
            item = self.quest_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.quest_cards.clear()
 
        self.quest_hdr_lbl.setText(f"QUESTS  ·  {len(quests)} available")
 
        if not quests:
            lbl = QLabel("No available quests.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {C['muted']}; font-size: 13px; padding: 40px;")
            self.quest_layout.addWidget(lbl)
            self.quest_layout.addStretch()
            return
 
        for q in quests:
            card = QuestCard(q)
            self.quest_cards[q.get("id")] = card
            self.quest_layout.addWidget(card)
        self.quest_layout.addStretch()
 
    def _select_all(self):
        for c in self.quest_cards.values():
            if c.checkbox.isEnabled():
                c.checkbox.setChecked(True)
 
    def _deselect_all(self):
        for c in self.quest_cards.values():
            c.checkbox.setChecked(False)
 
    def _on_start(self):
        selected = [
            q for q in self.all_quests
            if q.get("id") in self.quest_cards
            and self.quest_cards[q.get("id")].checkbox.isChecked()
            and self.quest_cards[q.get("id")].checkbox.isEnabled()
        ]
        if not selected:
            self._log("No quests selected.", "warn")
            return
        self._log(f"Starting {len(selected)} quest(s)...", "info")
        self._set_status(f"Running {len(selected)} quest(s)...", C['warning'])
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.refresh_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)
        self.worker = QuestWorker(self.api, selected)
        self.worker.log_sig.connect(self._log)
        self.worker.progress_sig.connect(self._on_quest_progress)
        self.worker.done_sig.connect(self._on_quest_done)
        self.worker.stopped_sig.connect(self._on_worker_stopped)
        self.worker.start()
 
    def _on_stop(self):
        if self.worker:
            self.worker.stop()
            self._log("Stopping...", "warn")
            self.stop_btn.setEnabled(False)
 
    def _on_quest_progress(self, qid, done, total):
        card = self.quest_cards.get(qid)
        if card:
            card.set_running()
            card.update_progress(done, total)
 
    def _on_quest_done(self, qid):
        card = self.quest_cards.get(qid)
        if card:
            card.set_done()
 
    def _on_worker_stopped(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)
        self._set_status("All tasks finished", C['success'])
        self._log("Done.", "ok")
 
 
def main():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
 
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
 
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(C['bg']))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(C['text']))
    pal.setColor(QPalette.ColorRole.Base,            QColor(C['card']))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(C['surface']))
    pal.setColor(QPalette.ColorRole.Text,            QColor(C['text']))
    pal.setColor(QPalette.ColorRole.Button,          QColor(C['surface']))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(C['text']))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(C['accent']))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C['white']))
    app.setPalette(pal)
 
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()
