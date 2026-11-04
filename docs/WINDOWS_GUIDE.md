# Beginner's guide: Windows 10 and Windows 11

This tutorial is for people who have never used a terminal. You can run **Project Structure Mapper** **without typing any commands**, using the **INICIAR_WINDOWS.bat** file.

The assistant's menus and messages are in Portuguese. This guide quotes each one with its meaning in English.

[← Back to the README](../README.md)

---

## 1. Install Python

The program needs **Python 3.8 or newer**, with no extra libraries.

1. Open [python.org/downloads](https://www.python.org/downloads/).
2. Download the Python 3 installer for Windows.
3. Follow the installation steps. If you see **Add python.exe to PATH**, tick it.
4. Close any terminal windows that were already open and open them again.

**How to check:** press the Windows key, type **cmd** and open **Command Prompt**. Then type:

~~~bat
py -3 --version
~~~

The terminal should show Python 3.8 or newer. If the **py** command does not work, try:

~~~bat
python --version
~~~

> Python is the interpreter that runs mapper.py. The BAT file looks for a working installation by itself.

## 2. Download the right files from GitHub

1. Go to [Project Structure Mapper](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper).
2. Make sure the selected branch is **main**. Version 2 is published there.
3. Click **Code**, then **Download ZIP**.
4. Open your Downloads folder and click **Extract all** on the downloaded file.
5. Open the extracted folder. It must contain **mapper.py** and **INICIAR_WINDOWS.bat**.

> If the repository is private, GitHub only lets authorised accounts in. Never share your login.

## 3. Run it with a double-click (the easiest way)

1. In the Mapper folder, double-click **INICIAR_WINDOWS.bat**.
2. A black window opens with three options: **1) Mapear um projeto** (map a project), **2) O que essa ferramenta faz?** (what does this tool do?) and **0) Sair** (exit).
3. Press **Enter** to choose **1**.
4. The program asks **which folder to analyse** (*Qual projeto vamos analisar?*). Paste the path (for example **C:\Projects\ExampleProject**) or press Enter to open a folder picker.
5. Choose **1, Público/resumido** (public summary) or **2, Privado/detalhado** (private, detailed report).
6. Press Enter to accept the default report folder, or choose another folder **outside the project**.
7. Check the summary (*RESUMO*), confirm, and note where the results were saved.

**Shortcut:** drag a folder from File Explorer onto **INICIAR_WINDOWS.bat**. The assistant opens with the path already filled in.

### Public or private?

| Choice | When to use it | Keep in mind |
| --- | --- | --- |
| **1, public** | File counts and likely technologies | Still review it before sharing |
| **2, private** | Detailed structure and file names | Never publish reports of internal projects |

The tool **makes no changes** to the analysed folder and sends nothing over the internet.

## 4. Open CMD in the program's folder

**CMD**, or **Command Prompt**, is the classic Windows 10/11 terminal. You use it to run programs by typing commands.

To start in the right folder without memorising paths:

1. Open the Mapper folder in **File Explorer**.
2. Click the **address bar**, where the folder path is shown.
3. Type **cmd** and press **Enter**.
4. CMD opens **in that same folder**.

### Commands ready to copy

**Check Python:**

~~~bat
py -3 --version
~~~

**Run the assistant through the BAT:**

~~~bat
INICIAR_WINDOWS.bat
~~~

**Run the assistant directly with Python:**

~~~bat
py -3 mapper.py
~~~

**Create a public report without the menu:**

~~~bat
py -3 mapper.py "C:\Projects\ExampleProject" --mode public
~~~

**Create a private report in another folder:**

~~~bat
py -3 mapper.py "C:\Projects\ExampleProject" --mode private --output "%USERPROFILE%\Documents\MapperReports"
~~~

**See the help and arguments:**

~~~bat
py -3 mapper.py --help
~~~

Replace **C:\Projects\ExampleProject** with the real project path. The **quotes** protect paths that contain spaces.

### What each part of the command means

| Command text | Meaning |
| --- | --- |
| **py -3** | Calls the installed Python 3 |
| **mapper.py** | The program we want to run |
| **"C:\Projects\ExampleProject"** | The folder to analyse |
| **--mode public** | Public summary report |
| **--mode private** | Internal, detailed report |
| **--output "..."** | Where to save the results |
| **--help** | Shows the help |

If you prefer to change folders by hand in CMD, use:

~~~bat
cd /d "C:\Path\To\The\Mapper\Folder"
~~~

**That path is only an example.** Replace it with the path shown in your File Explorer. **cd** changes the folder; **/d** also lets it change the drive.

## 5. Find the generated report

The default folder is:

~~~text
C:\Users\<your-user>\ProjectStructureReports\
    mapa-publico-YYYYmmdd-HHMMSS\
        relatorio.md
        estrutura.json
        mapa_do_projeto.zip
~~~

Names include the date and time of the run, so every run creates a new folder. In private mode the folder starts with **mapa-privado-** and also contains **arvore.txt**.

The program **refuses to save the report inside the project itself**. This stops the analysis from adding new files to the project you are studying.

## 6. Troubleshooting

| Symptom | What to check |
| --- | --- |
| **"Python 3.8 ou mais novo não foi encontrado"** (Python 3.8 or newer not found) | Install it from the official site, close CMD and open it again |
| **py is not recognised** | Try **python --version**. If it works, use **python** instead of **py -3** in the commands |
| **The ZIP only contains .gitignore** | Check that you downloaded the up-to-date main branch, and extract the whole ZIP again |
| **The BAT does not open, or Windows shows a warning** | Confirm where the file came from and read the BAT in Notepad. **Never dismiss security warnings automatically** or run code you have not authorised |
| **The folder picker does not open** | Paste the folder path into the terminal instead |
| **The folder has spaces or accents** | Use double quotes, for example **"C:\My Projects\Example Project"** |
| **The output folder is INSIDE the project** | Choose another folder, such as Documents |
| **The 25,000-file limit was reached** | Select a specific project folder, not a whole drive |
| **No code files were recognised** | Check that you chose the root folder of a code project |
| **The CMD window stays open at the end** | That is expected: the BAT waits for a key so you can read the messages |

**Do not run it as administrator:** the tool does not need elevated privileges.

## 7. Protecting data

**Never share private reports of a company project without permission.** They can reveal internal module and file names. Public mode reduces that exposure, but it should also be reviewed before publishing.

The Mapper does not run the project, does not check the database, does not find every dynamic route and is not a replacement for a security review.

## 8. Run the tests (optional)

To check the automated test suite, open CMD in the Mapper folder and type:

~~~bat
py -3 -m unittest discover -s tests -v
~~~

Version 2 reports **34 tests passing on Linux**, using fictitious projects (see the [history of PR #1](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper/pull/1)). **The BAT and the folder picker still need to be checked on a real Windows machine.**

---

[← README](../README.md) · [Version 2 pull request](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper/pull/1)
