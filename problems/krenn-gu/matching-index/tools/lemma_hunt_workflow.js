// Lemma hunt: propose, adversarially test, and rank candidate general-n lemmas for Krenn-Gu.
//
// A Claude Code Workflow script (not Node). Run it with the Workflow tool, passing args:
//   {repo, problem_dir, checker, scratch, gallagher_notes, papers}
// where checker is verifier/target/release/ghzcheck, gallagher_notes is a checkout of
// algal/krenn-gu-6x3-certificate at c04696e (its notes/ directory), and papers points at
// plain-text dumps of arXiv:2407.00303 and arXiv:2304.06407. Six proposer lenses, three
// skeptics each (mathematical, computational, literature), one judge. Every proposer must
// ship an exact-arithmetic test; every claim a skeptic makes must come from a command it
// ran. Launched once on 10 September 2026 (see ROADMAP.md, direction H) and stopped before
// completion for a credit reset; resume by running it again.
export const meta = {
  name: 'krenn-gu-lemma-hunt',
  description: 'Propose, adversarially test, and rank candidate general-n lemmas for the Krenn-Gu conjecture',
  phases: [
    { title: 'Propose', detail: 'six independent lenses, each with an exact computational test' },
    { title: 'Refute', detail: 'three skeptics per proposal: mathematical, computational, literature' },
    { title: 'Judge', detail: 'rank survivors and write the roadmap section' },
  ],
}

const A = args

const CONTEXT = `
You are working on the Krenn-Gu conjecture as a research mathematician with strong computational habits.

## Setting (read ${A.problem_dir}/README.md and ROADMAP.md first; they are short and current)
An edge-coloured edge-weighted multigraph on n vertices: every edge e = uv carries a colour at each half-edge
(c(e_u), c(e_v) in {0,..,d-1}) and a weight w(e) in C. A vertex colouring iota: V -> {0..d-1} filters the graph to edges
with c(e_u)=iota(u), c(e_v)=iota(v); the amplitude A(iota) is the sum over perfect matchings of the filtered graph of the
product of edge weights. GHZ graph: A(iota) = 1 for every feasible constant colouring, 0 for every non-constant colouring.
Dimension = number of feasible constant colourings. Conjecture (Krenn-Gu): n > 4 implies dimension <= 2.
Equivalent tensor form: with x_v in C^d and A_{uv} = x_u^T W_{uv} x_v, Haf(A(x)) = sum_i prod_v x_{v,i}.
Reductions already recorded in the README: (R1) one system per n: all candidates are sub-supports of the fully loaded K_n
with at most one edge per (pair, ordered colour pair), zero weight = absent edge. (R2) WLOG d = 3.
Gauge: w(e) -> lambda_{u,c(e_u)} lambda_{v,c(e_v)} w(e) preserves the zero pattern (scaling lemma).

## What is known
- Bogdanov 2017: positive real weights => impossible for n > 4 (three monochromatic matchings of distinct colours force a
  mixed matching). Any counterexample needs destructive interference.
- Chandran-Gajjala-Illickan, MFCS 2024 (text at ${A.papers}): Theorem 9: vertex connectivity <= 2 => mu <= 2.
  Theorem 10: if the skeleton has vertex connectivity <= 3 and n > 4 there is a graph on <= n-2 vertices with mu at least as
  large. Theorem 11: max degree 3 => conjecture holds. Theorem 12: min degree 3 => mu <= 3. Their reduction stops at
  4-connected skeletons.
- Mantey 2023: n = 4 gives mu(K4) = 3 (Groebner basis), unique configuration.
- Gallagher, 24 July 2026: Lean 4 certificate that no (6,3) GHZ graph exists over C (support sieve + exact Laurent /
  ideal-membership no-goods + 8 symmetry orbits of target-matching triples + CaDiCaL LRAT refutations replayed in Lean).
  His method notes are in ${A.gallagher_notes} (read 2026-07-23-unrestricted-certificate.md and 2026-07-23-mixed-weight-program.md).
  By R2 this settles every d at n = 6. So: THE CONJECTURE IS NOW EQUIVALENT TO AN INDUCTIVE STEP FROM A KNOWN BASE CASE.
- Dimension-2 GHZ graphs exist for every even n (e.g. the alternating 2n-cycle), so any candidate reduction can be
  sanity-tested for dimension preservation on them, and any identity claimed for all coloured weighted multigraphs can be
  tested on random instances.

## Tools you have
- Exact checker: ${A.checker} <instance.json> [--dump-colourings] [--max-matchings N]. Instance JSON schema:
  {"n":6,"colours":3,"root_of_unity":1,"edges":[{"u":0,"v":1,"cu":0,"cv":0,"w":[[1,1]]}, ...]} where w is a list of
  [numerator, denominator] coefficients over the basis 1, z, z^2, ... with z = exp(2 pi i / root_of_unity); omit w for 1.
  Output is JSON; with --dump-colourings every feasible colouring appears with exact matching count and reduced weight.
  Exit 0 = counterexample, 1 = evaluated and not one, 2 = unknown/refused input.
  Corpus: ${A.problem_dir}/instances/*.json. Reference implementation you can import ideas from:
  ${A.problem_dir}/tests/test_differential.py (Fractions arithmetic in Q(zeta_m), Hafnian by recursion).
- Python 3 with fractions; run with /home/user/proofstack/.venv/bin/python. Do NOT use floating point for any claim.
- Write all files under ${A.scratch}/<your-lens-name>/ (mkdir -p). Do NOT modify anything under ${A.repo}.
- A Lean build is using the CPUs; keep any single test run under ~3 minutes and n <= 8.

## Rules of this repository that apply to you
Every number you report must come from a command you ran. A test that fails is a valid result: report it as failed. Do not
soften a refutation. Distinguish theorem from heuristic in every statement you make. Do not invent citations.
`

