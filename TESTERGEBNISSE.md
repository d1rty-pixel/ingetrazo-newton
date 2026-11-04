# Prüfung von Newton 0.14.0

Geprüft am 4. November 2026 unter Windows x64 mit Python 3.12.14, PySide6 6.11.3 und MuJoCo 3.3.7. Host-Referenz: IngeTrazo v0.6.0, Commit `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`.

## Automatische Prüfung

Version 0.14.0 benennt die Extension in Newton um: Paket, Klassen, öffentliche Modulimporte, Settings-Schlüssel, Modellschlüssel, Overlay-Layer, Qt-Objektnamen, Preferences-Adapter, Toolbar, Kontextmenüs, Dialoge und Sprachdateien verwenden den neuen Namen. Die mitgelieferten `.igz`-Modelle sind direkt umgestellt. Alte Namensräume werden weder gelesen noch migriert. Die sichtbaren deutschen Toolbar-, Sidebar- und Preferences-Titel wurden zusätzlich über den echten Hostdialog offscreen gerendert und geprüft. Fremdprodukte und deren Quellen behalten ihre tatsächlichen Namen.

Version 0.13.0 ergänzt einen kategorisierten Werteeditor für Profile: Built-ins sind lesbar und schreibgeschützt, eigene Profile editierbar, Built-ins duplizierbar. Zusammenhängende englische Mastertexte und deutsche Übersetzungen erklären Zusammenhänge und Nebenwirkungen in Darstellung, Simulation, Runtime sowie den erweiterten Körpereinstellungen. Runtime bleibt auch in der deutschen Oberfläche Runtime. Die Preferences wurden mit Hostdialog und Segoe UI gerendert und visuell geprüft.

Profilzuordnungen speichern ID und Parametersignatur am Körper und überstehen natives `.igz`-Speichern/Laden. Prüfungen unterscheiden lokale Abweichungen, Profiländerungen und gelöschte Profile. Einzel-Sync erhält Geometrie, Transformation und Achslage. Sammel-Sync verwendet zuletzt bearbeitete Profilwerte, bleibt bis OK vorgemerkt und bildet einen Undo-Schritt; Abbrechen verändert weder Profile noch Körper. Vorabprüfung aller betroffenen Körper verhindert Teiländerungen bei fehlenden Achsen. Explizite Zuordnung alter Körper erhält deren bisher implizite statische Beweglichkeit. Ein fehlendes optionales Control-Display wird beim Profilanwenden als Standarddarstellung behandelt.

Version 0.12.1 ordnet die Steuerpultzeile als Istwert links, Regler mittig und Sollwerteingabe rechts. Sie verwendet dieselbe RangeControl-Komponente wie die Sidebar, einschließlich Reglerstil, Höhe, kompaktem 104-Pixel-Feld und Schutz gegen versehentliche Scrollradänderungen. Vier bestehende Prüfungen zu echten Antriebsreglern, gekoppelter Greiferöffnung und Palette bestehen in 8,66 Sekunden. Die Darstellung wurde zusätzlich mit fünf Aktorkarten und unterschiedlich langen Istwerten gerendert und visuell geprüft; sämtliche Regler und rechten Eingabefelder sind bündig.

Letzter vollständiger Lauf (Newton 0.14.0):

```text
.venv\Scripts\python.exe -m pytest tests -q --basetemp=.test-state/newton-rename
141 passed in 64.99s (0:01:04)
```

Die vollständige Suite enthält die Kopplung mit negativer Übersetzung sowie die neuen Kontakt- und Domino-Regressionen.

