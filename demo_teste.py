"""
demo_test.py
------------
Teste rapido, sem precisar de dois terminais nem de rede real: sobe o
Host (FanoronaServer) em uma thread e o Convidado (FanoronaClient) na
thread principal, na mesma maquina (127.0.0.1), e troca algumas
mensagens para validar que o protocolo esta funcionando.

Rode com:  python demo_test.py
"""

import threading
import time

from network.server import FanoronaServer
from network.client import FanoronaClient

PORT = 5050

server_messages = []
client_messages = []
welcome_received = threading.Event()


def start_server():
    server = FanoronaServer(
        port=PORT,
        on_message=lambda msg: server_messages.append(msg),
    )
    server.start()
    return server


def main():
    server_holder = {}

    def run_server():
        server_holder["server"] = start_server()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(0.3)

    def handle_welcome(data):
        print(f"[TESTE] Cliente recebeu welcome: {data}")
        welcome_received.set()

    client = FanoronaClient(
        "127.0.0.1",
        port=PORT,
        on_message=lambda msg: client_messages.append(msg),
        on_welcome=handle_welcome,
    )
    client.connect()

    assert welcome_received.wait(timeout=2), "Nao recebeu a mensagem de welcome a tempo."

    time.sleep(0.2)
    server = server_holder["server"]

    server.send("chat", {"text": "Ola Convidado, bem-vindo!"})
    client.send("chat", {"text": "Ola Host, valeu!"})
    client.send("move", {"from": [0, 0], "to": [0, 1]})

    time.sleep(0.3)

    print("\nMensagens recebidas pelo CLIENTE (vindas do servidor):", client_messages)
    print("Mensagens recebidas pelo SERVIDOR (vindas do cliente):", server_messages)

    assert any(m["type"] == "chat" and m["data"]["text"] == "Ola Convidado, bem-vindo!"
               for m in client_messages), "Cliente nao recebeu o chat do servidor."
    assert any(m["type"] == "chat" and m["data"]["text"] == "Ola Host, valeu!"
               for m in server_messages), "Servidor nao recebeu o chat do cliente."
    assert any(m["type"] == "move" for m in server_messages), "Servidor nao recebeu a jogada."

    print("\n[OK] Todos os testes passaram! Handshake, chat e jogada trafegaram corretamente.")

    client.close()
    server.close()


if __name__ == "__main__":
    main()