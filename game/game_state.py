"""
game_state.py
-------------
O "maestro" do jogo: e a UNICA parte do projeto que conhece rede, GUI
e regras ao mesmo tempo. As outras camadas nunca se falam diretamente:

    GUI  <-->  GameController  <-->  Peer (RMI/RPC via Pyro5)
                     |
                     v
                   Board / rules

Fluxo de uma jogada feita pelo jogador LOCAL:
    1. GUI detecta 2 cliques (origem e destino) e chama
       controller.try_local_move(from_pos, to_pos)
    2. Controller valida e aplica com rules.apply_move (que ja cuida
       de mover a peca e remover capturas)
    3. Se a jogada capturou algo e a MESMA peca ainda pode continuar
       capturando (rules.has_more_captures), o turno NAO passa -- o
       jogador precisa continuar jogando com essa peca (pending_capture)
    4. Manda a jogada pela rede (incluindo qual tipo de captura foi
       escolhido, se havia ambiguidade) e pede pra GUI redesenhar
    5. Se invalido: avisa a GUI para mostrar um erro (sem mexer na rede)

Fluxo de uma jogada RECEBIDA do oponente: espelha o fluxo local, mas
sem reenviar pela rede -- so aplica no tabuleiro local.
"""

from game.board import Board, PLAYER_ONE, PLAYER_TWO
from game import rules


