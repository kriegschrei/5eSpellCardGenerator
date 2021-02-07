#!/usr/bin/env python3
import math
#import cairo
import cairocffi as cairo
from cairosvg.parser import Tree
from cairosvg.surface import PNGSurface
import cairosvg
#import gi
#gi.require_version('Rsvg','2.0')
#from gi.repository import Rsvg
#from ctypes import *
#l=CDLL('librsvg-2-2.dll')
#g=CDLL('libgoobject-2.0-0.dll')
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

DPI = 100
COLOR_BLACK=(0,0,0)
COLOR_WHITE=(1,1,1)
TITLE_FONT   = 'Dalelands Uncial'
ITALIC_FONT  = 'Mplantin-Italic'
DEFAULT_FONT = 'Mplantin'


def percent(n,r):
    return n*r

def nameToRgb(name):
    return tuple( float(i)/255 for i in name_to_rgb(name))

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

pageWidthInches,pageHeightInches  = 8.5,11
pageHeightPoints, pageWidthPoints = pageHeightInches * DPI, pageWidthInches * DPI
cardHeightInches, cardWidthInches = 3.5,2.5
cardWidthPoints, cardHeightPoints = cardWidthInches * DPI, cardHeightInches * DPI
width, height = cardWidthPoints, cardHeightPoints
rowsPerPage = math.floor(pageWidthPoints / cardWidthPoints )
colsPerPage = math.floor(pageHeightPoints / cardHeightPoints )
interColBuffer = ( pageWidthPoints - ( cardWidthPoints * colsPerPage ) ) / ( colsPerPage + 1 )
interRowBuffer = ( pageHeightPoints - ( cardHeightPoints * rowsPerPage ) ) / ( rowsPerPage + 1 )




