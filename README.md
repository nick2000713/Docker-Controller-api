# Docker-Controller
Ein Web‑basiertes Tool zur Verwaltung und Steuerung von Docker‑Containern. Die Anwendung bietet eine übersichtliche Benutzer‑Oberfläche, mit der Container (sowohl einzeln als auch in Gruppen) gestartet, gestoppt und überwacht werden können. Zusätzlich verfügt die App über eine REST‑API, die eine Integration in Systeme wie Home Assistant ermöglicht.

Features
Web‑UI:

Verwaltung von Containern und Gruppen
Starten/Stoppen einzelner Container und ganzer Gruppen
Bearbeitung von Containern und Gruppen inklusive Bestellfunktionen (Reihenfolge und Verzögerung)
Benutzer‑Verwaltung (Erstellung, Bearbeitung und Löschung von Benutzern)
API-Key‑Verwaltung in der Benutzer‑Bearbeitung (API-Key kann direkt neu generiert werden)
REST‑API:

Endpunkt zum Steuern einzelner Container (/api/control)
Endpunkt zum Abfragen des Container‑Status (/api/status)
Endpunkt zum Steuern ganzer Gruppen (/api/control_group)
Endpunkt zum Abfragen des Gruppen‑Status (/api/group_status)
Home Assistant Integration:

Über REST‑Commands und REST‑Sensoren lässt sich die App in Home Assistant einbinden, sodass Container und Gruppen direkt über dein HA‑Dashboard gesteuert werden können.
Mit Template Switches kannst du den aktuellen Status der Container (z. B. „running“ oder „stopped“) direkt als Schalter anzeigen.
Installation
Voraussetzungen
Docker (oder ein Docker‑kompatibler Host, z. B. Unraid)
Python 3.10 oder höher (wenn lokal entwickelt werden soll)
Abhängigkeiten (siehe requirements.txt)
Docker‑Image bauen
Klone das Repository:
bash
Kopieren
git clone https://github.com/dein-benutzername/docker-controller.git
cd docker-controller
Baue das Docker‑Image:
bash
Kopieren
docker build -t dein_dockerhub_username/docker-controller:latest .
Erstelle einen persistenten Ordner auf deinem Host (z. B. /mnt/user/appdata/docker-controller), der die Datenbank und Icons enthält.
Container starten
Starte den Container, indem du den persistenten Ordner an den Pfad /app/data mountest und den Docker‑Socket durchreichst:

bash
Kopieren
docker run -d -p 5000:5000 \
  -v /mnt/user/appdata/docker-controller:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e ADMIN_USERNAME=dein_admin_username \
  -e ADMIN_PASSWORD=dein_admin_passwort \
  dein_dockerhub_username/docker-controller:latest
Konfiguration und Nutzung
Web‑UI
Rufe die Web‑Oberfläche unter http://<DOCKER_CONTROLLER_IP>:5000 auf.
Als Admin kannst du über die Navigation Container, Gruppen und Benutzer verwalten.
Beim Bearbeiten eines Benutzers kannst du mittels Checkboxen festlegen, auf welche Container der Benutzer Zugriff hat.
In der Admin‑Bearbeitung kannst du den API-Key des Benutzers anzeigen und bei Bedarf neu generieren.
API-Endpunkte
Die wichtigsten Endpunkte sind:

Einzelner Container steuern:
URL: /api/control
Methode: POST
Payload (JSON):

json
Kopieren
{
  "username": "dein_benutzer",
  "api_key": "dein_api_key",
  "container_id": 1,
  "action": "start" // oder "stop"
}
Status eines Containers abfragen:
URL: /api/status
Methode: GET
Parameter (Query-String):
username, api_key, container_id

Gruppe steuern:
URL: /api/control_group
Methode: POST
Payload (JSON):

json
Kopieren
{
  "username": "dein_benutzer",
  "api_key": "dein_api_key",
  "group_id": 2,
  "action": "start" // oder "stop"
}
Gruppenstatus abfragen:
URL: /api/group_status
Methode: GET
Parameter (Query-String):
username, api_key, group_id

