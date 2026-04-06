# PySide6 — referência expandida

**Repo:** o código **ativo** de produto é o CLI **`src/avell_storm_rgb/`**; esta referência aplica-se à **app desktop** em **`src/app/`** quando existir (rule `pyside6-qml-desktop.mdc` + `repo-context.mdc`). **QML primeiro** na GUI; **Qt Designer** só para fluxos **Widget** deliberados. **Dependências e execução local:** neste repositório usar **`uv`** (`uv sync`, `uv run`), ver `repo-context.mdc`.

---

## 1. Organização: Widgets (Designer + uic)

**Princípio:** Separar definição visual da lógica. Com Widgets, desenhar no **Qt Designer**, gerar Python com **`pyside6-uic`**, compor num controller. **Não** editar manualmente `ui_*.py` gerados.

**Neste projeto:** fluxo predefinido é **QML em `src/app/ui/`**; use Designer apenas se a feature for explicitamente baseada em Widgets.

### Evitar

UI complexa só em código Python sem separação clara, ou alterar ficheiros gerados pelo uic.

### Preferir (Widgets)

```python
# 1. Design 'my_app.ui' in Qt Designer (e.g. QMainWindow, QPushButton objectName 'myButton').
# 2. Run: pyside6-uic my_app.ui -o ui_my_app.py
# (Do not hand-edit ui_my_app.py.)

from PySide6.QtWidgets import QApplication, QMainWindow

from ui_my_app import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.myButton.clicked.connect(self._on_button_clicked)

    def _on_button_clicked(self) -> None:
        print("Button clicked from composed UI!")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

---

## 2. Qt Quick Controls 2 e QML

**Princípio:** UI declarativa no QML; negócio em Python (`QObject` com `Property`, `Signal`, `Slot`).

### Evitar — lógica pesada no QML

Loops, parsing, regras de domínio em blocos `onClicked` / JS.

### Preferir — backend Python + bindings

```python
# backend.py
from __future__ import annotations

import math

from PySide6.QtCore import QObject, Property, Signal, Slot


class Backend(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._input_value = "10"
        self._result_value = ""

    inputValueChanged = Signal()
    resultValueChanged = Signal()

    @Property(str, notify=inputValueChanged)
    def inputValue(self) -> str:
        return self._input_value

    @inputValue.setter
    def inputValue(self, value: str) -> None:
        if self._input_value != value:
            self._input_value = value
            self.inputValueChanged.emit()

    @Property(str, notify=resultValueChanged)
    def resultValue(self) -> str:
        return self._result_value

    @resultValue.setter
    def resultValue(self, value: str) -> None:
        if self._result_value != value:
            self._result_value = value
            self.resultValueChanged.emit()

    @Slot()
    def calculateFactorial(self) -> None:
        try:
            n = int(self.inputValue)
            if n < 0:
                self.resultValue = "Error: Negative input"
            else:
                self.resultValue = f"Factorial: {math.factorial(n)}"
        except ValueError:
            self.resultValue = "Error: Invalid number"
```

```qml
// main.qml — UI only; dados e ações via backend
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    width: 640
    height: 480
    visible: true
    title: qsTr("QML + Python backend")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20

        TextField {
            Layout.fillWidth: true
            placeholderText: qsTr("Enter a number")
            text: backend.inputValue
            onTextChanged: backend.inputValue = text
        }
        Button {
            Layout.fillWidth: true
            text: qsTr("Calculate factorial")
            onClicked: backend.calculateFactorial()
        }
        Label {
            Layout.fillWidth: true
            text: backend.resultValue
        }
    }
}
```

Entry típico: `QQmlApplicationEngine` + `rootContext().setContextProperty("backend", backend)` (ou registo de tipos, conforme o projeto).

---

## 3. Tipagem e estilo Python

- Type hints em código Python (incl. parâmetros, retornos, APIs expostas ao QML).
- **snake_case** para funções/variáveis Python; propriedades/slots expostos ao QML seguem as convenções Qt/PySide6 dos decoradores.
- Formatação / lint do projeto (ex.: **Black**, **Ruff**); **mypy** quando existir configuração.

---

## 4. Estilo, tema e HiDPI

- **HiDPI:** muitas apps chamam `app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)` para ícones/SVG mais nítidos (avaliar no `main` conforme versões Qt).
- **Temas de terceiros** (ex.: `qtvscodestyle`): **não** adicionar ao projeto sem pedido explícito do utilizador e entrada em dependências.

---

## 5. Higiene de sinais e slots

- Sintaxe `signal.connect(slot)`.
- Evitar lambdas em loops que capturem variáveis por referência incorreta; usar **`functools.partial`** ou métodos `@Slot(int)` etc.

```python
from functools import partial

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget


class MyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        for i in range(5):
            button = QPushButton(f"Button {i}")
            layout.addWidget(button)
            button.clicked.connect(partial(self._handle_button_with_arg, i))

    @Slot(int)
    def _handle_button_with_arg(self, index: int) -> None:
        print(f"Button {index} clicked!")
```

---

## 6. Desempenho e concorrência

- **Nunca** executar I/O bloqueante, esperas longas ou CPU intensiva **na thread da GUI**.
- Desviar trabalho para **QThread**, **QRunnable** + **QThreadPool**, ou APIs assíncronas compatíveis com o event loop Qt; actualizar UI só via sinais / `QMetaObject.invokeMethod` com tipos queued quando necessário.
- Para listas/modelos grandes, considerar modelos Qt (`QAbstractListModel`, etc.) em vez de reconstruir toda a árvore QML em cada alteração.
