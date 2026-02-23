.PHONY: search.push-image

search.push-image:
	docker build -t gide-search .
	docker image tag gide-search ghcr.io/bioimage-archive/gide-search:0.1.0
	docker image push ghcr.io/bioimage-archive/gide-search:0.1.0
