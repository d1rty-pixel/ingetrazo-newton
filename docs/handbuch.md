# Newton – Handbuch

Dieses Handbuch beschreibt die Bedienung von Newton 0.14.0. Installation und Überblick stehen in der [README](../README.md), die Beispielmodelle in [beispielmodelle.md](beispielmodelle.md).

## Grundablauf

1. Eine Gruppe oder Komponente auswählen.
2. In der **Newton-Toolbar** das **Drehachsen-Icon** oder **Linearachsen-Icon** anklicken. Es öffnet sich kein Dialog.
3. Im Modell zuerst den Dreh-/Startpunkt setzen. Ein zweiter Klick legt die positive Achsenrichtung fest. Die Fangfunktionen von IngeTrazo gelten dabei. Nach dem ersten Klick kann alternativ **X**, **Y** oder **Z** gedrückt werden. **Esc** bricht ohne Änderung ab.
4. In der **Newton-Sidebar** das Verhalten und den Antrieb einstellen. Änderungen gelten direkt: Zahlen mit Enter oder beim Verlassen des Feldes, Auswahllisten und Schalter sofort. Jede Änderung ist rückgängig machbar.
5. **Start** drücken. Passive Körper lassen sich mit gedrückter linker Maustaste greifen und ziehen. Das **Steuerpult** enthält benannte Antriebsregler. **Reset** kehrt zum unveränderten Originalmodell zurück.

## Sidebar

Alle Parameter stehen bei der gewählten Gruppe in der Sidebar. Sie ist wie die übrigen IngeTrazo-Seitenleisten in einklappbare Bereiche gegliedert: Ein Klick auf die Überschrift klappt einen Bereich auf oder zu, und dieser Zustand bleibt über einen Neustart erhalten. **Allgemein**, **Profil** und **Bewegung** sind anfangs offen, die übrigen Bereiche eingeklappt.

Wo die Sidebar auf einen anderen Körper verweist (Bezugskörper, Gegenkörper einer Verbindung, Endbefestigung, Leitachse einer Kopplung, Kollisionsausnahmen), steht er als eigene Zeile mit kleinem Vorschaubild und Namen. Das Trennsymbol dahinter entfernt den Verweis; beide Körper bleiben erhalten, und der Schritt ist rückgängig machbar.

Im Modell sind solche Beziehungen umrandet: Ist ein Körper ausgewählt, tragen die mit ihm verbundenen Körper einen Rand, in beide Richtungen: gelb für Bezugskörper, abhängige Körper und Kopplungen, magenta für Gegenkörper mechanischer Verbindungen und Seilenden, cyan gestrichelt für Kollisionsausnahmen. Beim Auswählen eines Körpers, etwa des Bezugskörpers, des Gegenkörpers einer Verbindung oder im Menü **Wählen…**, trägt der Körper unter dem Mauszeiger einen Rand in der Akzentfarbe, sofern er dafür in Frage kommt.

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

Die Modelllage beim Einrichten entspricht 0° beziehungsweise 0 mm. Ein verwendeter Grenzbereich muss diese Anfangslage enthalten. Körperwerte und lokale Overrides stehen in den Bereichen **Körper & Kontakt** und **Simulation Overrides**; globale Simulation und Runtime-Auswahl stehen in den Extension-Preferences.

Beschleunigung und Bremsverzögerung sind zunächst gekoppelt. Mit aktiviertem Kettenschalter folgt die Bremsverzögerung jeder Änderung der Beschleunigung. Nach dem Lösen lässt sie sich getrennt einstellen; erneutes Koppeln übernimmt sofort den Beschleunigungswert. Die Grenzen gelten in °/s² beziehungsweise mm/s² für den Sollverlauf. Beim Richtungswechsel bremst der Antrieb zuerst auf null und beschleunigt anschließend in die andere Richtung. Beide Werte und die Kopplung werden mit Profilen und Modellen gespeichert; ältere Einstellungen übernehmen automatisch die bisherige symmetrische Beschleunigung.

Bei Mehrfachauswahl lassen sich Körperwerte und lose/fest gemeinsam ändern. Achsen und Bezugskörper werden für eine einzelne gewählte Gruppe eingerichtet. Ohne ausgewählten Körper bleibt die Newton-Sidebar leer. Die Übersicht befindet sich im vorhandenen **Browser**: Die Typ-Spalte zeigt Newton, Achsenart und Reglername. Die bestehenden Körpernamen bleiben erhalten; es entstehen keine zusätzlichen Geometrieobjekte für Regler.

Der Bereich **Generic** steht oben in der Sidebar. Der ausgewählte Gruppen-/Komponentenname erscheint in der Überschrift hinter **Newton properties**. Beim Start bleibt die zuvor angezeigte Konfiguration sichtbar und wird deaktiviert, die Bereiche lassen sich weiter auf- und zuklappen; die Sidebar lässt sich weiterhin durchscrollen. Start/Pause und Reset liegen in Toolbar und Steuerpult. Hinweise zum Platzieren und Bearbeiten erscheinen einige Sekunden in der Statuszeile von IngeTrazo, Meldungen der laufenden Simulation im Steuerpult. Ohne Auswahl bleibt die Sidebar wie bisher leer.

