#!/usr/bin/env bash
# Stop and remove all running containers
docker-compose down web || true
# Remove the omaha-server_web image
docker rmi omaha-server_web || true
# Build and start the containers
docker-compose up -d --build --remove-orphans

sleep 3

docker-compose exec -T web python omaha-server/manage.py migrate
docker-compose exec -T web python omaha-server/createadmin.py
 