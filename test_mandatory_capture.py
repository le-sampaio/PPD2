"""
test_mandatory_capture.py
--------------------------
Testa a regra de CAPTURA OBRIGATORIA: se existe qualquer jogada que
capture uma peca do adversario, o jogador NAO pode fazer um movimento
livre (sem captura) -- precisa escolher uma jogada que capture.

Rode com: python test_mandatory_capture.py
"""

from game.board import Board, PLAYER_ONE, PLAYER_TWO, EMPTY, ROWS, COLS
from game import rules


def empty_board() -> Board:
    board = Board()
    for row in range(ROWS):
        for col in range(COLS):
            board.set(row, col, EMPTY)
    return board


def test_no_capture_available_allows_free_move():
    b = empty_board()
    b.set(2, 2, PLAYER_ONE)
    # Nenhuma peca do adversario no tabuleiro -- movimento livre deve ser permitido.
    assert rules.has_capture_available(b, PLAYER_ONE) is False
    result = rules.apply_move(b, PLAYER_ONE, (2, 2), (2, 3))
    assert result == []
    print("[OK] movimento livre permitido quando nao ha captura disponivel")


def test_free_move_blocked_when_capture_available_elsewhere():
    b = empty_board()
    # Peca A: pode fazer um movimento livre (sem ninguem por perto)
    b.set(0, 0, PLAYER_ONE)
    # Peca B: tem uma captura disponivel por aproximacao
    b.set(2, 2, PLAYER_ONE)
    b.set(2, 4, PLAYER_TWO)
    b.set(2, 5, PLAYER_TWO)

    assert rules.has_capture_available(b, PLAYER_ONE) is True

    # Tentar mover a Peca A (movimento livre) deve ser BLOQUEADO, porque
    # a Peca B tem uma captura obrigatoria disponivel.
    try:
        rules.apply_move(b, PLAYER_ONE, (0, 0), (0, 1))
        assert False, "deveria ter bloqueado o movimento livre"
    except rules.InvalidMoveError as error:
        assert "obrigat" in str(error).lower()

    # A Peca A nao deve ter se movido (o apply_move deve falhar ANTES de mexer no tabuleiro)
    assert b.get(0, 0) == PLAYER_ONE
    assert b.get(0, 1) == EMPTY

    # Mas mover a Peca B fazendo a captura deve funcionar normalmente.
    captured = rules.apply_move(b, PLAYER_ONE, (2, 2), (2, 3))
    assert set(captured) == {(2, 4), (2, 5)}
    print("[OK] movimento livre bloqueado quando ha captura obrigatoria em outra peca")


def test_initial_position_has_forced_capture():
    """
    Fato conhecido do Fanorona: na posicao inicial, o primeiro jogador
    (Jogador 1) SEMPRE tem uma captura disponivel -- o primeiro lance
    do jogo nunca e livre.
    """
    b = Board()
    assert rules.has_capture_available(b, PLAYER_ONE) is True

    # Um movimento livre bobo (que nao captura nada) deve ser bloqueado
    # logo no primeiro lance da partida.
    try:
        rules.apply_move(b, PLAYER_ONE, (0, 0), (0, 1))
        assert False, "primeiro lance deveria ser obrigatoriamente uma captura"
    except rules.InvalidMoveError:
        pass

    print("[OK] posicao inicial forca captura no primeiro lance (fato conhecido do jogo real)")


def test_game_controller_rejects_free_move_when_capture_available():
    from game.game_state import GameController

    class FakeNetwork:
        def send(self, msg_type, data):
            pass

    controller = GameController(my_player=PLAYER_ONE, network=FakeNetwork())
    controller.board = empty_board()
    controller.board.set(0, 0, PLAYER_ONE)
    controller.board.set(2, 2, PLAYER_ONE)
    controller.board.set(2, 4, PLAYER_TWO)
    controller.board.set(2, 5, PLAYER_TWO)
    controller.current_turn = PLAYER_ONE

    invalid = {}
    controller.on_invalid_move = lambda reason: invalid.update(reason=reason)

    controller.try_local_move((0, 0), (0, 1))

    assert "obrigat" in invalid.get("reason", "").lower()
    assert controller.board.get(0, 0) == PLAYER_ONE  # nao se moveu
    assert controller.current_turn == PLAYER_ONE      # turno nao passou
    print("[OK] GameController repassa o erro de captura obrigatoria para a GUI")


if __name__ == "__main__":
    test_no_capture_available_allows_free_move()
    test_free_move_blocked_when_capture_available_elsewhere()
    test_initial_position_has_forced_capture()
    test_game_controller_rejects_free_move_when_capture_available()
    print("\n[OK] TODOS OS TESTES DE CAPTURA OBRIGATORIA PASSARAM")