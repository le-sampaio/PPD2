"""
board_view.py
-------------
Desenha o tabuleiro do Fanorona em um Canvas do Tkinter e traduz
cliques do mouse em coordenadas (linha, coluna) do tabuleiro, que sao
repassadas para o GameController (game/game_state.py) validar e
aplicar.

Esta tela NAO decide se um movimento e valido -- ela so junta 2
cliques (origem e destino) e chama controller.try_local_move(). Quem
diz se pode ou nao e o controller (que usa game/rules.py).
"""

import tkinter as tk

from game.board import ROWS, COLS, EMPTY, PLAYER_ONE, PLAYER_TWO, Board
from game import rules

MARGIN = 60
CELL_SIZE = 90
PIECE_RADIUS = 22

COLOR_BG = "#e8d9b5"
COLOR_LINE = "#3a2e1f"
COLOR_P1 = "#f4f1ec"      # pecas do Jogador 1 (claras)
COLOR_P2 = "#2b2b2b"      # pecas do Jogador 2 (escuras)
COLOR_SELECTED = "#c0392b"


class BoardView(tk.Frame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.selected_pos: tuple | None = None
        self.game_over = False  # trava cliques e o botao Desistir quando o jogo acaba

        # Faz a coluna do painel lateral (1) crescer quando a janela for
        # redimensionada, em vez de ficar com largura fixa e espremida.
        self.grid_columnconfigure(0, weight=0)  # coluna do tabuleiro: tamanho fixo
        self.grid_columnconfigure(1, weight=1)  # coluna do chat: expande
        self.grid_rowconfigure(1, weight=1)

        # --- Area do tabuleiro (esquerda) ---
        canvas_width = MARGIN * 2 + CELL_SIZE * (COLS - 1)
        canvas_height = MARGIN * 2 + CELL_SIZE * (ROWS - 1)

        # Painel "quem sou eu" + contador de capturas, acima do tabuleiro.
        info_bar = tk.Frame(self)
        info_bar.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="new")

        # Circulo colorido mostrando a cor da minha peca (branca/preta)
        my_color = COLOR_P1 if self.controller.my_player == PLAYER_ONE else COLOR_P2
        my_color_name = "Branca" if self.controller.my_player == PLAYER_ONE else "Preta"
        self.player_indicator = tk.Canvas(info_bar, width=26, height=26,
                                           highlightthickness=0, bg=self.cget("bg"))
        self.player_indicator.create_oval(3, 3, 23, 23, fill=my_color, outline=COLOR_LINE, width=2)
        self.player_indicator.pack(side="left")

        tk.Label(info_bar, text=f"Voce e a peca {my_color_name}",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(8, 20))

        self.captures_label = tk.Label(info_bar, text="Pecas conquistadas: 0",
                                        font=("Segoe UI", 11))
        self.captures_label.pack(side="left")

        self.canvas = tk.Canvas(self, width=canvas_width, height=canvas_height, bg=COLOR_BG)
        self.canvas.grid(row=1, column=0, padx=10, pady=10, sticky="n")
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.status_label = tk.Label(self, text="", font=("Segoe UI", 11))
        self.status_label.grid(row=2, column=0, sticky="w", padx=10)

        # --- Painel lateral: chat + acoes (direita) ---
        side_panel = tk.Frame(self)
        side_panel.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=10)
        side_panel.grid_rowconfigure(1, weight=1)  # a lista de chat cresce verticalmente
        side_panel.grid_columnconfigure(0, weight=1)

        tk.Label(side_panel, text="Chat", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w")

        self.chat_box = tk.Listbox(side_panel)
        self.chat_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        chat_input_frame = tk.Frame(side_panel)
        chat_input_frame.grid(row=2, column=0, sticky="ew")
        chat_input_frame.grid_columnconfigure(0, weight=1)
        self.chat_entry = tk.Entry(chat_input_frame)
        self.chat_entry.grid(row=0, column=0, sticky="ew")
        self.chat_entry.bind("<Return>", lambda event: self._send_chat())
        tk.Button(chat_input_frame, text="Enviar", command=self._send_chat).grid(row=0, column=1)

        self.resign_button = tk.Button(side_panel, text="Desistir", fg="red",
                                        command=self._resign)
        self.resign_button.grid(row=3, column=0, sticky="ew", pady=(20, 0))

        # Liga os callbacks do controller a esta tela
        self.controller.on_chat_message = self._on_chat_message
        self.controller.on_invalid_move = self._on_invalid_move
        self.controller.on_game_over = self._on_game_over
        self.controller.on_capture_choice_needed = self._ask_capture_choice
        self.controller.on_turn_changed = self._on_turn_changed

        # Se o jogo ja comeca com o turno do jogador local (ex: Jogador 1
        # assim que a partida abre), mostra o popup de "Sua vez!" logo de cara.
        if self.controller.current_turn == self.controller.my_player:
            self.after(300, lambda: self._show_turn_popup())

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def redraw(self) -> None:
        # Se ha uma captura em sequencia pendente, a peca certa ja fica
        # pre-selecionada -- o jogador so precisa clicar no proximo destino.
        if self.controller.pending_capture_pos is not None:
            self.selected_pos = self.controller.pending_capture_pos

        self.canvas.delete("all")
        self._draw_grid()
        self._draw_pieces()

        # Contador de pecas que EU ja capturei do adversario
        my_captures = self.controller.captures.get(self.controller.my_player, 0)
        self.captures_label.config(text=f"Pecas conquistadas: {my_captures}")

        if self.game_over:
            return  # a mensagem de fim de jogo ja foi definida em _on_game_over

        if self.controller.pending_capture_pos is not None:
            turn_text = "Continue capturando com a mesma peca!"
        else:
            turn_text = "Sua vez" if self.controller.current_turn == self.controller.my_player else "Vez do oponente"
        self.status_label.config(text=turn_text)

    def _cell_center(self, row: int, col: int) -> tuple:
        x = MARGIN + col * CELL_SIZE
        y = MARGIN + row * CELL_SIZE
        return x, y

    def _draw_grid(self) -> None:
        # Linhas retas: todas as horizontais e verticais
        for row in range(ROWS):
            x1, y1 = self._cell_center(row, 0)
            x2, y2 = self._cell_center(row, COLS - 1)
            self.canvas.create_line(x1, y1, x2, y2, fill=COLOR_LINE, width=2)
        for col in range(COLS):
            x1, y1 = self._cell_center(0, col)
            x2, y2 = self._cell_center(ROWS - 1, col)
            self.canvas.create_line(x1, y1, x2, y2, fill=COLOR_LINE, width=2)

        # Diagonais: so nos pontos onde Board.has_diagonal() e True,
        # desenhando o segmento local ate os vizinhos diagonais
        for row in range(ROWS):
            for col in range(COLS):
                if not Board.has_diagonal(row, col):
                    continue
                x1, y1 = self._cell_center(row, col)
                for d_row, d_col in [(-1, -1), (-1, 1)]:
                    n_row, n_col = row + d_row, col + d_col
                    if 0 <= n_row < ROWS and 0 <= n_col < COLS:
                        x2, y2 = self._cell_center(n_row, n_col)
                        self.canvas.create_line(x1, y1, x2, y2, fill=COLOR_LINE, width=2)

    def _draw_pieces(self) -> None:
        board = self.controller.board
        for row in range(ROWS):
            for col in range(COLS):
                value = board.get(row, col)
                if value == EMPTY:
                    continue
                x, y = self._cell_center(row, col)
                color = COLOR_P1 if value == PLAYER_ONE else COLOR_P2
                outline = COLOR_SELECTED if self.selected_pos == (row, col) else COLOR_LINE
                self.canvas.create_oval(
                    x - PIECE_RADIUS, y - PIECE_RADIUS, x + PIECE_RADIUS, y + PIECE_RADIUS,
                    fill=color, outline=outline, width=3,
                )

    # ------------------------------------------------------------------
    # Interacao
    # ------------------------------------------------------------------
    def _on_canvas_click(self, event) -> None:
        if self.game_over:
            return

        col = round((event.x - MARGIN) / CELL_SIZE)
        row = round((event.y - MARGIN) / CELL_SIZE)
        if not (0 <= row < ROWS and 0 <= col < COLS):
            return

        if self.selected_pos is None:
            # Primeiro clique: seleciona a peca de origem (se for do jogador local)
            if self.controller.board.get(row, col) == self.controller.my_player:
                self.selected_pos = (row, col)
                self.redraw()
        else:
            # Segundo clique: tenta mover da origem selecionada ate aqui
            from_pos = self.selected_pos
            self.selected_pos = None
            if (row, col) != from_pos:
                self.controller.try_local_move(from_pos, (row, col))
            self.redraw()

    def _send_chat(self) -> None:
        text = self.chat_entry.get().strip()
        if not text:
            return
        self.chat_box.insert(tk.END, f"Voce: {text}")
        self.controller.send_chat(text)
        self.chat_entry.delete(0, tk.END)

    def _resign(self) -> None:
        self.controller.resign()

    def _ask_capture_choice(self, from_pos: tuple, to_pos: tuple) -> str:
        """
        Chamado pelo GameController quando um movimento permite AMBAS
        as capturas (aproximacao e afastamento). Mostra um popup modal
        (bloqueia o resto da janela ate o jogador escolher) com as
        duas opcoes, mostrando quantas pecas cada uma captura.

        Retorna "approach" ou "withdrawal", conforme o botao clicado.
        """
        board = self.controller.board
        player = self.controller.my_player
        approach = rules.get_captures_by_approach(board, player, from_pos, to_pos)
        withdrawal = rules.get_captures_by_withdrawal(board, player, from_pos, to_pos)

        choice = {"value": None}

        dialog = tk.Toplevel(self)
        dialog.title("Escolha a captura")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()  # torna o popup modal (bloqueia o resto da janela)

        tk.Label(
            dialog,
            text="Este movimento permite duas capturas diferentes.\nEscolha qual aplicar:",
            font=("Segoe UI", 11), justify="center",
        ).pack(padx=24, pady=(20, 14))

        def choose(value: str) -> None:
            choice["value"] = value
            dialog.destroy()

        tk.Button(
            dialog, text=f"Aproximacao  ({len(approach)} peca(s) capturada(s))",
            width=34, command=lambda: choose("approach"),
        ).pack(padx=24, pady=6)

        tk.Button(
            dialog, text=f"Afastamento  ({len(withdrawal)} peca(s) capturada(s))",
            width=34, command=lambda: choose("withdrawal"),
        ).pack(padx=24, pady=(6, 20))

        # Se o jogador fechar a janela no X sem escolher, usamos aproximacao
        # como padrao em vez de travar o jogo esperando uma escolha que nunca vem.
        dialog.protocol("WM_DELETE_WINDOW", lambda: choose("approach"))

        # Centraliza o popup em relacao a janela principal
        dialog.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # wait_window roda um loop de eventos aninhado: o codigo para AQUI
        # ate o popup ser fechado (por um dos dois botoes ou pelo X),
        # e so entao continua -- por isso este metodo pode simplesmente
        # "return choice['value']" no final, de forma sincrona.
        self.wait_window(dialog)
        return choice["value"]

    def _on_turn_changed(self, current_turn: int) -> None:
        """
        Chamado pelo GameController toda vez que o turno passa de um
        jogador para o outro. Se o turno novo for o MEU, mostra o popup
        de "Sua vez!". Nao dispara durante uma sequencia de capturas
        (o controller so chama on_turn_changed quando o turno de fato
        muda de jogador).
        """
        if current_turn == self.controller.my_player and not self.game_over:
            self._show_turn_popup()

    def _show_turn_popup(self) -> None:
        """
        Popup avisando que agora e a sua vez. Diferente do popup de fim
        de jogo, este NAO e modal (nao usa grab_set) -- o jogador pode
        continuar vendo/interagindo com o tabuleiro por baixo -- e some
        sozinho depois de um tempinho, sem precisar clicar em nada.
        """
        dialog = tk.Toplevel(self)
        dialog.overrideredirect(True)  # sem barra de titulo, visual de "toast"
        dialog.attributes("-topmost", True)

        frame = tk.Frame(dialog, bg="#1e7e34", padx=28, pady=16,
                          highlightbackground="#155d27", highlightthickness=2)
        frame.pack()
        tk.Label(frame, text="SUA VEZ!", font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#1e7e34").pack()

        dialog.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + 40
        dialog.geometry(f"+{x}+{y}")

        # Fecha sozinho depois de 1.4s, e tambem se o jogador clicar nele
        dialog.bind("<Button-1>", lambda event: dialog.destroy())
        dialog.after(1400, lambda: dialog.destroy() if dialog.winfo_exists() else None)

    # ------------------------------------------------------------------
    # Callbacks vindos do GameController
    # ------------------------------------------------------------------
    def _on_chat_message(self, text: str) -> None:
        self.chat_box.insert(tk.END, f"Oponente: {text}")

    def _on_invalid_move(self, reason: str) -> None:
        self.status_label.config(text=f"Jogada invalida: {reason}")

    def _on_game_over(self, winner_player: int) -> None:
        self.game_over = True
        self.selected_pos = None
        self.resign_button.config(state="disabled")

        i_won = winner_player == self.controller.my_player
        summary = "Voce venceu!" if i_won else "Voce perdeu."
        self.status_label.config(text=f"Fim de jogo -- {summary}")

        self._show_game_over_dialog(i_won)

    def _show_game_over_dialog(self, i_won: bool) -> None:
        """
        Mostra um popup destacado avisando quem venceu a partida. E so
        informativo (nao bloqueia nada alem de si mesmo) -- o tabuleiro
        ja fica travado por conta da flag self.game_over.
        """
        dialog = tk.Toplevel(self)
        dialog.title("Fim de jogo")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        headline = "VOCE VENCEU!" if i_won else "VOCE PERDEU"
        color = "#1e7e34" if i_won else "#a12622"

        tk.Label(
            dialog, text=headline, font=("Segoe UI", 20, "bold"), fg=color,
        ).pack(padx=40, pady=(24, 6))

        subtitle = "Parabens, todas as pecas do adversario foram capturadas!" if i_won \
            else "Voce ficou sem pecas (ou desistiu). Bora jogar de novo?"
        tk.Label(
            dialog, text=subtitle, font=("Segoe UI", 10), wraplength=280, justify="center",
        ).pack(padx=40, pady=(0, 20))

        tk.Button(dialog, text="Fechar", width=16, command=dialog.destroy).pack(pady=(0, 20))

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        dialog.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")