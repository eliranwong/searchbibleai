import vertexai, os, traceback, argparse
from vertexai.preview.generative_models import GenerativeModel
from vertexai.generative_models._generative_models import (
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
)
from searchbible import config
from searchbible.utils.bible_studies import bible_study_suggestions
from searchbible.utils.streaming_word_wrapper import StreamingWordWrapper
from searchbible.health_check import HealthCheck
if not hasattr(config, "exit_entry"):
    HealthCheck.setBasicConfig()
    HealthCheck.saveConfig()
    print("Updated!")
#HealthCheck.setPrint()
from prompt_toolkit.styles import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path
import threading


# Install google-cloud-aiplatform FIRST!
#!pip install --upgrade google-cloud-aiplatform


class GeminiPro:

    def __init__(self, name="Gemini Pro", temperature=0.9, max_output_tokens=8192):
        # authentication
        authpath1 = os.path.join(HealthCheck.getFiles(), "credentials_googleaistudio.json")
        if os.path.isfile(authpath1):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = authpath1
            self.runnable = True
        else:
            print(f"API key json file '{authpath1}' not found!")
            print("Read https://github.com/eliranwong/letmedoit/wiki/Google-API-Setup for setting up Google API.")
            self.runnable = False
        # initiation
        vertexai.init()
        self.name, self.temperature = name, temperature
        self.generation_config=GenerationConfig(
            temperature=temperature, # 0.0-1.0; default 0.9
            max_output_tokens=max_output_tokens, # default
            candidate_count=1,
        )
        self.safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        }
        self.defaultPrompt = ""
        #self.enableVision = (os.path.realpath(__file__).endswith("vision.py"))

    def run(self, prompt=""):
        completer = WordCompleter(
            bible_study_suggestions + config.read_suggestions,
            ignore_case=True,
            sentence=True,
        )
        custom_key_bindings = KeyBindings()

        @custom_key_bindings.add("c-n")
        def _(event):
            buffer = event.app.current_buffer
            buffer.text = ".new"
            buffer.validate_and_handle()

        if self.defaultPrompt:
            prompt, self.defaultPrompt = self.defaultPrompt, ""
        historyFolder = os.path.join(HealthCheck.getFiles(), "history")
        Path(historyFolder).mkdir(parents=True, exist_ok=True)
        chat_history = os.path.join(historyFolder, "geminipro")
        chat_session = PromptSession(history=FileHistory(chat_history))

        promptStyle = Style.from_dict({
            # User input (default text).
            "": config.terminalCommandEntryColor2,
            # Prompt.
            "indicator": config.terminalPromptIndicatorColor2,
        })

        #completer = WordCompleter(["[", "[NO_FUNCTION_CALL]"], ignore_case=True) if self.enableVision else None

        if not self.runnable:
            print(f"{self.name} is not running due to missing configurations!")
            return None
        model = GenerativeModel("gemini-pro")
        chat = model.start_chat(
            #context=f"You're {self.name}, a helpful AI assistant.",
        )
        #HealthCheck.print2(f"\n{self.name} + Vision loaded!" if self.enableVision else f"\n{self.name} loaded!")
        HealthCheck.print2(f"\n{self.name} loaded!")
        print("(To start a new chart, enter '.new')")
        print(f"(To quit, enter '{config.exit_entry}')\n")
        while True:
            if not prompt:
                prompt = HealthCheck.simplePrompt(
                    style=promptStyle,
                    promptSession=chat_session,
                    completer=completer,
                    custom_key_bindings=custom_key_bindings,
                    bottom_toolbar=" [ctrl+q] exit [ctrl+n] new chat ",
                )
                if prompt and not prompt in (".new", config.exit_entry) and hasattr(config, "currentMessages"):
                    config.currentMessages.append({"content": prompt, "role": "user"})
            else:
                prompt = HealthCheck.simplePrompt(
                    style=promptStyle,
                    promptSession=chat_session,
                    completer=completer,
                    custom_key_bindings=custom_key_bindings,
                    bottom_toolbar=" [ctrl+q] exit [ctrl+n] new chat ",
                    default=prompt,
                )
            if prompt == config.exit_entry:
                break
            elif prompt == ".new":
                clear()
                chat = model.start_chat()
                print("New chat started!")
            elif prompt := prompt.strip():
                streamingWordWrapper = StreamingWordWrapper()
                config.pagerContent = ""
                #self.addPagerContent = True

                # declare a function
