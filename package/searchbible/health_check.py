import os, traceback, json, pprint, wcwidth, textwrap, threading, time, subprocess, sys, re, pkg_resources, requests, shutil
import openai, tiktoken
from openai import OpenAI
from pygments.styles import get_style_by_name
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit import prompt
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from searchbible.utils.prompt_shared_key_bindings import prompt_shared_key_bindings
from searchbible import config
from searchbible.utils.shortcuts import createShortcuts
from pathlib import Path
from packaging import version


def check_openai_errors(func):
    def wrapper(*args, **kwargs):
        try: 
            return func(*args, **kwargs)
        except openai.APIError as e:
            print("Error: Issue on OpenAI side.")
            print("Solution: Retry your request after a brief wait and contact us if the issue persists.")
        except openai.APIConnectionError as e:
            print("Error: Issue connecting to our services.")
            print("Solution: Check your network settings, proxy configuration, SSL certificates, or firewall rules.")
        except openai.APITimeoutError as e:
            print("Error: Request timed out.")
            print("Solution: Retry your request after a brief wait and contact us if the issue persists.")
        except openai.AuthenticationError as e:
            print("Error: Your API key or token was invalid, expired, or revoked.")
            print("Solution: Check your API key or token and make sure it is correct and active. You may need to generate a new one from your account dashboard.")
            HealthCheck.changeAPIkey()
        except openai.BadRequestError as e:
            print("Error: Your request was malformed or missing some required parameters, such as a token or an input.")
            print("Solution: The error message should advise you on the specific error made. Check the [documentation](https://platform.openai.com/docs/api-reference/) for the specific API method you are calling and make sure you are sending valid and complete parameters. You may also need to check the encoding, format, or size of your request data.")
        except openai.ConflictError as e:
            print("Error: The resource was updated by another request.")
            print("Solution: Try to update the resource again and ensure no other requests are trying to update it.")
        except openai.InternalServerError as e:
            print("Error: Issue on OpenAI servers.")
            print("Solution: Retry your request after a brief wait and contact us if the issue persists. Check the [status page](https://status.openai.com).")
        except openai.NotFoundError as e:
            print("Error: Requested resource does not exist.")
            print("Solution: Ensure you are the correct resource identifier.")
        except openai.PermissionDeniedError as e:
            print("Error: You don't have access to the requested resource.")
            print("Solution: Ensure you are using the correct API key, organization ID, and resource ID.")
        except openai.RateLimitError as e:
            print("Error: You have hit your assigned rate limit.")
            print("Solution: Pace your requests. Read more in OpenAI [Rate limit guide](https://platform.openai.com/docs/guides/rate-limits).")
        except openai.UnprocessableEntityError as e:
            print("Error: Unable to process the request despite the format being correct.")
            print("Solution: Please try the request again.")
        except:
            print(traceback.format_exc())
    return wrapper

