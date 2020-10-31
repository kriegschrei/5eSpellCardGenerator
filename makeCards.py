#!/usr/bin/env python3
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color
import csv
from optparse import OptionParser
import json
from colorthief import ColorThief
from textwrap import wrap,fill
import math
import re
import random #testing only	

TITLE_FONT        = 'dalelands.ttf'
SCHOOL_FONT  = 'mplantinitalic.ttf'
DEFAULT_FONT = 'mplantin.ttf'

COLORS = {
	'Cantrip' : 'Snow',
	'C' : 'Snow',
	'0' : 'Snow',
	'1' : 'LightPink',
	'2' : 'DeepPink',
	'3' : 'Red',
	'4' : 'Orange',
	'5' : 'Yellow',
	'6' : 'Green',
	'7' : 'SkyBlue',
	'8' : 'Blue',
	'9' : 'Purple'
}

ASSET_PATH = 'Assets'
TIME_REGEX = re.compile('(?P<spec>instantaneous|hour|minute|day|bonus|reaction|action|round)',re.IGNORECASE)
RANGE_REGEX = re.compile('(?P<spec>self|touch|ft|radius|mile|sight)',re.IGNORECASE)
TARGET_REGEX = re.compile('(?P<spec>humanoid|creature|self|sphere|cone|line|square|cube|radius)',re.IGNORECASE)
SAVE_REGEX = re.compile('(?P<spec>str|int|cha|wis|dex|con)',re.IGNORECASE)
EFFECT_REGEX = re.compile('(?P<spec>acid|bludgeoning|buff|charmed|cold|combatdefense|communication|control|creation|debuff|detection|exploration|fire|force|foreknowledge|frightened|healing|light|lightning|melee|movement|necrotic|piercing|poison|prone|psychic|radiant|ranged|restrained|shapechanging|social|summoning|thunder|unconcious|utility|warding)',re.IGNORECASE)
PIXEL_BUFFER = 2
BORDER_OFFSET = 5
TOP_OFFSET = 25
parser = OptionParser()
parser.add_option('-c','--config',dest='configFile',help='CSV file to read')
(opts,args) = parser.parse_args()

def main():
	spells,spellList = readSpellList(opts.configFile)
	spellBook = []
	spellCount = len(spells)
	sideBorderPixels = 91 # .50 inches
	bufferPixels = 6
	topBottomBorderPixels = 147
	thisTop = topBottomBorderPixels
	thisLeft = sideBorderPixels
	maxCol = 4
	maxRow = 2
	currentPage = 1
	idx = 0
	pages = []

	while idx < spellCount:
		thisPage = makeNewImage(2200,1700)
		currentRow = 1
		thisTop = topBottomBorderPixels
		while currentRow <= maxRow and idx < spellCount:
			currentCol = 1
			thisLeft = sideBorderPixels
			while currentCol <= maxCol and idx < spellCount:
				s = spellList[idx]
				print('Working on spell {0}, idx {1}, page {2}, row {3}, col {4}'.format(s,idx,currentPage,currentRow,currentCol))
				spell = Spell(spells[s],s)
				card = makeCard(spell)
				print('Adding image {0} to page {1}'.format(idx,currentPage))
				#print(thisPage)
				#print(card)
				thisPage.composite(card,thisLeft,thisTop)
				thisLeft += bufferPixels + card.width
				idx += 1
				currentCol += 1
			thisTop  += card.height + bufferPixels
			currentRow += 1
		thisPage.save(filename='page_{0}.pdf'.format(currentPage))
		currentPage += 1
		
