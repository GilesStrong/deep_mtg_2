make_route_id:
	@uv run python -c "import nanoid; print(nanoid.generate())" 
