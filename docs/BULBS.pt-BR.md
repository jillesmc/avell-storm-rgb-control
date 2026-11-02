[🇺🇸 English](BULBS.md) · 🇧🇷 Português

# Lâmpadas inteligentes Tuya

⏱️ **Tempo de leitura:** ~6 min

> **TL;DR**
> - Opcional: `uv sync --extra tuya` (mais `--extra gui` para o app). Sem ele, nada muda.
> - Importe o `devices.json` do wizard do tinytuya **uma vez**; depois tudo é **local** (LAN, sem nuvem).
> - Abrir o app **nunca altera** uma lâmpada, e as chaves locais **nunca aparecem**.

**Leia isto se…** você quer controlar lâmpadas Tuya pelo app ou pela CLI, ou vai mexer no código das lâmpadas.

---

## 🛠️ Configurar (uma vez)

| Passo | Comando / ação |
|-------|----------------|
| 1. Obter as chaves locais (fora do app, usa a nuvem Tuya uma vez) | `python -m tinytuya wizard` → grava `devices.json` |
| 2. Instalar o suporte | `uv sync --extra gui --extra tuya` |
| 3. Importar | CLI: `uv run avell-storm-rgb bulb import ~/caminho/devices.json` · GUI: **Devices → Smart bulbs → Import Tuya devices…** |
| 4. Conectar (GUI) | Clique em **Connect** numa lâmpada → ela aparece na sidebar com um interruptor |

O import só guarda entradas de luz (`category: dj`) que têm chave local. As outras aparecem como ignoradas
(`no local key`, `not a bulb (category cz)`, `missing category`). Reimportar atualiza pelo id e **nunca apaga**.

## 🧭 Arquivos

| Arquivo | Quem grava | Conteúdo |
|---------|------------|----------|
| `~/.config/avell-storm-rgb/tuya_devices.json` (modo **0600**) | `bulb import`/`remove`, Import/Remove da GUI, lâmpada respondendo num IP novo | id, nome, **chave local**, MAC, protocolo, último IP |
| `~/.config/avell-storm-rgb/state.json` → `devices.bulbs` | **só** a GUI (`AppFacade`) | `{"<id>": {"remembered": true, "follow": "keyboard"}}` |

> [!WARNING]
> `tuya_devices.json` contém as chaves locais. Não compartilhe. As chaves nunca aparecem no `state.json`,
> em logs, textos da GUI, saída da CLI (humana ou `--json`) nem em mensagens de erro; as listagens mostram `key: set`.

Nenhuma cor ou brilho é salvo para as lâmpadas: **a própria lâmpada é a fonte da verdade**.
`$XDG_CONFIG_HOME` substitui `~/.config` quando definido.

## 🛠️ CLI

Alvo = um nome (sem diferenciar maiúsculas nem acentos: `escritorio` = `Escritório`), um id ou `all`.

| Comando | Efeito | Saída (exit) |
|---------|--------|--------------|
| `bulb import <devices.json> [--json]` | Importa/atualiza o inventário | 0 · 1 arquivo ruim / sem lâmpadas · 3 inventário ilegível |
| `bulb list [--json]` | Cada lâmpada uma vez, em paralelo, prazo de 10 s (`online`/`offline`, IP, `key: set`) | 0 |
| `bulb status [alvo] [--json]` | Ligada/desligada, modo, brilho, temperatura ou cor | 1 se algum alvo está offline |
| `bulb on\|off\|toggle <alvo>` | Liga/desliga; `toggle` lê e inverte | 1 se algum alvo está offline/falhou |
| `bulb bright <1-100> <alvo>` | Brilho do modo atual; **liga a lâmpada** | idem |
| `bulb white [--temp 0-100] <alvo>` | Modo branco (0 quente … 100 frio); **liga a lâmpada** | idem |
| `bulb color <R> <G> <B> <alvo>` | Modo cor, RGB 0–255; **liga a lâmpada** | idem |
| `bulb remove <alvo>` | Apaga a entrada **e a chave** (`all` não é aceito) | 0 |
| `state show [--json]` | Também lista as lâmpadas salvas (`bulb  Escritório  <id>  remembered  follow keyboard`) | 3 se o inventário está ilegível |

