# Docker Controller

Docker Controller is a web-based tool for managing and controlling Docker containers. The application offers a user-friendly interface to start, stop, and monitor individual containers or groups of containers. It also provides a REST API, making it easy to integrate with systems like Home Assistant. 
NOTE: THIS PROJECT WAS ENTIRELY BUILT WITH CHATGPT. Please refrain from submitting pull requests or similar contributions—simply share the code with ChatGPT. I have zero programming skills, and it's nothing short of a miracle that this shit works.

## Features

- **Web UI**
  - Container & Group Control:
    Start or stop individual containers or entire groups with a single click.
  - Advanced Management:
    Edit containers and groups, set custom startup orders and delays to ensure dependencies (e.g. databases) are started before dependent services.
  - User Management:
    Create, edit, and delete users. Assign specific containers to each user so that only authorized users can control certain containers.
  - API Key Management:
    Generate and update API keys directly in the user management interface. This key is required for API calls and is used to verify that the user is allowed to control a given container.
  - Intuitive Selection:
    Choose containers via checkboxes (both for group creation and user management) for a clearer, more efficient interface.

- **REST API**
  - `/api/control` – Control a single container (start/stop)
  - `/api/status` – Retrieve the status of a single container
  - `/api/control_group` – Control all containers in a group (start/stop)
  - `/api/group_status` – Retrieve the status of a group (e.g. number of running containers vs. total)
  - ***Access Control:***
    All API endpoints validate the provided username and API key and ensure that a user can only control containers they are assigned to (unless the user is an admin).
    Home Assistant Integration

- **Home Assistant Integration**
  - RESTful commands and sensors for container and group control
  - Template switches that display the current state and trigger actions
  - Example YAML configuration provided for integration

## Installation

Running the Container
Start the container with the persistent data directory mounted to /app/data and pass the Docker socket:

    docker run -d -p 5000:5000 \
      -v /mnt/user/appdata/docker-controller:/app/data \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -e ADMIN_USERNAME=your_admin_username \
      -e ADMIN_PASSWORD=your_admin_password \
      anysale/docker-controller-api:latest

## Usage

Access the UI:
Open your browser and navigate to http://<DOCKER_CONTROLLER_IP>:5000.

Admin Interface:
As an administrator, you can manage containers, groups, and users. When editing a user, you can select which containers the user has access to using checkboxes. You can also generate or update the user’s API key directly in the user edit screen.

### REST API Endpoints

**Container & Group IDs:**
- The API uses numerical IDs for containers and groups. To find these IDs, open the edit page for a container or group – the URL will include the ID (e.g., 
/container/edit/3 means the container ID is 3).

**Control a Single Container**
- URL: /api/control
- Method: POST
- Payload (JSON):
  
      {
        "username": "your_username",
        "api_key": "your_api_key",
        "container_id": 1,
        "action": "start"  // or "stop"
      }

**Get Status of a Single Container**
- URL: /api/status
- Method: GET
- Query Parameters: username, api_key, container_id

**Control a Group of Containers**
- URL: /api/control_group
- Method: POST
- Payload (JSON):
  
      {
        "username": "your_username",
        "api_key": "your_api_key",
        "group_id": 2,
        "action": "start"  // or "stop"
      }

**Get Status of a Group**
- URL: /api/group_status
- Method: GET
- uery Parameters: username, api_key, group_id

## Home Assistant Integration
You can integrate Docker Controller into Home Assistant using RESTful commands and sensors.

REST Commands
Add the following entries to your Home Assistant configuration.yaml (or a separate YAML file):
CONTAINER_ID and GROUP_ID: Numeric IDs of the container or group. You find These when you EDIT the Container or Group in the URL.

    rest_command:
    start_<YOUR_NAME_OF_CONTAINER>:
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
    
      stop_<YOUR_NAME_OF_CONTAINER>:
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
    
      start_<YOUR_NAME_OF_CONTAINER>:
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
    
      stop_<YOUR_NAME_OF_GROUP>:
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



