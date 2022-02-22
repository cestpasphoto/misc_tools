#!/usr/bin/env python3
import camelot # tabula lib much worse than camelot
import re
import argparse
import sys

import logging
from rich.logging import RichHandler
from rich.console import Console
logger = logging.getLogger(__name__)
handler = RichHandler(console=Console(file=sys.stderr))
handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
logger.addHandler(handler)


# logging plus joli et moins verbeux en mode normal
# Commentaires dans le code, renommer
# try / catch pour gerer les erreurs de page
# Export en .exe portable windows

def readMultipleLines(liste, startIndex, continueIf=','):
	string = ''
	while (string.strip() == '' or string.strip()[-1] == continueIf):
		if startIndex >= len(liste):
			logger.debug('debug data: ' + str(liste[-1]) + ' ' + str(startIndex) + ' ' + string)
			startIndex = None
			break
		else:
			string += liste[startIndex]
			startIndex += 1
	return (string.strip(), startIndex)



# Aller a la 1e ligne non vide de INSEE, puis regarder lignes suivantes
# si INSEE non vide                 , endIndex = l
# si insee vide  ville vide       poste vide     , ligne suivante
# si insee vide  ville vide       poste non vide , ligne suivante
# si insee vide  ville non vide   poste vide     , endIndex = l
# si insee vide  ville non vide   poste non vide , ? endIndex = l

##### Exemple 1 ####
#  7   SAINT FORT SUR LE NE  16316                 16130
#  8         SAINT MEME LES  16340                 16720
#  9              CARRIERES                             
# 10           SAINT PREUIL  16343                 16130
##### Exemple 2 ####
#  5                 AUBERIE  63014    63172, 63174, 63177, 63178,
#  6                                   63179, 63170, 63175, 63176,
#  7                                                  63171, 63173
#  8                  AULNAT  63019                          63510
##### Exemple 3 ####
# 29   ST GENES-CHAMPANELLE  63345                        63122                              
# 30                 DALLET                                                                  
# 31                         63133                        63111                              
# 32                  MEZEL                                                                  
# 33                         63226                        63115                              
# 34    PERIGNAT-SUR-ALLIER                                                                  
# 35                         63273          63802, 63801, 63800                              
# 36         MUR-SUR-ALLIER  63226                        63115


def readLine(table, startIndex):
	# Avance jusqu'a trouver un INSEE non nul
	# puis avance jusqu'a trouver un INSEE non nul ou nom ville non nul
	phase1 = True
	endIndex = len(table.df[0])
	for i in range(startIndex, len(table.df[0])):
		if phase1:
			if table.df[1][i].strip() != '':
				phase1 = False
		else:
			if table.df[1][i].strip() != '' or table.df[0][i].strip() != '':
				endIndex = i
				break

	resultat = []
	for x in range(0, 3):
		l = [table.df[x][i] for i in range(startIndex, endIndex)]
		resultat.append(''.join(l))
	return resultat, endIndex

def parse_pdf_lettice(pdfLink, page):
	tables = camelot.read_pdf(pdfLink, pages=str(page), copy_text=['h','v'])
	logger.debug(str(len(tables)) + ' table(s) found on page ' + str(page))
	result = ""

	for table in tables:
		if table.df.shape[1] == 5:
			logger.warning('Not sure of the result for page ' + str(table.page) + ' because only 5 columns instead of 6')
		elif table.df.shape[1] != 6:
			logger.debug('Skipping this table because doesnt have 5 or 6 columns: ' + str(table.df.shape))
			continue

		for row in range(table.shape[0]):
			# Check if header or not
			strings = ''.join([ table.df[i][row] for i in range(5) ])
			if 'INSEE' in strings or 'POSTAL' in strings:
				if row != 0: logger.debug('Dropping row ' + string(row) + ' because containing headers')
				continue
			else:
				if row == 0: logger.debug('Row 0 does NOT contain headers')

			# Read the rate
			taux_set = set([x.strip() for x in table.df[3][row].split('\n') if x.strip() != ''])
			nb_taux = len(taux_set)
			if nb_taux == 1:
				taux = list(taux_set)[0].strip('*')
			else:
				taux = None
				logger.warning('Multiple or none rate found in same table:' + str(taux_set))

			# Read other columns
			communes   = table.df[0][row].split('\n')
			insees     = table.df[1][row].split('\n')
			codePostes = table.df[2][row].split('\n')
			iCommune, iInsee, iPostal = 0, 0, 0
			parsed_data = []
			while iCommune < len(communes):
				commune  , iCommune = readMultipleLines(communes  , iCommune, continueIf='-')
				insee    , iInsee   = readMultipleLines(insees    , iInsee)
				codePoste, iPostal  = readMultipleLines(codePostes, iPostal , continueIf=',')
				if iCommune is None or iInsee is None or iPostal is None:
					logger.error('Cant align columns on page ' + str(page))
					return None
				parsed_data.append([commune, insee, codePoste])
			
			if parsed_data is None:
				return None

			logger.debug('Success on row ' + str(row) + ', converting parsed data to csv')
			for data in parsed_data:
				result += data[0].strip(' -')          + ';'
				result += data[1]                      + ';'
				result += data[2]                      + ';'
				result += taux if taux is not None else '' + ';'
				result += '\n'

	return result

