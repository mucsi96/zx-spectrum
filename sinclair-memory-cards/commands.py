"""Sinclair BASIC keywords of the rubber-key 48K ZX Spectrum, grouped by difficulty.

This is the full set of *named* keyword tokens printed on the keyboard in white
(keyword mode), green (extended mode) and red (symbol shift / extended-symbol shift).
Only the bare comparison glyphs (<=, >=, <>) and pure punctuation symbols are left
out, since they are not named commands and do not work as a picture.

Each entry has:
  cmd  - the keyword printed on the "word" card
  does - a plain explanation, fed to Claude so it can invent a pictogram

The decks let you play with a subset. They are ordered by how useful/approachable
a command is for a young beginner, not by keyboard colour:
  simple       - the commands you type every session, plus colour and sound
  intermediate - graphics, data, sequences, the printer, files and common functions
  advanced     - the maths and machine-level functions (rarely needed by a beginner)
"""

COMMANDS = {
    "simple": [
        {"cmd": "PRINT", "does": "Shows words or numbers on the screen."},
        {"cmd": "LET", "does": "Stores a value in a named variable, e.g. LET a=5."},
        {"cmd": "INPUT", "does": "Asks the person to type something in while the program runs."},
        {"cmd": "RUN", "does": "Starts the program from the beginning."},
        {"cmd": "LIST", "does": "Shows the program lines on the screen."},
        {"cmd": "CLS", "does": "Clears the whole screen."},
        {"cmd": "NEW", "does": "Erases the program from memory so you can start fresh."},
        {"cmd": "GOTO", "does": "Jumps to a different line number."},
        {"cmd": "GOSUB", "does": "Calls a little subroutine, then comes back."},
        {"cmd": "RETURN", "does": "Goes back from a subroutine to just after the GOSUB."},
        {"cmd": "IF", "does": "Does something only when a test is true (IF ... THEN)."},
        {"cmd": "THEN", "does": "Comes after IF and says what to do when the test is true."},
        {"cmd": "FOR", "does": "Starts a counting loop that repeats until NEXT."},
        {"cmd": "TO", "does": "Gives the end value of a FOR counting loop."},
        {"cmd": "STEP", "does": "Says how big each jump of a FOR loop is."},
        {"cmd": "NEXT", "does": "Goes back to repeat the FOR loop with the next count."},
        {"cmd": "PAUSE", "does": "Waits quietly for a chosen number of moments."},
        {"cmd": "STOP", "does": "Stops the program right where it is."},
        {"cmd": "REM", "does": "A remark: a note for people that the computer ignores."},
        {"cmd": "BORDER", "does": "Colours the frame around the edge of the screen."},
        {"cmd": "PAPER", "does": "Sets the background colour behind the letters."},
        {"cmd": "INK", "does": "Sets the colour of the letters and drawings."},
        {"cmd": "FLASH", "does": "Makes letters flash between two colours."},
        {"cmd": "BRIGHT", "does": "Makes the colours glow brighter."},
        {"cmd": "INVERSE", "does": "Swaps the ink and paper colours over."},
        {"cmd": "OVER", "does": "Draws on top of what is already on the screen."},
        {"cmd": "BEEP", "does": "Plays a beep of a chosen pitch and length."},
        {"cmd": "CLEAR", "does": "Empties all the variables."},
        {"cmd": "CONTINUE", "does": "Carries on a program that had stopped."},
        {"cmd": "COPY", "does": "Prints a copy of the screen on the printer."},
        {"cmd": "LOAD", "does": "Loads a program in from tape."},
        {"cmd": "SAVE", "does": "Saves a program out onto tape."},
    ],
    "intermediate": [
        {"cmd": "PLOT", "does": "Lights up a single dot at an x,y position."},
        {"cmd": "DRAW", "does": "Draws a line from the last dot to a new point."},
        {"cmd": "CIRCLE", "does": "Draws a circle of a chosen size around a point."},
        {"cmd": "POKE", "does": "Writes a number straight into a memory address."},
        {"cmd": "PEEK", "does": "Reads the number stored at a memory address."},
        {"cmd": "DIM", "does": "Sets aside space for an array: a list or table."},
        {"cmd": "DATA", "does": "Holds a list of values ready for READ to fetch."},
        {"cmd": "READ", "does": "Takes the next value out of a DATA list."},
        {"cmd": "RESTORE", "does": "Sends READ back to the start of the DATA."},
        {"cmd": "RANDOMIZE", "does": "Shakes up the random-number generator."},
        {"cmd": "AT", "does": "Chooses the row and column to print at."},
        {"cmd": "TAB", "does": "Moves printing across to a chosen column."},
        {"cmd": "LINE", "does": "A whole-line option, e.g. make a saved program auto-run."},
        {"cmd": "LPRINT", "does": "Prints words on the printer instead of the screen."},
        {"cmd": "LLIST", "does": "Lists the program on the printer."},
        {"cmd": "LEN", "does": "Tells how many letters are in a word."},
        {"cmd": "STR$", "does": "Turns a number into a string of characters."},
        {"cmd": "VAL", "does": "Turns a string of digits back into a number."},
        {"cmd": "VAL$", "does": "Works out a string from a string expression."},
        {"cmd": "CHR$", "does": "Gives the character that belongs to a code number."},
        {"cmd": "CODE", "does": "Gives the code number of a character."},
        {"cmd": "RND", "does": "Gives a random number."},
        {"cmd": "INKEY$", "does": "Reads which key is being pressed right now."},
        {"cmd": "AND", "does": "True only when both tests are true."},
        {"cmd": "OR", "does": "True when either test is true."},
        {"cmd": "NOT", "does": "Flips true into false and false into true."},
        {"cmd": "DEF FN", "does": "Defines your own new function."},
        {"cmd": "FN", "does": "Uses a function you made with DEF FN."},
        {"cmd": "MERGE", "does": "Loads a program and mixes it into the current one."},
        {"cmd": "VERIFY", "does": "Checks that a saved tape matches the program."},
        {"cmd": "CAT", "does": "Lists the files stored on a microdrive."},
        {"cmd": "FORMAT", "does": "Prepares a microdrive cartridge for use."},
        {"cmd": "MOVE", "does": "Moves data between channels or files."},
        {"cmd": "ERASE", "does": "Deletes a file from a microdrive."},
        {"cmd": "OPEN #", "does": "Opens a channel or file to talk to."},
        {"cmd": "CLOSE #", "does": "Closes a channel or file when finished."},
        {"cmd": "IN", "does": "Reads a value from a hardware port."},
        {"cmd": "OUT", "does": "Sends a value out to a hardware port."},
    ],
    "advanced": [
        {"cmd": "SIN", "does": "The sine of an angle: a smooth up-and-down wave."},
        {"cmd": "COS", "does": "The cosine of an angle: a smooth wave."},
        {"cmd": "TAN", "does": "The tangent of an angle."},
        {"cmd": "ASN", "does": "The angle whose sine is a value (arcsine)."},
        {"cmd": "ACS", "does": "The angle whose cosine is a value (arccosine)."},
        {"cmd": "ATN", "does": "The angle whose tangent is a value (arctangent)."},
        {"cmd": "LN", "does": "The natural logarithm of a number."},
        {"cmd": "EXP", "does": "The number e raised to a power."},
        {"cmd": "INT", "does": "Rounds a number down to a whole number."},
        {"cmd": "SQR", "does": "The square root of a number."},
        {"cmd": "SGN", "does": "The sign of a number: minus, zero or plus."},
        {"cmd": "ABS", "does": "The size of a number, ignoring any minus sign."},
        {"cmd": "PI", "does": "The number pi, about 3.14159."},
        {"cmd": "USR", "does": "Runs a machine-code routine at an address."},
        {"cmd": "BIN", "does": "Writes a number in binary: only ones and zeros."},
        {"cmd": "POINT", "does": "Tells whether a screen dot is switched on or off."},
        {"cmd": "SCREEN$", "does": "Reads the character shown at a screen position."},
        {"cmd": "ATTR", "does": "Reads the colours in force at a screen position."},
    ],
}

# Per-group display info. No colours on the cards themselves (colour is only ever
# used inside the AI pictures). Decks are told apart by a number of small faint dots
# ("rank"), so a deck can still be sorted out after the cards are cut.
GROUP_STYLE = {
    "simple":       {"label": "Simple",       "rank": 1},
    "intermediate": {"label": "Intermediate", "rank": 2},
    "advanced":     {"label": "Advanced",     "rank": 3},
}

GROUP_ORDER = ["simple", "intermediate", "advanced"]