Winkelanschläge, Positions-/Zielwerte und die begrenzten Körper- und Umgebungswerte Reibung, Rückprall und Schwerkraft besitzen breite Schieberegler mit kompaktem Zahlenfeld. Bei einem begrenzten Positionsantrieb entspricht der Reglerbereich genau Minimum und Maximum, bei einem Geschwindigkeitsantrieb ±Maximalgeschwindigkeit. Das gilt auch für Linearachsen in Millimetern. Die Bereiche passen sich bei Änderungen der Grenzen sofort an. Genaue Eingaben bleiben möglich; Winkel über eine volle Umdrehung werden unterstützt. Ein Ziehvorgang ändert das Modell live und bleibt ein gemeinsamer Undo-Schritt. Beim Scrollen über diese Regler werden Werte nicht versehentlich geändert.

## Achsen platzieren und bearbeiten

Drehachsen erscheinen als ausgerichteter Kreis mit Achsenlinie; Linearachsen als Richtungspfeil. Beim Platzieren zeigt Newton nach dem Klick auf den Startpunkt die künftige Achse in Richtung des Mauszeigers. Bei Drehachsen folgt als letzter Schritt die **0°-Richtung**: ein Klick (oder X/Y/Z) senkrecht zur Achse legt fest, wo 0° liegt; **Enter** behält die bisherige Richtung. Der Mauszeiger arbeitet dabei in der Drehebene der Achse, fängt an Geometrie und rastet auf die in diese Ebene projizierten Weltachsen ein. Newton misst daraus den **Startwinkel**, also den Winkel der modellierten Lage (Richtung vom Achspunkt zur Körpermitte) gegenüber 0°. Anschläge, Ziele und Ist-Werte gelten danach absolut zu dieser 0°-Richtung; eine geöffnet gezeichnete Tür kann so Anschläge und Ziel auf „geschlossen = 0°“ beziehen. Liegt der Startwinkel außerhalb der bisherigen Anschläge, verschiebt Newton sie beim Platzieren um den Startwinkel. Die 0°-Richtung dreht mit, wenn Körper oder Achsobjekt gedreht werden; Drehen nur des Achsobjekts um die eigene Achse ändert den Startwinkel. Mit dem Auswahlwerkzeug lässt sich ein Achsensymbol anklicken; ausgewählt wird dann das zugehörige Achsobjekt, die Sidebar zeigt seinen Körper. Verschoben, gedreht und skaliert wird das Achsobjekt mit den Werkzeugen von IngeTrazo; eigene Ziehgriffe gibt es nicht. Alternativ bleibt die Neupositionierung über das entsprechende Toolbar-Icon verfügbar. Während der Simulation und auf gesperrten Achsen-Layern ist die Bearbeitung gesperrt.

Jede Achse ist zusätzlich ein eigenes Objekt **Achse · <Körper>** aus Kanten auf dem Layer `Newton Axes`. Die IngeTrazo-Werkzeuge Verschieben, Drehen und Skalieren wirken darauf wie auf jede Gruppe: Startpunkt und Richtung der Achse folgen dem Objekt, im selben Undo-Schritt. Wird der Körper verschoben, wandert das Achsobjekt mit. Löschen des Achsobjekts entfernt die Achse; eine Kopie des Achsobjekts wird verworfen, eine Kopie des Körpers erhält ein eigenes. Dokumente ohne Achsobjekte erhalten sie beim Öffnen. Achsobjekte nehmen an der Simulation nicht teil. Ist ein Körper ausgewählt, ersetzt **Newton ▸ Achsobjekt auswählen** bzw. **Verbindungsobjekt auswählen** im Kontextmenü die Auswahl durch das jeweilige Objekt; der Eintrag ist nur aktiv, wenn der Körper ein solches Objekt besitzt. **Achsobjekt sperren** (Bereich **Bewegung**) und **Verbindungsobjekt sperren** (Bereich **Mechanische Verbindung**) setzen die Objektsperre von IngeTrazo: Das Objekt lässt sich im Modell weder auswählen noch mit Werkzeugen verschieben oder drehen, folgt aber weiter seinem Körper. Bei gesperrtem Verbindungsobjekt sind auch die Punktfelder gesperrt. Entsperren geht über dieselbe Checkbox oder den Browser; beides ist rückgängig machbar.

Die Achsenplatzierung verwendet dieselbe Fang- und Achsen-Inferenz wie das native Linienwerkzeug. Fangpunkte auf vorhandener Geometrie, die magnetische Ausrichtung an X/Y/Z und die Shift-Sperre bleiben verfügbar; es ist keine separate Fangberechnung nötig.