#                get_vision_func = generative_models.FunctionDeclaration(
#                    name="analyze_images",
#                    description="Describe or analyze images. Remember, do not use this function for non-image related tasks. Even it is an image-related task, use this function ONLY if I provide at least one image file path or image url.",
#                    parameters={
#                        "type": "object",
#                        "properties": {
#                            "query": {
#                                "type": "string",
#                                "description": "Questions or requests that users ask about the given images",
#                            },
#                            "files": {
#                                "type": "string",
#                                "description": """Return a list of image paths or urls, e.g. '["image1.png", "/tmp/image2.png", "https://letmedoit.ai/image.png"]'. Return '[]' if image path is not provided.""",
#                            },
#                        },
#                        "required": ["query", "files"],
#                    },
#                )
#                vision_tool = generative_models.Tool(
#                    function_declarations=[get_vision_func],
#                )

                try:
                    # https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini
                    # Note: At the time of writing, function call feature with Gemini Pro is very weak, compared with the function call feature offerred by ChatGPT:
                    # 1. Gemini Pro do not accept multiple tools in a single message
                    # 2. Gemini Pro is weak to determine if it is appropriate to use the given tool or not.  When a tool is given, it is called by mistake so often.  In contrast, ChatGPT has the "auto" setting which makes ChatGPT obviously smarter than Gemini Pro.
                    #if "[NO_FUNCTION_CALL]" in prompt or not self.enableVision:
                    #    allow_function_call = False
                    #    prompt = prompt.replace("[NO_FUNCTION_CALL]", "")
                    #else:
                    #    allow_function_call = True
                    completion = chat.send_message(
                        prompt,
                        # Optional:
                        generation_config=self.generation_config,
                        safety_settings=self.safety_settings,
                        #tools=[vision_tool] if allow_function_call else None,
                        stream=True,
                    )

                    # Create a new thread for the streaming task
                    streaming_event = threading.Event()
                    self.streaming_thread = threading.Thread(target=streamingWordWrapper.streamOutputs, args=(streaming_event, completion,))
                    # Start the streaming thread
                    self.streaming_thread.start()

                    # wait while text output is steaming; capture key combo 'ctrl+q' or 'ctrl+z' to stop the streaming
                    streamingWordWrapper.keyToStopStreaming(streaming_event)

                    # when streaming is done or when user press "ctrl+q"
                    self.streaming_thread.join()

                    # format response when streaming is not applied
                    #tokens = list(pygments.lex(fullContent, lexer=MarkdownLexer()))
                    #print_formatted_text(PygmentsTokens(tokens), style=HealthCheck.getPygmentsStyle())

                except:
                    self.streaming_thread.join()
                    HealthCheck.print2(traceback.format_exc())

            prompt = ""

        HealthCheck.print2(f"\n{self.name} closed!")

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="geminipro cli options")
    # Add arguments
    parser.add_argument("default", nargs="?", default=None, help="default entry")
    parser.add_argument('-o', '--outputtokens', action='store', dest='outputtokens', help="specify maximum output tokens with -o flag; default: 8192")
    parser.add_argument('-t', '--temperature', action='store', dest='temperature', help="specify temperature with -t flag: default: 0.9")
    # Parse arguments
    args = parser.parse_args()
    # Get options
    prompt = args.default.strip() if args.default and args.default.strip() else ""
    if args.outputtokens and args.outputtokens.strip():
        try:
            max_output_tokens = int(args.outputtokens.strip())
        except:
            max_output_tokens = 8192
    else:
        max_output_tokens = 8192
    if args.temperature and args.temperature.strip():
        try:
            temperature = float(args.temperature.strip())
        except:
            temperature = 0.9
    else:
        temperature = 0.9
    GeminiPro(
        temperature=temperature,
        max_output_tokens = max_output_tokens,
    ).run(
        prompt=prompt,
    )

if __name__ == '__main__':
    main()