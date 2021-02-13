#!/usr/bin/env python3
import math
import cairocffi as cairo
import cairosvg
import sys
import os
import csv
import re
import io
import pangocffi as pango
import pangocairocffi as pc
from optparse import OptionParser
from colorthief import ColorThief
from webcolors import name_to_rgb
from textwrap import wrap,fill
from pprint import pprint
import traceback
import numpy as np
import skimage.transform
import pandas as pd
import logging as log
import json

LOG_LEVEL = 'Debug'

# Calculate percent, really not needed
def percent(n,r):
    return n*r

def nameToRgb(name):
    return tuple( float(i)/255 for i in name_to_rgb(name))

# Read command line arguments
parser = OptionParser()
parser.add_option('-c','--config',dest='configFile',help='XLSX file to read')
parser.add_option('-o','--output',dest='outFile',default='DnDCards.pdf',help='PDF file to write to [default=%default]')
parser.add_option('-d','--dpi',dest='dpi',default=100,help='Resolution of PDF in Dots-Per-Inch [default=%default]')
parser.add_option('-t','--title-font',dest='titleFont',default='DalelandsUncial',help='Font for title elements [default=%default]')
parser.add_option('-i','--italic-font',dest='italicFont',default='Mplantin-Italic',help='Font for italic elements [default=%default]')
parser.add_option('-f','--font',dest='defaultFont',default='Mplantin',help='Default font for most text [default=%default]')
parser.add_option('-W','--page-width',dest='pageWidth',default='8.5',help='Width of page output.  In inches but anything should work [default=%default]')
parser.add_option('-H','--page-height',dest='pageHeight',default='11',help='Height of page output.  [default=%default]')
parser.add_option('-w','--card-width',dest='cardWidth',default='2.5',help='Width of card. [default=%default]')
parser.add_option('-s','--card-height',dest='cardHeight',default='3.5',help='Height of card. [default=%default]')
parser.add_option('-a','--asset-path',dest='assetPath',default='Assets',help='Path to asset directory.  Must have sub-directoriees for SpellAndClass and Icons. [default=%default]')
(opts,args) = parser.parse_args()

DPI          = float(opts.dpi)
COLOR_BLACK  = (0,0,0)
COLOR_WHITE  = (1,1,1)


ASSET_PATH = opts.assetPath
TIME_REGEX = re.compile('(?P<spec>instantaneous|hour|minute|day|bonus|reaction|action|round)',re.IGNORECASE)
RANGE_REGEX = re.compile('(?P<spec>self|touch|ft|radius|mile|sight)',re.IGNORECASE)
TARGET_REGEX = re.compile('(?P<spec>humanoid|creature|self|sphere|cone|line|square|cube|radius)',re.IGNORECASE)
SAVE_REGEX = re.compile('(?P<spec>str|int|cha|wis|dex|con)',re.IGNORECASE)
EFFECT_REGEX = re.compile('(?P<spec>acid|bludgeoning|buff|charmed|cold|combatdefense|communication|control|creation|debuff|detection|exploration|fire|force|foreknowledge|frightened|healing|light|lightning|melee|movement|necrotic|piercing|poison|prone|psychic|radiant|ranged|restrained|shapechanging|social|summoning|thunder|unconcious|utility|warding)',re.IGNORECASE)
ATTACK_REGEX = re.compile('(?P<spec>melee|ranged)',re.IGNORECASE)
CURRENCY_REGEX = re.compile('^(?P<num>\d+)(?P<unit>.+)$',re.IGNORECASE)
DMG_REGEX = re.compile('\d+?(?P<spec>d\d+)',re.IGNORECASE)


BORDER_COLORS = {
    'racialabilities': (.6,.898,.314),
    'backgroundfeatures': (118/255,66/255,138/255),
}

# Assign spell level colors, using HTML color names
SPELL_LEVEL_COLORS = {
	'Cantrip' : nameToRgb('Snow'),
	'C' : nameToRgb('Snow'),
	'0' : nameToRgb('Snow'),
	'1' : nameToRgb('LightPink'),
	'2' : nameToRgb('DeepPink'),
	'3' : nameToRgb('Red'),
	'4' : nameToRgb('Orange'),
	'5' : nameToRgb('Yellow'),
	'6' : nameToRgb('Green'),
	'7' : nameToRgb('SkyBlue'),
	'8' : nameToRgb('Blue'),
	'9' : nameToRgb('Purple')
}

SHEET_KEYS = {
    'backgroundfeatures' : 'Feature',
    'racialabilities'    : 'Ability',
}

LEFT_ATTR = {
    # 'racialAbilities' : '' # Intentionally left blank
    'backgroundfeatures' : {
        'name' : 'background',
        'drawCircle' : False,
        'useClassAttribute' : True,
    },
    'weapons' : {
        'name' : 'PROFICIENT',
        'drawCirle' : True,
        'useClassAttribute' : False
    },
    'armor' : {
        'name' : 'PROFICIENT',
        'drawCircle' : True,
        'useClassAtrribute' : False,
    },
    'tools' : {
        'name' : 'PROFICIENT',
        'drawCircle' : True,
        'useClassAttribute' : False
    },
    'spells' : {
        'name' : 'school',
        'drawCircle' : False,
        'useClassAttribute' : True
    },
    'classfeatures' : {
        'name' : 'class',
        'drawCirce' : False,
        'useClassAttribute' : True
    }
}

ICON_MAP = {
    'backgroundfeatures' : 'background',
    'racialabilities' : None,
    'weapons' : None,
    'armor' : None,
    'tools' : None,
    'spells' : 'school',
    'classfeatures' : 'class',
}

SUBTITLE_MAP = {
    'classfeatures' : 'subclass',
    'weapons' : 'rarity',
}

PROPERTY_MAP = {
    'weapons' : [ 'attunement','ammunition','finesse','heavy','light','loading','reach','thrown','two-handed' ],
    'spells'  : [ 'ritual','concentration','verbal','somatic','material','consumed' ]
}

BOTTOM_ICON_MAP = {
    'spells' : 'classes',
    'racialabilities' : 'races'
}

NOTES_MAP = {
    
}

SPECIAL_MAP = {
    'weapons' : 'Special Instructions',
    'spells'  : 'At Higher Levels',
}

