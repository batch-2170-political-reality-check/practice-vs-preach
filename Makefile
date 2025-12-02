default:
	@echo "For downloading data and speeches dataset compiling:"
	@echo "Set URL_LIST in .env to the path of csv file which contains Bundestag xml urls." 
	@echo "Set DF_CSV in .env to the path where resulted data frame will be stored as csv file"
	@echo "Then run: make speeches"

speeches:
	@uv run python -m prp.tools speeches
