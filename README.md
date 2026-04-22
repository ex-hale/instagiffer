# Instagiffer 🚧 2.x WIP 🚧

We're about to bring this classic into a new era! There are great plans but whatever will happen here: Instagiffer will remain an easy to use, free for all tool. And it's still called "*GIF*"!

This being said: **Things can and will break**! If you want a stable version please refer to the [main branch](https://github.com/ex-hale/instagiffer/tree/master) and [it's latest releases](https://github.com/ex-hale/instagiffer/releases).

## Be a part!

Please take part in the process, [**file a 2.x-issue**](https://github.com/ex-hale/instagiffer/issues/new?labels=2.x) and lets discuss ideas and features!

## Ideas so far

- [ ] **a solid backend** - Instagiffer 2.x has a stable core module that works entirely UI-free and can be driven the same way via command line, unit tests or any interfaces.
  - [ ] **in-memory** as much as possible - We'll try to replace things that were done by ImageMagick CLI with PIL, reducing from and to disk reads and writes so things remain responsive in the UI and you get to your results quicker.
  - [ ] **serializable projects** - what you put together you can revisit, spin it off some more, remix, or share recipes with others. The backend will save things into its temp (If you want that! It can be optional of course) and make it available to the UI to fill out fields and all.
  - [ ] **beyond gif** - we'll explore outputting other formats to convey the gif-idea. There's already a multitude of ways to input things and since we're still powered by `ffmpeg` it'd be easy to go for new animated image and video formats too.
- [ ] **fresh frontend**  - Tkinter shows it's age. It deserves our respect but honestly: **Qt for Python** ran so far ahead! There is [so much on board already](https://doc.qt.io/qtforpython-6/api.html#pyside-api) we can use:
  - [ ] **Signals and threads** - responsive UIs are not only about changing window size and High-DPI. That will come as well!! but also non-blocking tasks and background workers that make things available asap.
  - [ ] **Themes** - dark/light mode is nothing new anymore but that will come almost out of the box with Qt. And much more. Might be we spin up a retro Tk-flavor theme to remember the good times.
  - [ ] **built-in packaging** Qt for Python comes with [pyside6-deploy](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html#pyside6-deploy) we might replace some of our build tooling and get fast and solid packages for all platforms ([including Android?](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html))
  - [ ] **Translated UI** - let's try to incorporate [**weblate**](https://weblate.org) for internationalized texts and documentation (Qt has it's own translation tool. Might also work, let's investigate, but no idea how it fits with community internationalization)
- [ ] **fresh DX** - let's also try some of these fancy new developer tools like `uv`, `ruff` and `ty` by [astral.sh](https://astral.sh/)

## Dev setup

* get `uv` ([docs](https://github.com/astral-sh/uv#installation))
  ```
  # On macOS and Linux.
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # On Windows.
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

* get the code of this branch directly
  ```
  git clone -b 2.x https://github.com/ewerybody/instagiffer

  cd instagiffer
  ```

* sync the project
  ```
  uv sync
  ```

* check for dependencies
  ```
  uv run poe deps
  ```

* run the unit test(s) ... wip
  ```
  uv run pytest
  ```

* run the main entry file (not much yet)
  ```
  uv run instagiffer
  ```

* setup your IDE
  * VS Codium/Code
    * get the Python extension
    * turn off Pylance, I recommend to get the `ty` extension instead!

    * there are 2 Debug configurations set up already
        * **Instagiffer** - runs the main entry script
        * **Py: Current File** - runs the current file with the set Python interpreter. Make sure it's set to the one in the `.venv`


much more to come ...
