# Newton — Recherche zu SketchyPhysics und IngeTrazo

Stand: 3. November 2026. Recherche und Quellcodeanalyse, noch kein Laufzeittest und keine implementierte Physik-Extension.

Nachtrag zur anschließenden Umsetzung: Newton ist inzwischen implementiert; siehe [Handbuch](handbuch.md). Als Backend wird MuJoCo 3.3.7 verwendet, nachdem die Installation von PyBullet an fehlenden offiziellen Windows-Binärpaketen und fehlenden C++-Buildwerkzeugen scheiterte. Die folgenden Abschnitte halten den ursprünglichen Recherchestand fest.

## Ergebnis

Ein funktionaler Nachbau ist technisch plausibel. Eine eigene Physik-Engine ist dafür nicht erforderlich. IngeTrazo liefert Modellgeometrie, Komponenten, Python-/Qt-Oberfläche und Erweiterungspunkte. Eine zusätzliche Engine berechnet Bewegung und Kontakte. Die eigentliche Entwicklungsarbeit liegt im Adapter, in der Bedienung und in einer zuverlässigen Simulation innerhalb des Modellierprogramms.

Untersucht wurde der öffentliche IngeTrazo-Quellstand `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`, zugleich Release v0.6.0 vom 1. November 2026. Eine lokale Referenzkopie liegt unter `ingetrazo-source/`. Die hier vorgeschlagene Architektur ist eine Schlussfolgerung aus dem Quellcode, keine bereits nachgewiesene Produktfunktion. [Release](https://github.com/ingelibre/ingetrazo/releases/tag/v0.6.0)

## Was SketchyPhysics ausmacht

SketchyPhysics verbindet gruppierte 3D-Objekte mit interaktiver Starrkörperphysik. Zentral sind Start/Pause/Reset, ein Inspector, verbundene Gelenke und direktes Ziehen während der Simulation. Körper können statisch, eingefroren, ignoriert oder ohne Kollision sein. Steuerungen umfassen Schieberegler, Eingaben und Formeln. Hinzu kommen Schubkräfte, Magnetkräfte, Emitter und eine Auftriebsebene. Die dokumentierten Gelenke umfassen Hinge, Servo, Motor, Slider, Piston, Gyro, Fixed, Corkscrew, Spring, Ball und Universal. [Historische Projekt-FAQ](https://community.sketchucation.com/topic/111111/sketchyphysics3-faq)

Spätere Versionen ergänzten beziehungsweise verbesserten zusammengesetzte Kollisionskörper, konvexe Hüllen, statische Meshes, Schwerpunkt-/Massefunktionen, kontinuierliche Kollisionserkennung, Kontakt-Ereignisse und Aufzeichnung einschließlich Kamera. Die Autoren dokumentieren dabei auch Probleme mit Skalierungen und gespiegelten Körpern: Diese Fälle gehören ausdrücklich in unseren Adaptertest. [Entwicklerbeitrag zu 3.5.6](https://community.sketchucation.com/topic/147275/sketchyphysics-3-5-6-26-january-2015)

Die Projektseite nennt 3.7.4 vom 26. November 2017 als letzten Stand und beschränkt ihn auf SketchUp mit 32 Bit. Dort sind außerdem Raycasts, Impulse, Skriptfunktionen und Sound dokumentiert. MSPhysics ist ein eigenständiger Nachfolger mit anderem Umfang; dessen 14 Gelenktypen dürfen nicht pauschal als ursprüngliche SketchyPhysics-Funktionen gelten. [SketchyPhysics-Projektseite](https://sketchy-physics.github.io/page/index.html), [MSPhysics vom Entwickler](https://github.com/AntonSynytsia/MSPhysics)

## Welche Teile IngeTrazo bereitstellt

Die dokumentierte Extension-API hat Version 2 und ist während 0.x veränderlich. Einstieg ist `setup(app)`. Relevante Funktionen sind:

| Bedarf | Vorhandener Zugang |
|---|---|
| Inspector und Steuerpanel | `add_panel`, eigene Qt-Widgets und Dialoge |
| Befehle und Kontextmenüs | `add_menu`, `add_menu_action`, `add_context_menu` |
| Parameter im Projekt | `document_data`, `set_document_data` |
| Parameter am Körper | `group.ext[app.key]` |
| Gelenkmarkierungen | `add_overlay`, `world_to_pixels`, `add_pickable` |
| Platzierung | `add_snap_provider`, Tool-Basisklasse |
| Dokumentwechsel | `on_document_changed`, `on_document_closed` |
| Getrennte Simulationsszene | `enter_workspace`, `leave_workspace` |

Modelländerungen sollen über die History laufen. Hintergrundberechnung darf das Dokument nicht direkt verändern; Ergebnisse müssen in den GUI-Thread zurückgegeben werden. Menü-Tools werden als einmalige Aktionen aktiviert: Ein interaktives Gelenkwerkzeug benötigt zusätzlich eine geeignete Aktivierung im Viewport. [Plugin-Leitfaden](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/docs/plugins.md), [ExtensionApp](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/views/extension_api.py), [Tool-Basis](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/tools/base.py)

Im untersuchten Core und in den Runtime-Abhängigkeiten ist keine Starrkörper-Engine vorhanden. Komponenten besitzen dagegen Transformationsmatrizen (`xform`); Gruppen haben persistente `uid`-Kennungen. Beides eignet sich für die Zuordnung zwischen Modell und Engine. Klassische Gruppen und Instanzen behandeln ihre Geometrie unterschiedlich. Der Adapter muss daher lokale Koordinaten, verschachtelte Transformationen und Körper-Schwerpunkte vereinheitlichen. [Gruppenimplementierung](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/core/group.py), [Abhängigkeiten](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/requirements.txt)

### Die entscheidende Rendering-Grenze

`add_overlay` ist ein QPainter-Overlay über dem Bild. Es ist kein allgemeiner 3D-Renderer mit Tiefentest. Für beschriftete Gelenke ist es geeignet; für viele schattierte Physikkörper allein nicht.

Der Viewport besitzt intern `begin_groups_preview` und `set_groups_preview_matrix`. Dabei werden die ausgewählten Körper zusammengefasst und durch eine gemeinsame Vorschau-Matrix gezeichnet. Das löst eine gemeinsame Verschiebung oder Rotation, aber keine unabhängigen Posen vieler Körper. Eine öffentlich dokumentierte Batch-Schnittstelle für temporäre Einzeltransformationen habe ich im geprüften Stand nicht gefunden. [Viewport, ab Zeile 6694](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/views/viewport.py#L6694)

Vorschlag: Beim Start eine eigene Simulationsszene erzeugen und im Workspace anzeigen. Nur deren Komponentenmatrizen aktualisieren; das Originalmodell bleibt geparkt. Beim Reset wird der Workspace verlassen. Eine Aktion „Pose übernehmen“ schreibt die gewählte Endlage als einen rückgängig machbaren Schritt ins Original. Das Workspace-Protokoll unterstützt diese Trennung grundsätzlich. Cache-Aktualisierung, Picking und Geschwindigkeit der bewegten Szene müssen praktisch verifiziert werden. Der Workspace allein ist noch keine schnelle Animationsschnittstelle.

## Machbarkeitsmatrix

Die Bewertungen bedeuten: technisch mit zusätzlicher Engine beziehungsweise eigenem Erweiterungscode abbildbar. Sie sind keine Zusage, dass IngeTrazo diese Funktionen bereits enthält.

| Funktionsfamilie | Einschätzung | Benötigte Umsetzung |
|---|---|---|
| Fallende Körper, Kontakte, Schwerkraft | Gut | Engine, Körperadapter, Positionsübertragung |
| Masse, Reibung, Rückprall, Dämpfung | Gut | Physikparameter und Inspector |
| Statisch, ignoriert, keine Kollision | Gut | Körpermodus und Kollisionsfilter |
| Eingefroren/Schlafen und Aufwecken | Gut, Semantik abstimmen | Engine-Aktivierung und Auslöser |
| Box, Kugel, Zylinder, Kapsel | Gut | Primitive Kollisionsformen |
| Konvexe und zusammengesetzte Körper | Gut, zusätzlicher Aufwand | Hüllen beziehungsweise Zerlegung; eigene Kollisionsvorschau |
| Beliebige bewegte konkave Meshes | Aufwendig | Enginegerechte Zerlegung; Löcher nicht durch eine einzige Hülle verschließen |
| Statische Umgebung | Gut | Dreiecksmesh oder vereinfachte Collider |
| Hinge, Motor, Servo | Gut, Backend prüfen | Drehgelenk plus Geschwindigkeits-/Positionsregelung |
| Slider, Piston, Spring | Gut, Backend prüfen | Lineargelenk, Antrieb, Feder und Dämpfung |
| Ball, Universal, Corkscrew, Gyro | Machbar, aufwendiger | Passende Constraints oder deren Kombination |
| Fixed und brechende Verbindung | Machbar | Verbindung plus Belastungsschwelle und Auflösen |
| Schub und Magneteffekte | Gut | Eigene Kraftmodelle auf der Engine |
| Emitter | Machbar | Körperlebenszyklus, Kopien, Limits und Darstellung |
| Auftrieb | Machbar, zusätzliche Logik | Verdrängungsnäherung und Kräfte; eigene Flüssigkeitssimulation unnötig für einfache Ebene |
| Mausziehen | Machbar | Picking, Zielpunkt und temporärer Feder-/Zugconstraint |
| Tastatur, Schieberegler, Gamepad | Machbar | Eingaberouting; Gamepad gesondert anbinden |
| Skripte und Kontakt-Ereignisse | Machbar | Eigene Python-Ereignisschnittstelle |
| Replay und Animationsexport | Machbar | Posen aufzeichnen; Bild-/Videoexport separat integrieren |
| Bestehende SketchyPhysics-Modelle | Nicht automatisch kompatibel | Separater Metadatenimport und Übersetzung; Ruby-/SketchUp-Code benötigt Portierung |

Insbesondere gilt: Geometrie aus einer `.skp` zu öffnen bedeutet nicht, dass Gelenke, Physikattribute oder Ruby-Skripte anschließend funktionieren. Dafür wurde kein vorhandener SketchyPhysics-Importer nachgewiesen.

## Fertige Physik-Engines

### Bullet / PyBullet als erster Prototyp-Kandidat

Bullet ist eine fertige Physik-Engine; PyBullet stellt Python-Zugriff bereit. Damit entfällt die Entwicklung von Kontaktlöser, Kollisionsdetektion und grundlegender Dynamik. Das offizielle Beispiel demonstriert auch veränderbare Constraints. [Bullet-Projekt](https://github.com/bulletphysics/bullet3), [Constraint-Beispiel](https://github.com/bulletphysics/bullet3/blob/master/examples/pybullet/examples/constraint.py)

Meine Empfehlung ist, zunächst PyBullet als austauschbares Backend zu erproben. Wichtig: „Bullet unterstützt Gelenke“ garantiert nicht, dass die Python-Schnittstelle jede frei im Modell erstellte Verbindung direkt anbietet. Frei verbundene Einzelkörper, geschlossene Mechanismen, Motoren und Federverhalten müssen als konkrete Fälle geprüft werden. Falls die Bindings einschränken, kann ein anderes Backend oder eine native Brücke sinnvoller sein.

### MuJoCo als Alternative für Mechanismen

MuJoCo besitzt Gelenke, Aktuatoren und zusätzliche Bindungen. Sein Modell ist grundsätzlich als Körperbaum organisiert; mehrere primitive Gelenke können zusammengesetzte Beweglichkeiten bilden. Für frei zusammengesteckte Mechanismen und Schleifen braucht es eine bewusste Übersetzung. [Offizielle Modellierungsdokumentation](https://mujoco.readthedocs.io/en/stable/modeling.html)

Das macht MuJoCo zu einem ernsthaften Vergleichskandidaten, falls motorisierte Mechanik wichtiger wird als frei hinzufügbare Spielobjekte. Die endgültige Auswahl sollte nach kleinen Funktionsproben erfolgen, nicht allein anhand der Featurelisten.

### Was wir den Engines „beibringen“ müssen

1. Welche Modellgruppe welcher Körper ist und ob sie beweglich ist.
2. Welche vereinfachte Kollisionsform verwendet wird. Sichtbare Geometrie und Kollisionsgeometrie dürfen verschieden sein.
3. Masse, Schwerpunkt, Trägheit, Materialparameter und Anfangsgeschwindigkeit.
4. Welche zwei Körper ein Gelenk verbindet; lokale Anker, Achsen, Grenzen und Antriebswerte.
5. Umrechnung der Engine-Pose zurück in die Modelltransformation. Schwerpunkt und Modellursprung sind oft verschieden.
6. Verhalten von Start/Pause/Reset, Eingaben, gespeicherten Parametern und Replay.

Vorschlag: SI-Einheiten verwenden, feste Physikschritte mit Zeitakkumulator und davon getrennte Bildaktualisierung. Neue Körperdaten und Gelenke speichern, laufende Engine-Handles und jeden Zeitschritt dagegen nur im Arbeitsspeicher halten. Kopierte Körper brauchen eigene Identitäten und korrekt neu zugeordnete Gelenkverweise.

## Lokal installieren und testen

### Mit installierter Windows-Version

1. In IngeTrazo `Extensions → Open plugins folder` öffnen.
2. Eine einzelne `.py` oder ein Paketverzeichnis dort ablegen.
3. Bei einem Paket muss `__init__.py` unmittelbar im Paketordner liegen, beispielsweise:

```text
%APPDATA%\ingetrazo\plugins\
  newton\
    __init__.py
    panel.py
    adapter.py
    backends\
      __init__.py
      bullet.py
```

4. IngeTrazo vollständig neu starten. Ein ZIP wird für die lokale Entwicklung vorher entpackt; ein zusätzlicher äußerer ZIP-Ordner verhindert die Erkennung.
5. Ladefehler erscheinen im Extensions-Menü; vollständige Fehler stehen im Log. Ein `.disabled`-Marker in einem Paket verhindert dessen Laden.

Die Erkennung erfolgt beim Start. Ein dokumentiertes allgemeines Hot-Reload ist nicht vorhanden. Pakete sollten relative Imports verwenden: Der Loader verwendet private Modulnamen und fügt den Pluginordner nicht global zu `sys.path` hinzu. Für private Tests ist kein Katalogeintrag erforderlich. [Loader-Quellcode](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/core/extensions.py)

### Entwicklungsumgebung aus dem Quellcode

Für ein natives Python-Backend ist zunächst eine eigene Python-Umgebung am bequemsten. Der Windows-Build verwendet Python 3.12. Beispiel nach Installation von Python 3.12, im Ordner `ingetrazo-source`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Erst für den PyBullet-Prototyp:
.\.venv\Scripts\python.exe -m pip install pybullet
.\.venv\Scripts\python.exe main.py
```

Diese Befehle wurden hier nicht ausgeführt. Abhängigkeiten und passende Wheels sind vor dem ersten Lauf zu prüfen. Den eigenen Plugin-Code kann man für diese Entwicklungsinstanz unter `<app>/plugins/` ablegen; identische Plugin-Namen im Benutzerordner vermeiden, weil das mitgelieferte zuerst gefunden wird. Die Python-Konsole in IngeTrazo (`Ctrl+Shift+P`) eignet sich für kleine Geometrie- und API-Versuche. [Start aus Quellcode](https://github.com/ingelibre/ingetrazo/tree/v0.6.0), [Windows-Build](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/.github/workflows/build-windows.yml)

Ein `pip install` in dieser Umgebung installiert nichts in die Python-Laufzeit einer bereits paketierten IngeTrazo-EXE. Für die spätere Auslieferung braucht es entweder passende mitgelieferte native Module einschließlich Bibliotheken oder einen separat gestarteten Physikprozess. Letzterer kann die Python-/ABI-Abhängigkeit vom Host reduzieren, erfordert aber eine Prozessschnittstelle. Das Plugin-System dokumentiert derzeit keinen fertigen allgemeinen Abhängigkeitsinstaller.

## Sinnvolle erste Umsetzung

Vor einem großen Nachbau sollten drei technische Proben abgeschlossen werden:

1. **Darstellung:** 50 unabhängig bewegte Komponenten in einer Simulationsszene; Reset, Projektwechsel und Rückkehr zum Original funktionieren. Bildrate messen, keine vorab garantieren.
2. **Mechanik:** Zwei frei ausgewählte Körper über Hinge verbinden; Motor und Servo ergänzen. Zusätzlich einen geschlossenen Viergelenkmechanismus prüfen. Das entscheidet über die Engine-Bindings.
3. **Installation:** Derselbe Prototyp läuft sowohl aus Quellcode als auch mit der installierten Windows-Version samt Physikabhängigkeit.

Danach als erste nutzbare Version: statischer Boden, dynamische Gruppen, Box/Kugel/konvexe Hülle, Masse/Reibung/Rückprall, Start/Pause/Reset, ein Inspector und Hinge/Motor. Ein Turm fallender Würfel, ein Pendel und ein angetriebenes Rad bilden konkrete Abnahmeszenen. Piston, Feder, Mausziehen und Replay folgen anschließend. Magnetismus, Emitter, Auftrieb und Skriptkompatibilität sollten erst nach stabiler Grundlage hinzukommen.

Der größte offene Punkt ist somit die robuste Integration in IngeTrazo: Darstellung, Eingaben, Dokumentlebenszyklus und Auslieferung. Die grundlegende Physik können fertige Bibliotheken übernehmen.
