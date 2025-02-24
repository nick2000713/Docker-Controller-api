# Docker Controller

Ein webbasierter Dienst zur Verwaltung und Steuerung von Docker-Containern. Mit dieser Anwendung kannst du Container (einzeln oder in Gruppen) starten, stoppen und überwachen – sowohl über die Web-Oberfläche als auch über eine REST-API, die sich ideal in Systeme wie Home Assistant integrieren lässt.

## Features

- **Web-UI:**
  - Verwaltung von Containern und Gruppen
  - Starten/Stoppen einzelner Container und ganzer Gruppen
  - Bearbeitung von Containern und Gruppen inklusive Reihenfolge und Verzögerung
  - Benutzerverwaltung (Erstellung, Bearbeitung und Löschung von Benutzern)
  - API-Key-Verwaltung in der Benutzerbearbeitung – API-Key kann direkt neu generiert werden
  - Auswahl der Container per Checkbox (sowohl bei Gruppen als auch in der Benutzerverwaltung)

- **REST-API:**
  - **/api/control** – Steuert einen einzelnen Container (start/stop)
  - **/api/status** – Gibt den Status eines einzelnen Containers zurück
  - **/api/control_group** – Steuert alle Container einer Gruppe (start/stop)
  - **/api/group_status** – Gibt den Status einer Gruppe zurück

- **Home Assistant Integration:**
  - RESTful Commands und REST-Sensoren für die Container- und Gruppensteuerung
  - Template Switches, die den aktuellen Status anzeigen und per Knopfdruck Container steuern
  - Beispielkonfigurationen für REST-Commands, Sensoren und Template Switches

## Installation

### Voraussetzungen

- Docker oder ein Docker-kompatibler Host (z.B. Unraid)
- Python 3.10 oder höher (falls lokal entwickelt wird)
- Abhängigkeiten gemäß `requirements.txt`

### Docker-Image bauen

1. Repository klonen:
   ```bash
   git clone https://github.com/dein-benutzername/docker-controller.git
   cd docker-controller

