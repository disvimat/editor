"""Document tree operations: editing, navigation and undo."""

import copy
import random

from disvimat.core.document import Character, Document, Matrix, Sign, Structure


def fraction() -> Structure:
    return Structure("fraction", [[], []])


def test_insert_characters_and_signs() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(Sign("plus"))
    assert len(document.root) == 2
    assert document.cursor_index() == 2


def test_inserting_a_structure_enters_its_first_slot() -> None:
    document = Document()
    document.insert(fraction())
    assert document.cursor_path() == [(0, 0)]
    assert document.cursor_index() == 0
    document.insert(Character("2"))
    structure = document.root[0]
    assert isinstance(structure, Structure)
    assert structure.slots[0] == [Character("2")]


def test_exit_leaves_the_cursor_after_the_structure() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(fraction())
    left = document.exit()
    assert isinstance(left, Structure)
    assert document.cursor_path() == []
    assert document.cursor_index() == 2


def test_enter_and_left_and_right() -> None:
    document = Document()
    document.insert(fraction())
    document.insert(Character("2"))
    document.exit()
    crossed = document.left()
    assert isinstance(crossed, Structure)
    structure = document.enter()
    assert isinstance(structure, Structure)
    assert document.right() == Character("2")
    assert document.right() is None  # end of the slot


def test_next_slot_and_exit_from_the_last_one() -> None:
    document = Document()
    document.insert(fraction())
    assert document.next_slot() == 1
    assert document.cursor_path() == [(0, 1)]
    assert document.next_slot() is None  # last slot: it exits
    assert document.cursor_path() == []
    assert document.cursor_index() == 1


def test_backspace_removes_whole_structures() -> None:
    document = Document()
    document.insert(fraction())
    document.exit()
    removed = document.backspace()
    assert isinstance(removed, Structure)
    assert document.is_empty()


def test_undo_restores_tree_and_cursor() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(fraction())
    document.insert(Character("2"))
    document.exit()
    document.backspace()
    assert len(document.root) == 1
    assert document.undo()
    assert len(document.root) == 2
    assert document.cursor_index() == 2  # as it was before deleting
    assert document.redo()
    assert len(document.root) == 1


def test_undo_without_history() -> None:
    document = Document()
    assert not document.undo()
    assert not document.redo()


def test_load_replaces_the_content_and_is_undoable() -> None:
    document = Document()
    document.insert(Character("1"))
    document.load([Character("9"), Sign("plus")])
    assert len(document.root) == 2
    assert document.cursor_index() == 2
    assert document.undo()
    assert document.root == [Character("1")]


# --- line revisions (caches keyed on line content) -------------------------


def test_editing_one_line_leaves_the_other_revisions_alone() -> None:
    """The point of revisions: untouched lines must look untouched."""
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    document.new_line()
    document.insert(Character("3"))
    before = document.revisions()

    document.line_up()  # move to the middle line and edit only that one
    document.insert(Character("9"))
    after = document.revisions()

    assert after[1] != before[1]
    assert [after[0], after[2]] == [before[0], before[2]]


def test_navigation_does_not_change_any_revision() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(fraction())
    document.insert(Character("2"))
    before = document.revisions()
    document.left()
    document.right()
    document.exit()
    document.to_line_start()
    document.to_line_end()
    assert document.revisions() == before


def test_editing_inside_a_structure_touches_the_line_holding_it() -> None:
    document = Document()
    document.insert(fraction())  # cursor descends into the first slot
    before = document.revisions()
    document.insert(Character("7"))  # mutates a nested list, not the line
    assert document.revisions() != before


def test_deleting_touches_the_line() -> None:
    document = Document()
    document.insert(Character("1"))
    before = document.revisions()
    document.backspace()
    assert document.revisions() != before


def test_a_deletion_that_does_nothing_creates_no_revision() -> None:
    """A wasted re-render is the cost of a revision handed out for nothing."""
    document = Document()
    document.insert(Character("1"))
    unchanged = document.revisions()
    assert document.delete() is None  # cursor at the end, nothing to delete
    assert document.revisions() == unchanged
    document.to_line_start()
    assert document.backspace() is None  # at the start, nothing to the left
    assert document.revisions() == unchanged