Version 0.12.0 prüft zusammengesetzte Kollisionskörper mit einem tatsächlich durchfallenden Prüfkörper: Eine gemeinsame konvexe Hülle hält ihn über der Öffnung an, vier Teilkörper lassen ihn durch die Öffnung bis zum Boden fallen. Die Kollisionsanzeige enthält alle vier Geometrien; die Gesamtmasse bleibt erhalten. Die neue Energiekette hat 22 starre Rahmen mit je vier Teilkörpern und keine pauschalen Selbstkontakt-Ausnahmen für nicht benachbarte Glieder. Die räumliche Trennung von Radkörper und Pleuel wird mit mindestens 39,9 mm geometrischem Abstand geprüft; ein Newtonlauf bestätigt den weiter arbeitenden Kurbeltrieb. Die Sidebar verwirft eine Teilkomponenten-Kollisionsform auf einem einfachen Körper ohne Untergruppen.

Vier Simulationssekunden Kontakt-Audit: vorher 156 Körper, 156 Geometrien, durchschnittlich 78 Kontakte, 7,818 s Laufzeit; nachher 90 Körper, 156 Geometrien, durchschnittlich 47,63 Kontakte, 5,720 s Laufzeit. Freiheitsgrade bleiben 201. Die Kategorie Kette/Kette entfällt im geprüften Lauf; verbleibende Kontakte sind Kabel/Bett, Kabel/Kette und Kette/Bett. Das sind einzelne Vergleichsläufe, keine allgemeine Geschwindigkeitsgarantie. `scripts/audit_contacts.py` dokumentiert die aktiven Kontaktpaare und Kategorien.

Das überarbeitete Modell besteht die 24-Sekunden-Prüfung: Motorwinkel 15,02 rad, Hub −136,7 bis +163,4 mm, Kurbelabweichung unter 0,14 mm und maximaler gemessener Kabelabstand etwa 50,5 mm einschließlich der offenen Kettenenden. Die starre erste Rahmenbefestigung besitzt eine sichtbare Konsole; die zusätzlichen Konsolendetails sind wie die Bettschrauben reine Darstellung, die Befestigung wird durch den festgehaltenen ersten Körper berechnet.

Version 0.11.0 ergänzt elf Prüfungen zu Motorregelung, Anti-Windup, Echtzeitmessung, Qualität und mechanischen Verbindungen sowie drei native UI-Prüfungen. Ein Motor hält unter einer zusätzlichen Last seine Geschwindigkeit mit weniger als 1 % Abweichung; ein zu schwacher Motor respektiert sein Kraftlimit und schwingt nach Entlastung nicht durch einen aufgeladenen Integrator über. Die Telemetrie wird ausdrücklich durch JSON serialisiert, wie im echten Worker-Protokoll. Natives Rotieren führt Punkt und Bolzenachse mit; Undo stellt beide wieder her.

Kugel-, Bolzen- und starre Verbindungen werden im Solver auf ihre tatsächlich erlaubten Bewegungen geprüft. Die native Bedienprüfung verbindet zwei Körper mit einem Bolzen durch Gegenkörperwahl, Punktplatzierung und Y-Achsenwahl, bearbeitet anschließend den Punkt direkt in der Sidebar und prüft Undo. Ein echter Qt-Mausdruck aktiviert das Ziehen der Markierung; Loslassen ist ein Undo-Schritt. Der Radiergummi entfernt nur die Verbindung und erhält die Geometrie. Die Echtzeitanzeige und der Pause-Zustand werden mit einem echten externen Worker geprüft.

Im regulär installierten IngeTrazo wurde die laufende neue Fassung visuell bestätigt: Das Steuerpult zeigte etwa 0,49× Echtzeit bei 37,2°/s Sollwert und 37,3°/s Istwert. Die Sidebar blieb währenddessen sichtbar und deaktiviert. Die bestehenden Anwenderfenster wurden nicht geschlossen oder verändert.

Der wiederholbare zweisekündige Worker-Benchmark des gespeicherten Kurbeltriebs benötigt vorher 7,265 s (0,275×), mit Ausgewogen 3,685 s (0,543×) und mit Schnell 2,198 s (0,910×). Newtonalische Geometrie und die zwei internen Kabelschritte sind gleich geblieben. Es handelt sich um einzelne Messungen auf diesem Rechner, ohne GUI-Zeichenzeit; sie sind keine allgemeine Geschwindigkeitsgarantie. Das Profil vor der Änderung zeigte 6,712 von 7,262 s in `mj_step`, weitere 0,424 s im zur Ausgabe zusätzlich aufgerufenen `mj_forward`. Ein nativer Timer-Lauf lokalisierte den Großteil der Rechenzeit im Constraint-Solver.

