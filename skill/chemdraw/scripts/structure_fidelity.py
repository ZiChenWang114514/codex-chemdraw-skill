"""Validate and preserve molecular semantics in generated CDXML."""

from __future__ import annotations

from pathlib import Path
from xml.dom import minidom


class StructureFidelityError(RuntimeError):
    """Generated CDXML does not preserve the requested molecular structure."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.public_message = message


def _elements(parent, name: str):
    return [
        child
        for child in parent.childNodes
        if child.nodeType == child.ELEMENT_NODE and child.tagName == name
    ]


def _first_fragment(document):
    fragments = document.getElementsByTagName("fragment")
    if not fragments:
        raise StructureFidelityError(
            "structure_fidelity_mismatch", "Generated CDXML contains no molecule fragment"
        )
    return fragments[0]


def _integer_attribute(node, name: str, default: int) -> int:
    raw = node.getAttribute(name)
    try:
        return int(raw) if raw else default
    except ValueError as exc:
        raise StructureFidelityError(
            "structure_fidelity_mismatch",
            f"Generated CDXML has an invalid {name} attribute",
        ) from exc


def _bond_order(node) -> float:
    raw = node.getAttribute("Order") or "1"
    aliases = {"1.5": 1.5, "Aromatic": 1.5}
    try:
        return aliases.get(raw, float(raw))
    except ValueError as exc:
        raise StructureFidelityError(
            "structure_fidelity_mismatch", "Generated CDXML has an invalid bond order"
        ) from exc


def _point(node) -> tuple[float, float]:
    values = node.getAttribute("p").split()
    if len(values) != 2:
        raise StructureFidelityError(
            "structure_fidelity_mismatch", "Generated CDXML atom has no valid position"
        )
    try:
        return float(values[0]), float(values[1])
    except ValueError as exc:
        raise StructureFidelityError(
            "structure_fidelity_mismatch", "Generated CDXML atom has no valid position"
        ) from exc


def _side(a: tuple[float, float], b: tuple[float, float], point: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])


def _validate_double_bond_geometry(molecule, nodes) -> int:
    from rdkit import Chem

    positions = [_point(node) for node in nodes]
    count = 0
    for bond in molecule.GetBonds():
        stereo = bond.GetStereo()
        if stereo not in (Chem.BondStereo.STEREOE, Chem.BondStereo.STEREOZ):
            continue
        stereo_atoms = list(bond.GetStereoAtoms())
        if len(stereo_atoms) != 2:
            raise StructureFidelityError(
                "stereochemistry_not_preserved",
                "Specified double-bond geometry could not be verified",
            )
        begin = bond.GetBeginAtomIdx()
        end = bond.GetEndAtomIdx()
        left = _side(positions[begin], positions[end], positions[stereo_atoms[0]])
        right = _side(positions[begin], positions[end], positions[stereo_atoms[1]])
        if abs(left) < 1e-8 or abs(right) < 1e-8:
            raise StructureFidelityError(
                "stereochemistry_not_preserved",
                "Specified double-bond geometry is not represented by the CDXML layout",
            )
        represented = (
            Chem.BondStereo.STEREOZ if left * right > 0 else Chem.BondStereo.STEREOE
        )
        if represented != stereo:
            raise StructureFidelityError(
                "stereochemistry_not_preserved",
                "Generated CDXML reverses specified double-bond geometry",
            )
        count += 1
    return count


def _prepare_molecule(smiles: str):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise StructureFidelityError("invalid_smiles", "SMILES could not be parsed")
    AllChem.Compute2DCoords(molecule)
    Chem.WedgeMolBonds(molecule, molecule.GetConformer())
    return molecule


def _validate_graph(molecule, nodes, bonds) -> dict[int, object]:
    from rdkit import Chem

    if len(nodes) != molecule.GetNumAtoms() or len(bonds) != molecule.GetNumBonds():
        raise StructureFidelityError(
            "structure_fidelity_mismatch",
            "Generated CDXML atom or bond count differs from the requested molecule",
        )

    node_ids: dict[str, int] = {}
    for index, (atom, node) in enumerate(zip(molecule.GetAtoms(), nodes)):
        node_id = node.getAttribute("id")
        if not node_id or node_id in node_ids:
            raise StructureFidelityError(
                "structure_fidelity_mismatch", "Generated CDXML atom identifiers are invalid"
            )
        node_ids[node_id] = index
        values = (
            _integer_attribute(node, "Element", 6),
            _integer_attribute(node, "Isotope", 0),
            _integer_attribute(node, "Charge", 0),
        )
        expected = (atom.GetAtomicNum(), atom.GetIsotope(), atom.GetFormalCharge())
        if values != expected:
            raise StructureFidelityError(
                "structure_fidelity_mismatch",
                "Generated CDXML changed an element, isotope, or formal charge",
            )

    by_pair = {
        frozenset((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())): bond
        for bond in molecule.GetBonds()
    }
    kekule = Chem.Mol(molecule)
    try:
        Chem.Kekulize(kekule, clearAromaticFlags=True)
    except Exception as exc:
        raise StructureFidelityError(
            "structure_fidelity_mismatch",
            "Requested molecule could not be converted to a deterministic bond representation",
        ) from exc
    expected_orders = {
        bond.GetIdx(): float(bond.GetBondTypeAsDouble())
        for bond in kekule.GetBonds()
    }
    mapped: dict[int, object] = {}
    for node in bonds:
        try:
            begin = node_ids[node.getAttribute("B")]
            end = node_ids[node.getAttribute("E")]
        except KeyError as exc:
            raise StructureFidelityError(
                "structure_fidelity_mismatch", "Generated CDXML bond references an unknown atom"
            ) from exc
        bond = by_pair.get(frozenset((begin, end)))
        if bond is None or abs(_bond_order(node) - expected_orders[bond.GetIdx()]) > 0.01:
            raise StructureFidelityError(
                "structure_fidelity_mismatch",
                "Generated CDXML changed molecular connectivity or bond order",
            )
        mapped[bond.GetIdx()] = node
    return mapped


def _expected_wedge_displays(molecule, nodes, mapped_bonds) -> dict[int, str]:
    from rdkit import Chem

    node_ids = [node.getAttribute("id") for node in nodes]
    expected: dict[int, str] = {}
    for bond in molecule.GetBonds():
        direction = bond.GetBondDir()
        if direction not in (Chem.BondDir.BEGINWEDGE, Chem.BondDir.BEGINDASH):
            continue
        node = mapped_bonds[bond.GetIdx()]
        begin_id = node_ids[bond.GetBeginAtomIdx()]
        at_begin = node.getAttribute("B") == begin_id
        if direction == Chem.BondDir.BEGINWEDGE:
            display = "WedgeBegin" if at_begin else "WedgeEnd"
        else:
            display = "WedgedHashBegin" if at_begin else "WedgedHashEnd"
        expected[bond.GetIdx()] = display
    return expected


def _validate_wedges(mapped_bonds, expected: dict[int, str]) -> int:
    for bond_index, node in mapped_bonds.items():
        actual = node.getAttribute("Display")
        desired = expected.get(bond_index, "")
        if actual != desired:
            raise StructureFidelityError(
                "stereochemistry_not_preserved",
                "Generated CDXML does not encode the requested wedge-bond direction",
            )
    return len(expected)


def repair_and_validate_drawn_cdxml(
    smiles: str,
    path: str | Path,
    *,
    repair_stereo: bool = True,
) -> dict[str, object]:
    """Repair missing wedge bonds and verify CDXML against the source SMILES."""
    from rdkit import Chem

    output = Path(path)
    molecule = _prepare_molecule(smiles)
    try:
        document = minidom.parse(str(output))
    except Exception as exc:
        raise StructureFidelityError(
            "structure_fidelity_mismatch", "Generated CDXML could not be parsed"
        ) from exc
    fragment = _first_fragment(document)
    nodes = _elements(fragment, "n")
    bonds = _elements(fragment, "b")
    mapped_bonds = _validate_graph(molecule, nodes, bonds)

    expected_displays = _expected_wedge_displays(molecule, nodes, mapped_bonds)
    if repair_stereo:
        for bond_index, display in expected_displays.items():
            mapped_bonds[bond_index].setAttribute("Display", display)
        output.write_bytes(document.toxml(encoding="UTF-8"))
    wedge_count = _validate_wedges(mapped_bonds, expected_displays)

    stereo_double_bonds = _validate_double_bond_geometry(molecule, nodes)
    specified_centers = sum(
        atom.GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED
        for atom in molecule.GetAtoms()
    )
    return {
        "status": "preserved",
        "canonical_isomeric_smiles": Chem.MolToSmiles(molecule, isomericSmiles=True),
        "specified_chiral_centers": specified_centers,
        "stereo_double_bonds": stereo_double_bonds,
        "isotope_atoms": sum(bool(atom.GetIsotope()) for atom in molecule.GetAtoms()),
        "charged_atoms": sum(bool(atom.GetFormalCharge()) for atom in molecule.GetAtoms()),
        "wedge_bonds": wedge_count,
    }
