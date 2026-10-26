# C08 — Source and operating-setting interpretation

## Status
Completed for the existing-evidence interpretation, with source-generation provenance and causal mechanism isolation explicitly limited. No new tracking was run.

## Reproduce
Run `python scripts/analyze_revision_settings.py` using the production environment. The script verifies all 30 primary evaluation-file completion checksums and the retained representative trajectory hashes. It writes representative vectors/objectives/all signed margins, sampled trajectories, constraint violation counts and a hashed input manifest.

## Source characterization
The archived source SHA-256 is `0084449f47507d7db5cf3af781ec2d899e0ff63e5ebb83ea806d14ea80444734`. ASTRA units and reference-relative z/pz/t conventions follow the installed upstream beamphysics/interfaces/astra.py; diagnostic columns follow astra/parsers.py. For moments, exclude the reference and six status -3 probes, retaining 9,993 status -1 records. This differs intentionally from the unchanged 9,999 transmission denominator. Weights use absolute macrocharge. The file's total charge magnitude is 1 nC.

RMS sizes are 0.482927/0.483139 mm, emission-time RMS is 2.551397 ps, and Gaussian-equivalent FWHM is 6.008082 ps. Ordinary-particle radii reach 0.999486 mm. This reports empirical support and moments, not an inferred generator recipe or functional shape. Initial normalized emittance from the centered x/px and y/py covariance determinants divided by electron rest energy is 0.427339/0.427489 micrometre-radian. Reconstructed kinetic energy is approximately 0.600002 eV with negligible stored spread. Cathode material, temperature and original distribution-generation settings are not independently documented; no new thermal model is asserted.

## Geometry and mechanisms
The metadata lists every cavity origin, solenoid and quadrupole position. Quadrupoles at 8.70046 and 12.50092 m lie between accelerating structures, each of length 0.065 m. Consequently a downstream-of-complete-linac interpretation would be incorrect. The saved Xemit/Yemit trajectories show growth of asymmetry beyond initially similar moments, including 3.2985/3.3001 micrometre-radian near 5.2 m and 2.9298/4.1003 near 12.4 m for the horizontal extreme. This supports a transport association, not attribution to an isolated mechanism. Linear focusing alone does not imply emittance growth.

Zemit sigma_energy is projected full-bunch RMS, including correlated chirp. Its covariance column divided by sigma_energy gives the linear z-energy correlation; the horizontal extreme has approximately -0.968 at the exit. No slice or dechirped objective is substituted. If a causal claim is later needed, separately plan fixed-input quadrupole and phase counterfactuals with the same source/resolution and full exit validation; these would be isolated diagnostic runs, not replacements for the primary data. They are not required for the present descriptive claims and have not been launched.

## Selected points and constraints
The six roles map to six distinct full parameter vectors in c08_representatives.csv. All eight signed margins are retained, positive inside the production profile and normalized by each absolute threshold. No primary observation exactly matches the configured nominal vector (absolute tolerance 1e-10 in stored physical coordinates), so no nominal-lattice improvement is quantified. The analysis does not assert absence of nominal runs elsewhere.

Transmission is exactly one in every primary observation; maximum mean energy is 201.41 MeV. These two inequalities are never violated in the observed sample. Every other inequality has violations, enumerated in c08_constraint_activity.csv; counts overlap and must not be summed as distinct failed observations. Neither empirical inactivity nor absence of violations proves domain-wide redundancy.
