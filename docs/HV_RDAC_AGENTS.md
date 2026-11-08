# HV-RDAC project guidance for Codex

Read `HV_RDAC_Codex_Brief.md` before proposing architecture or modifying simulations.
Treat the brief's numbers as initial hypotheses, not validated hardware specifications.
Prioritize mathematical consistency, reproducible ngspice experiments, and honest feasibility assessment.
Work incrementally: low-bit low-voltage model -> 12-bit model -> transformer parasitics -> vendor devices -> KiCad.
Never claim simulated results without running the simulation; if dependencies are absent, give exact commands and state the limitation.
Keep engineering derivations and assumptions in markdown with consistent SI units.
Do not implement a kilovolt hardware build at this stage.