```console
$ uv run avell-storm-rgb bulb status
Quarto       on   white   brightness 100%  temperature 100%
Escritório   on   colour  #ff8800  brightness 100%
Sala         offline
```

Sem o extra, todo verbo `bulb` imprime
`error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya` (exit 1). `state restore` nunca fala com lâmpadas.

## 🧭 GUI

| Onde | O quê |
|------|-------|
| **Devices → Smart bulbs** | Botão Import, uma linha por lâmpada (`online · <ip>` / `offline`), **Connect** / **Disconnect**, **Remove** (pede confirmação; apaga a chave) |
| **Sidebar** | Uma entrada por lâmpada lembrada, em ordem de nome, com interruptor. Desabilitado até a primeira leitura; "Unavailable" quando não responde |
| **Página da lâmpada** | Linha de status ("On · White · 192.168.0.22"), interruptor, brilho, temperatura do branco, cor, modo, **Follow** |
| **Indisponível** | Motivo + **Retry** / **Forget** (Forget mantém a chave) |

Disconnect/Forget = parar de lembrar (chave mantida). Remove = apagar a chave. Operações de lâmpada nunca mostram o overlay de "ocupado".

## 🧭 O que o app faz — e nunca faz

| Regra | Detalhe |
|-------|---------|
| **Ao abrir, só lê** | Na abertura, no Retry e na atualização o app só **lê** as lâmpadas. Nunca acende uma luz no login |
| **Estado real** | A página mostra a última leitura ou o resultado do último comando; "Reading…" antes da primeira leitura |
| **Atualização** | Ao abrir, quando a janela aparece, quando uma página abre e a cada **30 s** com a janela visível. Nada na bandeja (exceto lâmpadas seguindo algo, lidas a cada 5 s) |
| **Comandos explícitos ligam** | Brilho, branco e cor ligam a lâmpada (como o app Tuya) |
| **Só local** | Protocolo LAN Tuya (3.3), TCP 6668; descoberta em UDP 6666/6667; IP da memória → ARP → último IP → descoberta |

## 🔁 Follow (teclado, tela, barra de LED)

Na página da lâmpada, **Follow** = None / Keyboard / Screen / LED bar. Só aparecem as fontes disponíveis no momento.

| Fonte | Cor enviada à lâmpada |
|-------|-----------------------|
| **Keyboard** | Média de cada escrita sólida/por tecla/animação/seguir-tela que o app manda ao teclado. Efeitos de firmware e teclado apagado não enviam nada |
| **Screen** (extra `screen`) | Média da captura de tela. **Uma captura só**, compartilhada com o seguir-tela do teclado (um seletor no Wayland) |
| **LED bar** | Média estática da paleta aplicada, enquanto a luz da barra está ligada |

- **Nunca liga a lâmpada**: só manda a cor, e só enquanto a última leitura diz que ela está ligada (desconhecido = desligada).
- **Taxa:** no máximo 4 atualizações/s por lâmpada, só quando algum canal mudou ≥ 8.
- **Uma conexão local** fica aberta enquanto segue; nesse tempo, outros apps da rede não controlam essa lâmpada localmente.
- A escolha é salva e volta na próxima abertura. Disconnect para o follow mas mantém a escolha.
- Captura cancelada ou janela fechada → quem seguia a tela volta para None, com uma mensagem.

## ⚠️ Erros que podem aparecer

| Situação | Mensagem |
|----------|----------|
| Lâmpada fora da rede | `Escritório is not reachable on the network. Check that it is powered; discovery uses UDP 6666/6667.` |
| Chave ou protocolo errados | `Escritório rejected the local key or protocol — re-import devices.json` |
| Inventário corrompido | `error: bulb inventory is unreadable (<reason>): <path>` |

Os ids, chaves, MACs e IPs desta página são fictícios.

## Próximo

- Organização do código e threads → [ARCHITECTURE](ARCHITECTURE.pt-BR.md#-lâmpadas-tuya)
- Fluxos passo a passo → [FLOWS](FLOWS.pt-BR.md#-9--lâmpadas-tuya)
- Testes sem lâmpadas → [DEVELOPMENT](DEVELOPMENT.pt-BR.md#-testes)