Mit dem nativen **Radiergummi (E)** lässt sich ein Achsensymbol entfernen. Körpergeometrie und Bezugskörper-Zuordnung bleiben dabei erhalten. Der Button **Achse entfernen** bleibt verfügbar. Ein auf einer Achse begonnener Radierstrich löscht ausschließlich Achsen; Undo stellt sie wieder her.

Alle Achsendarstellungen gehören zum reservierten, sprachunabhängigen Layer **`Newton Axes`**. Die Extension verwendet einen bestehenden Layer dieses Namens oder legt ihn an, sobald Achsen vorhanden sind. Das Auge im nativen Layers-Panel blendet die Darstellungen gemeinsam aus; Geometrie und Newton bleiben aktiv. Ein gesperrter Achsen-Layer verhindert das Radieren seiner Symbole. Die Körper behalten ihre ursprünglichen Layer. Achsobjekte bestehen nur aus Kanten und erzeugen keine Modellflächen; der Layer wird nicht gedruckt.

Beim ausgewählten Körper erscheinen farbige Grenzen und kurze Zahlen direkt an seiner Achse: **Grün** markiert den Bewegungsbereich, **Blau/Rot** die Anschläge und **Gelb** die aktuelle Position. Das **violette gestrichelte** Zeichen zeigt das Servo-Ziel, die gepunktete Linie die Nullstellung. Drehachsen verwenden Winkelbögen, Linearachsen eine maßstäbliche Strecke. In der Simulation folgen die Anzeigen dem Bezugskörper und den tatsächlichen Gelenkständen. Das Bedienen eines Reglers hebt die zugehörige Achse hervor. Andere Achsen bleiben dezent.

Die Achsenbeschriftung verwendet mindestens 12 pt in Fettschrift und dunkle, kontrastreiche Schilder. Min, Max und Ist werden benannt. Die Platzierung sucht freien Raum außerhalb aller projizierten Achsen und vermeidet andere Schilder. Dünne gepunktete Hinweislinien ordnen die Schilder zu. Bei sehr dicht belegten Ansichten wird die Position mit der geringsten Überdeckung gewählt. Positions- und Bereichslinien sind 4 px stark, Anschläge und Ziele 3 px. Auch die Schilder lassen sich als Achsen auswählen oder mit dem Radiergummi entfernen.

## Bezugskörper

Der professionelle Begriff für die Zuordnung zu einem übergeordneten Element ist **Bezugskörper**.

- Kind auswählen → **Kettensymbol „Bezugskörper zuweisen“** → Bezugskörper im Modell anklicken. Alternativ stehen die Befehle im Kontextmenü und in der Sidebar bereit.
- Beim normalen Verschieben des Bezugskörpers folgen seine abhängigen Teile, einschließlich weiterer Unterstufen. Sie sind auch in der Bewegungsvorschau enthalten. Die Änderung bleibt **ein gemeinsamer Undo-Schritt**.
- Wird nur das Kind verschoben, bleibt der Bezugskörper stehen. Die Zuordnung bleibt erhalten; Unterstufen des Kindes folgen dem Kind.
- Rotation und Skalierung über die nativen Gruppentransformationen werden ebenfalls weitergegeben; Achsenposition und Richtung werden mitgeführt.
- **Bezugskörper-Zuordnung lösen** trennt die Abhängigkeit, ohne Teile zu verschieben. Eine vorhandene Achse bleibt erhalten und bezieht sich danach auf die Welt.
- Ein beweglicher Körper mit Bezugskörper, aber ohne eigene Achse, ist in der Simulation starr mit seinem Bezugskörper verbunden. Eine platzierte Achse gibt die entsprechende relative Bewegung frei.
- **Fest** bedeutet mit Bezugskörper: fest an diesem verschraubt. Der Körper folgt dessen Bewegung, lässt sich aber nicht selbst ziehen. Ohne Bezugskörper bedeutet fest: an der Welt fixiert.
- Einstellungen ohne Wirkung sind deaktiviert. Bei **Fest** betrifft das Bewegung, Achskopplung und Biegsames Material; Masse und eigene Simulationseinstellungen bleiben nur mit Bezugskörper aktiv, weil der Körper dann dessen Bewegung mitträgt. Eine mechanische Verbindung bleibt möglich, denn ein fester Körper kann einen beweglichen verankern. Bei **Nicht simulieren** bleiben nur Verhalten und Profil bedienbar.
- Ohne Bezugskörper ist eine platzierte Achse an der Welt befestigt. Ein beweglicher Körper ohne Achse und ohne Bezugskörper ist frei beweglich.

Direkt verbundene Körper kollidieren nicht miteinander, damit sich Lager nicht selbst blockieren. Andere Körperpaare kollidieren weiterhin. Geschlossene Bezugskörper-/Gelenkkreise werden mit einer Meldung abgewiesen.

## Verbindungen zwischen Körpern

