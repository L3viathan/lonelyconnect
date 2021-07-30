import random
from time import monotonic
from collections import deque


class Game:
    def __init__(self, state):
        self.parts = deque()
        self.part = None
        self.state = state

    def load(self, game_data):
        """Given data from a file, load questions or whatever exists in this game"""
        for part_data in game_data["parts"]:
            part = PART_TYPES[part_data["type"]](self)
            part.load(part_data)
            self.parts.append(part)

    def secrets(self):
        """Return data for the current stage."""
        if self.part:
            return self.part.secrets()
        return {}

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

    def buzz(self, who):
        if self.part:
            return self.part.buzz(who)

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
    def __init__(self, game):
        self.game = game
        self.task = None
        self.tasks = deque()

    def load(self, part_data):
        raise NotImplementedError

    def secrets(self):
        if self.task:
            return self.task.secrets()
        return {}

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

    def buzz(self, who):
        if self.task:
            return self.task.buzz(who)

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


class MissingVowels(Part):
    def __init__(self, game):
        super().__init__(game)
        self.timer = None

    def load(self, part_data):
        groups = part_data["groups"]
        random.shuffle(groups)
        for group_data in groups:
            self.tasks.append(MissingVowelGroup(group_data, self))

class Connections(Part):
    def load(self, part_data):
        """Given part data, load questions or other tasks (theoretically)."""
        questions = part_data["questions"]
        random.shuffle(questions)
        for question_data in questions:
            self.tasks.append(Question(question_data, self))


class Sequences(Part):
    def load(self, part_data):
        """Given part data, load questions or other tasks (theoretically)."""
        questions = part_data["questions"]
        random.shuffle(questions)
        for question_data in questions:
            self.tasks.append(Question(question_data, self, is_sequences=True))


class Task:
    def __init__(self, task_data, part):
        self.part = part

    @property
    def state(self):
        return self.part.game.state

    def __iter__(self):
        return self


class MissingVowelGroup(Task):
    def __init__(self, task_data, part):
        self.part = part
        self.name = task_data["name"]
        self.phrases = deque(Phrase(phrase_data) for phrase_data in task_data["phrases"])
        self.phrase = None
        self.clear = False

    @property
    def timer(self):
        return self.part.timer

    def secrets(self):
        if self.phrase:
            return {
                "answer": self.phrase.answer,
            }
        return {}

    def stage(self):
        stage_data = {
            "time_remaining": self.timer and self.timer.remaining_round,
            "time_total": self.timer and self.timer.duration,
            "name": self.name,
        }
        if self.phrase:
            stage_data["phrase"] = self.phrase.answer if self.clear else self.phrase.obfuscated
        return stage_data

    def actions(self, state):
        if self.state.buzz in ("left", "right") and not self.clear:
            return [
                ("award_primary", "Give a point to the buzzing team"),
                ("punish_primary", "Take a point from the buzzing team"),
                ("award_secondary", "Give a point to the other team"),
                ("punish_secondary", "Take a point from the other team"),
            ]
        return []

    def action(self, key, state):
        if key not in [k for (k, _desc) in self.actions(state)]:
            return None
        kind, _, team_id = key.partition("_")
        if team_id == "primary":
            team = self.state.buzz
        else:
            team = "right" if self.state.buzz == "left" else "left"
        state.points[team] += 1 if kind == "award" else -1

    def __next__(self):
        if self.phrases and (not self.phrase or self.clear):
            self.phrase = self.phrases.popleft()
            self.clear = False
        elif not self.clear:
            self.clear = True
        else:
            raise StopIteration("Out of steps")



class Question(Task):
    def __init__(self, task_data, part, is_sequences=False):
        super().__init__(task_data, part)
        self.answer = task_data["answer"]
        self.explanation = task_data["explanation"]
        self.steps = [Step(step_data) for step_data in task_data["steps"]]
        self.is_sequences = is_sequences
        self.active_team = None
        self.n_shown = 0
        self.timer = None

    def secrets(self):
        return {
            "step_explanations": [step.explanation for step in self.steps[: self.n_shown]],
            "explanation": self.explanation,
        }

    def stage(self):
        if self.timer and not self.timer.remaining and self.state.buzz != "inactive":
            self.state.buzz = "inactive"
        steps = [step.label for step in self.steps[: self.n_shown]]
        if self.is_sequences and self.n_shown == 4:
            steps[-1] = "<span class='questionmark'>?</span>"
        return {
            "steps": steps,
            "answer": self.answer if self.n_shown == 5 else None,
            "time_remaining": self.timer and self.timer.remaining_round,
            "time_total": self.timer and self.timer.duration,
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
        if not available and self.n_shown == 4 and self.timer and not self.timer.remaining:
            # other team didn't buzz, but we showed all
            available.extend(
                [
                    ("award_bonus", "Give 1 point to other team"),
                    ("no_points", "No points for either team"),
                ],
            )
        return available

    def buzz(self, who):
        if self.timer:
            self.timer.freeze()
        self.active_team = who

    def action(self, key, state):
        """Perform an action"""
        if key not in [k for (k, _desc) in self.actions(state)]:
            return None
        if key.startswith("start_"):
            _, __, team = key.partition("_")
            self.active_team = team
            self.n_shown += 1
            state.buzz = f"active-{team}"
            self.timer = Timer(30)
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
            if self.n_shown == 5:
                self.timer = None  # the latest here
        else:
            raise StopIteration("Out of steps")


def obfuscate(string):
    chars = [char for char in string.upper() if char not in "AEIOU"]
    return "".join(char if not i or random.random() > 0.2 else f" {char}" for i, char in enumerate(chars))


class Phrase:
    def __init__(self, phrase_data):
        if isinstance(phrase_data, str):
            # automatically obfuscate
            self.answer = phrase_data.upper()
            self.obfuscated = obfuscate(phrase_data)
        else:
            self.answer = phrase_data["answer"].upper()
            self.obfuscated = phrase_data["obfuscated"].upper()
        print("Initialized phrase", self.answer, "as", self.obfuscated)


class Step:
    def __init__(self, step_data):
        self.label = step_data["label"]
        self.explanation = step_data.get("explanation")


class Timer:
    def __init__(self, seconds):
        self.end = monotonic() + seconds
        self.duration = seconds
        self._remaining = None

    @property
    def remaining(self):
        if self._remaining:
            return self._remaining
        now = monotonic()
        if now >= self.end:
            return 0
        return self.end - now

    @property
    def remaining_round(self):
        return int(self.remaining)

    def freeze(self):
        self._remaining = self.remaining


PART_TYPES = {
    "connections": Connections,
    "sequences": Sequences,
    "missing vowels": MissingVowels,
}
