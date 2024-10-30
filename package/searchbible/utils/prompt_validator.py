from searchbible import config
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.application import run_in_terminal
#from prompt_toolkit.application import get_app
import re


class RegexValidator(Validator):
    def __init__(self, pattern=""):
        super().__init__()
        self.filter = pattern # e.g. "^[0-9|]*?$"

    def validate(self, document):
        text = document.text

        if re.search(self.filter, text) or text.lower() in (config.exit_entry, config.cancel_entry):
            pass
        else:
            raise ValidationError(message='This entry accepts numbers only!', cursor_position=len(text)-1)


class NumberValidator(Validator):
    def validate(self, document):
        text = document.text

        if text.lower() in (config.exit_entry, config.cancel_entry):
            pass
        elif text and not text.isdigit():
            i = 0

            # Get index of first non numeric character.
            # We want to move the cursor here.
            for i, c in enumerate(text):
                if not c.isdigit():
                    break

            raise ValidationError(message='This entry accepts numbers only!', cursor_position=i)


class FloatValidator(Validator):
    def validate(self, document):
        text = document.text

        if text.lower() in (config.exit_entry, config.cancel_entry):
            pass
        try:
            float(text)
        except:
            raise ValidationError(message='This entry accepts floating point numbers only!', cursor_position=0)


class NoAlphaValidator(Validator):
    def validate(self, document):
        text = document.text

        if text.lower() in (config.exit_entry, config.cancel_entry):
            pass
        elif text and text.isalpha():
            i = 0

            # Get index of first non numeric character.
            # We want to move the cursor here.
            for i, c in enumerate(text):
                if c.isalpha():
                    break

            raise ValidationError(message='This entry does not accept alphabet letters!', cursor_position=i)