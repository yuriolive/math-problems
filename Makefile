# Repository-wide gates.
#
# Every rule in README.md's working-rules list was previously enforced by whoever
# remembered to run the right script. That is the failure mode the rules are about, so
# `make check` runs all of them and `make check-fast` runs the subset that needs no
# toolchain beyond Python.
#
# Per-problem targets live in problems/<collection>/<id>/Makefile.

.PHONY: check check-fast check-docs check-intake check-sorry test-python test-rust \
        audit-lean problems clean help

PROBLEM_DIRS := $(wildcard problems/*/*/Makefile)
PROBLEMS := $(patsubst %/Makefile,%,$(PROBLEM_DIRS))

help:
	@echo "make check       every gate, including Rust and Lean (slow: compiles Mathlib)"
	@echo "make check-fast  docs, intake and the sorry scan (seconds, Python only)"
	@echo "make test        Python and Rust tests for every problem"
	@echo "make problems    list the problem directories found"

# The gate to run before a commit. Ordered cheapest-first so it fails early.
check: check-fast test-python test-rust audit-lean

check-fast: check-docs check-intake check-sorry

# Rule 10: markdown that renders on GitHub, not just locally.
check-docs:
	uv run python tools/check_docs.py

# Rules 12 and 13: no problem carries an unanswered intake question.
check-intake:
	uv run python tools/intake/scaffold.py --check

# Rule 8, the fast half: no `sorry` or `admit` token in any Lean source. No toolchain
# needed, so this runs in CI where compiling Mathlib would not.
check-sorry:
	uv run python tools/lean/audit.py --skip-build

# Rule 8, the full half: every audited theorem on the three standard axioms only.
# Compiles against Mathlib.
audit-lean:
	uv run python tools/lean/audit.py

test: test-python test-rust

test-python:
	@for d in $(PROBLEMS); do \
		echo "== python tests: $$d"; \
		$(MAKE) -C $$d test-python || exit 1; \
	done

test-rust:
	@for d in $(PROBLEMS); do \
		echo "== rust tests: $$d"; \
		$(MAKE) -C $$d test-rust || exit 1; \
	done

problems:
	@for d in $(PROBLEMS); do echo $$d; done

clean:
	@for d in $(PROBLEMS); do $(MAKE) -C $$d clean || true; done
