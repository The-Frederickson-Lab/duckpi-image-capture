import os

from fabric.connection import Connection as FabricConnection
from unittest.mock import Mock, call, create_autospec

from duckpi_ic.ic import make_filename_base, move_files_to_remote, update_first_last


def test_make_filename():
    """Test that we can make a filename according to spec"""
    filename = make_filename_base(camera="A", stage=1, row=2)
    assert filename == "cam_A_1_2"


def test_update_first_last(tmp_path):
    """Test that update_first_last correctly copies the
    file contents.
    """
    first = tmp_path / "first.jpg"
    first.open("a").close()
    last = tmp_path / "last.jpg"
    last.open("a").close()
    local1 = tmp_path / "local1.jpg"
    local1.write_text("local1")
    local2 = tmp_path / "local2.jpg"
    local2.write_text("local2")

    first_last = [first, last]
    local_paths = [local1, local2]

    assert os.stat(first).st_size == 0

    update_first_last(first_last, local_paths)

    assert os.stat(first).st_size > 0
    assert os.stat(last).st_size == 0

    update_first_last(first_last, local_paths)

    assert os.stat(first).st_size > 0
    assert os.stat(last).st_size > 0


def test_move_to_remote(monkeypatch):
    """Test that move_to_remote handles paths correctly"""

    from duckpi_ic.settings import settings

    mock_remote_save_path = "/path/to/remote/home"

    monkeypatch.setattr(settings, "REMOTE_SAVE_DIR", mock_remote_save_path)

    mock_fabric_connection = Mock(FabricConnection)

    mock_remove = create_autospec(os.remove)

    monkeypatch.setattr(os, "remove", mock_remove)

    local_paths = [f"/noexist/cameraMOCK/{n}.jpg" for n in range(1, 3)]

    name = "test-experiment"

    failures = move_files_to_remote(mock_fabric_connection, local_paths, name)

    assert len(failures) == 0

    mock_fabric_connection.put.assert_called()

    put_calls = [
        call(
            local_paths[n],
            os.path.join(mock_remote_save_path, f"{name}/cameraMOCK/{n+1}.jpg"),
        )
        for n in range(0, 2)
    ]

    mock_fabric_connection.put.assert_has_calls(put_calls)

    remove_calls = [call(p) for p in local_paths]

    mock_remove.assert_has_calls(remove_calls)

    mock_fabric_exception_connection = Mock(FabricConnection)

    mock_fabric_exception_connection.put = Mock(side_effect=Exception())

    mock_remove.reset_mock()

    failures = move_files_to_remote(mock_fabric_exception_connection, local_paths, name)

    mock_remove.assert_not_called()

    assert len(failures) == 2