const PROPOSAL = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    title: { type: 'string' },
    lemma_statement: { type: 'string', description: 'Precise mathematical statement, with quantifiers, of the lemma proposed' },
    implication: { type: 'string', description: 'Exactly what follows if the lemma holds: full conjecture via induction from n=6, or a weaker general-n theorem (say which), or nothing general' },
    proof_sketch: { type: 'string' },
    known_obstacles: { type: 'string', description: 'Where the sketch is incomplete or where you expect it to fail' },
    testable_consequence: { type: 'string', description: 'A checkable identity or property that must hold if the lemma is true, and what instances test it' },
    test_script_path: { type: 'string' },
    test_command: { type: 'string' },
    test_output_summary: { type: 'string' },
    test_passed: { type: 'boolean' },
    instances_tested: { type: 'integer' },
    confidence_lemma_true: { type: 'number', description: '0..1' },
    confidence_provable_in_weeks: { type: 'number', description: '0..1' },
  },
  required: ['lens', 'title', 'lemma_statement', 'implication', 'proof_sketch', 'known_obstacles', 'testable_consequence',
             'test_script_path', 'test_command', 'test_output_summary', 'test_passed', 'instances_tested',
             'confidence_lemma_true', 'confidence_provable_in_weeks'],
}

const VERDICT = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    refuted: { type: 'boolean', description: 'true if the lemma as stated is false, or the argument has a gap you could not close, or the test does not actually test the claim' },
    severity: { type: 'string', enum: ['fatal', 'gap', 'minor', 'none'] },
    reason: { type: 'string' },
    evidence: { type: 'string', description: 'the counterexample, the failing command and its output, or the citation' },
    salvage: { type: 'string', description: 'if refuted, the strongest weaker statement that survives, if any' },
  },
  required: ['lens', 'refuted', 'severity', 'reason', 'evidence', 'salvage'],
}

const JUDGEMENT = {
  type: 'object',
  properties: {
    ranking: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          status: { type: 'string', enum: ['survives', 'refuted', 'salvaged'] },
          score: { type: 'number' },
          one_line_verdict: { type: 'string' },
          next_step: { type: 'string' },
        },
        required: ['title', 'status', 'score', 'one_line_verdict', 'next_step'],
      },
    },
    recommendation: { type: 'string' },
    roadmap_markdown: { type: 'string', description: 'A ready-to-paste markdown section for ROADMAP.md, no em dashes, citing only verified facts' },
  },
  required: ['ranking', 'recommendation', 'roadmap_markdown'],
}