def makeCard(spell):
	card = Card(spell.name)
	card.title=spell.name
	print('SPELL {0}:'.format(card.title))
	card.schoolColor          = getSchoolColor(spell.school)
	card.schoolIcon	           = makeRoundIcon(spell.school)
	card.titleBar	           = makeRectangle(card.card.width-10,card.schoolIcon.height,card.schoolColor)
	card.spellLevelMarker = makeSpellLevelMarker(spell.level.upper())
	card.spellLevelText      = makeText(
		spell.level.upper(),
		800,
		600,
		'black',
		'center',
		TITLE_FONT,
		getTextToFitSize(spell.level.upper(),card.spellLevelMarker.width-10,card.spellLevelMarker.height-20)
	)
	
	card.titleText = makeText(
		card.title.upper(),
		(card.titleBar.width - card.schoolIcon.width - card.spellLevelMarker.width-25),
		card.titleBar.height-4,
		'white')
	card.schoolText = makeText(
		spell.school.lower(),
		800,
		600,
		'black',
		'center',
		SCHOOL_FONT,
		getTextToFitSize(spell.school.lower(),200,14))
	simpleStatList = []
	statList = []
	statFontSizes = []
	# Create stat icons and text images
	for stat in ('ritual', 'concentration','verbal','somatic','material','consumed'):
		if getattr(spell,stat):
			simpleStatList.append(stat)
	statTextWidth = (card.card.width-10)/len(simpleStatList)
	for stat in simpleStatList:
		statFontSizes.append(getTextToFitSize(stat,statTextWidth,30,14))
	fontSize = min(statFontSizes)
	for stat in simpleStatList:
		d = {
			'icon' : makeIcon(stat,25,25),
			'text' : makeText(stat,800,600,'black','center',DEFAULT_FONT,fontSize)
		}
		statList.append(d)
	card.stats = statList
	# Spell components
	if spell.components:
		if spell.components[0] != '(':
			spell.components = '({0}'.format(spell.components)
		if spell.components[-1] != ')':
			spell.components = '{0})'.format(spell.components)
		fontSize= getTextToFitSize(spell.components,card.card.width-10,16)
		card.components = makeText(spell.components,800,600,'black','center',DEFAULT_FONT,fontSize)
	# Make a little line
	card.lineBreak = makeRectangle(card.card.width-10,BORDER_OFFSET,card.schoolColor)
	# spec block

	card.castingtime = makeSpecBlock('castingtime','Casting Time:' ,spell.castingtime,TIME_REGEX)
	card.range           = makeSpecBlock('range','Range: ',spell.range,RANGE_REGEX)
	card.target           = makeSpecBlock('target','Target: ',spell.target,TARGET_REGEX)
	card.duration      = makeSpecBlock('duration','Duration: ',spell.duration,TIME_REGEX)
	if spell.attack:
		card.attack = makeSpecBlock('attack','Attack: ',spell.attack)
	if spell.save:
		card.save   = makeSpecBlock('saving','Saving Throw: ',spell.save,SAVE_REGEX)
	if spell.effect:
		card.effect = makeSpecBlock('effect','Effect: ',spell.effect,EFFECT_REGEX)
	# make the bottom row, for the classes and reference
	try:
		card.reference = makeText(spell.reference,
			800,
			600,
			'black',
			'center',
			SCHOOL_FONT,
			getTextToFitSize(spell.reference,200,30,14))
	except:
		card.reference=makeNewImage(1,1)#Image(width=1,height=1,background=Color('transparent'),resolution=200)
	classList = []
	classFontSizes = []
	classTextWidth = (card.card.width-10)/len(spell.classes)
	for charClass in spell.classes:
		classFontSizes.append(getTextToFitSize(charClass,classTextWidth,16))
	fontSize = min(classFontSizes)
	#print(fontSize)
	for charClass in sorted(spell.classes):
		d = {
			'icon' : makeRoundIcon(charClass,30,30),
			'text' : makeText(charClass,800,600,'black','center',DEFAULT_FONT,fontSize)
		}
		classList.append(d)
	card.classes = classList

	# At Higher Levels
	if spell.athigherlevels:
	#	print('processing higher levels: {0}'.format(spell.athigherlevels))
		card.higherLevelBar =  makeRectangle(card.card.width-10,24,card.schoolColor)
		card.atHigherLevelsTitle = makeText('AT HIGHER LEVELS',800,600,'white','center',TITLE_FONT,20)
		card.higherLevelsText = makeText(spell.athigherlevels,card.card.width-10,60,'black','center',DEFAULT_FONT,14)

	descriptionHeight = calcDescHeight(card)
	card.description = makeText(
		spell.description,
		card.card.width - ( BORDER_OFFSET * 4 ),
		descriptionHeight,
		'black',
		'left',
		DEFAULT_FONT,
		18
	)
