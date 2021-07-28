from collections import deque


class Game:
    def __init__(self, state):
        self.parts = deque()
        self.part = None
        self.timer = None
        self.state = state

    def load(self, game_data):
        """Given data from a file, load questions or whatever exists in this game"""
        print("game data:", game_data)
        for part_data in game_data["parts"]:
            part = PART_TYPES[part_data["type"]]()
            part.load(part_data)
            self.parts.append(part)

    def stage(self):
        """Return data for the current stage."""
        if self.part:
            return self.part.stage()
        return {}

    def actions(self):
        """Return all available actions at this point in time."""
        if self.part:
            return self.part.actions(self.state)
        return []

    def action(self, key):
        """Perform an action"""
        if self.part:
            return self.part.action(key, self.state)
        return None

    def __iter__(self):
        return self

    def __next__(self):
        """Advance one step. E.g.: show one more hint, or go to next question, etc."""
        try:
            return next(self.part)
        except StopIteration:
            if self.parts:
                self.part = self.parts.popleft()
            else:
                raise
        except TypeError:
            self.part = self.parts.popleft()


class Part:
    def __init__(self):
        self.task = None
        self.tasks = deque()

    def load(self, part_data):
        raise NotImplementedError

    def stage(self):
        if self.task:
            return self.task.stage()
        return {}

    def actions(self, state):
        """Return all available actions at this point in time."""
        if self.task:
            return self.task.actions(state)
        return []

    def action(self, key, state):
        """Perform an action"""
        if self.task:
            return self.task.action(key, state)
        return None

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.task)
        except StopIteration:
            self.task = None
            if self.tasks:
                self.task = self.tasks.popleft()
            else:
                raise
        except TypeError:
            if self.tasks:
                self.task = self.tasks.popleft()
            else:
                raise StopIteration


class Connections(Part):
    def load(self, part_data):
        """Given part data, load questions or other tasks (theoretically)."""
        for task_data in part_data["questions"]:
            self.tasks.append(Question(task_data))


class Sequences(Connections):
    pass


class Question:
    def __init__(self, task_data):
        self.answer = task_data["answer"]
        self.steps = [Step(step_data) for step_data in task_data["steps"]]
        self.is_sequences = len(self.steps) == 3
        if self.is_sequences:
            self.steps.append(Step(None))  # question mark
        self.active_team = None
        self.n_shown = 0

    def stage(self):
        return {
            "steps": [step.label for step in self.steps[: self.n_shown]],
            "answer": self.answer if self.n_shown == 5 else None,
        }

    def actions(self, state):
        """Return all available actions at this point in time."""
        available = []
        if self.n_shown > 4:
            return available
        if not self.n_shown:
            available.extend(
                [
                    ("start_left", "Start question for left team"),
                    ("start_right", "Start question for right team"),
                ],
            )
        if state.buzz in ("left", "right"):
            # can only award if they buzzed
            available.extend(
                [
                    ("award_primary", "Give points to primary team"),
                    ("award_bonus", "Give 1 point to other team"),
                    ("no_points", "No points for either team"),
                ],
            )
        if not available and self.n_shown == 4:
            # other team didn't buzz, but we showed all
            available.extend(
                [
                    ("award_bonus", "Give 1 point to other team"),
                    ("no_points", "No points for either team"),
                ],
            )
        return available

    def action(self, key, state):
        """Perform an action"""
        if key not in [k for (k, _desc) in self.actions(state)]:
            return None
        if key.startswith("start_"):
            _, __, team = key.partition("_")
            self.active_team = team
            self.n_shown += 1
            state.buzz = f"active-{team}"
            # self.timer = Timer(30)
        if key.startswith("award_"):
            team = self.active_team
            if not team:
                raise RuntimeError("unknown active team")
            if key == "award_primary":
                state.points[team] += {1: 5, 2: 3, 3: 2, 4: 1}[self.n_shown]
            elif key == "award_bonus":
                state.points["left" if team == "right" else "right"] += 1
            else:
                raise RuntimeError("unknown award_ key")
            self.n_shown = 5
            state.buzz = "inactive"
            self.active_team = None
        if key == "no_points":
            self.n_shown = 5
            state.buzz = "inactive"
            self.active_team = None

    def __iter__(self):
        return self

    def __next__(self):
        if not self.n_shown:
            # activate only via an action (to mark team)
            pass
        elif self.n_shown == 1:
            self.n_shown += 1
        elif self.n_shown == 2 and self.is_sequences:
            self.n_shown += 2
        elif self.n_shown < 5:
            self.n_shown += 1
        else:
            raise StopIteration("Out of steps")


class Step:
    def __init__(self, step_data):
        if step_data is None:
            self.label = "?"
            self.explanation = None
        else:
            self.label = step_data["label"]
            self.explanation = step_data.get("explanation")


PART_TYPES = {
    "connections": Connections,
    "sequences": Sequences,
}