SPEC_LIST = {
    'weapons' : [
        {
            'col'   : 'category',
            'name'  : 'Category',
            'regex' : re.compile('(?P<spec>martial|simple)',re.IGNORECASE)
        },
        {
            'col' : 'type',
            'name' : 'Type',
            'regex' : re.compile('(?P<spec>melee|ranged)',re.IGNORECASE)
        },
        {
            'col' : 'damage',
            'name' : 'Damage',
            'regex' : DMG_REGEX
        },
        {
            'col' : 'damagetype',
            'name' : 'Damage Type',
            'regex' : re.compile('(?P<spec>bludgeoning|piercing|slashing)',re.IGNORECASE)
        },
        {
            'col'   : 'versatile',
            'name'  : 'Versatile',
            'regex' : DMG_REGEX
        },
        {
            'col'  : 'range',
            'name' : 'Range',
        'regex' : re.compile(r'\d+(\?:\s+)?(?P<spec>\/)',re.IGNORECASE),
        },
        {
            'col'   : 'weight',
            'name'  : 'Weight',
            'regex' : re.compile('\d+(?:\s+)?(?P<spec>lb)',re.IGNORECASE),
        },
    ],
    'spells' : [
        {
            'col'  : 'castingtime',
            'name' : 'Casting Time',
            'regex' : TIME_REGEX,
        },
        {
            'col' : 'range',
            'name' : 'Range',
            'regex' : RANGE_REGEX,
        },
        {
            'col' : 'target',
            'name' : 'Target',
            'regex' : TARGET_REGEX,
        },
        {
            'col' : 'duration',
            'name' : 'Duration',
            'regex' : TIME_REGEX,  
        },
        {
            'col' : 'attack',
            'name' : 'Attack',
            'regex' : ATTACK_REGEX,
        },
        {
            'col' : 'save',
            'name' : 'Saving Throw',
            'regex' : SAVE_REGEX,
        },
        {
            'col' : 'effect',
            'name' : 'Effect',
            'regex' : EFFECT_REGEX
        }        
    ]
}

TITLE_FONT   = opts.titleFont
ITALIC_FONT  = opts.italicFont
DEFAULT_FONT = opts.defaultFont

# Compute some heights, width, page layout buffers, etc
pageHeightPoints, pageWidthPoints = float(opts.pageHeight) * DPI, float(opts.pageWidth)  * DPI
cardWidthPoints, cardHeightPoints = float(opts.cardWidth)  * DPI, float(opts.cardHeight) * DPI
width, height                     = cardWidthPoints, cardHeightPoints
rowsPerPage                       = math.floor(pageWidthPoints  / cardWidthPoints )
colsPerPage                       = math.floor(pageHeightPoints / cardHeightPoints )
interColBuffer                    = ( pageWidthPoints  - ( cardWidthPoints  * colsPerPage ) ) / ( colsPerPage + 1 )
interRowBuffer                    = ( pageHeightPoints - ( cardHeightPoints * rowsPerPage ) ) / ( rowsPerPage + 1 )

# Buffer between elements, in pixels
PIXEL_BUFFER = 2

# Height Percentages
TWENTY_PERCENT_HEIGHT     = percent(.20,cardHeightPoints)
TWELVE_PERCENT_HEIGHT     = percent(.12,cardHeightPoints)
FIVE_PERCENT_HEIGHT       = percent(.05,cardHeightPoints)
FOUR_PERCENT_HEIGHT       = percent(.04,cardHeightPoints)
THREE_HALF_PERCENT_HEIGHT = percent(.035,cardHeightPoints)
THREE_PERCENT_HEIGHT      = percent(.03,cardHeightPoints)

# Width Percentages
FOUR_PCT_WIDTH            = percent(.04,cardWidthPoints)
EIGHTY_PCT_WIDTH          = percent(.80,cardWidthPoints)
FOURTEEN_PCT_WIDTH        = percent(.14,cardWidthPoints)
TEN_PCT_WIDTH             = percent(.10,cardWidthPoints)
TWO_PCT_WIDTH             = percent(.02,cardWidthPoints)

# Referenced width and heights
USABLE_WIDTH        = cardWidthPoints       - FOUR_PCT_WIDTH
COST_HEIGHT         = TWELVE_PERCENT_HEIGHT - PIXEL_BUFFER * 2
LEVEL_BANNER_HEIGHT = FOUR_PERCENT_HEIGHT   + TWELVE_PERCENT_HEIGHT

# Buffer between elements, in pixels
PIXEL_BUFFER = 2

def main():
    surface = cairo.PDFSurface(opts.outFile,pageWidthPoints,pageHeightPoints)
    ctx     = cairo.Context(surface)

    # Set some default values
    page = 1
    row  = 0
    col  = 0
    x    = interColBuffer
    y    = interRowBuffer

    # Read the excel file as a pandas dataframe
    if not opts.configFile:
        print('Please provide a XLSX file with the -c option.')
        exit(0)
    try:
        sheetData = pd.read_excel( opts.configFile , sheet_name = None )
    except:
        print('Unable to read XLSX file: {0}'.format(str(e)))

    for sheet in sheetData:
        sheetDict = sheetData[sheet].to_dict('records')
        page,row,col,x,y = processPage(
            ctx=ctx,
            sheetDict = sheetDict,
            sheetName = alphanum(sheet),
            page  = page,
            row   = row,
            col   = col,
            x     = x,
            y     = y
        )
    surface.finish()
    return

