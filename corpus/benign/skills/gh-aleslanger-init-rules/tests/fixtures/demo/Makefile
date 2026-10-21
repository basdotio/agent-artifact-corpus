.PHONY: test lint typecheck gen
test:
	pytest -q
lint:
	ruff check .
typecheck:
	mypy app
gen:
	python -m grpc_tools.protoc -I proto --python_out=app/gen proto/orders.proto
