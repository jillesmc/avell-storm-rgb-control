[🇺🇸 English](README.md) · 🇧🇷 Português

# Formato do arquivo de animação

⏱️ **Leitura:** ~3 min

> **TL;DR**
> - Texto puro, **uma instrução por linha**. Ele edita um **mapa de cores** (posição → cor), e o `apply` envia o mapa ao teclado.
> - As coordenadas são **do dispositivo**: `(linha 0, coluna 0)` é o canto **inferior esquerdo**.
> - Rode com `avell-storm-rgb keyboard play-animation --file <script>` (ou mande pelo stdin).

**Leia isto se…** você quer escrever ou entender um script de animação por tecla.

---

## 🛠️ Comandos

| Comando | Efeito |
|---------|--------|
| `pos R C r,g,b` | Define a cor de (linha `R`, coluna `C`) como `r,g,b` no mapa de cores |
| `apply` | Aplica de fato a retroiluminação do teclado a partir do mapa atual |
| `clear` | Limpa o mapa de cores |
| `wait N` | Espera `N` segundos (`N` pode ser decimal) |
| `brightness B` | Define o brilho da retroiluminação como `B` (inteiro **0–50**) |
| `shift Rdiff Cdiff` | Soma `Rdiff` à linha e `Cdiff` à coluna de toda entrada (entradas empurradas para fora da grade são descartadas) |

## ⚠️ Observações

- **Comentários:** linhas começando com `#` são ignoradas. Uma linha começando com `/*` abre um bloco de comentário e `*/` fecha. Blocos podem ser aninhados.
- **`shift 0 -1`** move tudo uma coluna para a esquerda.
- **`(linha 0, coluna 0)` é o canto inferior esquerdo.** Essa é a orientação *do dispositivo*; a grade por tecla da GUI mostra a linha 0 em cima.
- Os exemplos foram feitos para **16 × 6** posições (XMG Fusion 15). A grade do controlador é 6 × 21.

## 🧭 Exemplos nesta pasta

| Arquivo | Mostra |
|---------|--------|
| `gaming_mode` | WASD e setas em vermelho (como o *Gaming mode* do XMG Control Center) |
| `xmg_f15` | O texto `XMG F15` |
| `manjaro_i3` | Mapa estático: teclas Fn / F e teclas mod do i3 em branco, o resto no azul-esverdeado do Manjaro (QWERTZ) |
| `sine_wave.py` | Gera uma onda senoidal; mande a saída para a CLI |

```bash
python assets/animations/sine_wave.py | avell-storm-rgb keyboard play-animation
```

Rode a partir da raiz do repo, no ambiente que tem a CLI instalada (ex.: `uv run`).