const LENSES = [
  { key: 'contraction', brief: `Vertex-pair contraction. Fix two vertices u, v with colours a, b. The residual amplitude on V minus {u,v} is
(W_uv)_{ab} * Haf(A restricted) + sum over w != w' of (W_uw)_{a,iota(w)} (W_vw')_{b,iota(w')} Haf(A restricted minus w, w'),
which is (W_uv)_{ab} Haf(A) plus a first derivative of Haf in the direction of a rank-2-ish matrix c. Find an EXACT
reduction from an n-vertex GHZ graph of dimension 3 to an (n-2)-vertex object of the same kind (possibly over C[eps]/eps^2,
possibly with a marked vertex, possibly a g-GHZ graph with nonzero rather than unit monochromatic weights). State the lemma
that would make the CGI induction go through for 4-connected skeletons. Test the amplitude identity exactly on random instances.` },
  { key: 'colour-cuts', brief: `Colour-specific cuts. A 4-connected skeleton can still have monochromatic subgraphs G_i (edges with both
half-edges colour i) that have small vertex cuts; each G_i only needs a perfect matching. Generalise the cut-based reduction
of Chandran-Gajjala-Illickan Theorem 10 to cuts in the coloured structure (a cut in G_i, or in the graph of bichromatic
edges, or a cut separating colours), and state the lemma precisely. Read their Section 3 proof first. Test any identity
you claim about amplitudes across a cut on random instances.` },
  { key: 'hamming', brief: `Hamming hierarchy. Colourings at Hamming distance 1 from constant give, for each vertex u and colours a != b,
sum_w (W_uw)_{ba} * P_a(V minus {u,w}) = 0 where P_a(U) is the colour-a monochromatic matching sum on the induced
subgraph on U; distance 2 gives quadratic relations; the constant colouring gives P_a(V) = 1. Organise the whole system by
distance from constant and look for a general-n contradiction or a reduction to n-2 by deleting a matched pair. Derive the
exact identities, test them on random instances, and state the strongest lemma you can defend.` },
  { key: 'gf2', brief: `Parity and Pfaffians. For integer weights, A(iota) mod 2 equals the number of perfect matchings of the odd-weight
support mod 2, and over GF(2) a Hafnian is a Pfaffian whose square is a determinant. So an integer-weight GHZ graph forces a
coloured support S in which every constant colouring has an odd matching count and every other colouring an even one,
equivalently the 3^n induced GF(2) adjacency matrices A^iota are nonsingular exactly for constant iota. Formulate this
precisely, decide it computationally at n = 6 (SAT with XOR constraints; /home/user/proofstack/.venv/bin/python has
pysat and pycryptosat), and attempt a general-n impossibility by GF(2) rank arguments. Say exactly which Formal
Conjectures entries (integer, trinary) a general-n parity theorem would settle. Note: a parity support at n = 6 exists
implies the method alone cannot prove the integer conjecture; report that honestly if it happens.` },
  { key: 'tensor', brief: `Tensor obstructions. The GHZ tensor sum_i prod_v x_{v,i} has rank 3 and every flattening has rank <= 3.
Haf(A(x)) with A_{uv} = x_u^T W_{uv} x_v is a Hafnian of bilinear forms in which W_{uv} is shared by every matching through uv.
Find an invariant of Hafnian-of-bilinear-forms tensors (a flattening rank, a Koszul flattening, a substitution-method bound,
a symmetry/stabiliser argument) that the GHZ tensor violates for n >= 8 with d = 3, or prove that no such invariant exists at
the level you tried. Compute the invariant exactly on random instances and on the d = 2 GHZ graphs to make sure it is
consistent with what exists.` },
  { key: 'fourier', brief: `Character sums. Apply the transversal Fourier transform over Z_3 at every vertex: the GHZ tensor becomes the
uniform superposition over zero-sum strings, and the amplitude equations become Haf(Fhat W (k)) = 3 * [sum k_v = 0 mod 3]
where Fhat W_{uv}(k_u,k_v) is the 2D DFT of the 3x3 weight matrix. Summing over all colourings gives scalar identities such
as Haf( (sum_{ab} (W_uv)_{ab})_{uv} ) = 3. Enumerate the family of scalar and low-order identities this produces, look for
an averaging or counting argument valid for all n (e.g. combine with Bogdanov-type positivity after averaging over the
torus gauge or over colour permutations), and state the lemma. Test every identity you write down exactly on random
instances.` },
]