Die drei Toolbar-Icons **Kugelgelenk**, **Bolzengelenk** und **Starre Verbindung** erstellen eine zusätzliche Verbindung zwischen zwei Körpern; sie zeigen dieselben Bilder wie die Typauswahl. Einen Körper auswählen, das Icon des gewünschten Typs anklicken, den gemeinsamen Verbindungspunkt setzen und zum Schluss den Gegenkörper anklicken; der Körper unter dem Mauszeiger ist dabei umrandet, wenn er in Frage kommt. Ein **Kugelgelenk** lässt räumliche Drehungen frei. Für ein **Bolzengelenk** nach dem Punkt die Richtung anklicken oder X/Y/Z drücken, dann den Gegenkörper. Eine **starre Verbindung** hält die relative Lage fest. **Körper verbinden…** im Kontextmenü und in der Sidebar läuft genauso ab und verwendet den im Bereich **Mechanische Verbindung** gewählten Typ. So lassen sich geschlossene Mechanismen aufbauen, ohne die Bezugskörper-Hierarchie umzubauen. Wäre der gewählte Körper fest an einem festen Gegenkörper oder ohne Newton, wird er dabei automatisch beweglich, sonst könnte sich nichts bewegen; ein fester Körper, an dem ein beweglicher Gegenkörper hängt, bleibt fest. Die Statusleiste meldet das Ergebnis.

Jede Verbindung ist zusätzlich ein eigenes Objekt **Verbindung · <Körper>** aus Kanten auf dem Layer `Newton Axes`. Seine Form zeigt den Typ wie sein Piktogramm in der Auswahlliste: ein Kugelgelenk eine Kugel, ein Bolzengelenk einen gestrichelten Bolzen durch einen Ring, eine starre Verbindung einen Würfel mit einer verschraubten Platte am Verbindungspunkt. Die Extension zeichnet es in den Farben der Achsen nach, mit gelbem Verbindungspunkt, beim Überfahren rot, gesperrt grau. Violett bleibt dem Servo-Ziel vorbehalten. Ist der Körper ausgewählt, nennt ein Schild „→ Gegenkörper“. Bei kleinen Körpern bleibt die Darstellung mindestens 18 px groß. Wie beim Achsobjekt wirken Verschieben, Drehen und Skalieren von IngeTrazo darauf: Verbindungspunkt und Bolzenachse folgen dem Objekt, im selben Undo-Schritt; wird der Körper verschoben, wandert das Verbindungsobjekt mit. Da der Verbindungspunkt meist im Körper liegt, wählt ein Klick mit dem Auswahlwerkzeug in seiner Nähe das Verbindungsobjekt statt des Körpers; es leuchtet dabei auf. Löschen oder Radieren des Verbindungsobjekts entfernt die Verbindung und erhält beide Körper. Alternativ stehen Sidebar und Kontextmenü bereit. In der Sidebar steht der Gegenkörper als Zeile mit Vorschaubild; **Verbundenen Körper festlegen…** tauscht nur den Gegenkörper aus, Punkt, Typ und Bolzenachse bleiben. Das Trennsymbol der Zeile entfernt die Verbindung. Punktkoordinaten sind direkt in Millimetern editierbar; Bolzen besitzen eine editierbare Achse. Während der Simulation zeigt eine gelbe Markierung den mitbewegten Verbindungspunkt. Verbindungsobjekte nehmen an der Simulation nicht teil. Seile/Kabel verwenden weiterhin ihre eigenen Endbefestigungen. Verbindungstyp, Befestigungspunkt und Bolzenachse werden in der `.igz` gespeichert.

## Gemeinsam bewegte Achsen

Im Bereich **Achskopplung → Achse folgen → Wählen…** kann eine Achse einem Positionsantrieb desselben Typs folgen; das Menü zeigt nur passende Achsen. Die gewählte Leitachse erscheint als Zeile, ihr Trennsymbol macht die Achse wieder unabhängig. **Gleichläufig/Gegenläufig** bezieht sich auf die räumliche Richtung der beiden Achsen. Eine Übersetzung von 1 bedeutet gleichen Weg beziehungsweise Winkel. Standardmäßig ist jede Achse unabhängig.

Die Kopplung wird im MuJoCo-Solver erzwungen. Im Steuerpult erscheint nur der führende Regler; die folgende Achse lässt sich nicht ziehen. Die zulässigen Wege, Geschwindigkeiten und Beschleunigungen werden auf den gemeinsamen Bereich begrenzt. Der führende Antrieb liefert die gemeinsame Kraft beziehungsweise das gemeinsame Drehmoment; das Kraftlimit der folgenden Achse wird nicht als zweiter Antrieb verwendet. Ein führender Antrieb kann mehrere direkte Folgeachsen besitzen. Kopplungsketten, Kreise und gemischte Dreh-/Linear-Kopplungen sind noch nicht enthalten.

Beim Entfernen einer führenden Achse oder beim Festsetzen ihres Körpers werden ihre Folgeachsen wieder unabhängig. Dieser Vorgang ist gemeinsam rückgängig machbar. Kopplungen werden im Modell gespeichert; eigene Profile kopieren keine Verweise auf andere Modellkörper.