Home Assistant Integration
REST Commands
In deiner configuration.yaml (oder in einer separaten YAML-Datei) fügst du beispielsweise folgende Einträge hinzu:

yaml
Kopieren
rest_command:
  start_container:
    url: "http://<DOCKER_CONTROLLER_IP>:5000/api/control"
    method: POST
    headers:
      Content-Type: application/json
    payload: >
      {
        "username": "YOUR_USERNAME",
        "api_key": "YOUR_API_KEY",
        "container_id": CONTAINER_ID,
        "action": "start"
      }

  stop_container:
    url: "http://<DOCKER_CONTROLLER_IP>:5000/api/control"
    method: POST
    headers:
      Content-Type: application/json
    payload: >
      {
        "username": "YOUR_USERNAME",
        "api_key": "YOUR_API_KEY",
        "container_id": CONTAINER_ID,
        "action": "stop"
      }

  start_group:
    url: "http://<DOCKER_CONTROLLER_IP>:5000/api/control_group"
    method: POST
    headers:
      Content-Type: application/json
    payload: >
      {
        "username": "YOUR_USERNAME",
        "api_key": "YOUR_API_KEY",
        "group_id": GROUP_ID,
        "action": "start"
      }

  stop_group:
    url: "http://<DOCKER_CONTROLLER_IP>:5000/api/control_group"
    method: POST
    headers:
      Content-Type: application/json
    payload: >
      {
        "username": "YOUR_USERNAME",
        "api_key": "YOUR_API_KEY",
        "group_id": GROUP_ID,
        "action": "stop"
      }
Ersetze die Platzhalter:

<DOCKER_CONTROLLER_IP> durch die IP deines Docker‑Controllers (z. B. 192.168.100.12).
YOUR_USERNAME und YOUR_API_KEY durch den Benutzernamen und API-Key, die in der App vergeben wurden.
CONTAINER_ID und GROUP_ID mit den entsprechenden numerischen IDs.
REST Sensoren
Für die Statusanzeige richtest du REST‑Sensoren ein:

yaml
Kopieren
sensor:
  - platform: rest
    resource: "http://<DOCKER_CONTROLLER_IP>:5000/api/status?container_id=CONTAINER_ID&username=YOUR_USERNAME&api_key=YOUR_API_KEY"
    name: "Crafty Status"
    value_template: "{{ value_json.status }}"
    headers:
      Content-Type: application/json
    scan_interval: 60

  - platform: rest
    resource: "http://<DOCKER_CONTROLLER_IP>:5000/api/group_status?group_id=GROUP_ID&username=YOUR_USERNAME&api_key=YOUR_API_KEY"
    name: "Group Status"
    value_template: "{{ value_json.status }}"
    headers:
      Content-Type: application/json
    scan_interval: 60
Template Switch
Um einen Schalter mit integrierter Statusanzeige zu erstellen, kannst du einen Template Switch verwenden:

yaml
Kopieren
switch:
  - platform: template
    switches:
      crafty_container:
        friendly_name: "Crafty Container"
        value_template: "{{ is_state('sensor.crafty_status', 'running') }}"
        turn_on:
          service: rest_command.start_container
        turn_off:
          service: rest_command.stop_container
Sicherheitshinweis
Internes Netzwerk:
Wenn Home Assistant und der Docker‑Controller im selben internen Netzwerk liegen, kannst du HTTP verwenden.
Externe Exposition:
Falls du den Dienst ins Internet stellen möchtest, solltest du HTTPS über einen Reverse Proxy einrichten und zusätzliche Authentifizierungsmechanismen verwenden.
Contributing
Beiträge sind willkommen! Bitte erstelle Pull Requests oder Issues, wenn du Verbesserungen oder Fehlerbehebungen vorschlagen möchtest.

Lizenz
Dieses Projekt ist unter der MIT License lizenziert.

