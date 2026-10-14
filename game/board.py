"""
board.py
--------
Representa o estado do tabuleiro do Fanorona.

O tabuleiro oficial (Fanorona Tsivy) tem 5 linhas x 9 colunas = 45
intersecoes (pontos), nao 45 "casas" como um tabuleiro de xadrez -- as
pecas ficam EM CIMA das intersecoes, nao dentro de quadrados.

Cada intersecao pode ter linhas retas (horizontal/vertical) e, em
metade delas, tambem diagonais -- formando um padrao de "X" que se
repete a cada 2 colunas. E por essas linhas (retas ou diagonais,
dependendo do ponto) que as pecas se movem e capturam.

Convencao de coordenadas usada neste projeto:
    (linha, coluna), linha de 0 a 4 (5 linhas), coluna de 0 a 8 (9 colunas)
    (0, 0) fica no canto superior esquerdo.

Valores em cada posicao do tabuleiro:
    0  -> vazio
    1  -> peca do Jogador 1
    2  -> peca do Jogador 2
"""

ROWS = 5
COLS = 9

EMPTY = 0
PLAYER_ONE = 1
PLAYER_TWO = 2


class Board:
    def __init__(self):
        # grid[linha][coluna]
        self.grid: list[list[int]] = [[EMPTY] * COLS for _ in range(ROWS)]
        self._setup_initial_position()

    def _setup_initial_position(self) -> None:
        """
        Posicao inicial oficial do Fanorona:
        - As duas primeiras linhas (de cada lado) ficam cheias com as
          pecas de cada jogador.
        - A linha do meio (linha 2) fica cheia, EXCETO o ponto central
          (2, 4), que comeca vazio.
        - Jogador 1 ocupa as linhas 0 e 1 (parte de cima).
        - Jogador 2 ocupa as linhas 3 e 4 (parte de baixo).
        """
        for col in range(COLS):
            self.grid[0][col] = PLAYER_ONE
            self.grid[1][col] = PLAYER_ONE
            self.grid[3][col] = PLAYER_TWO
            self.grid[4][col] = PLAYER_TWO

        # Linha do meio: metade de cada lado, com o centro vazio
        for col in range(COLS):
            if col < COLS // 2:
                self.grid[2][col] = PLAYER_ONE
            elif col > COLS // 2:
                self.grid[2][col] = PLAYER_TWO
            else:
                self.grid[2][col] = EMPTY  # ponto central (2, 4)

    @staticmethod
    def has_diagonal(row: int, col: int) -> bool:
        """
        Retorna True se o ponto (row, col) tem linhas diagonais alem
        das retas. No Fanorona, isso segue um padrao de xadrez: um
        ponto tem diagonais se (row + col) for par.
        
        """
        return (row + col) % 2 == 0

    def get(self, row: int, col: int) -> int:
        return self.grid[row][col]

    def set(self, row: int, col: int, value: int) -> None:
        self.grid[row][col] = value

    def is_inside(self, row: int, col: int) -> bool:
        return 0 <= row < ROWS and 0 <= col < COLS

    def count_pieces(self, player: int) -> int:
        return sum(row.count(player) for row in self.grid)

    def to_list(self) -> list[list[int]]:
        """Copia serializavel do tabuleiro (util para mandar no 'state' via rede)."""
        return [row[:] for row in self.grid]

    def __repr__(self) -> str:
        symbols = {EMPTY: ".", PLAYER_ONE: "1", PLAYER_TWO: "2"}
        lines = []
        for row in self.grid:
            lines.append(" ".join(symbols[v] for v in row))
        return "\n".join(lines)


if __name__ == "__main__":
    # Teste rapido: imprime o tabuleiro inicial no terminal
    b = Board()
    print(b)
    print(f"\nPecas do Jogador 1: {b.count_pieces(PLAYER_ONE)}")
    print(f"Pecas do Jogador 2: {b.count_pieces(PLAYER_TWO)}")