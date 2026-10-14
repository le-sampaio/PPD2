"""
main.py
-------
Ponto de entrada do jogo. Ordem de execucao:

    1. Abre a janela com a tela de menu (Host / Convidado).
    2. Quando o jogador escolhe um dos dois, cria um FanoronaPeer
       (network/peer.py) e sobe a comunicacao RMI/RPC (Pyro5):
         - Host: host_start() abre a porta e NAO bloqueia; quando o
           Convidado chega, o peer chama on_guest_joined.
         - Convidado: guest_connect() bloqueia ate o handshake terminar,
           por isso roda em uma thread separada.
    3. Assim que o handshake termina, cria o GameController
       (game/game_state.py) e manda a GUI trocar para o tabuleiro.

Nenhum IP ou porta fica fixo no codigo: tudo vem do que o usuario
digita no menu (o Host ve o proprio IP na tela para passar ao adversario).

Detalhe importante de concorrencia:
    O Tkinter NAO e thread-safe. Os metodos remotos chegam em threads
    do Pyro, entao o peer recebe schedule=lambda fn: app.after(0, fn):
    todo callback de rede e agendado na thread principal da GUI.
"""

import random
import threading
import traceback
from tkinter import messagebox

from gui.app import FanoronaApp
from network.peer import FanoronaPeer, get_local_ip
from game.board import PLAYER_ONE, PLAYER_TWO
from game.game_state import GameController


def main():
    app = FanoronaApp()

    def new_peer() -> FanoronaPeer:
        # Um peer novo por tentativa: se a conexao falhar, nada fica "sujo".
        return FanoronaPeer(schedule=lambda fn: app.after(0, fn))

    def start_game(peer: FanoronaPeer, my_player: int, starting_player: int) -> None:
        print(f"[main] Handshake concluido: voce e o Jogador {my_player}, "
              f"o Jogador {starting_player} comeca. Abrindo o tabuleiro...")
        try:
            controller = GameController(
                my_player=my_player,
                peer=peer,
                starting_player=starting_player,
            )
            controller.on_connection_lost = lambda: messagebox.showwarning(
                "Conexao perdida", "O adversario desconectou."
            )
            app.show_board(controller)
        except Exception as error:  # nao deixar a tela parada sem explicacao
            traceback.print_exc()
            messagebox.showerror("Erro ao abrir o tabuleiro", f"{type(error).__name__}: {error}")

    def start_as_host(port: int) -> None:
        peer = new_peer()
        # O Host sorteia quem comeca; o Convidado descobre pelo retorno
        # de registrar_adversario.
        starting_player = random.choice([PLAYER_ONE, PLAYER_TWO])

        # Chamado (na thread da GUI) quando o Convidado se registra.
        peer.on_guest_joined = lambda starting: start_game(peer, PLAYER_ONE, starting)

        try:
            peer.host_start(port, starting_player)
        except OSError as error:  # ex: porta ja em uso
            app.show_menu_status(f"Nao foi possivel abrir a porta {port}: {error}")
            return
        app.show_menu_status(
            f"Aguardando o adversario... Informe a ele o IP {get_local_ip()} e a porta {port}."
        )

    def start_as_guest(ip: str, port: int) -> None:
        peer = new_peer()

        def connect_in_background() -> None:
            try:
                info = peer.guest_connect(ip, port)  # bloqueia ate o handshake
            except Exception as error:  # CommunicationError, OSError, erro do host...
                message = f"Nao foi possivel conectar em {ip}:{port}: {error}"
                print(f"[main] {message}")
                app.after(0, lambda: app.show_menu_status(message))
                peer.close()
                return
            app.after(0, lambda: start_game(
                peer, info["your_player"], info["starting_player"]
            ))

        threading.Thread(target=connect_in_background, daemon=True).start()

    # Liga os botoes da tela de menu as funcoes acima
    app.on_host_requested = start_as_host
    app.on_join_requested = start_as_guest

    app.mainloop()


if __name__ == "__main__":
    main()