"""
test_movement.py
-----------------
Testa as regras de MOVIMENTO (sem captura ainda) diretamente, sem
precisar abrir a GUI nem subir rede: cria um GameController "fake"
(sem rede real) e testa jogadas validas e invalidas.

Rode com: python test_movement.py
"""

from game.board import Board, PLAYER_ONE, PLAYER_TWO, EMPTY
from game import rules


def test_get_valid_directions():
    b = Board()
    # (0,0): soma par -> tem diagonal
    assert set(rules.get_valid_directions(b, 0, 0)) == {"N", "S", "L", "O", "NE", "NO", "SE", "SO"}
    # (0,1): soma impar -> so retas
    assert set(rules.get_valid_directions(b, 0, 1)) == {"N", "S", "L", "O"}
    print("[OK] get_valid_directions")


def test_valid_straight_move():
    b = Board()
    # Peca do Jogador 1 em (1, 1) pode mover para (2, 1)? (2,1) esta ocupado
    # no setup inicial (linha do meio, lado do Jogador 1) -- vamos usar um
    # ponto vazio de verdade: o centro (2, 4) esta vazio.
    # Peca do Jogador 1 em (1, 4) pode mover reto para (2, 4) (vazio).
    assert b.get(1, 4) == PLAYER_ONE
    assert b.get(2, 4) == EMPTY
    assert rules.is_valid_move(b, PLAYER_ONE, (1, 4), (2, 4)) is True
    print("[OK] movimento reto valido")


def test_valid_diagonal_move():
    b = Board()
    # (1, 4) tem soma 5 (impar) -> SEM diagonal. Vamos testar um ponto
    # com diagonal: (1, 3), soma 4 (par) -> TEM diagonal.
    # (1, 3) e do Jogador 1. Diagonal SE leva a (2, 4), que esta vazio.
    assert Board.has_diagonal(1, 3) is True
    assert b.get(1, 3) == PLAYER_ONE
    assert b.get(2, 4) == EMPTY
    assert rules.is_valid_move(b, PLAYER_ONE, (1, 3), (2, 4)) is True
    print("[OK] movimento diagonal valido (ponto com diagonal)")


def test_invalid_diagonal_on_point_without_diagonal():
    b = Board()
    # (1, 4) NAO tem diagonal (soma impar). Tentar mover na diagonal
    # SE, de (1,4) para (2,5), deve ser invalido mesmo (2,5) estando
    # ocupado ou nao -- a direcao em si ja e invalida nesse ponto.
    assert Board.has_diagonal(1, 4) is False
    assert rules.is_valid_move(b, PLAYER_ONE, (1, 4), (2, 5)) is False
    print("[OK] diagonal bloqueada em ponto sem diagonal")


def test_invalid_move_to_occupied_cell():
    b = Board()
    # (1, 0) do Jogador 1 tentando mover para (0, 0), que ja tem peca
    # do proprio Jogador 1 -- destino ocupado, deve ser invalido.
    assert rules.is_valid_move(b, PLAYER_ONE, (1, 0), (0, 0)) is False
    print("[OK] movimento para casa ocupada bloqueado")


def test_invalid_move_wrong_player():
    b = Board()
    # (1, 4) e do Jogador 1 -- o Jogador 2 nao pode mover essa peca.
    assert rules.is_valid_move(b, PLAYER_TWO, (1, 4), (2, 4)) is False
    print("[OK] jogador nao pode mover peca do adversario")


def test_invalid_move_too_far():
    b = Board()
    # Tentar mover 2 casas de uma vez (nao e 1 passo) deve ser invalido.
    assert rules.is_valid_move(b, PLAYER_ONE, (0, 0), (2, 0)) is False
    print("[OK] movimento de mais de 1 passo bloqueado")


def test_move_piece_executes():
    b = Board()
    rules.move_piece(b, (1, 4), (2, 4))
    assert b.get(1, 4) == EMPTY
    assert b.get(2, 4) == PLAYER_ONE
    print("[OK] move_piece move a peca corretamente")


def test_full_turn_via_game_controller():
    """Simula um turno completo, como a GUI faria, usando GameController."""
    from game.game_state import GameController

    class FakeNetwork:
        def __init__(self):
            self.sent = []

        def send(self, msg_type, data):
            self.sent.append((msg_type, data))

    net = FakeNetwork()
    controller = GameController(my_player=PLAYER_ONE, network=net)

    board_changed = {"called": False}
    controller.on_board_changed = lambda board: board_changed.update(called=True)

    controller.try_local_move((1, 4), (2, 4))

    assert controller.board.get(2, 4) == PLAYER_ONE
    assert controller.board.get(1, 4) == EMPTY
    assert controller.current_turn == PLAYER_TWO  # turno trocou
    assert net.sent == [("move", {"from": [1, 4], "to": [2, 4], "capture_type": None})]
    assert board_changed["called"] is True
    print("[OK] GameController.try_local_move (turno completo, incl. troca de turno e envio pela rede)")


def test_cannot_move_out_of_turn():
    from game.game_state import GameController

    class FakeNetwork:
        def send(self, msg_type, data):
            pass

    controller = GameController(my_player=PLAYER_TWO, network=FakeNetwork())
    # current_turn comeca como PLAYER_ONE, mas eu sou PLAYER_TWO -> deve barrar
    invalid_reason = {}
    controller.on_invalid_move = lambda reason: invalid_reason.update(reason=reason)

    controller.try_local_move((3, 4), (2, 4))

    assert invalid_reason.get("reason") == "Nao e a sua vez."
    assert controller.board.get(3, 4) == PLAYER_TWO  # nada mudou no tabuleiro
    print("[OK] bloqueia jogada fora de turno")


if __name__ == "__main__":
    test_get_valid_directions()
    test_valid_straight_move()
    test_valid_diagonal_move()
    test_invalid_diagonal_on_point_without_diagonal()
    test_invalid_move_to_occupied_cell()
    test_invalid_move_wrong_player()
    test_invalid_move_too_far()
    test_move_piece_executes()
    test_full_turn_via_game_controller()
    test_cannot_move_out_of_turn()
    print("\n[OK] TODOS OS TESTES DE MOVIMENTO PASSARAM")