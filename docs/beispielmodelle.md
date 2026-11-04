# Beispielmodelle

Die Modelle liegen unter [`models/`](../models). Sie lassen sich in IngeTrazo direkt öffnen. Die Skripte unter `scripts/` erzeugen einige davon neu und öffnen sie in einem Testfenster der Entwicklungsumgebung (siehe [AGENTS.md](../AGENTS.md)).

| Modell | Zeigt |
|---|---|
| `Domino-30-Steine.igz`, `Domino-30-Steine-mit-Pendel.igz` | Flächige Kontakte, Dominosteine kommen zur Ruhe |
| `Gelenkkette.igz` | Zwölf starre Glieder mit passiven Drehgelenken |
| `Industrieroboter-3-Achsen.igz`, `Industrieroboter-mit-Drehgreifer.igz`, `Industrieroboter-mit-Synchrongreifer.igz` | Drehservos, Steuerpult, Achskopplung |
| `Kollisionen-Testmodell.igz` | Kollisionsausnahmen und konvexe Hülle |
| `Kurbeltrieb-mit-Energiekette.igz`, `Kurbeltrieb-mit-Schleppkette.igz` | Motor, Kurbeltrieb, Kabel in einer Kette |
| `Schleppkette-mit-Kabel.igz`, `Seil-und-Kabel.igz` | Seile und Kabel |
| `Sonne-und-Planet.igz` | Anziehung und Startgeschwindigkeit |

## Kurbeltrieb mit Energiekette

