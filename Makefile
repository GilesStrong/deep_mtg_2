make_route_id:
	@uv run python -c "import nanoid; print(nanoid.generate())" 

be_tests:
	@cd app && uv run python manage.py test -v 2

fe_tests:
	@cd frontend && bun run test --run
	