def processPage(ctx,sheetDict,sheetName,page,row,col,x,y):

    # Get items
    try:
        log.info('Reading item list for sheet {0}'.format(sheetName))
        items,itemList = readItemList(sheetDict,SHEET_KEYS[alphanum(sheetName)])
    except Exception as e:
        log.error('Unable to parse sheet {0}: {1}'.format(sheetName,str(e)),exc_info=True)
        exit(1)
    
    # Need to get a count of each quantity of each item
    totalItemCount = len(itemList)
 
    # New Page
    idx = 0
    log.debug('Processing {0} items for sheet {1}'.format(totalItemCount,sheetName))
    log.debug('idx {0} page {1} row {2} col {3}'.format(idx,page,row,col))
    while idx < totalItemCount:
        # Set the row count to 1, it's a new page
        # Disabled because we want to continue where the last sheet left off
        # row is passed from main()
        # currentRow = 1
        # Start the drawing right inside the buffer
        #currentX = interColBuffer
        #currentY = interRowBuffer
        while row < rowsPerPage and idx < totalItemCount:
            while col < colsPerPage and idx < totalItemCount:
                a = itemList[idx]
                print('Working on item {0} idx {1}, page {2}, row {3}, col {4}, x {5}, y {6}, icb: {7}, irb: {8} cwp: {9}'.format(a,idx,page,row,col,x,y,interColBuffer,interRowBuffer,cardWidthPoints)) 
                # Draw the actual card
                item = cardItem(items[a],a,sheetName)
                makeCard(ctx,item,x,y,sheetName)
                # Update the current x position to 1 card width + the buffer
                x += cardWidthPoints + interColBuffer
                # Increment the index
                idx += 1
                # Increment the column count
                col += 1
            # Exit this loop if the end of the page is reached
            if idx == totalItemCount:
                break
            else:
                row += 1
            
            if col == colsPerPage and row == rowsPerPage:
                log.debug('colLoop: reached the end of the page')
                break
            else:
                y += cardHeightPoints + interRowBuffer
                # Reset the X coordinate
                x = interColBuffer
                # Reset the column count
                col = 0
                log.debug('starting a new row c:{0} r:{1}'.format(col,row))
        if col == colsPerPage and row == rowsPerPage:
            log.debug('rowLoop: reached the end of the page')
            # Increment the page count
            page += 1
            # Add the page
            ctx.show_page()
            # Reset the row count
            row = 0
            y = interRowBuffer
            col = 0
            x = interColBuffer
# Finish the drawing
    return page , row , col , x , y

