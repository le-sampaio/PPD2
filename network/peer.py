"""
peer.py
-------
Camada de comunicacao do Fanorona usando RMI/RPC (Pyro5).

Substitui server.py, client.py e protocol.py do primeiro trabalho.

Ideia central: cada tabuleiro e, ao mesmo tempo, SERVIDOR e CLIENTE.
    - Como SERVIDOR: expoe um objeto remoto (FanoronaRemote) cujos
      metodos o ADVERSARIO chama (receber_jogada, receber_chat, ...).
    - Como CLIENTE: guarda um Proxy para o objeto remoto do adversario
      e chama os metodos dele (send_move, send_chat, ...).

Equivalencia com o exemplo Java do professor:
    InverterItf / UnicastRemoteObject -> classe FanoronaRemote com @expose
    Naming.rebind(...)                -> daemon.register(obj, objectId=...)
    Naming.lookup(...)                -> Pyro5.api.Proxy(uri)
    RemoteException                   -> Pyro5.errors.CommunicationError

Handshake (no lugar do "welcome" por socket):
    1. O HOST sobe um daemon na porta escolhida e fica esperando.
    2. O CONVIDADO sobe o proprio daemon, localiza o objeto do host pelo
       IP e porta digitados pelo usuario e chama
       registrar_adversario(minha_uri), passando a referencia remota dele.
    3. O host guarda um Proxy para essa URI (assim consegue chamar o
       convidado de volta) e RETORNA {your_player, starting_player}.

Concorrencia:
    - Chamadas RECEBIDAS chegam em threads do Pyro. Elas nunca mexem na
      GUI direto: so agendam o trabalho via 'schedule' (app.after(0, ...))
      e retornam na hora.
    - Chamadas ENVIADAS passam por uma fila (_outbox) consumida por UMA
      thread. Assim a GUI nao trava se a rede demorar, e a ordem das
      mensagens e preservada (importante em sequencias de capturas).
"""

import queue
import socket
import threading

import Pyro5.api
import Pyro5.errors

# Nome do objeto remoto dentro do daemon. NAO e IP nem porta: e so o
# "nome" do objeto, igual ao "InverterRef" do exemplo em Java.
OBJECT_ID = "fanorona"

# Tempo maximo (segundos) esperando o adversario responder a uma chamada.
CALL_TIMEOUT = 5


