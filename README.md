docker build --target dev --tag profile_service:dev -f dockerfiles/Dockerfile.profile_service .
docker run --env-file ./.env -p 5200:5000 --mount "type=bind,source=$(pwd),target=/profile_service" -it profile_service:dev


docker run --env-file ./.env -p 5200:5000 --mount "type=bind,source=$(pwd)/profile_service,target=/app/profile_service" -it profile_service:dev







docker build --target prod --tag profile_service:prod -f dockerfiles/Dockerfile.profile_service .

docker run --publish 8000:5000 -it --env-file .env profile_service:prod
docker run --publish 8000:5000 -it --env-file .env profile_service:dev