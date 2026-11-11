# Protocolo de aplicação compartilhado entre cliente e servidor.
#
# Enquadramento (framing): cada mensagem é UM objeto JSON codificado em UTF-8
# e terminado por "\n". O TCP entrega um fluxo de bytes, sem fronteiras de
# mensagem: um único recv() pode trazer meia mensagem ou duas mensagens juntas.
# Por isso lemos para um buffer até encontrar o "\n".
# (json.dumps escapa quebras de linha dentro de strings como "\\n", então o
# caractere "\n" real nunca aparece no meio de uma mensagem.)

import json

DELIMITADOR = b"\n"
TAM_MAX_MENSAGEM = 1024 * 1024  # 1 MiB: evita que um par mal-comportado esgote a memória


def enviar_mensagem(sock, obj):
    """Serializa obj em JSON e envia como uma linha."""
    dados = json.dumps(obj, ensure_ascii=False).encode("utf-8") + DELIMITADOR
    sock.sendall(dados)  # sendall garante que todos os bytes sejam enviados


def enviar_linha_bruta(sock, texto):
    """Envia texto qualquer como uma linha (usado na demo para mandar JSON inválido)."""
    sock.sendall(texto.encode("utf-8") + DELIMITADOR)


class LeitorDeLinhas:
    """Acumula bytes recebidos do socket e devolve uma linha completa por vez."""

    def __init__(self, sock):
        self.sock = sock
        self.buffer = b""

    def ler_linha(self):
        """Retorna a próxima linha (str, sem o "\\n") ou None se a conexão foi fechada."""
        while DELIMITADOR not in self.buffer:
            if len(self.buffer) > TAM_MAX_MENSAGEM:
                raise ValueError("mensagem excede o tamanho máximo permitido")
            dados = self.sock.recv(1024)  # pode vir um pedaço de qualquer tamanho
            if not dados:                 # outro lado fechou a conexão
                return None
            self.buffer += dados
        linha, self.buffer = self.buffer.split(DELIMITADOR, 1)
        return linha.decode("utf-8", errors="replace")
