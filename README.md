# Calculadora/Utilitário Remoto com Sockets TCP

Exercício 1 de Sistemas Distribuídos (UFG). Extensão do exemplo cliente-servidor com sockets TCP
da Fig. 2.3 (Cap. 2) do livro *Distributed Systems*, de Tanenbaum & van Steen.

O servidor oferece **7 operações** (4 numéricas e 3 de texto) que o cliente chama remotamente,
e **cada requisição pode conter várias operações diferentes**, executadas em lote.

## Arquitetura

```
 ┌───────────── cliente ─────────────┐          ┌───────────── servidor ─────────────┐
 │ monta um lote de operações        │  TCP     │ accept() → lê uma linha JSON        │
 │ {"ops": [op1, op2, ...]}  ────────┼─────────►│ para cada op do lote:               │
 │                                   │          │   tabela de despacho → função       │
 │ imprime um resultado por op ◄─────┼──────────┤ {"results": [res1, res2, ...]}      │
 └───────────────────────────────────┘          └─────────────────────────────────────┘
```

| Arquivo        | Papel |
|----------------|-------|
| `constCS.py`   | `HOST` e `PORT` usados pelos dois lados (padrão: `localhost:5678`). |
| `protocolo.py` | Enquadramento das mensagens: envio de JSON terminado em `\n` e leitura com buffer. |
| `server.py`    | Servidor: socket `AF_INET`/`SOCK_STREAM`, tabela de despacho e processamento do lote. |
| `client.py`    | Cliente: modo interativo e modo de demonstração (`--demo`). |

O servidor mantém a estrutura do exemplo do livro (`socket` → `bind` → `listen` → `accept` →
`recv`/`send`), com duas extensões:

- fica em laço aceitando **várias conexões em sequência** (um cliente por vez, sem threads);
- em cada conexão, atende **várias requisições** até o cliente fechar o socket.

Apenas a biblioteca padrão do Python 3 é usada.

## Protocolo de aplicação

### Enquadramento

O TCP é um fluxo de bytes e não preserva fronteiras de mensagem: um `recv(1024)` pode devolver
meia mensagem ou duas mensagens juntas. Por isso, **cada mensagem é um objeto JSON em UTF-8
numa única linha, terminado por `\n`**. O receptor acumula bytes num buffer até encontrar o `\n`
(classe `LeitorDeLinhas` em `protocolo.py`). Assim mensagens grandes (a demo envia ~48 KB)
chegam inteiras. Há um limite de 1 MiB por mensagem para proteger a memória do servidor.

### Requisição

```json
{"ops": [
  {"op": "add",   "args": [2, 3]},
  {"op": "upper", "args": ["ola"]}
]}
```

### Resposta

Um resultado por operação, **na mesma ordem** da requisição:

```json
{"results": [
  {"op": "add",   "ok": true, "result": 5},
  {"op": "upper", "ok": true, "result": "OLA"}
]}
```

Se uma operação falhar, só ela é marcada com erro; as outras são executadas normalmente:

```json
{"results": [
  {"op": "div", "ok": false, "error": "divisão por zero"},
  {"op": "add", "ok": true,  "result": 300}
]}
```

Se a requisição inteira for inválida (JSON malformado ou sem a lista `"ops"`), a resposta é um
erro único, e a conexão continua aberta para as próximas requisições:

```json
{"ok": false, "error": "JSON inválido: Expecting ',' delimiter"}
```

## Operações

| Operação      | Argumentos               | Retorno                         | Possíveis erros |
|---------------|--------------------------|---------------------------------|-----------------|
| `add`         | `a`, `b` (números)       | `a + b`                         | nº de argumentos ≠ 2; argumento não numérico |
| `sub`         | `a`, `b` (números)       | `a - b`                         | nº de argumentos ≠ 2; argumento não numérico |
| `mul`         | `a`, `b` (números)       | `a * b`                         | nº de argumentos ≠ 2; argumento não numérico |
| `div`         | `a`, `b` (números)       | `a / b` (sempre float)          | nº de argumentos ≠ 2; argumento não numérico; divisão por zero |
| `upper`       | `texto` (string)         | texto em maiúsculas             | nº de argumentos ≠ 1; argumento não é texto |
| `reverse`     | `texto` (string)         | texto invertido                 | nº de argumentos ≠ 1; argumento não é texto |
| `count_words` | `texto` (string)         | quantidade de palavras (inteiro)| nº de argumentos ≠ 1; argumento não é texto |

Erros gerais: operação desconhecida (por item); JSON inválido e requisição sem `"ops"` (para a
requisição inteira). Números são `int` ou `float` do JSON; `true`/`false` não são aceitos como números.

Para **adicionar uma operação**, basta escrever a função em `server.py` e registrá-la no dicionário
`OPERACOES`, que mapeia `nome → (função, número de argumentos)`.

