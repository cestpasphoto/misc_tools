#!/usr/bin/env python3
import time
import os
import pickle
import json
import sys

characters={
  "Baby Peach": [ 2.25, 2.00, 2.50, 2.75, 4.00, 2.00, 5.00, 5.00, 4.50, 5.00, 4.25, 4.00	]
, "Baby Rosalina": [ 2.25, 2.00, 2.50, 2.75, 4.25, 2.00, 4.75, 4.75, 4.25, 4.75, 3.75, 4.00	]
, "Baby Mario": [ 2.50, 2.25, 2.75, 3.00, 4.25, 2.25, 4.50, 4.50, 4.00, 4.50, 4.00, 3.75	]
, "Toadette": [ 2.75, 2.50, 3.00, 3.25, 4.25, 2.50, 4.25, 4.25, 3.75, 4.25, 3.50, 3.75	]
, "Koopa Troopa": [ 2.75, 2.50, 3.00, 3.25, 4.00, 2.50, 4.50, 4.50, 4.00, 4.50, 4.25, 3.75	]
, "Toad": [ 3.00, 2.75, 3.25, 3.50, 4.00, 2.75, 4.25, 4.25, 3.75, 4.25, 4.00, 3.50	]
, "Cat Peach": [ 3.25, 3.00, 3.50, 3.75, 4.00, 2.75, 4.00, 4.00, 3.50, 4.00, 3.75, 3.50	]
, "Peach": [ 3.50, 3.25, 3.75, 4.00, 3.75, 3.00, 3.75, 3.75, 3.25, 3.75, 3.75, 3.50	]
, "Tanooki Mario": [ 3.50, 3.25, 3.75, 4.00, 3.75, 3.25, 3.75, 3.75, 3.25, 3.75, 3.25, 3.50	]
, "Mario": [ 3.75, 3.50, 4.00, 4.25, 3.50, 3.50, 3.50, 3.50, 3.00, 3.50, 3.50, 3.25	]
, "Luigi": [ 3.75, 3.50, 4.00, 4.25, 3.50, 3.50, 3.75, 3.75, 3.25, 3.75, 3.25, 3.25	]
, "Rosalina": [ 4.00, 3.75, 4.25, 4.50, 3.25, 3.75, 3.25, 3.25, 2.75, 3.25, 3.75, 3.25	]
, "Metal Mario": [ 4.25, 4.00, 4.50, 4.75, 3.25, 4.50, 3.25, 3.25, 2.75, 3.25, 3.25, 3.00	]
, "Waluigi": [ 4.50, 4.25, 4.75, 5.00, 3.25, 4.00, 3.00, 3.00, 2.50, 3.00, 3.00, 3.00	]
, "Wario": [ 4.75, 4.50, 5.00, 5.25, 3.00, 4.25, 2.75, 2.75, 2.25, 2.75, 3.25, 2.75	]
, "Bowser": [ 4.75, 4.50, 5.00, 5.25, 3.00, 4.50, 2.50, 2.50, 2.00, 2.50, 3.00, 2.75	]
}
# Baby Peach = Baby Daisy
# Baby Rosalina = Lemmy
# Baby Mario = Baby Luigi = Dry Bones = Light Mii
# Toadette = Wendy = Isabelle
# Koopa Troopa = Lakitu = Bowser Jr,
# Toad = Shy Guy = Larry
# Cat Peach = Inkling Girl = Female Villager
# Peach = Daisy = Yoshi
# Tanooki Mario = Inkling Boy = Male Villager
# Mario = Ludwig = Medium Mii
# Luigi = Iggy
# Rosalina = King Boo = Link (both outfits)
# Metal Mario = Gold Mario = Pink Gold Peach
# Waluigi = Donkey Kong = Roy
# Wario = Dry Bowser
# Bowser = Morton = Heavy Mii

bodies={
  "Standard Kart": [	0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, ]
, "Pipe Frame": [ -0.50, -0.50, 0.00, -0.50, 0.50, -0.25, 0.50, 0.25, 0.50, -0.25, 0.25, 0.50, ]
, "Mach 8": [ 0.00, 0.50, 0.00, 0.25, -0.25, 0.25, -0.25, 0.25, 0.00, -0.25, 0.25, 0.00, ]
, "Steel Driver": [ 0.25, -0.25, 0.50, -0.75, -0.75, 0.50, -0.50, -0.50, 0.75, -0.50, 0.00, -0.50, ]
, "Cat Cruiser": [ -0.25, 0.00, -0.25, 0.25, 0.25, 0.00, 0.25, 0.00, 0.00, 0.25, 0.00, 0.25, ]
, "Circuit Special": [ 0.50, 0.25, -0.50, -0.25, -0.75, 0.25, -0.50, -0.25, -0.25, -0.75, -0.50, -0.75, ]
, "Badwagon": [ 0.50, 0.00, -0.25, -0.50, -1.00, 0.50, -0.75, -0.50, -0.25, -0.75, 0.50, -1.00, ]
, "Prancer": [ 0.25, 0.00, 0.00, 0.00, -0.50, -0.25, 0.00, -0.25, 0.25, 0.00, -0.25, -0.25, ]
, "Biddybuggy": [ -0.75, -0.25, -0.50, -0.50, 0.75, -0.50, 0.50, 0.50, 0.50, 0.25, 0.25, 0.75, ]
, "Landship": [ -0.50, -0.75, 0.50, -0.25, 0.50, -0.50, 0.25, -0.25, 0.75, 0.00, 0.75, 0.50, ]
, "Sneeker": [ 0.25, 0.00, -0.25, 0.00, -0.50, 0.00, 0.00, 0.00, 0.00, -0.25, -0.75, -0.25, ]
, "W 25 Silver Arrow": [ -0.25, 0.25, -0.25, 0.00, 0.25, -0.25, 0.25, 0.25, 0.25, 0.00, 0.50, 0.25, ]
, "Blue Falcon": [ 0.25, 0.25, -0.25, 0.00, -0.25, -0.50, -0.25, 0.50, 0.25, -0.50, 0.00, -0.25, ]
, "Tanooki Kart": [ -0.25, 0.00, 0.25, 0.00, -0.50, 0.25, 0.25, 0.00, 0.50, 0.00, 1.00, -0.25, ]
}
# Standard Kart = 300 SL Roadster = The Duke
# Pipe Frame = Varmint = City Tripper
# Mach 8 = Sports Coupe = Inkstriker
# Steel Driver = Tri-Speeder = Bone Rattler
# Cat Cruiser = Comet = Yoshi Bike = Teddy Buggy
# Circuit Special = B-Dasher = P-Wing
# Badwagon = GLA = Standard ATV
# Prancer = Sport Bike = Jet Bike
# Biddybuggy = Mr Scooty
# Landship = Streetle
# Sneeker = Gold Standard = Master Cycle
# W 25 Silver Arrow = Standard Bike = Flame Rider = Wild Wiggler
# Blue Falcon = Splat Buggy
# Tanooki Kart = Koopa Clown = Master Cycle Zero