#	if spell.background:
#		try:
#			card.background = makeBackground(spell.background,card.card.width,card.card.height)
#		except:
#			pass
	card.finishedCard = assembleCard(card)
	return card.finishedCard
	#spellBook.append(card.finishedCard)
#	spellBook.sequence.append(card.finishedCard)




def makeBackground(b,w,h):
	return
	#with Image(filename='{0}/backgrounds/{1}.png'.format(ASSET_PATH,b)) as img:
	#	wDiff = 
#65535

def makeNewImage(w=500,h=700,c='transparent'):
	img = Image(width=w,height=h,resolution=200,background=Color(c))
	img.compression_quality = 100
	img.units = 'pixelsperinch'
	img.resolution = (200,200)
	return img

def calcDescHeight(c):
	d = c.card.height + TOP_OFFSET + c.titleBar.height + ( PIXEL_BUFFER * 12 )
	d -= c.schoolText.height + max(s['icon'].height for s in c.stats) + max(s['text'].height for s in c.stats)
	d -= max(cc['icon'].height for cc in c.classes) + max(cc['text'].height for cc in c.classes)
	d -= ( c.lineBreak.height * 3 ) + c.castingtime.height + c.range.height + c.target.height + c.duration.height
	d -= BORDER_OFFSET * 2
	try:
		d -= c.components.height
		d -= PIXEL_BUFFER * 2 
	except:
		pass
	
	try:
		d -= card.attack.height
		d -= PIXEL_BUFFER
	except:
		pass
	try:
		d -= card.save.height
		d -= PIXEL_BUFFER
	except:
		pass
	try:
		d -= c.effect.height
		d -= PIXEL_BUFFER
	except:
		pass

	try:
		d -= c.higherLevelBar.height
		d -= PIXEL_BUFFER * 2
		d -= higherLevelsText.height
	except:
		pass

	return d

class  Card:
	def __init__(self,name):
		self.name = name
		self.card   =  makeNewImage()#Image(width=400,height=600,resolution=200)

class Spell:
	def __init__(self,data,name):
		self.name = name
		for d in data:
			if d== 'Classes':
				setattr(self,d.lower().replace(' ',''),data[d].strip().split(','))
			else:
				setattr(self,d.lower().replace(' ',''),data[d].strip())

def makeSpecBlock(iconName,text,s,reg=TIME_REGEX):
	img =  makeNewImage()#Image(width=800,height=600,background=Color('transparent'),resolution=200)
	icon = makeIcon(iconName,20,20)
	text = makeNormalText(text,20)
	timeIcon = makeSpecIcon(s.lower().replace(' ',''),20,20,reg)
	timeText = makeNormalText(s,20)
	leftOffset = 0
	img.composite(icon,leftOffset,0)
	leftOffset += icon.width + PIXEL_BUFFER
	img.composite(text,leftOffset,0)
	leftOffset += text.width + ( PIXEL_BUFFER * 2 )
	img.composite(timeIcon,leftOffset,0)
	leftOffset += timeIcon.width + PIXEL_BUFFER
	img.composite(timeText,leftOffset,0)
	img.trim(color=Color('transparent'),fuzz=0.0)
	return img

def makeSpecIcon(text,width,height,reg=TIME_REGEX):
	img = makeNewImage(width,height)#Image(width=width,height=height,background=Color('transparent'),resolution=200)
	regMatch = reg.search(text)
	if regMatch is not None:
		s = regMatch.groupdict()['spec'].lower()
		icon = makeIcon(s,width,height)
		img.composite(icon,0,0)
	return img

