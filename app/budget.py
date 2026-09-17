from datetime import date


class DailyBudget:
    """Tracks how many requests have been served today and reports whether the
    daily soft or hard cap has been crossed. Resets automatically at midnight.
    """

    def __init__(self, soft_cap: int, hard_cap: int):
        self.soft_cap = soft_cap
        self.hard_cap = hard_cap
        self._day = date.today()
        self._count = 0

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._day:
            self._day = today
            self._count = 0

    def record(self) -> str:
        """Records one request and returns 'normal', 'soft', or 'hard'."""
        self._reset_if_new_day()
        self._count += 1
        if self._count > self.hard_cap:
            return "hard"
        if self._count > self.soft_cap:
            return "soft"
        return "normal"