Die überarbeitete Fassung **models/Kurbeltrieb-mit-Energiekette.igz** ersetzt die überlappenden geschlossenen Kanalstücke durch 22 offene Glieder. Jedes Glied besteht aus zwei abgerundeten Seitenlaschen mit Gelenkbünden und zwei kurzen Querstegen; die Laschen wechseln ihre seitliche Einbauebene. Ein Glied ist ein einziger starrer Körper mit vier Kollisionsformen. Nur unmittelbar verbundene Lagerpartner sind von gegenseitigem Kontakt ausgenommen; Kontakte zwischen nicht benachbarten Gliedern bleiben aktiv. Das orientiert sich am grundsätzlichen Aufbau aus Seitenlaschen und Querstegen: [igus Energieketten-Wiki](https://www.igus.eu/energy-chain/wiki).

Die neue Kollisionsform **Teilkomponenten** berechnet jede direkt untergeordnete Gruppe/Komponente als eigenen konvexen Teilkörper. So bleiben die Öffnungen zwischen den Teilen frei; es wird keine gemeinsame Hülle über die gesamte Rahmenöffnung gelegt. Die Gesamtmasse wird auf die Teilkörper verteilt. Die Kollisionsanzeige zeichnet alle Teilformen. Ohne untergeordnete Gruppen wird die Auswahl mit einer verständlichen Meldung abgelehnt.

Das Pleuel liegt jetzt in einer um 105 mm versetzten Ebene vor dem Rad auf einem verlängerten Kurbelzapfen mit Sicherung. Zwischen dem eigentlichen Radkörper einschließlich Nabe und dem Pleuel bleiben 40 mm axialer Abstand. Die Kurbel-/Kolbengeometrie und der 300-mm-Hub bleiben erhalten. Die Kraftübertragung erfolgt weiterhin über reale Gelenk- und Verbindungsbedingungen.

Im viersekündigen Kontaktvergleich sinkt die mittlere Kontaktzahl von 78 auf 47,6; die bisherigen Kette-gegen-Kette-Kontakte verschwinden. Das Pleuel/Rad-Paar hatte bereits vorher eine Lager-Kollisionsausnahme und erzeugte keine aktiven Solver-Kontakte, obwohl sich seine Darstellung überschnitt. Die neue Geometrie beseitigt diese sichtbare Überschneidung. Der Vergleichslauf benötigt 5,72 statt 7,82 Sekunden für vier Simulationssekunden auf diesem Rechner; die 24-Sekunden-Prüfung bestätigt weiterhin Hub und Kabelführung. Die frühere Modellfassung bleibt für Vergleiche unter ihrem bisherigen Dateinamen erhalten.

Der zweisekündige Newtonvergleich am Kurbeltrieb ergab auf diesem Rechner etwa **0,28× Echtzeit vorher**, **0,54× mit Ausgewogen** und **0,91× mit Schnell**. Das sind reine Worker-Messungen; Darstellung, Rechnerlast und andere Modelle verändern die tatsächlich erreichte Geschwindigkeit. `scripts/benchmark_newton.py --quality=balanced` wiederholt den Versuch. Der vollständige 24-Sekunden-Test mit Ausgewogen erhält den 300-mm-Hub und die Kabelführung.

## Kurbeltrieb mit Schleppkette

Das zusätzliche Modell **Kurbeltrieb-mit-Schleppkette.igz** verbindet einen fest montierten Elektromotor über seine Welle mit einem Speichenrad. Ein äußerer Kurbelzapfen und ein passives Pleuel treiben den Kreuzkopf samt Kolbenstange. Der Hub von 300 mm bewegt das Obertrum der unten festgehaltenen Schleppkette. Ein durchgehendes orangefarbenes Netzkabel verläuft von der Steckdose durch die Kette und anschließend über eine freie Reserveschleife zurück zum feststehenden Motor. Es ist an Steckdose und Motor befestigt; die bewegliche Kettenführung wirkt durch Kontakte. Das Steuerpult enthält **Antriebswelle · Motordrehzahl**; der Kolben hat keinen eigenen Antrieb. Die Drehzahl reagiert auf die mechanische Last.

Der Prüflauf über 24 Sekunden bestätigt mindestens eine volle Radumdrehung, etwa −136,6 bis +163,4 mm Hub und weniger als 0,1 mm Abweichung zur geometrischen Kurbelgleichung. Die Achsen sind zunächst ausgeblendet. Version 0.10.1 überträgt Kollisionsausnahmen eines Seils/Kabels auf alle seine Abschnitte, etwa für idealisierte Stecker und Lagergehäuse. Kontakte im eigentlichen Schleppkettenkanal bleiben aktiv.

## Seile, Kabel und Gelenkketten

Die drei neuen Modelle liegen unter `models`:

- **Seil-und-Kabel.igz**: zwei jeweils 2 m lange, einseitig eingespannte Stränge mit gleichen Endgewichten. Orange zeigt das weiche Seil, Blau das steifere Kabel; beide kollidieren mit der Unterlage.
- **Gelenkkette.igz**: zwölf starre Glieder mit passiven Drehgelenken. Diese erste Gelenkkette bewegt sich in einer Ebene; sie berechnet keine frei ineinandergreifenden Metallringe.
- **Schleppkette-mit-Kabel.igz**: 22 starre Führungsglieder mit Winkelanschlägen und einem Schlitten mit Positionsantrieb **Verfahrweg**. Das orange Kabel ist separat biegsam und kollidiert mit den überlappenden Kanalflächen. Seiten und Stege sind transparent, damit es sichtbar bleibt. Der Schlitten verbindet beide Enden mechanisch; das Kabel ist nicht an jedes Glied gebunden. Die Modellgrenzen erlauben −150 bis +250 mm, geprüft sind Vor-/Rückfahrt zwischen −100 und +200 mm. Kleine Lastabweichungen des realen Schlittenwerts bleiben möglich. Die Achsen liegen auf dem zunächst ausgeblendeten Layer **Newton Axes**.

Öffnen eines Testfensters: `.venv\Scripts\python.exe scripts/flexible_demos.py carrier --existing --open` (statt `carrier` auch `rope` oder `chain`). Die Testfenster verwenden normale Schwerkraft −9,81 m/s² und die modellierte Unterlage. Im regulären IngeTrazo diese Werte unter **Preferences → Newton → Simulation** prüfen, falls vorher das Sonnenmodell mit Null-Schwerkraft lief.

## Kollisionen-Testmodell

**`models/Kollisionen-Testmodell.igz`** zeigt drei Fälle: Ein blauer Würfel landet auf einer Platte, ein orangefarbener Würfel fällt durch seine ausgenommene Platte bis zur Unterlage. An einem Bauteil mit Öffnung zeigt die konvexe Hülle die aufgefüllte Öffnung. Öffnen: `python scripts/collision_demo.py --existing --open`.

## Sonne und Planet

Das Testmodell [Sonne und Planet](../models/Sonne-und-Planet.igz) enthält zwei frei bewegliche Kugeln mit Massen 100 und 5 kg, Abstand 4 m und einem absichtlich vergrößerten G = 0,16 m³/(kg·s²). Die Umlaufzeit beträgt etwa 12,26 s. Beide kreisen um ihren gemeinsamen Schwerpunkt; die Sonne ist nicht festgehalten. Schwerkraftvektor, Boden und Dämpfung sind ausgeschaltet. `scripts/solar_system.py --existing --open` öffnet das Modell mit diesen globalen Vorgaben in einem eigenen Testfenster. Beide Körper speichern zusätzlich Null-Schwerkraft und ausgeschalteten Boden als Overrides, sodass das Modell auch mit anderen globalen Vorgaben funktioniert.

## Industrieroboter mit Synchrongreifer

Das Modell **`models/Industrieroboter-mit-Synchrongreifer.igz`** besitzt vier Drehservos und einen gemeinsamen Regler **Greifer Öffnung**. Er zeigt den Abstand der Backen in Millimetern: 105 mm offen bis 5 mm geschlossen. Beide Backen bewegen sich symmetrisch. Erzeugen und separat öffnen: `python scripts/robot_arm.py --gripper --open`.
