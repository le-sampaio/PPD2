# Fanorona (RMI/RPC com Pyro5)

Jogo Fanorona para dois jogadores, com comunicação entre os tabuleiros via RMI/RPC usando Pyro5.
Projeto 2 de Programação Paralela e Distribuída (IFCE 2026.2).

## Requisitos

- Python 3.10+
- Tkinter (já vem com o Python na maioria das instalações)
- Pyro5:

```bash
pip install -r requirements.txt
```

## Como iniciar

Em cada máquina (ou em dois terminais, na mesma máquina), execute:

```bash
python main.py
```

## Como jogar

O IP **não** fica fixo no código: ele é informado pelo usuário na tela inicial.

**Jogador 1 (Host)**
1. Informe a porta (padrão: `5050`) e clique em **Iniciar como Host**.
2. A tela mostra o IP da sua máquina e a porta. Passe os dois para o adversário.

**Jogador 2 (Convidado)**
1. Digite o **IP do Host** e a **porta** informados pelo Host.
2. Clique em **Conectar**.

Quando a conexão é feita, o tabuleiro abre nas duas máquinas e o jogo sorteia quem começa.

Para testar na mesma máquina, abra dois terminais e use o IP `127.0.0.1`.

> Em máquinas diferentes, as duas precisam estar na mesma rede, e a porta escolhida
> pelo Host deve estar liberada no firewall.

## Funcionalidades

- Controle de turno (sorteio de quem inicia)
- Movimentação das peças
- Desistência
- Chat durante toda a partida
- Indicação do vencedor

## Estrutura

- `main.py`: ponto de entrada; liga o menu, a rede e o jogo
- `network/peer.py`: comunicação RMI/RPC com Pyro5
- `game/`: tabuleiro, regras e estado do jogo
- `gui/`: interface em Tkinter (menu e tabuleiro)
