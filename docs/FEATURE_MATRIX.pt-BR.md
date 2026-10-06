[🇺🇸 English](FEATURE_MATRIX.md) · 🇧🇷 Português

# Matriz de funcionalidades e paridade (ITE 8291 + ITE 8233)

⏱️ **Leitura:** ~2 min

> **TL;DR**
> - Cada capacidade do hardware e o **comando da CLI** que chega nela, uma por linha.
> - **Regra de paridade:** toda linha precisa continuar acessível pela CLI unificada `avell-storm-rgb`.
> - Parâmetros por efeito e o que exclui o quê → [DEVICE_FEATURES_DEEP_DIVE](DEVICE_FEATURES_DEEP_DIVE.pt-BR.md). CLI vs GUI → [OVERVIEW](OVERVIEW.pt-BR.md).

**Leia isto se…** você precisa saber se algo é suportado e como chamar.

Inspiração upstream: [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl). O protocolo da barra de LED vem de fontes do fabricante com licença MIT (veja [NOTICE](../NOTICE)).

---

## 🧭 ITE 8291 — retroiluminação do teclado

USB `048d`, produtos `6004`, `6006`, `CE00`, `600B`, `bcdDevice` 0.03.

| Capacidade | Limites / notas | CLI |
|------------|-----------------|-----|
| Desligar | `turn_off` | `keyboard power off` |
| Brilho | **0–50** | `keyboard brightness <n>` |
| Efeitos de firmware embutidos | breathing, wave, random, rainbow, ripple, marquee, raindrop, aurora, fireworks | `keyboard effect <nome> …` |
| Opções de efeito | velocidade 0–10, brilho, slot de cor da paleta, direção **ou** reativo, save | flags do mesmo subcomando |
| Cor sólida (teclado inteiro) | cores com nome ou RGB | `keyboard solid-color …` |
| Paleta | definir slot 1–7, restaurar padrão, aleatória | `keyboard palette restore \| random \| set-slot` |
| Padrão de teste demo | sequência de 6 passos | `keyboard demo-test-pattern` |
| Congelar animação | velocidade → 11 | `keyboard freeze-animation` |
| Cores por tecla + DSL de animação | grade 6 × 21; arquivo ou stdin | `keyboard play-animation …` |
| Seguir a tela | amostra 16 × 6; região opcional no X11; seletor de janela do portal no Wayland | `keyboard follow-screen …` (extra `[screen]`) |
| Inspecionar | versão de FW, brilho, ligado/desligado | `keyboard inspect …` |
| Listar teclados compatíveis | enumeração USB | `device list --kind keyboard` |
| Debug do tráfego USB | stderr | `keyboard --debug …` |

> [!WARNING]
> A opção de **cor** do efeito escolhe um **slot da paleta**, não um valor RGB. **Direção** e **reativo** dividem um byte do protocolo, então a CLI torna os dois mutuamente exclusivos.

## 🧭 ITE 8233 — barra de LED

USB `048d:7000`, `048d:7001`, ou string de produto contendo `8233`.

| Capacidade | Limites / notas | CLI |
|------------|-----------------|-----|
| Ligar / desligar | sequência de inicialização | `led-bar power on \| off` |
| Cor estática | com nome + `#RRGGBB` | `led-bar color <spec>` |
| Paleta | presets + lista separada por vírgulas | `led-bar palette <spec>` |
| Efeito visual | static, breathing, wave, impact, raindrop | `led-bar effect <nome>` |
| Brilho | **0–100** (aplicado com um efeito) | `led-bar brightness <n> --with-effect …` |
| Velocidade do movimento | 1–10 (aplicada com um efeito) | `led-bar speed <n> --with-effect …` |
| Status / descoberta | | `led-bar inspect` / `device list --kind led-bar` |

> [!NOTE]
> A barra de LED só recebe brilho e velocidade **dentro de um report de efeito**. Por isso os dois comandos reaplicam um efeito (`--with-effect`).

## 🛠️ Referência USB

- Teclado: vendor `048d`, produtos listados acima.
- Barra de LED: `048d:7000`, `048d:7001`, ou produto contendo `8233`.
- Regras udev: [DEVELOPMENT](DEVELOPMENT.pt-BR.md). Este repo ainda não as empacota.
