.PHONY: clean
clean:
	rm -rf .pygit/objects/*
	find . -name "*.copy" -type f -delete