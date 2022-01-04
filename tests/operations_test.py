"""
Test HabiticaOperator class
"""

from unittest import mock

import pytest

from habot.habitica_operations import (HabiticaOperator, NotFoundException,
                                       AmbiguousOperationException)


@pytest.fixture()
def test_operator(header_fx):
    """
    Create a HabiticaOperator for tests.
    """
    return HabiticaOperator(header_fx)

# pylint: disable=redefined-outer-name


@pytest.mark.parametrize(
    ["task_name", "task_type"],
    [
        ("Test TODO 1", None),
        ("Test TODO 1", "todo"),
        ("Test", "daily"),
        ("Test", "habit"),
    ]
)
@pytest.mark.usefixtures("mock_task_finding")
def test_task_finder(test_operator, task_name, task_type):
    """
    Test that task finder is able to find a matching task when one exists.
    """
    found_task = test_operator.find_task(task_name, task_type=task_type)
    assert found_task


@pytest.mark.parametrize(
    ["task_name", "exception"],
    [
        ("nonexistent task", NotFoundException),
        ("Test", AmbiguousOperationException),
    ]
)
@pytest.mark.usefixtures("mock_task_finding")
def test_task_finder_exception(test_operator, task_name, exception):
    """
    Test that NotFoundException is raised when task is not found.
    """
    with pytest.raises(exception):
        test_operator.find_task(task_name)


@pytest.mark.usefixtures("mock_task_ticking")
def test_tick(requests_mock, test_operator):
    """
    Test that tick_task sends the correct request.
    """
    task_uid = "963e2ced-fa22-4b18-a22b-c423764e26f3"
    tick_url = f"https://habitica.com/api/v3/tasks/{task_uid}/score/up"
    test_operator.tick_task("Test habit")

    assert len(requests_mock.request_history) == 2
    tick_request = requests_mock.request_history[1]
    assert tick_url in tick_request.url


@mock.patch("habitica_helper.task.Task.add_to_user")
@pytest.mark.parametrize(
    ("name", "note", "type_"),
    [
        ("test task", "test note", "todo"),
        ("test task", None, "todo"),
        ("test task", "", "todo"),
        ("test habit", "do domething cool", "habit"),
        ("test daily", "drink water", "daily"),
    ]
)
def test_add_task_successfully(mock_add, name, note, type_, test_operator,
                               header_fx):
    """
    Ensure that `add_task` method call works in happy cases.

    Tasks classes with and without notes must be created successfully with the
    correct text, notes and type and `add_to_user` must be called.
    """
    # pylint: disable=too-many-arguments
    task = test_operator.add_task(name, note, type_)
    mock_add.assert_called_with(header_fx)

    assert task.text == name

    if note:
        assert task.notes == note
    else:
        assert not task.notes

    if type_:
        assert task.tasktype == type_
    else:
        assert task.tasktype == "todo"


@mock.patch("habitica_helper.task.Task.add_to_user")
def test_add_task_default_type(mock_add, test_operator, header_fx):
    """
    Make sure that if a task type is not provided, a todo is created.
    """
    task = test_operator.add_task("some task")
    assert task.tasktype == "todo"
    mock_add.assert_called_with(header_fx)


@mock.patch("habitica_helper.task.Task.add_to_user")
def test_add_task_illegal_type(mock_add, test_operator):
    """
    Ensure that an error is reported when illegal task type is given.
    """
    with pytest.raises(ValueError) as e:  # pylint: disable=invalid-name
        test_operator.add_task("some task", task_type="illegal_type")
    assert "Illegal task type 'illegal_type'" in str(e.value)
    mock_add.assert_not_called()


@mock.patch("habitica_helper.habrequest.post")
def test_join_quest(mock_post, monkeypatch, test_operator, header_fx):
    """
    Test that a new quest will be joined.
    """
    def _quest_dict(*args, **kwargs):
        # pylint: disable=unused-argument
        return {"quest": {"key": "some-quest",
                          "active": False,
                          "members": ["some-other-member",
                                      "more-members"],
                          }
                }

    monkeypatch.setattr("habot.habitica_operations.get_dict_from_api",
                        _quest_dict)
    test_operator.join_quest()
    mock_post.assert_called_with(
            "https://habitica.com/api/v3/groups/party/quests/accept",
            headers=header_fx)


@mock.patch("habitica_helper.habrequest.post")
def test_do_not_join_active_quest(mock_post, monkeypatch, test_operator):
    """
    Test that an joining an active quest will not be attempted.
    """
    def _quest_dict(*args, **kwargs):
        # pylint: disable=unused-argument
        return {"quest": {"key": "some-quest",
                          "active": True,
                          "members": [],
                          }
                }

    monkeypatch.setattr("habot.habitica_operations.get_dict_from_api",
                        _quest_dict)
    test_operator.join_quest()
    mock_post.assert_not_called()


@mock.patch("habitica_helper.habrequest.post")
def test_do_not_rejoin_quest(mock_post, monkeypatch, test_operator, header_fx):
    """
    Test that if the user has already joined a quest, it won't be rejoined.
    """
    def _quest_dict(*args, **kwargs):
        # pylint: disable=unused-argument
        return {"quest": {"key": "some-quest",
                          "active": True,
                          "members": [header_fx["x-api-user"]],
                          }
                }

    monkeypatch.setattr("habot.habitica_operations.get_dict_from_api",
                        _quest_dict)
    test_operator.join_quest()
    mock_post.assert_not_called()


@mock.patch("habitica_helper.habrequest.post")
def test_cron(mock_post, test_operator, header_fx):
    """
    Test that `cron` method makes the right API call.
    """
    test_operator.cron()
    mock_post.assert_called_with("https://habitica.com/api/v3/cron",
                                 headers=header_fx)
