"""
app.py
------
Janela principal da aplicacao (Tkinter). Responsavel so por navegar
entre "telas" (menu inicial e tabuleiro de jogo) -- nao sabe nada de
rede nem de regras do jogo, so troca de frame e repassa eventos.
"""

import tkinter as tk

from gui.menu_view import MenuView
from gui.board_view import BoardView


class FanoronaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fanorona")
        # O tabuleiro sozinho ocupa ~860px de largura (MARGIN*2 + CELL_SIZE*8),
        # entao a janela precisa ser mais larga que isso para sobrar espaco
        # de verdade para o painel de chat ao lado.
        self.geometry("1250x680")
        self.minsize(1150, 620)
        self.resizable(True, True)

        # Referencias preenchidas depois que a rede conectar (via main.py)
        self.controller = None  # sera um game.game_state.GameController

        self._current_frame: tk.Frame | None = None
        self.show_menu()

    def _switch_to(self, frame: tk.Frame) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        self._current_frame = frame
        frame.pack(fill="both", expand=True)

    def show_menu(self) -> None:
        """Mostra a tela inicial: escolher Host ou Convidado."""
        menu = MenuView(self, on_host=self._on_host_chosen, on_join=self._on_join_chosen)
        self._switch_to(menu)

    def show_menu_status(self, text: str) -> None:
        if isinstance(self._current_frame, MenuView):
            self._current_frame.status_label.config(text=text)

    def show_board(self, controller) -> None:
        """
        Mostra a tela do tabuleiro. 'controller' e o GameController ja
        criado (com a rede conectada) em main.py.
        """
        self.controller = controller
        controller.on_board_changed = self._on_board_changed
        board_view = BoardView(self, controller)
        self._switch_to(board_view)
        board_view.redraw()

    def _on_board_changed(self, board) -> None:
        if isinstance(self._current_frame, BoardView):
            self._current_frame.redraw()

    # ------------------------------------------------------------------
    # Estes dois callbacks sao preenchidos de verdade pelo main.py
    # (que sabe como subir o FanoronaServer / FanoronaClient). Aqui na
    # GUI eles ficam so como "ganchos" -- a tela de menu chama, e quem
    # decide o que fazer de fato e o main.py.
    # ------------------------------------------------------------------
    def _on_host_chosen(self, port: int) -> None:
        if hasattr(self, "on_host_requested"):
            self.on_host_requested(port)

    def _on_join_chosen(self, ip: str, port: int) -> None:
        if hasattr(self, "on_join_requested"):
            self.on_join_requested(ip, port)


if __name__ == "__main__":
    # Teste visual rapido: abre so a tela de menu, sem rede de verdade.
    app = FanoronaApp()
    app.mainloop()