"""
rules.py
--------
Concentra TODA a logica de regras do Fanorona: movimento, capturas por
aproximacao e por afastamento, sequencia de capturas, e checagem de
vencedor.

As 8 direcoes possiveis a partir de um ponto (linha, coluna):
    N, S, L, O (retas)          -> sempre disponiveis
    NE, NO, SE, SO (diagonais)  -> so em pontos onde has_diagonal() e True
"""

from game.board import Board, EMPTY, PLAYER_ONE, PLAYER_TWO, ROWS, COLS

# As 8 direcoes como vetores (delta_linha, delta_coluna)
DIRECTIONS = {
    "N":  (-1, 0),
    "S":  (1, 0),
    "L":  (0, 1),
    "O":  (0, -1),
    "NE": (-1, 1),
    "NO": (-1, -1),
    "SE": (1, 1),
    "SO": (1, -1),
}

# Direcao oposta de cada direcao (usado na regra de sequencia de
# capturas: nao se pode continuar capturando voltando pelo mesmo
# caminho que acabou de ser percorrido).
OPPOSITE_DIRECTION = {
    "N": "S", "S": "N",
    "L": "O", "O": "L",
    "NE": "SO", "SO": "NE",
    "NO": "SE", "SE": "NO",
}


class InvalidMoveError(Exception):
    """Levantada quando um movimento nao segue as regras do jogo."""
    pass


def other_player(player: int) -> int:
    return PLAYER_TWO if player == PLAYER_ONE else PLAYER_ONE


def get_valid_directions(board: Board, row: int, col: int) -> list[str]:
    """
    Retorna a lista de direcoes validas a partir do ponto (row, col):
    as 4 retas sempre, mais as 4 diagonais se board.has_diagonal(row, col).
    """
    directions = ["N", "S", "L", "O"]
    if board.has_diagonal(row, col):
        directions += ["NE", "NO", "SE", "SO"]
    return directions


def get_move_direction(from_pos: tuple, to_pos: tuple) -> str | None:
    """
    Descobre qual das 8 direcoes de DIRECTIONS corresponde ao vetor
    de from_pos ate to_pos. Retorna None se o passo nao bater com
    NENHUMA das 8 direcoes (ex: mais de uma casa, ou fora de linha).
    """
    delta = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])
    for direction_name, vector in DIRECTIONS.items():
        if vector == delta:
            return direction_name
    return None


def is_valid_move(board: Board, player: int, from_pos: tuple, to_pos: tuple) -> bool:
    """
    Verifica se mover a peca de from_pos para to_pos e valido para
    'player' no estado atual do tabuleiro, considerando:
      - from_pos e to_pos estao dentro do tabuleiro
      - from_pos tem uma peca do 'player'
      - to_pos esta vazio
      - o movimento e de exatamente 1 passo, em uma das 8 direcoes
      - a direcao do movimento e valida para from_pos (reta sempre
        disponivel, diagonal so nos pontos marcados)
    """
    from_row, from_col = from_pos
    to_row, to_col = to_pos

    if not (board.is_inside(from_row, from_col) and board.is_inside(to_row, to_col)):
        return False

    if board.get(from_row, from_col) != player:
        return False

    if board.get(to_row, to_col) != EMPTY:
        return False

    move_direction = get_move_direction(from_pos, to_pos)
    if move_direction is None:
        return False

    return move_direction in get_valid_directions(board, from_row, from_col)


def move_piece(board: Board, from_pos: tuple, to_pos: tuple) -> None:
    """
    Move a peca de from_pos para to_pos, sem verificar regras (quem
    chama e responsavel por ja ter validado) e sem lidar com capturas
    -- so troca o conteudo das duas posicoes.
    """
    from_row, from_col = from_pos
    to_row, to_col = to_pos

    piece = board.get(from_row, from_col)
    board.set(from_row, from_col, EMPTY)
    board.set(to_row, to_col, piece)


def _scan_line_for_captures(board: Board, player: int, start_pos: tuple, direction: str) -> list[tuple]:
    """
    Percorre o tabuleiro a partir de start_pos (exclusive) na direcao
    dada, coletando pecas do ADVERSARIO consecutivas, ate encontrar
    uma casa vazia, uma peca do proprio 'player', ou o fim do
    tabuleiro. Usado tanto pela captura por aproximacao quanto pela
    de afastamento -- a unica diferenca entre as duas e de ONDE e em
    qual direcao comeca a varredura (ver funcoes abaixo).
    """
    d_row, d_col = DIRECTIONS[direction]
    opponent = other_player(player)

    captured = []
    row, col = start_pos[0] + d_row, start_pos[1] + d_col
    while board.is_inside(row, col) and board.get(row, col) == opponent:
        captured.append((row, col))
        row += d_row
        col += d_col
    return captured


def get_captures_by_approach(board: Board, player: int, from_pos: tuple, to_pos: tuple) -> list[tuple]:
    """
    Captura por APROXIMACAO: ao mover de from_pos para to_pos, olhamos
    na MESMA direcao do movimento, a partir de to_pos, e capturamos as
    pecas do adversario encontradas em sequencia.
    """
    direction = get_move_direction(from_pos, to_pos)
    if direction is None:
        return []
    return _scan_line_for_captures(board, player, to_pos, direction)