Der vollständige 24-Sekunden-Lauf mit Ausgewogen und neuer Motorregelung erreicht 15,02 rad Motorwinkel statt 10,95 rad im alten Lauf. Der Hub bleibt −0,1366 bis +0,1634 m; die maximale geometrische Kurbelabweichung liegt unter 0,08 mm. Die Endverbindungen bleiben bei etwa 0,5 mm Fehler, der maximale gemessene Kanalabstand sinkt auf etwa 6,30 cm einschließlich des offenen Ausgangs. Ein instabiler Versuch mit CG und pyramidalem Reibungskegel wurde verworfen; die veröffentlichten Stufen verwenden weiterhin elliptische Reibung.

Das Modell **Kurbeltrieb-mit-Schleppkette.igz** wurde über 24 Simulationssekunden geprüft: Motorwinkel 10,95 rad, Hub −0,1366 bis +0,1634 m, maximale Abweichung zur geometrischen Kurbelgleichung unter 0,00008 m. Die Endverbindungen zeigen etwa 0,4 mm Fehler. Die 156 Körper umfassen den durchgängigen Kraftfluss Motorwelle → Rad → Pleuel → passiver Kolben → Schleppkette. Das Kabel ist nur an Steckdose und Motor befestigt und hat eine freie Reserveschleife hinter dem beweglichen Kettenausgang. Die größten Abstände der ausgewerteten Kabelabschnitte zur bewegten Kanal-Mittellinie liegen unter 6,5 cm, einschließlich des offenen Kettenausgangs. Es gab keinen automatischen Simulationsreset.

Die zusätzliche Regression von Version 0.10.1 prüft Kollisionsausnahmen für ein ganzes flexibles Objekt: Ohne Ausnahme berühren sich die Abschnitte und das Gehäuse, mit Ausnahme bleiben sämtliche Abschnitte kontaktfrei und ruhig. Die Kontaktflächen der eigentlichen Schleppkette sind davon nicht ausgenommen.

Der Kurbeltrieb wurde abschließend mit `C:\Program Files\IngeTrazo\ingetrazo.exe --new-window` im regulären IngeTrazo geöffnet und visuell geprüft. Das bestehende Fenster mit dem ungespeicherten Anwenderprojekt blieb geöffnet.

Version 0.10.0 ergänzt MuJoCos natives Kabel-Elastizitätsplugin mit getrennten Biege-/Torsionsmoduli, Radius, Dämpfung, Anfangsbefestigung und optionaler Endbefestigung. Geprüft werden segmentierte Darstellung im temporären Modell, unveränderte Quelldaten, Speichern/Laden, echte externe QProcess-Simulation, Reset, Sidebar-Undo, Konvertierung einer gruppierten Linie, das Einlesen bearbeiteter Linienendpunkte sowie natives Verschieben mit Undo. Alle drei Anfangsarten (eingespannt, gelenkig und frei) werden im echten Newtonmodell geprüft.

Das Seil-/Kabelmodell läuft fünf Sekunden mit Endgewichten und Unterlagenkontakt: Das steifere Kabel hängt höher, die Endverbindungen weichen weniger als 1 cm ab, und die gemeldete Zeit bleibt trotz interner Unterteilung korrekt. Die Längen der Seilabschnitte bleiben konstant, der eingespannte Anfang fest. Die Gelenkkette schwingt vier Sekunden, ohne dass sich die Gelenkabstände ändern.

