"""A three way merge of text by lines, with git style conflict markers."""

from difflib import SequenceMatcher

YOURS_MARKER = "<<<<<<< yours"
SEPARATOR = "======="
SERVER_MARKER = ">>>>>>> server"


def _sync_regions(base: list[str], mine: list[str], theirs: list[str]):
    """
    The stretches of base that both sides kept, as (base start, base end,
    mine start, theirs start). Ends with an empty one after the last line.
    """
    mine_blocks = SequenceMatcher(None, base, mine, autojunk=False)
    theirs_blocks = SequenceMatcher(None, base, theirs, autojunk=False)
    mine_matches = mine_blocks.get_matching_blocks()
    theirs_matches = theirs_blocks.get_matching_blocks()

    i = j = 0
    while i < len(mine_matches) and j < len(theirs_matches):
        mine_base, mine_start, mine_size = mine_matches[i]
        theirs_base, theirs_start, theirs_size = theirs_matches[j]
        start = max(mine_base, theirs_base)
        end = min(mine_base + mine_size, theirs_base + theirs_size)
        if start < end:
            yield (
                start,
                end,
                mine_start + start - mine_base,
                theirs_start + start - theirs_base,
            )
        if mine_base + mine_size < theirs_base + theirs_size:
            i += 1
        else:
            j += 1
    yield len(base), len(base), len(mine), len(theirs)


def merge3(base: str, mine: str, theirs: str) -> tuple[str, bool]:
    """
    Merges the changes from base to mine with the ones from base to theirs.
    Returns the merged text and whether it has conflicts: places both sides
    changed differently, kept as both versions between conflict markers.
    """
    base_lines, mine_lines, theirs_lines = (
        text.splitlines() for text in (base, mine, theirs)
    )
    merged: list[str] = []
    has_conflicts = False
    base_at = mine_at = theirs_at = 0

    for start, end, mine_start, theirs_start in _sync_regions(
        base_lines, mine_lines, theirs_lines
    ):
        base_chunk = base_lines[base_at:start]
        mine_chunk = mine_lines[mine_at:mine_start]
        theirs_chunk = theirs_lines[theirs_at:theirs_start]

        if mine_chunk == theirs_chunk or theirs_chunk == base_chunk:
            merged += mine_chunk
        elif mine_chunk == base_chunk:
            merged += theirs_chunk
        else:
            has_conflicts = True
            merged += [YOURS_MARKER, *mine_chunk, SEPARATOR, *theirs_chunk]
            merged.append(SERVER_MARKER)

        merged += base_lines[start:end]
        base_at = end
        mine_at = mine_start + end - start
        theirs_at = theirs_start + end - start

    return "".join(f"{line}\n" for line in merged), has_conflicts


def has_markers(text: str) -> bool:
    """Whether conflicts of merge3 are left in the text"""
    return any(line in (YOURS_MARKER, SERVER_MARKER) for line in text.splitlines())
