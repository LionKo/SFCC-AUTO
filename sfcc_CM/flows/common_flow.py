from __future__ import annotations


class CommonFlow:
    def __init__(self, bot: object) -> None:
        self.bot = bot

    def handle_emergency(self, screenshot=None) -> bool:
        return self.bot.handle_emergency_buttons(initial_screenshot=screenshot)

    def run_once(self, screenshot=None, max_clicks: int = 1) -> bool:
        return self.bot.handle_common_layers_once(screenshot=screenshot, max_clicks=max_clicks)

    def handle_exception(self, screenshot=None, max_clicks: int = 1) -> bool:
        return self.bot.handle_exception_layer(max_clicks=max_clicks, initial_screenshot=screenshot)