Die Schleppkette wird zwölf Sekunden lang auf +180, −100 und +200 mm verfahren. Geprüft werden weniger als 4 cm Abweichung zum Schlittenziel unter Last, weniger als 5 mm Fehler der Endverbindungen und Kabelabschnitte innerhalb von 6 cm zur tatsächlichen bewegten Kanal-Mittellinie. Der Kanal besteht aus getrennten Kontaktflächen mit überlappenden Übergängen; das Kabel ist nur an den Enden befestigt. Es besitzt eigene Kugelgelenke und native Biege-/Torsionskräfte. Zu steife Konfigurationen werden vor dem Start mit einem verständlichen Fehler zurückgewiesen.

Die drei Modelle **Seil-und-Kabel.igz**, **Gelenkkette.igz** und **Schleppkette-mit-Kabel.igz** wurden nativ gespeichert und wieder geladen. Das Schleppketten-Testfenster samt Werkstoffeditor und Verfahrweg-Steuerpult wurde geöffnet und visuell geprüft. Die gespeicherte Endfassung hat transparente Kanalwände und ausgeblendete Achsen.

Version 0.9.0 prüft vier geordnete Preferences-Register und die Übernahme globaler Simulationseinstellungen erst bei OK. Globale Simulation und Laufzeit sind aus der Sidebar entfernt. Die Objektoverrides sind direkt editierbar, rückgängig machbar und überstehen Profile und natives Speichern/Laden. Newtontests prüfen Schwerelosigkeit, seitliche Gravitation, getrennte Bodenfreigabe bei global ein- und ausgeschaltetem Boden und erhaltene Körperkontakte. Lineare und rotatorische Dämpfung werden global und lokal geprüft.

Das neue Sonnen-/Planetenmodell wird über drei Umläufe geprüft: Abstand 4 m mit weniger als 2,5 cm Abweichung, stabiler gemeinsamer Schwerpunkt und nachweisbare Bewegung der Sonne. Null-Schwerkraft und fehlende Dämpfung ermöglichen einen freien Umlauf ohne Gelenk oder vorgegebene Bahn. Anziehung bleibt auch bei überlappenden Zentren endlich; Startgeschwindigkeiten werden beim erneuten Laden wiederhergestellt. Das Modell wurde im eigenen nativen IngeTrazo-Fenster geöffnet; die neuen Objekteinstellungen und der Start im externen Newtonprozess wurden kontrolliert.

Version 0.8.0 prüft zusätzlich die sichtbare, deaktivierte Konfiguration während der Simulation, Generic an erster Stelle und den Objektnamen in der Überschrift. Bremsverzögerung mit Synchronisierung, getrennte Werte, Undo und natives Speichern/Laden werden geprüft. Ein externer Newtonlauf bestätigt unterschiedliche Beschleunigungs- und Bremsraten einschließlich des Abbremsens vor einer Richtungsumkehr. Die Kollisionsanzeige startet standardmäßig aus, liegt in den Preferences und öffnet die native Tastenkürzel-Verwaltung; Konfliktverwaltung und Speichern übernimmt der Host. Das vorübergehende Umschalten ändert keine Startvorgabe. Der Beschriftungstest prüft zusätzlich freien Abstand zu den projizierten Achsenbereichen.

Im neu geöffneten nativen Roboterfenster wurden der Generic-Bereich, die Überschrift, der Kettenschalter für die Bremsverzögerung und die ausgelagerten Schilder kontrolliert. Nach Start blieb die gesamte Konfiguration sichtbar und grau hinterlegt; die Simulationssteuerung blieb verfügbar.

Version 0.7.0 ergänzt folgende Prüfungen:

