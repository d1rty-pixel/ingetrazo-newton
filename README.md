# Newton 0.14.0

Newton für **IngeTrazo 0.6.0 / Extension API 2**, Windows x64. Berechnung mit **MuJoCo 3.3.7** in einem separaten Python-Prozess. Die IngeTrazo-Core-Dateien werden nicht verändert.

Flächige Kontakte verwenden mehrere Kontaktpunkte und eine elliptische Reibungsberechnung. Ein konvexer Collider mit acht Ecken wird nur dann als exakter, räumlich ausgerichteter Quader berechnet, wenn alle Ecken den Quader mathematisch bestätigen. Andere Hüllen bleiben Hüllen. Damit kommen umgefallene Dominosteine zur Ruhe, ohne sie künstlich einzufrieren. Hintergrund: [MuJoCo 3.3.7, Kontaktoptionen](https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html#option-flag-multiccd).

Newton verwendet das Python-Paket `newton`, den Modellschlüssel `group.ext["newton"]`, den Settings-Präfix `newton/` und den reservierten Layer `Newton_Axes`. Es gibt keine Kompatibilitäts-Aliasse und keinen automatischen Import früherer Daten oder Einstellungen. Die mitgelieferten Modelle sind auf dieses Schema umgestellt.

## Am Modell arbeiten

### Offene Energiekette und getrennte Rad-/Pleuelebenen

Die überarbeitete Fassung **models/Kurbeltrieb-mit-Energiekette.igz** ersetzt die überlappenden geschlossenen Kanalstücke durch 22 offene Glieder. Jedes Glied besteht aus zwei abgerundeten Seitenlaschen mit Gelenkbünden und zwei kurzen Querstegen; die Laschen wechseln ihre seitliche Einbauebene. Ein Glied ist ein einziger starrer Körper mit vier Kollisionsformen. Nur unmittelbar verbundene Lagerpartner sind von gegenseitigem Kontakt ausgenommen; Kontakte zwischen nicht benachbarten Gliedern bleiben aktiv. Das orientiert sich am grundsätzlichen Aufbau aus Seitenlaschen und Querstegen: [igus Energieketten-Wiki](https://www.igus.eu/energy-chain/wiki).

Die neue Kollisionsform **Teilkomponenten** berechnet jede direkt untergeordnete Gruppe/Komponente als eigenen konvexen Teilkörper. So bleiben die Öffnungen zwischen den Teilen frei; es wird keine gemeinsame Hülle über die gesamte Rahmenöffnung gelegt. Die Gesamtmasse wird auf die Teilkörper verteilt. Die Kollisionsanzeige zeichnet alle Teilformen. Ohne untergeordnete Gruppen wird die Auswahl mit einer verständlichen Meldung abgelehnt.

Das Pleuel liegt jetzt in einer um 105 mm versetzten Ebene vor dem Rad auf einem verlängerten Kurbelzapfen mit Sicherung. Zwischen dem eigentlichen Radkörper einschließlich Nabe und dem Pleuel bleiben 40 mm axialer Abstand. Die Kurbel-/Kolbengeometrie und der 300-mm-Hub bleiben erhalten. Die Kraftübertragung erfolgt weiterhin über reale Gelenk- und Verbindungsbedingungen.

Im viersekündigen Kontaktvergleich sinkt die mittlere Kontaktzahl von 78 auf 47,6; die bisherigen Kette-gegen-Kette-Kontakte verschwinden. Das Pleuel/Rad-Paar hatte bereits vorher eine Lager-Kollisionsausnahme und erzeugte keine aktiven Solver-Kontakte, obwohl sich seine Darstellung überschnitt. Die neue Geometrie beseitigt diese sichtbare Überschneidung. Der Vergleichslauf benötigt 5,72 statt 7,82 Sekunden für vier Simulationssekunden auf diesem Rechner; die 24-Sekunden-Prüfung bestätigt weiterhin Hub und Kabelführung. Die frühere Modellfassung bleibt für Vergleiche unter ihrem bisherigen Dateinamen erhalten.

### Geschwindigkeit, Antriebe und Verbindungen

Das Steuerpult zeigt die tatsächlich erreichte Simulationsgeschwindigkeit als **× Echtzeit**. Bei Pause wird keine Wartezeit in die Messung eingerechnet. Ein Tooltip nennt Newtonzeit, Anzeigeaufbereitung, Antwortzeit des Prozesses, Kontaktzahl, Solver-Iterationen und interne Teilschritte. Die Anzeigeaufbereitung misst das Anwenden der Posen und UI-Signale, nicht die reine GPU-Zeichenzeit.

Unter **Preferences → Newton → Simulation → Qualität** stehen **Schnell**, **Ausgewogen** und **Präzise**. Die Auswahl gilt beim nächsten Start. Lange Kabelmechanismen verwenden bei Schnell/Ausgewogen einen CG-Solver mit elliptischer Reibung; Präzise verwendet Newton mit engerer Toleranz. Kollisionsgeometrie, Kabelauflösung und die für Stabilität erforderlichen Zeitschritte werden dabei nicht vereinfacht. Nach einem Rechenpaket werden nur die positionsabhängigen Daten erneuert, statt für die Ausgabe erneut das vollständige Gleichungssystem zu lösen.

Der zweisekündige Newtonvergleich am Kurbeltrieb ergab auf diesem Rechner etwa **0,28× Echtzeit vorher**, **0,54× mit Ausgewogen** und **0,91× mit Schnell**. Das sind reine Worker-Messungen; Darstellung, Rechnerlast und andere Modelle verändern die tatsächlich erreichte Geschwindigkeit. `scripts/benchmark_newton.py --quality=balanced` wiederholt den Versuch. Der vollständige 24-Sekunden-Test mit Ausgewogen erhält den 300-mm-Hub und die Kabelführung.

Geschwindigkeitsmotoren verwenden eine PI-Regelung mit Beschleunigungsvorsteuerung und Schutz vor dem Aufladen des Integrators am Kraftlimit. Dadurch gleicht der Motor Lasten aus, ohne sein eingestelltes Kraft-/Drehmomentlimit zu überschreiten. Im Steuerpult markiert **Limit** eine erreichte Begrenzung; der Istwert-Tooltip enthält Sollwert, aktuellen Rampenwert und Auslastung. Blockierte oder zu schwache Motoren bleiben physikalisch begrenzt.

Das neue Toolbar-Icon **Körper verbinden** erstellt eine zusätzliche Verbindung zwischen zwei Körpern. Einen Körper auswählen, bei Bedarf unter **Weitere Einstellungen → Mechanische Verbindung** den Typ wählen, den Gegenkörper anklicken und den gemeinsamen Verbindungspunkt platzieren. Ein **Kugelgelenk** lässt räumliche Drehungen frei. Für ein **Bolzengelenk** anschließend die Richtung anklicken oder X/Y/Z drücken. Eine **starre Verbindung** hält die relative Lage fest. So lassen sich geschlossene Mechanismen aufbauen, ohne die Bezugskörper-Hierarchie umzubauen.

Die violette Verbindungsmarkierung lässt sich mit dem Auswahlwerkzeug anklicken und anschließend ziehen. Vorschau und Esc-Abbruch ändern das Original nicht; Loslassen ergibt einen Undo-Schritt. Der Radiergummi entfernt die Verbindung und erhält beide Körper. Alternativ stehen Sidebar und Kontextmenü bereit. Punktkoordinaten sind direkt in Millimetern editierbar; Bolzen besitzen eine editierbare Achse. Die Markierungen gehören zur Sichtbarkeit von **Newton_Axes**. Seile/Kabel verwenden weiterhin ihre eigenen Endbefestigungen. Verbindungstyp, Befestigungspunkt und Bolzenachse werden in der `.igz` gespeichert.

### Seile, Kabel und Gelenkketten

Das zusätzliche Modell **Kurbeltrieb-mit-Schleppkette.igz** verbindet einen fest montierten Elektromotor über seine Welle mit einem Speichenrad. Ein äußerer Kurbelzapfen und ein passives Pleuel treiben den Kreuzkopf samt Kolbenstange. Der Hub von 300 mm bewegt das Obertrum der unten festgehaltenen Schleppkette. Ein durchgehendes orangefarbenes Netzkabel verläuft von der Steckdose durch die Kette und anschließend über eine freie Reserveschleife zurück zum feststehenden Motor. Es ist an Steckdose und Motor befestigt; die bewegliche Kettenführung wirkt durch Kontakte. Das Steuerpult enthält **Antriebswelle · Motordrehzahl**; der Kolben hat keinen eigenen Antrieb. Die Drehzahl reagiert auf die mechanische Last.

Der Prüflauf über 24 Sekunden bestätigt mindestens eine volle Radumdrehung, etwa −136,6 bis +163,4 mm Hub und weniger als 0,1 mm Abweichung zur geometrischen Kurbelgleichung. Die Achsen sind zunächst ausgeblendet. Version 0.10.1 überträgt Kollisionsausnahmen eines Seils/Kabels auf alle seine Abschnitte, etwa für idealisierte Stecker und Lagergehäuse. Kontakte im eigentlichen Schleppkettenkanal bleiben aktiv.

**Weitere Einstellungen → Flexibler Werkstoff** ergänzt **Starr**, **Seil** und **Kabel**. Für ein eigenes Seil/Kabel eine offene Linie oder einen zusammenhängenden offenen Linienzug zeichnen, gruppieren und den Werkstoff wählen. Eine einzelne Gerade wird automatisch in 20 Abschnitte unterteilt. Verzweigungen, geschlossene Schleifen und flächige Gruppen werden mit einer verständlichen Meldung abgelehnt. Bearbeitungen am ursprünglichen Linienzug werden beim nächsten Simulationsstart eingelesen; Gruppenbewegungen und Undo bleiben erhalten.

MuJoCos mitgeliefertes Plugin `mujoco.elasticity.cable` berechnet Biegung und Torsion einer nicht dehnbaren Folge räumlicher Kugelgelenke. Das Seil startet mit kleinem Biege-/Torsionsmodul, das Kabel mit höheren Werten; beide bleiben einstellbar. Radius und Gesamtmasse bestimmen zusätzlich das Verhalten. Der Anfang kann eingespannt, gelenkig befestigt oder frei sein. Ein starrer Bezugskörper bewegt die Anfangsbefestigung mit; das Ende lässt sich an einem weiteren starren Körper befestigen. Frei bewegliche Abschnitte lassen sich während der Simulation greifen. Reset stellt das Originalmodell wieder her. Die Flexibilität wird in der `.igz` gespeichert.

Für steifere und feinere Kabel verwendet der Worker automatisch kleinere interne Zeitschritte. Die nach außen gemeldete Simulationszeit und die Antriebsrampen bleiben gleich. Zu steife Konfigurationen werden mit einem Hinweis auf geringere Steifigkeit oder weniger Abschnitte abgewiesen. Eine numerisch instabile Simulation meldet einen Fehler.

Die drei neuen Modelle liegen unter `models`:

- **Seil-und-Kabel.igz**: zwei jeweils 2 m lange, einseitig eingespannte Stränge mit gleichen Endgewichten. Orange zeigt das weiche Seil, Blau das steifere Kabel; beide kollidieren mit der Unterlage.
- **Gelenkkette.igz**: zwölf starre Glieder mit passiven Drehgelenken. Diese erste Gelenkkette bewegt sich in einer Ebene; sie berechnet keine frei ineinandergreifenden Metallringe.
- **Schleppkette-mit-Kabel.igz**: 22 starre Führungsglieder mit Winkelanschlägen und einem Schlitten mit Positionsantrieb **Verfahrweg**. Das orange Kabel ist separat biegsam und kollidiert mit den überlappenden Kanalflächen. Seiten und Stege sind transparent, damit es sichtbar bleibt. Der Schlitten verbindet beide Enden mechanisch; das Kabel ist nicht an jedes Glied gebunden. Die Modellgrenzen erlauben −150 bis +250 mm, geprüft sind Vor-/Rückfahrt zwischen −100 und +200 mm. Kleine Lastabweichungen des realen Schlittenwerts bleiben möglich. Die Achsen liegen auf dem zunächst ausgeblendeten Layer **Newton_Axes**.

Öffnen eines Testfensters: `.venv\Scripts\python.exe scripts/flexible_demos.py carrier --existing --open` (statt `carrier` auch `rope` oder `chain`). Die Testfenster verwenden normale Schwerkraft −9,81 m/s² und die modellierte Unterlage. Im regulären IngeTrazo diese Werte unter **Preferences → Newton → Simulation** prüfen, falls vorher das Sonnenmodell mit Null-Schwerkraft lief.

Das sind biegsame, längenfeste Stränge und Gelenkmechanismen. Elastisches Dehnen wie bei Gummi, Bruch, allgemeine verformbare Volumenkörper und eine automatische Umwandlung beliebiger massiver Teile sind noch nicht enthalten. Die allgemeinen Körperprofile erfassen bislang die bisherigen Körper-/Antriebswerte, nicht die Mittellinie oder flexiblen Werkstoffdaten.

1. Eine Gruppe oder Komponente auswählen.
2. In der **Newton-Toolbar** das **Drehachsen-Icon** oder **Linearachsen-Icon** anklicken. Es öffnet sich kein Dialog.
3. Im Modell zuerst den Dreh-/Startpunkt setzen. Ein zweiter Klick legt die positive Achsenrichtung fest. Die Fangfunktionen von IngeTrazo gelten dabei. Nach dem ersten Klick kann alternativ **X**, **Y** oder **Z** gedrückt werden. **Esc** bricht ohne Änderung ab.
4. In der **Newton-Sidebar** das Verhalten und den Antrieb einstellen. Änderungen gelten direkt: Zahlen mit Enter oder beim Verlassen des Feldes, Auswahllisten und Schalter sofort. Jede Änderung ist rückgängig machbar.
5. **Start** drücken. Passive Körper lassen sich mit gedrückter linker Maustaste greifen und ziehen. Das **Steuerpult** enthält benannte Antriebsregler. **Reset** kehrt zum unveränderten Originalmodell zurück.

Der Bereich **Generic** steht oben in der Sidebar. Der ausgewählte Gruppen-/Komponentenname erscheint in der Überschrift hinter **Newton properties**. Beim Start bleibt die zuvor angezeigte Konfiguration sichtbar und wird deaktiviert; die Sidebar lässt sich weiterhin durchscrollen. Start/Pause und Reset bleiben bedienbar. Ohne Auswahl bleibt die Sidebar wie bisher leer.

Winkelanschläge, Positions-/Zielwerte und die begrenzten Körper- und Umgebungswerte Reibung, Rückprall und Schwerkraft besitzen breite Schieberegler mit kompaktem Zahlenfeld. Bei einem begrenzten Positionsantrieb entspricht der Reglerbereich genau Minimum und Maximum, bei einem Geschwindigkeitsantrieb ±Maximalgeschwindigkeit. Das gilt auch für Linearachsen in Millimetern. Die Bereiche passen sich bei Änderungen der Grenzen sofort an. Genaue Eingaben bleiben möglich; Winkel über eine volle Umdrehung werden unterstützt. Ein Ziehvorgang ändert das Modell live und bleibt ein gemeinsamer Undo-Schritt. Beim Scrollen über diese Regler werden Werte nicht versehentlich geändert.

Drehachsen erscheinen als ausgerichteter Kreis mit Achsenlinie; Linearachsen als Richtungspfeil. Mit dem Auswahlwerkzeug lässt sich ein Achsensymbol anklicken, um seinen Körper auszuwählen. An der ausgewählten Achse verschiebt **Ziehen am Kreisgriff** den Ursprung; **Ziehen am quadratischen Richtungsgriff** richtet sie neu aus. Die Fangfunktionen und eine zur Ansicht parallele Arbeitsebene helfen beim Platzieren. Beim Richtungsgriff setzt X/Y/Z eine Weltachsenrichtung. **Esc** verwirft die Vorschau; Loslassen übernimmt die Änderung als einen Undo-Schritt. Die Körpergeometrie wird dabei nicht verschoben. Alternativ bleibt die Neupositionierung über das entsprechende Toolbar-Icon verfügbar. Während der Simulation und auf gesperrten Achsen-Layern ist die Bearbeitung gesperrt.

Die Achsenplatzierung verwendet dieselbe Fang- und Achsen-Inferenz wie das native Linienwerkzeug. Fangpunkte auf vorhandener Geometrie, die magnetische Ausrichtung an X/Y/Z und die Shift-Sperre bleiben verfügbar; es ist keine separate Fangberechnung nötig.

Mit dem nativen **Radiergummi (E)** lässt sich ein Achsensymbol entfernen. Körpergeometrie und Bezugskörper-Zuordnung bleiben dabei erhalten. Der Button **Achse entfernen** bleibt verfügbar. Ein auf einer Achse begonnener Radierstrich löscht ausschließlich Achsen; Undo stellt sie wieder her.

Alle Achsendarstellungen gehören zum reservierten, sprachunabhängigen Layer **`Newton_Axes`**. Die Extension verwendet einen bestehenden Layer dieses Namens oder legt ihn an, sobald Achsen vorhanden sind. Das Auge im nativen Layers-Panel blendet die Darstellungen gemeinsam aus; Geometrie und Newton bleiben aktiv. Ein gesperrter Achsen-Layer verhindert das Radieren seiner Symbole. Die Körper behalten ihre ursprünglichen Layer. Die Darstellungen bleiben gerenderte Hilfen und erzeugen keine zusätzlichen Modellflächen.

Beim ausgewählten Körper erscheinen farbige Grenzen und kurze Zahlen direkt an seiner Achse: **Grün** markiert den Bewegungsbereich, **Blau/Rot** die Anschläge und **Gelb** die aktuelle Position. Das **violette gestrichelte** Zeichen zeigt das Servo-Ziel, die gepunktete Linie die Nullstellung. Drehachsen verwenden Winkelbögen, Linearachsen eine maßstäbliche Strecke. In der Simulation folgen die Anzeigen dem Bezugskörper und den tatsächlichen Gelenkständen. Das Bedienen eines Reglers hebt die zugehörige Achse hervor. Andere Achsen bleiben dezent.

Die Achsenbeschriftung verwendet mindestens 12 pt in Fettschrift und dunkle, kontrastreiche Schilder. Min, Max und Ist werden benannt. Die Platzierung sucht freien Raum außerhalb aller projizierten Achsen und Griffe und vermeidet andere Schilder. Dünne gepunktete Hinweislinien ordnen die Schilder zu. Bei sehr dicht belegten Ansichten wird die Position mit der geringsten Überdeckung gewählt. Positions- und Bereichslinien sind 4 px stark, Anschläge und Ziele 3 px. Auch die Schilder lassen sich als Achsen auswählen oder mit dem Radiergummi entfernen.

## Kollisionen prüfen und ausschalten

Kollisionsformen sind standardmäßig ausgeblendet. **Window → Preferences → Newton → Kollisionsformen beim Start anzeigen** legt die Vorgabe für neue Fenster fest und übernimmt die Anzeige bei OK auch ins aktuelle Fenster. Die Ansicht verwendet die tatsächlichen Kollisionsformen des Newtonprozesses als farbige Umrisse mit transparenten Flächen. Der zusätzliche Befehl im Extensions-Menü schaltet die Anzeige vorübergehend um, auch ohne Auswahl und während der Simulation. Eine vorübergehende Umschaltung ändert die Startvorgabe nicht. Ältere gespeicherte Laufzeitanzeigen werden nicht als neue Startvorgabe übernommen.

Der Button **Tastenkürzel für Kollisionsanzeige…** in den Newton-Preferences öffnet IngeTrazos native Tastenkürzel-Seite direkt beim passenden Befehl. Dort lassen sich ein Kürzel vergeben und Konflikte prüfen; zunächst ist keines vorbelegt. Ausgewählte Körper werden in der Kollisionsansicht hervorgehoben. Die Anzeige verändert keine Kontakte. Im Bearbeitungsmodus wird die Form nach Geometrie- oder Parameteränderungen neu berechnet; Szene und Undo-History bleiben unverändert.

Unter **Weitere Einstellungen → Kollisionsausnahmen**: einen Körper auswählen, **Körper ausnehmen…** drücken und den zweiten Körper im Modell anklicken. Dieses Paar darf sich anschließend durchdringen. Die Liste zeigt die gespeicherten Ausnahmen; **Ausnahme entfernen** aktiviert wieder das normale Kontaktverhalten. Beide Befehle sind rückgängig machbar und werden in der `.igz` gespeichert. Direkte Bezugskörper-Verbindungen bleiben zusätzlich automatisch von gegenseitiger Kollision ausgenommen.

**`models/Kollisionen-Testmodell.igz`** zeigt drei Fälle: Ein blauer Würfel landet auf einer Platte, ein orangefarbener Würfel fällt durch seine ausgenommene Platte bis zur Unterlage. An einem Bauteil mit Öffnung zeigt die konvexe Hülle die aufgefüllte Öffnung. Öffnen: `python scripts/collision_demo.py --existing --open`.

## Gemeinsam bewegte Achsen

Unter **Weitere Einstellungen → Achskopplung → Achse folgen** kann eine Achse einem Positionsantrieb desselben Typs folgen. **Gleichläufig/Gegenläufig** bezieht sich auf die räumliche Richtung der beiden Achsen. Eine Übersetzung von 1 bedeutet gleichen Weg beziehungsweise Winkel. Standardmäßig ist jede Achse unabhängig.

Die weiteren Objekteinstellungen sind in **Achskopplung**, **Körper & Kontakt**, **Kollisionsausnahmen** und **Eigene Simulationseinstellungen** gegliedert. Jeder Abschnitt erklärt zusammengehörige Parameter in einem Kontextabsatz. Die Achskopplung erscheint nur bei einer einzelnen ausgewählten Achse; Richtung und Übersetzung erscheinen erst bei einer folgenden Achse.

**Window → Preferences → Newton** enthält vier Register: **Appearance / Darstellung**, **Simulation**, **Profiles / Profile** und **Runtime**. Dort stehen Icon-Set und Kollisionsanzeige, globale Schwerkraft/Boden/Dämpfung, Profilverwaltung sowie der Python-Pfad. Änderungen werden erst mit OK übernommen, globale Simulationswerte beim nächsten Start verwendet. Die Sidebar enthält keine globale Simulation oder Runtime-Konfiguration mehr.

Unter **Eigene Simulationseinstellungen** kann ein Körper die globale Schwerkraft durch einen eigenen Weltvektor X/Y/Z ersetzen, lineare und rotatorische Dämpfung festlegen und den automatischen Boden bei Z = 0 unabhängig ein-/ausschalten. Modellierte Unterlagen behalten ihre normalen Kontakte. Ausschalten des Hauptschalters stellt die Vererbung wieder her. Die Overrides werden mit dem Modell und in eigenen Profilen gespeichert.

**Anziehung** erzeugt ein zum Körperschwerpunkt gerichtetes Newtonsches Kraftfeld mit der Stärke μ = G × Masse (m³/s²). Null erzeugt kein Feld. Verwenden alle Körper dasselbe G, wirken die Kräfte gegenseitig und erhalten den Gesamtimpuls. Ein Glättungsradius entschärft die Singularität im Zentrum. **Startgeschwindigkeit X/Y/Z** gilt für frei bewegliche Körper in Weltkoordinaten und wird bei jedem Simulationsstart wiederhergestellt. Die Werte sind unabhängig von Gelenkantrieben.

Das Testmodell [Sonne und Planet](models/Sonne-und-Planet.igz) enthält zwei frei bewegliche Kugeln mit Massen 100 und 5 kg, Abstand 4 m und einem absichtlich vergrößerten G = 0,16 m³/(kg·s²). Die Umlaufzeit beträgt etwa 12,26 s. Beide kreisen um ihren gemeinsamen Schwerpunkt; die Sonne ist nicht festgehalten. Schwerkraftvektor, Boden und Dämpfung sind ausgeschaltet. `scripts/solar_system.py --existing --open` öffnet das Modell mit diesen globalen Vorgaben in einem eigenen Testfenster. Beide Körper speichern zusätzlich Null-Schwerkraft und ausgeschalteten Boden als Overrides, sodass das Modell auch mit anderen globalen Vorgaben funktioniert.

Die Kopplung wird im MuJoCo-Solver erzwungen. Im Steuerpult erscheint nur der führende Regler; die folgende Achse lässt sich nicht ziehen. Die zulässigen Wege, Geschwindigkeiten und Beschleunigungen werden auf den gemeinsamen Bereich begrenzt. Der führende Antrieb liefert die gemeinsame Kraft beziehungsweise das gemeinsame Drehmoment; das Kraftlimit der folgenden Achse wird nicht als zweiter Antrieb verwendet. Ein führender Antrieb kann mehrere direkte Folgeachsen besitzen. Kopplungsketten, Kreise und gemischte Dreh-/Linear-Kopplungen sind noch nicht enthalten.

Beim Entfernen einer führenden Achse oder beim Festsetzen ihres Körpers werden ihre Folgeachsen wieder unabhängig. Dieser Vorgang ist gemeinsam rückgängig machbar. Kopplungen werden im Modell gespeichert; eigene Profile kopieren keine Verweise auf andere Modellkörper.

Das Modell **`models/Industrieroboter-mit-Synchrongreifer.igz`** besitzt vier Drehservos und einen gemeinsamen Regler **Greifer Öffnung**. Er zeigt den Abstand der Backen in Millimetern: 105 mm offen bis 5 mm geschlossen. Beide Backen bewegen sich symmetrisch. Erzeugen und separat öffnen: `python scripts/robot_arm.py --gripper --open`.

## Bezugskörper

Der professionelle Begriff für die Zuordnung zu einem übergeordneten Element ist **Bezugskörper**.

- Kind auswählen → **Kettensymbol „Bezugskörper zuweisen“** → Bezugskörper im Modell anklicken. Alternativ stehen die Befehle im Kontextmenü und in der Sidebar bereit.
- Beim normalen Verschieben des Bezugskörpers folgen seine abhängigen Teile, einschließlich weiterer Unterstufen. Sie sind auch in der Bewegungsvorschau enthalten. Die Änderung bleibt **ein gemeinsamer Undo-Schritt**.
- Wird nur das Kind verschoben, bleibt der Bezugskörper stehen. Die Zuordnung bleibt erhalten; Unterstufen des Kindes folgen dem Kind.
- Rotation und Skalierung über die nativen Gruppentransformationen werden ebenfalls weitergegeben; Achsenposition und Richtung werden mitgeführt.
- **Bezugskörper-Zuordnung lösen** trennt die Abhängigkeit, ohne Teile zu verschieben. Eine vorhandene Achse bleibt erhalten und bezieht sich danach auf die Welt.
- Ein beweglicher Körper mit Bezugskörper, aber ohne eigene Achse, ist in der Simulation starr mit seinem Bezugskörper verbunden. Eine platzierte Achse gibt die entsprechende relative Bewegung frei.
- **Fest** bedeutet mit Bezugskörper: fest an diesem verschraubt. Der Körper folgt dessen Bewegung, lässt sich aber nicht selbst ziehen. Ohne Bezugskörper bedeutet fest: an der Welt fixiert.
- Ohne Bezugskörper ist eine platzierte Achse an der Welt befestigt. Ein beweglicher Körper ohne Achse und ohne Bezugskörper ist frei beweglich.

Direkt verbundene Körper kollidieren nicht miteinander, damit sich Lager nicht selbst blockieren. Andere Körperpaare kollidieren weiterhin. Geschlossene Bezugskörper-/Gelenkkreise werden mit einer Meldung abgewiesen.

## Sidebar statt Einrichtungsdialog

Alle Parameter stehen bei der gewählten Gruppe in der Sidebar:

| Einstellung | Bedeutung |
|---|---|
| Lose / beweglich, fest, ohne Newton | Teilnahme und Beweglichkeit des Körpers |
| Bezugskörper | Übergeordnetes Element; Zuordnung oder Trennung |
| Reglername | Beispielsweise „Greifer schließen“, „Tür links“, „Vorschub“ |
| Frei / passiv | Keine Regelung; durch Gravitation, Kontakte oder Ziehen bewegen |
| Servo / Zielwinkel | Zielwinkel in Grad anfahren und halten |
| Position / Zielweg | Lineares Ziel in Millimetern anfahren und halten |
| Motor / Geschwindigkeit | Drehgeschwindigkeit in °/s oder Vorschub in mm/s |
| Minimum / Maximum | Optionale Winkel- oder Weganschläge |
| Startziel | Gespeicherter Reglerwert beim Start der Simulation |
| Geschwindigkeit | Maximale Geschwindigkeit des Antriebs-Sollverlaufs |
| Beschleunigung | Beschleunigungsgrenze des Antriebs-Sollverlaufs |
| Bremsverzögerung | Eigene Grenze für Abbremsen und Richtungswechsel; der Kettenschalter synchronisiert sie mit der Beschleunigung |
| Maximale Kraft | Begrenzung in Nm beziehungsweise N |

Die Modelllage beim Einrichten entspricht 0° beziehungsweise 0 mm. Ein verwendeter Grenzbereich muss diese Anfangslage enthalten. Körperwerte und lokale Overrides stehen unter **Weitere Körper- und Umgebungseinstellungen**; globale Simulation und Runtime-Auswahl stehen in den Extension-Preferences.

Beschleunigung und Bremsverzögerung sind zunächst gekoppelt. Mit aktiviertem Kettenschalter folgt die Bremsverzögerung jeder Änderung der Beschleunigung. Nach dem Lösen lässt sie sich getrennt einstellen; erneutes Koppeln übernimmt sofort den Beschleunigungswert. Die Grenzen gelten in °/s² beziehungsweise mm/s² für den Sollverlauf. Beim Richtungswechsel bremst der Antrieb zuerst auf null und beschleunigt anschließend in die andere Richtung. Beide Werte und die Kopplung werden mit Profilen und Modellen gespeichert; ältere Einstellungen übernehmen automatisch die bisherige symmetrische Beschleunigung.

Bei Mehrfachauswahl lassen sich Körperwerte und lose/fest gemeinsam ändern. Achsen und Bezugskörper werden für eine einzelne gewählte Gruppe eingerichtet. Ohne ausgewählten Körper bleibt die Newton-Sidebar leer. Die Übersicht befindet sich im vorhandenen **Browser**: Die Typ-Spalte zeigt Newton, Achsenart und Reglername. Die bestehenden Körpernamen bleiben erhalten; es entstehen keine zusätzlichen Geometrieobjekte für Regler.

## Simulation und Steuerpult

- **Start / Pause / Fortsetzen / Reset** sind in Toolbar, Sidebar und Steuerpult verfügbar. Start und Pause teilen sich einen zustandsabhängigen Button. Das Steuerpult funktioniert auch ohne Objektauswahl.
- In der Simulation greift die linke Maustaste passive, nicht feste Körper. Die Bewegung erfolgt als gedämpfte Zugkraft an der Greifstelle, ohne Teleportieren; Gelenke und Kontakte wirken weiter. Loslassen beendet die Zugkraft.
- Die Maus bewegt das Zugziel in der zum Bildschirm parallelen Ebene durch den Greifpunkt. Kamera-Navigation über die mittlere Maustaste bleibt verfügbar.
- **Servo- und Motorkörper mit Regler können nicht manuell gezogen werden**, auch dann nicht, wenn das Kraftlimit klein ist. Sie werden ausschließlich über das Steuerpult gesteuert. Diese Regel wird sowohl in der Oberfläche als auch im Newtonprozess geprüft.
- Beim Start angetriebener Modelle öffnet sich das separate **Steuerpult** automatisch. Jede Aktorkarte trägt den Titel **Gruppen-/Komponentenname Aktorname**. Der Istwert steht ganz links, der breite Schieberegler mittig und das kleine Sollwert-Eingabefeld rechts. Reglerstil, Höhe, Abstand und 104-Pixel-Eingabefeld entsprechen den Min-/Max-Reglern der Sidebar. Eine gemeinsame Istwertspaltenbreite hält alle Regler bündig, auch bei unterschiedlichen Einheiten oder langen Zahlen. Der Toolbar-Befehl öffnet das Steuerpult jederzeit erneut.
- Bei Pause wird ein neues Reglerziel erst beim Fortsetzen angefahren. Reset verwirft die Laufzeitziele. Dauerhafte Startwerte werden in der Sidebar eingestellt.
- Geschwindigkeit und Beschleunigung begrenzen den Sollverlauf; der tatsächliche Körper folgt ihm entsprechend Kraftlimit, Lasten und Kontakten. Die Simulation bleibt physikalisch, daher ist dies keine Zusicherung einer exakt begrenzten realen Beschleunigung.
- Speichern im Simulations-Workspace weist auf Reset und anschließendes Speichern des Originals hin. Eine Übernahme der simulierten Endlage ist noch nicht enthalten.

## Profile

Die einfügbaren Beispielmodelle wurden aus der Oberfläche entfernt. Stattdessen gibt es acht vorgefertigte Profile: freie Drehachse, Drehmotor, Drehservo, freie Linearachse, Linearmotor, lineare Positionierung sowie freier und fester Körper.

Ein Profil überschreibt Masse, Reibung, Rückprall, Kollisionsform und Beweglichkeit sowie Antrieb, Grenzwerte, Startziel, Geschwindigkeit, Beschleunigung und Kraftlimit. Bei vorhandener Achse bleiben Platzierung, Reglername und Bezugskörper erhalten. Fehlt eine benötigte Achse, beginnt die Platzierung im Modell; Esc bricht ohne Datenänderung ab. Ein Körperprofil ohne Achse entfernt eine vorhandene Achse, erhält aber den Bezugskörper.

**Window → Preferences → Newton → Profile** zeigt die Werte jedes Profils nach Körper/Kontakt, Bewegung und Simulation Overrides. Eigene Profile sind direkt editierbar, Built-ins schreibgeschützt und duplizierbar. **Speichern unter…** übernimmt die aktuellen Objekteinstellungen. Änderungen in den Preferences werden mit **OK** gespeichert; **Abbrechen** verwirft sie.

Beim Anwenden merkt sich der Körper die Profil-ID und den übernommenen Parameterstand. Die Sidebar zeigt **Synchron**, **Lokal geändert**, **Profil geändert** oder **Profil fehlt**. **Sync** übernimmt die aktuellen Profilparameter und überschreibt lokale Abweichungen; Achslage, Namen, Geometrie und Bezugskörper bleiben erhalten. **Zuordnung lösen** erhält die Objektwerte. Die Zuordnung wird in der `.igz` gespeichert; eigene Profile liegen in den lokalen IngeTrazo-Benutzereinstellungen.

Unter **Preferences → Newton → Profile → Zugeordnete Körper synchronisieren (N)** lässt sich der gemeinsame Sync im aktuellen Modell für **OK** vormerken; erneutes Anklicken nimmt ihn zurück. Auch nach dem Vormerken bearbeitete Profilwerte werden verwendet. Der Vorgang wird vollständig geprüft und lässt sich mit einem Undo rückgängig machen. Bereits existierende Körper ohne Zuordnung kannst du mit **Auswahl zuordnen, Werte behalten** verbinden, ohne ihre Parameter sofort zu ändern. Neue Achsen benötigen weiterhin eine Platzierung in der Sidebar.

## Toolbar, Darstellung und Sprache

Vier native Trenner gliedern die zwölf Toolbar-Aktionen in Achsen/Verbindungen, Körper, Bezugskörper, Simulation und Sidebar. Profilverwaltung und Einstellungen sind aus der Toolbar entfernt. Standardmäßig verwendet sie IngeTrazos native Icon-Funktion und Toolbar-Größe. Unter **Window → Preferences → Newton** stehen zusätzlich die Icon-Sets **Kontur** und **Akzent** zur Wahl. Die Wahl wird mit **OK** gespeichert. Alle Sets reagieren auf die helle und dunkle Palette.

Die Extension ergänzt den nativen Preferences-Dialog über einen lokalen Adapter: Die Extension-API 2 besitzt dafür keinen offiziellen Registrierungspunkt. IngeTrazo-Dateien bleiben unverändert; bestehende Seiten und ihre Navigation bleiben erhalten. Dieser Adapter ist gegen den unten genannten Hoststand geprüft.

Die Oberfläche folgt IngeTrazos Spracheinstellung. Englisch und Deutsch sind enthalten. **`newton/i18n/en.json`** ist die englische Masterdatei; eine fehlende Sprache oder Übersetzung fällt auf Englisch zurück. Selbst vergebene Objekt-, Regler- und Profilnamen werden nicht übersetzt. Nach einer Änderung der Hostsprache gilt deren üblicher Neustartablauf.

## Lokal installieren oder aktualisieren

Voraussetzung: ein normaler **Python-3.12-Interpreter (64 Bit)** mit MuJoCo. Die IngeTrazo-EXE selbst ist kein Python-Interpreter.

```powershell
.\scripts\setup-runtime.ps1 -Python 'C:\Pfad\zu\Python312\python.exe'
.\scripts\install-local.ps1
```

Eine bereits vorhandene Installation mit Sicherung aktualisieren:

```powershell
.\scripts\install-local.ps1 -Update
```

Alternativ kann mit `-Python 'C:\Pfad\zur\Umgebung\Scripts\python.exe'` eine vorhandene Umgebung mit `mujoco==3.3.7` angegeben werden.

Der Installer kopiert den Extension-Code nach `%APPDATA%\ingetrazo\plugins\newton` und speichert den Python-Pfad in `runtime.json`. Bei einem Update wird die bekannte vorherige Installation unter `.backups` im Projekt gesichert. Andere Extensions werden nicht verändert.

**IngeTrazo vollständig neu starten**, danach **Extensions → Newton…** öffnen. Die Newton-Toolbar lässt sich über die normale Toolbar-Verwaltung einblenden. Der Projektordner mit `.venv` muss erhalten bleiben, solange diese Laufzeit benutzt wird. Nach einem Umzug lässt sich der Python-Pfad unter **Preferences → Newton → Runtime** neu wählen.

Manuell: den gesamten Ordner `newton` einschließlich `__init__.py` und `i18n` direkt in den persönlichen Pluginordner kopieren und in der Sidebar bei ausgewähltem Körper den Interpreter wählen. Alte Daten-Namensräume und alte Plugin-Imports werden nicht unterstützt; Modelle müssen ausdrücklich auf das Newton-Schema umgestellt werden. Name, Achse, Parameter und Bezugskörper reisen im `.igz` mit.

## Grenzen

- Ein Körper hat höchstens eine eingehende Bezugskörper-/Gelenkverbindung. Verzweigte Ketten funktionieren; geschlossene Bezugskörperketten und mehrere Gelenke am selben Körper noch nicht. Achskopplungen verbinden die Bewegungskoordinaten bereits vorhandener Gelenke.
- Newtonkörper sind aktuell Gruppen/Komponenten auf oberster Modellebene. Verschachtelte Geometrie innerhalb eines solchen Körpers bildet einen gemeinsamen Collider.
- Native Gruppentransformationen und ihre Undo-/Redo-Schritte werden durch lokale Extension-Adapter ergänzt. Direkte Geometrieänderungen durch andere Extensions ohne diese Commands können die Bezugskörper-Nachführung umgehen. Geometrie innerhalb eines Körpers zu verformen ist kein Verschieben des Körpers.
- Unkonfigurierte normale Gruppen sind statisch. Unkonfigurierte Face-me-Maßstabsfiguren sind nur visuell. Verborgene Top-Level-Gruppen werden ausgelassen; lose Geometrie wird angezeigt, kollidiert aber nicht.
- Box und Kugel sind vereinfachte umschließende Collider. Konvexe Hüllen schließen konkave Löcher. Keine automatische konkave Zerlegung; degenerierte Hüllen können abgewiesen werden.
- Rückprall ist eine Näherung über MuJoCos Kontakt-Dämpfung. Der optionale Boden ist eine unendliche Ebene bei Z=0.
- Noch keine Kugel-/Universalgelenke, Replay, Magnetismus, Auftrieb oder SketchyPhysics-Skriptkompatibilität.
- Pro Fenster eine Simulation; der Workspace sperrt Projektwechsel. Keine garantierte Bildrate für große Modelle.
- IngeTrazos 0.x-API ist veränderlich. Geprüft wurde v0.6.0, Commit `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`.

## Entwicklung und Prüfung

Für Entwicklung und Tests wird der IngeTrazo-Quellstand v0.6.0 als `ingetrazo-source` neben der Extension benötigt. Diese externe Referenzkopie sowie die lokale Python-Umgebung, Laufzeitkonfiguration, Logs und erzeugten Pakete werden nicht im Newton-Repository versioniert.

```powershell
git clone https://github.com/ingelibre/ingetrazo.git ingetrazo-source
git -C ingetrazo-source checkout e61132a7f8a098ca77fb6b0e7cac488c1bd410cb
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp=.test-state/pytest
.\.venv\Scripts\python.exe scripts\preview.py Pendel --edit
.\.venv\Scripts\python.exe scripts\package.py
```

Die automatisierten Tests prüfen Starrkörperdynamik, Gelenke, Servo-/Linearregelung, Bezugskörper-Nachführung mit nativen Commands und Undo/Redo, Live-Vorschau, Speichern/Laden, physikalisches Ziehen und dessen Antriebssperre, Geschwindigkeits-/Beschleunigungsprofile, Toolbar-Platzierung ohne Dialog, direkte Sidebar-Änderungen, Radiergummi, Profilverwaltung, Browser, Steuerpult, Icons und Sprach-Fallback. Hinzu kommen Solver-Kopplungen einschließlich Kontakt und negativer Übersetzung, Öffnungsregler, Layer-Sichtbarkeit und laufende Achsenanzeigen. Die Kontaktprüfung enthält rotierte Quader, die Abgrenzung zu anderen Hüllen und das Beruhigen aller 30 Dominosteine. Die Preferences-Integration prüft OK/Abbrechen und bestehende Seitennavigation. Hosttests verwenden IngeTrazos echten Loader und MainWindow. Beispielmodelle stehen ausschließlich als Entwicklungswerkzeug über `scripts/preview.py` bereit.

Module: `model.py` (Geometrie/Daten), `worker.py` (Newtonprozess), `session.py` (Prozess/Workspace), `panel.py` (Sidebar/Browser), `toolbar.py` (Icons/Aktionen), `joints.py` (Achsenplatzierung), `eraser.py` (Radiergummi), `references.py` (Bezugskörper/Undo), `interaction.py` (Zuweisen/Ziehen), `controls.py` (Steuerpult), `profiles.py`/`profile_ui.py` (Profile), `preferences.py` (Darstellung), `i18n.py` (Sprache). `scripts/update-translations.py` aktualisiert die Sprachkataloge.

## Lizenz

GPL-3.0-or-later; siehe LICENSE. MuJoCo und weitere Abhängigkeiten werden separat installiert und behalten ihre jeweiligen Lizenzen. Das ZIP enthält keine Python- oder MuJoCo-Binärdateien.
