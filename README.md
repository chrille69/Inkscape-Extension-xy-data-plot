# Inkscape Extension xy-data-plot

This repository contains an inkscape-extensions for plotting xy-data.

## Requirements

- Inkscape 1.2
- Python 3.8

## Installation

Put the files

```
xy-data-plot.inx
xy-data-plot.py
```

into your extension-directory. You will find the directory under `Edit -> Settings -> System`.

## Usage

- Create a rectangle and select it.
- Choose the xy-data-plot-extension under `Extensions -> Render`.
- Provide a well-formed CSV-file. You find an example in the repository.

## Workaround for logarithmic scales

Recalculate the values of your axis: Build the logarithm to the Base of 10 of
every value in this axis. Disable subticks in the extension and rename the ticklabels (eg. 1, 10, 100)
after the creation of the plot.

Happy inkscaping