class GameController:
    def __init__(self, my_player: int, peer, starting_player: int = PLAYER_ONE,
                 on_board_changed=None,
                 on_chat_message=None, on_game_over=None, on_invalid_move=None,
                 on_capture_choice_needed=None, on_turn_changed=None):
        """
        my_player: PLAYER_ONE ou PLAYER_TWO -- quem SOU EU nesta maquina
                   (o Host recebe PLAYER_ONE, o Convidado recebe
                   PLAYER_TWO, conforme definido no handshake
                   registrar_adversario da camada de rede)
        peer: instancia de FanoronaPeer (network/peer.py), ja conectada.
              O controller chama peer.send_move / send_chat / send_resign
              para falar com o adversario e liga nos callbacks do peer
              (on_move, on_chat, on_resign, on_disconnect) para ouvir
              o que vem de la. O resto (host_start / guest_connect) e
              responsabilidade do main.py
        starting_player: quem joga primeiro (o Host sorteia e informa o
                         Convidado no handshake)
        on_board_changed: callback chamado como on_board_changed(board)
                           sempre que o tabuleiro mudar -- a GUI usa
                           isso pra saber quando redesenhar
        on_chat_message: callback chamado como on_chat_message(text)
                          quando chega uma mensagem de chat do oponente
        on_game_over: callback chamado como on_game_over(winner_player)
        on_invalid_move: callback chamado como on_invalid_move(motivo)
                          quando o jogador LOCAL tenta uma jogada invalida
        on_turn_changed: callback chamado como on_turn_changed(current_turn)
                          toda vez que o turno passa de um jogador para o
                          outro -- a GUI usa isso pra saber a hora certa de
                          mostrar o popup de "Sua vez!" (so quando o turno
                          MUDA de verdade, nao durante uma sequencia de
                          capturas com a mesma peca).
        on_capture_choice_needed: callback chamado como
                          on_capture_choice_needed(from_pos, to_pos) quando
                          um movimento permite AMBAS capturas (aproximacao
                          e afastamento) e o jogador precisa escolher.
                          Deve retornar "approach" ou "withdrawal".
                          Por padrao (sem GUI escolhendo), usa sempre
                          "approach" -- da pra melhorar depois com um
                          popup na interface perguntando ao jogador.
        """
        self.board = Board()
        self.my_player = my_player
        self.current_turn = starting_player  # sorteado pelo Host no handshake
        self.peer = peer

        # Quando uma captura permite continuar capturando com a MESMA
        # peca (sequencia de capturas), guardamos aqui a posicao dessa
        # peca e a direcao usada no ultimo passo -- enquanto isso nao
        # for None, o jogador so pode mover ESSA peca, e o turno nao passa.
        self.pending_capture_pos: tuple | None = None
        self._pending_capture_direction: str | None = None

        # Quantas pecas do adversario cada jogador ja capturou ate agora.
        # Ex: self.captures[PLAYER_ONE] = pecas que o Jogador 1 capturou.
        self.captures: dict[int, int] = {PLAYER_ONE: 0, PLAYER_TWO: 0}

        self.on_board_changed = on_board_changed or (lambda board: None)
        self.on_chat_message = on_chat_message or (lambda text: None)
        self.on_game_over = on_game_over or (lambda winner: None)
        self.on_invalid_move = on_invalid_move or (lambda reason: None)
        self.on_turn_changed = on_turn_changed or (lambda current_turn: None)
        self.on_capture_choice_needed = on_capture_choice_needed or (
            lambda from_pos, to_pos: "approach"
        )
        # Chamado quando o adversario cai / some da rede (preenchido pelo main.py)
        self.on_connection_lost = lambda: None

        # Liga o que vem do adversario (metodos remotos chamados no peer)
        # aos handlers deste controller. Os lambdas buscam o callback so na
        # hora da chamada, porque a GUI troca on_chat_message / on_game_over
        # depois que o controller e criado.
        self.peer.on_move = self._apply_remote_move
        self.peer.on_chat = lambda text: self.on_chat_message(text)
        self.peer.on_resign = self._on_remote_resign
        self.peer.on_disconnect = lambda: self.on_connection_lost()

    # ------------------------------------------------------------------
    # Chamado pela GUI quando o jogador LOCAL tenta fazer uma jogada
    # ------------------------------------------------------------------
    def try_local_move(self, from_pos: tuple, to_pos: tuple) -> None:
        if self.current_turn != self.my_player:
            self.on_invalid_move("Nao e a sua vez.")
            return

        if self.pending_capture_pos is not None and from_pos != self.pending_capture_pos:
            self.on_invalid_move("Voce precisa continuar capturando com a mesma peca.")
            return

        if not rules.is_valid_move(self.board, self.my_player, from_pos, to_pos):
            self.on_invalid_move("Movimento nao permitido.")
            return

        # Descobre se ha ambiguidade de captura (aproximacao E afastamento
        # possiveis) ANTES de aplicar, para poder perguntar a escolha.
        approach = rules.get_captures_by_approach(self.board, self.my_player, from_pos, to_pos)
        withdrawal = rules.get_captures_by_withdrawal(self.board, self.my_player, from_pos, to_pos)

        capture_type = None
        if approach and withdrawal:
            capture_type = self.on_capture_choice_needed(from_pos, to_pos)

        try:
            captured = rules.apply_move(self.board, self.my_player, from_pos, to_pos, capture_type)
        except rules.InvalidMoveError as error:
            self.on_invalid_move(str(error))
            return

        self.peer.send_move(from_pos, to_pos, capture_type)

        self._finish_move(from_pos, to_pos, captured)

    # ------------------------------------------------------------------
    # Chamado pelo chat da GUI
    # ------------------------------------------------------------------
    def send_chat(self, text: str) -> None:
        self.peer.send_chat(text)

    def resign(self) -> None:
        self.peer.send_resign()
        opponent = PLAYER_TWO if self.my_player == PLAYER_ONE else PLAYER_ONE
        self.on_game_over(opponent)

    # ------------------------------------------------------------------
    # Tudo que vem do oponente chega por callbacks do peer (ligados no
    # __init__): cada metodo remoto chamado la (receber_jogada,
    # receber_chat, desistir) cai direto no handler correspondente.
    # Nao existe mais um "on_network_message" com if/elif por tipo.
    # ------------------------------------------------------------------
    def _on_remote_resign(self) -> None:
        self.on_game_over(self.my_player)  # o oponente desistiu, eu venci

    def _apply_remote_move(self, from_pos: tuple, to_pos: tuple, capture_type: str | None) -> None:
        opponent = PLAYER_TWO if self.my_player == PLAYER_ONE else PLAYER_ONE
        try:
            captured = rules.apply_move(self.board, opponent, from_pos, to_pos, capture_type)
        except rules.InvalidMoveError as error:
            # Isso so aconteceria se os dois lados ficassem com o tabuleiro
            # dessincronizado (ex: mensagem perdida) -- nao deveria ocorrer
            # em uso normal, mas evitamos travar o jogo se acontecer.
            print(f"[game_state] Jogada remota invalida recebida: {error}")
            return

        self._finish_move(from_pos, to_pos, captured, is_local=False)

    def _finish_move(self, from_pos: tuple, to_pos: tuple, captured: list, is_local: bool = True) -> None:
        """
        Parte comum entre jogada local e remota: decide se a sequencia
        de capturas continua, troca o turno (ou nao), avisa a GUI e
        checa se o jogo acabou.
        """
        player = self.my_player if is_local else (
            PLAYER_TWO if self.my_player == PLAYER_ONE else PLAYER_ONE
        )
        direction = rules.get_move_direction(from_pos, to_pos)

        if captured:
            self.captures[player] += len(captured)

        if captured and rules.has_more_captures(self.board, player, to_pos, direction):
            # A mesma peca pode continuar capturando -- turno NAO passa.
            self.pending_capture_pos = to_pos
            self._pending_capture_direction = direction
        else:
            self.pending_capture_pos = None
            self._pending_capture_direction = None
            self._switch_turn()

        self.on_board_changed(self.board)

        winner = rules.check_winner(self.board)
        if winner is not None:
            self.on_game_over(winner)

    def _switch_turn(self) -> None:
        self.current_turn = PLAYER_TWO if self.current_turn == PLAYER_ONE else PLAYER_ONE
        self.on_turn_changed(self.current_turn)