def makeNormalText(text,size,fontColor='black',alignment='center',font=DEFAULT_FONT):
	img = makeNewImage()#Image(width=800,height=600,background=Color('transparent'),resolution=200)
	with Drawing() as ctx:
		ctx.font =  '{0}/Fonts/{1}'.format(ASSET_PATH,font)
		ctx.font_size = size
		ctx.fill_color = Color('black')
		ctx.text_alignment = alignment
		ctx.text(int(800/2),int(600/2),text)
		ctx.draw(img)
	img.trim(color=Color('transparent'),fuzz=0.0)
	#img.save(filename='normaltext_{0}.png'.format(random.random()))
	return img

def makeIcon(icon,width,height):
	try:
		img = Image(filename='{0}/Icons/{1}.svg'.format(ASSET_PATH,icon),resolution=200)
	except:
		img = makeNewImage(width,height)#Image(width=width,height=height,background=Color('transparent'),resolution=200)
	#img.opaque_paint(target=Color('white'),fill=Color('black'),fuzz=0.5)
	#img.negate
	img.trim(color=Color('transparent'),fuzz=0.0)
	img.transparent_color(color=Color('white'),alpha=0.0)
	img.resize(width,height,blur=0.1)
	return img

def assembleCard(card):
	topOffset = TOP_OFFSET
	img = makeNewImage(card.card.width,card.card.height,'white') #Image(width=card.card.width,height=card.card.height,background=Color('white'),resolution=200) as img:
		#img.compression_quality = 100
		#img.units = 'pixelsperinch'
		#img.resolution = (200,200)
	img.composite(card.titleBar,BORDER_OFFSET,topOffset)
		
	img.composite(
		card.titleText,
		int(card.card.width/2 + BORDER_OFFSET + card.schoolIcon.width - card.spellLevelMarker.width - BORDER_OFFSET - card.titleText.width/2 - PIXEL_BUFFER),
		int(card.titleBar.height/2 - card.titleText.height/2 + topOffset)
		)
	card.spellLevelMarker.composite(
		card.spellLevelText,
		int((card.spellLevelMarker.width/2 - card.spellLevelText.width/2)),
		int((card.spellLevelMarker.height/2 -card.spellLevelText.height/2) )
	)
	

	img.composite(card.spellLevelMarker,card.card.width-card.spellLevelMarker.width-BORDER_OFFSET-2,0)

	img.composite(card.schoolIcon,BORDER_OFFSET + PIXEL_BUFFER,topOffset)#img.composite(card.back,0,0)
	topOffset += card.titleBar.height + PIXEL_BUFFER
	img.composite(card.schoolText,BORDER_OFFSET+5,topOffset)
	img.composite(card.reference,card.card.width-BORDER_OFFSET-card.reference.width-3,topOffset)
	topOffset += card.schoolText.height + PIXEL_BUFFER
	# add the stats
	maxStatIconWidth = max(s['icon'].width for s in card.stats)
	maxStatTextWidth = max(s['text'].width for s in card.stats)
	maxStatWidth = max(maxStatIconWidth,maxStatTextWidth)
	#print(maxStatWidth)
	# The number of pixels each stat can have
	statWidth = (( card.card.width - ( BORDER_OFFSET * 2 ) ) / len(card.stats)) 
	# The center of that
	statCenter = statWidth / 2
	for stat in card.stats:
		
		iconLeft = int(statCenter -  stat['icon'].width/2)
		img.composite(stat['icon'],iconLeft,topOffset)
		textLeft = int(statCenter - stat['text'].width/2)
		img.composite(stat['text'],textLeft,topOffset+stat['icon'].height)
		statCenter += statWidth
	topOffset += stat['icon'].height  + stat['text'].height + (PIXEL_BUFFER * 2 )
	try:
		img.composite(card.components,int(card.card.width/2-card.components.width/2),topOffset + PIXEL_BUFFER )
		topOffset +=  card.components.height + ( PIXEL_BUFFER * 2)
	except:
		pass
	img.composite(card.lineBreak,BORDER_OFFSET,topOffset)
	topOffset += card.lineBreak.height + PIXEL_BUFFER
	
	img.composite(card.castingtime,int(card.card.width/2-card.castingtime.width/2),topOffset)
	topOffset += card.castingtime.height + PIXEL_BUFFER
	img.composite(card.range,int(card.card.width/2-card.range.width/2),topOffset)
	topOffset += card.range.height + PIXEL_BUFFER
	img.composite(card.target,int(card.card.width/2-card.target.width/2),topOffset)
	topOffset += card.target.height + PIXEL_BUFFER
	img.composite(card.duration,int(card.card.width/2-card.duration.width/2),topOffset)
	topOffset += card.duration.height + PIXEL_BUFFER
	try:
		img.composite(card.attack,int(card.card.width/2-card.attack.width/2),topOffset)
		topOffset += card.attack.height + PIXEL_BUFFER
	except:
		pass
	try:
		img.composite(card.save,int(card.card.width/2-card.save.width/2),topOffset)
		topOffset += card.save.height + PIXEL_BUFFER
	except:
		pass
	try:
		img.composite(card.effect,int(card.card.width/2-card.effect.width/2),topOffset)
		topOffset += card.effect.height + PIXEL_BUFFER
	except:
		pass

	#At higher leves, not every spell has this
	try:
		img.composite(card.higherLevelBar,BORDER_OFFSET,topOffset)
		img.composite(
			card.atHigherLevelsTitle,
			int(card.card.width/2-card.atHigherLevelsTitle.width/2),
			int(topOffset+card.higherLevelBar.height/2-card.atHigherLevelsTitle.height/2)
		)
		topOffset += card.higherLevelBar.height + PIXEL_BUFFER
		img.composite(card.higherLevelsText,int(card.card.width/2-card.higherLevelsText.width/2),topOffset)
		topOffset += card.higherLevelsText.height + PIXEL_BUFFER
	except Exception as e:
		pass
	# Line break
	img.composite(card.lineBreak,BORDER_OFFSET,topOffset)
	topOffset += card.lineBreak.height + PIXEL_BUFFER

	# Now the description (check and see if there are @ higher levels first, also assemble the class and reference)
	img.composite(card.description,BORDER_OFFSET *2,topOffset)
	# Classes and reference
	topOffset += card.description.height + PIXEL_BUFFER

	# The width of the card, minus borders, divided by the number of classes (+1) gets the offset for each class.
	# Increment after each class is placed.
	classOffset =  (card.card.width - (BORDER_OFFSET*2)) / (len(card.classes)+1)
	classCenter = 0
	maxIconHeight = max(charClass['icon'].height for charClass in card.classes)
	maxTextHeight = max(charClass['text'].height for charClass in card.classes)
	# Height of the card, minus the border, minus the 2 hights, minus 2 for spacing
	bottomOffset = card.card.height - ( BORDER_OFFSET * 2 ) - maxTextHeight - maxIconHeight 
	for charClass in card.classes:
		classCenter += classOffset
		iconLeft = int(classCenter - charClass['icon'].width/2 + BORDER_OFFSET)
		img.composite(charClass['icon'],iconLeft,bottomOffset)
		textLeft = int(classCenter - charClass['text'].width/2 + BORDER_OFFSET)
		img.composite(charClass['text'],textLeft,bottomOffset+charClass['icon'].height + PIXEL_BUFFER )
	bottomOffset -= card.lineBreak.height + PIXEL_BUFFER
	img.composite(card.lineBreak,BORDER_OFFSET,bottomOffset)
	# At higher levels
	


	img.composite(makeCardBack(card.card,card.schoolColor))
	img.save(filename="{0}.png".format(card.title))
	img.save(filename="{0}.pdf".format(card.title))
	return img


