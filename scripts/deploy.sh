curl -O https://raw.githubusercontent.com/nbqduong/e-sim/main/scripts/install-docker-ubuntu.sh
curl -O https://raw.githubusercontent.com/nbqduong/e-sim/main/docker-compose.prod.yml
mkdir -p deploy/nginx
curl -o deploy/nginx/backend.conf https://raw.githubusercontent.com/nbqduong/e-sim/main/deploy/nginx/backend.conf
sh install-docker-ubuntu.sh
echo $1 | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
docker compose -f docker-compose.prod.yml up