- Kollisionsformen werden im Bearbeitungsmodus durch den externen Newtonprozess ermittelt, nach Parameteränderungen aktualisiert und als Umrisse mit transparenten Flächen gezeichnet. Derselbe Geometriedatensatz steht während der Simulation zur Verfügung. Auch rein statische Dokumente lassen sich prüfen.
- Die Kollisionsdemo landet mit aktiviertem Kontakt auf der Platte; ein ausgeschlossenes Paar durchdringt sich. Entfernen der Ausnahme stellt den tatsächlichen Kontakt wieder her. Paarzuordnungen überstehen Speichern/Laden und Undo. Bisher unkonfigurierte statische Körper werden dabei nicht versehentlich beweglich.
- Echte native Mausereignisse aktivieren den Achsengriff bereits beim Drücken. Ziehen verschiebt den Ursprung mit Vorschau, Loslassen übernimmt und Undo stellt die ursprünglichen Daten wieder her. Die Körpergeometrie bleibt unverändert. Abbrechen eines Richtungsgriffs verwirft die Vorschau; seine Arbeitsebene liegt am ursprünglichen Griffpunkt.
- Größere Achsenschilder werden ohne Überlappung angeordnet und bleiben über ihre sichtbaren Rechtecke auswählbar. Der Test zeichnet mit einem echten QPainter in ein Bild.
- Die neue Achsenplatzierung wurde unmittelbar mit IngeTrazos nativem Linienwerkzeug verglichen: Fangpunkte auf vorhandener Geometrie und magnetische X-/Y-/Z-Ausrichtung liefern dieselben Punkte und Inferenzarten.

Version 0.7.1 ergänzt breite Sidebar-Schieberegler mit kompakten Zahlenfeldern. Geprüft werden die genaue Übernahme linearer Min-/Max-Werte, die laufende Anpassung der Positionsgrenzen, die sofortige Modelldatenänderung sowie ein gemeinsamer Undo-/Redo-Schritt für einen vollständigen Ziehvorgang. Präzise Winkeleingaben über 180° und passive/deaktivierte Bedienelemente bleiben korrekt. Die Darstellung wurde zusätzlich im nativen Roboterfenster an einer Linearachse mit 0–50 mm kontrolliert.

Die ursprüngliche Domino-Szene zeigte zwischen 10 und 15 Simulationssekunden Positionsschwankungen bis 69,93 mm und deutliches anhaltendes Kippen. Nach der Kontaktkorrektur fallen weiterhin alle 30 Steine (der letzte nach 3,3 s); die maximale Positionsspanne im selben Ruhefenster beträgt 0,56 mm. Auch die Änderung der Orientierungen wird begrenzt geprüft. Die Szene wird nicht künstlich eingefroren. Ein separater Test bestätigt die exakte Geometrie rotierter Quader; ein verformtes Acht-Ecken-Polyeder wird weiterhin als Hülle behandelt.

Nach der Sidebar-Gliederung (0.6.1) wurde die betroffene Host-/UI-Suite erneut geprüft: `32 passed in 24.96s`. Die Newtonberechnung wurde dafür nicht verändert. Im nativen Testfenster wurden die vier Abschnitte mit zusammenhängenden Kontexttexten auf Lesbarkeit und Abstände geprüft. Bei unabhängigen Achsen sind Richtung und Übersetzung ausgeblendet; führende und folgende Achsen besitzen passende Kontextbeschreibungen.