def makeText(title,width,height,fontColor,alignment='center',font=TITLE_FONT,fontSize=50):
	img =makeNewImage(width*3,height*3)# Image(width=width*3,height=height*3,background=Color('transparent'),resolution=200)
	with Drawing() as ctx:
		ctx.font =  '{0}/Fonts/{1}'.format(ASSET_PATH,font)
		ctx.font_size = fontSize
		ctx.fill_color = Color(fontColor)
		ctx.text_alignment = alignment
		message,startY= wordWrap(
			img,
			ctx,
			title,
			width,
			height,
			30
		)		
		ctx.text(int((width)/2),int(startY),message)
		ctx.draw(img)
		img.trim(color=Color('transparent'),fuzz=0.0)
	return img

def getTextToFitSize(text,roi_width,roi_height,size=80):
	mutable_message = text
	iteration_attempts = 1000
	def eval_metrics(txt):
		metrics = ctx.get_font_metrics(image,txt,True)
		return (metrics.text_width,metrics.text_height)

	def shrink_text():
		ctx.font_size = ctx.font_size - 0.75
		mutable_message = text
	image = makeNewImage()
	#with Image(width=800,height=600,background=Color('transparent'),resolution=200) as image:
	with Drawing() as ctx:
		ctx.font_size = size
		width, height = eval_metrics(mutable_message)	
		# End when the font size is as small as it gets, or the text fits within the bounds
		while ctx.font_size > 0 and ( height > roi_height or width > roi_width ):
			shrink_text()
			width,height = eval_metrics(mutable_message)
		return ctx.font_size
		


