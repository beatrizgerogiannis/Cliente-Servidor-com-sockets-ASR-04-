from socket  import *
from constCS import * #-
import json
import shlex
import sys
from protocolo import enviar_mensagem, enviar_linha_bruta, LeitorDeLinhas


def mostrar_resposta(resposta):
    """Imprime a resposta do servidor de forma legível."""
    if "results" not in resposta:  # erro da requisição como um todo (ex.: JSON inválido)
        print(f"  ERRO NA REQUISIÇÃO: {resposta.get('error')}")
        return
    for i, r in enumerate(resposta["results"], 1):
        if r.get("ok"):
            print(f"  [{i}] {r['op']:<12} ok    -> {r['result']!r}")
        else:
            print(f"  [{i}] {str(r.get('op')):<12} ERRO  -> {r['error']}")


def requisitar(s, leitor, ops):
    """Envia um lote de operações e espera a resposta."""
    requisicao = {"ops": ops}
    print(f"Enviando: {json.dumps(requisicao, ensure_ascii=False)}")
    enviar_mensagem(s, requisicao)
    resposta = leitor.ler_linha()
    if resposta is None:
        raise ConnectionError("servidor fechou a conexão")
    mostrar_resposta(json.loads(resposta))


# ---------------------------------------------------------------------------
# Modo demonstração: lotes fixos, incluindo casos de erro.
# ---------------------------------------------------------------------------

LOTES_DEMO = [
    ("Lote 1: várias operações numéricas e de texto numa só requisição", [
        {"op": "add", "args": [2, 3]},
        {"op": "sub", "args": [10, 4.5]},
        {"op": "mul", "args": [6, 7]},
        {"op": "div", "args": [1, 4]},
        {"op": "upper", "args": ["olá, mundo"]},
        {"op": "reverse", "args": ["sistemas distribuídos"]},
        {"op": "count_words", "args": ["o rato roeu a roupa do rei de roma"]},
    ]),
    ("Lote 2: erros por operação (as demais continuam funcionando)", [
        {"op": "div", "args": [5, 0]},             # divisão por zero
        {"op": "pow", "args": [2, 8]},             # operação desconhecida
        {"op": "add", "args": [1]},                # número de argumentos errado
        {"op": "mul", "args": ["3", 4]},           # tipo errado
        {"op": "upper", "args": [123]},            # tipo errado
        {"op": "add", "args": [100, 200]},         # esta deve dar certo
    ]),
    ("Lote 3: mensagem grande (texto de ~50 KB, bem maior que recv(1024))", [
        {"op": "count_words", "args": ["palavra " * 6000]},
    ]),
]


def modo_demo(s, leitor):
    for titulo, ops in LOTES_DEMO:
        print(f"\n=== {titulo}")
        if titulo.startswith("Lote 3"):  # não imprime o texto gigante inteiro
            enviar_mensagem(s, {"ops": ops})
            print(f"Enviando: {{\"ops\": [{{\"op\": \"count_words\", \"args\": [\"palavra palavra ...\" ({len(ops[0]['args'][0])} caracteres)]}}]}}")
            mostrar_resposta(json.loads(leitor.ler_linha()))
        else:
            requisitar(s, leitor, ops)

    print("\n=== Lote 4: JSON inválido (o servidor responde erro e segue vivo)")
    bruto = '{"ops": [{"op": "add", "args": [1, 2]'  # falta fechar colchetes/chaves
    print(f"Enviando: {bruto}")
    enviar_linha_bruta(s, bruto)
    mostrar_resposta(json.loads(leitor.ler_linha()))

    print("\n=== Lote 5: formato errado (sem a chave \"ops\")")
    bruto = '{"op": "add", "args": [1, 2]}'
    print(f"Enviando: {bruto}")
    enviar_linha_bruta(s, bruto)
    mostrar_resposta(json.loads(leitor.ler_linha()))

    print("\n=== Lote 6: depois dos erros, a mesma conexão continua funcionando")
    requisitar(s, leitor, [{"op": "mul", "args": [3, 3]}, {"op": "reverse", "args": ["fim"]}])


# ---------------------------------------------------------------------------
# Modo interativo: o usuário monta um lote e envia.
# ---------------------------------------------------------------------------

AJUDA = """Comandos:
  <op> <arg1> [arg2]  adiciona uma operação ao lote. Ex.: add 2 3 | upper "ola mundo"
  lote                mostra o lote atual
  enviar              envia o lote ao servidor (e o esvazia)
  limpar              esvazia o lote sem enviar
  ajuda               mostra esta ajuda
  sair                encerra o cliente
Operações do servidor: add, sub, mul, div, upper, reverse, count_words
Argumentos que parecem números são enviados como números; use aspas para textos com espaço."""


def converter_argumento(token):
    """Converte '3' -> 3, '2.5' -> 2.5; o resto fica como texto."""
    for tipo in (int, float):
        try:
            return tipo(token)
        except ValueError:
            pass
    return token


def modo_interativo(s, leitor):
    print(AJUDA)
    lote = []
    while True:
        try:
            linha = input(f"\n[{len(lote)} op(s) no lote] > ").strip()
        except EOFError:
            break
        if not linha:
            continue
        try:
            partes = shlex.split(linha)
        except ValueError as e:
            print(f"Entrada inválida: {e}")
            continue
        comando = partes[0]
        if comando == "sair":
            break
        elif comando == "ajuda":
            print(AJUDA)
        elif comando == "lote":
            for i, op in enumerate(lote, 1):
                print(f"  [{i}] {json.dumps(op, ensure_ascii=False)}")
            if not lote:
                print("  (vazio)")
        elif comando == "limpar":
            lote = []
        elif comando == "enviar":
            if not lote:
                print("Lote vazio; adicione operações antes de enviar.")
                continue
            requisitar(s, leitor, lote)
            lote = []
        else:
            # Qualquer outro comando vira uma operação; quem valida é o servidor.
            lote.append({"op": comando, "args": [converter_argumento(t) for t in partes[1:]]})


# ---------------------------------------------------------------------------

s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT)) # connect to server (block until accepted)
leitor = LeitorDeLinhas(s)
try:
    if "--demo" in sys.argv:
        modo_demo(s, leitor)
    else:
        modo_interativo(s, leitor)
finally:
    s.close()               # close the connection
