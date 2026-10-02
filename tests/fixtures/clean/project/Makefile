.PHONY: integration

integration:
	docker compose up -d db
	go test -tags integration ./...