def get_local_ip(toward: str | None = None) -> str:
    """
    Descobre o IP desta maquina na rede local, para MOSTRAR ao usuario
    (host) ou para montar a propria URI (convidado).

    Usa um socket UDP "conectado" so para o sistema operacional escolher
    a interface de rede certa -- nenhum dado e enviado. A comunicacao do
    jogo em si e toda feita via Pyro5.

    toward: IP do outro lado; se informado, devolve o IP da interface
            usada para alcanca-lo.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((toward or "10.255.255.255", 9))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"  # sem rede nenhuma: so serve para teste local
    finally:
        sock.close()


@Pyro5.api.expose
class FanoronaRemote:
    """
    Objeto REMOTO: os metodos publicos daqui sao os que o adversario
    chama pela rede (equivale a interface InverterItf + Servidor do
    exemplo em Java). Cada tipo de mensagem do protocolo antigo virou
    um metodo.
    """

    def __init__(self, peer: "FanoronaPeer"):
        self._peer = peer  # privado (comeca com _): nao e exposto na rede

    def registrar_adversario(self, uri_do_convidado: str) -> dict:
        """Chamado pelo CONVIDADO no host. Retorna os dados de inicio."""
        return self._peer._handle_register(uri_do_convidado)

    def receber_jogada(self, origem: list, destino: list, tipo_captura) -> None:
        self._peer._dispatch("on_move", tuple(origem), tuple(destino), tipo_captura)

    def receber_chat(self, texto: str) -> None:
        self._peer._dispatch("on_chat", texto)

    def desistir(self) -> None:
        self._peer._dispatch("on_resign")


class FanoronaPeer:
    def __init__(self, schedule=None):
        """
        schedule: funcao que recebe uma funcao sem argumentos e a executa
                  na thread da GUI. Em main.py: lambda fn: app.after(0, fn).
                  Sem GUI (testes no terminal), executa direto.
        """
        self._schedule = schedule or (lambda fn: fn())

        # Callbacks (preenchidos pelo GameController / main.py).
        # Sao sempre chamados via schedule, ou seja, na thread da GUI.
        self.on_move = lambda from_pos, to_pos, capture_type: None
        self.on_chat = lambda text: None
        self.on_resign = lambda: None
        self.on_disconnect = lambda: None
        self.on_guest_joined = lambda starting_player: None  # so o host usa

        self._daemon: Pyro5.api.Daemon | None = None
        self._opponent: Pyro5.api.Proxy | None = None
        self._opponent_lock = threading.Lock()
        self._starting_player: int | None = None

        self._outbox: queue.Queue = queue.Queue()
        self._running = False

    # ------------------------------------------------------------------
    # Inicio como HOST (Jogador 1): nao bloqueia
    # ------------------------------------------------------------------
    def host_start(self, port: int, starting_player: int) -> None:
        """
        Sobe o daemon na porta escolhida e fica esperando o convidado.
        Quando ele chegar, on_guest_joined(starting_player) e chamado.
        """
        self._starting_player = starting_player
        self._daemon = Pyro5.api.Daemon(host="0.0.0.0", port=port)
        self._daemon.register(FanoronaRemote(self), objectId=OBJECT_ID)
        threading.Thread(target=self._daemon.requestLoop, daemon=True).start()

    def _handle_register(self, guest_uri: str) -> dict:
        """Roda numa thread do Pyro, quando o convidado se apresenta."""
        proxy = Pyro5.api.Proxy(guest_uri)
        proxy._pyroTimeout = CALL_TIMEOUT
        with self._opponent_lock:
            if self._opponent is not None:
                raise RuntimeError("Esta partida ja tem dois jogadores.")
            self._opponent = proxy
        self._start_sender()
        self._schedule(lambda: self.on_guest_joined(self._starting_player))
        return {"your_player": 2, "starting_player": self._starting_player}

    # ------------------------------------------------------------------
    # Inicio como CONVIDADO (Jogador 2): bloqueia ate o handshake acabar
    # ------------------------------------------------------------------
    def guest_connect(self, host_ip: str, host_port: int) -> dict:
        """
        Conecta no host e devolve {"your_player": 2, "starting_player": N}.
        Bloqueia -- chame de uma thread separada, nunca da thread da GUI.
        Levanta Pyro5.errors.CommunicationError se nao conseguir conectar.
        """
        # O convidado tambem precisa ser alcancavel, para o host chama-lo.
        my_ip = get_local_ip(toward=host_ip)
        self._daemon = Pyro5.api.Daemon(host=my_ip)  # porta escolhida pelo SO
        my_uri = self._daemon.register(FanoronaRemote(self), objectId=OBJECT_ID)
        threading.Thread(target=self._daemon.requestLoop, daemon=True).start()

        host_proxy = Pyro5.api.Proxy(f"PYRO:{OBJECT_ID}@{host_ip}:{host_port}")
        host_proxy._pyroTimeout = CALL_TIMEOUT
        with self._opponent_lock:
            self._opponent = host_proxy

        info = host_proxy.registrar_adversario(str(my_uri))
        self._start_sender()
        return info

    # ------------------------------------------------------------------
    # Envio (chamado pelo GameController): so enfileira, nao bloqueia
    # ------------------------------------------------------------------
    def send_move(self, from_pos: tuple, to_pos: tuple, capture_type) -> None:
        self._outbox.put(("receber_jogada", (list(from_pos), list(to_pos), capture_type)))

    def send_chat(self, text: str) -> None:
        self._outbox.put(("receber_chat", (text,)))

    def send_resign(self) -> None:
        self._outbox.put(("desistir", ()))

    def _start_sender(self) -> None:
        self._running = True
        threading.Thread(target=self._sender_loop, daemon=True).start()

    def _sender_loop(self) -> None:
        """Unica thread que fala com o adversario: preserva a ordem."""
        while self._running:
            method_name, args = self._outbox.get()
            if method_name is None:  # sinal de encerramento (close)
                break
            try:
                with self._opponent_lock:
                    # Um Proxy do Pyro5 pertence a thread que o usou por
                    # ultimo. Ele foi criado/usado em outra thread (handshake),
                    # entao esta thread assume a posse antes de chamar.
                    self._opponent._pyroClaimOwnership()
                    getattr(self._opponent, method_name)(*args)
            except Pyro5.errors.CommunicationError:
                self._running = False
                self._schedule(lambda: self.on_disconnect())
                break
            except Exception as error:  # erro levantado pelo metodo remoto
                print(f"[peer] Erro na chamada remota {method_name}: {error}")

    # ------------------------------------------------------------------
    # Recebimento (chamado pelas threads do Pyro via FanoronaRemote)
    # ------------------------------------------------------------------
    def _dispatch(self, callback_name: str, *args) -> None:
        # O callback e buscado so na hora de executar (na thread da GUI),
        # entao nao se perde mensagem que chegue antes do controller ligar
        # seus handlers: as chamadas agendadas rodam em ordem.
        self._schedule(lambda: getattr(self, callback_name)(*args))

    def close(self) -> None:
        self._running = False
        self._outbox.put((None, ()))
        if self._daemon is not None:
            self._daemon.shutdown()
        if self._opponent is not None:
            with self._opponent_lock:
                self._opponent._pyroClaimOwnership()
                self._opponent._pyroRelease()


if __name__ == "__main__":
    # Teste de chat pelo terminal, sem GUI nem jogo:
    #   maquina A:  python peer.py host <porta>
    #   maquina B:  python peer.py join <ip_do_host> <porta>
    import sys

    if len(sys.argv) < 3 or (sys.argv[1] == "join" and len(sys.argv) < 4):
        print("Uso:\n  python peer.py host <porta>\n  python peer.py join <ip_do_host> <porta>")
        sys.exit(1)

    peer = FanoronaPeer()
    peer.on_chat = lambda text: print(f"\n[adversario]: {text}")
    peer.on_resign = lambda: print("\n[adversario desistiu]")
    peer.on_disconnect = lambda: print("\n[conexao com o adversario perdida]")

    if sys.argv[1] == "host":
        port = int(sys.argv[2])
        peer.on_guest_joined = lambda starting: print(
            f"\n[convidado entrou] Jogador {starting} comeca. Digite para conversar.")
        peer.host_start(port, starting_player=1)
        print(f"Aguardando o convidado em {get_local_ip()}:{port} ...")
    else:
        info = peer.guest_connect(sys.argv[2], int(sys.argv[3]))
        print(f"Conectado! Voce e o Jogador {info['your_player']}; "
              f"o Jogador {info['starting_player']} comeca.")

    while True:
        text = input("> ")
        if text.strip().lower() == "sair":
            break
        peer.send_chat(text)

    peer.close()