import pydoc, textwrap
from searchbible import config
from searchbible.utils.prompt_shared_key_bindings import prompt_shared_key_bindings
from searchbible.utils.prompt_multiline_shared_key_bindings import prompt_multiline_shared_key_bindings
from searchbible.utils.prompt_validator import NumberValidator
from prompt_toolkit import prompt
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings, ConditionalKeyBindings
from prompt_toolkit.shortcuts import set_title
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard

class Prompts:

    def __init__(self, custom_key_bindings=None):
        self.custom_key_bindings = custom_key_bindings
        config.multilineInput = False
        config.clipboard = PyperclipClipboard()
        config.promptStyle1 = self.promptStyle1 = Style.from_dict({
            # User input (default text).
            "": config.terminalCommandEntryColor1,
            # Prompt.
            "indicator": config.terminalPromptIndicatorColor1,
        })
        config.promptStyle2 = self.promptStyle2 = Style.from_dict({
            # User input (default text).
            "": config.terminalCommandEntryColor2,
            # Prompt.
            "indicator": config.terminalPromptIndicatorColor2,
        })
        self.inputIndicator = [
            ("class:indicator", ">>> "),
        ]
        self.shareKeyBindings()
        config.showKeyBindings = self.showKeyBindings
        config.terminalColors = {
            "ansidefault": "ansidefault",
            "ansiblack": "ansiwhite",
            "ansired": "ansibrightred",
            "ansigreen": "ansibrightgreen",
            "ansiyellow": "ansibrightyellow",
            "ansiblue": "ansibrightblue",
            "ansimagenta": "ansibrightmagenta",
            "ansicyan": "ansibrightcyan",
            "ansigray": "ansibrightblack",
            "ansiwhite": "ansiblack",
            "ansibrightred": "ansired",
            "ansibrightgreen": "ansigreen",
            "ansibrightyellow": "ansiyellow",
            "ansibrightblue": "ansiblue",
            "ansibrightmagenta": "ansimagenta",
            "ansibrightcyan": "ansicyan",
            "ansibrightblack": "ansigray",
        }

    def getToolBar(self, multiline=False):
        if multiline:
            return f" [ctrl+q] exit [escape+enter] send "
        return f" [ctrl+q] exit [enter] send "

    def shareKeyBindings(self):
        this_key_bindings = KeyBindings()
        @this_key_bindings.add("c-q")
        def _(event):
            buffer = event.app.current_buffer
            buffer.text = config.exit_entry
            buffer.validate_and_handle()
        #@this_key_bindings.add("c-y")
        #def _(event):
        #    buffer = event.app.current_buffer
        #    config.predefinedContextTemp = config.predefinedContext
        #    config.predefinedContext = "[none]"
        #    buffer.text = ".new"
        #    buffer.validate_and_handle()
        #    run_in_terminal(lambda: config.print3("Predefined context temporarily changed to: [none]"))
        #@this_key_bindings.add("c-s")
        #def _(event):
        #    buffer = event.app.current_buffer
        #    buffer.text = ".save"
        #    buffer.validate_and_handle()
        #@this_key_bindings.add("c-g")
        #def _(_):
        #    config.launchPager()
        @this_key_bindings.add("escape", "d")
        def _(_):
            config.developer = not config.developer
            config.saveConfig()
            run_in_terminal(lambda: config.print3(f"Developer mode: {'enabled' if config.developer else 'disabled'}!"))
        @this_key_bindings.add("c-l")
        def _(_):
            config.toggleMultiline()
        #@this_key_bindings.add("c-o")
        #def _(event):
        #    buffer = event.app.current_buffer
        #    config.defaultEntry = buffer.text
        #    event.app.current_buffer.text = ".context"
        #    event.app.current_buffer.validate_and_handle()
        @this_key_bindings.add("c-k")
        def _(_):
            run_in_terminal(self.showKeyBindings)
        @this_key_bindings.add("escape", "r")
        def _(_):
            print(f"Restarting Search Bible AI ...")
            config.restartApp()
        @this_key_bindings.add("c-w")
        def _(_):
            config.wrapWords = not config.wrapWords
            config.saveConfig()
            run_in_terminal(lambda: config.print3(f"Word Wrap: '{'enabled' if config.wrapWords else 'disabled'}'!"))
        @this_key_bindings.add("escape", "m")
        def _(_):
            config.mouseSupport = not config.mouseSupport
            config.saveConfig()
            run_in_terminal(lambda: config.print3(f"Entry Mouse Support: '{'enabled' if config.mouseSupport else 'disabled'}'!"))

        conditional_prompt_multiline_shared_key_bindings = ConditionalKeyBindings(
            key_bindings=prompt_multiline_shared_key_bindings,
            filter=Condition(lambda: config.multilineInput),
        )
        available_key_bindings = [
            this_key_bindings,
            conditional_prompt_multiline_shared_key_bindings,
            prompt_shared_key_bindings,
        ]
        if self.custom_key_bindings:
            available_key_bindings.append(self.custom_key_bindings)
        self.prompt_shared_key_bindings = merge_key_bindings(available_key_bindings)

    def showKeyBindings(self):
        bindings = {
            "ctrl+q": "quit / exit current feature",
            "ctrl+z": "cancel",
            "ctrl+a": "select / unselect all",
            "ctrl+c": "copy [w/ mouse support]",
            "ctrl+v": "paste [w/ mouse support]",
            "ctrl+x": "cut [w/ mouse support]",
            #"ctrl+n": "new chat",
            #"ctrl+y": "new chat without context",
            #"ctrl+s": "save chat",
            #"ctrl+o": "change predefined context",
            #"ctrl+g": "pager view",
            "ctrl+d": "forward delete",
            "ctrl+h": "backspace",
            #"ctrl+e": "swap command execution mode",
            "ctrl+k": "show key bindings",
            "ctrl+l": "toggle multi-line entry",
            #"ctrl+b": "toggle input audio",
            #"ctrl+p": "toggle response audio",
            "ctrl+w": "toggle word wrap",
            "ctrl+r": "insert a linebreak",
            #"ctrl+i or tab": "insert a file or folder path",
            #"shift+tab": f"insert '{config.terminalEditorTabText}' [configurable]",
            #"esc+f": "display device information",
            #"esc+c": "count current message tokens",
            #"esc+i": "toggle improved writing feature",
            "esc+m": "toggle mouse support",
            #"esc+t": "system command prompt",
            "esc+b": "move cursor to line beginning",
            "esc+e": "move cursor to line end",
            "esc+a": "move cursor to entry beginning",
            "esc+z": "move cursor to entry end",
            "esc+s": "swap text brightness",
            "esc+d": "swap developer mode",
            "esc+r": "restart SearchBibleAI",
        }
        textEditor = config.customTextEditor.split(" ", 1)[0]
        bindings["ctrl+e"] = f"""edit current input with '{config.customTextEditor if textEditor and config.isPackageInstalled(textEditor) else "eTextEdit"}'"""
        bindings["esc+p"] = f"""edit the previous response with '{config.customTextEditor if textEditor and config.isPackageInstalled(textEditor) else "eTextEdit"}'"""
        multilineBindings = {
            "enter": "new line",
            "esc+enter": "complete entry",
            "esc+1": "go up 10 lines",
            "esc+2": "go up 20 lines",
            "esc+3": "go up 30 lines",
            "esc+4": "go up 40 lines",
            "esc+5": "go up 50 lines",
            "esc+6": "go up 60 lines",
            "esc+7": "go up 70 lines",
            "esc+8": "go up 80 lines",
            "esc+9": "go up 90 lines",
            "esc+0": "go up 100 lines",
            "f1": "go down 10 lines",
            "f2": "go down 20 lines",
            "f3": "go down 30 lines",
            "f4": "go down 40 lines",
            "f5": "go down 50 lines",
            "f6": "go down 60 lines",
            "f7": "go down 70 lines",
            "f8": "go down 80 lines",
            "f9": "go down 90 lines",
            "f10": "go down 100 lines",
            "ctrl+u": f"go up '{config.terminalEditorScrollLineCount}' lines [configurable]",
            "ctrl+j": f"go down '{config.terminalEditorScrollLineCount}' lines [configurable]",
        }
        keyHelp = f"{config.divider}\n"
        keyHelp += "# Key Bindings\n"
        keyHelp += "[blank]: launch action menu\n"
        for key, value in bindings.items():
            keyHelp += f"{key}: {value}\n"
        keyHelp += "\n## Key Bindings\n[for multiline entry only]\n"
        for key, value in multilineBindings.items():
            keyHelp += f"{key}: {value}\n"
        keyHelp += f"{config.divider}\n"

        if config.isPackageInstalled("less"):
            pydoc.pipepager(f"To close this help page, press 'q'\n\n{keyHelp}\nTo close this help page, press 'q'", cmd='less -R')
        else:
            print(keyHelp)

    def simplePrompt(self, numberOnly=False, validator=None, inputIndicator="", default="", accept_default=False, completer=None, promptSession=None, style=None, is_password=False, bottom_toolbar=None):
        config.selectAll = False
        inputPrompt = promptSession.prompt if promptSession is not None else prompt
        if not inputIndicator:
            inputIndicator = self.inputIndicator
        if numberOnly:
            validator = NumberValidator()
        userInput = inputPrompt(
            inputIndicator,
            key_bindings=self.prompt_shared_key_bindings,
            bottom_toolbar=self.getToolBar(config.multilineInput) if bottom_toolbar is None else bottom_toolbar,
            #enable_system_prompt=True,
            swap_light_and_dark_colors=Condition(lambda: not config.terminalResourceLinkColor.startswith("ansibright")),
            style=self.promptStyle1 if style is None else style,
            validator=validator,
            multiline=Condition(lambda: config.multilineInput),
            default=default,
            accept_default=accept_default,
            completer=completer,
            is_password=is_password,
            mouse_support=Condition(lambda: config.mouseSupport),
            clipboard=config.clipboard,
        )
        userInput = textwrap.dedent(userInput) # dedent to work with code block
        return userInput if hasattr(config, "addPathAt") and config.addPathAt else userInput.strip()
