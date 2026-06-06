import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


APP_VERSION = "4.0"
BASE_DIR = Path(__file__).resolve().parent
CHOICES = ("Rock", "Paper", "Scissors")
BEATS = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}
COUNTERS = {value: key for key, value in BEATS.items()}
MATCH_TARGETS = {"Quick Play": None, "Best of 3": 2, "Best of 5": 3}
DIFFICULTIES = ("Casual", "Adaptive")


@dataclass(frozen=True)
class RoundRecord:
    number: int
    player_choice: str
    computer_choice: str
    outcome: str
    player_match_score: int
    computer_match_score: int
    played_at: str


class GameEngine:
    """Display-independent Rock Paper Scissors rules and session state."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.mode = "Quick Play"
        self.difficulty = "Casual"
        self.reset_session()

    def reset_session(self):
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.best_streak = 0
        self.current_streak = 0
        self.history = []
        self.new_match()

    def new_match(self):
        self.player_match_score = 0
        self.computer_match_score = 0
        self.match_over = False
        self.match_winner = None

    def set_mode(self, mode):
        if mode not in MATCH_TARGETS:
            raise ValueError(f"Unknown game mode: {mode}")
        self.mode = mode
        self.new_match()

    def set_difficulty(self, difficulty):
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        self.difficulty = difficulty

    def choose_computer_move(self):
        if self.difficulty == "Adaptive" and self.history:
            counts = {
                choice: sum(record.player_choice == choice for record in self.history)
                for choice in CHOICES
            }
            predicted_move = max(CHOICES, key=lambda choice: counts[choice])
            if self.rng.random() < 0.75:
                return COUNTERS[predicted_move]
        return self.rng.choice(CHOICES)

    @staticmethod
    def determine_outcome(player_choice, computer_choice):
        if player_choice not in CHOICES or computer_choice not in CHOICES:
            raise ValueError("Choices must be Rock, Paper, or Scissors")
        if player_choice == computer_choice:
            return "Draw"
        if BEATS[player_choice] == computer_choice:
            return "Win"
        return "Loss"

    def play_round(self, player_choice, computer_choice=None):
        if self.match_over:
            raise RuntimeError("The match is complete")

        computer_choice = computer_choice or self.choose_computer_move()
        outcome = self.determine_outcome(player_choice, computer_choice)

        if outcome == "Win":
            self.wins += 1
            self.player_match_score += 1
            self.current_streak = max(1, self.current_streak + 1)
            self.best_streak = max(self.best_streak, self.current_streak)
        elif outcome == "Loss":
            self.losses += 1
            self.computer_match_score += 1
            self.current_streak = 0
        else:
            self.draws += 1

        target = MATCH_TARGETS[self.mode]
        if target and (
            self.player_match_score >= target or self.computer_match_score >= target
        ):
            self.match_over = True
            self.match_winner = (
                "Player"
                if self.player_match_score > self.computer_match_score
                else "Computer"
            )

        record = RoundRecord(
            number=len(self.history) + 1,
            player_choice=player_choice,
            computer_choice=computer_choice,
            outcome=outcome,
            player_match_score=self.player_match_score,
            computer_match_score=self.computer_match_score,
            played_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.history.append(record)
        return record

    @property
    def total_rounds(self):
        return self.wins + self.losses + self.draws

    @property
    def win_rate(self):
        decided_rounds = self.wins + self.losses
        return (self.wins / decided_rounds * 100) if decided_rounds else 0.0

    def snapshot(self):
        return {
            "version": APP_VERSION,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "settings": {"mode": self.mode, "difficulty": self.difficulty},
            "session": {
                "wins": self.wins,
                "losses": self.losses,
                "draws": self.draws,
                "win_rate": round(self.win_rate, 1),
                "best_streak": self.best_streak,
                "total_rounds": self.total_rounds,
            },
            "match": {
                "player_score": self.player_match_score,
                "computer_score": self.computer_match_score,
                "complete": self.match_over,
                "winner": self.match_winner,
            },
            "history": [asdict(record) for record in self.history],
        }


class RPSGameApp:
    COLORS = {
        "background": "#eef2f7",
        "card": "#ffffff",
        "text": "#172033",
        "muted": "#64748b",
        "accent": "#4f46e5",
        "accent_dark": "#3730a3",
        "success": "#15803d",
        "danger": "#b91c1c",
        "draw": "#a16207",
        "border": "#dbe3ee",
    }

    def __init__(self, master, engine=None):
        self.master = master
        self.engine = engine or GameEngine()
        self.reveal_pending = False
        self.pending_after_id = None
        self.images = {}

        self.master.title(f"RPS Arena {APP_VERSION}")
        self.master.geometry("960x720")
        self.master.minsize(820, 650)
        self.master.configure(background=self.COLORS["background"])
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.master.iconbitmap(BASE_DIR / "icon.ico")
        except tk.TclError:
            pass

        self.mode_var = tk.StringVar(value=self.engine.mode)
        self.difficulty_var = tk.StringVar(value=self.engine.difficulty)
        self.result_var = tk.StringVar(value="Choose your move to begin.")
        self.player_choice_var = tk.StringVar(value="READY")
        self.computer_choice_var = tk.StringVar(value="READY")
        self.match_score_var = tk.StringVar()
        self.record_var = tk.StringVar()
        self.win_rate_var = tk.StringVar()
        self.streak_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Ready  |  Shortcuts: R / P / S to play, Ctrl+N for a new match"
        )

        self.configure_styles()
        self.build_ui()
        self.create_menu()
        self.bind_shortcuts()
        self.refresh_stats()

    def configure_styles(self):
        style = ttk.Style(self.master)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self.COLORS["background"])
        style.configure(
            "Card.TFrame",
            background=self.COLORS["card"],
            borderwidth=1,
            relief="solid",
        )
        style.configure("StatCell.TFrame", background=self.COLORS["card"])
        style.configure(
            "Title.TLabel",
            background=self.COLORS["background"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.COLORS["background"],
            foreground=self.COLORS["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.COLORS["card"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "CardText.TLabel",
            background=self.COLORS["card"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Muted.TLabel",
            background=self.COLORS["card"],
            foreground=self.COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "ChoiceDisplay.TLabel",
            background=self.COLORS["card"],
            foreground=self.COLORS["accent"],
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Result.TLabel",
            background=self.COLORS["card"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "Choice.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 10),
        )
        style.configure(
            "Accent.TButton",
            background=self.COLORS["accent"],
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
        )
        style.map(
            "Accent.TButton",
            background=[
                ("active", self.COLORS["accent_dark"]),
                ("pressed", self.COLORS["accent_dark"]),
            ],
        )
        style.configure(
            "StatValue.TLabel",
            background=self.COLORS["card"],
            foreground=self.COLORS["accent"],
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background="#172033",
            foreground="#e2e8f0",
            padding=(12, 7),
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview",
            rowheight=27,
            font=("Segoe UI", 9),
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=self.COLORS["text"],
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#e8edf5",
            foreground=self.COLORS["text"],
        )

    def build_ui(self):
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        main = ttk.Frame(self.master, style="App.TFrame", padding=(24, 18, 24, 12))
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(2, weight=1)

        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="RPS ARENA", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Classic rules, smarter matches, better stats.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w")
        ttk.Button(
            header,
            text="New Match",
            style="Accent.TButton",
            command=self.new_match,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        settings = ttk.Frame(main, style="Card.TFrame", padding=12)
        settings.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        settings.columnconfigure(4, weight=1)
        ttk.Label(settings, text="Mode", style="CardText.TLabel").grid(
            row=0, column=0, padx=(0, 7)
        )
        mode_combo = ttk.Combobox(
            settings,
            textvariable=self.mode_var,
            values=tuple(MATCH_TARGETS),
            state="readonly",
            width=14,
        )
        mode_combo.grid(row=0, column=1, padx=(0, 20))
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_changed)

        ttk.Label(settings, text="Opponent", style="CardText.TLabel").grid(
            row=0, column=2, padx=(0, 7)
        )
        difficulty_combo = ttk.Combobox(
            settings,
            textvariable=self.difficulty_var,
            values=DIFFICULTIES,
            state="readonly",
            width=12,
        )
        difficulty_combo.grid(row=0, column=3)
        difficulty_combo.bind("<<ComboboxSelected>>", self.on_difficulty_changed)
        ttk.Label(
            settings,
            text="Adaptive learns which move you favor.",
            style="Muted.TLabel",
        ).grid(row=0, column=4, sticky="e")

        arena = ttk.Frame(main, style="Card.TFrame", padding=18)
        arena.grid(row=2, column=0, sticky="nsew", padx=(0, 7))
        arena.columnconfigure((0, 1), weight=1)
        ttk.Label(arena, text="THE ARENA", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(arena, text="YOU", style="Muted.TLabel").grid(
            row=1, column=0, pady=(20, 2)
        )
        ttk.Label(arena, text="COMPUTER", style="Muted.TLabel").grid(
            row=1, column=1, pady=(20, 2)
        )
        ttk.Label(
            arena, textvariable=self.player_choice_var, style="ChoiceDisplay.TLabel"
        ).grid(row=2, column=0, pady=(0, 14))
        ttk.Label(
            arena, textvariable=self.computer_choice_var, style="ChoiceDisplay.TLabel"
        ).grid(row=2, column=1, pady=(0, 14))

        ttk.Separator(arena).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(0, 14)
        )
        self.result_label = ttk.Label(
            arena,
            textvariable=self.result_var,
            style="Result.TLabel",
            anchor="center",
            justify="center",
        )
        self.result_label.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        button_row = ttk.Frame(arena, style="Card.TFrame")
        button_row.grid(row=5, column=0, columnspan=2)
        self.choice_buttons = []
        for column, choice in enumerate(CHOICES):
            image = self.load_image(choice)
            button = ttk.Button(
                button_row,
                text=choice,
                image=image,
                compound="top",
                style="Choice.TButton",
                command=lambda selected=choice: self.request_round(selected),
            )
            button.grid(row=0, column=column, padx=6)
            self.choice_buttons.append(button)

        ttk.Label(
            arena,
            text="Use the buttons or press R, P, or S.",
            style="Muted.TLabel",
        ).grid(row=6, column=0, columnspan=2, pady=(16, 0))

        sidebar = ttk.Frame(main, style="App.TFrame")
        sidebar.grid(row=2, column=1, sticky="nsew", padx=(7, 0))
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(2, weight=1)

        match_card = ttk.Frame(sidebar, style="Card.TFrame", padding=16)
        match_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        match_card.columnconfigure(0, weight=1)
        ttk.Label(match_card, text="MATCH", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            match_card, textvariable=self.match_score_var, style="StatValue.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        stats_card = ttk.Frame(sidebar, style="Card.TFrame", padding=16)
        stats_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        stats_card.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(stats_card, text="SESSION", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )
        self.create_stat(stats_card, 1, 0, "Record", self.record_var)
        self.create_stat(stats_card, 1, 1, "Win rate", self.win_rate_var)
        self.create_stat(stats_card, 1, 2, "Best streak", self.streak_var)

        history_card = ttk.Frame(sidebar, style="Card.TFrame", padding=12)
        history_card.grid(row=2, column=0, sticky="nsew")
        history_card.rowconfigure(1, weight=1)
        history_card.columnconfigure(0, weight=1)
        ttk.Label(history_card, text="ROUND HISTORY", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        columns = ("round", "you", "computer", "result")
        self.history_tree = ttk.Treeview(
            history_card, columns=columns, show="headings", height=8
        )
        headings = {
            "round": ("#", 36),
            "you": ("You", 72),
            "computer": ("CPU", 72),
            "result": ("Result", 62),
        }
        for column, (heading, width) in headings.items():
            self.history_tree.heading(column, text=heading)
            self.history_tree.column(column, width=width, minwidth=36, anchor="center")
        self.history_tree.tag_configure("Win", foreground=self.COLORS["success"])
        self.history_tree.tag_configure("Loss", foreground=self.COLORS["danger"])
        self.history_tree.tag_configure("Draw", foreground=self.COLORS["draw"])
        self.history_tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            history_card, orient="vertical", command=self.history_tree.yview
        )
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        ttk.Label(self.master, textvariable=self.status_var, style="Status.TLabel").grid(
            row=1, column=0, sticky="ew"
        )

    def create_stat(self, parent, row, column, label, variable):
        cell = ttk.Frame(parent, style="StatCell.TFrame")
        cell.grid(row=row, column=column, sticky="ew")
        ttk.Label(cell, textvariable=variable, style="StatValue.TLabel").pack()
        ttk.Label(cell, text=label, style="Muted.TLabel").pack()

    def load_image(self, choice):
        path = BASE_DIR / f"{choice.lower()}.gif"
        try:
            self.images[choice] = tk.PhotoImage(file=path)
        except tk.TclError:
            self.images[choice] = None
        return self.images[choice]

    def create_menu(self):
        menu = tk.Menu(self.master)
        game_menu = tk.Menu(menu, tearoff=False)
        game_menu.add_command(
            label="New Match", accelerator="Ctrl+N", command=self.new_match
        )
        game_menu.add_command(
            label="Reset Session", accelerator="Ctrl+Shift+R", command=self.reset_session
        )
        game_menu.add_separator()
        game_menu.add_command(
            label="Export Statistics", accelerator="Ctrl+E", command=self.export_stats
        )
        game_menu.add_separator()
        game_menu.add_command(label="Exit", command=self.close)
        menu.add_cascade(label="Game", menu=game_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="How to Play", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.master.configure(menu=menu)

    def bind_shortcuts(self):
        for key, choice in (("r", "Rock"), ("p", "Paper"), ("s", "Scissors")):
            self.master.bind(
                key, lambda _event, selected=choice: self.request_round(selected)
            )
        self.master.bind("<Control-n>", lambda _event: self.new_match())
        self.master.bind("<Control-N>", lambda _event: self.new_match())
        self.master.bind("<Control-e>", lambda _event: self.export_stats())
        self.master.bind("<Control-E>", lambda _event: self.export_stats())
        self.master.bind("<Control-Shift-r>", lambda _event: self.reset_session())
        self.master.bind("<Control-Shift-R>", lambda _event: self.reset_session())

    def request_round(self, player_choice):
        if self.reveal_pending:
            return
        if self.engine.match_over:
            self.result_var.set("This match is complete. Start a new match to continue.")
            self.status_var.set("Match complete")
            return

        self.reveal_pending = True
        self.set_choice_buttons_enabled(False)
        self.player_choice_var.set(player_choice.upper())
        self.computer_choice_var.set("THINKING...")
        self.result_var.set("Computer is choosing...")
        self.status_var.set(f"You selected {player_choice}")
        self.pending_after_id = self.master.after(
            350, lambda: self.finish_round(player_choice)
        )

    def finish_round(self, player_choice):
        self.pending_after_id = None
        record = self.engine.play_round(player_choice)
        self.computer_choice_var.set(record.computer_choice.upper())

        messages = {
            "Win": f"{player_choice} beats {record.computer_choice}. You win!",
            "Loss": f"{record.computer_choice} beats {player_choice}. Computer wins.",
            "Draw": f"Both chose {player_choice}. It is a draw.",
        }
        result_text = messages[record.outcome]
        if self.engine.match_over:
            if self.engine.match_winner == "Player":
                result_text += "\nMatch won. Strong finish."
            else:
                result_text += "\nMatch lost. Start a new match for a rematch."

        self.result_var.set(result_text)
        self.history_tree.insert(
            "",
            0,
            values=(
                record.number,
                record.player_choice,
                record.computer_choice,
                record.outcome,
            ),
            tags=(record.outcome,),
        )
        self.refresh_stats()
        self.status_var.set(
            f"Round {record.number}: {record.outcome.lower()}  |  "
            f"{self.engine.total_rounds} rounds played"
        )
        self.reveal_pending = False
        self.set_choice_buttons_enabled(not self.engine.match_over)

    def refresh_stats(self):
        target = MATCH_TARGETS[self.engine.mode]
        target_text = f"first to {target}" if target else "open play"
        self.match_score_var.set(
            f"You {self.engine.player_match_score}  -  "
            f"{self.engine.computer_match_score} CPU  ({target_text})"
        )
        self.record_var.set(
            f"{self.engine.wins}-{self.engine.losses}-{self.engine.draws}"
        )
        self.win_rate_var.set(f"{self.engine.win_rate:.0f}%")
        self.streak_var.set(str(self.engine.best_streak))

    def set_choice_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for button in self.choice_buttons:
            button.configure(state=state)

    def on_mode_changed(self, _event=None):
        self.cancel_pending_reveal()
        self.engine.set_mode(self.mode_var.get())
        self.reset_match_display()
        self.result_var.set(f"{self.engine.mode} selected. Choose your move.")
        self.status_var.set("Game mode changed; match score reset")

    def on_difficulty_changed(self, _event=None):
        self.engine.set_difficulty(self.difficulty_var.get())
        self.status_var.set(f"Opponent set to {self.engine.difficulty}")

    def new_match(self):
        self.cancel_pending_reveal()
        self.engine.new_match()
        self.reset_match_display()
        self.result_var.set("New match ready. Choose your move.")
        self.status_var.set("New match started; session statistics retained")

    def reset_session(self):
        if self.engine.total_rounds and not messagebox.askyesno(
            "Reset Session",
            "Reset all scores, streaks, and round history?",
            parent=self.master,
        ):
            return
        self.cancel_pending_reveal()
        self.engine.reset_session()
        self.reset_match_display()
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self.result_var.set("Session reset. Choose your move.")
        self.status_var.set("Session statistics reset")

    def reset_match_display(self):
        self.player_choice_var.set("READY")
        self.computer_choice_var.set("READY")
        self.set_choice_buttons_enabled(True)
        self.refresh_stats()

    def cancel_pending_reveal(self):
        if self.pending_after_id is not None:
            self.master.after_cancel(self.pending_after_id)
            self.pending_after_id = None
        self.reveal_pending = False

    def export_stats(self):
        export_path = BASE_DIR / "rps_stats.json"
        try:
            export_path.write_text(
                json.dumps(self.engine.snapshot(), indent=2), encoding="utf-8"
            )
        except OSError as error:
            messagebox.showerror(
                "Export Failed", f"Could not export statistics:\n{error}", parent=self.master
            )
            return
        self.status_var.set(f"Statistics exported to {export_path.name}")
        messagebox.showinfo(
            "Export Complete",
            f"Statistics saved to:\n{export_path}",
            parent=self.master,
        )

    def show_help(self):
        messagebox.showinfo(
            "How to Play",
            "Rock beats Scissors, Scissors beats Paper, and Paper beats Rock.\n\n"
            "Quick Play has no match limit. Best of 3 is first to 2 wins; "
            "Best of 5 is first to 3 wins. Draws do not advance the match score.\n\n"
            "Adaptive opponents learn your most common move and try to counter it.\n\n"
            "Keyboard: R = Rock, P = Paper, S = Scissors, Ctrl+N = New Match.",
            parent=self.master,
        )

    def show_about(self):
        messagebox.showinfo(
            "About RPS Arena",
            f"RPS Arena {APP_VERSION}\n"
            "Originally developed by Kai Piper\n\n"
            "A refined Rock Paper Scissors desktop game with match modes, "
            "adaptive AI, session analytics, history, shortcuts, and JSON export.",
            parent=self.master,
        )

    def close(self):
        self.cancel_pending_reveal()
        self.master.destroy()


def main():
    root = tk.Tk()
    RPSGameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