ASSET_PATH = 'Assets'
TIME_REGEX = re.compile('(?P<spec>instantaneous|hour|minute|day|bonus|reaction|action|round)',re.IGNORECASE)
RANGE_REGEX = re.compile('(?P<spec>self|touch|ft|radius|mile|sight)',re.IGNORECASE)
TARGET_REGEX = re.compile('(?P<spec>humanoid|creature|self|sphere|cone|line|square|cube|radius)',re.IGNORECASE)
SAVE_REGEX = re.compile('(?P<spec>str|int|cha|wis|dex|con)',re.IGNORECASE)
EFFECT_REGEX = re.compile('(?P<spec>acid|bludgeoning|buff|charmed|cold|combatdefense|communication|control|creation|debuff|detection|exploration|fire|force|foreknowledge|frightened|healing|light|lightning|melee|movement|necrotic|piercing|poison|prone|psychic|radiant|ranged|restrained|shapechanging|social|summoning|thunder|unconcious|utility|warding)',re.IGNORECASE)
ATTACK_REGEX = re.compile('(?P<spec>melee|ranged)',re.IGNORECASE)
COMPONENT_LIST = [ 'ritual','concentration','verbal','somatic','material','consumed' ]
SPEC_LIST      = [
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
PIXEL_BUFFER = 2
CARD_TOP_OFFSET = percent(.04 ,cardHeightPoints)
BORDER_WIDTH = percent(.02,cardWidthPoints)
SPELL_TITLE_HEIGHT = percent(.12,cardHeightPoints)
SPELL_TITLE_WIDTH = cardWidthPoints - (BORDER_WIDTH * 2)
SPELL_LEVEL_WIDTH = percent(.14,cardWidthPoints)
SPELL_LEVEL_HEIGHT = CARD_TOP_OFFSET + SPELL_TITLE_HEIGHT
SMALL_TEXT_BOX_HEIGHT = percent(.03,cardHeightPoints)
MEDIUM_TEXT_BOX_HEIGHT = percent(.04,cardHeightPoints)
THREE_PERCENT_HEIGHT = percent(.03,cardHeightPoints)
THREE_HALF_PERCENT_HEIGHT = percent(.035,cardHeightPoints)
FOUR_PERCENT_HEIGHT = percent(.04,cardHeightPoints)
FIVE_PERCENT_HEIGHT = percent(.05,cardHeightPoints)
EIGHTY_PCT_WIDTH    = percent(.8,cardWidthPoints)

parser = OptionParser()
parser.add_option('-c','--config',dest='configFile',help='CSV file to read')
(opts,args) = parser.parse_args()

def main():
    filename = 'test.pdf'
    surface = cairo.PDFSurface(filename,pageWidthPoints,pageHeightPoints)
    #layout = PangoCairo.create_layout(context)

    ctx = cairo.Context(surface)
    # Get spells
    try:
        spells,spellList = readSpellList(opts.configFile)
    except Exception as e:
        print('Unable to open csv file: {0}'.format(str(e)))
        exit(1) 
    spellCount = len(spells)

    # New page
    currentPage = 1
    idx = 0
    while idx < spellCount:
        # Set the row count to 1, it's a new page
        currentRow = 1
        # Start the drawing right inside the buffer
        currentX = interColBuffer
        currentY = interRowBuffer
        while currentRow <= rowsPerPage and idx < spellCount:
            # New column, set the column count to 1
            currentCol = 1
            while currentCol <= colsPerPage and idx < spellCount:
                s = spellList[idx]
                print('Working on spell {0}, idx {1}, page {2}, row {3}, col {4}'.format(s,idx,currentPage,currentRow,currentCol))
                spell = Spell(spells[s],s)
                # Draw the actual card
                makeCard(ctx,spell,currentX,currentY)
                # Update the current x position to 1 card width + the buffer
                currentX += cardWidthPoints + interColBuffer
                # Increment the index
                idx += 1
                # Increment the column count
                currentCol += 1
            # Increment the row count and move the cursor
            currentY += cardHeightPoints + interRowBuffer
            # Reset the X coordinate
            currentX = interColBuffer
            # Increment the row count
            currentRow += 1
        # Increment the page count
        currentPage += 1
        # Add the page
        ctx.show_page()
    # Finish the darwing
    surface.finish()
                            

def makeCard(ctx,spell,x,y):
    origX,origY = ( x,y)
    bottomY = y + cardHeightPoints - BORDER_WIDTH
    x += BORDER_WIDTH
    y += BORDER_WIDTH
    
    #ctx.move_to(origX,origY)
    # Get the main color from colorThief
    schoolColor = getSchoolColor(spell.school)
    # Text location
    addSchoolTextAndReference(ctx,spell.school,spell.reference,x+(width*.1),y)
    y += CARD_TOP_OFFSET
    y += addSpellTitle(
        ctx=ctx,
        x=x,
        y=y,
        width=SPELL_TITLE_WIDTH,
        height=SPELL_TITLE_HEIGHT,
        color=schoolColor,
        school=spell.school.lower(),
        text=spell.name.upper()
    )
        # Make and place the spell level banner
    spellLevelBanner(ctx,spell.level,x+SPELL_TITLE_WIDTH-SPELL_LEVEL_WIDTH-1,origY-1)

    # Add the spell level text
    drawText(
        ctx=ctx,
        text=spell.level.upper(),
        fontName=TITLE_FONT,
        # Find the left side of the spell level box (the box is adjused -1 in spellLevelBanner)
        x = x + SPELL_TITLE_WIDTH - SPELL_LEVEL_WIDTH,
        # The top of the banner
        y = origY,
        targetW=SPELL_LEVEL_WIDTH-2,
        targetH=SPELL_LEVEL_HEIGHT-2,
        threshold=.10,
        talign='Center'
    )

    # Add the school text and reference under the spell name banner
    # Get the height of the text box to move below it
    # Original location
    #y += addSchoolTextAndReference(ctx,spell.school,spell.reference,x,y)
    y += 1
    # Set the "components" - Concentration, Ritual, Verbal, Somatic, Material. Icons and text
    y += 1 + addSpellComponents(ctx,spell,SPELL_TITLE_WIDTH,x+1,y)
    # Add the material components, if they exist
    if spell.materialcomponents:
        if spell.materialcomponents[0] != '(':
            spell.materialcomponents = '({0}'.format(spell.materialcomponents)
        if spell.materialcomponents[-1] != ')':
            spell.materialcomponents = '{0})'.format(spell.materialcomponents)
        _,h,_ = drawText(
            ctx=ctx,
            text=spell.materialcomponents,
            fontName=ITALIC_FONT,
            x = x,
            y = y,
            targetW = SPELL_TITLE_WIDTH,
            targetH = SMALL_TEXT_BOX_HEIGHT,
            talign = 'Center'
        )
        y += h + 1
    # Add a horizontal bar
    y += 1 + addRectangle(ctx,x,y,SPELL_TITLE_WIDTH,BORDER_WIDTH,schoolColor)
    # Add the stats ( Casting Time, Range, Target, Duration, Saving Throw, Attack, Effect)
    y += 1 + addSpellSpecs(ctx,spell,SPELL_TITLE_WIDTH,x,y)
    # If "AT HIGHER LEVELS"
    if spell.athigherlevels:
        y += 1 + addHigherLevelTitle(
            ctx=ctx,
            x=x,
            y=y,
            width=SPELL_TITLE_WIDTH,
            height=THREE_HALF_PERCENT_HEIGHT,
            color=schoolColor,
            text='AT HIGHER LEVELS'
        )
        t = spell.athigherlevels.split('\n')
     #   print('t:{0}'.format(t))
        tt = len(t)
      #  print('tt:{0}'.format(tt))
        ttt = tt * SMALL_TEXT_BOX_HEIGHT
       # print('TTT:{0}'.format(ttt))
       #     input('?')
        w,h,_ = drawText(
            ctx=ctx,
            text=spell.athigherlevels,
            fontName=DEFAULT_FONT,
            x = x,
            y = y,
            targetW = SPELL_TITLE_WIDTH,
            targetH = ttt,
            threshold=.5,
            color = COLOR_BLACK,
            talign = 'Center',
            halign = 'Center',
            valign = 'Top'
        )
        y += 1 + h
        # Add the "At Higher Levels" bar
        # Add the "At Higher Levels" text
    # Add a horizontal spacer bar
    y += 1 + addRectangle(ctx,x,y,SPELL_TITLE_WIDTH,BORDER_WIDTH,schoolColor)

    # Jump to the bottom, add the classes and class text\
    bottomY -= 1 + addClasses(ctx,spell,SPELL_TITLE_WIDTH,x,bottomY)
    # Add a horizontal spacer bar above the classes
    bottomY -= 1 + addRectangle(ctx,x,bottomY - BORDER_WIDTH,SPELL_TITLE_WIDTH,BORDER_WIDTH,schoolColor)
    # The rest of the space is for descriptive text, make it fit
    drawText(
        ctx = ctx,
        text = spell.description,
        x = x + 1,
        y = y,
        targetW = SPELL_TITLE_WIDTH - 2,
        targetH = bottomY - y,
        threshold = 0.1,
        valign = 'Top',
        halign = 'Left',
        talign = 'Left'
    )


    # Add colored border
   # ctx.restore()
   # ctx.new_path()
    #s  ctx.move_to(origX,origY)
    addRoundedBorder(
        ctx=ctx,
        c=schoolColor,
        x=origX+(BORDER_WIDTH/2),
        y=origY+(BORDER_WIDTH/2),
        w=width-BORDER_WIDTH,
        h=height-BORDER_WIDTH,
        t=BORDER_WIDTH,
    )
    # And a thin black border around the whole thing
    ctx.set_source_rgb(0,0,0)
    ctx.set_line_width(1)
    ctx.rectangle(origX,origY,width,height)
    ctx.stroke()
    # return
    return

def addClasses(ctx,spell,w,x,y):
    # Save the context
    ctx.save()
    # Create the layout
    layout = pc.create_layout(ctx)
    # Sort the class list
    classList = sorted([ c for c in spell.classes ])
    # Get the width in points per class
    classTextWidth = w/len(classList)
    # Find the center of each point segment
    classTextCenter = classTextWidth/2
    # Set the icon diameter, it's 10% of the width for no real reason
    classIconDiameter = cardWidthPoints * .1
    # Collect the font sizes per class
    classFontSizes = {}
    for c in classList:
        cw,ch,fontSize,_ = wrapText(ctx,layout,c.lower(),classTextWidth,SMALL_TEXT_BOX_HEIGHT)
        classFontSizes[c] = {
            'w' : cw,
            'fs' : fontSize,
            'h' : ch,
        }
    # Use the smallest font size
    fontSize = min( [ classFontSizes[c]['fs'] for c in classFontSizes])
    # And the biggest height
    fontHeight  = max( [ classFontSizes[c]['h'] for c in classFontSizes])
    # Right now Y is at the bottom of the image, move it up to the top of the text
    y -= fontHeight + classIconDiameter + 2
    # Set the starting center of the text and image (back it up by 1/2 of each width later)
    currentXOffset = x + classTextCenter
    for c in classList:

        w,h,_ = drawText(
            ctx      = ctx,
            text     = c,
            x        = currentXOffset - classFontSizes[c]['w']/2,
            y        = y,
            targetW  = classFontSizes[c]['w'],
            targetH  = fontHeight,
            valign   = 'Top',
            fontSize = fontSize
        )
        drawRoundSurface(
            ctx=ctx,
            imagePath='{0}/ClassesAndSchools/{1}.png'.format(ASSET_PATH,c.lower()),
            diameter=classIconDiameter,
            x=currentXOffset-classIconDiameter/2,
            y=y + fontHeight + 1
        )
        currentXOffset += classTextWidth
    ctx.restore()
    return fontHeight + classIconDiameter + 1

def addHigherLevelTitle(ctx,x,y,width,height,color,text,fontName=TITLE_FONT,fontColor=COLOR_WHITE):
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


def addSpellTitle(ctx,x,y,width,height,color,school,text,fontName=TITLE_FONT,fontColor=COLOR_WHITE,talign='Center'):
    # Make and place the spell name banner
    addRectangle(
        ctx=ctx,
        x=x,
        y=y,
        w=width,
        h=height,
        c=color
    )
    # Scale and place the spell school icon
    drawRoundSurface(
        ctx=ctx,
        imagePath='{0}/ClassesAndSchools/{1}.png'.format(ASSET_PATH,school),
        diameter=height,
        x=x+1,
        y=y
    )
    # Set the spell name text (dependant on the width of the school icon and level banner)
    drawText(
        ctx=ctx,
        text=text,
        fontName=fontName,
        x=x+1+height+(BORDER_WIDTH/2),
        y=y+(BORDER_WIDTH/2),
        targetW=width - height - SPELL_LEVEL_WIDTH - BORDER_WIDTH,
        targetH=height-BORDER_WIDTH,
        color=fontColor,
        talign=talign
    )
    return height

def addSpellSpecs(ctx,spell,w,x,y):
    ctx.save()
    origY = y
    layout = pc.create_layout(ctx)
    spaceWidth = w
    #specList = []
    # Get list of specs to parse
    #for i,s in iter(SP)
    totalHeight = 0
    specList = [ s for i,s in enumerate(SPEC_LIST) if getattr(spell,SPEC_LIST[i]['col'])]
    
    # Get the minimum font size and maximum width for each of the texts
    fontSizeMin = 200
    textWidthMax = 0
    heightMax = 0

    for spec in specList:
        # Find the minimum font size to fit the text
        # Jam the text together
        thisText = '{0}{1}'.format(spec['name'],getattr(spell,spec['col'])).replace('\n',' ')
        # Get the size needed
        # Initial runthrough is with max width
        # Threshold is high because we don't want any wrapping, ever
        sw,sh,fontSize,_ = wrapText(ctx,layout,thisText,spaceWidth,THREE_HALF_PERCENT_HEIGHT,threshold=10)
        if fontSize < fontSizeMin:
            fontSizeMin = fontSize
        if sw > textWidthMax:
            textWidthMax = sw
        if sh > heightMax:
            heightMax = sh
    # Going through again, now to scale it down since we have the height
    tempHeight = heightMax
    for spec in specList:
        thisText = '{0}{1}'.format(spec['name'],getattr(spell,spec['col'])).replace('\n',' ')
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
        tw,_,_,_ = wrapText(ctx,layout,getattr(spell,spec['col']).replace('\n',' '),textWidthMax-4,heightMax,threshold=1000,fontSize=fontSizeMin)
        if tw > TextWidthMax:
            TextWidthMax = tw
    
    # now, finally do it
    for spec in specList:
        thisX = x + 1
        addSVG(
            ctx=ctx,
            svg=spec['col'],
            x=x+1,
            y=y,
            w=heightMax,
            h=heightMax,
        )
        thisX += heightMax + 1
        
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
        specText = getattr(spell,spec['col'])
        thisX += NameWidthMax + 1
        regMatch = spec['regex'].search(specText)
        if regMatch is not None:
            s = regMatch.groupdict()['spec'].lower()
         #   print(s)
            try:
                addSVG(
                    ctx=ctx,
                    svg=s,
                    x=thisX,
                    y=y,
                    w=heightMax,
                    h=heightMax,
                )
            except Exception as e:
                print("can't create svg '{0}': {1}".format(s,str(e)))
        thisX += heightMax + 1
        
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
        y += heightMax + 1

        # Layout should be:
        # specName left of center (add colon)
        # icon left of that
        # specText icon right of center
        # specText right of that
        # Get the specName
    ctx.restore()
    return y - origY

        
    


def addSpellComponents(ctx,spell,w,x,y):
    ctx.save()
    layout = pc.create_layout(ctx)
    # A list of the components in the spell
    componentList = [ c for c in COMPONENT_LIST if getattr(spell,c)]
    
    # The width per component, in points
    componentTextWidth  = w/len(componentList)
    componentTextCenter = componentTextWidth/2
    componentFontSizes  = {}
    # Find the usable font size for each word
    for c in componentList:
        cw,ch,fontSize,_ = wrapText(ctx,layout,c.lower(),componentTextWidth,SMALL_TEXT_BOX_HEIGHT)
        componentFontSizes[c] = {
            'w' : cw,
            'fs' : fontSize,
            'h' : ch,
        }
    # Get the minimum size
    fontSize=200
    fontHeight=0
    fontSize=min([ componentFontSizes[c]['fs'] for c in componentFontSizes ] )
    fontHeight=max([ componentFontSizes[c]['h'] for c in componentFontSizes] )
    # Go back and draw them
    currentXOffset = x + componentTextCenter
    for comp in componentList:
        w,h,_ = drawText(
            ctx=ctx,
            text=comp,
            x=currentXOffset - componentFontSizes[comp]['w']/2,
            y=y,
            targetW=componentFontSizes[comp]['w'],
            targetH=fontHeight,
            fontSize=fontSize
        )
        addSVG(
            ctx=ctx,
            svg=comp,
            x=currentXOffset - fontHeight / 2,
            y=y + fontHeight + 1,
            w=fontHeight,
            h=fontHeight
        )

        currentXOffset += componentTextWidth

    ctx.restore()
    return fontHeight*2 + 1

def addSVG(ctx,svg,x,y,w,h):
    ctx.save()
    svgFile='{0}/Icons/{1}.svg'.format(ASSET_PATH,svg)
    svgObj = cairosvg.svg2png(
        bytestring=open(svgFile,'rb').read(),
        write_to= None,
        dpi = DPI,
        output_width = 512,
        output_height = 512
    )
    svgBytes = io.BytesIO(svgObj)
    svgSurface = cairo.ImageSurface.create_from_png(svgBytes)
    width = svgSurface.get_width()
    height = svgSurface.get_height()
    scale = h/height
    ctx.translate(x,y)
    ctx.scale(scale,scale)
    ctx.set_source_surface(svgSurface,0,0)
    ctx.paint()
    ctx.restore()
    return

def addSchoolTextAndReference(ctx,school,ref,x,y):
    # Set the spell school text under the logo
    refX = x + 1
    refY = y + 1
    refH = SMALL_TEXT_BOX_HEIGHT
    refW = cardWidthPoints - (BORDER_WIDTH * 2) - (PIXEL_BUFFER*2) - SPELL_LEVEL_WIDTH - (width*.1)
    # Text
    refW - SPELL_TITLE_WIDTH
    sw,sh,_ = drawText(
        ctx=ctx,
        text=school.lower(),
        fontName=ITALIC_FONT,
        x=refX,
        y=refY,
        targetH=refH,
        targetW=refW,
        valign='Center',
        halign='Left',
        talign='Left'
    )
    # Set the reference under the spell level banner
    rw,rh,_ = drawText(
        ctx=ctx,
        text=ref.upper(),
        fontName=ITALIC_FONT,
        x=refX,
        y=refY,
        targetH=refH,
        targetW=refW,
        valign='Top',
        halign='Right',
        talign='Right'
    )
    return max(rh,sh) #Return the max height of this text area

def drawText(ctx,text,x,y,targetW,targetH,fontName=DEFAULT_FONT,threshold=.2,color=COLOR_BLACK,valign='Center',halign='Center',talign='Left',fontSize=200):
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

def wrapText(ctx,layout,text,targetW,targetH,threshold=.2,fontSize=200,fontName=DEFAULT_FONT):
    #print('TW:{0},TH{1}'.format(targetW,threshold))
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
    #print('{0},{1},{2},{3}'.format(w,h,targetW,targetH))
    return int(w),int(h),fontSize,mutable_text
    
def addRectangle(ctx,x,y,w,h,c):
    ctx.set_source_rgb(*c)
    ctx.rectangle(x,y,w,h)
    ctx.set_line_width(0)
    ctx.fill()
    return h

def addRoundedBorder(ctx,c,x,y,w,h,t):
    roundRect(
        ctx=ctx,
        x=x,
        y=y,
        width=w,
        height=h,
        r=w*0.1,
        thickness=t,
        rgb=c
    )

    return

def drawSVG(ctx,imagePath,x,y,w,h):
    # save the content
    return

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

def spellLevelBanner(ctx,level,x,y):
    # Set the color to the spell level's color
    ctx.set_source_rgb(*(SPELL_LEVEL_COLORS[level]))
    ctx.move_to(x, y+1)
    # Draw down 70% of the shape
    ctx.rel_line_to(0,percent(.7,SPELL_LEVEL_HEIGHT-1))
    # Make the point
    ctx.rel_line_to(SPELL_LEVEL_WIDTH/2,percent(.3,SPELL_LEVEL_HEIGHT))
    # And back up to the right
    ctx.rel_line_to(SPELL_LEVEL_WIDTH/2,percent(-.3,SPELL_LEVEL_HEIGHT))
    # Draw back up to the top of the border box
    ctx.line_to(x+SPELL_LEVEL_WIDTH,y+BORDER_WIDTH+CARD_TOP_OFFSET)
    # Radius is half the width
    r = SPELL_LEVEL_WIDTH / 2
    # Create an arc -90 degrees back to the starting point
    ctx.arc_negative(x +SPELL_LEVEL_WIDTH - r,y + BORDER_WIDTH + r,r,0,-90*(math.pi/180))
    # Close up the path
    #ctx.close_path()
    # Fill it
    ctx.fill_preserve()
    # Draw a black line
    ctx.set_source_rgb(0,0,0)
    ctx.set_line_width(1)
    ctx.stroke()
    return

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

def roundRect(ctx,x,y,width,height,r,rgb=COLOR_BLACK,thickness=10):
    ctx.set_line_width(thickness)
    ctx.set_source_rgb(*rgb)
    ctx.arc(x+r, y+r, r, math.pi, 3*math.pi/2)
    ctx.arc(x+width-r, y+r, r, 3*math.pi/2, 0)
    ctx.arc(x+width-r, y+height-r, r, 0, math.pi/2)
    ctx.arc(x+r, y+height-r, r, math.pi/2, math.pi)
    ctx.close_path()
    ctx.stroke()
    return

def getSchoolColor(school):
    ct = ColorThief('{0}/ClassesAndSchools/{1}.png'.format(ASSET_PATH,school.lower()))
    dc = [ float(i) / 255 for i in ct.get_color(quality=1) ]
    
    return tuple(dc)

class Spell:
	def __init__(self,data,name):
		self.name = name
		for d in data:
			if d== 'Classes':
				setattr(self,d.lower().replace(' ',''),data[d].strip().split(','))
			else:
				setattr(self,d.lower().replace(' ',''),data[d].strip())
                
if __name__ == '__main__':
    main()