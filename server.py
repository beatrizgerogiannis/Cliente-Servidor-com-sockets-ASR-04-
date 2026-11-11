from socket  import *
from constCS import * #-
import json
from protocolo import enviar_mensagem, LeitorDeLinhas

# ---------------------------------------------------------------------------
# Operações oferecidas pelo servidor.
# Cada função recebe os argumentos já desempacotados e devolve o resultado,
# ou lança ErroOperacao com uma mensagem amigável.
# ---------------------------------------------------------------------------

class ErroOperacao(Exception):
    """Erro de uma operação específica (não derruba o lote nem o servidor)."""


def exigir_numero(x):
    # bool é subclasse de int em Python; não queremos aceitar true/false como número
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ErroOperacao(f"argumento {x!r} não é numérico")
    return x


def exigir_texto(x):
    if not isinstance(x, str):
        raise ErroOperacao(f"argumento {x!r} não é texto")
    return x


def op_add(a, b):
    return exigir_numero(a) + exigir_numero(b)

def op_sub(a, b):
    return exigir_numero(a) - exigir_numero(b)

def op_mul(a, b):
    return exigir_numero(a) * exigir_numero(b)

def op_div(a, b):
    a, b = exigir_numero(a), exigir_numero(b)
    if b == 0:
        raise ErroOperacao("divisão por zero")
    return a / b

def op_upper(texto):
    return exigir_texto(texto).upper()

def op_reverse(texto):
    return exigir_texto(texto)[::-1]

def op_count_words(texto):
    return len(exigir_texto(texto).split())


# Tabela de despacho: nome da operação -> (função, número de argumentos).
# Para adicionar uma operação nova basta escrever a função e incluí-la aqui.
OPERACOES = {
    "add":         (op_add, 2),
    "sub":         (op_sub, 2),
    "mul":         (op_mul, 2),
    "div":         (op_div, 2),
    "upper":       (op_upper, 1),
    "reverse":     (op_reverse, 1),
    "count_words": (op_count_words, 1),
}


def executar_operacao(item):
    """Executa UMA operação do lote e devolve o dicionário de resultado."""
    if not isinstance(item, dict):
        return {"op": None, "ok": False, "error": "cada operação deve ser um objeto JSON"}
    nome = item.get("op")
    args = item.get("args", [])
    if nome not in OPERACOES:
        return {"op": nome, "ok": False, "error": f"operação desconhecida: {nome!r}"}
    if not isinstance(args, list):
        return {"op": nome, "ok": False, "error": "'args' deve ser uma lista"}
    funcao, aridade = OPERACOES[nome]
    if len(args) != aridade:
        return {"op": nome, "ok": False,
                "error": f"'{nome}' espera {aridade} argumento(s), recebeu {len(args)}"}
    try:
        return {"op": nome, "ok": True, "result": funcao(*args)}
    except ErroOperacao as e:
        return {"op": nome, "ok": False, "error": str(e)}
    except Exception as e:  # rede de segurança: erro inesperado vira erro da operação
        return {"op": nome, "ok": False, "error": f"erro interno: {e}"}


def resumir(texto, limite=200):
    """Encurta textos longos só para o log do servidor."""
    return texto if len(texto) <= limite else texto[:limite] + f"... ({len(texto)} caracteres)"


def processar_requisicao(linha):
    """Interpreta uma linha JSON e processa TODAS as operações do lote, em ordem."""
    try:
        requisicao = json.loads(linha)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON inválido: {e.msg}"}
    if not isinstance(requisicao, dict) or not isinstance(requisicao.get("ops"), list):
        return {"ok": False, "error": "requisição deve ter o formato {\"ops\": [...]}"}
    # Aqui está o ponto central do exercício: várias funcionalidades por requisição.
    return {"results": [executar_operacao(item) for item in requisicao["ops"]]}


# ---------------------------------------------------------------------------
# Laço principal (mesma estrutura do exemplo do livro: socket, bind, listen,
# accept, recv/send), agora aceitando várias conexões em sequência.
# ---------------------------------------------------------------------------

s = socket(AF_INET, SOCK_STREAM)
s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # permite reiniciar o servidor sem esperar a porta liberar
s.bind((HOST, PORT))  #-
s.listen(1)           #-
print(f"Servidor ouvindo em {HOST}:{PORT} (Ctrl+C para encerrar)")

try:
  while True:                    # aceita um cliente por vez, para sempre
    (conn, addr) = s.accept()    # returns new socket and addr. client
    print(f"Conexão de {addr}")
    leitor = LeitorDeLinhas(conn)
    try:
      while True:                # várias requisições na mesma conexão
        try:
          linha = leitor.ler_linha()
        except ValueError as e:  # mensagem grande demais: avisa e encerra a conexão
          enviar_mensagem(conn, {"ok": False, "error": str(e)})
          break
        if linha is None: break  # stop if client stopped
        print(f"  <- {resumir(linha)}")
        resposta = processar_requisicao(linha)
        print(f"  -> {resumir(json.dumps(resposta, ensure_ascii=False))}")
        enviar_mensagem(conn, resposta)
    except OSError as e:         # cliente caiu no meio: segue atendendo os próximos
      print(f"Erro na conexão com {addr}: {e}")
    finally:
      conn.close()               # close the connection
      print(f"Conexão com {addr} encerrada")
except KeyboardInterrupt:
  print("\nServidor encerrado.")
finally:
  s.close()
