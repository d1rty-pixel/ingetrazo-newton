# Newton

Newton ist eine Physik-Extension für den 3D-Modellierer [IngeTrazo](https://github.com/ingelibre/ingetrazo). Sie greift die Idee von SketchyPhysics auf: Gruppen und Komponenten eines Modells werden zu Körpern, die fallen, kollidieren, sich an Achsen drehen oder verschieben und von Motoren angetrieben werden. Die Simulation läuft direkt im Modell und lässt sich jederzeit auf den Ausgangszustand zurücksetzen.

Version 0.14.0 · für IngeTrazo 0.6.0 (Extension API 2) · Physik mit [MuJoCo](https://mujoco.org) 3.3.7 · Lizenz GPL-3.0-or-later

## Was Newton kann

- **Körper:** beweglich, fest oder ausgenommen; Masse, Reibung, Rückprall und Kollisionsform (Box, Kugel, konvexe Hülle, Teilkomponenten).
- **Achsen:** Dreh- und Linearachsen direkt im Modell platzieren, mit Anschlägen, Servo- oder Motorantrieb und Kraftlimit.
- **Bezugskörper:** Teile hängen an anderen Teilen und folgen ihnen beim Bearbeiten und in der Simulation.
- **Verbindungen:** Kugel-, Bolzen- und starre Verbindungen schließen Mechanismen wie einen Kurbeltrieb.
- **Achskopplung:** mehrere Achsen folgen einem gemeinsamen Regler, etwa zwei Greiferbacken.
- **Seile und Kabel:** offene Linienzüge werden zu biegsamen, längenfesten Strängen.
- **Steuerpult:** benannte Regler für alle Antriebe; passive Körper lassen sich mit der Maus ziehen.
- **Profile:** wiederverwendbare Parametersätze für Körper und Antriebe.

Noch nicht enthalten sind unter anderem Kugel- und Universalgelenke als Achsen, Replay, Magnetismus, Auftrieb und die Skripte von SketchyPhysics. Alle Grenzen stehen im [Handbuch](docs/handbuch.md#grenzen).

## Voraussetzungen

- IngeTrazo 0.6.0 (Windows-Installation oder Flatpak unter Linux)
- ein separates **Python 3.12 (64 Bit)** mit `mujoco==3.3.7`. Newton startet die Physik in diesem Python als eigenen Prozess; IngeTrazo selbst bringt kein passendes Python mit.

## Installation

### Windows

```powershell
.\scripts\setup-runtime.ps1 -Python 'C:\Pfad\zu\Python312\python.exe'
.\scripts\install-local.ps1
```

`setup-runtime.ps1` legt die Umgebung `.venv` im Projektordner an. `install-local.ps1` kopiert die Extension nach `%APPDATA%\ingetrazo\plugins\newton` und trägt den Python-Pfad in `runtime.json` ein. Eine bestehende Installation aktualisiert `install-local.ps1 -Update`; die vorherige Fassung landet unter `.backups`. Eine vorhandene Umgebung mit MuJoCo lässt sich mit `-Python 'C:\Pfad\zur\Umgebung\Scripts\python.exe'` angeben.

### Linux (Flatpak)

Es gibt noch kein Installationsskript. Von Hand:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mujoco==3.3.7
target=~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins/newton
mkdir -p "$target"
cp newton/*.py "$target"/ && cp -r newton/i18n "$target"/
printf '{"python": "%s"}\n' "$PWD/.venv/bin/python" > "$target/runtime.json"
```

Das Flatpak darf auf das Home-Verzeichnis zugreifen und kann die `.venv` deshalb direkt starten.

### Nach der Installation

IngeTrazo vollständig neu starten und **Extensions → Newton…** öffnen. Die Newton-Toolbar lässt sich über die normale Toolbar-Verwaltung einblenden. Die `.venv` muss erhalten bleiben, solange Newton sie benutzt. Nach einem Umzug wird der Python-Pfad unter **Preferences → Newton → Runtime** neu gewählt.

## Erste Schritte

1. Eine Gruppe oder Komponente auswählen.
2. In der Newton-Toolbar **Drehachse** oder **Linearachse** anklicken.
3. Im Modell den Dreh- bzw. Startpunkt anklicken, dann die Richtung anklicken oder **X**, **Y** oder **Z** drücken. **Esc** bricht ab.
4. In der Newton-Sidebar Verhalten und Antrieb einstellen. Änderungen gelten sofort und lassen sich rückgängig machen.
5. **Start** drücken. Passive Körper mit der linken Maustaste ziehen, Antriebe über das Steuerpult bewegen. **Reset** stellt das Originalmodell wieder her.

Fertige Beispiele liegen unter [`models/`](models) und sind in [docs/beispielmodelle.md](docs/beispielmodelle.md) beschrieben.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/handbuch.md](docs/handbuch.md) | Bedienung aller Funktionen, technische Hinweise und Grenzen |
| [docs/beispielmodelle.md](docs/beispielmodelle.md) | Die mitgelieferten Modelle und ihre Prüfwerte |
| [docs/known-issues.md](docs/known-issues.md) | Known bugs and observations (English) |
| [docs/backlog.md](docs/backlog.md) | Agreed follow-up work (English) |
| [docs/testergebnisse.md](docs/testergebnisse.md) | Prüfprotokoll je Version |
| [docs/recherche.md](docs/recherche.md) | Ursprüngliche Recherche zu SketchyPhysics und IngeTrazo |
| [AGENTS.md](AGENTS.md) | Development setup, tests and conventions (English) |

## Lizenz

GPL-3.0-or-later, siehe [LICENSE](LICENSE). MuJoCo und weitere Abhängigkeiten werden separat installiert und behalten ihre eigenen Lizenzen. Das gepackte ZIP enthält keine Python- oder MuJoCo-Binärdateien.