def parse_pdf_stream(pdfLink, page):
	tables = camelot.read_pdf(pdfLink, pages=str(page), flavor='stream')
	logger.debug(str(len(tables)) + ' table(s) found on page ' + str(page))
	result = ""

	for table in tables:
		if   table.df[0][0].replace('\n', '').startswith('IDENTIFIANT'):
			startIndex = 4
		elif table.df[0][1].replace('\n', '').startswith('IDENTIFIANT'):
			startIndex = 5
		elif table.df[0][0].replace('\n', '').startswith('COMMUNES'):
			startIndex = 2
		elif table.df[0][1].replace('\n', '').startswith('COMMUNES'):
			startIndex = 3
		else:
			logger.warning('Output CSV will be incomplete on page ' + str(page) + ' because table headers are incorrect')
			logger.debug('Table headers = ' + table.df[0][0][:20] + ' ' + table.df[0][1][:20])
			continue
		if table.df.shape[1] == 5:
			logger.warning('Not sure of the result for page ' + str(table.page) + ' because only 5 columns instead of 6')
		elif table.df.shape[1] != 6:
			logger.debug('Skipping this table because doesnt have 5 or 6 columns', str(table.df.shape))
			continue

		# Look for startIndex
		for i in range (1, 5):
			for col in range(1, table.df.shape[1]):
				if table.df[col][i].strip().isnumeric():
					startIndex = i
					break
			else:
				string = table.df[0][i].strip()
				if string.isalpha() and not string.startswith('COMMUNES') and not string.startswith('CONCERNEES'):
					startIndex = i
					break
			# Continue if not broke, else propagate the 'break'
				continue
			break
		
		# Read the rate
		taux_set = set()
		for col in range(3, table.df.shape[1]):
			taux_set.update( set(table.df[col][startIndex:]) )
		# Look for percentage
		liste_taux = []
		for colonne in taux_set:
			liste_taux += re.findall(r'-?\d+,\d+\ ?\%', colonne)
		nb_taux = len(liste_taux)
		if nb_taux == 1:
			taux = liste_taux[0].strip('*')
		else:
			taux = None
			logger.warning('Multiple or none rate found in same table:' + str(taux_set))

		logger.debug('Success, converting parsed data to csv')
		index = startIndex
		while index < len(table.df[0]):
			line_data, index = readLine(table, index)
			result += line_data[0].strip(' -')         + ';'
			result += line_data[1]                     + ';'
			result += line_data[2]                     + ';'
			result += taux if taux is not None else '' + ';'
			result += '\n'

	return result

def parsePDF(pdfLink, pages, page_break=False):
	output_csv = ""
	for page in pages:
		logger.info('Parsing page ' + str(page))
		page_csv = parse_pdf_lettice(pdfLink, page)

		if page_csv is None:
			logger.warning('Parsing failed on page ' + str(page) + ', starting again using fallback method... and crossing fingers')
			page_csv = parse_pdf_stream(pdfLink, page)

		if page_csv is None:
			logger.warning('Fallback method also failed on page ' + str(page))
			logger.error('Cant read page ' + str(page) + ' this page will be skipped')
		else:
			if page_break:
				output_csv += 'page ' + str(page) + '\n'
			output_csv += page_csv
	return output_csv

def autodetect_page():
	import myparser
	from bs4 import BeautifulSoup
	urssaf_site = 'https://www.urssaf.fr/portail/home/utile-et-pratique/lettres-circulaires.html'
	try:
		html = myparser.readPage(urssaf_site, headers='firefox', printErr=False)
	except myparser.urllib.error.HTTPError:
		logger.error('Cant read site of urssaf, please download document by yourself and use --input option')
		return
	soup = BeautifulSoup(html, 'lxml')
	last_news = soup.find('table', attrs={'class': 'cnirtable lettreRecherche'})
	link_suffix = last_news.find('tbody').findAll('td')[0].find('a')['href']
	link = 'https://www.urssaf.fr' + link_suffix
	logger.info('Last document is on page ' + link)
	return link


def main():
	parser = argparse.ArgumentParser(description='Lecteur de PDF URSSAF pour Marie')
	parser.add_argument('--input'      , '-i', action='store', default='web'       , help='input PDF from URSSAF (or "web" to get online data)')
	parser.add_argument('--output'     , '-o', action='store', default='marie.csv' , help='output csv')
	parser.add_argument('--begin'      , '-b', action='store', default='1'         , help='first page to parse')
	parser.add_argument('--end'        , '-e', action='store', default='1000'      , help='last  page to parse')
	parser.add_argument('--nopb'       , '-p', action='store_true'                 , help='disable dedicated line in output for each new page')
	parser.add_argument('--debug'            , action='store_true'                 , help='enable debugging info')
	args = parser.parse_args()

	logger.setLevel(level=logging.INFO)
	if args.debug:
		logger.setLevel(level=logging.DEBUG)
	if args.input == 'web':
		# args.input = 'https://www.urssaf.fr/portail/files/live/sites/urssaf/files/Lettres_circulaires/2020/ref_LCIRC-2020-0000005.pdf?origine=recherche'
		args.input = autodetect_page()
	
	try:
		logger.info('Loading pdf and checking number of pages (ignore any "UserWarning")')
		tablesTmp = camelot.read_pdf(args.input, pages='1-end', flavor='stream')
	except:
		logger.critical('Cant any pdf in file/url ' + args.input[:20])
		return
	pageMin = max(int(args.begin), tablesTmp[0] .parsing_report['page'])
	pageMax = min(int(args.end)  , tablesTmp[-1].parsing_report['page'])
	# pageMin = int(args.begin)
	# pageMax = int(args.end)
	logger.info('Reading page ' + str(pageMin) + ' to ' + str(pageMax))

	csv = parsePDF(pdfLink=args.input, pages=range(pageMin, pageMax+1), page_break=not(args.nopb))
	logger.info('Writing csv info to ' + args.output)
	with open(args.output,'wb') as f:
		f.write(csv.encode('windows-1252'))
	logger.debug('Done')

main()
