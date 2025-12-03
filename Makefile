default:
	@echo "For downloading data and speeches dataset compiling:"
	@echo "Set URL_LIST in .env to the path of csv file which contains Bundestag xml urls."
	@echo "Set DF_CSV in .env to the path where resulted data frame will be stored as csv file"
	@echo "Then run: make speeches"

speeches:
	@uv run python -m prp.tools speeches


#################### DOCKER #######################
BUILDX ?= DOCKER_BUILDKIT=1

docker_build:
	$(BUILDX) docker build --tag=$$GAR_IMAGE:dev .

docker_run:
	docker run --rm -it -e PORT=8000 -p 8000:8000 --env-file .env $$GAR_IMAGE:dev

docker_build_prod:
	docker build \
  --platform linux/amd64 \
  -t $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/taxifare/$$GAR_IMAGE:prod .

docker_push_prod:
	docker push $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/taxifare/$$GAR_IMAGE:prod
################################################
