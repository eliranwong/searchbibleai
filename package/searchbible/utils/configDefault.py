from searchbible import config
import pprint, os, shutil
from prompt_toolkit.shortcuts import yes_no_dialog

def setConfig(defaultSettings, thisTranslation={}, temporary=False):
    for key, value in defaultSettings:
        if not hasattr(config, key):
            value = pprint.pformat(value)
            exec(f"""config.{key} = {value} """)
            if temporary:
                config.excludeConfigList.append(key)
    if thisTranslation:
        for i in thisTranslation:
            if not i in config.thisTranslation:
                config.thisTranslation[i] = thisTranslation[i]

defaultSettings = (
    ('aiSystemMessage', "You're an expert on the Bible.\nPlease respond to all my inquiries with spiritual insights and informed knowledge regarding biblical teachings.\nPlease always strive to maintain an engaging and continuous conversation.\n"),
    ('thisTranslation', {}),
    ('cancel_entry', '.cancel'),
    ('exit_entry', '.exit'),
    ('terminalHeadingTextColor', 'ansigreen'),
    ('terminalResourceLinkColor', 'ansiyellow'),
    ('terminalCommandEntryColor1', 'ansiyellow'),
    ('terminalPromptIndicatorColor1', 'ansimagenta'),
    ('terminalCommandEntryColor2', 'ansigreen'),
    ('terminalPromptIndicatorColor2', 'ansicyan'),
    ('terminalSearchHighlightBackground', 'ansiblue'),
    ('terminalSearchHighlightForeground', 'ansidefault'),
    ('embeddingModel', 'paraphrase-multilingual-mpnet-base-v2'),
    ('customTextEditor', ""), # e.g. 'micro -softwrap true -wordwrap true'; built-in text editor eTextEdit is used when it is not defined.
    ('pagerView', False),
    #('usePygame', True),
    ('wrapWords', True),
    ('mouseSupport', False),
    ('autoUpgrade', True),
    ('chatGPTApiModel', 'gpt-3.5-turbo-16k'),
    ('chatGPTApiMaxTokens', 2000),
    ('chatGPTApiMinTokens', 256),
    ('llmTemperature', 0.8),
    ('openaiApiKey', ''),
    ('openaiApiOrganization', ''),
    ('predefinedContext', '[none]'),
    ('customPredefinedContext', ''),
    ('applyPredefinedContextAlways', False), # True: apply predefined context with all use inputs; False: apply predefined context only in the beginning of the conversation
    ('pygments_style', ''),
    ('developer', False),
 
    ("mainText", "NET"),
    ("mainB", 43),
    ("mainC", 3),
    ("mainV", 16),
    ("enableCaseSensitiveSearch", False),
    ("noWordWrapBibles", []), # some bibles display better, without word wrap feature, e.g. CUV
    ("chapterParagraphsAndSubheadings", True),

    ('terminalEnableTermuxAPI', False),
    ('terminalEditorScrollLineCount', 20),
    ('terminalEditorTabText', "    "),
    ('blankEntryAction', "..."),
    ('storagedirectory', ""),
    ('vlcSpeed', 1.0),
    ('gcttsLang', "en-GB"),
    ('gcttsSpeed', 1.0),
    ('gttsLang', "en"), # gTTS is used by default if ttsCommand is not given
    ('gttsTld', ""), # https://gtts.readthedocs.io/en/latest/module.html#languages-gtts-lang
    ('ttsCommand', ""), # ttsCommand is used if it is given; offline tts engine runs faster; on macOS [suggested speak rate: 100-300], e.g. "say -r 200 -v Daniel"; on Ubuntu [espeak; speed in approximate words per minute; 175 by default], e.g. "espeak -s 175 -v en"; remarks: always place the voice option, if any, at the end
    ('ttsCommandSuffix', ""), # try on Windows; ttsComand = '''Add-Type -TypeDefinition 'using System.Speech.Synthesis; class TTS { static void Main(string[] args) { using (SpeechSynthesizer synth = new SpeechSynthesizer()) { synth.Speak(args[0]); } } }'; [TTS]::Main('''; ttsCommandSuffix = ")"; a full example is Add-Type -TypeDefinition 'using System.Speech.Synthesis; class TTS { static void Main(string[] args) { using (SpeechSynthesizer synth = new SpeechSynthesizer()) { synth.Speak(args[0]); } } }'; [TTS]::Main("Text to be read")
    ("ttsLanguages", ["en", "en-gb", "en-us", "zh", "yue", "el"]), # users can edit this item in config.py to support more or less languages
    ("ttsLanguagesCommandMap", {"en": "", "en-gb": "", "en-us": "", "zh": "", "yue": "", "el": "",}), # advanced users need to edit this item manually to support different voices with customised tts command, e.g. ttsCommand set to "say -r 200 -v Daniel" and ttsLanguagesCommandMap set to {"en": "Daniel", "en-gb": "Daniel", "en-us": "", "zh": "", "yue": "", "el": "",}

    ('noOfLinesPerChunkForParsing', 100),
    ('parseEnglishBooksOnly', False),
    ('useLiteVerseParsing', False),
    ('standardAbbreviation', "ENG"),
    ('convertChapterVerseDotSeparator', True),
    ('parseBookChapterWithoutSpace', True),
    ('parseBooklessReferences', True),
    ('parseClearSpecialCharacters', False),
    ('parserStandarisation', "NO"),

    ('terminalEditorScrollLineCount', 20),
    ('maxClosestMatches', 20),
    ('compareBibles', False),
    ('compareBibleVersions', ["KJV", "NET"]),

    ("chatbot", "chatgpt"),
)

# save default configs
configFile = os.path.join(config.packageFolder, "config.py")
backupFile = os.path.join(config.storagedirectory, "config_backup.py")
if os.path.getsize(configFile) == 0:
    if os.path.isfile(backupFile):
        restore_backup = yes_no_dialog(
            title="Configuration Backup Found",
            text=f"Do you want to use the following backup?\n{backupFile}"
        ).run()
        if restore_backup:
            shutil.copy(backupFile, configFile)
            print("Configuration backup restored!")
            config.restartApp()
# load default config
setConfig(defaultSettings)
# share setConfig, to allow plugins to add customised config
config.setConfig = setConfig
# back up newly saved config
if os.path.getsize(configFile) == 0:
    config.saveConfig()
    shutil.copy(configFile, backupFile)