## Eigene Simulationseinstellungen und Kraftfelder

Die weiteren Objekteinstellungen sind in **Achskopplung**, **Körper & Kontakt** (mit den Kollisionsausnahmen) und **Eigene Simulationseinstellungen** gegliedert. Jeder Abschnitt erklärt zusammengehörige Parameter in einem Kontextabsatz. Die Achskopplung erscheint nur bei einer einzelnen ausgewählten Achse; Richtung und Übersetzung erscheinen erst bei einer folgenden Achse.

Unter **Eigene Simulationseinstellungen** kann ein Körper die globale Schwerkraft durch einen eigenen Weltvektor X/Y/Z ersetzen, lineare und rotatorische Dämpfung festlegen und den automatischen Boden bei Z = 0 unabhängig ein-/ausschalten. Modellierte Unterlagen behalten ihre normalen Kontakte. Ausschalten des Hauptschalters stellt die Vererbung wieder her. Die Overrides werden mit dem Modell und in eigenen Profilen gespeichert.

**Anziehung** erzeugt ein zum Körperschwerpunkt gerichtetes Newtonsches Kraftfeld mit der Stärke μ = G × Masse (m³/s²). Null erzeugt kein Feld. Verwenden alle Körper dasselbe G, wirken die Kräfte gegenseitig und erhalten den Gesamtimpuls. Ein Glättungsradius entschärft die Singularität im Zentrum. **Startgeschwindigkeit X/Y/Z** gilt für frei bewegliche Körper in Weltkoordinaten und wird bei jedem Simulationsstart wiederhergestellt. Die Werte sind unabhängig von Gelenkantrieben.

## Seile, Kabel und Gelenkketten

Der Bereich **Flexibler Werkstoff** ergänzt **Starr**, **Seil** und **Kabel**. Für ein eigenes Seil/Kabel eine offene Linie oder einen zusammenhängenden offenen Linienzug zeichnen, gruppieren und den Werkstoff wählen. Eine einzelne Gerade wird automatisch in 20 Abschnitte unterteilt. Verzweigungen, geschlossene Schleifen und flächige Gruppen werden mit einer verständlichen Meldung abgelehnt. Bearbeitungen am ursprünglichen Linienzug werden beim nächsten Simulationsstart eingelesen; Gruppenbewegungen und Undo bleiben erhalten.

MuJoCos mitgeliefertes Plugin `mujoco.elasticity.cable` berechnet Biegung und Torsion einer nicht dehnbaren Folge räumlicher Kugelgelenke. Das Seil startet mit kleinem Biege-/Torsionsmodul, das Kabel mit höheren Werten; beide bleiben einstellbar. Radius und Gesamtmasse bestimmen zusätzlich das Verhalten. Der Anfang kann eingespannt, gelenkig befestigt oder frei sein. Ein starrer Bezugskörper bewegt die Anfangsbefestigung mit; das Ende lässt sich über **Endbefestigung → Wählen…** an einem weiteren starren Körper befestigen; das Trennsymbol der Zeile macht es wieder frei. Frei bewegliche Abschnitte lassen sich während der Simulation greifen. Reset stellt das Originalmodell wieder her. Die Flexibilität wird in der `.igz` gespeichert.

Für steifere und feinere Kabel verwendet der Worker automatisch kleinere interne Zeitschritte. Die nach außen gemeldete Simulationszeit und die Antriebsrampen bleiben gleich. Zu steife Konfigurationen werden mit einem Hinweis auf geringere Steifigkeit oder weniger Abschnitte abgewiesen. Eine numerisch instabile Simulation meldet einen Fehler.

Das sind biegsame, längenfeste Stränge und Gelenkmechanismen. Elastisches Dehnen wie bei Gummi, Bruch, allgemeine verformbare Volumenkörper und eine automatische Umwandlung beliebiger massiver Teile sind noch nicht enthalten. Die allgemeinen Körperprofile erfassen bislang die bisherigen Körper-/Antriebswerte, nicht die Mittellinie oder flexiblen Werkstoffdaten.

## Kollisionen prüfen und ausschalten

Kollisionsformen sind standardmäßig ausgeblendet. **Window → Preferences → Newton → Darstellung → Kollisionsformen in neuen Fenstern anzeigen** legt die Vorgabe für neue Fenster fest und übernimmt die Anzeige bei OK auch ins aktuelle Fenster. Die Ansicht verwendet die tatsächlichen Kollisionsformen des Newtonprozesses als farbige Umrisse mit transparenten Flächen. Der zusätzliche Befehl im Extensions-Menü schaltet die Anzeige vorübergehend um, auch ohne Auswahl und während der Simulation. Eine vorübergehende Umschaltung ändert die Startvorgabe nicht. Im Bereich **Körper & Kontakt** blendet **Kollisionsform anzeigen** nur die Form des ausgewählten Körpers ein oder aus, unabhängig von der globalen Anzeige und ohne sie zu ändern. Diese Ausnahme gilt nur für das geöffnete Dokument bis zum Neustart, wird nicht gespeichert und erzeugt keinen Undo-Schritt. Ältere gespeicherte Laufzeitanzeigen werden nicht als neue Startvorgabe übernommen.

