"""
menu_view.py
------------
Tela inicial: o jogador escolhe se vai HOSPEDAR uma partida (Host,
Jogador 1) ou ENTRAR em uma partida existente (Convidado, Jogador 2,
informando o IP do Host).

Esta tela nao abre socket nenhum -- ela so coleta a escolha do usuario
e chama os callbacks on_host/on_join, que quem decide o que fazer com
isso e o main.py.
"""

import tkinter as tk
from tkinter import ttk

DEFAULT_PORT = 5050


class MenuView(tk.Frame):
    def __init__(self, master, on_host, on_join):
        super().__init__(master)
        self.on_host = on_host
        self.on_join = on_join

        tk.Label(self, text="Fanorona", font=("Segoe UI", 32, "bold")).pack(pady=(60, 10))
        tk.Label(self, text="Jogo de tabuleiro com comunicacao via sockets",
                 font=("Segoe UI", 11)).pack(pady=(0, 40))

        # --- Bloco Host ---
        host_frame = ttk.LabelFrame(self, text="Hospedar partida (Jogador 1)")
        host_frame.pack(pady=10, padx=40, fill="x")

        tk.Label(host_frame, text="Porta:").grid(row=0, column=0, padx=10, pady=10)
        self.host_port_entry = tk.Entry(host_frame, width=10)
        self.host_port_entry.insert(0, str(DEFAULT_PORT))
        self.host_port_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Button(host_frame, text="Iniciar como Host",
                  command=self._handle_host_click).grid(row=0, column=2, padx=10, pady=10)

        # --- Bloco Convidado ---
        join_frame = ttk.LabelFrame(self, text="Entrar em uma partida (Jogador 2)")
        join_frame.pack(pady=10, padx=40, fill="x")

        tk.Label(join_frame, text="IP do Host:").grid(row=0, column=0, padx=10, pady=10)
        self.join_ip_entry = tk.Entry(join_frame, width=15)
        self.join_ip_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(join_frame, text="Porta:").grid(row=0, column=2, padx=10, pady=10)
        self.join_port_entry = tk.Entry(join_frame, width=10)
        self.join_port_entry.insert(0, str(DEFAULT_PORT))
        self.join_port_entry.grid(row=0, column=3, padx=10, pady=10)

        tk.Button(join_frame, text="Conectar",
                  command=self._handle_join_click).grid(row=0, column=4, padx=10, pady=10)

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.pack(pady=20)

    def _handle_host_click(self) -> None:
        try:
            port = int(self.host_port_entry.get())
        except ValueError:
            self.status_label.config(text="Porta invalida.")
            return
        self.status_label.config(text=f"Aguardando o Convidado conectar na porta {port} ...")
        self.on_host(port)

    def _handle_join_click(self) -> None:
        ip = self.join_ip_entry.get().strip()
        if not ip:
            self.status_label.config(text="Informe o IP do Host.")
            return
        try:
            port = int(self.join_port_entry.get())
        except ValueError:
            self.status_label.config(text="Porta invalida.")
            return
        self.status_label.config(text=f"Conectando em {ip}:{port} ...")
        self.on_join(ip, port)