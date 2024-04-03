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
from customtkinter import filedialog
import requests

from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
import datetime

from os import path
bundle_dir = path.abspath(path.dirname(__file__))
iconPath = path.join(bundle_dir, 'icon.ico')

runData = {}

vlcPath = "vlc/vlc-3.0.20/vlc.exe"
ffmpegPath = "ffmpeg/ffmpeg-n4.4.4-94-g5d07afd482-win64-lgpl-shared-4.4/bin/ffmpeg.exe"
ffprobePath = "ffmpeg/ffmpeg-n4.4.4-94-g5d07afd482-win64-lgpl-shared-4.4/bin/ffprobe.exe"

home = os.path.expanduser("~")
cwd = home + "/PaceClipper"
version = "1.0.0-beta1"

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
        self.title(f"PaceClipper v{version}")
        self.resizable(False, False)

        self.name = StringVar()
        self.smoothing = customtkinter.StringVar(value="off")

        self.vidLabel = customtkinter.CTkLabel(
            self, text="", font=("Arial", 16))
        self.vidLabel.grid(row=0, column=0, columnspan=5,
                           padx=12, pady=5, sticky="w")

        self.vidButton = customtkinter.CTkButton(self, text="Select OBS folder", font=("Arial", 16),
                                                 command=self.findVideo)
        self.vidButton.grid(row=1, column=0, columnspan=3,
                            padx=10, pady=(5, 5), sticky="w")

        self.outButton = customtkinter.CTkButton(self, text="Open output folder", font=("Arial", 16),
                                                 command=self.openOut)
        self.outButton.grid(row=0, column=2, columnspan=3,
                            padx=45, pady=(15, 10), sticky="e")

        self.nameInputLabel = customtkinter.CTkLabel(
            self, text="Minecraft username:", font=("Arial", 16))
        self.nameInputLabel.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.nameInput = customtkinter.CTkEntry(self, font=(
            "Arial", 16), textvariable=self.name, validate="focusout", validatecommand=self.setName)
        self.nameInput.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        self.fetchButton = customtkinter.CTkButton(
            self, text="Fetch", font=("Arial", 16), command=self.fetch)
        self.fetchButton.grid(row=3, column=0, columnspan=1, padx=10, pady=10)

        self.loadingLabel = customtkinter.CTkLabel(
            self, text="", font=("Arial", 16))
        self.loadingLabel.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        self.runList = customtkinter.CTkOptionMenu(
            self, values=[""], command=self.selectRun)
        self.startSplit = customtkinter.CTkOptionMenu(self, values=[""])
        self.endSplit = customtkinter.CTkOptionMenu(self, values=[""])

        self.startLabel = customtkinter.CTkLabel(
            self, text="Start: ", font=("Arial", 16))
        self.endLabel = customtkinter.CTkLabel(
            self, text="End: ", font=("Arial", 16))
        self.runLabel = customtkinter.CTkLabel(
            self, text="Run: ", font=("Arial", 16))

        self.nameInput.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        self.watchBtn = customtkinter.CTkButton(
            self, text="Watch", font=("Arial", 16), command=self.watchSplit)

        self.clipButton = customtkinter.CTkButton(
            self, text="Clip", font=("Arial", 16), command=self.clip)

        self.smoothButton = customtkinter.CTkCheckBox(self, text="Blend down to 60 fps", font=("Arial", 16),
                                                      command=self.update_smoothing, variable=self.smoothing, onvalue="on", offvalue="off")

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

    @async_handler
    async def openOut(self):
        os.startfile(f"{cwd}/videos")

    def setIcon(self, window):
        if window.winfo_exists():
            window.iconbitmap(iconPath)

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
                "videoPath": "C:/OBS/",
                "startOffset": 4,
                "endOffset": 0,
                "extraBitratePercent": 30,
                "doSmoothing": False,
            }
            settings = default_settings
            self.save_settings()
        self.setVideoPath(settings["videoPath"])
        self.name.set(settings["name"])
        self.smoothing.set("on" if settings["doSmoothing"] else "off")
        startOffset = settings["startOffset"]
        endOffset = settings["endOffset"]

    def setVideoPath(self, path, save=True):
        global settings
        settings["videoPath"] = path
        self.vidLabel.configure(text=settings["videoPath"])
        if save:
            self.save_settings()

    def setName(self, save=True):
        global settings
        settings["name"] = self.name.get()
        if save:
            self.save_settings()

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
        progWindow = customtkinter.CTkToplevel(self)

        progWindow.geometry(self.getCenteredPosition(300, 48))
        progWindow.attributes("-alpha", 0.0)  # dont render window yet
        progWindow.title(description)
        progWindow.resizable(False, False)
        app.after(201, self.setIcon, progWindow)

        bar = customtkinter.CTkProgressBar(progWindow, mode="determinate")
        bar.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        bar.set(0.0)

        pctLabel = customtkinter.CTkLabel(
            progWindow, text="0%", font=("Arial", 16))
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
            progWindow, text=error, font=("Arial", 16))
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
            await self.display_error("Dependencies not downloaded", 300, 48)
            return
        run = runData[self.runList.get()]
        start = run[self.startSplit.get()] - settings["startOffset"]
        end = run[self.endSplit.get()] + settings["endOffset"]

        if run[self.startSplit.get()] == run[self.endSplit.get()]:
            await self.display_error("Start and end splits are the same", 260, 48)
            return

        if run[self.startSplit.get()] > run[self.endSplit.get()]:
            await self.display_error("Start split is after end split", 260, 48)
            return

        filePath = await getFileName(settings["videoPath"], start)
        if filePath is None:
            await self.display_error("No videos found", 200, 48)
            return

        ctime = os.path.getctime(filePath)
        vodStartOffset = int(start - ctime)
        vodEndOffset = int(end - ctime)

        vidDuration = int(float(check_output([ffprobePath, "-i", filePath, "-v", "quiet",
                          "-show_entries", "format=duration", "-of", "csv=p=0"]).decode("utf-8").strip()))

        if vodStartOffset > vidDuration or vodEndOffset > vidDuration:
            await self.display_error("Run was not recorded", 200, 48)
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

        duration = end - start

        dms, dss = divmod(duration, 60)
        dhs, dms = divmod(dms, 60)

        lastUpdated = datetime.datetime.fromtimestamp(run['lastUpdated']).strftime('%I_%M%p_%d_%m_%y')
        if self.startSplit.get() == "start":
            baseName = f"{self.startSplit.get()}_{mes:01d}_{ses:02d}_{self.endSplit.get()}_{lastUpdated}"
        else:
            baseName = f"{mss}_{sss}_{self.startSplit.get()}_{mes:01d}_{ses:02d}_{self.endSplit.get()}_{lastUpdated}"

        name = f"videos\\unfinished_{baseName}.mp4"
        nameSmooth = f"videos\\unfinished_{baseName}_smooth.mp4"

        if not await self.run_ffmpeg(["-ss", f"{hs:02d}:{ms:02d}:{ss:02d}", "-t",
                                      f"{int(dhs):02d}:{int(dms):02d}:{int(dss):02d}", "-i", filePath, "-avoid_negative_ts", "make_zero", "-c:v", "copy", "-c:a", "copy", name],
                                     duration, "Clipping video..."):
            return

        # remove "unfinished" once complete
        renamed = f"videos\\{baseName}.mp4"
        if not os.path.exists(renamed):
            os.rename(name, renamed)

        if nvenc and settings["doSmoothing"]:
            # get bitrate of trimmed vid
            bitrate = int(check_output([ffprobePath, "-v", "quiet", "-select_streams", "v:0",
                                        "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1",
                                        renamed]).decode("utf-8").strip())

            # apply extra bitrate to reduce impact of double nvenc encoding, default 30% extra
            boosted = int(bitrate * (1 + int(settings["extraBitratePercent"]) / 100))

            if not await self.run_ffmpeg(["-i", renamed, "-vf", "tblend=all_mode=average", "-r", "60", "-c:v", "h264_nvenc", "-b:v",
                                          str(boosted), "-preset", "p7", "-profile", "high", "-c:a", "copy", nameSmooth],
                                         duration, "Converting framerate..."):
                return

            renamedSmooth = f"videos\\{baseName}_smooth.mp4"

            # remove "unfinished" once complete
            if not os.path.exists(renamedSmooth):
                os.rename(nameSmooth, renamedSmooth)
            os.system(f"explorer /select,{os.getcwd()}\\{renamedSmooth}")
            winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS | winsound.SND_ASYNC)
        else:
            os.system(f"explorer /select,{os.getcwd()}\\{renamed}")
            winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS | winsound.SND_ASYNC)

    @async_handler
    async def findVideo(self):
        folder = filedialog.askdirectory()
        if folder:
            self.setVideoPath(folder)

    @async_handler
    async def watchSplit(self):
        global settings
        run = runData[self.runList.get()]
        start = run[self.startSplit.get()] - settings["startOffset"]

        filePath = await getFileName(settings["videoPath"], start)

        ctime = os.path.getctime(filePath)
        vodStartOffset = int(start - ctime)
        subprocess.Popen([vlcPath, f"file:///{filePath}", f"--start-time={vodStartOffset}", "--no-video-title-show"])

    @async_handler
    async def fetch(self):
        global runData, settings
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

        self.runLabel.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.startLabel.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.endLabel.grid(row=7, column=0, padx=10, pady=5, sticky="w")

        self.runList.grid(row=5, column=0, columnspan=2,
                          padx=(70, 0), pady=10, sticky="w")
        self.startSplit.grid(row=6, column=0, columnspan=2,
                             padx=(70, 0), pady=10, sticky="w")
        self.endSplit.grid(row=7, column=0, columnspan=2,
                           padx=(70, 0), pady=10, sticky="w")

        self.clipButton.grid(row=8, column=0, columnspan=1, padx=10, pady=10)
        self.watchBtn.grid(row=8, column=1, columnspan=2,
                           padx=10, pady=10, sticky="w")

        if nvenc:
            self.smoothButton.grid(
                row=9, column=2, columnspan=2, padx=5, pady=5, sticky="e")

        runs = []
        i = 0
        splitOptions = []
        for run in data:
            i += 1
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
            lastUpdated = datetime.datetime.fromtimestamp(run['lastUpdated']).strftime('%I:%M%p %d/%m/%y')
            name = f"{m:01d}:{s:02d} {idToName(lastSplit)} @ {lastUpdated}"
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


if __name__ == "__main__":
    if not os.path.exists(cwd):
        os.mkdir(cwd)
    if not os.path.exists(cwd + "/videos"):
        os.mkdir(cwd + "/videos")

    os.chdir(cwd)

    app = App()
    app.after(1, app.load_settings)
    app.iconbitmap(iconPath)

    asyncio.get_event_loop_policy().get_event_loop().create_task(app.download_dependencies())
    app.async_mainloop()
