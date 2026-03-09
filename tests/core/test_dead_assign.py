from __future__ import annotations

from invar.core.dead_assign import check_dead_assigns
from invar.core.models import FileInfo, RuleConfig


def _check_source(source: str) -> list:
    file_info = FileInfo(
        path="src/invar/core/sample.py", lines=len(source.splitlines()), source=source
    )
    return check_dead_assigns([file_info], RuleConfig())


def test_detects_simple_dead_assignment() -> None:
    source = """
def f():
    value = 1
    return 0
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "value" in violations[0].message


def test_augassign_reads_previous_value() -> None:
    source = """
def f():
    total = 1
    total += 2
    return total
"""
    violations = _check_source(source)
    assert violations == []


def test_reports_unpacking_name_that_is_never_read() -> None:
    source = """
def f():
    a, b = (1, 2)
    return a
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "b" in violations[0].message


def test_loop_target_is_tracked() -> None:
    source = """
def f(items):
    for item in items:
        return 1
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "item" in violations[0].message


def test_variable_used_in_nested_scope_is_not_reported() -> None:
    source = """
def f():
    value = 1
    def nested():
        return value
    return nested()
"""
    violations = _check_source(source)
    assert violations == []


def test_with_target_is_tracked() -> None:
    source = """
def f(ctx):
    with ctx as handle:
        return 1
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "handle" in violations[0].message


def test_except_var_is_tracked() -> None:
    source = """
def f():
    try:
        raise ValueError("x")
    except ValueError as err:
        return 1
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "err" in violations[0].message


def test_exclusions_for_underscore_and_inline_allow() -> None:
    source = """
def f():
    _tmp = 1
    x = 2  # @invar:allow dead_assign: intentional scratch
    return 0
"""
    violations = _check_source(source)
    assert violations == []


def test_conditional_overwrite_is_not_reported_false_positive() -> None:
    source = """
def f(flag: bool):
    value = 1
    if flag:
        value = 2
    return value
"""
    violations = _check_source(source)
    assert violations == []


def test_loop_default_overwrite_is_not_reported_false_positive() -> None:
    source = """
def f(items):
    result = 0
    for item in items:
        result = item
    return result
"""
    violations = _check_source(source)
    assert violations == []


def test_while_counter_not_false_positive() -> None:
    source = """
def f(n: int) -> int:
    count = 0
    while n > 0:
        count += 1
        n -= 1
    return count
"""
    violations = _check_source(source)
    assert violations == []


def test_boolean_flag_loop_carried() -> None:
    source = """
def f(items) -> bool:
    found = False
    for item in items:
        if item == target:
            found = True
    return found
"""
    violations = _check_source(source)
    assert violations == []


def test_accumulator_loop_carried() -> None:
    source = """
def f(numbers) -> int:
    total = 0
    for num in numbers:
        total += num
    return total
"""
    violations = _check_source(source)
    assert violations == []


def test_prev_value_tracking() -> None:
    source = """
def f(items):
    prev = None
    for item in items:
        yield prev
        prev = item
"""
    violations = _check_source(source)
    assert violations == []


def test_buffer_reset_loop_carried() -> None:
    source = """
def f(chunks) -> str:
    buffer = ""
    for chunk in chunks:
        buffer = buffer + chunk
    return buffer
"""
    violations = _check_source(source)
    assert violations == []


def test_for_loop_next_iteration_read_clears_pending_write() -> None:
    source = """
def f(items):
    prev = None
    for item in items:
        if prev is not None:
            consume(prev)
        prev = item
"""
    violations = _check_source(source)
    assert violations == []


def test_for_loop_true_dead_write_still_reported() -> None:
    source = """
def f(items):
    prev = None
    for item in items:
        if prev is not None:
            consume(prev)
        prev = item
        scratch = item
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "scratch" in violations[0].message


def test_true_dead_assign_in_loop() -> None:
    source = """
def f(items):
    unused = 0
    for item in items:
        x = item
    return items
"""
    violations = _check_source(source)
    assert len(violations) == 2
    assert "unused" in violations[0].message


# Regression tests for while-loop false positives (da-while-repro)
# These tests reproduce pre-fix false positives where loop-carried state is incorrectly reported as dead.
# At pre-fix: violations should be found (tests FAIL).
# After fix: violations should be empty (tests PASS).
# Negative control: test_while_loop_true_dead_write_still_reported always expects violations.


