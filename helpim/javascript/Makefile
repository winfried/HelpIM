BUILDDIR  = ./htdocs
SOURCEDIR = ./src

OUTFILE   = $(BUILDDIR)/helpim.base.js
DEPSFILE  = $(SOURCEDIR)/deps.js

all: clean deps build

build:
	@echo "building jsapp";
	@mkdir -p htdocs
	@../../parts/xmpptk/lib/closure-library/closure/bin/build/closurebuilder.py --root=../../parts/xmpptk/lib/closure-library/ --root=$(SOURCEDIR) --namespace="helpim" --output_mode=compiled -f '--compilation_level=ADVANCED_OPTIMIZATIONS' -f '--define=goog.DEBUG=false' --compiler_jar=../../parts/xmpptk/utils/compiler/compiler.jar > $(OUTFILE)

clean:
	@rm -f $(OUTFILE) 2> /dev/null
	@rm -f $(DEPSFILE) 2> /dev/null

deps:
	@echo "building dependencies";
	@../../parts/xmpptk/lib/closure-library/closure/bin/build/depswriter.py --root_with_prefix="$(SOURCEDIR) ../../../javascript/" > $(DEPSFILE)
