import os, platform

mainFile = os.path.realpath(__file__)
packageFolder = os.path.dirname(mainFile)

# create config.py if it does not exist; in case user delete the file for some reasons
configFile = os.path.join(packageFolder, "config.py")
if not os.path.isfile(configFile):
    open(configFile, "a", encoding="utf-8").close()

try:
    from searchbible import config
except:
    # write off problematic config file
    open(configFile, "w", encoding="utf-8").close()
    from searchbible import config

# share packageFolder paths in config
config.packageFolder = packageFolder
#package = os.path.basename(config.packageFolder)
if os.getcwd() != config.packageFolder:
    os.chdir(config.packageFolder)

# check current platform
config.thisPlatform = platform.system()
# check if it is running with Android Termux
config.isTermux = True if os.path.isdir("/data/data/com.termux/files/home") else False