def test_while_loop_boolean_flag_carried_state() -> None:
    """Loop-carried boolean state like was_awaiting_approval should not be reported.

    Pre-fix: FALSE POSITIVE - incorrectly reports was_awaiting_approval as dead.
    Post-fix: No violations (body-read simulation clears pending writes).

    The key pattern: variable is READ before being REASSIGNED in loop body.
    At pre-fix, only condition is re-checked, not body reads.
    """
    source = """
def f() -> bool:
    was_awaiting_approval = False
    while True:
        current = read_state()
        if was_awaiting_approval:
            notify()
        was_awaiting_approval = current.awaiting
        if should_exit(current):
            return was_awaiting_approval
"""
    violations = _check_source(source)
    # Pre-fix: FAILS (reports was_awaiting_approval as dead)
    # Post-fix: PASSES (no violations)
    assert violations == []


def test_while_loop_cursor_update_carried_state() -> None:
    """Follow-mode cursor update like seen_count should not be reported.

    Pre-fix: FALSE POSITIVE - incorrectly reports seen_count as dead.
    Post-fix: No violations (body-read simulation clears pending writes).
    """
    source = """
def f() -> int:
    seen_count = 0
    while True:
        latest_entries = read_entries()
        if len(latest_entries) < seen_count:
            seen_count = 0
        if len(latest_entries) > seen_count:
            emit(latest_entries[seen_count:])
            seen_count = len(latest_entries)
        if done(latest_entries):
            return seen_count
"""
    violations = _check_source(source)
    # Pre-fix: FAILS (reports seen_count as dead)
    # Post-fix: PASSES (no violations)
    assert violations == []


def test_while_loop_accumulated_state_via_helper() -> None:
    """Helper-returned accumulated state like message_history should not be reported.

    Pre-fix: FALSE POSITIVE - incorrectly reports message_history as dead.
    Post-fix: No violations (body-read simulation clears pending writes).
    """
    source = """
def f() -> list:
    message_history = []
    while True:
        pending_message = poll()
        if pending_message is not None:
            response = process(pending_message, message_history)
            message_history = response
            message_history = compact(message_history)
        if should_stop(message_history):
            return message_history
"""
    violations = _check_source(source)
    # Pre-fix: FAILS (reports message_history as dead)
    # Post-fix: PASSES (no violations)
    assert violations == []


def test_while_loop_true_dead_write_still_reported() -> None:
    """Negative control: truly dead write in while loop should still be reported."""
    source = """
def f(items):
    while items:
        item = items.pop()
        process(item)
        unused_value = item.id
    return items
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "unused_value" in violations[0].message


def test_anima_repro_agent_message_history_not_reported() -> None:
    """Exact anima-style loop-carried message_history assignment stays live."""
    source = """
async def f(agent):
    message_history = []
    while True:
        pending_message = await poll()
        if pending_message is not None:
            response_result = await process(agent, pending_message, message_history)
            message_history = response_result
            message_history = await compact(agent, message_history)
            continue
        await sleep()
"""
    violations = _check_source(source)
    assert violations == []


def test_anima_repro_talk_runtime_was_awaiting_approval_not_reported() -> None:
    """Exact anima-style tuple assignment keeps approval flag live."""
    source = """
async def f(session):
    was_awaiting_approval = False
    while True:
        (
            should_return,
            had_error,
            was_awaiting_approval,
        ) = await wait_for_interact_or_input_or_stream(
            session=session,
            was_awaiting_approval=was_awaiting_approval,
        )
        if should_return:
            return
        if had_error:
            break
"""
    violations = _check_source(source)
    assert violations == []


def test_anima_repro_inspect_collect_seen_count_not_reported() -> None:
    """Exact anima-style follow cursor update stays live."""
    source = """
def f(instance_id):
    seen_count = 0
    while True:
        latest_entries = read(instance_id)
        if len(latest_entries) < seen_count:
            seen_count = 0
        if len(latest_entries) > seen_count:
            emit(latest_entries[seen_count:])
            seen_count = len(latest_entries)
        sleep()
"""
    violations = _check_source(source)
    assert violations == []


def test_anima_repro_unrelated_dead_assign_still_reported() -> None:
    """Negative control: unrelated while-loop dead assignment still reports."""
    source = """
def f(instance_id):
    seen_count = 0
    while True:
        latest_entries = read(instance_id)
        if len(latest_entries) > seen_count:
            emit(latest_entries[seen_count:])
            seen_count = len(latest_entries)
        stale_snapshot = latest_entries
        sleep()
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "stale_snapshot" in violations[0].message
