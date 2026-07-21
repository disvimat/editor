"""Document tree operations: editing, navigation and undo."""

from disvimat.core.document import Character, Document, Sign, Structure


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