def makeCard(ctx,item,x,y,sheetName):
    origX,origY = ( x,y)
    bottomY = y + cardHeightPoints - TWO_PCT_WIDTH
    x += TWO_PCT_WIDTH
    y += TWO_PCT_WIDTH

    # Get the border color based on the item.school, item.class, or sheetName
    borderColor = getBorderColor(item,sheetName)

    # Try to add the left text
    try:
        leftAttr = LEFT_ATTR[sheetName]

        # Use the 'name' of the attribute, but try to get the spreadsheet field
        # If configured
        try:
            leftAttribute = getattr(item,leftAttr['name'])
        except:
            leftAttribute = leftAttr['name']

        leftWidth = addLeftText(
            ctx=ctx,
            text=leftAttribute,
            x=x + TEN_PCT_WIDTH, # Accounts for the curve
            y=y,
            w = USABLE_WIDTH - ( TEN_PCT_WIDTH * 2 ) - ( PIXEL_BUFFER * 2),
            h=THREE_PERCENT_HEIGHT,
            c=leftAttr['drawCircle']
        )
    except Exception as e:
        log.info('Unable to add left text: {0}'.format(str(e)))#,exc_info=True)
        leftWidth = 0

    # If there is a spelllevel or a level, leave space for the banner
    if hasattr(item,'spellevel') or hasattr(item,'level'):
        levelBannerWidth = FOURTEEN_PCT_WIDTH
    else:
        levelBannerWidth = 0

    # Add the reference text
    y += PIXEL_BUFFER + addReferenceText(
        ctx=ctx,
        ref=item.reference,
        # Make sure it's to the right of the 'left text'
        x=x + TEN_PCT_WIDTH + leftWidth,
        y=y,
        # Subtract leftWidth to account for the text on the left
        w=USABLE_WIDTH - (TEN_PCT_WIDTH * 2 )- ( PIXEL_BUFFER * 2 ) - leftWidth - levelBannerWidth,
        h=THREE_PERCENT_HEIGHT)
    
    # Add the background box for the title
    # This has to be done seperate from the title text because of the possiblity of a level banner
    addRectangle(
        ctx=ctx,
        x=x,
        y=y,
        w=USABLE_WIDTH,
        h=TWELVE_PERCENT_HEIGHT,
        c=borderColor
    )

    # Temporary holder for the title width,
    # Decreases when we add the level  banner, cost, and icon
    titleUsableWidth = USABLE_WIDTH
    titleX = x

    # Add the level banner
    if hasattr(item,'spelllevel'):
        levelNum = item.spellevel
    elif hasattr(item,'level'):
        levelNum = item.level
    else:
        levelNum = False
    
    if levelNum:
        levelColor = getLevelColor(item)
        titleUsableWidth -= addLevelBanner(
            ctx=ctx,
            color=levelColor,
            x=x+USABLE_WIDTH-FOURTEEN_PCT_WIDTH-PIXEL_BUFFER,
            y=origY-PIXEL_BUFFER
        )
        drawText(
            ctx=ctx,
            text = levelNum.upper(),
            fontName = TITLE_FONT,
            x = x + USABLE_WIDTH - FOURTEEN_PCT_WIDTH,
            y = origY,
            targetW = FOURTEEN_PCT_WIDTH - 2,
            targetH = LEVEL_BANNER_HEIGHT - 2,
            threshold = .10,
            talign = 'Center'
        )

    # Try to get an icon to use
    iconName = getIcon(item,sheetName)

    # Draw the icon
    try:
        iconWidth = addTitleIcon(
            ctx=ctx,
            imagePath='{0}/png/{1}.png'.format(ASSET_PATH,iconName),
            diameter=TWELVE_PERCENT_HEIGHT - PIXEL_BUFFER * 2,
            x= x + PIXEL_BUFFER,
            y = y + PIXEL_BUFFER,
        )
        titleX += iconWidth
        titleUsableWidth -= iconWidth
    except Exception as e:
        log.info('Did not add title icon: {0}'.format(str(e)))#,exc_info=True)
        pass

    # Try to add the cost
    if hasattr(item,'cost') and item.cost is not None and item.cost != '':
        costHeight = TWELVE_PERCENT_HEIGHT - PIXEL_BUFFER * 2,
        titleUsableWidth -= addCostIcon(
            ctx=ctx,
            x=x + USABLE_WIDTH - FOURTEEN_PCT_WIDTH - costHeight + PIXEL_BUFFER,
            y=y + PIXEL_BUFFER,
            w=costHeight,
            h=costHeight,
            cost=cost
        )

    # Finally make the title fit in the space that is lef
    y += addTitleText(
        ctx=ctx,
        x=titleX,
        y=y,
        width=titleUsableWidth,
        height=TWELVE_PERCENT_HEIGHT,
        color=borderColor,
        text=item.name.upper()
    )

    # Add the subtitle
    try:
        subTitle=getattr(item,SUBTITLE_MAP[sheetName])
    except:
        subTitle = None

    if subTitle and subTitle is not None and subTitle != '':
        stw,sth,_ = drawText(
            ctx=ctx,
            text=subTitle.upper(),
            fontName=TITLE_FONT,
            x = x + PIXEL_BUFFER,
            y = y,
            targetW = USABLE_WIDTH,
            targetH = THREE_PERCENT_HEIGHT,
            valign='Center',
            fontSize=14,
            halign='Center',
            talign='Center'
        )
        y += sth
        log.debug('Adding horizontal bar after subTitle')
        y += PIXEL_BUFFER + addRectangle(ctx,x,y,USABLE_WIDTH,TWO_PCT_WIDTH,borderColor)

    # Try to add the properties
    try:
        propertyList = [ p for p in PROPERTY_MAP[sheetName] if getattr(item,p)]
    except:
        propertyList = None

    if propertyList:
              # Add the weapon properties
        y += PIXEL_BUFFER + addProperties(
            ctx,
            propertyList,
            USABLE_WIDTH,
            x + PIXEL_BUFFER,
            y
        )

        # Add horizontal bar
        log.debug('Adding horizontal bar after Properties')
        y += PIXEL_BUFFER + addRectangle(ctx,x,y,USABLE_WIDTH,TWO_PCT_WIDTH,borderColor)

    # Try to get spec list
    try:
        specList = [ s for i,s in enumerate(SPEC_LIST[sheetName]) if getattr(item,str(SPEC_LIST[sheetName][i]['col']))]
    except:
        specList = None

    if specList:
        y += addSpecs(
            ctx=ctx,
            specList=specList,
            width=USABLE_WIDTH,
            x=x,
            y=y
        )

    
    # Add the special bar if there is a special attribute
    try:
        specialName = SPECIAL_MAP[sheetName].upper()
        specialField = alphanum(specialName)
        specialText = getattr(item,specialField).strip()
    except:
        specialName = None
        specialField = None
        specialText = None

    if specialName and specialText and specialText != '':
        y += PIXEL_BUFFER + addSpecialTitle(
            ctx=ctx,
            x=x,
            y=y,
            width=USABLE_WIDTH,
            height=THREE_HALF_PERCENT_HEIGHT,
            color=borderColor,
            text=specialName,
        )
        w,h,_ = drawText(
            ctx=ctx,
            text=specialText,
            x = x,
            y = y,
            targetW = USABLE_WIDTH,
            #targetH = len(specialText.split('\n')) * THREE_PERCENT_HEIGHT,
            targetH = bottomY - y, # Up to the entire space if needed?
            threshold = 1,
            talign = 'Left',
            halign = 'Left',
            valign = 'Top',
            fontSize = 14
        )
        y += PIXEL_BUFFER + h 

    if (specialName and specialText and specialText != '' ) or (specList):
        y += PIXEL_BUFFER + addRectangle(ctx,x,y,USABLE_WIDTH,TWO_PCT_WIDTH,borderColor)

    # Try to get the bottom icons
    try:
        bottomIcons = getattr(item,BOTTOM_ICON_MAP[sheetName])
        lo.info('Added bottom icons')
    except Exception as e:
        log.info('Could not get bottom icons: {0}'.format(str(e)),exc_info=True)
        bottomIcons = None
    if bottomIcons:
        bottomY -= PIXEL_BUFFER + addBottomIcons(ctx,bottomIcons,USABLE_WIDTH,x,bottomY)
        bottomY -= PIXEL_BUFFER + addRectangle(ctx,x,bottomY - TWO_PCT_WIDTH,USABLE_WIDTH,TWO_PCT_WIDTH,borderColor)
    
 
    try:
        notesField = NOTES_MAP[sheetName]
    except:
        notesField = 'notes'
    try:
        bottomNotes = getattr(item,notesField)
    except:
        bottomNotes = None
    if bottomNotes:
        bottomY -= PIXEL_BUFFER + addNotes(ctx,weapon.notes,USABLE_WIDTH,x,bottomY)
        bottomY -= PIXEL_BUFFER + addRectangle(ctx,x,bottomY - TWO_PCT_WIDTH,USABLE_WIDTH,TWO_PCT_WIDTH,borderColor)
    

    # If there is an image, leave 20% of the remaining space for the image.
    if hasattr(item,'image'):
        targetHeight = bottomY - y - TWENTY_PERCENT_HEIGHT
    else:
        targetHeight = bottomY - y

    # add the item description
    if hasattr(item,'description'):
        w,h,_ = drawText(
            ctx = ctx,
            text = item.description.strip(),
            x = x + PIXEL_BUFFER *2 ,
            y = y,
            targetW = USABLE_WIDTH - (PIXEL_BUFFER*2),
            targetH = targetHeight,
            threshold = 0.1,
            valign = 'Top',
            halign = 'Left',
            talign = 'Left',
            fontSize = 16
        )
        
        y += h + PIXEL_BUFFER

    # Try to add an image, if there is one:
    if hasattr(item,'image'):
        try:
            rotation = item.rotate
        except:
            rotation = 0

         # Add horizontal space above classes
        y += PIXEL_BUFFER + addRectangle(ctx,x,bottomY - TWO_PCT_WIDTH,USABLE_WIDTH,TWO_PCT_WIDTH,borderColor)
        
        ctx.save()
        addItemImage(
            ctx = ctx,
            item = item.image,
            r = rotation,
            x = x,
            y = y,
            w = USABLE_WIDTH - ( PIXEL_BUFFER * 2 ),
            h = bottomY - y
        )
        ctx.restore()

    # Add colored border
    addRoundedBorder(
        ctx=ctx,
        c=borderColor,
        x=origX+(TWO_PCT_WIDTH/2),
        y=origY+(TWO_PCT_WIDTH/2),
        w=width-TWO_PCT_WIDTH,
        h=height-TWO_PCT_WIDTH,
        t=TWO_PCT_WIDTH,
    )

    # And a thin black border around the whole thing
    ctx.set_source_rgb(0,0,0)
    ctx.set_line_width(1)
    ctx.rectangle(origX,origY,width,height)
    ctx.stroke()
    # return
    return