class HealthCheck:

    # token limit
    # reference: https://platform.openai.com/docs/models/gpt-4
    tokenLimits = {
        #"gpt-3.5-turbo-instruct": 4097,
        "gpt-3.5-turbo": 4097,
        "gpt-3.5-turbo-16k": 16385,
        "gpt-3.5-turbo-1106": 16385,
        "gpt-4-turbo-preview": 128000,
        "gpt-4-0125-preview": 128000,
        "gpt-4-1106-preview": 128000, # official 128,000; but "This model supports at most 4096 completion tokens"; set 8192 here to work with LetMeDoIt AI dynamic token feature
        #"gpt-4-vision-preview": 128,000, # used in plugin "analyze images"
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
    }

    models = tuple(tokenLimits.keys())

    @staticmethod
    def check():
        HealthCheck.checkPythonVersion()
        if config.autoUpgrade:
            HealthCheck.updateApp()
        if not hasattr(config, "openaiApiKey"):
            HealthCheck.setBasicConfig()
        createShortcuts()
        HealthCheck.setOsOpenCmd()
        #HealthCheck.checkPygame()

    @staticmethod
    def setBasicConfig(): # minimum config to work with standalone scripts built with AutoGen
        config.openaiApiKey = ''
        config.chatGPTApiModel = 'gpt-3.5-turbo-16k'
        config.chatGPTApiMaxTokens = 4000
        config.chatGPTApiMinTokens = 256
        config.llmTemperature = 0.8
        config.max_consecutive_auto_reply = 10
        config.exit_entry = '.exit'
        config.cancel_entry = '.cancel'
        config.terminalPromptIndicatorColor1 = "ansimagenta"
        config.terminalPromptIndicatorColor2 = "ansicyan"
        config.terminalCommandEntryColor1 = "ansiyellow"
        config.terminalCommandEntryColor2 = "ansigreen"
        config.terminalResourceLinkColor = "ansiyellow"
        config.terminalHeadingTextColor = "ansigreen"
        config.mouseSupport = False
        config.embeddingModel = "paraphrase-multilingual-mpnet-base-v2"
        config.max_agents = 5
        config.max_group_chat_round = 12
        config.max_consecutive_auto_reply = 10
        config.includeIpInSystemMessage = False
        config.wrapWords = True
        config.pygments_style = ""
        # work with bible verse parser
        config.noOfLinesPerChunkForParsing = 100
        config.parseEnglishBooksOnly = False
        config.useLiteVerseParsing = False
        config.standardAbbreviation = "ENG"
        config.convertChapterVerseDotSeparator = True
        config.parseBookChapterWithoutSpace = True
        config.parseBooklessReferences = True
        config.parseClearSpecialCharacters = False
        config.parserStandarisation = "NO"

    @staticmethod
    def setOsOpenCmd():
        if config.terminalEnableTermuxAPI:
            config.open = "termux-share"
        elif config.thisPlatform == "Linux":
            config.open = "xdg-open"
        elif config.thisPlatform == "Darwin":
            config.open = "open"
        elif config.thisPlatform == "Windows":
            config.open = "start"
        # name macOS
        if config.thisPlatform == "Darwin":
            config.thisPlatform = "macOS"

    @staticmethod
    def checkPygame():
        # try import pygame
        try:
            # hide pygame welcome message
            os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
            import pygame
            pygame.mixer.init()
            config.isPygameInstalled = True
        except:
            config.isPygameInstalled = False

    # automatic update
    config.pipIsUpdated = False
    def updateApp():
        thisPackage = "searchbible"
        #thisPackage = f"{package}_android" if config.isTermux else thisPackage
        print(f"Checking '{thisPackage}' version ...")
        installed_version = HealthCheck.getPackageInstalledVersion(thisPackage)
        if installed_version is None:
            print("Installed version information is not accessible!")
        else:
            print(f"Installed version: {installed_version}")
        latest_version = HealthCheck.getPackageLatestVersion(thisPackage)
        if latest_version is None:
            print("Latest version information is not accessible at the moment!")
        elif installed_version is not None:
            print(f"Latest version: {latest_version}")
            if latest_version > installed_version:
                if config.thisPlatform == "Windows":
                    print("Automatic upgrade feature is yet to be supported on Windows!")
                    print(f"Run 'pip install --upgrade {thisPackage}' to manually upgrade this app!")
                else:
                    try:
                        # delete old shortcut files
                        appName = "SearchBibleAI"
                        shortcutFiles = (f"{appName}.bat", f"{appName}.command", f"{appName}.desktop")
                        for shortcutFile in shortcutFiles:
                            shortcut = os.path.join(config.packageFolder, shortcutFile)
                            if os.path.isfile(shortcut):
                                os.remove(shortcut)
                        # upgrade package
                        HealthCheck.installmodule(f"--upgrade {thisPackage}")
                        HealthCheck.restartApp()
                    except:
                        print(f"Failed to upgrade '{thisPackage}'!")

    @staticmethod
    def getPackageInstalledVersion(package):
        try:
            installed_version = pkg_resources.get_distribution(package).version
            return version.parse(installed_version)
        except pkg_resources.DistributionNotFound:
            return None

    @staticmethod
    def getPackageLatestVersion(package):
        try:
            response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=10)
            latest_version = response.json()['info']['version']
            return version.parse(latest_version)
        except:
            return None

    @staticmethod
    def installmodule(module, update=True):
        #executablePath = os.path.dirname(sys.executable)
        #pippath = os.path.join(executablePath, "pip")
        #pip = pippath if os.path.isfile(pippath) else "pip"
        #pip3path = os.path.join(executablePath, "pip3")
        #pip3 = pip3path if os.path.isfile(pip3path) else "pip3"

        isInstalled, _ = subprocess.Popen("pip -V", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        pipInstallCommand = f"{sys.executable} -m pip install"

        if isInstalled:

            if update:
                if not config.pipIsUpdated:
                    pipFailedUpdated = "pip tool failed to be updated!"
                    try:
                        # Update pip tool in case it is too old
                        updatePip = subprocess.Popen(f"{pipInstallCommand} --upgrade pip", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        *_, stderr = updatePip.communicate()
                        if not stderr:
                            print("pip tool updated!")
                        else:
                            print(pipFailedUpdated)
                    except:
                        print(pipFailedUpdated)
                    config.pipIsUpdated = True
            try:
                upgrade = (module.startswith("-U ") or module.startswith("--upgrade "))
                if upgrade:
                    moduleName = re.sub("^[^ ]+? (.+?)$", r"\1", module)
                else:
                    moduleName = module
                print(f"{'Upgrading' if upgrade else 'Installing'} '{moduleName}' ...")
                installNewModule = subprocess.Popen(f"{pipInstallCommand} {module}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                *_, stderr = installNewModule.communicate()
                if not stderr:
                    print(f"Package '{moduleName}' {'upgraded' if upgrade else 'installed'}!")
                else:
                    print(f"Failed {'upgrading' if upgrade else 'installing'} package '{moduleName}'!")
                    if config.developer:
                        print(stderr)
                return True
            except:
                return False

        else:

            print("pip command is not found!")
            return False

    @staticmethod
    def checkPythonVersion():
        # requires python 3.8+; required by package 'tiktoken'
        pythonVersion = sys.version_info
        if pythonVersion < (3, 8):
            print("Python version higher than 3.8 is required!")
            print("Closing ...")
            exit(1)
        elif pythonVersion >= (3, 12):
            print("Some features may not work with python version newer than 3.11!")

    @staticmethod
    def setSharedItems():
        config.storagedirectory = HealthCheck.getFiles()
        config.excludeConfigList = []
        config.divider = "--------------------"
        # share frequently used methods in config to avoid circular imports
        if not hasattr(config, "print"):
            config.print = HealthCheck.print
        if not hasattr(config, "print2"):
            config.print2 = HealthCheck.print2
        if not hasattr(config, "print3"):
            config.print3 = HealthCheck.print3
        if not hasattr(config, "print4"):
            config.print4 = HealthCheck.print4
        if not hasattr(config, "restartApp"):
            config.restartApp = HealthCheck.restartApp
        if not hasattr(config, "isPackageInstalled"):
            config.isPackageInstalled = HealthCheck.isPackageInstalled
        if not hasattr(config, "saveConfig"):
            config.saveConfig = HealthCheck.saveConfig

    @staticmethod
    def set_log_file_max_lines(log_file, max_lines):
        if os.path.isfile(log_file):
            # Read the contents of the log file
            with open(log_file, "r", encoding="utf-8") as fileObj:
                lines = fileObj.readlines()
            # Count the number of lines in the file
            num_lines = len(lines)
            if num_lines > max_lines:
                # Calculate the number of lines to be deleted
                num_lines_to_delete = num_lines - max_lines
                if num_lines_to_delete > 0:
                    # Open the log file in write mode and truncate it
                    with open(log_file, "w", encoding="utf-8") as fileObj:
                        # Write the remaining lines back to the log file
                        fileObj.writelines(lines[num_lines_to_delete:])
                filename = os.path.basename(log_file)
                HealthCheck.print3(f"Number of old lines deleted from log file '{filename}': {num_lines_to_delete}")

    @staticmethod
    def saveConfig():
        with open(os.path.join(config.packageFolder, "config.py"), "w", encoding="utf-8") as fileObj:
            for name in dir(config):
                excludeConfigList = [
                    "selectAll",
                    "open",
                    "read_suggestions",
                    "currentVerses",
                    "mainFile",
                    "packageFolder",
                    "thisPlatform",
                    "divider",
                    "pipIsUpdated",
                    "isPygameInstalled",
                    "clipboard",
                    "multilineInput",
                    "promptStyle1",
                    "promptStyle2",
                    "terminalColors",
                    "addPathAt",
                    "defaultEntry",
                    "predefinedContextTemp",
                    "pagerContent",
                    "new_chat_response",
                    "currentMessages",
                    "tempChunk",
                ]
                excludeConfigList = excludeConfigList + config.excludeConfigList
                if not name.startswith("__") and not name in excludeConfigList:
                    try:
                        value = eval(f"config.{name}")
                        if not callable(value) and not str(value).startswith("<"):
                            fileObj.write("{0} = {1}\n".format(name, pprint.pformat(value)))
                    except:
                        pass

    @staticmethod
    def restartApp():
        HealthCheck.print2(f"Restarting Search Bible AI ...")
        os.system(f"{sys.executable} {config.mainFile}")
        exit(0)

    @staticmethod
    def isPackageInstalled(package):
        return True if shutil.which(package.split(" ", 1)[0]) else False

    @staticmethod
    def getFiles():
        # option 1: config.storagedirectory; user custom folder
        if not hasattr(config, "storagedirectory") or (config.storagedirectory and not os.path.isdir(config.storagedirectory)):
            config.storagedirectory = ""
        if config.storagedirectory:
            return config.storagedirectory
        # option 2: defaultStorageDir; located in user home directory
        defaultStorageDir = os.path.join(os.path.expanduser('~'), "searchbible")
        try:
            Path(defaultStorageDir).mkdir(parents=True, exist_ok=True)
        except:
            pass
        if os.path.isdir(defaultStorageDir):
            return defaultStorageDir
        # option 3: directory "files" in app directory; to be deleted on every upgrade
        else:
            return os.path.join(config.packageFolder, "files")

    @staticmethod
    def getCliOutput(cli):
        try:
            process = subprocess.Popen(cli, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, *_ = process.communicate()
            return stdout.decode("utf-8")
        except:
            return ""

    def getClipboardText():
        if not hasattr(config, "clipboard"):
            config.clipboard = PyperclipClipboard()
        return HealthCheck.getCliOutput("termux-clipboard-get") if config.terminalEnableTermuxAPI else config.clipboard.get_data().text

    @staticmethod
    def spinning_animation(stop_event):
        while not stop_event.is_set():
            for symbol in "|/-\\":
                print(symbol, end="\r")
                time.sleep(0.1)
        #print("\r", end="")
        #print(" ", end="")

    @staticmethod
    def startSpinning():
        config.stop_event = threading.Event()
        config.spinner_thread = threading.Thread(target=HealthCheck.spinning_animation, args=(config.stop_event,))
        config.spinner_thread.start()

    @staticmethod
    def stopSpinning():
        try:
            config.stop_event.set()
            config.spinner_thread.join()
        except:
            pass

    @staticmethod
    def simplePrompt(inputIndicator="", validator=None, default="", accept_default=False, completer=None, promptSession=None, style=None, is_password=False, bottom_toolbar=None, custom_key_bindings=None):
        this_key_bindings = KeyBindings()

        @this_key_bindings.add("c-q")
        def _(event):
            buffer = event.app.current_buffer
            buffer.text = config.exit_entry
            buffer.validate_and_handle()

        available_key_bindings = [
            this_key_bindings,
            prompt_shared_key_bindings,
        ]
        if custom_key_bindings:
            available_key_bindings.append(custom_key_bindings)
        this_key_bindings = merge_key_bindings(available_key_bindings)

        config.selectAll = False
        inputPrompt = promptSession.prompt if promptSession is not None else prompt
        if not hasattr(config, "clipboard"):
            config.clipboard = PyperclipClipboard()
        if not inputIndicator:
            inputIndicator = [
                ("class:indicator", ">>> "),
            ]
        userInput = inputPrompt(
            inputIndicator,
            key_bindings=this_key_bindings,
            bottom_toolbar=bottom_toolbar if bottom_toolbar is not None else f" [ctrl+q] {config.exit_entry}",
            #enable_system_prompt=True,
            swap_light_and_dark_colors=Condition(lambda: not config.terminalResourceLinkColor.startswith("ansibright")),
            style=style,
            validator=validator,
            #multiline=Condition(lambda: config.multilineInput),
            default=default,
            accept_default=accept_default,
            completer=completer,
            is_password=is_password,
            mouse_support=Condition(lambda: config.mouseSupport),
            clipboard=config.clipboard,
        )
        userInput = textwrap.dedent(userInput) # dedent to work with code block
        return userInput if hasattr(config, "addPathAt") and config.addPathAt else userInput.strip()

    @staticmethod
    def getStringWidth(text):
        width = 0
        for character in text:
            width += wcwidth.wcwidth(character)
        return width

    @staticmethod
    def getPygmentsStyle():
        theme = config.pygments_style if hasattr(config, "pygments_style") and config.pygments_style else "stata-dark" if not config.terminalResourceLinkColor.startswith("ansibright") else "stata-light"
        return style_from_pygments_cls(get_style_by_name(theme))

    @staticmethod
    def print(content):
        print_formatted_text(HTML(content))

    @staticmethod
    def print2(content):
        print_formatted_text(HTML(f"<{config.terminalPromptIndicatorColor2}>{content}</{config.terminalPromptIndicatorColor2}>"))

    @staticmethod
    def print3(content):
        splittedContent = content.split(": ", 1)
        if len(splittedContent) == 2:
            key, value = splittedContent
            print_formatted_text(HTML(f"<{config.terminalPromptIndicatorColor2}>{key}:</{config.terminalPromptIndicatorColor2}> {value}"))
        else:
            config.print2(splittedContent)

    @staticmethod
    def print4(content):
        splittedContent = content.split(") ", 1)
        if len(splittedContent) == 2:
            key, value = splittedContent
            print_formatted_text(HTML(f"<{config.terminalPromptIndicatorColor2}>{key})</{config.terminalPromptIndicatorColor2}> {value}"))
        else:
            config.print2(splittedContent)

    @staticmethod
    def getEmbeddingFunction(embeddingModel=None):
        # import statement is placed here to make this file compatible on Android
        from chromadb.utils import embedding_functions
        embeddingModel = embeddingModel if embeddingModel is not None else config.embeddingModel
        if embeddingModel == "text-embedding-ada-002":
            return embedding_functions.OpenAIEmbeddingFunction(api_key=config.openaiApiKey, model_name="text-embedding-ada-002")
        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embeddingModel) # support custom Sentence Transformer Embedding models by modifying config.embeddingModel

    @staticmethod
    def changeAPIkey():
        print("Enter your OpenAI API Key [required]:")
        apikey = prompt(default=config.openaiApiKey, is_password=True)
        if apikey and not apikey.strip().lower() in (config.cancel_entry, config.exit_entry):
            config.openaiApiKey = apikey
        #HealthCheck.checkCompletion()

    @staticmethod
    @check_openai_errors
    def checkCompletion():
        # instantiate a client that can shared with plugins
        os.environ["OPENAI_API_KEY"] = config.openaiApiKey
        client = OpenAI()
        client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content" : "hello"}],
            n=1,
            max_tokens=10,
        )
        # set variable 'OAI_CONFIG_LIST' to work with pyautogen
        oai_config_list = []
        for model in HealthCheck.models:
            oai_config_list.append({"model": model, "api_key": config.openaiApiKey})
        os.environ["OAI_CONFIG_LIST"] = json.dumps(oai_config_list)

    # The following method was modified from source:
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    @staticmethod
    def count_tokens_from_messages(messages, model=""):
        if not model:
            model = config.chatGPTApiModel

        """Return the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            print("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        if model in {
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-0613",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-16k-0613",
                "gpt-4-1106-preview",
                "gpt-4-0314",
                "gpt-4-32k-0314",
                "gpt-4",
                "gpt-4-0613",
                "gpt-4-32k",
                "gpt-4-32k-0613",
            }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "gpt-3.5-turbo" in model:
            #print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
            return HealthCheck.count_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
        elif "gpt-4" in model:
            #print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
            return HealthCheck.count_tokens_from_messages(messages, model="gpt-4-0613")
        else:
            raise NotImplementedError(
                f"""count_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            if not "content" in message or not message.get("content", ""):
                num_tokens += len(encoding.encode(str(message)))
            else:
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":
                        num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens