#!/usr/bin/env bash
# Independent re-verification of Gallagher's n = 6 Lean certificate, from a clean machine.
#
#   tools/audit_gallagher_certificate.sh [workdir]
#
# Clones algal/krenn-gu-6x3-certificate at the pinned commit, installs the pinned Lean
# toolchain through elan, fetches the Mathlib cache, and runs the author's own release gate
# (50 artifact checksums, `lake build KrennGuCertificate`, `#print axioms`). The expected
# axiom closure is [propext, Classical.choice, Lean.ofReduceBool, Lean.trustCompiler,
# Quot.sound]: the last two come from native_decide and mean the Lean compiler is trusted.
# Reference machine (author): 8 cores, 128 GiB, 22 min 18 s after the cache fetch.
set -uo pipefail
WORK="${1:-$PWD/gallagher-audit}"; mkdir -p "$WORK"; cd "$WORK"
COMMIT=c04696e515e0c02be140353fb52ea60c62e827b1
echo "== start $(date -u +%FT%TZ)"
[ -d kg6 ] || git clone -q https://github.com/algal/krenn-gu-6x3-certificate.git kg6
cd kg6 && git checkout -q "$COMMIT"
if [ ! -x "$HOME/.elan/bin/elan" ]; then
  curl -sSf https://elan.lean-lang.org/elan-init.sh -o /tmp/elan-init.sh && sh /tmp/elan-init.sh -y --default-toolchain none
fi
export PATH="$HOME/.elan/bin:$PATH"
elan toolchain install "$(cat lean-toolchain)" 2>&1 | tail -1
lean --version
echo "== lake exe cache get  $(date -u +%FT%TZ)"
lake exe cache get 2>&1 | tail -3
echo "== verify_release.sh   $(date -u +%FT%TZ)"
scripts/verify_release.sh 2>&1 | tail -40
echo "== exit=$? end $(date -u +%FT%TZ)"
