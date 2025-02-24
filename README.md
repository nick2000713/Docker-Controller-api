# Docker Controller

Docker Controller is a web-based tool for managing and controlling Docker containers. The application offers a user-friendly interface to start, stop, and monitor individual containers or groups of containers. It also provides a REST API, making it easy to integrate with systems like Home Assistant.

## Features

- **Web UI**
  - Manage individual containers and container groups
  - Start/Stop individual containers and entire groups
  - Edit containers and groups, including setting order and delays for startup
  - User management: create, edit, and delete users
  - API key management integrated in the user editing screen (users can have their API key generated/updated)
  - Container selection via checkboxes (for both group creation and user management)

- **REST API**
  - `/api/control` – Control a single container (start/stop)
  - `/api/status` – Retrieve the status of a single container
  - `/api/control_group` – Control all containers in a group (start/stop)
  - `/api/group_status` – Retrieve the status of a group (e.g., running/total)

- **Home Assistant Integration**
  - RESTful commands and sensors for container and group control
  - Template switches that display the current state and trigger actions
  - Example YAML configuration provided for integration

## Installation

Running the Container
Start the container with the persistent data directory mounted to /app/data and pass the Docker socket:

    ```bash
    docker run -d -p 5000:5000 \
      -v /mnt/user/appdata/docker-controller:/app/data \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -e ADMIN_USERNAME=your_admin_username \
      -e ADMIN_PASSWORD=your_admin_password \
      your_dockerhub_username/docker-controller:latest

### Docker-Image bauen

1. Repository klonen:
   ```bash
   git clone https://github.com/dein-benutzername/docker-controller.git
   cd docker-controller

2. Build the Docker Image:
    ```bash
    docker build -t your_dockerhub_username/docker-controller:latest .
Create a Persistent Data Directory: Create a folder on your host (e.g., /mnt/user/appdata/docker-controller) to store the database and icons.


##Usage

Access the UI:
Open your browser and navigate to http://<DOCKER_CONTROLLER_IP>:5000.

Admin Interface:
As an administrator, you can manage containers, groups, and users. When editing a user, you can select which containers the user has access to using checkboxes. You can also generate or update the user’s API key directly in the user edit screen.

REST API Endpoints
Control a Single Container
URL: /api/control
Method: POST
Payload (JSON):
json
Kopieren
{
  "username": "your_username",
  "api_key": "your_api_key",
  "container_id": 1,
  "action": "start"  // or "stop"
}
Get Status of a Single Container
URL: /api/status
Method: GET
Query Parameters: username, api_key, container_id
Control a Group of Containers
URL: /api/control_group
Method: POST
Payload (JSON):
json
Kopieren
{
  "username": "your_username",
  "api_key": "your_api_key",
  "group_id": 2,
  "action": "start"  // or "stop"
}
Get Status of a Group
URL: /api/group_status
Method: GET
Query Parameters: username, api_key, group_id
Home Assistant Integration
You can integrate Docker Controller into Home Assistant using RESTful commands and sensors.

REST Commands
Add the following entries to your Home Assistant configuration.yaml (or a separate YAML file):

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
Replace the placeholders:

<DOCKER_CONTROLLER_IP>: IP address of your Docker Controller (e.g., 192.168.100.12).
YOUR_USERNAME and YOUR_API_KEY: Credentials for your user.
CONTAINER_ID and GROUP_ID: Numeric IDs of the container or group.
REST Sensors
Define REST sensors to monitor the status:

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
Create a template switch to combine the status and control functionality:

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
Lovelace Dashboard
Open your Home Assistant dashboard.
Click on the three dots in the top-right corner and select "Edit Dashboard".
Add an Entities Card and include your sensors (e.g., sensor.crafty_status) and template switches (e.g., switch.crafty_container).
Save your changes.