## Como executar

Requer Python 3. Abra dois terminais na pasta do projeto.

**Terminal 1 — servidor:**

```bash
python3 server.py
```

**Terminal 2 — cliente em modo demonstração** (envia lotes de exemplo, incluindo casos de erro):

```bash
python3 client.py --demo
```

**Terminal 2 — cliente em modo interativo:**

```bash
python3 client.py
```

No modo interativo você monta um lote e o envia:

```
[0 op(s) no lote] > add 2 3
[1 op(s) no lote] > upper "ola mundo"
[2 op(s) no lote] > count_words "a b c"
[3 op(s) no lote] > enviar
Enviando: {"ops": [{"op": "add", "args": [2, 3]}, {"op": "upper", "args": ["ola mundo"]}, {"op": "count_words", "args": ["a b c"]}]}
  [1] add          ok    -> 5
  [2] upper        ok    -> 'OLA MUNDO'
  [3] count_words  ok    -> 3
```

Comandos: `<op> <args...>`, `lote` (mostra o lote), `enviar`, `limpar`, `ajuda`, `sair`.
Argumentos que parecem números são enviados como números; use aspas para textos com espaços.

Encerre o servidor com `Ctrl+C`. Para rodar em máquinas diferentes, ajuste `HOST` em `constCS.py`
para o IP do servidor.

## Exemplo de saída (`python3 client.py --demo`)

```
=== Lote 1: várias operações numéricas e de texto numa só requisição
Enviando: {"ops": [{"op": "add", "args": [2, 3]}, {"op": "sub", "args": [10, 4.5]}, {"op": "mul", "args": [6, 7]}, {"op": "div", "args": [1, 4]}, {"op": "upper", "args": ["olá, mundo"]}, {"op": "reverse", "args": ["sistemas distribuídos"]}, {"op": "count_words", "args": ["o rato roeu a roupa do rei de roma"]}]}
  [1] add          ok    -> 5
  [2] sub          ok    -> 5.5
  [3] mul          ok    -> 42
  [4] div          ok    -> 0.25
  [5] upper        ok    -> 'OLÁ, MUNDO'
  [6] reverse      ok    -> 'sodíubirtsid sametsis'
  [7] count_words  ok    -> 9

=== Lote 2: erros por operação (as demais continuam funcionando)
Enviando: {"ops": [{"op": "div", "args": [5, 0]}, {"op": "pow", "args": [2, 8]}, {"op": "add", "args": [1]}, {"op": "mul", "args": ["3", 4]}, {"op": "upper", "args": [123]}, {"op": "add", "args": [100, 200]}]}
  [1] div          ERRO  -> divisão por zero
  [2] pow          ERRO  -> operação desconhecida: 'pow'
  [3] add          ERRO  -> 'add' espera 2 argumento(s), recebeu 1
  [4] mul          ERRO  -> argumento '3' não é numérico
  [5] upper        ERRO  -> argumento 123 não é texto
  [6] add          ok    -> 300

=== Lote 3: mensagem grande (texto de ~50 KB, bem maior que recv(1024))
Enviando: {"ops": [{"op": "count_words", "args": ["palavra palavra ..." (48000 caracteres)]}]}
  [1] count_words  ok    -> 6000

=== Lote 4: JSON inválido (o servidor responde erro e segue vivo)
Enviando: {"ops": [{"op": "add", "args": [1, 2]
  ERRO NA REQUISIÇÃO: JSON inválido: Expecting ',' delimiter

=== Lote 5: formato errado (sem a chave "ops")
Enviando: {"op": "add", "args": [1, 2]}
  ERRO NA REQUISIÇÃO: requisição deve ter o formato {"ops": [...]}

=== Lote 6: depois dos erros, a mesma conexão continua funcionando
Enviando: {"ops": [{"op": "mul", "args": [3, 3]}, {"op": "reverse", "args": ["fim"]}]}
  [1] mul          ok    -> 9
  [2] reverse      ok    -> 'mif'
```

## Como foi atendido o requisito "mais de uma funcionalidade por requisição"

No exemplo original, cada mensagem do cliente produzia um único processamento (ecoar o texto com
`*`). Aqui a requisição carrega uma **lista** de operações (`"ops"`), que podem ser de tipos
diferentes — por exemplo, uma soma, uma divisão e uma conversão para maiúsculas na mesma
mensagem. O servidor percorre a lista em ordem, despacha cada item para a função correspondente
pela tabela `OPERACOES` e devolve uma lista `"results"` alinhada com a de entrada. Como cada
operação é executada e validada isoladamente, um erro numa delas (divisão por zero, tipo errado,
operação inexistente) não impede as demais nem derruba o servidor. Com isso, várias
funcionalidades são acessadas em **uma única ida e volta pela rede**.
