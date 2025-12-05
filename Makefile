default:
	@echo There are no default targets

#################### DOCKER #######################
BUILDX ?= DOCKER_BUILDKIT=1
TAG := $(shell date +%Y%m%d-%H%M%S)
ifeq ($(BUILD_FORCE),1)
BUILD_FORCE = --no-cache --progress=plain
else
BUILD_FORCE =
endif

docker-build:
	$(BUILDX) docker --debug build $(BUILD_FORCE) --tag=$$GAR_IMAGE:dev .

docker-run:
	bin/docker-run.sh

docker-build-prod:
	docker build \
  --platform linux/amd64 \
  -t $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG) .

docker-push-prod:
	docker push $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG)

deploy: docker-build-prod docker-push-prod
	cd terraform && terraform apply -var="rag_image_tag=$(TAG)" -auto-approve
################################################
