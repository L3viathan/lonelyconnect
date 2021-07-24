from collections import deque

class Game:
    def __init__(self):
        self.parts = deque()
        self.part = None

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
        return None # TODO: out of parts? End credits? or also in between parts?

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
            self.task = self.tasks.popleft()


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
        self.n_shown = 0

    def stage(self):
        return {
            "steps": [
                step.label
                for step in self.steps[:self.n_shown]
            ],
            "answer": self.answer if self.n_shown == 5 else None,
        }

    def __iter__(self):
        return self

    def __next__(self):
        if self.n_shown < 2:
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