Der Button **Tastenkürzel für Kollisionsanzeige…** in den Newton-Preferences öffnet IngeTrazos native Tastenkürzel-Seite direkt beim passenden Befehl. Dort lassen sich ein Kürzel vergeben und Konflikte prüfen; zunächst ist keines vorbelegt. Ausgewählte Körper werden in der Kollisionsansicht hervorgehoben. Die Anzeige verändert keine Kontakte. Im Bearbeitungsmodus wird die Form nach Geometrie- oder Parameteränderungen neu berechnet; Szene und Undo-History bleiben unverändert.

Im Bereich **Körper & Kontakt** unter **Kollisionsausnahmen**: einen Körper auswählen, **Körper ausnehmen…** drücken und den zweiten Körper im Modell anklicken. Dieses Paar darf sich anschließend durchdringen. Jede gespeicherte Ausnahme steht als Zeile mit Vorschaubild; ihr Trennsymbol aktiviert wieder das normale Kontaktverhalten. Beide Befehle sind rückgängig machbar und werden in der `.igz` gespeichert. Direkte Bezugskörper-Verbindungen bleiben zusätzlich automatisch von gegenseitiger Kollision ausgenommen.

## Simulation und Steuerpult

- **Start / Pause / Fortsetzen / Reset** sind in Toolbar und Steuerpult verfügbar. Start und Pause teilen sich einen zustandsabhängigen Button. Das Steuerpult funktioniert auch ohne Objektauswahl.
- In der Simulation greift die linke Maustaste passive, nicht feste Körper. Die Bewegung erfolgt als gedämpfte Zugkraft an der Greifstelle, ohne Teleportieren; Gelenke und Kontakte wirken weiter. Loslassen beendet die Zugkraft.
- Die Maus bewegt das Zugziel in der zum Bildschirm parallelen Ebene durch den Greifpunkt. Kamera-Navigation über die mittlere Maustaste bleibt verfügbar.
- **Servo- und Motorkörper mit Regler können nicht manuell gezogen werden**, auch dann nicht, wenn das Kraftlimit klein ist. Sie werden ausschließlich über das Steuerpult gesteuert. Diese Regel wird sowohl in der Oberfläche als auch im Newtonprozess geprüft.
- Beim Start öffnet sich das separate **Steuerpult** automatisch, falls es nicht schon offen ist. Es zeigt auch die Simulationszeit. Jede Aktorkarte trägt den Titel **Gruppen-/Komponentenname Aktorname**. Der Istwert steht ganz links, der breite Schieberegler mittig und das kleine Sollwert-Eingabefeld rechts. Reglerstil, Höhe, Abstand und 104-Pixel-Eingabefeld entsprechen den Min-/Max-Reglern der Sidebar. Eine gemeinsame Istwertspaltenbreite hält alle Regler bündig, auch bei unterschiedlichen Einheiten oder langen Zahlen. Es öffnet sich an der oberen rechten Ecke der 3D-Ansicht, neben der Sidebar, mit gleichem Abstand nach oben und rechts; unter Wayland bestimmt der Compositor die Position. Es ist nur so hoch wie seine Regler und scrollt, sobald diese höher als die 3D-Ansicht sind. Der Toolbar-Befehl öffnet das Steuerpult jederzeit erneut. Fehlermeldungen tragen ein rotes, Warnungen ein gelbes Ausrufezeichen; einfache Hinweise erscheinen ohne Zeichen.
- Bei Pause wird ein neues Reglerziel erst beim Fortsetzen angefahren. Reset verwirft die Laufzeitziele. Dauerhafte Startwerte werden in der Sidebar eingestellt.
- Geschwindigkeit und Beschleunigung begrenzen den Sollverlauf; der tatsächliche Körper folgt ihm entsprechend Kraftlimit, Lasten und Kontakten. Die Simulation bleibt physikalisch, daher ist dies keine Zusicherung einer exakt begrenzten realen Beschleunigung.
- Speichern im Simulations-Workspace weist auf Reset und anschließendes Speichern des Originals hin. Eine Übernahme der simulierten Endlage ist noch nicht enthalten.

Das Steuerpult zeigt die tatsächlich erreichte Simulationsgeschwindigkeit als **× Echtzeit**. Bei Pause wird keine Wartezeit in die Messung eingerechnet. Ein Tooltip nennt Newtonzeit, Anzeigeaufbereitung, Antwortzeit des Prozesses, Kontaktzahl, Solver-Iterationen und interne Teilschritte. Die Anzeigeaufbereitung misst das Anwenden der Posen und UI-Signale, nicht die reine GPU-Zeichenzeit.