def addLeftText(ctx,text,x,y,w,h,c):
    circleOffset = 0
    # Add the proficency cirle if defined
    if c:
        ctx.save()
        ctx.set_source_rgb(0,0,0)
        ctx.set_line_width(1)
        ctx.arc(x+h/2+PIXEL_BUFFER/2,y+h/2+PIXEL_BUFFER/2,h/2-PIXEL_BUFFER/2,0,2*math.pi)
        ctx.close_path()
        ctx.stroke()
        ctx.restore()
        circleOffset += h + PIXEL_BUFFER

    tw,th,_ = drawText(
        ctx=ctx,
        text=text,
        fontName=ITALIC_FONT,
        x=x + circleOffset + PIXEL_BUFFER * 2,
        y=y,
        targetH=h,
        targetW=w,
        valign='Center',
        halign='Left',
        talign='Left',
    )
    return circleOffset + tw + PIXEL_BUFFER

def addReferenceText(ctx,ref,x,y,w,h):
    refX = x + PIXEL_BUFFER
    refY = y + PIXEL_BUFFER
    refH = h
    refW = w
    circH = h + PIXEL_BUFFER
    

    # Set the reference text to the right
    rw,rh,_ = drawText(
        ctx=ctx,
        text=ref.upper(),
        fontName=ITALIC_FONT,
        x=refX,
        y=refY,
        targetH=refH,
        targetW=refW,
        valign='Center',
        halign='Right',
        talign='Right'
    )
    return(rh) # Return the max height of this text area

def addBottomIcons(ctx,iconList,w,x,y):
    ctx.save()
   
    layout       = pc.create_layout(ctx)
    sortedList   = sorted(list(iconList))
    print(sortedList)
    textWidth    = w / len(sortedList)
    textCenter   = textWidth / 2
    iconDiameter = TEN_PCT_WIDTH
    fontSizes    = {}
    for c in sortedList:
        cw,ch,fontSize,_ = wrapText(ctx,layout,c.lower(),textWidth,THREE_PERCENT_HEIGHT)
        fontSizes[c] = {
            'w' : cw,
            'fs' : fontSize,
            'h' : ch,
        }
    fontSize   = min( [ fontSizes[c]['fs'] for c in fontSizes] )
    fontHeight = max( [ fontSizes[c]['h'] for c in fontSizes]  )
    y -= fontHeight + iconDiameter + PIXEL_BUFFER * 2
    # Set the starting center of the text and image (back it up by 1/2 of each width later)
    currentXOffset = x + textCenter
    for c in sortedList:
        cIcon = alphanum(c)
        w,h,_ = drawText(
            ctx      = ctx,
            text     = c,
            x        = currentXOffset - fontSizes[c]['w']/2,
            y        = y,
            targetW  = fontSizes[c]['w'],
            targetH  = fontHeight,
            valign   = 'Top',
            fontSize = fontSize
        )
        try:
            drawRoundSurface(
                ctx       = ctx,
                imagePath = '{0}/png/{1}.png'.format(ASSET_PATH,cIcon),
                diameter  = iconDiameter,
                x         = currentXOffset - iconDiameter / 2,
                y         = y + fontHeight + PIXEL_BUFFER
            )
        except Exception as e:
            print("Can't add icon for {0}: {1}".format(cIcon,str(e)))
        currentXOffset += textWidth
    ctx.restore()
    return fontHeight + iconDiameter + PIXEL_BUFFER

def addCostIcon(ctx,cost,x,y,h,w):
    unit = 'gp'
    regMatch = CURRENCY_REGEX.match(cost)
    if regegMatch is not None:
        unit = alphanum(regMatch.groupdict()['unit'])
    addSVG(
        ctx=ctx,
        svg=unit,
        x=x,
        y=y,
        w=w,
        h=h
    )
    drawText(
        ctx=ctx,
        text=cost,
        fontName=TITLE_FONT,
        x = x,
        y=y,
        targetW=w,
        targetH=h,
        threshold=.10,
        talign='Center'
    )
    return w

def addLevelBanner(ctx,color,x,y):
    # Set the color to the spell level's color
    ctx.set_source_rgb(color)
    ctx.move_to(x, y+1)
    # Draw down 70% of the shape
    ctx.rel_line_to(0,percent(.7,SPELL_LEVEL_HEIGHT-PIXEL_BUFFER))
    # Make the point
    ctx.rel_line_to(FOURTEEN_PCT_WIDTH/2,percent(.3,SPELL_LEVEL_HEIGHT))
    # And back up to the right
    ctx.rel_line_to(FOURTEEN_PCT_WIDTH/2,percent(-.3,SPELL_LEVEL_HEIGHT))
    # Draw back up to the top of the border box
    ctx.line_to(x+FOURTEEN_PCT_WIDTH,y+TWO_PCT_WIDTH+FOUR_PERCENT_HEIGHT)
    # Radius is half the width
    r = FOURTEEN_PCT_WIDTH / 2
    # Create an arc -90 degrees back to the starting point
    ctx.arc_negative(x +FOURTEEN_PCT_WIDTH - r,y + TWO_PCT_WIDTH + r,r,0,-90*(math.pi/180))
    # Fill it
    ctx.fill_preserve()
    # Draw a black line
    ctx.set_source_rgb(0,0,0)
    ctx.set_line_width(1)
    ctx.stroke()
    return FOURTEEN_PCT_WIDTH

def addNotes(ctx,notes,w,x,y):
    ctx.save()
    layout = pc.create_layout(ctx)
    # Find out how big the notes box will be
    boxWidth,boxHeight,fontSize,_ = wrapText(ctx,layout,notes,w,TWELVE_PERCENT_HEIGHT)
    y -= boxHeight + ( PIXEL_BUFFER * 2 )
    # Now create the text since we know the y
    w,h,_ = drawText(
        ctx=ctx,
        text=notes,
        x=x,
        y=y + PIXEL_BUFFER,
        targetW=w,
        targetH=boxHeight,
        valign='Top',
        fontSize=fontSize
    )
    ctx.restore()
    return boxHeight + ( PIXEL_BUFFER * 2 )

