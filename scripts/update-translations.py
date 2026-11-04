"""Maintain the English master and German catalogue; migrate legacy UI text."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT/"newton"
LEGACY = {
    "Newton":"Newton", "Newton…":"Newton…", "Newton · Eigenschaften":"Newton properties",
    "Auswahl":"Selection", "Lose / beweglich":"Movable", "Fest":"Fixed", "Nicht simulieren":"Exclude from simulation",
    "Verhalten":"Behaviour", "Bezugskörper":"Reference body", "Keiner":"None", "Keiner · unabhängig":"None",
    "Zuweisen":"Assign", "Lösen":"Detach", "Bewegung":"Motion", "Noch keine Achse platziert":"No axis",
    "Reglername":"Control name", "Frei / passiv":"Free / passive", "Servo / Zielposition":"Servo / position",
    "Servo / Zielwinkel":"Servo / angle", "Position / Zielweg":"Position / distance", "Motor / Geschwindigkeit":"Motor / speed",
    "Antrieb":"Actuator", "Anschläge verwenden":"Use limits", "Minimum":"Minimum", "Maximum":"Maximum",
    "Startziel":"Initial target", "Geschwindigkeit":"Speed", "Beschleunigung":"Acceleration", "Max. Kraft":"Max. force",
    "Achse entfernen":"Remove axis", "Weitere Körper- und Umgebungseinstellungen":"More settings",
    "Konvexe Hülle":"Convex hull", "Kugel":"Sphere", "Kollisionsform":"Collision shape", "Masse (kg)":"Mass (kg)",
    "Reibung":"Friction", "Rückprall (Näherung)":"Bounce (approx.)", "Boden bei Z = 0":"Ground at Z = 0",
    "Schwerkraft Z (m/s²)":"Gravity Z (m/s²)", "Python mit MuJoCo":"Python with MuJoCo",
    "Laufzeit auswählen…":"Choose runtime…", "Python mit MuJoCo auswählen":"Choose Python with MuJoCo",
    "Python (python.exe python);;Alle Dateien (*)":"Python (python.exe python);;All files (*)",
    "Fortsetzen":"Resume", "Zurück im Originalmodell.":"Original model restored.",
    "Gruppe im Modell wählen":"Select a body.", "Gruppe wählen und eine Achse über die Newton-Toolbar platzieren.":"Select a body and place an axis.",
    "Gruppe wählen → Dreh- oder Linearachsen-Icon → Achse im Modell platzieren.":"Select a body and place an axis.",
    "Bewegungsparameter aktuell.":"Motion updated.", "Drehachse":"Rotation axis", "Linearachse":"Linear axis",
    " · starr angebunden, solange keine Achse platziert ist":" · rigid attachment",
    "Bitte genau eine Gruppe oder Komponente auswählen.":"Select one group or component.",
    "Projekt oder Körper wurde gewechselt. Achse erneut platzieren.":"Document changed. Place the axis again.",
    "Achse platziert. Antrieb und Grenzen in der Sidebar einstellen.":"Axis placed.",
    "Platzierung abgebrochen.":"Placement cancelled.",
    "Dreh-/Startpunkt anklicken, dann Richtung anklicken oder X/Y/Z drücken. Esc bricht ab.":"Pick the origin, then a direction or X/Y/Z. Esc cancels.",
    "Dreh-/Startpunkt anklicken. Esc bricht ab.":"Pick the origin. Esc cancels.",
    "Richtung: zweiten Punkt auf der Achse anklicken oder X/Y/Z drücken.":"Pick the direction or press X/Y/Z.",
    "Zuerst genau einen abhängigen Körper auswählen.":"Select one dependent body.",
    "Zuweisung abgebrochen.":"Assignment cancelled.",
    "Projekt gewechselt. Bezugskörper erneut wählen.":"Document changed. Pick the reference body again.",
    "Bezugskörper zugewiesen: ":"Reference body assigned: ",
    "Jetzt den Bezugskörper im Modell anklicken. Seine abhängigen Teile folgen beim Verschieben.":"Pick the reference body.",
    "Bezugskörper-Zuordnung gelöst; Lage und Bewegungsart bleiben erhalten.":"Reference body detached.",
    "Bezugskörper zuweisen":"Assign reference body", "Bezugskörper zuweisen…":"Assign reference body…",
    "Bezugskörper-Zuordnung lösen":"Detach reference body",
    "Bezugskörper im Modell anklicken. Esc bricht ab.":"Pick the reference body. Esc cancels.",
    "Simulation: passive Körper mit gedrückter Maustaste ziehen. Geregelte Körper über das Steuerpult bewegen.":"Drag passive bodies. Use controls for actuators.",
    "Passive Körper mit gedrückter Maustaste ziehen. Geregelte Körper über das Steuerpult bewegen.":"Drag passive bodies. Use controls for actuators.",
    "Newton · Ziehen":"Newton drag", "Achse platzieren":"Place axis",
    "Simulation fortsetzen, um einen Körper zu ziehen.":"Resume to drag a body.",
    "Dieser Körper ist fest oder geregelt. Antriebe werden über das Steuerpult bewegt.":"Fixed or actuated body. Use the controls.",
    "Während des Versuchs werden keine Modellteile gelöscht. Dafür zuerst Reset verwenden.":"Reset before deleting model geometry.",
    "Newton — temporäre Simulation":"Newton simulation", "Simulation ist temporär. Reset, dann das Originalprojekt speichern.":"Reset before saving the model.",
    "Newtonprozess antwortet nicht (15 Sekunden).":"Newton process timed out (15 seconds).",
    "Zuerst den aktuellen Workspace schließen.":"Close the current workspace first.",
    "Bitte einen Python-Interpreter mit installiertem MuJoCo wählen.":"Choose Python with MuJoCo installed.",
    "Simulationsansicht konnte nicht geöffnet werden.":"Could not open the simulation workspace.",
    "Simulation lieferte ungültige Körperpositionen":"Invalid simulation poses.",
    "Unbekannter Newtonfehler":"Unknown Newton error.",
    "Diese Bezugskörper-Zuordnung würde einen Gelenkkreis erzeugen.":"This reference would create a cycle.",
    "Bezugskörper fehlt. Bitte neu zuweisen oder Zuordnung lösen.":"Reference body is missing. Reassign or detach it.",
    "Der Bezugskörper muss sichtbar sein und an der Simulation teilnehmen.":"The reference body must be visible and participate in the simulation.",
    "Singuläre Transformation des Bezugskörpers":"Singular reference body transform.",
    "Gelenkachse darf nicht null sein":"The joint axis must not be zero.",
    "Unbekannter Gelenktyp oder Antrieb":"Unknown joint type or actuator.",
    "Ungültiger Gelenkparameter":"Invalid joint parameter.",
    "Gelenkgrenzen oder Kraft ungültig":"Invalid joint limits or force.",
    "Geschwindigkeit und Beschleunigung müssen positiv sein":"Speed and acceleration must be positive.",
    "Der Gelenkbereich muss die Startlage 0 enthalten":"Joint limits must include the initial position zero.",
    "Ungültige Gravitation":"Invalid gravity.", "Doppelte Körper-ID":"Duplicate body ID.",
    "Gelenkkreis erkannt. Jeder Körper darf einen übergeordneten Körper haben; geschlossene Ketten werden noch nicht unterstützt.":"Joint cycle detected. Closed chains are not supported.",
    "Verbundener Körper fehlt, ist verborgen oder ohne Newton. Gelenkverbindung prüfen.":"Referenced body is missing, hidden or excluded from the simulation.",
    "Ungültige Masse oder Körpergröße":"Invalid body mass or size.", "Ungültige Kontaktparameter":"Invalid contact properties.",
    "Ungültige Körpermasse":"Invalid body mass.", "Keine Welt oder Zeitschritt außerhalb 1..24":"No world or step count outside 1..24.",
    "Ungültiger Reglerwert oder unbekanntes Gelenk":"Invalid control target or unknown joint.",
    "Feste Körper können nicht gezogen werden":"Fixed bodies cannot be dragged.",
    "Geregelte Körper werden ausschließlich über ihren Regler bewegt":"Actuated bodies must use their controls.",
    "Keine dynamischen Körper. Gruppen auswählen und als dynamisch übernehmen oder Demo einfügen.":"No movable bodies. Select a body and make it movable.",
    "Ungültiger Vektor: ":"Invalid vector: ", "Unbekannte Kollisionsform: ":"Unknown collision shape: ",
    "Unbekannter Befehl: ":"Unknown command: ", "Newtonprozess: ":"Newton process: ",
    "Newtonprozess beendet (":"Newton process stopped (", "Anker":"Origin", "Achse":"Axis",
    "Körper konfigurieren und Newton simulieren":"Configure bodies and run Newton",
    "Simulationszeit: 0.00 s":"Time: 0.00 s",
}
EXTRA_DE = {
    "Pick the 0° direction, X/Y/Z, or Enter to keep it.":"0°-Richtung wählen, X/Y/Z oder Enter zum Beibehalten.",
    "Joint limits must include the initial position.":"Die Anschläge müssen die Startlage enthalten.",
    "Runtime":"Runtime","Built-in":"Built-in","Simulation overrides":"Simulation Overrides",
    "Child components":"Teilkomponenten","Compound":"Zusammengesetzt",
    "Compound collision needs child groups or components.":"Diese Kollisionsform benötigt untergeordnete Gruppen oder Komponenten.",
    "Invalid compound collision shape.":"Ungültige zusammengesetzte Kollisionsform.",
    "Quick":"Schnell","Balanced":"Ausgewogen","Precise":"Präzise","Quality":"Qualität",
    "Quick spends less time resolving contacts and connections. Precise improves constraint convergence. Cable stability steps and collision geometry stay unchanged. Applies at the next simulation start.":"Schnell benötigt weniger Rechenzeit für Kontakte und Verbindungen. Präzise löst diese genauer. Die Stabilitätsschritte für Kabel und die Kollisionsgeometrie bleiben gleich. Gilt ab dem nächsten Simulationsstart.",
    "Paused":"Pausiert","Measuring…":"Wird gemessen…","{speed:.2f}× real time":"{speed:.2f}× Echtzeit","Limit":"Limit",
    "Target: {target:.1f} · Ramp: {command:.1f} · Load: {load:.0f}%":"Soll: {target:.1f} · Rampe: {command:.1f} · Auslastung: {load:.0f}%",
    "Newton: {newton:.1f} ms\nDisplay preparation: {ui:.1f} ms\nRound trip: {roundtrip:.1f} ms\nBodies: {bodies} · Contacts: {contacts}\nSolver iterations: {iterations} · Substeps: {substeps}":"Newton: {newton:.1f} ms\nAnzeigeaufbereitung: {ui:.1f} ms\nRückmeldung: {roundtrip:.1f} ms\nKörper: {bodies} · Kontakte: {contacts}\nSolver-Iterationen: {iterations} · Teilschritte: {substeps}",
    "Connect bodies":"Körper verbinden","Connect bodies…":"Körper verbinden…","Connect…":"Verbinden…",
    "Replace…":"Neu platzieren…","Remove connection":"Verbindung entfernen","Mechanical connection":"Mechanische Verbindung",
    "Ball joint":"Kugelgelenk","Pin joint":"Bolzengelenk","Fixed connection":"Starre Verbindung",
    "Pin axis":"Bolzenachse","Point {axis}":"Punkt {axis}","Missing body":"Körper fehlt",
    "Pick another body and place the connection":"Gegenkörper wählen und Verbindung platzieren",
    "Pick the other body. Esc cancels.":"Den Gegenkörper wählen. Esc bricht ab.",
    "Pick the connection point. Esc cancels.":"Den Verbindungspunkt platzieren. Esc bricht ab.",
    "Pick the pin direction or press X/Y/Z.":"Die Bolzenrichtung wählen oder X/Y/Z drücken.",
    "Move connection point":"Verbindungspunkt verschieben","Drag the connection point. Esc cancels.":"Verbindungspunkt ziehen. Esc bricht ab.",
    "The body is hidden or locked.":"Der Körper ist ausgeblendet oder gesperrt.","Choose another body.":"Wähle einen anderen Körper.",
    "Make at least one body movable.":"Mindestens ein Körper muss beweglich sein.",
    "Use the flexible material end attachments for ropes and cables.":"Verwende bei Seilen und Kabeln die Endbefestigungen im Werkstoffbereich.",
    "Both bodies must participate in the simulation.":"Beide Körper müssen an der Simulation teilnehmen.",
    "Invalid mechanical connection.":"Ungültige mechanische Verbindung.","The connection axis must not be zero.":"Die Verbindungsachse darf nicht Null sein.",
    "Attachment body is missing or refers to itself.":"Der Befestigungskörper fehlt oder verweist auf sich selbst.",
    "Unknown simulation quality.":"Unbekannte Simulationsqualität.",
    "Connect this body to another at a point in the model. A ball joint allows rotation in all directions, a pin rotates around one axis, and a fixed connection locks their relative pose. These connections can close a mechanism such as a crank and piston without changing the reference-body hierarchy. Drag the connection marker to move it; use the eraser to remove it.":"Verbinde diesen Körper an einem Punkt im Modell mit einem anderen. Ein Kugelgelenk erlaubt Drehungen in alle Richtungen, ein Bolzen dreht um eine Achse, eine starre Verbindung hält die relative Lage fest. Damit lassen sich Mechanismen wie Kurbel und Kolben schließen, ohne die Bezugskörper-Hierarchie zu ändern. Ziehe die Verbindungsmarkierung zum Verschieben oder entferne sie mit dem Radiergummi.",
    "Choose a clamped or pinned start before assigning a reference body.":"Wähle einen eingespannten oder gelenkig befestigten Anfang, bevor du einen Bezugskörper zuweist.",
    "Rigid":"Starr","Rope":"Seil","Cable":"Kabel","Material":"Werkstoff","Radius":"Radius",
    "Flexible material":"Flexibler Werkstoff","Bending modulus":"Biegemodul","Torsion modulus":"Torsionsmodul",
    "Joint damping":"Gelenkdämpfung","Clamped":"Eingespannt","Pinned":"Gelenkig befestigt","Free":"Frei",
    "End attachment":"Endbefestigung",
    "Choose Rope or Cable for a grouped open line. The line becomes the centre line of an inextensible, bendable body during simulation. Radius and bending/torsion moduli determine stiffness; damping calms oscillations. The start can be clamped, pinned or free and follows the reference body. Optionally attach the end to another body. Total mass is set under Body & contact.":"Wähle Seil oder Kabel für eine gruppierte offene Linie. Sie wird in der Simulation zur Mittellinie eines nicht dehnbaren, biegsamen Körpers. Radius sowie Biege- und Torsionsmodul bestimmen die Steifigkeit; Dämpfung beruhigt Schwingungen. Der Anfang kann eingespannt, gelenkig befestigt oder frei sein und folgt dem Bezugskörper. Das Ende lässt sich an einem anderen Körper befestigen. Die Gesamtmasse steht unter Körper & Kontakt.",
    "Select a group containing one open line without faces.":"Wähle eine Gruppe mit einem einzelnen offenen Linienzug ohne Flächen.",
    "Invalid flexible material.":"Ungültiger flexibler Werkstoff.","Invalid centre line.":"Ungültige Mittellinie.",
    "Use a centre line with 3 to 201 points.":"Verwende eine Mittellinie mit 3 bis 201 Punkten.",
    "Centre line contains coincident points.":"Die Mittellinie enthält identische aufeinanderfolgende Punkte.",
    "Flexible bodies cannot also have a motion axis.":"Flexible Körper können nicht gleichzeitig eine Bewegungsachse besitzen.",
    "Use a rigid reference body.":"Verwende einen starren Bezugskörper.",
    "Invalid cable centre line.":"Ungültige Kabelmittellinie.","Invalid cable start.":"Ungültige Kabelbefestigung.",
    "Attachment body is missing.":"Der Befestigungskörper fehlt.",
    "Cable reference body is missing.":"Der Bezugskörper des Kabels fehlt.","Cable end body is missing.":"Der Körper der Kabelendbefestigung fehlt.",
    "Cable is too stiff for this resolution. Reduce stiffness or use fewer segments.":"Das Kabel ist für diese Auflösung zu steif. Verringere die Steifigkeit oder verwende weniger Segmente.",
    "Simulation became unstable. Reduce stiffness or use fewer segments.":"Die Simulation wurde instabil. Verringere die Steifigkeit oder verwende weniger Segmente.",
    "Capsule":"Kapsel",
    "Attraction":"Anziehung","Softening radius":"Glättungsradius",
    "Initial velocity {axis}":"Startgeschwindigkeit {axis}",
    "Invalid attraction.":"Ungültige Anziehung.",
    "Initial velocity needs a freely movable body.":"Eine Startgeschwindigkeit benötigt einen frei beweglichen Körper.",
    "Attraction pulls other bodies towards this body's centre. Its strength is G × mass; use the same G for each body for mutual gravity. Softening smooths the field near the centre. Initial velocity starts freely movable bodies in world coordinates and is restored by Reset.":"Anziehung zieht andere Körper zum Mittelpunkt dieses Körpers. Ihre Stärke entspricht G × Masse; verwende für gegenseitige Gravitation bei allen Körpern dasselbe G. Der Glättungsradius entschärft das Kraftfeld nahe am Mittelpunkt. Die Startgeschwindigkeit bewegt frei bewegliche Körper entlang der Weltachsen und wird bei Reset wiederhergestellt.",
    "Appearance":"Darstellung","Gravity Z":"Schwerkraft Z","Gravity {axis}":"Schwerkraft {axis}",
    "Linear damping":"Lineare Dämpfung","Angular damping":"Rotationsdämpfung",
    "Simulation overrides":"Eigene Simulationseinstellungen",
    "Use own simulation settings":"Eigene Einstellungen verwenden",
    "Ground contact at Z = 0":"Bodenkontakt bei Z = 0",
    "Invalid damping.":"Ungültige Dämpfung.","Invalid simulation override.":"Ungültige Simulationseinstellungen.",
    "Invalid ground contact override.":"Ungültige Bodenkontakteinstellung.",
    "These defaults apply at the next simulation start. Negative Z gravity pulls downwards; the optional ground is an infinite plane at Z = 0. Damping gradually reduces linear or rotational motion. Individual bodies can replace these defaults using Simulation overrides in the Newton sidebar.":"Diese Vorgaben gelten ab dem nächsten Simulationsstart. Eine negative Schwerkraft in Z-Richtung zieht nach unten; der optionale Boden ist eine unendliche Ebene bei Z = 0. Dämpfung bremst geradlinige Bewegungen oder Drehungen allmählich ab. Einzelne Körper können diese Vorgaben über Eigene Simulationseinstellungen in der Newton-Sidebar ersetzen.",
    "Normally this body uses the global simulation settings from Preferences. Enable overrides to give only this body its own gravity, damping and ground contact. Gravity is a world-space acceleration: zero makes it weightless, while positive Z pulls upwards. Disable overrides to inherit the global settings again.":"Normalerweise verwendet dieser Körper die globalen Simulationseinstellungen aus den Preferences. Aktiviere eigene Einstellungen, um nur für diesen Körper Schwerkraft, Dämpfung und Bodenkontakt festzulegen. Die Schwerkraft wirkt entlang der Weltachsen: Null macht den Körper schwerelos, ein positives Z zieht ihn nach oben. Nach dem Ausschalten gelten wieder die globalen Vorgaben.",
    "Generic":"Allgemein","Deceleration":"Bremsverzögerung",
    "Keep braking deceleration equal to acceleration":"Bremsverzögerung mit der Beschleunigung synchron halten",
    "Synchronize acceleration and deceleration":"Beschleunigung und Bremsverzögerung synchronisieren",
    "Show collision shapes in new windows":"Kollisionsformen in neuen Fenstern anzeigen",
    "Collision display":"Kollisionsanzeige","Accuracy":"Genauigkeit",
    "Gravity and ground":"Schwerkraft und Boden","Damping":"Dämpfung","Python environment":"Python-Umgebung",
    "Configure collision display shortcut…":"Tastenkürzel für Kollisionsanzeige…",
    "Collision shapes are visual inspection aids and start hidden by default. Enable them here for future windows, or assign a shortcut to toggle them while working. This display setting does not change the simulation contacts.":"Kollisionsformen sind eine visuelle Prüfhilfe und beim Start standardmäßig ausgeblendet. Aktiviere sie hier für künftige Fenster oder weise ein Tastenkürzel zu, um sie während der Arbeit umzuschalten. Diese Anzeigeeinstellung verändert die Simulationskontakte nicht.",
    "Show collision shapes":"Kollisionsformen anzeigen","Collision exceptions":"Kollisionsausnahmen",
    "Exclude body…":"Körper ausnehmen…","Restore collision":"Kollision wiederherstellen",
    "Remove exception":"Ausnahme entfernen",
    "Bodies normally collide with each other. Add another body here to let this pair pass through each other; other contacts stay active. Bodies directly attached to each other already have their mutual collision disabled automatically.":"Körper stoßen normalerweise miteinander zusammen. Füge hier einen anderen Körper hinzu, damit sich dieses Paar gegenseitig durchdringen kann; alle anderen Kontakte bleiben aktiv. Bei direkt miteinander verbundenen Körpern ist die gegenseitige Kollision bereits automatisch ausgeschaltet.",
    "Could not inspect collision shapes. Check the Newton Runtime.":"Kollisionsformen konnten nicht ermittelt werden. Bitte die Newton-Laufzeit prüfen.",
    "Pick the body that should pass through this body. Esc cancels.":"Den Körper anklicken, der diesen Körper durchdringen darf. Esc bricht ab.",
    "Edit axis":"Achse bearbeiten","Drag the handle. X/Y/Z sets direction; Esc cancels.":"Griff ziehen. X/Y/Z setzt die Richtung; Esc bricht ab.",
    "Document changed.":"Das Dokument wurde gewechselt.","Min":"Min","Max":"Max","Actual":"Ist",
    "Axis coupling":"Achskopplung","Body & contact":"Körper & Kontakt","Runtime":"Laufzeit",
    "Mass determines how strongly the body reacts to forces. Friction resists sliding, while bounce controls its response to impact. The collision shape approximates the visible geometry; a convex hull closes holes and recesses.":"Die Masse bestimmt, wie stark der Körper auf Kräfte reagiert. Reibung wirkt dem Gleiten entgegen, Rückprall beschreibt sein Verhalten beim Aufprall. Die Kollisionsform nähert die sichtbare Geometrie an; eine konvexe Hülle schließt Löcher und Vertiefungen.",
    "These settings apply to all bodies in the simulation. Negative Z gravity pulls downwards. The optional ground is an infinite horizontal plane at Z = 0; enable it when the model has no floor of its own.":"Diese Einstellungen gelten für alle Körper der Simulation. Eine negative Schwerkraft in Z-Richtung zieht nach unten. Der optionale Boden ist eine unendlich große horizontale Ebene bei Z = 0; aktiviere ihn, wenn das Modell keinen eigenen Boden hat.",
    "The Newton engine runs in a separate Python environment with MuJoCo installed. Choose its Python executable here if simulation cannot start or the environment has moved. This normally only needs to be configured once.":"Die Newtonberechnung läuft in einer separaten Python-Umgebung mit installiertem MuJoCo. Wähle hier deren Python-Programm, wenn die Simulation nicht startet oder die Umgebung verschoben wurde. Diese Einrichtung ist normalerweise nur einmal nötig.",
    "This axis drives {bodies} through a shared control. To change how a following axis moves, select that body. Its direction and ratio define the relationship; the leading axis supplies the drive force.":"Diese Achse treibt {bodies} über einen gemeinsamen Regler an. Um die Bewegung einer folgenden Achse einzustellen, wähle deren Körper aus. Richtung und Übersetzung bestimmen das Verhältnis; die führende Achse liefert die Antriebskraft.",
    "This axis follows the selected leading axis and uses its control. Direction determines whether the parts move together or in opposite directions. A ratio of 1 means equal travel or angle; 2 means this axis moves twice as far. The leading axis supplies the drive force.":"Diese Achse folgt der gewählten führenden Achse und verwendet deren Regler. Die Richtung bestimmt, ob sich die Teile gleichläufig oder gegenläufig bewegen. Eine Übersetzung von 1 bedeutet gleichen Weg oder Winkel; bei 2 bewegt sich diese Achse doppelt so weit. Die führende Achse liefert die Antriebskraft.",
    "This axis currently moves independently. Choose another position actuator to make it follow that axis through a shared control. Direction sets how the parts move relative to each other, and the ratio sets their relative travel or angle.":"Diese Achse bewegt sich derzeit unabhängig. Wähle einen anderen Positionsantrieb, damit sie dessen Achse über einen gemeinsamen Regler folgt. Die Richtung bestimmt die Bewegung der Teile zueinander, die Übersetzung das Verhältnis ihrer Wege oder Winkel.",
    "Follow axis":"Achse folgen","Direction":"Richtung","Ratio":"Übersetzung",
    "Independent":"Unabhängig","Same direction":"Gleichläufig","Opposite direction":"Gegenläufig",
    "Invalid axis coupling.":"Ungültige Achskopplung.",
    "Invalid control display.":"Ungültige Regleranzeige.",
    "Coupled axis is missing or refers to itself.":"Gekoppelte Achse fehlt oder verweist auf sich selbst.",
    "Coupling chains and cycles are not supported.":"Kopplungsketten und Kreise werden noch nicht unterstützt.",
    "Choose a matching position actuator.":"Einen passenden Positionsantrieb wählen.",
    "Coupled axes have no shared travel.":"Gekoppelte Achsen haben keinen gemeinsamen Bewegungsbereich.",
    "Use the shared actuator control.":"Den gemeinsamen Regler verwenden.",
    "Newton":"Newton","Newton properties":"Newton-Eigenschaften","Newton controls":"Newton-Steuerpult",
    "Newton settings":"Newton-Einstellungen","Newton profiles":"Newton-Profile","Newton…":"Newton…",
    "Profile":"Profil","Apply profile…":"Profil anwenden…","Save as…":"Speichern als…",
    "Apply to selection":"Auf Auswahl anwenden","Save selection as…":"Aus Auswahl speichern…",
    "Replace from selection":"Aus Auswahl ersetzen","Rename":"Umbenennen","Delete":"Löschen",
    "Built-in":"Vorgefertigt","Save profile":"Profil speichern","Rename profile":"Profil umbenennen","Name":"Name",
    "Profile applied.":"Profil angewendet.","Select one body.":"Einen Körper auswählen.",
    "A profile needs a name.":"Ein Profil benötigt einen Namen.","Invalid body profile.":"Ungültiges Körperprofil.",
    "Free rotation":"Freie Drehachse","Rotary motor":"Drehmotor","Rotary servo":"Drehservo",
    "Free linear axis":"Freie Linearachse","Linear motor":"Linearmotor","Linear positioning":"Lineare Positionierung",
    "Fixed body":"Fester Körper","Free body":"Freier Körper","World":"Welt",
    "IngeTrazo":"IngeTrazo",
    "Axes and profiles":"Achsen und Profile","Axes":"Achsen","Bodies":"Körper","References":"Bezugskörper",
    "Simulation":"Simulation","Extension":"Erweiterung","Profiles":"Profile","Controls":"Steuerpult",
    "Place rotation axis":"Drehachse platzieren","Place linear axis":"Linearachse platzieren",
    "Pick the pivot and direction":"Drehpunkt und Richtung anklicken","Pick the origin and direction":"Startpunkt und Richtung anklicken",
    "Manage parameter profiles":"Parameterprofile verwalten","Make the selection movable":"Auswahl beweglich machen",
    "Fix the selection":"Auswahl fixieren","Pick a reference body":"Bezugskörper anklicken",
    "Keep the current placement":"Aktuelle Lage beibehalten","Start / pause":"Start / Pause",
    "Run or pause the simulation":"Simulation starten oder pausieren","Return to the original model":"Zum Originalmodell zurückkehren",
    "Drag body":"Körper ziehen","Drag passive bodies":"Passive Körper ziehen","Open named actuator controls":"Benannte Antriebsregler öffnen",
    "Show properties of the selection":"Eigenschaften der Auswahl anzeigen",
    "Start":"Start","Pause":"Pause","Resume":"Fortsetzen","Reset":"Zurücksetzen",
    "No actuators":"Keine Antriebe","Actual: —":"Ist: —","Actual: {value:.1f} {unit}":"Ist: {value:.1f} {unit}",
    "Time: {seconds:.2f} s":"Zeit: {seconds:.2f} s","{count} bodies selected":"{count} Körper ausgewählt",
    "Parameters":"Parameter","None":"Keiner","Maximum":"Maximum","Minimum":"Minimum",
    "No movable bodies. Select a body and make it movable.":"Keine beweglichen Körper. Einen Körper auswählen und beweglich schalten.",
    "Axis placed.":"Achse platziert.","Motion updated.":"Bewegung aktualisiert.",
    "More settings":"Weitere Einstellungen", "Drag passive bodies. Use controls for actuators.":"Passive Körper ziehen. Antriebe über das Steuerpult.",
    "Fixed or actuated body. Use the controls.":"Fest oder angetrieben. Das Steuerpult verwenden.",
    "Select a body and place an axis.":"Körper wählen und Achse platzieren.",
}


def migrate():
    standalone = {"worker.py","model.py","references.py"}
    for name in ("panel.py","joints.py","interaction.py","session.py","references.py","worker.py","model.py","__init__.py"):
        path = PACKAGE/name
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        parents = {child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        data = text.encode("utf-8")
        lines = data.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1]+len(line))
        edits = []
        for node in ast.walk(tree):
            if not isinstance(node,ast.Constant) or not isinstance(node.value,str) or node.value not in LEGACY:
                continue
            if isinstance(parents.get(node),ast.JoinedStr):
                continue
            english = json.dumps(LEGACY[node.value],ensure_ascii=False)
            replacement = english if name in standalone else "tr("+english+")"
            start,end = offsets[node.lineno-1]+node.col_offset,offsets[node.end_lineno-1]+node.end_col_offset
            edits.append((start,end,replacement.encode("utf-8")))
        for start,end,replacement in sorted(edits,reverse=True):
            data = data[:start]+replacement+data[end:]
        text = data.decode("utf-8")
        if name not in standalone and "from .i18n import tr" not in text:
            marker = "from __future__ import annotations"
            text = text.replace(marker,marker+"\nfrom .i18n import tr",1) if marker in text else "from .i18n import tr\n"+text
        # Remaining legacy fragments are f-string parts (not AST expressions).
        for german,english in LEGACY.items():
            if german not in ("Newton","Achse","Anker","Fest","Keiner","Minimum","Maximum","Pause","Start","Reset"):
                text = text.replace(german,english)
        path.write_text(text,encoding="utf-8")


HELP_DE = {
    "SIMULATION":"Vorgaben für jede Simulation. Sie gelten ab dem nächsten Start und für alle Körper, die keine eigenen Simulationseinstellungen verwenden.",
    "SHOW_COLLIDERS":"Kollisionsformen sind die vereinfachte Geometrie, mit der Newton Kontakte berechnet: ein Quader, eine Kugel oder eine konvexe Hülle um jeden Körper. Sie erscheinen als farbige Umrisse über dem Modell und zeigen, wo die Kontaktgeometrie vom sichtbaren Modell abweicht. Diese Option legt fest, ob die Anzeige beim Öffnen eines Fensters eingeschaltet ist; der Menübefehl „Kollisionsformen anzeigen“ schaltet sie im aktuellen Fenster um. Die Anzeige ändert nie, wie Körper zusammenstoßen.",
    "COLLIDER_SHORTCUT":"Öffnet die Tastenkürzel-Einstellungen von IngeTrazo beim Befehl, der die Kollisionsanzeige umschaltet. Standardmäßig ist kein Kürzel belegt.",
    "GRAVITY":"Beschleunigung entlang der Z-Achse des Modells in m/s². −9,81 entspricht der Erdschwerkraft, 0 macht alle Körper schwerelos, positive Werte ziehen nach oben. Stärkere Schwerkraft bedeutet mehr Last für die Antriebe.",
    "GROUND":"Fügt bei Höhe Z = 0 einen unsichtbaren, unendlichen Boden ein, auf dem Körper landen. Schalte ihn aus, wenn sich Teile unterhalb von Z = 0 bewegen sollen oder das Modell eine eigene Unterlage hat.",
    "LINEAR_DAMPING":"Bremst bewegte Körper ab, ähnlich wie Luftwiderstand. Bei 1 /s verliert ein freier Körper pro Sekunde etwa zwei Drittel seiner Geschwindigkeit; 0 schaltet die Dämpfung ab. Mehr Dämpfung beruhigt Schwingungen, bremst aber auch gewollte Bewegungen, sodass Antriebe mehr Kraft brauchen.",
    "ANGULAR_DAMPING":"Wie die lineare Dämpfung, aber für Drehungen: bremst kreiselnde und taumelnde Körper ab. 0 schaltet sie ab.",
    "QUALITY":"Wie genau Gelenke und Kontakte berechnet werden. Schnell eignet sich zum Einrichten großer Mechanismen, Ausgewogen für die normale Arbeit und Präzise zum Prüfen anspruchsvoller Kontakte. Geometrie und Kabelauflösung bleiben gleich, die Bewegung kann sich zwischen den Stufen aber leicht unterscheiden.",
    "RUNTIME":"Der Python-Interpreter der Umgebung, in der MuJoCo 3.3.7 installiert ist. Newton führt darin Simulation und Kollisionsanzeige als eigenen Prozess aus. Ändere den Pfad nur, wenn diese Umgebung verschoben oder ersetzt wurde; für Änderungen am Modell ist das nie nötig.",
    "PROFILES":"Ein Profil überträgt Parameter auf einen Körper und behält dabei dessen Lage und Bezugskörper bei. Körper merken sich ihr Profil, behalten ihre Werte aber bis zum ausdrücklichen Sync. Dieser überschreibt auch lokale Änderungen. Synchronisiere einen Körper in der Sidebar oder merke hier alle zugeordneten Körper für OK vor. Built-ins sind schreibgeschützt, lassen sich aber ansehen und als Ausgangspunkt für ein eigenes Profil duplizieren.",
    "BODY":"Die Kollisionsform bestimmt, wo sich ein Körper bewegen kann. Quader und Hülle schließen Öffnungen und können einen Mechanismus blockieren; Teilkomponenten lassen die Lücken frei.",
    "MOTION":"Ein Servo hält eine Position, ein Motor eine Geschwindigkeit. Kraftlimit, Last und Kontakte bestimmen, was der Körper tatsächlich erreicht.",
    "CONNECTION":"Eine Verbindung schließt einen Mechanismus, etwa zwischen Pleuel und Schlitten, ohne die Bezugskörper zu ändern. Sie muss die Bewegung der vorhandenen Achsen zulassen; eine starre Verbindung kann den Mechanismus blockieren.",
    "FLEXIBLE":"Der Linienzug wird zu einem biegsamen Strang mit fester Länge. Ein größerer Radius macht ihn steifer und enger in Führungen; steife, fein unterteilte Stränge kosten Rechenzeit.",
    "COLLISIONS":"Nimm den Kontakt zwischen Teilen aus, die bereits ein Gelenk führt, etwa zwischen Bolzen und Lager, wenn ihre Überschneidung den Mechanismus sonst verklemmt. Das Paar kann sich dann durchdringen; die Führung muss deshalb vom Gelenk kommen. Kontakte mit anderen Körpern bleiben erhalten.",
    "OVERRIDES":"Verwende Overrides, wenn dieser Körper eine andere Umgebung braucht. Er stößt weiterhin mit Nachbarn zusammen und zieht an verbundenen Teilen; eine lokale Schwerkraft kann deshalb den ganzen Mechanismus bewegen. Schalte Overrides aus, um wieder die globalen Vorgaben zu verwenden. Ein Schwerkraftvektor aus Nullen macht diesen Körper dagegen ausdrücklich schwerelos.",
    "FIELDS":"Kombiniere Anziehung mit einer seitlichen Startgeschwindigkeit, um statt eines geraden Falls eine Umlaufbahn zu erzeugen. Nahe am Zentrum nimmt die Anziehung stark zu; ein größerer Softening-Radius verhindert dort extreme Kräfte. Die Startgeschwindigkeit wird beim Start eines frei beweglichen Körpers gesetzt.",
    "COUPLING_FREE":"Kopple Achsen, wenn ein Regler mehrere Teile bewegen soll, etwa zwei Greiferbacken. Anschläge auf beiden Seiten begrenzen die gemeinsame Bewegung.",
    "COUPLING_FOLLOWER":"Diese Achse folgt dem Regler der führenden Achse. Richtung und Übersetzung bestimmen ihre relative Bewegung; der führende Antrieb liefert die Kraft für beide.",
    "COUPLING_LEADER":"{bodies} folgen diesem Regler. Ihre zusätzliche Last und ihre Anschläge wirken auch auf die führende Achse. Wähle einen folgenden Körper aus, um seinen Weg oder seine Bewegungsrichtung zu ändern.",
    "PROFILE_OVERRIDES":"Aktivierte Overrides ersetzen beim Anwenden des Profils die globale Umgebung. Sie können damit auch die Last verbundener Teile verändern. Lass sie ausgeschaltet, wenn das Profil den Vorgaben der jeweiligen Simulation folgen soll.",
}


def generate():
    german = {en:de for de,en in LEGACY.items()}
    german.update(EXTRA_DE)
    import runpy
    help_texts = runpy.run_path(str(PACKAGE/"help_texts.py"))
    german.update({help_texts[key]:value for key,value in HELP_DE.items()})
    german.update({
        "Body & contact":"Körper & Kontakt", "No axis":"Keine Achse", "Initial target":"Startwert",
        "Built-in · read-only":"Built-in · schreibgeschützt", "Custom profile":"Eigenes Profil", "Duplicate…":"Duplizieren…",
        "Synchronize acceleration and deceleration":"Beschleunigung und Bremsverzögerung synchronisieren",
        "Sync linked bodies":"Zugeordnete Körper synchronisieren", "Sync linked bodies ({count})":"Zugeordnete Körper synchronisieren ({count})",
        "Sync queued for OK. Local values will be overwritten.":"Sync für OK vorgemerkt. Lokale Werte werden überschrieben.",
        "Linked bodies synced.":"Zugeordnete Körper synchronisiert.", "Sync":"Sync", "Unlink":"Zuordnung lösen",
        "Missing profile":"Profil fehlt", "Profile changed":"Profil geändert", "Local changes":"Lokal geändert", "In sync":"Synchron",
        "Link selection without changing values":"Auswahl zuordnen, Werte behalten",
        "Profile link queued for OK. Object values stay unchanged.":"Zuordnung für OK vorgemerkt. Objektwerte bleiben erhalten.",
        "Overwrite profile parameters; keep axis placement and reference bodies.":"Profilparameter überschreiben; Achslage und Bezugskörper beibehalten.",
        "Place an axis on each linked body before syncing this profile.":"Platziere vor dem Sync eine Achse an jedem zugeordneten Körper.",
    })
    # Keep established technical terminology, including legacy messages.
    german["Runtime"] = "Runtime"
    german["Built-in"] = "Built-in"
    german["Simulation overrides"] = "Simulation Overrides"
    for key,value in list(german.items()):
        german[key] = value.replace("Newton-Laufzeit","Newton Runtime").replace("Laufzeit auswählen","Runtime auswählen")
    english = set(german)
    for path in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="tr" and node.args and isinstance(node.args[0],ast.Constant):
                english.add(node.args[0].value)
    # Master is the canonical identity catalogue, never translated prose.
    directory = PACKAGE/"i18n"
    directory.mkdir(exist_ok=True)
    (directory/"en.json").write_text(json.dumps({s:s for s in sorted(english)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (directory/"de.json").write_text(json.dumps(dict(sorted(german.items())),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    import sys
    if "--migrate" in sys.argv:
        migrate()
    generate()