def test_a_new_line_renumbers_both_halves() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(Character("2"))
    document.to_line_start()
    before = document.revisions()
    document.new_line()
    after = document.revisions()
    assert len(after) == 2
    assert after[0] != before[0]
    assert after[1] not in before


def test_merging_lines_drops_the_revision_of_the_line_that_went() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    assert len(document.revisions()) == 2
    document.to_line_start()
    document.merge_with_previous_line()
    revisions = document.revisions()
    assert len(revisions) == 1
    assert len(document.lines) == 1


def test_merging_with_the_next_line_keeps_revisions_aligned() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    document.line_up()
    document.to_line_end()
    document.merge_with_next_line()
    assert len(document.revisions()) == len(document.lines) == 1


def test_undo_never_revives_an_old_revision() -> None:
    """A cache keyed on revisions must not match restored content to a
    rendering built from different content that once sat at that index."""
    document = Document()
    document.insert(Character("1"))
    seen = set(document.revisions())
    document.insert(Character("2"))
    seen.update(document.revisions())
    document.undo()
    assert not seen & set(document.revisions())
    seen.update(document.revisions())
    document.redo()
    assert not seen & set(document.revisions())


def test_loading_lines_renumbers_everything() -> None:
    document = Document()
    before = set(document.revisions())
    document.load_lines([[Character("1")], [Character("2")]])
    revisions = document.revisions()
    assert len(revisions) == 2
    assert not before & set(revisions)


def test_matrix_growth_touches_the_line() -> None:
    document = Document()
    document.insert(Matrix("matrix", rows=2, cols=2, slots=[[], [], [], []]))
    before = document.revisions()
    document.matrix_add_row()
    assert document.revisions() != before
    between = document.revisions()
    document.matrix_add_column()
    assert document.revisions() != between


def test_revisions_are_a_copy_not_the_live_list() -> None:
    document = Document()
    revisions = document.revisions()
    revisions[0] = -1
    assert document.revisions() != revisions


def test_invalidate_renumbers_every_line() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    before = set(document.revisions())
    document.invalidate()
    assert not before & set(document.revisions())


# --- copy-on-write snapshots ----------------------------------------------
#
# Undo snapshots share their lines with the live document, so every edit has
# to buy a private copy of the line it touches first. Get that wrong and the
# edit lands inside the undo history instead of (or as well as) the
# document — silently, and only visible once the user undoes something.


def matrix() -> Matrix:
    return Matrix("matrix", rows=2, cols=2, slots=[[], [], [], []])


def test_deleting_does_not_reach_into_the_undo_snapshot() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(Character("2"))
    document.to_line_start()
    document.delete()
    assert document.root == [Character("2")]
    assert document.undo()
    assert document.root == [Character("1"), Character("2")]


def test_growing_a_matrix_does_not_reach_into_the_undo_snapshot() -> None:
    document = Document()
    document.insert(matrix())
    document.insert(Character("7"))
    assert document.matrix_add_row()
    live = document.root[0]
    assert isinstance(live, Matrix)
    assert live.rows == 3
    assert document.undo()
    restored = document.root[0]
    assert isinstance(restored, Matrix)
    assert restored.rows == 2, "the snapshot kept a matrix the edit had grown"
    assert len(restored.slots) == 4


def test_growing_a_matrix_column_does_not_reach_into_the_snapshot() -> None:
    document = Document()
    document.insert(matrix())
    assert document.matrix_add_column()
    assert document.undo()
    restored = document.root[0]
    assert isinstance(restored, Matrix)
    assert restored.cols == 2
    assert len(restored.slots) == 4