def addItemImage(ctx,image,r,x,y,w,h):
    ctx.save()
    # Move to the center of the usable space
    ctx.translate( x + ( w / 2 ), y + ( h / 2 ) )
    itemSurface = cairo.ImageSurface.create_from_png(image)
    imageHeight   = itemSurface.get_height()
    imageWidth    = itemSurface.get_width()
    doneRotating  = False

    if str(r).lower() == 'cw':
        rotate = 1
    elif str(r).lower() == 'ccw':
        rotate = -1    
    else:
        rotate = False
        widthScale  = w / imageWidth
        heightScale = h / imageHeight
        scale       = min( w / imageWidth , h / imageHeight )

    if rotate:
        rotation = calculateRotation(
            targetWidth=w,
            targetHeight=h,
            imageWidth=itemSurface.get_width(),
            imageHeight=itemSurface.get_height(),
            increment=rotate
        )
        scale = min( w / rotation['width'] , h / rotation['height'] )
        ctx.rotate( ( ( rotation['degree'] ) * math.pi ) / 180.0 )
        
    ctx.scale( scale, scale )
    ctx.translate( -0.5 * imageWidth , -0.5 * imageHeight )
    ctx.set_source_surface(itemSurface,0,0)
    ctx.paint()
    ctx.restore()
    return
    
def addProperties(ctx,propertyList,w,x,y):
    ctx.save()
    layout = pc.create_layout(ctx)
   # propertyList = [ p for p in WEAPON_PROPERTIES if getattr(weapon,p)]

    propTextWidth = w / len(propertyList)
    propTextCenter = propTextWidth / 2
    propFontSizes = {}
    # Find the ussable font size for each word
    for p in propertyList:
        pw,ph,fontSize,_ = wrapText(ctx,layout,p.lower(),propTextWidth,THREE_PERCENT_HEIGHT)
        propFontSizes[p] = {
            'w'  : pw,
            'fs' : fontSize,
            'h'  : ph
        }
    # Get the minimum size
    fontSize = 50
    fontHeight = 0
    fontSize   = min([ propFontSizes[p]['fs'] for p in propFontSizes])
    fontHeight = max([ propFontSizes[p]['h']  for p in propFontSizes])

    # Go back and draw them
    currentXOffset = x + propTextCenter
    for prop in propertyList:
        w,h,_ = drawText(
            ctx=ctx,
            text=prop,
            x=currentXOffset - propFontSizes[prop]['w']/2,
            y=y,
            targetW=propFontSizes[prop]['w'],
            targetH=fontHeight,
            fontSize=fontSize
        )
        try:
            prop = ICON_MAP[prop]
        except:
            pass
        try:
            addSVG(
                ctx=ctx,
                svg=prop,
                x=currentXOffset - fontHeight / 2,
                y=y + fontHeight + PIXEL_BUFFER,
                w=fontHeight,
                h=fontHeight
            )
        except Exception as e:
            print("Couldn't load icon for {0}".format(prop))

        currentXOffset += propTextWidth
    ctx.restore()
    return fontHeight * 2 + PIXEL_BUFFER

def addRectangle(ctx,x,y,w,h,c):
    ctx.save()
    ctx.set_source_rgb(*c)
    ctx.rectangle(x,y,w,h)
    ctx.set_line_width(0)
    ctx.fill()
    ctx.restore()
    return h

def addRoundedBorder(ctx,c,x,y,w,h,t):
    roundRect(
        ctx=ctx,
        x=x,
        y=y,
        width=w,
        height=h,
        r=TEN_PCT_WIDTH,
        thickness=t,
        rgb=c
    )
    return

def addSpecialTitle(ctx,x,y,width,height,color,text,fontName=TITLE_FONT,fontColor=COLOR_WHITE):
    addRectangle(
        ctx=ctx,
        x=x,
        y=y,
        w=width,
        h=height,
        c=color
    )
    drawText(
        ctx=ctx,
        text=text,
        fontName=fontName,
        x=x,
        y=y,
        targetW=width,
        targetH=height,
        color=fontColor,
        talign='Center',
        halign='Center',
        valign='Center'
    )
    return height 

def addSpecs(ctx,specList,w,x,y):
    ctx.save()
    origY = y
    layout = pc.create_layout(ctx)
    specWidth = w
        # Get the min font size and max width for each of the texts
    fontSizeMin = 50
    textWidthMax = 0
    heightMax = 0
    
    for spec in specList:
        thisText = '{0}{1}'.format(spec['name'],getattr(weapon,spec['col'])).replace('\n',' ')
        sw,sh,fontSize,_ = wrapText(ctx,layout,thisText,specWidth,THREE_HALF_PERCENT_HEIGHT,threshold=10)
        if fontSize < fontSizeMin:
            fontSizeMin = fontSize
        if sw > textWidthMax:
            textWidthMax = sw
        if sh > heightMax:
            heightMax = sh
    # Going through again, now to scale it down since we have the height
    tempHeight = heightMax
    for spec in specList:
        thisText = '{0}{1}'.format(spec['name'],getattr(weapon,spec['col'])).replace('\n',' ')
        sw,sh,fontSize,_ = wrapText(ctx,layout,thisText,textWidthMax-4,tempHeight,threshold=1000,fontSize=fontSizeMin)
        if fontSize < fontSizeMin:
            fontSizeMin = fontSize
        if sw > textWidthMax:
            textWidthMax = sw
        if sh > heightMax:
            heightMax = sh

    # Ok, now get them seperate
    NameWidthMax = 0
    TextWidthMax = 0
    # Height should be the same no matter what
    for spec in specList:
        nw,_,_,_ = wrapText(ctx,layout,spec['name'],textWidthMax-4,heightMax,threshold=1000,fontSize=fontSizeMin)
        if nw > NameWidthMax:
            NameWidthMax = nw
        tw,_,_,_ = wrapText(ctx,layout,getattr(weapon,spec['col']).replace('\n',' '),textWidthMax-4,heightMax,threshold=1000,fontSize=fontSizeMin)
        if tw > TextWidthMax:
            TextWidthMax = tw
    
    # now, finally do it
    for spec in specList:
        thisX = x + PIXEL_BUFFER
        try:
            addSVG(
                ctx=ctx,
                svg=spec['col'],
                x=x + PIXEL_BUFFER,
                y=y,
                w=heightMax,
                h=heightMax,
            )
            thisX += heightMax + PIXEL_BUFFER
        except:
            pass
        
        nw,nh,_ = drawText(
            ctx=ctx,
            text=spec['name'],
            x=thisX,
            y=y,
            targetW = NameWidthMax,
            targetH = heightMax,
            threshold = 10,
            talign = 'Right',
            halign = 'Right',
            fontSize = fontSizeMin
        )
        specText = getattr(weapon,spec['col'])

        thisX += NameWidthMax + PIXEL_BUFFER
        try:
          #  print('Looking at spec: {0}'.format(spec))
            if 'regex' in spec:
                regMatch = spec['regex'].search(specText)
                if regMatch is not None:
                    s = regMatch.groupdict()['spec'].lower()
            
                    # check icon map for override
                    try:
                        s = ICON_MAP[s]
                    except:
                        pass
                    
                    # There's nothing in the range to match on a regex for an icon name
                    # So we have to force it.
                    # range = 30/120 (matching on the / is tricky?)
                    if spec['col'] == 'range':
                        s = 'distance'
                    
                    addSVG(
                        ctx=ctx,
                        svg=s,
                        x=thisX,
                        y=y,
                        w=heightMax,
                        h=heightMax,
                    )
                    thisX += heightMax + PIXEL_BUFFER
        except Exception as e:
            print("can't create svg for '{2}' '{0}': {1}".format(spec,s,str(e)))
            traceback.print_exc()
            pass
        
        tw,th,_ = drawText(
            ctx=ctx,
            text=specText,
            x=thisX,
            y=y,
            targetW = TextWidthMax,
            targetH = heightMax,
            threshold=1000,
            talign = 'Left',
            halign = 'Left',
            fontSize = fontSizeMin,
            
        )
        y += heightMax + PIXEL_BUFFER
    ctx.restore()
    return y - origY  

