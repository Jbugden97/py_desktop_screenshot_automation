from py_desktop_screenshot_automation.scrollable_frame import mouse_wheel_units


def test_windows_mouse_wheel_delta_uses_120_step_units() -> None:
    assert mouse_wheel_units(120) == -1
    assert mouse_wheel_units(-240) == 2


def test_small_mouse_wheel_delta_is_preserved() -> None:
    assert mouse_wheel_units(3) == -3
    assert mouse_wheel_units(-2) == 2
    assert mouse_wheel_units(0) == 0
