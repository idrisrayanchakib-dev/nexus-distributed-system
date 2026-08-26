import tkinter as tk
from tkinter import messagebox
from typing import Any, List
import customtkinter as ctk

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


class ManageMessagesWindow(ctk.CTkToplevel):
    """Window allowing users to view, edit, or retract their sent messages."""

    def __init__(self, parent: Any, node: Any) -> None:
        super().__init__(parent)
        self.title("Manage Messages")
        self.geometry("520x620")
        self.configure(fg_color=COLOR_BG)
        self.node = node
        self.parent = parent

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_BG)
        self.scroll.pack(fill="both", expand=True, padx=15, pady=15)
        self.refresh()

    def refresh(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        my_msgs = self.node.db.get_my_messages(self.node.username)
        if not my_msgs:
            ctk.CTkLabel(
                self.scroll,
                text="No messages to manage.",
                font=("Arial", 14),
                text_color=COLOR_TEXT_SUB,
            ).pack(pady=20)
            return

        for m in my_msgs:
            msg_id, contact_id, _, content, timestamp, _, lamport_t = m
            room = "Global" if contact_id == "broadcast" else "Private"

            card = ctk.CTkFrame(self.scroll, fg_color=COLOR_CARD, corner_radius=10)
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(
                card,
                text=f"🕒 {timestamp} • {room} • Clock: {lamport_t}",
                font=("Arial", 11, "bold"),
                text_color=COLOR_ACCENT,
            ).pack(anchor="w", padx=10, pady=(5, 0))

            ctk.CTkLabel(
                card,
                text=content,
                wraplength=420,
                font=("Arial", 13),
                text_color=COLOR_TEXT_MAIN,
            ).pack(anchor="w", padx=10)

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=5)

            ctk.CTkButton(
                btn_frame,
                text="✎ Edit",
                width=80,
                fg_color="#F9A8D4",
                text_color="black",
                hover_color="#F472B6",
                command=lambda mid=msg_id, txt=content: self.open_edit(mid, txt),
            ).pack(side="left", padx=(0, 5))

            ctk.CTkButton(
                btn_frame,
                text="🗑 Delete",
                width=80,
                fg_color=COLOR_DANGER,
                hover_color="#d16682",
                command=lambda mid=msg_id: self.do_delete(mid),
            ).pack(side="left")

    def do_delete(self, msg_id: str) -> None:
        if messagebox.askyesno("Delete", "Permanently retract this message across all peers?"):
            self.node.delete_message_net(msg_id)
            self.refresh()
            self.parent.refresh_all_chat_displays()

    def open_edit(self, msg_id: str, old_text: str) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Message")
        dialog.geometry("360x180")
        dialog.configure(fg_color=COLOR_BG)

        ctk.CTkLabel(dialog, text="Update your message:", text_color=COLOR_TEXT_MAIN).pack(pady=(15, 5))
        entry = ctk.CTkEntry(dialog, fg_color=COLOR_SIDEBAR, border_color=COLOR_ACCENT, text_color=COLOR_TEXT_MAIN)
        entry.insert(0, old_text)
        entry.pack(fill="x", padx=20, pady=10)

        def save() -> None:
            new_val = entry.get().strip()
            if new_val:
                self.node.edit_message_net(msg_id, new_val)
                dialog.destroy()
                self.refresh()
                self.parent.refresh_all_chat_displays()

        ctk.CTkButton(dialog, text="Save Changes", fg_color=COLOR_SUCCESS, hover_color="#86c981", text_color="#181825", command=save).pack(pady=10)


class GroupChatWindow(ctk.CTkToplevel):
    """Private Multicast Chat Room Window."""

    def __init__(self, parent: Any, room_id: str, participants: List[str], node: Any) -> None:
        super().__init__(parent)
        self.title("Private Room")
        self.geometry("520x620")
        self.configure(fg_color=COLOR_BG)
        self.room_id = room_id
        self.participants = participants
        self.node = node

        names = [node.peers[p]["name"] if p in node.peers else p[:4] for p in participants if p != node.id]

        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, height=50)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text=f"🔒 Private Room with: {', '.join(names)}",
            font=("Roboto Medium", 14),
            text_color=COLOR_PRIMARY,
        ).pack(pady=10)

        self.display = ctk.CTkTextbox(self, state="disabled", fg_color=COLOR_BG, text_color=COLOR_TEXT_MAIN, font=("Arial", 13))
        self.display.pack(expand=True, fill="both", padx=15, pady=10)

        fr = ctk.CTkFrame(self, fg_color="transparent")
        fr.pack(fill="x", padx=15, pady=15)

        self.entry = ctk.CTkEntry(
            fr,
            placeholder_text="Type a secret message...",
            fg_color=COLOR_SIDEBAR,
            border_color=COLOR_ACCENT,
            border_width=1,
            corner_radius=20,
            height=40,
        )
        self.entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.entry.bind("<Return>", self.send)

        ctk.CTkButton(
            fr,
            text="➤",
            width=50,
            height=40,
            corner_radius=20,
            fg_color=COLOR_ACCENT,
            hover_color="#6c9af0",
            command=self.send,
        ).pack(side="right")
        self.reload_history()

    def reload_history(self) -> None:
        self.display.configure(state="normal")
        self.display.delete("1.0", "end")
        msgs = self.node.db.load_chat(self.room_id)
        for m in msgs:
            self.display.insert("end", f"[{m[4]}] {m[2]}: {m[3]}\n")
        self.display.configure(state="disabled")
        self.display.see("end")

    def send(self, e: Any = None) -> None:
        txt = self.entry.get().strip()
        if txt:
            self.node.send_group_message(self.room_id, self.participants, txt)
            self.reload_history()
            self.entry.delete(0, "end")
