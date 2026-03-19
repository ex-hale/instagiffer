# Instagiffer 🚧 2.x WIP 🚧

We're about to bring this classic into a new era! There are great plans but whatever will happen here: Instagiffer will remain an easy to use, free for all tool.

This being said: **Things can and will break**! If you want a stable version please refer to the [main branch](https://github.com/ex-hale/instagiffer/tree/master) and [it's latest releases](https://github.com/ex-hale/instagiffer/releases).

## Be a part!

Please take part in the process, [**file a 2.x-issue**](https://github.com/ex-hale/instagiffer/issues/new?labels=2.x) and lets discuss ideas and features!

## Ideas so far

- [ ] **a solid backend** - Instagiffer has a stable core module that works entirely UI-free and can be driven the same way via command line, unit tests or any interfaces.
  - [ ] **in-memory** as much as possible - We'll try to replace things that were done by ImageMagick CLI with PIL, reducing from and to disk reads and writes so things remain responsive in the UI and you get to your results quicker.
  - [ ] **serializable projects** - what you put together you can revisit, spin it off some more, remix, or share recipes with others. The backend will save things into its temp (If you want that! It can be optional of course) and make it available to the UI to fill out fields and all.
- [ ] **Qt for Python** frontend - Tkinter shows it's age. It deserves our respect but honestly: Qt ran so far ahead! There is so much we can use
  - [ ] **Signals and threads** - responsive UIs are not only about changing window size and High-DPI. That will come as well!! but also non blocking tasks and background workers that make things available asap.
  - [ ] **Themes** - dark/light mode is nothing new anymore but that will come almost out of the box with Qt. And much more. Might be we spin up a retro Tk-flavor theme to remember the good times.

much more to come ...