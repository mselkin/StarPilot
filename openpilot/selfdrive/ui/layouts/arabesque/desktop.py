from collections.abc import Callable

import pyray as rl

from openpilot.selfdrive.ui.layouts.arabesque.theme import DEFAULT_THEME
from openpilot.selfdrive.ui.layouts.arabesque.tools.terminal import Terminal
from openpilot.system.ui.lib.application import gui_app, MouseEvent, MousePos, TextAlignment
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.label import gui_label


class ArabesqueLayout(Widget):
  def __init__(self, on_exit: Callable[[], None]):
    super().__init__()
    self._on_exit = on_exit
    self._menu_open = False
    self._pressed_rect: rl.Rectangle | None = None
    self._active_tool: Widget | None = None
    self._active_name = ""

  def _update_layout_rects(self):
    rect = self._rect
    # GuiApplication scales both drawing and input from these logical coordinates.
    self._scale = s = min(rect.width / 2160, rect.height / 1080)
    self._bar = rl.Rectangle(rect.x, rect.y, rect.width, 104 * s)
    self._menu_button = rl.Rectangle(rect.x + 24 * s, rect.y + 8 * s, 88 * s, 88 * s)
    self._exit_button = rl.Rectangle(rect.x + 24 * s, rect.y + 116 * s, 456 * s, 116 * s)
    self._back_button = rl.Rectangle(rect.x + rect.width - 296 * s, rect.y + 8 * s, 272 * s, 88 * s)
    self._dock = rl.Rectangle(rect.x + (rect.width - 456 * s) / 2, rect.y + rect.height - 208 * s, 456 * s, 176 * s)
    self._tool_rect = rl.Rectangle(rect.x, self._bar.y + self._bar.height, rect.width, rect.height - self._bar.height)

  def _open_tool(self, name: str, tool: Widget):
    self._close_tool()
    self._active_tool, self._active_name = tool, name
    tool.set_rect(self._tool_rect)
    tool.show_event()

  def _close_tool(self):
    tool, self._active_tool = self._active_tool, None
    self._active_name = ""
    self._menu_open = False
    self._pressed_rect = None
    gui_app.mouse_events.clear()
    # Transient tools have one explicit lifecycle owner, rather than persistent _child registration.
    if tool is not None:
      tool.hide_event()

  def hide_event(self):
    super().hide_event()
    self._close_tool()

  def _handle_mouse_press(self, pos: MousePos):
    self._pressed_rect = None
    if rl.check_collision_point_rec(pos, self._menu_button):
      self._pressed_rect = self._menu_button
    elif self._menu_open:
      if rl.check_collision_point_rec(pos, self._exit_button):
        self._pressed_rect = self._exit_button
    elif self._active_tool is not None and rl.check_collision_point_rec(pos, self._back_button):
      self._pressed_rect = self._back_button
    elif self._active_tool is None and rl.check_collision_point_rec(pos, self._dock):
      self._pressed_rect = self._dock

  def _handle_mouse_release(self, pos: MousePos):
    pressed = self._pressed_rect
    self._pressed_rect = None
    if pressed is self._menu_button and rl.check_collision_point_rec(pos, self._menu_button):
      self._menu_open = not self._menu_open
    elif self._menu_open:
      self._menu_open = False
      if pressed is self._exit_button and rl.check_collision_point_rec(pos, self._exit_button):
        self._on_exit()
    elif pressed is self._back_button and rl.check_collision_point_rec(pos, self._back_button):
      self._close_tool()
    elif pressed is self._dock and rl.check_collision_point_rec(pos, self._dock):
      self._open_tool(tr("Terminal"), Terminal())

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    if mouse_event.left_released and not rl.check_collision_point_rec(mouse_event.pos, self._rect):
      self._pressed_rect = None
      self._menu_open = False

  def _render(self, rect: rl.Rectangle):
    s, theme = self._scale, DEFAULT_THEME
    rl.draw_rectangle_rec(rect, theme.background)
    if self._active_tool is not None:
      # Widget handles input after drawing: gate the whole frame before the tool sees chrome gestures.
      tool_enabled = self.enabled and not self._menu_open and self._pressed_rect is None and not any(
        event.slot == 0 and not rl.check_collision_point_rec(event.pos, self._tool_rect) for event in gui_app.mouse_events)
      self._active_tool.set_enabled(tool_enabled)
      rl.begin_scissor_mode(int(self._tool_rect.x), int(self._tool_rect.y), int(self._tool_rect.width), int(self._tool_rect.height))
      self._active_tool.render(self._tool_rect)
      rl.end_scissor_mode()

    rl.draw_rectangle_rec(self._bar, theme.surface)
    rl.draw_line_ex(rl.Vector2(rect.x, self._bar.y + self._bar.height),
                    rl.Vector2(rect.x + rect.width, self._bar.y + self._bar.height), 2 * s, theme.control)
    menu_pressed = self._menu_open or self._pressed_rect is self._menu_button and self.is_pressed
    rl.draw_rectangle_rounded(self._menu_button, 0.28, 12, theme.pressed if menu_pressed else theme.control)

    center = rl.Vector2(self._menu_button.x + 42 * s, self._menu_button.y + 44 * s)
    rl.draw_ring(center, 15 * s, 20 * s, 0, 360, 24, theme.background)
    rl.draw_line_ex(rl.Vector2(center.x + 18 * s, center.y - 20 * s), rl.Vector2(center.x + 18 * s, center.y + 20 * s),
                    5 * s, theme.background)
    gui_label(rl.Rectangle(rect.x + 136 * s, rect.y, self._back_button.x - rect.x - 160 * s, self._bar.height),
              self._active_name or "Arabesque", round(40 * s), theme.text, theme.font_weight)

    if self._active_tool is not None:
      back_pressed = self._pressed_rect is self._back_button and self.is_pressed
      rl.draw_rectangle_rounded(self._back_button, 0.28, 12, theme.pressed if back_pressed else theme.control)
      gui_label(self._back_button, "< " + tr("Desktop"), round(32 * s), theme.background, theme.font_weight,
                alignment=TextAlignment.CENTER)
    else:
      rl.draw_rectangle_rounded(self._dock, 0.27, 12, theme.surface)
      rl.draw_rectangle_rounded_lines_ex(self._dock, 0.27, 12, 2 * s, theme.control)
      icon = rl.Rectangle(self._dock.x + 24 * s, self._dock.y + 24 * s, 128 * s, 128 * s)
      dock_pressed = self._pressed_rect is self._dock and self.is_pressed
      rl.draw_rectangle_rounded(icon, 0.2, 12, theme.pressed if dock_pressed else theme.control)
      rl.draw_line_ex(rl.Vector2(icon.x + 28 * s, icon.y + 38 * s), rl.Vector2(icon.x + 52 * s, icon.y + 62 * s), 6 * s, theme.background)
      rl.draw_line_ex(rl.Vector2(icon.x + 52 * s, icon.y + 62 * s), rl.Vector2(icon.x + 28 * s, icon.y + 86 * s), 6 * s, theme.background)
      rl.draw_line_ex(rl.Vector2(icon.x + 70 * s, icon.y + 86 * s), rl.Vector2(icon.x + 104 * s, icon.y + 86 * s), 6 * s, theme.background)
      gui_label(rl.Rectangle(self._dock.x + 176 * s, self._dock.y + 40 * s, self._dock.width - 200 * s, 48 * s),
                tr("Terminal"), round(36 * s), theme.text, theme.font_weight)
      gui_label(rl.Rectangle(self._dock.x + 176 * s, self._dock.y + 100 * s, self._dock.width - 200 * s, 36 * s),
                tr("Local shell"), round(28 * s), theme.secondary_text, theme.font_weight)

    if self._menu_open:
      exit_pressed = self._pressed_rect is self._exit_button and self.is_pressed
      color = theme.pressed if exit_pressed else theme.surface
      rl.draw_rectangle_rounded(self._exit_button, 0.22, 12, color)
      rl.draw_rectangle_rounded_lines_ex(self._exit_button, 0.22, 12, 2 * s, theme.control)
      gui_label(rl.Rectangle(self._exit_button.x + 28 * s, self._exit_button.y, self._exit_button.width - 56 * s, self._exit_button.height),
                tr("Exit Arabesque"), round(40 * s), theme.background if exit_pressed else theme.text, theme.font_weight)