- Freier Fall und Landung auf der Ebene; statischer Körper bleibt stehen.
- Körper-zu-Körper-Kontakt: zwei Würfel stapeln sich ohne Durchfallen.
- 50 unabhängige Körper landen und liefern endliche Posen.
- Pendel rotiert unter Gravitation; Gelenkanker bleibt fest.
- Motor treibt ein konvexes Rad; erneutes Initialisieren stellt die Anfangslage wieder her.
- Verschachtelte, gespiegelte und skalierte Geometrie wird korrekt kopiert, ohne das Original zu verändern.
- Demo und Parameteränderungen sind rückgängig machbar; Parameter überstehen `.igz`-Speichern und Laden.
- Unkonfigurierte, ignorierte und verborgene Gruppen werden entsprechend der dokumentierten Regeln behandelt.
- Echter externer Worker antwortet auf JSON-Protokoll und meldet ungültige Befehle.
- IngeTrazos echter Plugin-Loader und MainWindow laden die Extension; Simulation, Pause, Reset und unerwartetes Prozessende bewahren Originalszene und History.
- Servo fährt unter Gravitation wechselnde Zielwinkel an und hält sie.
- Linearpositionsantrieb fährt Zielwege an und begrenzt sie an den Anschlägen.
- Freie Linearachse fällt ausschließlich entlang ihrer Achse; Geschwindigkeitsantrieb lässt sich umkehren.
- Gelenk zwischen beweglichen Körpern führt seinen Anker mit dem Elternkörper mit.
- Gelenkkreise und fehlende Eltern werden ausdrücklich abgefangen; Legacy-Gelenke werden interpretiert.
- Benannte Regler fahren über echte externe Sessions eine Tür auf 60° und einen Schlitten auf 400 mm. Reset verwirft Laufzeitziele, ohne Startwerte zu verändern.
- Zwei Fangpunkte und die Achsen-Tastenkürzel richten Gelenke aus; Z wird vor dem eingebauten Zoom-Kürzel abgefangen.
- Native Verschiebungen des Bezugskörpers führen abhängige Teile und deren Achsen nach, auch bei klassischen Gruppen ohne Instanzmatrix.
- Kindbewegungen verändern den Bezugskörper nicht; Mehrfachauswahl bewegt Kinder nicht doppelt.
- Rotation, Live-Vorschau, Lösen der Zuordnung, Undo/Redo und Bezugskörper-Zuordnung nach `.igz`-Neuladen werden geprüft.
- Newtonalisches Ziehen bewegt passive Körper ohne Teleportieren und setzt passive Gelenkketten in Bewegung. Servo-/Motorkörper werden im Worker ausdrücklich abgewiesen.
- Bezugskörper-Verbindungen ohne eigene Achse bilden in der Simulation eine starre Verbindung.
- Ein als fest markiertes abhängiges Teil folgt seinem beweglichen Bezugskörper, lässt sich aber nicht selbst greifen.
- Geschwindigkeits- und Beschleunigungsgrenzen des Antriebs-Sollverlaufs werden geprüft.
- Alle elf Toolbar-Aktionen besitzen Icons; vier Trenner gliedern die Funktionen. Profilverwaltung und Einstellungen sind aus der Toolbar entfernt. Native Icons, alternative Sets und Palettenwechsel werden geprüft.
- Achsen werden ohne Dialog platziert; Sidebar-Änderungen gelten direkt, mit korrekter Einheitenumrechnung und ohne unbeabsichtigte History-Einträge beim Aktualisieren der Anzeige.
- Der native Radiergummi entfernt Dreh- und Linearachsen, erhält Geometrie und Bezugskörper und unterstützt Undo. Achsenstrich, Mehrfachachsen, Shift, Abbruch und gewöhnliches Geometrieradieren werden geprüft.
- Acht eingebaute Profile, Erstellen aus Objekteinstellungen, Umbenennen, Ersetzen und Löschen eigener Profile; Anwendung erhält räumliche Daten und Identitäten und bildet einen Undo-Schritt. Abbruch der Achsenplatzierung verändert nichts.
- Steuerpult startet, pausiert, setzt fort und setzt zurück, auch ohne Objektauswahl.
- Ohne Auswahl bleibt die Newton-Sidebar leer. Die echte Browser-Typspalte zeigt Servo-Achskörper und Reglernamen.
- Deutsche Hostsprache und englischer Fallback bei nicht unterstützter Sprache; englischer Masterkatalog und gültige Übersetzungsschlüssel.
- Der native Preferences-Dialog enthält genau einen Newton-Tab mit Icon-Auswahl und Profilverwaltung. Änderungen bleiben bis OK lokal, Abbrechen verwirft sie. Speichern, Umbenennen, Ersetzen und Löschen von Profilen werden im Dialog geprüft. Die bestehende Einheiten-Seitennavigation bleibt erhalten.
- Solver-Kopplung hält beide Backen gleich weit bewegt, auch bei asymmetrischer Last an einem festen Prüfkörper. Beide Kontaktpaare werden geprüft. Wiederöffnen, negativer Übersetzungsfaktor, begrenzter gemeinsamer Weg sowie Geschwindigkeits-/Beschleunigungsgrenzen werden geprüft. Fehlende Achsen, Kreise und ungültige Kopplungen werden abgewiesen.
- Ein Öffnungsregler bildet 5–105 mm auf den gemeinsamen Backenweg ab. Die Folgeachse hat keinen zweiten Regler, lässt sich nicht ziehen und wird beim Entfernen der führenden Achse in einem gemeinsamen Undo-Schritt entkoppelt.
- Vorhandener `Newton_Axes`-Layer wird wiederverwendet; Sichtbarkeit und Kopplung überstehen Speichern/Laden. Ausblenden unterdrückt Zeichnen und Achsen-Picking, ohne Körper oder Newton zu deaktivieren.
- Markierungen für Bereich, Grenzen, Nullstellung, Ziel und Istposition werden geprüft. Der Achsenrahmen folgt während der Simulation dem bewegten Bezugskörper.