def test_merging_lines_does_not_share_nodes_with_the_snapshot() -> None:
    """The nodes of the line that goes move into the line that stays."""
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(matrix())
    document.exit()
    document.to_line_start()
    assert document.merge_with_previous_line()
    assert len(document.lines) == 1
    # Grow the matrix that has just moved into the first line; the merge
    # left the cursor exactly where the joined content starts.
    assert document.enter() is not None
    assert document.matrix_add_row()
    assert document.undo()  # undoes the row
    assert document.undo()  # undoes the merge
    assert len(document.lines) == 2
    moved = document.lines[1][0]
    assert isinstance(moved, Matrix)
    assert moved.rows == 2, "editing the merged line reached back into the snapshot"


def test_merging_with_the_next_line_does_not_share_nodes() -> None:
    document = Document()
    document.insert(matrix())
    document.exit()
    document.new_line()
    document.insert(Character("9"))
    document.line_up()
    document.to_line_end()
    assert document.merge_with_next_line()
    document.to_line_start()
    document.enter()
    assert document.matrix_add_column()
    assert document.undo()
    assert document.undo()
    assert len(document.lines) == 2
    original = document.lines[0][0]
    assert isinstance(original, Matrix)
    assert original.cols == 2


def test_editing_a_nested_slot_does_not_reach_into_the_snapshot() -> None:
    document = Document()
    document.insert(fraction())
    document.insert(Character("1"))  # into the numerator
    document.insert(Character("2"))
    assert document.undo()
    structure = document.root[0]
    assert isinstance(structure, Structure)
    assert structure.slots[0] == [Character("1")]


def test_editing_one_line_does_not_disturb_the_snapshot_of_another() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    document.line_up()
    document.insert(Character("8"))  # first line becomes "18"
    assert document.lines[0] == [Character("1"), Character("8")]
    assert document.lines[1] == [Character("2")]
    assert document.undo()
    assert document.lines[0] == [Character("1")]
    assert document.lines[1] == [Character("2")], "the untouched line was disturbed"


def test_loaded_lines_are_not_edited_behind_the_caller_s_back() -> None:
    document = Document()
    outside = [Character("1")]
    document.load_lines([outside])
    assert_private_lines_are_really_private(document)
    document.insert(Character("2"))
    assert document.root == [Character("1"), Character("2")]
    assert outside == [Character("1")], "the caller's own list was modified"


def test_loading_a_different_number_of_lines_keeps_the_bookkeeping_aligned() -> None:
    document = Document()
    document.load_lines([[Character("1")], [Character("2")], [Character("3")]])
    assert_private_lines_are_really_private(document)
    document.load_lines([[Character("9")]])
    assert_private_lines_are_really_private(document)


def test_a_long_edit_session_undoes_and_redoes_exactly(  # noqa: C901
) -> None:
    """Differential check of the whole undo history.

    Copy-on-write is easy to get subtly wrong: an edit that reaches into a
    snapshot corrupts a state the user only sees much later, when they undo
    far enough back. So drive a long, varied session, remember every state
    it passed through, then walk the history backwards and forwards and
    require an exact match at each step.
    """
    random.seed(20260813)
    document = Document()

    def act(step: int) -> None:
        choice = step % 12
        if choice in (0, 1, 2):
            document.insert(Character(random.choice("0123456789")))
        elif choice == 3:
            document.insert(fraction())
        elif choice == 4:
            document.insert(matrix())
        elif choice == 5:
            document.new_line()
        elif choice == 6:
            document.backspace() if random.random() < 0.5 else document.delete()
        elif choice == 7:
            document.merge_with_previous_line()
        elif choice == 8:
            document.matrix_add_row() or document.matrix_add_column()
        elif choice == 9:
            document.next_slot()
        elif choice == 10:
            document.left() if random.random() < 0.5 else document.right()
        else:
            document.exit() or document.line_up() or document.line_down()

    history = [copy.deepcopy(document.lines)]
    for step in range(150):  # below UNDO_LIMIT, so nothing is dropped
        depth = len(document._past)
        act(step)
        if len(document._past) > depth:
            history.append(copy.deepcopy(document.lines))
        else:
            assert document.lines == history[-1], "changed without an undo step"

    assert len(history) > 40, "the session must exercise plenty of edits"
    forwards = list(history)

    while len(history) > 1:
        assert document.undo()
        history.pop()
        assert document.lines == history[-1]
    assert not document.undo()

    for state in forwards[1:]:
        assert document.redo()
        assert document.lines == state
    assert not document.redo()


