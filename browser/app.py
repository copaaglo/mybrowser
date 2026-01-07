from __future__ import annotations
import tkinter as tk
from dataclasses import dataclass

from browser.tab import Tab

HOME_URL = "https://example.com"


@dataclass
class Viewport:
    width: int
    height: int


class BrowserApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Cowser")
        self.root.geometry("1024x720")

        # Color Palette
        self.bg_color = "#E1F5FE"  # Light Baby Blue
        self.accent_color = "#B3E5FC"
        self.text_color = "#01579B"

        self.root.configure(bg=self.bg_color)

        # ===== Top UI =====
        top = tk.Frame(self.root, bg=self.bg_color)
        top.pack(fill="x")

        # Tab bar
        self.tabbar = tk.Frame(top, bg=self.bg_color)
        self.tabbar.pack(fill="x", padx=6, pady=(6, 0))

        # Controls row
        controls = tk.Frame(top, bg=self.bg_color)
        controls.pack(fill="x", padx=6, pady=6)

        self.btn_back = tk.Button(controls, text="←", width=3, command=self.go_back, bg=self.accent_color, fg=self.text_color, relief="flat")
        self.btn_fwd = tk.Button(controls, text="→", width=3, command=self.go_forward, bg=self.accent_color, fg=self.text_color, relief="flat")
        self.btn_reload = tk.Button(controls, text="⟳", width=3, command=self.reload, bg=self.accent_color, fg=self.text_color, relief="flat")
        self.btn_home = tk.Button(controls, text="⌂", width=3, command=self.home, bg=self.accent_color, fg=self.text_color, relief="flat")

        self.btn_back.pack(side="left")
        self.btn_fwd.pack(side="left", padx=(4, 0))
        self.btn_reload.pack(side="left", padx=(4, 0))
        self.btn_home.pack(side="left", padx=(4, 10))

        self.address_var = tk.StringVar(value=HOME_URL)
        self.address = tk.Entry(controls, textvariable=self.address_var, font=("Segoe UI", 12), bg="white", fg=self.text_color, relief="flat", highlightthickness=1, highlightbackground=self.accent_color)
        self.address.pack(side="left", fill="x", expand=True)
        self.address.bind("<Return>", self.on_enter)

        self.status_var = tk.StringVar(value="")
        self.status = tk.Label(self.root, textvariable=self.status_var, anchor="w", bg=self.bg_color, fg=self.text_color, font=("Segoe UI", 9))
        self.status.pack(fill="x")

        # ===== Canvas =====
        self.viewport = Viewport(width=1024, height=640)
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Tabs
        self.tabs: list[Tab] = []
        self.active_index: int = -1

        # Input
        self.root.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-1>", self.on_click)

        # Shortcuts
        self.root.bind("<Control-l>", lambda e: self.focus_address())
        self.root.bind("<Control-r>", lambda e: self.reload())
        self.root.bind("<Control-t>", lambda e: self.new_tab(HOME_URL))
        self.root.bind("<Control-w>", lambda e: self.close_tab(self.active_index))
        self.root.bind("<Alt-Left>", lambda e: self.go_back())
        self.root.bind("<Alt-Right>", lambda e: self.go_forward())

        self.new_tab(HOME_URL)

    def run(self) -> None:
        self.tick()
        self.root.mainloop()

    # ---- UI Actions ----
    def focus_address(self) -> None:
        self.address.focus_set()
        self.address.selection_range(0, tk.END)

    def on_enter(self, event=None) -> None:
        url = self.address_var.get().strip()
        if not url:
            return
        if "://" not in url:
            url = "https://" + url
        self.active_tab().load(url)
        self.address_var.set(self.active_tab().current_url_str())

    def on_wheel(self, event) -> None:
        self.active_tab().scroll_by(-int(event.delta) // 3)

    def on_click(self, event) -> None:
        self.active_tab().click(int(event.x), int(event.y))
        self.address_var.set(self.active_tab().current_url_str())

    def go_back(self) -> None:
        self.active_tab().go_back()
        self.address_var.set(self.active_tab().current_url_str())

    def go_forward(self) -> None:
        self.active_tab().go_forward()
        self.address_var.set(self.active_tab().current_url_str())

    def reload(self) -> None:
        self.active_tab().reload()
        self.address_var.set(self.active_tab().current_url_str())

    def home(self) -> None:
        self.active_tab().load(HOME_URL)
        self.address_var.set(self.active_tab().current_url_str())

    # ---- Tabs ----
    def new_tab(self, url: str) -> None:
        t = Tab(self.viewport)
        t.load(url)
        self.tabs.append(t)
        self.active_index = len(self.tabs) - 1
        self.render_tabbar()
        self.address_var.set(t.current_url_str())

    def close_tab(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.tabs):
            return
        del self.tabs[idx]
        if not self.tabs:
            self.new_tab(HOME_URL)
            return
        self.active_index = max(0, min(self.active_index, len(self.tabs) - 1))
        self.render_tabbar()
        self.address_var.set(self.active_tab().current_url_str())

    def switch_tab(self, idx: int) -> None:
        if 0 <= idx < len(self.tabs):
            self.active_index = idx
            self.render_tabbar()
            self.address_var.set(self.active_tab().current_url_str())

    def render_tabbar(self) -> None:
        for w in self.tabbar.winfo_children():
            w.destroy()

        for i, t in enumerate(self.tabs):
            is_active = (i == self.active_index)
            txt = (t.title[:18] + "…") if len(t.title) > 19 else t.title
            
            tab_frame = tk.Frame(self.tabbar, bg=self.accent_color if is_active else self.bg_color)
            tab_frame.pack(side="left", padx=2)

            btn = tk.Button(
                tab_frame,
                text=txt,
                relief="flat",
                bg=self.accent_color if is_active else self.bg_color,
                fg=self.text_color,
                font=("Segoe UI", 10, "bold" if is_active else "normal"),
                command=lambda j=i: self.switch_tab(j),
                padx=8,
            )
            btn.pack(side="left")

            xbtn = tk.Button(
                tab_frame, 
                text="×", 
                command=lambda j=i: self.close_tab(j), 
                padx=6,
                relief="flat",
                bg=self.accent_color if is_active else self.bg_color,
                fg=self.text_color,
                font=("Segoe UI", 10)
            )
            xbtn.pack(side="left")

        plus = tk.Button(
            self.tabbar, 
            text="+", 
            command=lambda: self.new_tab(HOME_URL), 
            padx=10,
            relief="flat",
            bg=self.bg_color,
            fg=self.text_color,
            font=("Segoe UI", 12, "bold")
        )
        plus.pack(side="right")

    def active_tab(self) -> Tab:
        return self.tabs[self.active_index]

    # ---- Main loop ----
    def tick(self) -> None:
        self.canvas.delete("all")
        tab = self.active_tab()
        tab.render(self.canvas)

        # Update status + buttons
        self.status_var.set(tab.current_url_str())
        self.btn_back.config(state="normal" if tab.can_go_back() else "disabled")
        self.btn_fwd.config(state="normal" if tab.can_go_forward() else "disabled")

        self.root.after(16, self.tick)
