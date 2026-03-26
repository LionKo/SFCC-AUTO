from __future__ import annotations


class CommonFlow:
    def __init__(self, bot: object) -> None:
        self.bot = bot

    def handle_emergency(self, screenshot=None) -> bool:
        return self.bot.handle_emergency_buttons(initial_screenshot=screenshot)

    def run_once(self, screenshot=None, max_clicks: int = 1) -> bool:
        if self.handle_emergency(screenshot):
            return True
        if self.bot.handle_exception_layer(max_clicks=max_clicks, initial_screenshot=screenshot):
            return True
        return self.bot.handle_global_priority_buttons(max_clicks=max_clicks, initial_screenshot=screenshot)

    def handle_exception(self, screenshot=None, max_clicks: int = 1) -> bool:
        return self.bot.handle_exception_layer(max_clicks=max_clicks, initial_screenshot=screenshot)
