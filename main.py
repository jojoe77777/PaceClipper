# if you want to attempt to run this on linux/mac,
# you will need to change the ffmpeg/ffprobe/vlc binary downloading & execution,
# the explorer command for opening folder, and the winsound usage

import asyncio
import glob
import hashlib
import json
import os
import subprocess
from subprocess import check_output
import zipfile
from tkinter import StringVar
import customtkinter
import winsound
from CTkToolTip import CTkToolTip
from customtkinter import filedialog
import requests
from ctypes import windll, byref, create_unicode_buffer
import webbrowser

from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
import datetime

from PIL import Image
from os import path

bundle_dir = path.abspath(path.dirname(__file__))

def getResourcePath(name):
    return path.join(bundle_dir, "resources", name)

runData = {}

vlcPath = "vlc/vlc-3.0.20/vlc.exe"
ffmpegPath = "ffmpeg/ffmpeg-n4.4.4-94-g5d07afd482-win64-lgpl-shared-4.4/bin/ffmpeg.exe"
ffprobePath = "ffmpeg/ffmpeg-n4.4.4-94-g5d07afd482-win64-lgpl-shared-4.4/bin/ffprobe.exe"

home = os.path.expanduser("~")
cwd = home + "/PaceClipper"
version = "1.1.0"

nvenc = False
downloaded = False

settings = {}

def idToName(eventId):
    resolve = {
        "nether": "Nether",
        "bastion": "Bastion",
        "fortress": "Fortress",
        "first_portal": "First Portal",
        "stronghold": "Stronghold",
        "end": "Enter End",
        "finish": "Finish",
    }
    return resolve.get(eventId, eventId)

async def getFileName(dir, runTime):
    try:
        fileList = glob.glob(dir + "/*.mkv") + glob.glob(dir + "/*.mp4")
        if not fileList:
            return None
        latest = sorted(fileList, key=os.path.getctime, reverse=True)
        for file in latest:
            ctime = os.path.getctime(file)
            if ctime < runTime:
                latest = file
                break
        return latest
    except:
        return None