def addTitleIcon(ctx,imagePath,diameter,x,y):
    # Scale and place the spell school icon
    drawRoundSurface(
        ctx=ctx,
        imagePath=imagePath,
        diameter=diameter,
        x=x + PIXEL_BUFFER,
        y=y
    )
    # Adjust the x position and the width to account for the icon
    return diameter + PIXEL_BUFFER * 2

def addTitleText(ctx,x,y,width,height,color,text,fontName=TITLE_FONT,fontColor=COLOR_WHITE,talign='Center',icon=None,rightMargin=0):
    drawText(
        ctx=ctx,
        text=text,
        fontName=fontName,
        x=x + PIXEL_BUFFER + (TWO_PCT_WIDTH/2),
        y=y+(TWO_PCT_WIDTH/2),
        # rightMargin accounts for a level banner
        targetW=width - rightMargin - TWO_PCT_WIDTH,
        targetH=height-TWO_PCT_WIDTH,
        color=fontColor,
        talign=talign
    )
    return height

def alphanum(text):
    return re.sub(r'[^a-z0-9]','',text.lower().strip())

def calculateRotation(targetWidth,targetHeight,imageWidth,imageHeight,increment=1):
    maxDim = int(max(imageWidth,imageHeight,targetWidth,targetHeight) * 2)
    center = int(maxDim/2)
    startX = int(center - imageWidth/2) - 1
    endX   = int(center + imageWidth/2) + 1
    startY = int(center - imageHeight/2) - 1
    endY   = int(center + imageHeight/2)
    img    = np.zeros([maxDim,maxDim],dtype=np.uint8)
    img[startY:endY,startX:endX] = 255
    targetRatio = float(targetWidth/targetHeight)
    imageRatio  = float(imageWidth/imageHeight)
    startDegree = 0
    maxDegree   = 179 * increment
    curDegree   = startDegree
    ratioDiff   = abs( imageRatio - targetRatio)
    outcome = {
        'width'  : imageWidth,
        'height' : imageHeight,
        'ratio'  : ratioDiff,
        'degree' : curDegree,
        'diff'   : ratioDiff
    }

    # Try every angle of rotation, find the smallest difference in the ratio.
    # End at 179 because 180 is upside down and that is pointless.
    while abs(curDegree) <= abs(maxDegree):
        tmpImg    = skimage.transform.rotate(img,curDegree,mode='edge')
        rect      = np.where(tmpImg == 1 )
        tmpWidth  = rect[1].max() - rect[1].min()
        tmpHeight = rect[0].max() - rect[0].min()
        tmpRatio  = float( tmpWidth / tmpHeight )
        tmpDiff   = abs( tmpRatio - targetRatio )
     #   print('Testing degree {0}, ratio {1} against {2}'.format(curDegree,tmpRatio,outcome['diff']))
        if tmpDiff < outcome['diff']:
            
            outcome['width']  = tmpWidth
            outcome['height'] = tmpHeight
            outcome['ratio']  = tmpRatio
            outcome['degree'] = curDegree
            outcome['diff']   = tmpDiff
      #      print('Updating stats: {0}'.format(outcome))
        curDegree += increment
    
    return outcome

def drawRoundSurface(ctx,imagePath,diameter,x,y):
    # save the context
    ctx.save()
    # open surface from png
    schoolSurface = cairo.ImageSurface.create_from_png(imagePath)
    # find the width and height
    w = schoolSurface.get_width()
    h = schoolSurface.get_height()
    # find the scale to get to desired diameter
    minDim = min(w,h)
    sc = diameter/minDim
    # scale
    ctx.translate(x,y)
    ctx.scale(sc,sc)
    # set the surface as the context
    ctx.set_source_surface(schoolSurface,0,0)
    # make an arc in the middle of the context that is the diameter /2 (circumference)
    ctx.arc(w/2,h/2,minDim/2,0,2*math.pi)
    # clip the context
    ctx.clip()
    # paint
    ctx.paint()
    # restore
    ctx.restore()
    # Add a black border
    ctx.set_source_rgb(0,0,0)
    ctx.set_line_width(1)
    ctx.arc(x+diameter/2,y+diameter/2,diameter/2,0,2*math.pi)
    ctx.stroke()
    return

