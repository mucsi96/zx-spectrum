" Vim syntax file for NextBASIC plain-text listings (ZX Spectrum Next kiosk)
" Colors follow the SpecNext-IDE-style scheme: bright Spectrum palette on dark.

if exists("b:current_syntax")
  finish
endif

syntax case match

" Line numbers at the start of a line
syntax match nextbasicLineNo "^\s*\d\+"

" Statements
syntax keyword nextbasicStatement PRINT LPRINT INPUT LET DIM READ DATA RESTORE
syntax keyword nextbasicStatement FOR NEXT IF THEN ELSE RUN STOP CONTINUE RETURN
syntax keyword nextbasicStatement PAUSE POKE RANDOMIZE CLS CLEAR NEW LIST LLIST
syntax keyword nextbasicStatement LOAD SAVE MERGE VERIFY ERASE CAT FORMAT MOVE
syntax keyword nextbasicStatement BEEP BORDER PLOT DRAW CIRCLE INK PAPER FLASH
syntax keyword nextbasicStatement BRIGHT INVERSE OVER OUT COPY GOTO GOSUB
syntax match nextbasicStatement "\<GO TO\>"
syntax match nextbasicStatement "\<GO SUB\>"
syntax match nextbasicStatement "\<DEF FN\>"

" Functions
syntax keyword nextbasicFunction RND PI FN POINT ATTR AT TAB CODE VAL LEN SIN COS
syntax keyword nextbasicFunction TAN ASN ACS ATN LN EXP INT SQR SGN ABS PEEK IN
syntax keyword nextbasicFunction USR NOT BIN
syntax match nextbasicFunction "\<\(INKEY\|SCREEN\|VAL\|STR\|CHR\)\$"

" Word operators
syntax keyword nextbasicWordOp AND OR TO STEP LINE

" Numbers
syntax match nextbasicNumber "\<\d\+\(\.\d\+\)\=\([eE][+-]\=\d\+\)\="

" ZX escapes: UDGs \a..\u, \xHH, \\, zmakebas block escapes
syntax match nextbasicEscape "\\\(\\\|[a-uA-U]\|[xX][0-9A-Fa-f][0-9A-Fa-f]\|[.',:][.',:]\)" contained containedin=nextbasicString
syntax match nextbasicEscape "\\\(\\\|[a-uA-U]\|[xX][0-9A-Fa-f][0-9A-Fa-f]\|[.',:][.',:]\)"

" Block graphics as Unicode quadrant characters
syntax match nextbasicBlock "[▘▝▀▖▌▞▛▗▚▐▜▄▙▟█]\+" containedin=nextbasicString

" Strings
syntax region nextbasicString start=+"+ end=+"+ contains=nextbasicEscape,nextbasicBlock

" REM comments (rest of the line)
syntax match nextbasicComment "\<REM\>.*$" contains=nextbasicEscape,nextbasicBlock

highlight default link nextbasicLineNo    LineNr
highlight default link nextbasicStatement Statement
highlight default link nextbasicFunction  Function
highlight default link nextbasicWordOp    Operator
highlight default link nextbasicNumber    Number
highlight default link nextbasicString    String
highlight default link nextbasicComment   Comment
highlight default link nextbasicEscape    SpecialChar
highlight default link nextbasicBlock     SpecialChar

let b:current_syntax = "nextbasic"