def wordWrap(img,draw,text,roi_width,roi_height,threshold=50):
	msg = text
	attempts = 1000
	columns = len(msg)
	def evalText(txt):
		metrics = draw.get_font_metrics(img,txt,True)
	#	print(metrics)
		return(metrics.text_width,metrics.text_height)
	def shrink_text():
		draw.font_size = draw.font_size - 0.75
	#	print('Font size is now {0}'.format(draw.font_size))
		msg = text
		return
	w,h = evalText(msg)
#	print('{0},{1}'.format(w,h))
#	print('{0},{1}'.format(roi_width,roi_height))
#	print('{0}'.format(draw.font_size))
	#while draw.font_size > 0 and w > roi_width and h > roi_height:
	while draw.font_size > 0 or w > roi_width or h > roi_height:
		w,h = evalText(msg)
	#	print('{0}: Attempt {1}, w: {2}/{3}, h: {4}/{5} '.format(msg,attempts,w,roi_width,h,roi_height))
		attempts -= 1
	
		# Get the height of the text shrunk down to fit first
		while h > roi_height:
	#		print('shrinking font size until {0} is less than {1}'.format(h,roi_height))
			shrink_text()
			w,h = evalText(msg)
		# Check if the width is in bounds, if yes then exit
		if w <= roi_width:
	#		print('width {0} is less than {1}'.format(w,roi_width))
			break
		# If the  w is under roi_width+50, shrink it until it fits
		elif w < ( roi_width + threshold ):
	#		print('{0}: width {1} is within the threshold of {2}, shrinking until it fits'.format(msg,w,roi_width+threshold))
			while w > roi_width:
				shrink_text()
				w,h = evalText(msg)
	#			print('width: {0}, height: {1}, msg: {2}'.format(w,h,msg))
		elif columns <= 1:
	#		print('only one column left, shrinking text and starting over')
			shrink_text()
		elif w > roi_width:
	#		print('columns is {0}'.format(columns))
			columns -= 1
	#		print('wrapping text at {0} columns'.format(columns))
			msg = '\n'.join(['\n'.join(wrap(line,columns,
				break_long_words=False))
				for line in text.splitlines() if line.strip() != ''])
	#		print('msg is now:\n{0}'.format(msg))
		else:
	#		print('something else')
			break
	metrics = draw.get_font_metrics(img,msg,True)
	#print(metrics)
	return msg,int(metrics.character_height)