def _reachable(lines: list[list[object]]) -> set[int]:
    """Identities of every list and node reachable from these lines."""
    seen: set[int] = set()

    def walk(sequence: list[object]) -> None:
        seen.add(id(sequence))
        for node in sequence:
            seen.add(id(node))
            slots = getattr(node, "slots", None)
            if slots is not None:
                for slot in slots:
                    walk(slot)

    for line in lines:
        walk(line)
    return seen


def assert_private_lines_are_really_private(document: Document) -> None:
    """The rule copy-on-write rests on.

    A line the document believes it owns outright must share nothing — not
    the list, not a node, not a nested slot — with any undo snapshot.
    Breaking this does not show up as a wrong answer straight away: it
    leaves the document one edit away from writing into its own history.

    The per-line bookkeeping must also stay aligned with the lines
    themselves: the web adapter pairs lines with revisions under
    ``strict=True``, so a drift there is a crash in production.
    """
    assert len(document._shared) == len(document.lines)
    assert len(document._revisions) == len(document.lines)
    snapshots = _reachable([line for lines, _ in document._past for line in lines])
    snapshots |= _reachable([line for lines, _ in document._future for line in lines])
    private = _reachable(
        [line for line, shared in zip(document.lines, document._shared, strict=True) if not shared]
    )
    assert private.isdisjoint(snapshots), "a line marked private is reachable from a snapshot"


def test_every_edit_keeps_private_lines_private() -> None:
    random.seed(20260813)
    document = Document()

    def act(step: int) -> None:
        choice = step % 12
        if choice in (0, 1, 2):
            document.insert(Character(random.choice("0123456789")))
        elif choice == 3:
            document.insert(fraction())
        elif choice == 4:
            document.insert(matrix())
        elif choice == 5:
            document.new_line()
        elif choice == 6:
            document.backspace() if random.random() < 0.5 else document.delete()
        elif choice == 7:
            document.merge_with_previous_line()
        elif choice == 8:
            document.matrix_add_row() or document.matrix_add_column()
        elif choice == 9:
            document.merge_with_next_line()
        elif choice == 10:
            document.left() if random.random() < 0.5 else document.right()
        else:
            document.exit() or document.line_up() or document.line_down()

    for step in range(150):
        act(step)
        assert_private_lines_are_really_private(document)

    while document.undo():
        assert_private_lines_are_really_private(document)
    while document.redo():
        assert_private_lines_are_really_private(document)


def test_merging_keeps_the_joined_line_private() -> None:
    """The nodes of the line that goes end up inside the line that stays."""
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(matrix())
    document.exit()
    document.to_line_start()
    assert document.merge_with_previous_line()
    assert_private_lines_are_really_private(document)


def test_merging_with_the_next_line_keeps_it_private() -> None:
    document = Document()
    document.insert(matrix())
    document.exit()
    document.new_line()
    document.insert(Character("9"))
    document.line_up()
    document.to_line_end()
    assert document.merge_with_next_line()
    assert_private_lines_are_really_private(document)


def test_undo_treats_every_restored_line_as_shared() -> None:
    """Undo hands back lines that older snapshots still point at.

    The line it restores is not necessarily private just because it was
    the last one edited: while the user was working elsewhere, every
    snapshot taken kept a reference to it.
    """
    document = Document()
    document.insert(Character("a"))
    document.new_line()
    document.insert(Character("b"))  # first line untouched from here on,
    document.insert(Character("c"))  # so these snapshots all share it
    document.line_up()
    document.insert(Character("d"))  # now the first line is the edit target
    assert document.undo()
    assert_private_lines_are_really_private(document)