def drawText(ctx,text,x,y,targetW,targetH,fontName=DEFAULT_FONT,threshold=.2,color=COLOR_BLACK,valign='Center',halign='Center',talign='Left',fontSize=50):
    # Initialize the text
    ctx.save()
    layout = pc.create_layout(ctx)
    if talign == 'Center':
        layout.set_alignment(pango.Alignment.CENTER)
    elif talign == 'Right':
        layout.set_alignment(pango.Alignment.RIGHT)
    else:
        layout.set_alignment(pango.Alignment.LEFT)
    w,h,fontSize,mutable_text = wrapText(ctx,layout,text,targetW,targetH,threshold,fontSize,fontName)
    # Paint the text
    ctx.set_source_rgb(*color)
    if valign == 'Center':
        vtrans = (targetH - h)/2
    elif valign == 'Bottom':
        vtrans = targetH - h
    # Top or undefined
    else:
        vtrans = 0
    if halign == 'Center':
        htrans = (targetW - w)/2
    elif halign == 'Right':
        htrans = targetW - w
    # Left or undefined
    else:
        htrans = 0
    ctx.translate(htrans+x,vtrans+y)
    #print("Translate to {0},{1}".format(htrans+x,vtrans+y))
    ctx.set_source_rgb(*color)
    layout.set_text(mutable_text)
    pc.show_layout(ctx,layout)
    ctx.restore()
    return w,h,fontSize

def getBorderColor(item,sheetName):
    if hasattr(item,'school'):
        pngName = aplhanum(item.spelllevel)
    elif hasattr(item,'class'):
        pngName = alphanum(item.level)
    else:
        pngName = False
    
    if pngName:
        ct = ColorThief('{0}/png/{1}.png'.format(ASSET_PATH,pngName))
        dc = [ float(i) / 255 for i in ct.get_color(quality=1) ]
    else:
        try:
            dc = BORDER_COLORS[sheetName]
        except:
            dc = COLOR_BLACK
    
    return tuple(dc)

def getIcon(item,sheetName):
    iconName = None
    try:
        iconField = ICON_MAP[sheetName]
    except:
        iconField = None

    try:
        iconName = alphanum(getattr(item,iconField))
    except:
        pass
    return iconName

def getLevelColor(item):
    levelColor = COLOR_WHITE
    if hasattr(item,'spellevel'):
        levelColor = tuple(SPELL_LEVEL_COLORS[item.spellevel])
    return levelColor

def readItemList(sheet,keyCol):
    items = {}
    itemList = []
    for item in sheet:
        key = item.pop(keyCol)
        if key in items:
            continue
        items[key] = item
        if 'quantity' in item:
            qty = item['quantity']
        else:
            qty= 1
        i = 1
        while i <= qty:
            itemList.append(key)
            i += 1
    return items,itemList

def roundRect(ctx,x,y,width,height,r,rgb=COLOR_BLACK,thickness=10):
    ctx.save()
    ctx.set_line_width(thickness)
    ctx.set_source_rgb(*rgb)
    ctx.arc(x+r, y+r, r, math.pi, 3*math.pi/2)
    ctx.arc(x+width-r, y+r, r, 3*math.pi/2, 0)
    ctx.arc(x+width-r, y+height-r, r, 0, math.pi/2)
    ctx.arc(x+r, y+height-r, r, math.pi/2, math.pi)
    ctx.close_path()
    ctx.stroke()
    ctx.restore()
    return

def wrapText(ctx,layout,text,targetW,targetH,threshold=.2,fontSize=50,fontName=DEFAULT_FONT):
    mutable_text = text
    columns = len(mutable_text)

    # Reduce the font size
    def shrinkText(fontSize):
        fontSize -= .5
        return fontSize
    
    # Set the text object
    def setText(ctx,layout,text,fontSize):
        font = pango.FontDescription()
        font.set_size(pango.units_from_double(fontSize))
        font.set_family(fontName)
        layout.set_font_description(font)
        layout.set_text(text)
        pc.update_layout(ctx,layout)
        layout_iter = layout.get_iter()
        extents     = layout_iter.get_layout_extents()[1]
        w           = pango.units_to_double(extents.width)
        h           = pango.units_to_double(extents.height)
        return w,h

    # Start by setting text and getting the font size
    w,h = setText(ctx,layout,mutable_text,fontSize)
    while fontSize > 0 or ( w > targetW and h > targetH):
        w,h = setText(ctx,layout,mutable_text,fontSize)
        # Shrink to fit the height first
        if h > targetH:
            fontSize = shrinkText(fontSize)
            w,h = setText(ctx,layout,mutable_text,fontSize)
        # Size is good, all done
        elif w <= targetW:
            break
        # Width is within threshold, just shrink now - no more excessive wrapping
        elif w <= ( targetW + (float(targetW) * threshold )):
            while w > targetW:
                fontSize = shrinkText(fontSize)
                w,h = setText(ctx,layout,mutable_text,fontSize)
        # Wrapped as much as possible at current size.  Shrink the size, reset the text
        # and start over
        elif columns <= 1:
            fontSize = shrinkText(fontSize)
            mutable_text = text
            columns = len(mutable_text)
            w,h = setText(ctx,layout,mutable_text,fontSize)
        # Wrap the text, preserve line breaks, and see if that fits (it will be to big)
        elif w > targetW:
            columns -= 1
            mutable_text = '\n'.join(['\n'.join(wrap(line,columns,break_long_words=False)) for line in text.splitlines() if line.strip() != ''])
            w,h = setText(ctx,layout,mutable_text,fontSize)  
        # Check if width is in bounds, if yes then exit
        else:
            break
    w,h = setText(ctx,layout,mutable_text,fontSize)
    return int(w),int(h),fontSize,mutable_text

class cardItem:
    def __init__(self,data,name,sheetName):
        self.name = name
        for d in data:
            if d == 'Races' or d == 'Classes':
                setattr(self,d.lower().replace(' ',''),(r.strip() for r in data[d].split(',')))
            else:   
                setattr(self,d.lower().replace(' ',''),str(data[d]).strip())
        if sheetName == 'weapons':
            mod = 'STR'
            if self.finesse is not None and self.finesse != '':
                mod = 'DEX or STR'
            elif self.type == 'ranged':
                mod = 'DEX'
            if self.damage is not None and self.damage != '':
                self.damage = '{0} + {1}'.format(self.damage,mod)
            if self.versatile is not None and self.versatile != '':
                self.versatile = '{0} + {1}'.format(self.versatile,mod)

        # Try to set the image name
        try:
            imageName = self.image
        except:
            imageName = name
        imageName = alphanum(imageName)

        if os.path.isfile(imageName):
            self.image = imageName
        else:
            try:
                delattr(self,'image')
            except:
                pass    

def debug(text):
    log.debug(text)
    input('?')

def startLogger():
    log.basicConfig(level=log.DEBUG)

if __name__ == '__main__':
    startLogger()
    main()