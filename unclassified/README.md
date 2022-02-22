# unclassified
### lcirc.py
Generate computer-friendly version of a circular letter of a French administration (taux de versement transport).  
It either downloads PDF from the web or use the user-provided PDF file; starting/ending page number can be specified to speed up processings or avoid a exception page.  
Main challenge is to parse the file: data may be visually aligned between columns, but it is not always the case on the table in PDF. We had to use 2 different approachs based on the conditions and pick the best result.


### mario_kart.py
Computes best car/body/tire/glider combination(s) in Mario Kart 8 (Switch).
It computes each criteria (speed, acceleration, weight, handling, traction), and gives a rating to the whole combination based on the maximum criteria after adjustement based on user preference. By default, it gives more priority to traction and handling, and less priority to speed: 

	#              Speed Accel Weight Handl Tract
	adjustement = [-1,    0  , 0   ,  1,   1.5]