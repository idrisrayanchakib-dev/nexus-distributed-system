import os
import time
import uuid
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional
import customtkinter as ctk

from nexus.network.node import P2PNode
from nexus.ui.components import GroupChatWindow, ManageMessagesWindow
from nexus.ui.theme import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_CARD,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SIDEBAR,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SUB,
)


class MainApp(ctk.CTk):
    """
    Main CustomTkinter Cyberpunk Dark Application for NEXUS P2P.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("NEXUS P2P: Distributed Secure System")
        self.geometry("1120x680")
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=COLOR_BG)

        self.node: Optional[P2PNode] = None
        self.group_windows: Dict[str, GroupChatWindow] = {}
        self.peer_vars: Dict[str, ctk.BooleanVar] = {}
        self.active_poll_data: Optional[Dict[str, Any]] = None
        self.poll_votes: Dict[int, int] = {}
        self.results_shown: bool = False

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_login()

    def on_closing(self) -> None:
        if self.node:
            try:
                self.node.stop()
            except Exception:
                pass
        self.destroy()

    def setup_login(self) -> None:
        self.login_fr = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=15)
        self.login_fr.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self.login_fr,
            text="🚀 NEXUS P2P",
            font=("Roboto Medium", 30),
            text_color=COLOR_PRIMARY,
        ).pack(pady=(30, 8), padx=60)

        ctk.CTkLabel(
            self.login_fr,
            text="Secure Distributed Chat & Consensus",
            font=("Arial", 12),
            text_color=COLOR_TEXT_SUB,
        ).pack(pady=(0, 20))

        self.e_name = ctk.CTkEntry(self.login_fr, placeholder_text="Username", width=260, height=40, border_color=COLOR_ACCENT)
        self.e_name.pack(pady=10)

        self.e_key = ctk.CTkEntry(self.login_fr, placeholder_text="Network Key", show="*", width=260, height=40, border_color=COLOR_ACCENT)
        self.e_key.pack(pady=10)

        self.e_id = ctk.CTkEntry(self.login_fr, placeholder_text="Recovery ID (Optional)", width=260, height=40, border_color=COLOR_ACCENT)
        self.e_id.pack(pady=10)

        ctk.CTkButton(
            self.login_fr,
            text="Connect to Mesh",
            width=260,
            height=45,
            fg_color=COLOR_PRIMARY,
            hover_color="#b294e0",
            text_color="#181825",
            font=("Arial", 14, "bold"),
            command=self.start_app,
        ).pack(pady=30)

    def start_app(self) -> None:
        name = self.e_name.get().strip()
        key = self.e_key.get().strip()
        specific_id = self.e_id.get().strip()

        if not name or not key:
            messagebox.showwarning("Input Required", "Please enter both Username and Network Key.")
            return

        try:
            self.node = P2PNode(name, key, specific_id, self.handle_event, self.log_system)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to initialize P2P Node: {e}")
            return

        self.clipboard_clear()
        self.clipboard_append(self.node.id)
        room_id = self.node.security.get_fingerprint()
        self.title(f"NEXUS | {name} | Room Fingerprint: {room_id} | Port: {self.node.port}")

        self.login_fr.destroy()
        self.setup_dashboard()
        self.refresh_all_chat_displays()
        self.restore_active_poll()
        self.after(1000, self.node.scan_network)

    def setup_dashboard(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Left Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, fg_color=COLOR_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        profile_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        profile_frame.pack(pady=20, padx=10, fill="x")
        ctk.CTkLabel(profile_frame, text="👤", font=("Arial", 28)).pack(side="left")
        ctk.CTkLabel(profile_frame, text=self.node.username, font=("Roboto Medium", 18), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=10)

        ctk.CTkLabel(self.sidebar, text="ONLINE PEERS", font=("Arial", 12, "bold"), text_color=COLOR_TEXT_SUB).pack(pady=(15, 5), padx=15, anchor="w")

        self.peer_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.peer_list_frame.pack(expand=True, fill="both", padx=5, pady=5)

        controls = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=15)

        ctk.CTkButton(controls, text="🔄 Rescan Mesh", fg_color=COLOR_CARD, hover_color="#45475a", command=self.node.scan_network).pack(fill="x", pady=4)
        ctk.CTkButton(controls, text="🔒 Private Room", fg_color=COLOR_PRIMARY, hover_color="#b294e0", text_color="#181825", command=self.create_group_room).pack(fill="x", pady=4)
        ctk.CTkButton(controls, text="📎 Send File", fg_color="#A6E3A1", hover_color="#86c981", text_color="#181825", command=self.pick_and_send_file).pack(fill="x", pady=4)
        ctk.CTkButton(controls, text="📝 My Messages", fg_color=COLOR_ACCENT, hover_color="#6c9af0", text_color="#181825", command=self.open_message_manager).pack(fill="x", pady=4)

        # 2. Middle Chat Stream
        self.chat_fr = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_fr.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(self.chat_fr, text="Global Mesh Channel", font=("Roboto Medium", 20), text_color=COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 10))

        self.chat_display = ctk.CTkTextbox(self.chat_fr, state="disabled", fg_color=COLOR_SIDEBAR, text_color=COLOR_TEXT_MAIN, font=("Consolas", 12), corner_radius=10)
        self.chat_display.pack(expand=True, fill="both", pady=(0, 15))

        inp_bar = ctk.CTkFrame(self.chat_fr, height=60, fg_color="transparent")
        inp_bar.pack(fill="x")

        self.msg_entry = ctk.CTkEntry(inp_bar, placeholder_text="Broadcast encrypted message...", height=50, corner_radius=25, border_width=0, fg_color=COLOR_SIDEBAR, text_color="white")
        self.msg_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.msg_entry.bind("<Return>", self.send_global)

        send_btn = ctk.CTkButton(inp_bar, text="➤", width=50, height=50, corner_radius=25, fg_color=COLOR_ACCENT, hover_color="#6c9af0", command=self.send_global)
        send_btn.pack(side="right")

        # 3. Right Election Center
        self.poll_fr = ctk.CTkFrame(self, width=280, fg_color=COLOR_SIDEBAR, corner_radius=0)
        self.poll_fr.grid(row=0, column=2, sticky="nsew")

        ctk.CTkLabel(self.poll_fr, text="🗳️ ELECTION CENTER", font=("Arial", 14, "bold"), text_color=COLOR_PRIMARY).pack(pady=20)
        self.btn_create_poll = ctk.CTkButton(self.poll_fr, text="+ New Poll", fg_color=COLOR_SUCCESS, hover_color="#86c981", text_color="#181825", command=self.open_poll_dialog)
        self.btn_create_poll.pack(pady=10, padx=20, fill="x")

        self.status_card = ctk.CTkFrame(self.poll_fr, fg_color=COLOR_CARD, corner_radius=10)
        self.status_card.pack(fill="x", padx=15, pady=10)
        self.lbl_timer = ctk.CTkLabel(self.status_card, text="Ready", font=("Arial", 16, "bold"), text_color=COLOR_TEXT_SUB)
        self.lbl_timer.pack(pady=15)

        self.active_poll_ui = ctk.CTkScrollableFrame(self.poll_fr, fg_color="transparent")
        self.active_poll_ui.pack(fill="both", expand=True, padx=5)

    def log_system(self, text: str) -> None:
        self.after(0, lambda: self._log(text))

    def _log(self, text: str) -> None:
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f" >>> [SYSTEM] {text}\n")
        self.chat_display.configure(state="disabled")

    def handle_event(self, t: str, d: Any) -> None:
        self.after(0, lambda: self._update(t, d))

    def _update(self, t: str, d: Any) -> None:
        if t in ["PEER_JOIN", "PEER_LEAVE"]:
            self.refresh_peers(d)
        elif t in ["CHAT", "REFRESH_CHAT"]:
            self.refresh_all_chat_displays()
        elif t == "GROUP_MSG":
            rid = d["room_id"]
            if rid in self.group_windows and self.group_windows[rid].winfo_exists():
                self.group_windows[rid].reload_history()
            else:
                self.open_group_window(rid, d["participants"])
        elif t == "POLL_START":
            self.start_poll_ui(d)
        elif t == "VOTE":
            self.record_vote_data(d["choice"])
        elif t == "POLL_RESULT":
            self.display_final_results(d["counts"], source="Leader")
        elif t == "FILE_COMPLETE":
            self._log(f"Received file: '{d['filename']}' ({d['filesize']} bytes) saved to downloads/.")

    def refresh_peers(self, peers: Dict[str, Any]) -> None:
        self.peer_vars = {}
        for w in self.peer_list_frame.winfo_children():
            w.destroy()
        if not peers:
            ctk.CTkLabel(self.peer_list_frame, text="No active peers", text_color="grey").pack(pady=10)
            return
        for pid, info in peers.items():
            card = ctk.CTkFrame(self.peer_list_frame, fg_color=COLOR_CARD)
            card.pack(fill="x", pady=2)
            var = ctk.BooleanVar()
            self.peer_vars[pid] = var
            chk = ctk.CTkCheckBox(card, text=f"{info['name']}", variable=var, text_color=COLOR_TEXT_MAIN, hover_color=COLOR_PRIMARY, fg_color=COLOR_PRIMARY)
            chk.pack(anchor="w", padx=10, pady=8)

    def refresh_all_chat_displays(self) -> None:
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        msgs = self.node.db.load_chat("broadcast")
        for m in msgs:
            # m: (msg_id, contact_id, sender_name, content, timestamp, is_private, lamport_time)
            ts = m[4]
            name = m[2]
            content = m[3]
            self.chat_display.insert("end", f"[{ts}] ", "time")
            self.chat_display.insert("end", f"{name}: ", "name")
            self.chat_display.insert("end", f"{content}\n", "msg")
        self.chat_display.tag_config("time", foreground="grey")
        self.chat_display.tag_config("name", foreground=COLOR_ACCENT)
        self.chat_display.tag_config("msg", foreground="white")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        for win in self.group_windows.values():
            if win.winfo_exists():
                win.reload_history()

    def create_group_room(self) -> None:
        selected_ids = [pid for pid, var in self.peer_vars.items() if var.get()]
        if not selected_ids:
            messagebox.showwarning("Select Peers", "Please check at least one peer in the list.")
            return
        participants = selected_ids + [self.node.id]
        room_id = str(uuid.uuid4())
        self.open_group_window(room_id, participants)

    def open_group_window(self, room_id: str, participants: List[str]) -> None:
        if room_id not in self.group_windows or not self.group_windows[room_id].winfo_exists():
            self.group_windows[room_id] = GroupChatWindow(self, room_id, participants, self.node)
        self.group_windows[room_id].focus()

    def open_message_manager(self) -> None:
        ManageMessagesWindow(self, self.node)

    def pick_and_send_file(self) -> None:
        if not self.node.peers:
            messagebox.showwarning("No Peers", "Cannot send file: No peers currently connected.")
            return
        filepath = filedialog.askopenfilename()
        if filepath:
            self.node.send_file(filepath)
            self._log(f"Sending file '{os.path.basename(filepath)}' to mesh...")

    def send_global(self, e: Any = None) -> None:
        txt = self.msg_entry.get().strip()
        if txt:
            self.node.broadcast_chat(txt)
            self.refresh_all_chat_displays()
            self.msg_entry.delete(0, "end")

    def restore_active_poll(self) -> None:
        last_poll = self.node.db.get_latest_poll()
        if not last_poll:
            return
        self.start_poll_ui(last_poll)
        counts = self.node.db.get_poll_counts(last_poll["id"])
        self.poll_votes = counts
        self.total_votes = sum(counts.values())
        if time.time() > last_poll["end_time"]:
            self.results_shown = True
            self.lbl_timer.configure(text="Results (History)", text_color=COLOR_SUCCESS)
            self.btn_create_poll.configure(state="normal", fg_color=COLOR_SUCCESS)
            self.display_final_results(counts, "History")
        else:
            self.node.election.active_poll_end_time = last_poll["end_time"]

    def open_poll_dialog(self) -> None:
        if time.time() < self.node.election.active_poll_end_time:
            messagebox.showerror("Locked", "An election is already in progress!")
            return
        d = ctk.CTkToplevel(self)
        d.geometry("320x360")
        d.configure(fg_color=COLOR_BG)
        ctk.CTkLabel(d, text="Create Poll", font=("Arial", 18, "bold"), text_color=COLOR_PRIMARY).pack(pady=10)

        q = ctk.CTkEntry(d, placeholder_text="Question", fg_color=COLOR_SIDEBAR)
        q.pack(fill="x", padx=20, pady=5)
        o = ctk.CTkEntry(d, placeholder_text="Options (e.g. Yes, No)", fg_color=COLOR_SIDEBAR)
        o.pack(fill="x", padx=20, pady=5)
        t = ctk.CTkEntry(d, placeholder_text="Duration in seconds (e.g. 30)", fg_color=COLOR_SIDEBAR)
        t.insert(0, "30")
        t.pack(fill="x", padx=20, pady=5)

        def sub() -> None:
            question = q.get().strip()
            options = [x.strip() for x in o.get().split(",") if x.strip()]
            if not question:
                messagebox.showwarning("Invalid Input", "Please enter a question.")
                return
            if len(options) < 2:
                messagebox.showwarning("Invalid Input", "Please provide at least 2 options.")
                return
            try:
                duration = int(t.get().strip())
                if duration <= 0:
                    raise ValueError
            except ValueError:
                duration = 30

            self.node.start_poll(question, options, duration)
            d.destroy()

        ctk.CTkButton(d, text="Launch Election", fg_color=COLOR_SUCCESS, hover_color="#86c981", text_color="#181825", command=sub).pack(pady=20)

    def start_poll_ui(self, data: Dict[str, Any]) -> None:
        self.active_poll_data = data
        self.poll_votes = {i: 0 for i in range(len(data["options"]))}
        self.total_votes = 0
        self.results_shown = False
        for w in self.active_poll_ui.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.active_poll_ui, text=data["question"], font=("Arial", 13, "bold"), text_color="white", wraplength=250).pack(pady=10)
        self.vote_widgets = []
        for i, opt in enumerate(data["options"]):
            btn = ctk.CTkButton(
                self.active_poll_ui,
                text=opt,
                height=35,
                fg_color=COLOR_CARD,
                hover_color=COLOR_ACCENT,
                border_width=1,
                border_color=COLOR_ACCENT,
                command=lambda x=i: self.submit_vote(x),
            )
            btn.pack(pady=3, fill="x")
            prog = ctk.CTkProgressBar(self.active_poll_ui, height=6, progress_color=COLOR_SUCCESS)
            prog.set(0)
            prog.pack(fill="x", pady=(0, 10))
            self.vote_widgets.append((btn, prog))
        self.update_timer()

    def update_timer(self) -> None:
        if self.results_shown or not self.active_poll_data:
            return
        rem = int(self.active_poll_data["end_time"] - time.time())
        if rem > 0:
            self.lbl_timer.configure(text=f"⏳ {rem}s Remaining", text_color="#F9A8D4")
            self.btn_create_poll.configure(state="disabled", fg_color=COLOR_CARD)
            self.after(1000, self.update_timer)
        else:
            self.lbl_timer.configure(text="⚙️ Computing...", text_color="orange")
            self.btn_create_poll.configure(state="normal", fg_color=COLOR_SUCCESS)
            for btn, _ in self.vote_widgets:
                btn.configure(state="disabled")
            if self.active_poll_data.get("sender_id") == self.node.id:
                self.after(1000, self.finalize_election)
            else:
                self.after(3000, self.check_results_received)

    def finalize_election(self) -> None:
        self.node.broadcast_result(self.active_poll_data["id"], self.poll_votes)
        self.display_final_results(self.poll_votes, source="Official")

    def check_results_received(self) -> None:
        if not self.results_shown:
            self.display_final_results(self.poll_votes, source="Backup")

    def submit_vote(self, choice: int) -> None:
        if self.node.cast_vote(self.active_poll_data["id"], choice):
            self.record_vote_data(choice)
            self.node.db.save_vote(self.active_poll_data["id"], choice)
            for btn, _ in self.vote_widgets:
                btn.configure(state="disabled", fg_color=COLOR_SIDEBAR)
            self.lbl_timer.configure(text="✅ Voted", text_color=COLOR_ACCENT)

    def record_vote_data(self, choice: int) -> None:
        choice = int(choice)
        if choice in self.poll_votes:
            self.poll_votes[choice] += 1
            self.total_votes += 1

    def display_final_results(self, counts_dict: Dict[Any, int], source: str = "") -> None:
        if self.results_shown:
            return
        self.results_shown = True
        counts = {int(k): v for k, v in counts_dict.items()}
        total = sum(counts.values())
        self.lbl_timer.configure(text=f"🏆 Results ({source})", text_color=COLOR_SUCCESS)

        for i, (btn, prog) in enumerate(self.vote_widgets):
            c = counts.get(i, 0)
            pct = c / total if total else 0
            btn.configure(text=f"{self.active_poll_data['options'][i]} ({int(pct*100)}%)", fg_color=COLOR_SIDEBAR)
            prog.set(pct)