Unter **Preferences → Newton → Simulation → Qualität** stehen **Schnell**, **Ausgewogen** und **Präzise**. Die Auswahl gilt beim nächsten Start. Lange Kabelmechanismen verwenden bei Schnell/Ausgewogen einen CG-Solver mit elliptischer Reibung; Präzise verwendet Newton mit engerer Toleranz. Kollisionsgeometrie, Kabelauflösung und die für Stabilität erforderlichen Zeitschritte werden dabei nicht vereinfacht. Nach einem Rechenpaket werden nur die positionsabhängigen Daten erneuert, statt für die Ausgabe erneut das vollständige Gleichungssystem zu lösen.

Geschwindigkeitsmotoren verwenden eine PI-Regelung mit Beschleunigungsvorsteuerung und Schutz vor dem Aufladen des Integrators am Kraftlimit. Dadurch gleicht der Motor Lasten aus, ohne sein eingestelltes Kraft-/Drehmomentlimit zu überschreiten. Im Steuerpult markiert **Limit** eine erreichte Begrenzung; der Istwert-Tooltip enthält Sollwert, aktuellen Rampenwert und Auslastung. Blockierte oder zu schwache Motoren bleiben physikalisch begrenzt.

## Profile

Die einfügbaren Beispielmodelle wurden aus der Oberfläche entfernt. Stattdessen gibt es acht vorgefertigte Profile: freie Drehachse, Drehmotor, Drehservo, freie Linearachse, Linearmotor, lineare Positionierung sowie freier und fester Körper.

Ein Profil überschreibt Masse, Reibung, Rückprall, Kollisionsform und Beweglichkeit sowie Antrieb, Grenzwerte, Startziel, Geschwindigkeit, Beschleunigung und Kraftlimit. Bei vorhandener Achse bleiben Platzierung, Reglername und Bezugskörper erhalten. Fehlt eine benötigte Achse, beginnt die Platzierung im Modell; Esc bricht ohne Datenänderung ab. Ein Körperprofil ohne Achse entfernt eine vorhandene Achse, erhält aber den Bezugskörper.

**Window → Preferences → Newton → Profile** zeigt die Werte jedes Profils nach Körper/Kontakt, Bewegung und Simulation Overrides. Eigene Profile sind direkt editierbar, Built-ins schreibgeschützt und duplizierbar. **Speichern unter…** übernimmt die aktuellen Objekteinstellungen. Änderungen in den Preferences werden mit **OK** gespeichert; **Abbrechen** verwirft sie.

Beim Anwenden merkt sich der Körper die Profil-ID und den übernommenen Parameterstand. Die Sidebar zeigt **Synchron**, **Lokal geändert**, **Profil geändert** oder **Profil fehlt**. **Sync** übernimmt die aktuellen Profilparameter und überschreibt lokale Abweichungen; Achslage, Namen, Geometrie und Bezugskörper bleiben erhalten. **Zuordnung lösen** erhält die Objektwerte. Die Zuordnung wird in der `.igz` gespeichert; eigene Profile liegen in den lokalen IngeTrazo-Benutzereinstellungen.

Unter **Preferences → Newton → Profile → Zugeordnete Körper synchronisieren (N)** lässt sich der gemeinsame Sync im aktuellen Modell für **OK** vormerken; erneutes Anklicken nimmt ihn zurück. Auch nach dem Vormerken bearbeitete Profilwerte werden verwendet. Der Vorgang wird vollständig geprüft und lässt sich mit einem Undo rückgängig machen. Bereits existierende Körper ohne Zuordnung kannst du mit **Auswahl zuordnen, Werte behalten** verbinden, ohne ihre Parameter sofort zu ändern. Neue Achsen benötigen weiterhin eine Platzierung in der Sidebar.

## Einstellungen, Toolbar und Sprache

**Window → Preferences → Newton** enthält vier Register: **Appearance / Darstellung**, **Simulation**, **Profiles / Profile** und **Runtime**. Dort stehen Kollisionsanzeige, globale Schwerkraft/Boden/Dämpfung, Profilverwaltung sowie der Python-Pfad. Änderungen werden erst mit OK übernommen, globale Simulationswerte beim nächsten Start verwendet. Die Sidebar enthält keine globale Simulation oder Runtime-Konfiguration mehr.

Jede Seite ist in Kategorien mit Überschrift gegliedert, die durch eine Linie getrennt sind. Jede Einstellung hat einen eigenen Erklärtext, der auch als Tooltip erscheint. Einstellungen, die eine physikalische Größe verändern (Schwerkraft, Boden, Dämpfung), zeigen zusätzlich ein Piktogramm dieser Größe. **Kollisionsformen in neuen Fenstern anzeigen** legt fest, ob die Kollisionsanzeige beim Öffnen eines Fensters eingeschaltet ist.