phase('Propose')
const proposals = await pipeline(
  LENSES,
  L => agent(`${CONTEXT}

## Your lens: ${L.key}
${L.brief}

## Deliverable
Work as follows. (1) Read the README, ROADMAP, the relevant paper sections, and Gallagher's two notes. (2) Derive your
lemma on paper, carefully, with every quantifier. (3) Identify a consequence that MUST hold if the lemma is true and that
can be tested with exact arithmetic on concrete instances: random coloured weighted multigraphs at n = 4, 6, 8 with
rational or root-of-unity weights, the corpus instances, and the dimension-2 GHZ graphs. (4) Write the test as a Python
script under ${A.scratch}/${L.key}/, run it, and record the command and the output. If the test fails, your lemma or your
derivation is wrong: say so, fix what can be fixed, and report the final state honestly. (5) Return the structured
proposal. Your final text is data, not a message to a human. Be specific: a lemma nobody can check is worth nothing here.`,
    { label: `propose:${L.key}`, phase: 'Propose', schema: PROPOSAL, effort: 'xhigh' }),
  (p, L) => {
    if (!p) return null
    log(`proposal ${L.key}: ${p.title} (test ${p.test_passed ? 'passed' : 'FAILED'} on ${p.instances_tested} instances)`)
    return p
  },
  async (p, L) => {
    if (!p) return null
    const skeptics = [
      { lens: 'mathematical', brief: `You are a skeptical referee. Check every step of the proof sketch. Find the gap, the missing quantifier,
the case the argument silently assumes away (dense 4-connected skeletons, multi-edges, bichromatic edges, zero weights,
cancellation). Construct an explicit counterexample to the lemma statement if you can, and verify it with the checker.
Default to refuted=true if you cannot close the argument yourself.` },
      { lens: 'computational', brief: `You are a skeptical experimentalist. Read the test script at ${p.test_script_path}. Does it actually test
the lemma as stated, or something weaker? Run it (${p.test_command}). Then construct adversarial instances the author did
not try: dense multi-edge instances at n = 6 and 8 with root-of-unity weights (root_of_unity 3, 4, 6), instances with
cancelling non-monochromatic colourings (see ${A.problem_dir}/instances/k4-d2-interference.json), the dimension-2 GHZ
graphs on 6 and 8 vertices, zero-weight edges, and degenerate supports. Every claim you make must come from a command you
ran with exact arithmetic. If a single instance violates the claimed consequence, the lemma as stated is refuted.` },
      { lens: 'literature', brief: `You are a skeptical literature referee. Compare the proposal against: Chandran-Gajjala-Illickan MFCS 2024
(full text at ${A.papers}, especially the proof of Theorem 10 and Section 3.6 'Limitations of our reduction'),
Chandran-Gajjala Quantum 2024 (local sparsification), Bogdanov's lemma, and Gallagher's notes in ${A.gallagher_notes}. Is
the lemma already known? Already proved false or shown to have a limitation there? Is the 'new' identity a restatement of
something in those texts? Is the implication claimed (e.g. 'with the n = 6 base case this proves the conjecture') actually
valid, given that the CGI reduction produces a graph on <= n-2 vertices with mu at least as large and that the base case is
n = 6? Quote the passages you rely on. Refute if the proposal's novelty or implication claim does not hold.` },
    ]
    const verdicts = await parallel(skeptics.map(s => () => agent(`${CONTEXT}

## The proposal under review (lens: ${p.lens})
Title: ${p.title}
Lemma: ${p.lemma_statement}
Claimed implication: ${p.implication}
Proof sketch: ${p.proof_sketch}
Author's own stated obstacles: ${p.known_obstacles}
Testable consequence: ${p.testable_consequence}
Test: ${p.test_command} -> ${p.test_output_summary} (author reports passed=${p.test_passed} on ${p.instances_tested} instances)

## Your role: ${s.lens} skeptic
${s.brief}
Write any files under ${A.scratch}/${L.key}/skeptic-${s.lens}/. Return the structured verdict; your final text is data.`,
      { label: `refute:${L.key}:${s.lens}`, phase: 'Refute', schema: VERDICT, effort: 'high' })))
    const vs = verdicts.filter(Boolean)
    const refutations = vs.filter(v => v.refuted)
    log(`${L.key}: ${refutations.length}/${vs.length} skeptics refute (${vs.map(v => v.lens + '=' + v.severity).join(', ')})`)
    return { proposal: p, verdicts: vs }
  },
)

const results = proposals.filter(Boolean)
log(`${results.length}/${LENSES.length} proposals completed the pipeline`)

phase('Judge')
const judgement = await agent(`${CONTEXT}

## Your role: judge
Below are ${results.length} proposals for a general-n lemma on the Krenn-Gu conjecture, each with three skeptics' verdicts.
Rank them. A proposal survives only if no skeptic found a fatal flaw AND its computational test actually tests the stated
lemma AND the implication claimed is valid. Treat a 'gap' as survivable only if the salvage is stated precisely. Score 0..10
on (a) probability the (possibly salvaged) lemma is true, (b) probability it is provable within weeks with this
repository's tools (exact checker, SAT with certificates, Lean), (c) value if proved (full conjecture > general-n theorem for
integer weights > infinite graph class > finite case). Then write the roadmap section: which one or two to pursue, the
exact statement to pursue, the first computational milestone for each, and what was refuted and why (so it is not
re-entered). No em dashes anywhere in your text. Cite only what is in the material below or in the repository.

${JSON.stringify(results, null, 2)}`,
  { label: 'judge', phase: 'Judge', schema: JUDGEMENT, effort: 'xhigh' })

return { judgement, results }