## Sichtprüfung und Installation

Die Sichtprüfung von 0.5.0 zeigte im separaten IngeTrazo-Testfenster native Icons und Trenner, das räumliche Drehachsensymbol, Profilwahl und Bewegungsparameter ohne Übernehmen-Button. Das geöffnete Steuerpult zeigte den benannten Regler und Start/Reset; Pause/Fortsetzen werden zustandsabhängig angezeigt und durch Hosttests geprüft. Die zusätzliche Preferences-Integration von 0.5.1 wurde gegen den echten Hostdialog automatisiert geprüft. In der Vorversion wurden Pendelstart und Servo-Tür auf 60° zusätzlich sichtbar geprüft. Radiergummi, Profilverwaltung und Ziehen sind automatisiert geprüft; ein vollständiger manueller Abnahmelauf dieser Interaktionen wurde nicht aufgezeichnet. Kein Bildratenbenchmark.

Der lokale Installer wurde zuerst in einem Projekt-Testordner ausgeführt. Anschließend wurde die Extension unter `%APPDATA%\ingetrazo\plugins\newton` installiert. Die konfigurierte Newtonlaufzeit ist die `.venv` dieses Projekts; der Installer konnte MuJoCo 3.3.7 importieren.

Die bereits laufende installierte IngeTrazo-EXE wurde nicht neu gestartet. Ihr geöffnetes Nutzerprojekt wurde nicht geändert. Die endgültige Freigabe für genau diese EXE setzt deshalb deren nächsten Neustart und das Laden der Extension voraus; die automatische Hostprüfung erfolgte gegen den oben genannten Quellstand.

Das neue Synchrongreifer-Modell wurde mit dem nativen Host geöffnet. Das Steuerpult zeigt fünf Regler einschließlich einer gemeinsamen Öffnungsweite. Der Achsen-Layer ist im nativen Layerbaum vorhanden. Die detaillierte Grenz- und Positionsgeometrie wurde in Hosttests geprüft; ein vollständiger manueller Durchlauf aller Sichtbarkeits- und Grenzänderungen wurde nicht aufgezeichnet.

Das separate Modell `models/Kollisionen-Testmodell.igz` wurde im nativen Fenster geöffnet. Sichtbar geprüft wurden die Kollisionsumrisse, der aufliegende blaue Würfel und der durch seine Platte gefallene orangefarbene Würfel. Ein vollständiger manueller Test aller Achsengriffe und Snap-Ansichten wurde nicht aufgezeichnet; diese Fälle sind durch die Hosttests abgedeckt.

Ein installierbares ZIP liegt unter `dist/newton-0.14.0.zip`. Es enthält den Extension-Code, englischen und deutschen Sprachkatalog und die Installationsanleitung, aber keine Python- oder MuJoCo-Binärdateien.