def makeSpellLevelMarker(lvl):
	try:
		clr = COLORS[lvl]
	except KeyError:
		clr = 'gray'
	img=Image(filename='{0}/spelllevel.png'.format(ASSET_PATH),resolution=200)
	overlay=Image(filename='{0}/spellleveloverlay.png'.format(ASSET_PATH),resolution=200)
	img.colorize(color=Color(clr),alpha='rgb(100%,100%,100%)')
	img.composite(overlay,0,0)
		#replaceColor(img,'rgb(128,128,128)',clr)
	return img

def replaceColor(img,origClr,newClr):
	img.opaque_paint(target=Color(origClr),fill=Color(newClr),fuzz=0.10)

def makeRectangle(w,h,c):
	rectangle = makeNewImage(w,h,c)#Image(width=w,height=h,background=Color(c),resolution=200)
	return rectangle

def getSchoolColor(school):
	ct = ColorThief('{0}/ClassesAndSchools/{1}.png'.format(ASSET_PATH,school.lower()))
	dc = ct.get_color(quality=1)
	return 'rgb{0}'.format(dc)

def makeCardBack(img,color):
	back = makeNewImage(img.width,img.height)#Image(width=img.width,height=img.height,background=Color('transparent'),resolution=200) 
	with Drawing() as inner:
		inner.fill_opacity = 0
		inner.stroke_width=20
		inner.stroke_color = Color('white')
		inner.rectangle(left=-6,top=-6,width=img.width+12,height=img.height+12,radius=(img.width-4)*0.1)
		inner.stroke_color = Color(color)
		inner.stroke_width = 6
		inner.rectangle(left=3,top=3,width=img.width-7,height=img.height-7,radius=(img.width-4)*0.1)
		inner.draw(back)
	return  back


def  makeRoundIcon(sch,width=80,height=80):
	img = Image(filename='{0}/ClassesAndSchools/{1}.png'.format(ASSET_PATH,sch.lower()),resolution=200)
	if img.width != img.height:
		makeSquareImage(img)
	#img.border('transparent',2,2)
	makeCircleImage(img,3)
	img.resize(width,height,blur=0.1)
	return img

def makeSquareImage(img):
	m = min(img.size)
	img.crop(
		(img.width - m)/2,
		(img.height - m)/2,
		(img.width + m)/2,
		(img.height + m)/2
	)
	return 

def makeCircleImage(img,border=None):
	img.border('transparent',3,3)
	origin = (img.width/2,img.height/2)
	radius = (img.width/2-2,img.height/2-2)
	mask = makeNewImage(img.width,img.height,'white')#with  Image(width=img.width,
	#	height=img.height,
	#	background=Color('white'),
	#	resolution=200) as mask:
	with Drawing() as ctx:
		clr = Color('black')
		#ctx.stroke_color = clr
		ctx.stroke_width = 0
		ctx.fill_color = clr
	
		ctx.ellipse(origin,radius)
		ctx.draw(mask)
	applyMask(img,mask)
	if border:
		with Drawing() as ctx:
			clr=Color('black')
			ctx.stroke_width=border
			ctx.fill_color=Color('transparent')
			ctx.stroke_color=clr
			ctx.ellipse(origin,radius)
			ctx.draw(img)
	return 

def applyMask(image,mask,invert=False):
	image.alpha_channel = True
	if invert:
		mask.negate()
	mask.transparent_color(color='white',alpha=0.0)
	image.composite_channel('alpha',mask,'copy_alpha')
	
def readSpellList(csvFile):
	spells = {}
	spellList = []
	reader = csv.DictReader(open(csvFile))
	for row in reader:
		key = row.pop('Spell')
		if key in spells:
			continue
		spells[key] = row
		spellList.append(key)
	return spells,spellList

if __name__ == "__main__":
	main()