# How to direct Traefik traffic through different traefik managed docker-compose files
This project shows how you can manage multiple traefik managed projects through one master traefik controller. This allows for containers routed by the same prefix (such as "/api") to be accessed through paths unique to their managing traefik container.


## 1. Create parent traefik container

This container will host traefik and process all traffic directed through (in this case) http requests (port 80). 

```yml
services:
  traefik-parent:
    container_name: traefik-parent
    image: traefik:latest
    ports:
      - "80:80"    # Expose HTTP port
      - "8080:8080"  # Traefik Dashboard (optional)
    command:
      - "--api.insecure=true"  # Expose dashboard
      - "--providers.docker=true"  # Enable Docker provider
      - "--providers.docker.exposedbydefault=false"  # Don't expose all services by default
      - "--entryPoints.web.address=:80"  # Define HTTP entrypoint
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # Traefik needs access to Docker socket
    networks:
      - proxy

networks:
  proxy:
    external: true

```
## 2. In a new docker compose file, create child traefik container
This container will tell traefik how it should route requests. This is done by defining a prefix to access the containers being routed by this. 

For example: 
- You may define the prefix as `this-traefik-container`, meaning all requests with that prefix will route through this container.
- Then, if you were managing trafic to an api container with the prefix `/api`, you could access it through `localhost/this-traefik-container/api`. 

This container also removes its prefix for subsequent routing for simplicities sake. It isnt necessary, but it allows you to route to subsequent containers without including /{{child-traefik-prefix}}. This simplifies the docker compose file but also simplifies some API frameworks.

For example, in FastAPI: without stripping the {{child-traefik-prefix}} before routing to the API's container, you would have to define your routes in FastAPI including this:
```python
# Without stripping
@app.get("/{{child-traefik-prefix}}/api")

# With stripping
@app.get("/api")
```
```yml
services:
  {{child-traefik-container-name}}:
    container_name: {{child-traefik-container-name}}
    image: traefik:latest
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entryPoints.web.address=:80"
    labels:
      - "traefik.enable=true"
      
      - "traefik.http.routers.{{child-traefik-container-name}}.rule=PathPrefix(`/{{child-traefik-prefix}}`)"
      - "traefik.http.routers.{{child-traefik-container-name}}.entrypoints=web"
      - "traefik.http.services.{{child-traefik-container-name}}.loadbalancer.server.port=80" 

      # Apply the child traefiks middleware to this container
      - "traefik.http.routers.{{child-traefik-container-name}}.middlewares={{child-traefik-middleware-name}}"

      # Define the middleware for this child traefik container. 
      # This needs a unique name (cannot be repeated by other child traefik containers)
      - "traefik.http.middlewares.{{child-traefik-middleware-name}}.stripprefix.prefixes=/{{child-traefik-prefix}}"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - proxy


networks: 
  proxy:
    external: true
```

## 3. In the same docker-compose file under services, create a container to be managed by the child

```yml
services:
  ...
  {{container-name}}:
    container_name: {{container-name}}
    image: {{container-image}}
    labels:
      - "traefik.enable=true"
      
      # This prefix only has to be unique among containers routed by this traefik container
      - "traefik.http.routers.{{container-name}}.rule=PathPrefix(`/{{container-prefix}}`)"
      - "traefik.http.routers.{{container-name}}.entrypoints=web"
      - "traefik.http.services.{{container-name}}.loadbalancer.server.port={{port to access within the container, e.g. 5000}}"

    networks:
      - proxy

networks: 
  proxy:
    external: true
```

## 3. Create the docker containers
- ### 1. Firstly, build the parent container
  ```bash
  cd traefik-parent
  docker compose up --build -d
  ```
- ### 2. Next, build a child container
  ```bash
  cd traefik-child-1
  docker compose up --build -d
  ```
- ### 3. Finally, access the container
  [http://localhost/traefik-1/api](http://localhost/traefik-1/api)

If all the steps have been completed correctly, you should be able to access the container through `localhost/{{child-trafik-prefix}}/{{container-prefix}}`