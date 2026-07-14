10 LET N=INT(RND*100)
20 PRINT "Auf welche Zahl tippst du?"
30 INPUT G
40 IF G>N THEN GO TO 110
50 IF G<N THEN GO TO 130
60 PRINT "Gut gemacht! Das ist richtig"
70 PRINT "Noch ein Spiel?"
80 INPUT Q$
90 IF Q$="ja" THEN GO TO 10
100 STOP
110 PRINT "Zu gross! Bitte nochmal raten!"
120 GO TO 20
130 PRINT "ZU KLEIN! Bitte nochmal raten!"
140 GO TO 20