def get_captures_by_withdrawal(board: Board, player: int, from_pos: tuple, to_pos: tuple) -> list[tuple]:
    """
    Captura por AFASTAMENTO: ao mover de from_pos para to_pos, olhamos
    na direcao OPOSTA ao movimento, a partir de from_pos (a casa que
    a peca acabou de deixar), e capturamos as pecas do adversario
    encontradas em sequencia se afastando dali.
    """
    direction = get_move_direction(from_pos, to_pos)
    if direction is None:
        return []
    return _scan_line_for_captures(board, player, from_pos, OPPOSITE_DIRECTION[direction])


def has_capture_available(board: Board, player: int) -> bool:
    """
    Verifica se existe QUALQUER movimento, de QUALQUER peca do
    'player', que resultaria em captura na posicao atual do tabuleiro.

    Usada para aplicar a regra de CAPTURA OBRIGATORIA do Fanorona: se
    isso for True, o jogador nao pode fazer um movimento livre (sem
    captura) -- e obrigado a escolher uma das jogadas que capturam.

    Fato conhecido do jogo: na posicao inicial, esta funcao ja retorna
    True para o primeiro jogador (o primeiro lance do Fanorona nunca
    e livre).
    """
    for row in range(ROWS):
        for col in range(COLS):
            if board.get(row, col) != player:
                continue
            for direction in get_valid_directions(board, row, col):
                d_row, d_col = DIRECTIONS[direction]
                to_pos = (row + d_row, col + d_col)
                if not board.is_inside(*to_pos) or board.get(*to_pos) != EMPTY:
                    continue
                from_pos = (row, col)
                if get_captures_by_approach(board, player, from_pos, to_pos) or \
                   get_captures_by_withdrawal(board, player, from_pos, to_pos):
                    return True
    return False


def apply_move(board: Board, player: int, from_pos: tuple, to_pos: tuple,
                capture_type: str | None = None) -> list[tuple]:
    """
    Aplica um movimento no tabuleiro: valida, move a peca e remove as
    pecas capturadas.

    capture_type: quando AMBAS as capturas (aproximacao e afastamento)
    sao possiveis no mesmo movimento, o jogador precisa escolher qual
    das duas aplicar -- passe "approach" ou "withdrawal". Se so uma
    das duas for possivel, capture_type e ignorado (a disponivel e
    usada automaticamente). Se nenhuma for possivel, o movimento e
    so um movimento simples (sem captura) -- MAS SO E PERMITIDO se
    nao houver NENHUMA captura disponivel em nenhuma peca do jogador
    (regra de captura obrigatoria, ver has_capture_available).

    Retorna a lista de posicoes capturadas nesse movimento (pode ser
    vazia, se o movimento nao capturou nada).

    Levanta InvalidMoveError se:
      - o movimento nao for valido:
      - ambas capturas forem possiveis e capture_type nao foi informado;
      - o movimento nao captura nada, mas existe captura obrigatoria
        disponivel em outra jogada.
    """
    if not is_valid_move(board, player, from_pos, to_pos):
        raise InvalidMoveError(f"Movimento invalido: {from_pos} -> {to_pos}")

    approach = get_captures_by_approach(board, player, from_pos, to_pos)
    withdrawal = get_captures_by_withdrawal(board, player, from_pos, to_pos)

    if approach and withdrawal:
        if capture_type == "approach":
            captured = approach
        elif capture_type == "withdrawal":
            captured = withdrawal
        else:
            raise InvalidMoveError(
                "Este movimento permite captura por aproximacao OU por "
                "afastamento -- e preciso escolher qual das duas (capture_type)."
            )
    elif approach:
        captured = approach
    elif withdrawal:
        captured = withdrawal
    else:
        captured = []

    if not captured and has_capture_available(board, player):
        raise InvalidMoveError(
            "Captura obrigatoria: existe pelo menos uma jogada que captura "
            "pecas do adversario nesta posicao -- voce precisa capturar, "
            "nao pode fazer um movimento livre."
        )

    move_piece(board, from_pos, to_pos)
    for row, col in captured:
        board.set(row, col, EMPTY)

    return captured


def has_more_captures(board: Board, player: int, pos: tuple, arrived_from_direction: str | None) -> bool:
    """
    Depois de uma captura, verifica se a MESMA peca (agora em 'pos')
    pode continuar capturando em outra direcao.

    Regra do Fanorona: a peca NAO pode continuar na mesma direcao
    usada no passo anterior, nem voltar pela direcao oposta (ou seja,
    nao pode "ir e voltar" pelo mesmo caminho). As demais direcoes
    validas para o ponto sao permitidas, desde que levem a uma casa
    vazia e resultem em captura (por aproximacao ou afastamento).
    """
    row, col = pos
    forbidden = {arrived_from_direction, OPPOSITE_DIRECTION.get(arrived_from_direction)}

    for direction in get_valid_directions(board, row, col):
        if direction in forbidden:
            continue

        d_row, d_col = DIRECTIONS[direction]
        to_pos = (row + d_row, col + d_col)

        if not board.is_inside(*to_pos) or board.get(*to_pos) != EMPTY:
            continue

        if get_captures_by_approach(board, player, pos, to_pos) or \
           get_captures_by_withdrawal(board, player, pos, to_pos):
            return True

    return False


def check_winner(board: Board) -> int | None:
    """
    Retorna PLAYER_ONE ou PLAYER_TWO se um dos jogadores tiver ficado
    sem pecas, ou None se o jogo continua.

    Nota: a regra completa do Fanorona tambem da vitoria a quem
    imobiliza o adversario (sem nenhum movimento valido possivel).
    
    """
    if board.count_pieces(PLAYER_ONE) == 0:
        return PLAYER_TWO
    if board.count_pieces(PLAYER_TWO) == 0:
        return PLAYER_ONE
    return None