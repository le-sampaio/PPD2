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

        # Faz a coluna do painel lateral (1) crescer quando a janela for
        # redimensionada, em vez de ficar com largura fixa e espremida.
        self.grid_columnconfigure(0, weight=0)  # coluna do tabuleiro: tamanho fixo
        self.grid_columnconfigure(1, weight=1)  # coluna do chat: expande
        self.grid_rowconfigure(0, weight=1)

        # --- Area do tabuleiro (esquerda) ---
        canvas_width = MARGIN * 2 + CELL_SIZE * (COLS - 1)
        canvas_height = MARGIN * 2 + CELL_SIZE * (ROWS - 1)
        self.canvas = tk.Canvas(self, width=canvas_width, height=canvas_height, bg=COLOR_BG)
        self.canvas.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.status_label = tk.Label(self, text="", font=("Segoe UI", 11))
        self.status_label.grid(row=1, column=0, sticky="w", padx=10)

        # --- Painel lateral: chat + acoes (direita) ---
        side_panel = tk.Frame(self)
        side_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
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

        tk.Button(side_panel, text="Desistir", fg="red",
                  command=self._resign).grid(row=3, column=0, sticky="ew", pady=(20, 0))

        # Liga os callbacks do controller a esta tela
        self.controller.on_chat_message = self._on_chat_message
        self.controller.on_invalid_move = self._on_invalid_move
        self.controller.on_game_over = self._on_game_over

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

    # ------------------------------------------------------------------
    # Callbacks vindos do GameController
    # ------------------------------------------------------------------
    def _on_chat_message(self, text: str) -> None:
        self.chat_box.insert(tk.END, f"Oponente: {text}")

    def _on_invalid_move(self, reason: str) -> None:
        self.status_label.config(text=f"Jogada invalida: {reason}")

    def _on_game_over(self, winner_player: int) -> None:
        vencedor = "Voce" if winner_player == self.controller.my_player else "Oponente"
        self.status_label.config(text=f"Fim de jogo! Vencedor: {vencedor}")