import random
from time import monotonic
from collections import deque


class Game:
    def __init__(self):
        self.parts = deque()
        self.part = None
        self.buzz_state = "inactive"
        self.points = {
            "left": 0,
            "right": 0,
        }

    @property
    def is_done(self):
        return not self.parts and not self.part

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
        base = {"points": self.points, "buzz_state": self.buzz_state}
        if self.part:
            return {**base, **self.part.stage()}
        return {"bigscores": True, **base}

    def actions(self):
        """Return all available actions at this point in time."""
        if self.part:
            return self.part.actions()
        elif self.parts:
            return [("next", "Load the next part")]
        return []

    def action(self, key):
        """Perform an action"""
        if self.part:
            try:
                return self.part.action(key)
            except StopIteration:
                if self.parts:
                    self.part = self.parts.popleft()
                else:
                    self.part = None
            # except TypeError: #???
            #     self.part = self.parts.popleft()
        elif key == "next" and self.parts:
            self.part = self.parts.popleft()
        else:
            return None

    def buzz(self, who):
        if self.buzz_state in ("active", f"active-{who}"):
            if self.part:
                self.part.buzz(who)
            self.buzz_state = who
            return who
        else:
            raise PermissionError


class Part:
    def __init__(self, game):
        self.game = game
        self.task = None
        self.tasks = deque()

    def secrets(self):
        if self.task:
            return self.task.secrets()
        return {}

    def stage(self):
        if self.task:
            return self.task.stage()
        return {"bigscores": True}

    def actions(self):
        """Return all available actions at this point in time."""
        if self.task:
            return self.task.actions()
        return [("next", "Load the next task")]

    def action(self, key):
        """Perform an action"""
        if self.task:
            try:
                return self.task.action(key)
            except StopIteration:
                if self.tasks:
                    self.task = self.tasks.popleft()
                else:
                    self.task = None
        elif self.tasks:
            self.task = self.tasks.popleft()
        else:
            raise StopIteration  # out of tasks

    def buzz(self, who):
        if self.task and hasattr(self.task, "buzz"):
            self.task.buzz(who)


class MissingVowels(Part):
    def __init__(self, game):
        super().__init__(game)
        self.timer = None

    def load(self, part_data):
        groups = part_data["groups"]
        random.shuffle(groups)
        for group_data in groups:
            self.tasks.append(MissingVowelGroup(group_data, self))

    def action(self, key):
        if key == "next":
            if not self.timer:
                self.timer = Timer(2 * 60)
            if not self.timer.remaining and not self.task.clear:
                raise StopIteration
        return super().action(key)


class Connections(Part):
    def load(self, part_data):
        """Given part data, load questions or other tasks (theoretically)."""
        questions = part_data["questions"]
        random.shuffle(questions)
        for _, question_data in zip(range(6), questions):
            self.tasks.append(Question(question_data, self))


class Sequences(Part):
    def load(self, part_data):
        """Given part data, load questions or other tasks (theoretically)."""
        questions = part_data["questions"]
        random.shuffle(questions)
        for _, question_data in zip(range(6), questions):
            self.tasks.append(Question(question_data, self, is_sequences=True))


class Task:
    def __init__(self, task_data, part):
        self.part = part

    @property
    def game(self):
        return self.part.game