class App(customtkinter.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        self.geometry(self.getCenteredPosition(520, 500))
        #self.geometry("520x500+-600+200")  # jojoe 2nd monitor for dev
        self.title(f"PaceClipper v{version}")
        self.resizable(False, False)

        self.name = StringVar()
        self.outname = StringVar()
        self.track1 = customtkinter.StringVar(value="on")
        self.track2 = customtkinter.StringVar(value="on")
        self.track3 = customtkinter.StringVar(value="on")
        self.track4 = customtkinter.StringVar(value="on")
        self.track5 = customtkinter.StringVar(value="on")
        self.track6 = customtkinter.StringVar(value="on")
        self.smoothing = customtkinter.StringVar(value="off")

        self.bgImage = customtkinter.CTkImage(Image.open(getResourcePath("bg.jpg")), size=(520, 500))
        self.bgImageLabel = customtkinter.CTkLabel(self, text="", image=self.bgImage)
        self.bgImageLabel.place(x=0, y=0, relwidth=1, relheight=1)

        customtkinter.CTkLabel(self, text="Settings",
                               font=("Minecraftia", 16), fg_color="#3E3548",
                               bg_color="#3E3548").place(x=425, y=10)

        self.obsFolder = customtkinter.CTkButton(self, text="OBS Folder", font=("Minecraftia", 16),
                                                 width=125, height=36, corner_radius=0,
                                                 fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
                                                 border_color="#b2a6bf", border_width=2,
                                                 command=self.findVideo)
        self.obsFolder.place(x=16, y=17)
        CTkToolTip(self.obsFolder, "Select recordings folder", follow=True, delay=0, font=("Minecraftia", 12),
                   border_color="#2e1e3b", border_width=2)

        self.obsSelection = customtkinter.CTkButton(self, text="", font=("Minecraftia", 12),
                                                   fg_color="#3E3548", bg_color="#3E3548", text_color="#AB9FB5",
                                                   hover_color="#493e54", anchor="w",
                                                   command=self.openObs
                                                   )
        self.obsSelection.place(x=145, y=21)
        self.obsTooltip = CTkToolTip(self.obsSelection, "", follow=True, delay=0.5, font=("Minecraftia", 12),
                                     border_color="#2e1e3b", border_width=2)

        self.outFolder = customtkinter.CTkButton(self, text="Output Folder", font=("Minecraftia", 16),
                                                 width=155, height=36, corner_radius=0,
                                                 fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
                                                 border_color="#b2a6bf", border_width=2,
                                                 command=self.findOutput
                                                 )
        self.outFolder.place(x=16, y=62)
        CTkToolTip(self.outFolder, "Select output folder", follow=True, delay=0, font=("Minecraftia", 12),
                   border_color="#2e1e3b", border_width=2)

        self.outSelection = customtkinter.CTkButton(self, text="J:/Path/to/output", font=("Minecraftia", 12),
                                                   fg_color="#3E3548", bg_color="#3E3548", text_color="#AB9FB5",
                                                   hover_color="#493e54", anchor="w",
                                                   command=self.openOut
                                                   )
        self.outSelection.place(x=175, y=66)
        self.outTooltip = CTkToolTip(self.outSelection, "", follow=True, delay=0.5, font=("Minecraftia", 12),
                                     border_color="#2e1e3b", border_width=2)

        self.username = customtkinter.CTkButton(self, text="Username", font=("Minecraftia", 16),
                                                width=110, height=36, corner_radius=0,
                                                fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
                                                border_color="#b2a6bf", border_width=2,
                                                )
        self.username.place(x=16, y=106)
        CTkToolTip(self.username, "Username (MC or Twitch)", follow=True, delay=0, font=("Minecraftia", 12),
                   border_color="#2e1e3b", border_width=2)

        vcmd = (self.register(self.setName), '%P')
        self.nameInput = customtkinter.CTkEntry(self, font=("Minecraftia", 16), textvariable=self.name, width=220,
                                                height=36, fg_color="#3E3548", bg_color="#3E3548",
                                                border_color="#867396", border_width=1,
                                                corner_radius=0, validatecommand=vcmd, validate="key")
        self.nameInput.place(x=130, y=106)

        self.outputName = customtkinter.CTkButton(self, text="File name", font=("Minecraftia", 16),
                                                  width=110, height=36, corner_radius=0,
                                                  fg_color="#3E3548", bg_color="#3E3548", hover_color="#3E3548",
                                                  border_color="#b2a6bf", border_width=2,
                                                  )

        self.outputNameExtension = customtkinter.CTkButton(self, text=".mp4", font=("Minecraftia", 16),
                                                           width=30, height=30, corner_radius=0,
                                                           fg_color="#3E3548", bg_color="#3E3548"
                                                           )

        self.outNameInput = customtkinter.CTkEntry(self, font=("Minecraftia", 16), textvariable=self.outname, width=190,
                                                   height=36, fg_color="#3E3548", bg_color="#3E3548",
                                                   border_color="#867396", validate="focusout", border_width=1,
                                                   corner_radius=0)

        self.outTooltip = CTkToolTip(self.outSelection, "", follow=True, delay=0.5, font=("Minecraftia", 12),
                                     border_color="#2e1e3b", border_width=2)

        customtkinter.CTkButton(self, text="", width=465, height=1, bg_color="#796d82").place(x=26, y=155)

        customtkinter.CTkLabel(self, text="Trimming",
                               font=("Minecraftia", 16), fg_color="#3E3548",
                               bg_color="#3E3548").place(x=425, y=158)

        self.fetchButton = customtkinter.CTkButton(
            self, text="Load runs", font=("Minecraftia", 16), width=125, height=36, corner_radius=0,
            fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
            border_color="#b2a6bf", border_width=2,
            command=self.fetch)
        self.fetchButton.place(x=16, y=162)

        customtkinter.CTkButton(self, text="", width=465, height=1, bg_color="#796d82").place(x=26, y=315)

        customtkinter.CTkLabel(self, text="Clipping",
                               font=("Minecraftia", 16), fg_color="#3E3548",
                               bg_color="#3E3548").place(x=425, y=318)

        self.outButton = customtkinter.CTkButton(self, text="Open output folder", font=("Arial", 16),
                                                 command=self.openOut)

        self.loadingLabel = customtkinter.CTkLabel(
            self, text="Loading...",
            font=("Minecraftia", 16), fg_color="#3E3548",
            bg_color="#3E3548")
        self.loadingLabel.place(x=155, y=166)

        self.runList = customtkinter.CTkOptionMenu(
            self, values=[""], font=("Minecraftia", 12), dropdown_font=("Minecraftia", 12), command=self.selectRun,
            bg_color="#3E3548", fg_color="#3E3548", button_color="#524c59", button_hover_color="#756c7f",
            dropdown_fg_color="#3E3548", dropdown_hover_color="#524c59",
        )

        self.runListButton = customtkinter.CTkButton(self, text="", font=("Minecraftia", 16),
                                                     width=263, height=32, corner_radius=0,
                                                     fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
                                                     border_color="#b2a6bf", border_width=2,
                                                     )
        self.runListButton.lower(self.runList)

        self.startSplit = customtkinter.CTkOptionMenu(self, values=[""], font=("Minecraftia", 12),
                                                      dropdown_font=("Minecraftia", 12), bg_color="#3E3548",
                                                      fg_color="#3E3548", button_color="#524c59",
                                                      button_hover_color="#756c7f",
                                                      dropdown_fg_color="#3E3548", dropdown_hover_color="#524c59", )
        self.startSplitButton = customtkinter.CTkButton(self, text="", font=("Minecraftia", 16),
                                                     width=144, height=32, corner_radius=0,
                                                     fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
                                                     border_color="#b2a6bf", border_width=2,
                                                     )
        self.startSplitButton.lower(self.startSplit)

        self.endSplit = customtkinter.CTkOptionMenu(self, values=[""], font=("Minecraftia", 12),
                                                    dropdown_font=("Minecraftia", 12), bg_color="#3E3548",
                                                    fg_color="#3E3548", button_color="#524c59",
                                                    button_hover_color="#756c7f", dropdown_fg_color="#3E3548",
                                                    dropdown_hover_color="#524c59")
        self.endSplitButton = customtkinter.CTkButton(self, text="", font=("Minecraftia", 16),
                                                     width=144, height=32, corner_radius=0,
                                                     fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
                                                     border_color="#b2a6bf", border_width=2,
                                                     )
        self.endSplitButton.lower(self.startSplit)

        self.startLabel = customtkinter.CTkLabel(
            self, text="Start: ", font=("Minecraftia", 16), width=60, height=30, fg_color="#3E3548", bg_color="#3E3548")
        self.endLabel = customtkinter.CTkLabel(
            self, text="End: ", font=("Minecraftia", 16), width=60, fg_color="#3E3548", bg_color="#3E3548")
        self.runLabel = customtkinter.CTkLabel(
            self, text="Run: ", font=("Minecraftia", 16), height=30, width=60, fg_color="#3E3548", bg_color="#3E3548")

        self.watchBtn = customtkinter.CTkButton(
            self, text="Watch", font=("Minecraftia", 18), width=100, height=45, corner_radius=0,
            fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
            border_color="#b2a6bf", border_width=2, command=self.watchSplit)

        self.clipButton = customtkinter.CTkButton(
            self, text="Clip", font=("Minecraftia", 18), width=100, height=45, corner_radius=0,
            fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
            border_color="#b2a6bf", border_width=2, command=self.clip)

        self.smoothButton = customtkinter.CTkCheckBox(self, text="Blend down to 60 fps", font=("Minecraftia", 16),
                                                      command=self.update_smoothing, variable=self.smoothing,
                                                      onvalue="on", offvalue="off", bg_color="#3E3548",
                                                      fg_color="#555577", hover_color="#b2a6bf")

        self.trackLabel = customtkinter.CTkLabel(
            self, text="Audio tracks:", font=("Minecraftia", 16), width=0, height=0, fg_color="#3E3548", bg_color="#3E3548")


        self.trackOpt1 = customtkinter.CTkCheckBox(self, text="1", font=("Minecraftia", 16),
                                                      command=self.updateTracks, variable=self.track1,
                                                      onvalue="on", offvalue="off", bg_color="#3E3548", border_color="#b2a6bf",
                                                      fg_color="#555577", hover_color="#493e54", width=0)
        self.trackOpt2 = customtkinter.CTkCheckBox(self, text="2", font=("Minecraftia", 16),
                                                   command=self.updateTracks, variable=self.track2,
                                                   onvalue="on", offvalue="off", bg_color="#3E3548", border_color="#b2a6bf",
                                                   fg_color="#555577", hover_color="#493e54", width=0)
        self.trackOpt3 = customtkinter.CTkCheckBox(self, text="3", font=("Minecraftia", 16),
                                                   command=self.updateTracks, variable=self.track3,
                                                   onvalue="on", offvalue="off", bg_color="#3E3548", border_color="#b2a6bf",
                                                   fg_color="#555577", hover_color="#493e54", width=0)
        self.trackOpt4 = customtkinter.CTkCheckBox(self, text="4", font=("Minecraftia", 16),
                                                   command=self.updateTracks, variable=self.track4,
                                                   onvalue="on", offvalue="off", bg_color="#3E3548", border_color="#b2a6bf",
                                                   fg_color="#555577", hover_color="#493e54", width=0)
        self.trackOpt5 = customtkinter.CTkCheckBox(self, text="5", font=("Minecraftia", 16),
                                                   command=self.updateTracks, variable=self.track5,
                                                   onvalue="on", offvalue="off", bg_color="#3E3548", border_color="#b2a6bf",
                                                   fg_color="#555577", hover_color="#493e54", width=0)
        self.trackOpt6 = customtkinter.CTkCheckBox(self, text="6", font=("Minecraftia", 16),
                                                   command=self.updateTracks, variable=self.track6,
                                                   onvalue="on", offvalue="off", bg_color="#3E3548", border_color="#b2a6bf",
                                                   fg_color="#555577", hover_color="#493e54", width=0)

        self.pacemanButton = customtkinter.CTkButton(
            self, text="PaceMan", font=("Minecraftia", 16), width=100, height=32, corner_radius=0,
            fg_color="#3E3548", bg_color="#3E3548", hover_color="#493e54",
            border_color="#b2a6bf", border_width=2, command=self.openPaceman)

    def getCenteredPosition(self, width, height):
        screenWidth = self.winfo_screenwidth()
        screenHeight = self.winfo_screenheight()

        centerX = int((screenWidth // 2) - (width / 2) - 8)
        # 32 - top bar size, 8 = invisible window border
        centerY = int((screenHeight // 2) - (height / 2) - 32 - 8)
        return f"{width}x{height}+{centerX}+{centerY}"

    def really_force_focus(self, window):
        window.attributes('-topmost', True)
        window.after(500, window.attributes, '-topmost', False)

    def update_smoothing(self):
        settings["doSmoothing"] = self.smoothButton.get() == "on"
        self.save_settings()

    def updateTracks(self):
        settings["track1"] = self.track1.get() == "on"
        settings["track2"] = self.track2.get() == "on"
        settings["track3"] = self.track3.get() == "on"
        settings["track4"] = self.track4.get() == "on"
        settings["track5"] = self.track5.get() == "on"
        settings["track6"] = self.track6.get() == "on"
        self.save_settings()

    @async_handler
    async def openPaceman(self):
        run = runData[self.runList.get()]
        webbrowser.open(f"https://paceman.gg/stats/run/{run['id']}/")

    @async_handler
    async def openObs(self):
        os.startfile(settings["obsPath"])

    @async_handler
    async def openOut(self):
        os.startfile(settings["outputPath"])

    def setIcon(self, window):
        if window.winfo_exists():
            window.iconbitmap(getResourcePath("icon.ico"))

    async def download_with_progress(self, download_url, save_path, extract_path, final_path, expected_hash):
        if os.path.exists(final_path):
            print(f"File already exists: {final_path}")
            return

        progWindow = customtkinter.CTkToplevel(self)
        progWindow.geometry(self.getCenteredPosition(300, 48))
        progWindow.title(f"Downloading {extract_path}")
        progWindow.resizable(False, False)
        progWindow.attributes("-alpha", 0.0)  # dont render window yet

        # customtkinter developer is stupid and hardcoded a 200ms icon, so we wait 201ms
        app.after(201, self.setIcon, progWindow)

        bar = customtkinter.CTkProgressBar(progWindow, mode="determinate")
        bar.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        bar.set(0.0)

        pctLabel = customtkinter.CTkLabel(
            progWindow, text="0%", font=("Arial", 16))
        pctLabel.grid(row=0, column=3, columnspan=2,
                      padx=10, pady=10, sticky="w")

        progWindow.update()  # make sure window appears
        await asyncio.sleep(0.01)
        # render window now that it's not white
        progWindow.attributes("-alpha", 1.0)
        self.really_force_focus(progWindow)

        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()  # Raise exception for non-2xx status codes

            # Get content size from headers
            total_size = int(response.headers.get('content-length', 0))

            with open(save_path, "wb") as f:
                downloaded_size = 0
                progInterval = 1
                lastUpdate = 0
                for chunk in response.iter_content(1024):
                    if chunk:  # filter out keep-alive new chunks
                        downloaded_size += len(chunk)
                        f.write(chunk)
                        progress = (downloaded_size / total_size) * 100
                        if progress > 99:
                            progress = 100
                        if (progress - lastUpdate) > progInterval:
                            lastUpdate = progress
                            if not progWindow.winfo_exists():
                                print("Cancelling download due to progress window closed")
                                exit(1)
                                return
                            bar.set(progress / 100)
                            pctLabel.configure(text=f"{progress:.0f}%")
                            progWindow.update()

            # Hash verification
            with open(save_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            if file_hash == expected_hash:
                print("Download successful and hash verified!")
                with zipfile.ZipFile(save_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    print(f"Extracted ZIP to: {extract_path}")
            else:
                print("Downloaded file hash does not match expected hash. Discarding file.")

            self.after(100, os.remove, save_path)
        except requests.exceptions.RequestException as e:
            print(f"Download failed: {e}")
        progWindow.destroy()

    async def download_dependencies(self):
        global nvenc, downloaded
        vlc_url = "https://vlc.pixelx.de/vlc/3.0.20/win32/vlc-3.0.20-win32.zip"
        await self.download_with_progress(vlc_url, "vlc.zip", "vlc", vlcPath,
                                          "d22155d8330f99f2050e8fe3fd2b8e85104ba7f899a875c21f92a97cbdfbb7c5")

        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2024-03-30-12-47/ffmpeg-n4.4.4-94-g5d07afd482-win64-lgpl-shared-4.4.zip"
        await self.download_with_progress(ffmpeg_url, "ffmpeg.zip", "ffmpeg",
                                          ffmpegPath,
                                          "5cef674974681aeb78cf8f68631531e5ac9a19ccb74525aaacc4a933534c14ec")

        nvenc = "cuda" in check_output(
            [ffmpegPath, "-hide_banner", "-init_hw_device", "list"]).decode("utf-8")
        print(f"NVENC available: {nvenc}")
        downloaded = True

    def load_settings(self):
        global settings, startOffset, endOffset
        filename = "settings.json"
        file_path = os.path.join(cwd, filename)

        try:
            with open(file_path, "r") as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            default_settings = {
                "name": "Username",
                "obsPath": "C:/OBS/",
                "outputPath": "C:/Output/",
                "startOffset": 2,
                "endOffset": 4,
                "extraBitratePercent": 30,
                "doSmoothing": False,
                "track1": True,
                "track2": True,
                "track3": True,
                "track4": True,
                "track5": True,
                "track6": True,
            }
            settings = default_settings
            self.save_settings()
        self.setObsPath(settings["obsPath"] if "obsPath" in settings else "C:/OBS/", True)
        self.setOutputPath(settings["outputPath"] if "outputPath" in settings else "C:/Output/", True)
        self.name.set(settings["name"])
        self.smoothing.set("on" if settings["doSmoothing"] else "off")
        self.track1.set("on" if "track1" in settings and settings["track1"] else "off")
        self.track2.set("on" if "track2" in settings and settings["track2"] else "off")
        self.track3.set("on" if "track3" in settings and settings["track3"] else "off")
        self.track4.set("on" if "track4" in settings and settings["track4"] else "off")
        self.track5.set("on" if "track5" in settings and settings["track5"] else "off")
        self.track6.set("on" if "track6" in settings and settings["track6"] else "off")
        startOffset = settings["startOffset"]
        endOffset = settings["endOffset"]

    def setObsPath(self, path, save=True):
        global settings
        settings["obsPath"] = path
        self.obsSelection.configure(text=(path if len(path) < 30 else "..." + path[-30:]))
        self.obsTooltip.messageVar.set(path)
        if save:
            self.save_settings()

    def setOutputPath(self, path, save=True):
        global settings
        settings["outputPath"] = path
        self.outSelection.configure(text=(path if len(path) < 30 else "..." + path[-30:]))
        self.outTooltip.messageVar.set(path)
        if save:
            self.save_settings()

    def setName(self, entry):
        global settings
        settings["name"] = entry
        self.save_settings()
        return True

    def save_settings(self):
        global settings
        filename = "settings.json"
        file_path = os.path.join(cwd, filename)

        with open(file_path, "w") as f:
            json.dump(settings, f, indent=4)

    @async_handler
    async def selectRun(self, runName):
        run = runData[runName]
        splitOptions = []
        for split in ['start', 'nether', 'bastion', 'fortress', 'first_portal', 'stronghold', 'end', 'finish']:
            if run[split] is not None:
                splitOptions.append(split)
        splitOptions.append('reset')
        self.startSplit.configure(values=splitOptions)
        self.startSplit.set(splitOptions[0])

        self.endSplit.configure(values=splitOptions)
        self.endSplit.set(splitOptions[-1])

    async def run_ffmpeg(self, args, duration, description="Encoding video"):
        progWindow = customtkinter.CTkToplevel(self, fg_color="#3E3548")

        progWindow.geometry(self.getCenteredPosition(300, 48))
        progWindow.attributes("-alpha", 0.0)  # dont render window yet
        progWindow.title(description)
        progWindow.resizable(False, False)
        app.after(201, self.setIcon, progWindow)

        bar = customtkinter.CTkProgressBar(progWindow, mode="determinate")
        bar.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        bar.set(0.0)

        pctLabel = customtkinter.CTkLabel(
            progWindow, text="0%", font=("Minecraftia", 16), bg_color="#3E3548", fg_color="#3E3548")
        pctLabel.grid(row=0, column=3, columnspan=2,
                      padx=10, pady=10, sticky="w")

        progWindow.update()
        await asyncio.sleep(0.01)
        # render window now that it's not white
        progWindow.attributes("-alpha", 1.0)
        self.really_force_focus(progWindow)

        process = subprocess.Popen([ffmpegPath, "-y", "-stats_period", "0.1", "-progress", "pipe:1", "-nostats",
                                    "-hide_banner", "-loglevel", "error"] + args,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   universal_newlines=True)

        try:
            while process.poll() is None:
                for line in process.stdout:
                    if "out_time_us" in line:
                        if not progWindow.winfo_exists():
                            print("Cancelling ffmpeg process due to progress window closed")
                            process.kill()
                            return False
                        out_time_us = int(line.split("=")[1].strip())
                        progress = ((out_time_us / 1000000) / duration) * 100
                        if progress > 99:
                            progress = 100
                        bar.set(progress / 100)
                        pctLabel.configure(text=f"{progress:.0f}%")
                        # share some time for window updates/button clicks
                        await asyncio.sleep(0.05)

        except Exception as e:
            print(f"ffmpeg error: {e}")
            return False
        finally:
            process.wait()
            progWindow.destroy()
            if process.returncode:
                print(f"Error: ffmpeg exited with code {process.returncode}")
        return True

    async def display_error(self, error, width=300, height=48):
        progWindow = customtkinter.CTkToplevel(self)
        progWindow.geometry(self.getCenteredPosition(width, height))
        progWindow.title(f"Error")
        progWindow.resizable(False, False)
        progWindow.attributes("-alpha", 0.0)  # dont render window yet

        # customtkinter developer is stupid and hardcoded a 200ms icon, so we wait 201ms
        app.after(201, self.setIcon, progWindow)

        label = customtkinter.CTkLabel(
            progWindow, text=error, font=("Minecraftia", 16), bg_color="#3E3548", fg_color="#3E3548", width=width,
            height=height)
        label.place(relx=0.5, rely=0.5, anchor="center")
        # label.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        progWindow.update()  # make sure window appears
        await asyncio.sleep(0.05)
        # render window now that it's not white
        progWindow.attributes("-alpha", 1.0)
        self.really_force_focus(progWindow)

    @async_handler
    async def clip(self):
        global settings
        if not downloaded:
            # probably won't happen since the download progress window is a busy loop
            await self.display_error("Dependencies not downloaded", 320, 48)
            return
        run = runData[self.runList.get()]
        start = run[self.startSplit.get()] - settings["startOffset"]
        end = run[self.endSplit.get()] + settings["endOffset"]

        if run[self.startSplit.get()] == run[self.endSplit.get()]:
            await self.display_error("Start and end splits are the same", 380, 48)
            return

        if run[self.startSplit.get()] > run[self.endSplit.get()]:
            await self.display_error("Start split is after end split", 320, 48)
            return

        filePath = await getFileName(settings["obsPath"], start)
        if filePath is None:
            await self.display_error("No video found for recording", 340, 48)
            return

        ctime = os.path.getctime(filePath)
        vodStartOffset = int(start - ctime)
        vodEndOffset = int(end - ctime)

        vidDuration = int(float(check_output([ffprobePath, "-i", filePath, "-v", "quiet",
                                              "-show_entries", "format=duration", "-of", "csv=p=0"]).decode(
            "utf-8").strip()))

        if vodStartOffset > vidDuration or vodEndOffset > vidDuration:
            await self.display_error("Run was not found in any video", 350, 48)
            return

        ms, ss = divmod(vodStartOffset, 60)
        hs, ms = divmod(ms, 60)

        startSeconds = round(run[self.startSplit.get()] - run['start'])
        mss, sss = divmod(startSeconds, 60)
        hss, mss = divmod(mss, 60)

        endSeconds = round(run[self.endSplit.get()] -
                           settings['startOffset'] - start)
        mes, ses = divmod(endSeconds, 60)
        hes, mes = divmod(mes, 60)

        duration = (end - start)

        dms, dss = divmod(duration, 60)
        dhs, dms = divmod(dms, 60)

        lastUpdated = datetime.datetime.fromtimestamp(run['lastUpdated']).strftime('%I_%M%p_%d_%m_%y')
        if self.startSplit.get() == "start":
            baseName = f"{self.startSplit.get()}_{mes:01d}_{ses:02d}_{self.endSplit.get()}_{lastUpdated}"
        else:
            baseName = f"{mss}_{sss}_{self.startSplit.get()}_{mes:01d}_{ses:02d}_{self.endSplit.get()}_{lastUpdated}"

        name = f"{settings['outputPath']}\\unfinished_{baseName}.mp4"
        nameSmooth = f"{settings['outputPath']}\\unfinished_{baseName}_smooth.mp4"

        tracks = [settings["track1"], settings["track2"], settings["track3"], settings["track4"], settings["track5"], settings["track6"]]
        trackArgs = ["-map", "0:v"]
        for i, track in enumerate(tracks):
            if track:
                trackArgs.append("-map")
                trackArgs.append(f"0:a:{i}?")

        if not await self.run_ffmpeg(["-ss", f"{hs:02d}:{ms:02d}:{ss:02d}", "-t",
                                      f"{int(dhs):02d}:{int(dms):02d}:{int(dss):02d}", "-i", filePath,
                                      "-avoid_negative_ts", "make_zero", "-c", "copy", "-acodec", "copy"] + trackArgs + [name],
                                     duration, "Clipping video..."):
            return

        # remove "unfinished" once complete
        if self.outname.get():
            renamed = f"{settings['outputPath']}/{self.outname.get()}.mp4"
        else:
            renamed = f"{settings['outputPath']}/{baseName}.mp4"
        if os.path.exists(renamed):
            os.unlink(renamed)
        os.rename(name, renamed)

        if nvenc and settings["doSmoothing"]:
            # get bitrate of trimmed vid
            bitrate = int(check_output([ffprobePath, "-v", "quiet", "-select_streams", "v:0",
                                        "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1",
                                        renamed]).decode("utf-8").strip())

            # apply extra bitrate to reduce impact of double nvenc encoding, default 30% extra
            boosted = int(bitrate * (1 + int(settings["extraBitratePercent"]) / 100))

            if not await self.run_ffmpeg(
                    ["-i", renamed, "-vf", "tblend=all_mode=average", "-r", "60", "-c:v", "h264_nvenc", "-b:v",
                     str(boosted), "-preset", "p7", "-profile", "high", "-c:a", "copy", nameSmooth],
                    duration, "Converting framerate..."):
                return

            renamedSmooth = f"{settings['outputPath']}/{baseName}_smooth.mp4"
            safePath = renamedSmooth.replace("/", "\\")

            # remove "unfinished" once complete
            if not os.path.exists(renamedSmooth):
                os.rename(nameSmooth, renamedSmooth)
            os.system(f"explorer /select,{safePath}")
            winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS | winsound.SND_ASYNC)
        else:
            safePath = renamed.replace("/", "\\")
            os.system(f"explorer /select,{safePath}")
            winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS | winsound.SND_ASYNC)

    @async_handler
    async def findVideo(self):
        folder = filedialog.askdirectory()
        if folder:
            self.setObsPath(folder)

    @async_handler
    async def findOutput(self):
        folder = filedialog.askdirectory()
        if folder:
            self.setOutputPath(folder)

    @async_handler
    async def watchSplit(self):
        global settings
        run = runData[self.runList.get()]
        start = run[self.startSplit.get()] - settings["startOffset"]

        filePath = await getFileName(settings["obsPath"], start)
        if filePath is None:
            await self.display_error("No recording found for this run", 360, 48)
            return

        ctime = os.path.getctime(filePath)
        vodStartOffset = int(start - ctime)
        subprocess.Popen([vlcPath, f"file:///{filePath}", f"--start-time={vodStartOffset}", "--no-video-title-show"])

    def hideThings(self):
        self.runLabel.place(x=0, y=999)
        self.startLabel.place(x=0, y=999)
        self.endLabel.place(x=0, y=999)
        self.runList.place(x=0, y=999)
        self.startSplit.place(x=0, y=999)
        self.endSplit.place(x=0, y=999)
        self.clipButton.place(x=0, y=999)
        self.watchBtn.place(x=0, y=999)
        self.outputName.place(x=0, y=999)
        self.outNameInput.place(x=0, y=999)
        self.outputNameExtension.place(x=0, y=999)
        self.runListButton.place(x=0, y=999)
        self.startSplitButton.place(x=0, y=999)
        self.endSplitButton.place(x=0, y=999)
        self.smoothButton.place(x=0, y=999)
        self.trackOpt1.place(x=0, y=999)
        self.trackOpt2.place(x=0, y=999)
        self.trackOpt3.place(x=0, y=999)
        self.trackOpt4.place(x=0, y=999)
        self.trackOpt5.place(x=0, y=999)
        self.trackOpt6.place(x=0, y=999)
        self.trackLabel.place(x=0, y=999)
        self.pacemanButton.place(x=0, y=999)

    def showThings(self):
        self.runLabel.place(x=12, y=203)
        self.startLabel.place(x=17, y=238)
        self.endLabel.place(x=12, y=275)

        self.runList.place(x=90, y=205)
        self.startSplit.place(x=90, y=240)
        self.endSplit.place(x=90, y=275)

        self.clipButton.place(x=400, y=385)
        self.watchBtn.place(x=400, y=435)
        self.outputName.place(x=16, y=446)
        self.outNameInput.place(x=130, y=446)
        self.outputNameExtension.place(x=320, y=446)

        self.runListButton.place(x=88, y=203)
        self.startSplitButton.place(x=88, y=238)
        self.endSplitButton.place(x=88, y=273)

        if nvenc:
            self.smoothButton.place(x=16, y=330)

        self.trackOpt1.place(x=16, y=416)
        self.trackOpt2.place(x=64, y=416)
        self.trackOpt3.place(x=112, y=416)
        self.trackOpt4.place(x=160, y=416)
        self.trackOpt5.place(x=208, y=416)
        self.trackOpt6.place(x=256, y=416)

        self.trackLabel.place(x=16, y=390)

        self.pacemanButton.place(x=352, y=203)

    @async_handler
    async def fetch(self):
        global runData, settings
        self.hideThings()
        self.loadingLabel.configure(text="Loading...")

        name = self.nameInput.get()
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, requests.get,
                                       f"https://paceman.gg/stats/api/getRecentTimestamps/?name={name}")
        if r.status_code != 200:
            self.loadingLabel.configure(text="Invalid username")
            return
        data = r.json()
        runData = {}

        self.showThings()

        runs = []
        i = 0
        splitOptions = []
        for run in data:
            i += 1
            if "realUpdate" in run:
                run['reset'] = run['realUpdate']
            else:
                run['reset'] = run['lastUpdated']
            lastSplit = 'nether'
            for split in ['start', 'nether', 'bastion', 'fortress', 'first_portal', 'stronghold', 'end', 'finish']:
                if run[split] is not None:
                    lastSplit = split
                    if i == 1:
                        splitOptions.append(split)

            start = run['start'] - settings['startOffset']
            seconds = round(run[lastSplit] - settings['startOffset'] - start)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            lastUpdated = datetime.datetime.fromtimestamp(run['lastUpdated']).strftime('%H:%M %d/%m/%y')
            name = f"{m:01d}:{s:02d} {idToName(lastSplit)} {lastUpdated}"
            runs.append(name)
            runData[name] = run

        splitOptions.append('reset')
        self.runList.configure(values=runs)
        self.runList.set(runs[0])

        self.startSplit.configure(values=splitOptions)
        self.startSplit.set(splitOptions[0])

        self.endSplit.configure(values=splitOptions)
        self.endSplit.set(splitOptions[-1])

        self.loadingLabel.configure(text="")

def load_font(fontpath):
    pathbuf = create_unicode_buffer(fontpath)
    AddFontResourceEx = windll.gdi32.AddFontResourceExW

    numFontsAdded = AddFontResourceEx(byref(pathbuf), 0x10 | 0x20, 0)
    return numFontsAdded > 0

if __name__ == "__main__":
    if not os.path.exists(cwd):
        os.mkdir(cwd)
    if not os.path.exists(cwd + "/videos"):
        os.mkdir(cwd + "/videos")

    if not load_font(getResourcePath("font.ttf")):
        print("Failed to load font")

    os.chdir(cwd)

    app = App()
    app.after(1, app.load_settings)
    app.after(2, app.fetch)
    app.iconbitmap(getResourcePath("icon.ico"))

    asyncio.get_event_loop_policy().get_event_loop().create_task(app.download_dependencies())
    app.async_mainloop()