tires = {
"Standard": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
"Monster": [ 0, 0, -0.25, -0.5, -0.5, 0.5, -0.75, -0.75, -0.5, -0.5, 0.5, -0.25, ],
"Roller": [ -0.5, -0.5, 0, 0, 0.5, -0.5, 0.25, 0.25, 0.25, 0.25, -0.25, 0.75, ],
"Slim": [ 0.25, 0.5, -0.25, -0.25, -0.5, 0, 0.25, 0, 0.25, 0.25, -1, -0.25, ],
"Slick": [ 0.5, 0.5, -0.75, -0.75, -0.75, 0.25, -0.25, -0.25, -0.75, -0.5, -1.25, -0.75, ],
"Metal": [ 0.5, -0.25, 0, -0.25, -1, 0.5, -0.25, -0.5, -0.25, -0.75, -0.75, -0.75, ],
"Button": [ -0.25, 0, -0.25, -0.25, 0.25, -0.5, 0, 0.25, 0, -0.25, -0.5, 0.5, ],
"Off-Road": [ 0.25, 0, 0.25, -0.5, -0.25, 0.25, -0.5, -0.25, -0.5, -0.5, 0.25, -0.5, ],
"Sponge": [ -0.25, -0.25, -0.5, 0.25, 0, -0.25, -0.25, 0, -0.5, 0, 0.25, 0.25, ],
}
# Standard = Blue Standard = GLA Tires
# Monster = Hot Monster = Ancient Tires
# Roller = Azure Roller
# Slim = Wood = Crimson Slim
# Slick = Cyber Slick
# Metal = Gold Tires
# Button = Leaf Tires
# Off-Road = Retro Off-Road = Triforce Tires
# Sponge = Cushion

gliders = {
"Super Glider": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ],
"Cloud Glider": [ -0.25, 0.25, 0, -0.25, 0.25, -0.25, 0, 0, 0, 0.25, 0, 0.25 ],
"Wario Wing": [ 0, 0.25, -0.25, 0, 0, 0.25, 0, -0.25, 0.25, 0, -0.25, 0 ],
"Peach Parasol": [ -0.25, 0.25, -0.25, -0.25, 0.25, 0, 0, -0.25, 0.25, 0.25, -0.25, 0.25 ],
}
# Super Glider = Waddle Wing = Hylian Kite
# Cloud Glider = Parachute = Flower Glider = Paper Glider
# Wario Wing = Plane Glider = Gold Glider = Paraglider
# Peach Parasol = Parafoil = Bowser Kite = MKTV Parafoil

#              Speed Accel Weight Handl Tract
adjustement = [-1,    0  , 0   ,  1,   1.5]

main_combinations = {}
for c_name, c_val in characters.items():
	for b_name, b_val in bodies.items():
		for t_name, t_val in tires.items():
			for g_name, g_val in gliders.items():
				values = [c+b+t+g for c,b,t,g in zip(c_val, b_val, t_val, g_val)]
				main_values = [ values[i] for i in [0,4,5,6,10] ]
				# Corrections
				main_values[2] = 6-main_values[2]
				adjusted_values = [ main_value-delta for main_value,delta in zip(main_values, adjustement)]
				#if min(adjusted_values) >= 3.75:
				#if main_values[1] >= 4 and main_values[2] <= 4.0 and main_values[3] >= 5.25:
				main_combinations[c_name+'+'+b_name+'+'+t_name+'+'+g_name] = (min(adjusted_values), main_values)

maxi_adjusted = max(main_combinations.values(), key=lambda x:x[0])[0]
main_combinations = { n:c for n,c in main_combinations.items() if c[0] >= maxi_adjusted-0.5 }
if len(main_combinations) > 10: main_combinations = { n:c for n,c in main_combinations.items() if c[0] >= maxi_adjusted-0.25 }
if len(main_combinations) > 10: main_combinations = { n:c for n,c in main_combinations.items() if c[0] >= maxi_adjusted      }

best_values_1 = {}
for name, values in main_combinations.items():
	if not any([values == other for other in best_values_1.values() ]):
		best_values_1[name] = values
best_values_2 = {}
for name, values in best_values_1.items():
	if [ all([v<=o for v,o in zip(values,other)]) for other in best_values_1.values() ].count(True) <= 1:
		best_values_2[name] = values
	

print(' '*53, adjustement)
print(' '*54, 'Speed Accel Weig Handl Tract')
for name, values in best_values_2.items():
	print(name, ' '*(50-len(name)), ': ', values[1])