Vier native Trenner gliedern die zwölf Toolbar-Aktionen in Achsen/Verbindungen, Körper, Bezugskörper, Simulation und Sidebar. Profilverwaltung und Einstellungen sind aus der Toolbar entfernt. Die Toolbar verwendet IngeTrazos Toolbar-Größe. Die Icons folgen dem Stil von IngeTrazo: Die Form ist in Textfarbe gezeichnet, das bestimmende Detail (Drehpunkt, Richtung, Verbindung) in der Akzentfarbe. Deaktivierte Icons erscheinen vollständig grau. Die Icons reagieren auf die helle und dunkle Palette.

In Sidebar und Profil-Editor zeigen Auswahllisten mit festen Werten (Verhalten, Kollisionsform, Antrieb, Verbindung, Werkstoff, Befestigung, Kopplungsrichtung, Achse) zu jedem Wert ein Piktogramm, das die Wechselwirkung der beteiligten Körper darstellt. Zahlenfelder physikalischer Größen (etwa Masse, Reibung, Rückprall, Grenzen, Geschwindigkeit, Kraft, Schwerkraft, Dämpfung, Anziehung, Kabelradius und -steifigkeit) tragen ein kleines Piktogramm hinter ihrem Namen. Die Sidebar lässt sich bis etwa 280 px Breite verkleinern, ohne dass Inhalte abgeschnitten oder Zeilen gestaucht werden.

Die Extension ergänzt den nativen Preferences-Dialog über einen lokalen Adapter: Die Extension-API 2 besitzt dafür keinen offiziellen Registrierungspunkt. IngeTrazo-Dateien bleiben unverändert; bestehende Seiten und ihre Navigation bleiben erhalten. Dieser Adapter ist gegen den unten genannten Hoststand geprüft.

Die Oberfläche folgt IngeTrazos Spracheinstellung. Englisch und Deutsch sind enthalten. Englisch ist die Ausgangssprache; **`newton/i18n/en.json`** ist die Masterdatei, jede weitere Sprache liegt daneben als eigene Datei (etwa `de.json`) mit genau denselben Einträgen. Eine fehlende Sprache fällt auf Englisch zurück. Selbst vergebene Objekt-, Regler- und Profilnamen werden nicht übersetzt. Nach einer Änderung der Hostsprache gilt deren üblicher Neustartablauf.

## Technische Hinweise

Flächige Kontakte verwenden mehrere Kontaktpunkte und eine elliptische Reibungsberechnung. Ein konvexer Collider mit acht Ecken wird nur dann als exakter, räumlich ausgerichteter Quader berechnet, wenn alle Ecken den Quader mathematisch bestätigen. Andere Hüllen bleiben Hüllen. Damit kommen umgefallene Dominosteine zur Ruhe, ohne sie künstlich einzufrieren. Hintergrund: [MuJoCo 3.3.7, Kontaktoptionen](https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html#option-flag-multiccd).

Newton verwendet das Python-Paket `newton`, den Modellschlüssel `group.ext["newton"]`, den Settings-Präfix `newton/` und den reservierten Layer `Newton Axes`. Es gibt keine Kompatibilitäts-Aliasse und keinen automatischen Import früherer Daten oder Einstellungen. Die mitgelieferten Modelle sind auf dieses Schema umgestellt.

### Grenzen

- Ein Körper hat höchstens eine eingehende Bezugskörper-/Gelenkverbindung. Verzweigte Ketten funktionieren; geschlossene Bezugskörperketten und mehrere Gelenke am selben Körper noch nicht. Achskopplungen verbinden die Bewegungskoordinaten bereits vorhandener Gelenke.
- Newtonkörper sind aktuell Gruppen/Komponenten auf oberster Modellebene. Verschachtelte Geometrie innerhalb eines solchen Körpers bildet einen gemeinsamen Collider.
- Native Gruppentransformationen und ihre Undo-/Redo-Schritte werden durch lokale Extension-Adapter ergänzt. Direkte Geometrieänderungen durch andere Extensions ohne diese Commands können die Bezugskörper-Nachführung umgehen. Geometrie innerhalb eines Körpers zu verformen ist kein Verschieben des Körpers.
- Unkonfigurierte normale Gruppen sind statisch. Unkonfigurierte Face-me-Maßstabsfiguren sind nur visuell. Ausgeblendete Gruppen und Gruppen auf ausgeblendeten Layern nehmen unsichtbar an der Simulation teil, als wären sie sichtbar; lose Geometrie wird angezeigt, kollidiert aber nicht.
- Box und Kugel sind vereinfachte umschließende Collider. Konvexe Hüllen schließen konkave Löcher. Keine automatische konkave Zerlegung; degenerierte Hüllen können abgewiesen werden.
- Rückprall ist eine Näherung über MuJoCos Kontakt-Dämpfung. Der optionale Boden ist eine unendliche Ebene bei Z=0.
- Noch keine Kugel-/Universalgelenke, Replay, Magnetismus, Auftrieb oder SketchyPhysics-Skriptkompatibilität.
- Pro Fenster eine Simulation; der Workspace sperrt Projektwechsel. Keine garantierte Bildrate für große Modelle.
- IngeTrazos 0.x-API ist veränderlich. Geprüft wurde v0.6.0, Commit `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`.
