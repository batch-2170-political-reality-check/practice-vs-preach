default:
	@echo "For downloading data and speeches dataset compiling:"
	@echo "Set URL_LIST in .env to the path of csv file which contains Bundestag xml urls."
	@echo "Set DF_CSV in .env to the path where resulted data frame will be stored as csv file"
	@echo "Then run: make speeches"

speeches:
	@uv run python -m practicepreach.tools speeches


#################### DOCKER #######################
BUILDX ?= DOCKER_BUILDKIT=1
TAG := $(shell date +%Y%m%d-%H%M%S)

docker-build:
	$(BUILDX) docker build --tag=$$GAR_IMAGE:dev .

docker-run:
	@./docker-run.sh
	#docker run --rm -it -e PORT=8000 -p 8000:8000 --env-file .env $$GAR_IMAGE:dev

docker-build-prod:
	docker build \
  --platform linux/amd64 \
  -t $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG) .

docker-push-prod:
	docker push $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG)

docker-deploy: docke_buil_prod docker-push-prod
	cd terraform && terraform apply -var="rag_image_tag=$(TAG)" -auto-approve
################################################
