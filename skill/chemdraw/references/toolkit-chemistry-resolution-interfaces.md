# Chemistry Resolution And Molecular Changes

## When To Load

Load for chemical-name resolution, CAS lookup, formula/MW validation, reagent abbreviations, structural modification, MCS diffs, or aligned names.

## Preferred Entry Points

- Resolve a molecule: MCP `resolve_name`.
- Modify a validated molecule: MCP `modify_molecule`.
- Draw grounded SMILES: MCP `draw_molecule`.
- Search collections: MCP `search_compound`.
- Python CAS resolution: `resolve.cas_resolver` high-level resolvers.
- Python naming support: curated reagent database and name decomposition modules.

## Inputs And Outputs

Accept a user-provided trusted SMILES or a resolver result. Verify canonical identity, formula, molecular weight, and source before drawing. Molecular modification must include an MCS-based before/after diff.

## Failure Modes

Names may be ambiguous, network resolvers may disagree, and abbreviations may be context dependent. Return alternatives and provenance rather than selecting silently. Reject direct string edits that bypass molecular graph validation.

## Supporting APIs

- `rdkit_utils`: canonicalization, formula/MW, molecule validation, and graph helpers.
- `naming.reagent_database`: known labels and display names.
- `naming.name_decomposer`: R-group decomposition and aligned naming support.
- `resolve.cas_resolver`: optional network-backed CAS/name lookups.

## Do Not Use Directly

Do not construct chemistry from raw atom/bond JSON, invent SMILES from memory, or treat a generated systematic name as stronger evidence than the validated molecular graph and source record.
