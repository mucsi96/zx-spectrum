"""Sinclair BASIC commands for the ZX Spectrum, grouped by difficulty.

Each command has:
  cmd  - the BASIC keyword printed on the "word" card
  desc - a short, child-friendly one-liner printed under the keyword
  does - a plain explanation, fed to Claude so it can invent a pictogram idea

Groups:
  simple       - the commands a beginner types first, every session
  intermediate - loops, decisions, sound and colour
  advanced      - graphics, memory pokes, data structures (rarely used by a beginner)

Eight commands per group => 8 word cards + 8 picture cards = 16 cards, one A4 page.
"""

COMMANDS = {
    "simple": [
        {"cmd": "PRINT", "desc": "Shows words or numbers on the screen",
         "does": "Displays text or numbers on the TV screen."},
        {"cmd": "LET", "desc": "Keeps a number or word in a named box",
         "does": "Stores a value in a variable, e.g. LET a=5."},
        {"cmd": "INPUT", "desc": "Waits for you to type something in",
         "does": "Asks the person to type a value while the program is running."},
        {"cmd": "RUN", "desc": "Starts your program from the beginning",
         "does": "Runs the BASIC program that is currently in memory."},
        {"cmd": "LIST", "desc": "Shows all the lines of your program",
         "does": "Lists the program lines on the screen so you can read them."},
        {"cmd": "CLS", "desc": "Wipes the screen clean",
         "does": "Clears everything off the screen."},
        {"cmd": "GOTO", "desc": "Jumps to another line number",
         "does": "Sends the program to carry on at a different line number."},
        {"cmd": "NEW", "desc": "Throws the program away to start fresh",
         "does": "Erases the whole program from memory so you can begin again."},
    ],
    "intermediate": [
        {"cmd": "IF", "desc": "Does something only if it is true",
         "does": "Runs a command only when a test is true, as in IF ... THEN."},
        {"cmd": "FOR", "desc": "Repeats something a set number of times",
         "does": "Starts a counting loop that repeats until NEXT."},
        {"cmd": "GOSUB", "desc": "Runs a helper part, then comes back",
         "does": "Calls a little subroutine and returns afterwards with RETURN."},
        {"cmd": "BEEP", "desc": "Makes a sound or a musical note",
         "does": "Plays a beep of a chosen pitch and length through the speaker."},
        {"cmd": "PAUSE", "desc": "Waits quietly for a little while",
         "does": "Stops the program for a chosen number of moments."},
        {"cmd": "BORDER", "desc": "Colours the edge around the screen",
         "does": "Sets the colour of the border frame around the screen."},
        {"cmd": "PAPER", "desc": "Colours the background behind letters",
         "does": "Sets the background colour that letters are printed on."},
        {"cmd": "INK", "desc": "Colours the letters and the drawings",
         "does": "Sets the colour used for printing and drawing."},
    ],
    "advanced": [
        {"cmd": "PLOT", "desc": "Lights up one tiny dot on the screen",
         "does": "Draws a single dot (pixel) at a chosen x,y position."},
        {"cmd": "DRAW", "desc": "Draws a straight line on the screen",
         "does": "Draws a line from the last dot to a new position."},
        {"cmd": "CIRCLE", "desc": "Draws a round circle",
         "does": "Draws a circle of a chosen size around a point."},
        {"cmd": "POKE", "desc": "Puts a number straight into memory",
         "does": "Writes a number directly into a memory address in the machine."},
        {"cmd": "PEEK", "desc": "Peeks at a number hidden in memory",
         "does": "Reads the number stored at a memory address."},
        {"cmd": "DATA", "desc": "Keeps a list of values ready to use",
         "does": "Stores a list of values that READ can fetch later."},
        {"cmd": "DIM", "desc": "Makes room for a list or a table",
         "does": "Sets aside space for an array of numbers or letters."},
        {"cmd": "RANDOMIZE", "desc": "Shakes the dice for random numbers",
         "does": "Mixes up the random number generator so numbers are unpredictable."},
    ],
}

# Display colours per group (border / light fill), used on the printed cards.
GROUP_STYLE = {
    "simple":       {"label": "Simple",       "border": "#2E7D32", "fill": "#E8F5E9"},
    "intermediate": {"label": "Intermediate", "border": "#E65100", "fill": "#FFF3E0"},
    "advanced":     {"label": "Advanced",     "border": "#6A1B9A", "fill": "#F3E5F5"},
}

GROUP_ORDER = ["simple", "intermediate", "advanced"]