class MissingVowelGroup(Task):
    def __init__(self, task_data, part):
        self.part = part
        self.name = task_data["name"]
        self.phrases = deque(
            Phrase(phrase_data) for phrase_data in task_data["phrases"]
        )
        self.phrase = None
        self.clear = False

    @property
    def timer(self):
        return self.part.timer

    def secrets(self):
        if self.phrase:
            return {
                "explanation": self.phrase.answer,
            }
        return {}

    def stage(self):
        stage_data = {
            "time_remaining": self.timer and self.timer.remaining_round,
            "time_total": self.timer and self.timer.duration,
            "name": self.name,
        }
        if self.phrase:
            stage_data["phrase"] = (
                self.phrase.answer if self.clear else self.phrase.obfuscated
            )
        return stage_data

    def actions(self):
        if self.game.buzz_state in ("left", "right") and not self.clear:
            return [
                ("award_primary", "Give a point to the buzzing team"),
                ("punish_primary", "Take a point from the buzzing team"),
                ("award_secondary", "Give a point to the other team"),
                ("punish_secondary", "Take a point from the other team"),
            ]
        elif self.clear:
            return [("next", "Go to the next clue")]
        else:
            return [("next", "Resolve clue")]

    def action(self, key):
        if key not in [k for (k, _desc) in self.actions()]:
            return None
        if key == "next":
            if self.phrases and (not self.phrase or self.clear):
                self.phrase = self.phrases.popleft()
                self.clear = False
                self.game.buzz_state = "active"
            elif not self.clear:
                self.clear = True
            else:
                raise StopIteration("Out of steps")
        else:
            kind, _, team_id = key.partition("_")
            if team_id == "primary":
                team = self.game.buzz_state
            else:
                team = "right" if self.game.buzz_state == "left" else "left"
            self.game.points[team] += 1 if kind == "award" else -1


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

    @property
    def clear(self):
        return self.n_shown > 4

    def secrets(self):
        return {
            "step_explanations": [
                step.explanation for step in self.steps[: self.n_shown]
            ],
            "explanation": self.explanation,
        }

    def stage(self):
        if (
            self.timer
            and not self.timer.remaining
            and self.game.buzz_state != "inactive"
        ):
            self.game.buzz_state = "inactive"
        steps = [
            {
                key: getattr(step, key)
                for key in (
                    ("label", "type", "explanation")
                    if self.clear
                    else ("label", "type")
                )
            }
            for step in self.steps[: self.n_shown]
        ]
        if self.is_sequences and self.n_shown == 4:
            steps[-1] = {"label": "<span class='questionmark'>?</span>", "type": "text"}
        return {
            "steps": steps,
            "answer": self.answer if self.n_shown == 5 else None,
            "time_remaining": self.timer and self.timer.remaining_round,
            "time_total": self.timer and self.timer.duration,
            "clear": self.clear,
        }

    def actions(self):
        """Return all available actions at this point in time."""
        available = []
        if self.n_shown > 4:
            return [("next", "Go on to next question")]
        if not self.n_shown:
            available.extend(
                [
                    ("start_left", "Start question for left team"),
                    ("start_right", "Start question for right team"),
                ],
            )
        else:
            available.extend([("next", "Show the next clue")])
        if self.game.buzz_state in ("left", "right"):
            # can only award if they buzzed
            available.extend(
                [
                    ("award_primary", "Give points to primary team"),
                    ("award_bonus", "Give 1 point to other team"),
                    ("no_points", "No points for either team"),
                ],
            )
        if self.n_shown < 4 and self.timer and not self.timer.remaining:
            self.n_shown = 4
        if self.n_shown == 4 and self.timer and not self.timer.remaining:
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
            if not self.timer.remaining:
                raise PermissionError
            self.timer.freeze()
        # self.active_team = who  # shouldn't be neccessary

    def action(self, key):
        """Perform an action"""
        if key not in [k for (k, _desc) in self.actions()]:
            return None
        if key.startswith("start_"):
            _, __, team = key.partition("_")
            self.active_team = team
            self.n_shown += 1
            self.game.buzz_state = f"active-{team}"
            self.timer = Timer(30)
        elif key in ("award_primary", "award_bonus"):
            team = self.active_team
            if key == "award_primary":
                self.game.points[team] += {1: 5, 2: 3, 3: 2, 4: 1}[self.n_shown]
            else:
                self.game.points["left" if team == "right" else "right"] += 1
            self.n_shown = 5
            self.game.buzz_state = "inactive"
            self.active_team = None
        elif key == "no_points":
            self.n_shown = 5
            self.game.buzz_state = "inactive"
            self.active_team = None
        elif key == "next":
            if self.n_shown == 1:
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
    chars = [char for char in string.upper() if char not in "AEIOUÄÖÜ "]
    return "".join(
        char if not i or random.random() > 0.2 else f" {char}"
        for i, char in enumerate(chars)
    )


class Phrase:
    def __init__(self, phrase_data):
        if isinstance(phrase_data, str):
            # automatically obfuscate
            self.answer = phrase_data.upper()
            self.obfuscated = obfuscate(phrase_data)
        else:
            self.answer = phrase_data["answer"].upper()
            self.obfuscated = phrase_data["obfuscated"].upper()


class Step:
    def __init__(self, step_data):
        self.label = step_data["label"]
        self.explanation = step_data.get("explanation")
        self.type = step_data.get("type", "text")


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

GAME = Game()
