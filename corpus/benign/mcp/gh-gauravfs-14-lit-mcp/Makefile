.PHONY: release
release:
	@kind=$${KIND:-patch}; \
	uv version --bump $$kind; \
	v=$$(uv version | awk '{print $$NF}'); \
	sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$$v\"/g" server.json; \
	git add pyproject.toml server.json; \
	git commit -m "chore: release v$$v"; \
	git tag "v$$v"; \
	git push origin HEAD; \
	git push origin "v$$v"; \
	echo "✅ Released v$$v"
