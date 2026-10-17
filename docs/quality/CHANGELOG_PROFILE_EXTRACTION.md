# Candidate profile extraction update

- Added candidate-name extraction from explicit name labels, with a conservative opening-lines fallback.
- The React profile uses the extracted name when available, falling back to the filename only when no name is found.
- Certification extraction now keeps only concise credential-like entries and filters common non-certification details such as salary expectations, joining availability, travel preferences, practical-experience prose, and references.
- Added regression tests for candidate name extraction and certification filtering.

Verification: `python -m unittest discover -s tests -v` — 22 tests passed.

Limitations: Name extraction is heuristic and should remain editable by the candidate. Certification extraction cannot guarantee every credential is genuine; extracted values should be reviewed before use.