**REST Sensors**
Define REST sensors to monitor the status:

    sensor:
      - platform: rest
        resource: "http://<DOCKER_CONTROLLER_IP>:5000/api/status?container_id=CONTAINER_ID&username=YOUR_USERNAME&api_key=YOUR_API_KEY"
        name: "YOUR_NAME_OF_STATUS"
        value_template: "{{ value_json.status }}"
        headers:
          Content-Type: application/json
        scan_interval: 60
    
      - platform: rest
        resource: "http://<DOCKER_CONTROLLER_IP>:5000/api/group_status?group_id=GROUP_ID&username=YOUR_USERNAME&api_key=YOUR_API_KEY"
        name: "YOUR_NAME_OF_GROUP_STATUS"
        value_template: "{{ value_json.status }}"
        headers:
          Content-Type: application/json
        scan_interval: 60
**Template Switch**
Create a template switch to combine the status and control functionality:

    # Template Switch that uses the override (if set within the last 10 seconds) or the actual sensor value
    switch:
      - platform: template
        switches:
          my_container:
            friendly_name: "My Container"
            value_template: >
              {%- set override = states('input_select.my_container_override') -%}
              {%- if override != "none" -%}
                {{ override }}
              {%- else -%}
                {%- if states('sensor.my_container_status') | lower | trim == 'running' -%}
                  on
                {%- else -%}
                  off
                {%- endif -%}
              {%- endif -%}
            turn_on:
              - service: input_select.select_option
                data:
                  entity_id: input_select.my_container_override
                  option: "on"
              - service: rest_command.start_my_container
            turn_off:
              - service: input_select.select_option
                data:
                  entity_id: input_select.my_container_override
                  option: "off"
              - service: rest_command.stop_my_container

**Complete Example with State Override**

    # Input Select for the override state
    input_select:
      my_container_override:
        name: "My Container Command Override"
        options:
          - "none"
          - "on"
          - "off"
        initial: "none"
    
    # REST Commands for controlling the container
    rest_command:
      start_my_container:
        url: "http://YOUR_IP:PORT/api/control"
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
      stop_my_container:
        url: "http://YOUR_IP:PORT/api/control"
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
    
    # REST Sensor to check the container's status (updates every 10 seconds)
    sensor:
      - platform: rest
        resource: "http://YOUR_IP:PORT/api/status?container_id=CONTAINER_ID&username=YOUR_USERNAME&api_key=YOUR_API_KEY"
        name: "my_container_status"
        value_template: "{{ value_json.status }}"
        headers:
          Content-Type: application/json
        scan_interval: 10
    
    # Template Switch that uses the override (if set within the last 10 seconds) or the actual sensor value
    switch:
      - platform: template
        switches:
          my_container:
            friendly_name: "My Container"
            value_template: >
              {%- set override = states('input_select.my_container_override') -%}
              {%- if override != "none" -%}
                {{ override }}
              {%- else -%}
                {%- if states('sensor.my_container_status') | lower | trim == 'running' -%}
                  on
                {%- else -%}
                  off
                {%- endif -%}
              {%- endif -%}
            turn_on:
              - service: input_select.select_option
                data:
                  entity_id: input_select.my_container_override
                  option: "on"
              - service: rest_command.start_my_container
            turn_off:
              - service: input_select.select_option
                data:
                  entity_id: input_select.my_container_override
                  option: "off"
              - service: rest_command.stop_my_container
    
    # Automation to reset the override 10 seconds after a manual change and update the sensor
    automation:
      - alias: "Reset My Container Command Override"
        trigger:
          - platform: state
            entity_id: input_select.my_container_override
            to: "on"
          - platform: state
            entity_id: input_select.my_container_override
            to: "off"
        action:
          - delay: "00:00:10"
          - service: input_select.select_option
            data:
              entity_id: input_select.my_container_override
              option: "none"
          - service: homeassistant.update_entity
            target:
              entity_id: sensor.my_container_status

**Lovelace Dashboard**
Open your Home Assistant dashboard.
Click on the three dots in the top-right corner and select "Edit Dashboard".
Add an Entities Card and include your sensors (e.g., sensor.YOUR_NAME_OF_STATUS) and template switches (e.g., switch.YOUR_NAME).
