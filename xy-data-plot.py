#! /usr/bin/python3
'''
Copyright (C) 2020 Christian Hoffmann christian@lehrer-hoffmann.de

##This extension allows you to draw a Cartesian grid in Inkscape.
##There is a wide range of options including subdivision, subsubdivions
## and logarithmic scales. Custom line widths are also possible.
##All elements are grouped with similar elements (eg all x-subdivs)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

from inkex import TextElement, Effect, Line, PathElement, Style, Vector2d
from inkex import Group, Rectangle, Boolean as Bool, errormsg, AbortExtension
import math
import re

def getCSVData(csvfile,fileencoding,csvoptions,ignorefirst,xidx,yidxarr):
  import csv
  data = XYValues(len(yidxarr))
  with open(csvfile, newline='', encoding=fileencoding ) as f:
    reader = csv.reader(f,**csvoptions)
    try:
      for row in reader:
        if reader.line_num <= ignorefirst:
            continue
        try:
          data.append( float(row[xidx]), [ float(row[yidx]) for yidx in yidxarr ] )
        except ValueError as e:
          errormsg(_("Float error: line {}: {}".format(reader.line_num, row)))
        except IndexError:
          errormsg(_("Not enough fields in line {}: {}".format(reader.line_num, row)))
    except csv.Error as e:
      errormsg(_("Error on importing CSV: {}\n{}\n{}".format(csvfile, reader.line_num, e)))
  return data

# Helper function for getting proper min-max-values
def ceil( n, decimals = None ):
  if not decimals:
    decimals = 1 if n == 0 else int( math.log10(abs(n)) )
  multiplier = 10 ** decimals
  return math.ceil(n / multiplier) * multiplier

def floor( n, decimals = None ):
  if not decimals:
    decimals = 1 if n == 0 else int( math.log10(abs(n)) )
  multiplier = 10 ** decimals
  return math.floor(n / multiplier) * multiplier

def textAt( x, y, text, style, rotate=0 ):
  "Places a test-element at global-coordinates."
  
  elem = TextElement(x=str(x), y=str(y))
  elem.text = text
  elem.style = style
  if rotate != 0:
    elem.set('transform','rotate({},{},{})'.format(rotate,x,y))
  return elem

def intersectionParameter(s0,s1,smax):
  if s1 == s0:
    return math.inf
  return (smax-s0)/(s1-s0)

def intersectionPoint(values,prevalues,xmin,xmax,ymin,ymax):
  sxmin = intersectionParameter(prevalues['x'],values['x'],xmin)
  sxmax = intersectionParameter(prevalues['x'],values['x'],xmax)
  symin = intersectionParameter(prevalues['y'],values['y'],ymin)
  symax = intersectionParameter(prevalues['y'],values['y'],ymax)
  s = 1
  if sxmin >= 0 and sxmin < 1 and sxmin < s:
    s = sxmin
  if sxmax >= 0 and sxmax < 1 and sxmax < s:
    s = sxmax
  if symin >= 0 and symin < 1 and symin < s:
    s = symin
  if symax >= 0 and symax < 1 and symax < s:
    s = symax
  return {'x': prevalues['x']+s*(values['x']-prevalues['x']), 'y': prevalues['y']+s*(values['y']-prevalues['y'])}

class XYValues:
  def __init__(self, numberOfYColumns=1 ):
    self.nYCols = numberOfYColumns
    self.data = []
    self.xmin = None
    self.xmax = None
    self.ymin = [None for i in range(numberOfYColumns)]
    self.ymax = [None for i in range(numberOfYColumns)]
  
  def __iter__(self):
    return iter(self.data)
  
  def append(self, x, yarr):
    self.data.append({'x':x,'y':yarr})
  
  def len(self):
    return len(self.data)
  
  def sort(self):
    self.data.sort(key=lambda tup: tup['x'])
  
  def getXMinMax(self):
    return self.xmin,self.xmax
  
  def getYMinMax(self):
    return min(self.ymin),max(self.ymax)
  
  def calculateMinMax(self):
    (self.xmin,self.xmax) = self._calculateMinMaxFromArray([val['x'] for val in self.data])
    for i in range(self.nYCols):
      (self.ymin[i],self.ymax[i]) = self._calculateMinMaxFromArray([val['y'][i] for val in self.data])
  
  def _calculateMinMaxFromArray(self,array,round=True):
    vmin = min(array)
    vmax = max(array)
    
    if round:
      vmax = ceil(vmax)
      vmin = floor(vmin, decimals = 1 if vmax == 0 else int( math.log10(abs(vmax)) ) )
    return (vmin, vmax)

class Axis:
  def __init__(self, von: Vector2d, bis: Vector2d, min: float, max: float ):
    "We need two svg-points and the min- and max-value of the axis."
    self.von = von
    self.bis = bis
    self.min = min
    self.max = max
    self.winkel = math.atan2(bis.y-von.y,bis.x-von.x)
    self.cos = math.cos(self.winkel)
    self.sin = math.sin(self.winkel)
    if min == max:
      raise ValueError('min == max')
  
  def transform(self, val: float):
    "Transform scalar value of axis to svg xy-coordinates"
    
    return self.von+(val-self.min)/(self.max-self.min)*(self.bis-self.von)
  
  def getTicks( self, ticks: int, linevon: float, linebis: float, style: Style):
    "The main ticks, linevon and linebis are the start- and end-point perpendicular to the axis in svg-coordinates."
    
    group = Group()
    if ticks <= 0:
      return group
    
    step = (self.max-self.min) / ticks
    for i in range(ticks+1):
      val = self.min + i * step
      point = self.transform(val)
      line = Line(
        x1=str(point.x-linevon*self.sin),
        y1=str(point.y+linevon*self.cos),
        x2=str(point.x-linebis*self.sin),
        y2=str(point.y+linebis*self.cos)
      )
      line.style = style
      group.add(line)
    return group

  def getSubTicks( self, ticks: int, subticks: int, linevon: float, linebis: float, style: Style):
    "Only the ticks between the main ticks, linevon and linebis are the start- and end-point perpendicular to the axis in svg-coordinates."
    
    group = Group()
    if ticks <= 0 or subticks <= 0:
      return group
    
    step = (self.max-self.min) / ticks
    for i in range(ticks):
      val = self.min + i * step
      for j in range(1,subticks+1):
        subval = val + j * step / (subticks+1)
        point = self.transform(subval)
        line = Line(
          x1=str(point.x-linevon*self.sin),
          y1=str(point.y+linevon*self.cos),
          x2=str(point.x-linebis*self.sin),
          y2=str(point.y+linebis*self.cos)
        )
        line.style = style
        group.add(line)
    return group
    
  def getNumbers( self, ticks: int, fmtstr: str, intan: float, inrad: float, style: Style ):
    "The numbers at the main-ticks. intan: shift perpendicular to axis, inrad: shift in axis."
    
    group = Group()
    if ticks <= 0:
      return group
    
    step = (self.max-self.min) / ticks
    for i in range(ticks+1):
      val = self.min + i * step
      point = self.transform(val)
      group.add( textAt( point.x-intan*self.sin+inrad*self.cos, point.y+intan*self.cos+inrad*self.sin, ("{0:"+fmtstr+"}").format(val), style) )
    return group
  
class XY_Data_Plot(Effect):
  def __init__(self):
    Effect.__init__(self)

    self.arg_parser.add_argument("--tab")
    self.arg_parser.add_argument("--csv_file",        dest="csv_file",      action="store", type=str,  default="")
    self.arg_parser.add_argument("--csv_encoding",    dest="csv_encoding",  action="store", type=str,  default="utf-8")
    self.arg_parser.add_argument("--csv_delimiter",   dest="csv_delimiter", action="store", type=str,  default=";")
    self.arg_parser.add_argument("--csv_columnx",     dest="xidx",          action="store", type=int,  default=0)
    self.arg_parser.add_argument("--csv_columny",     dest="yidxs",         action="store", type=str,  default="1")
    self.arg_parser.add_argument("--csv_ignorefirst", dest="ignorefirst",   action="store", type=int,  default=0)
    self.arg_parser.add_argument("--csv_storedata",   dest="storedata",     action="store", type=Bool, default="false")
    
    self.arg_parser.add_argument("--xaxis_format"   ,  dest="xformat"   , action="store", type=str,   default="")
    self.arg_parser.add_argument("--xaxis_min"      ,  dest="xmin"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--xaxis_max"      ,  dest="xmax"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--xaxis_tick_n"   ,  dest="xtickn"    , action="store", type=int,   default=10)
    self.arg_parser.add_argument("--xaxis_subtick_n",  dest="xsubtickn" , action="store", type=int,   default=0)
    self.arg_parser.add_argument("--xaxis_ticksin"  ,  dest="xticksin"  , action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--xaxis_ticksout" ,  dest="xticksout" , action="store", type=Bool, default="false")
    self.arg_parser.add_argument("--xaxis_grid"     ,  dest="xgrid"     , action="store", type=Bool, default="false")
    
    self.arg_parser.add_argument("--yaxis_format"   ,  dest="yformat"   , action="store", type=str,   default="")
    self.arg_parser.add_argument("--yaxis_min"      ,  dest="ymin"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--yaxis_max"      ,  dest="ymax"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--yaxis_tick_n"   ,  dest="ytickn"    , action="store", type=int,   default=10)
    self.arg_parser.add_argument("--yaxis_subtick_n",  dest="ysubtickn" , action="store", type=int,   default=0)
    self.arg_parser.add_argument("--yaxis_ticksin"  ,  dest="yticksin"  , action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--yaxis_ticksout" ,  dest="yticksout" , action="store", type=Bool, default="false")
    self.arg_parser.add_argument("--yaxis_grid"     ,  dest="ygrid"     , action="store", type=Bool, default="false")

    self.arg_parser.add_argument("--border_create_left"  , dest="border_left"  , action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--border_create_bottom", dest="border_bottom", action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--border_create_right" , dest="border_right" , action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--border_create_top"   , dest="border_top"   , action="store", type=Bool, default="true")
    
    self.arg_parser.add_argument("--label_title", dest="label_title", type=str, action="store", default="")
    self.arg_parser.add_argument("--label_xaxis", dest="label_xaxis", type=str, action="store", default="")
    self.arg_parser.add_argument("--label_yaxis", dest="label_yaxis", type=str, action="store", default="")
    
    self.arg_parser.add_argument("--stroke_width"     , dest="stroke_width"     , type=float, action="store", default="1")
    self.arg_parser.add_argument("--stroke_width_unit", dest="stroke_width_unit", type=str  , action="store", default="px")
    self.arg_parser.add_argument("--shape_remove_old" , dest="remove", action="store", type=Bool, default="false")

  def transformx(self,x):
    "Transforms x-data-values in svg x-coordinates."
    
    return (x-self.xmin)*self.bb.width/(self.xmax-self.xmin)+self.bb.left

  def transformy(self,y):
    "Transforms y-data-values in svg y-coordinates."
    
    return (self.ymax-y)*self.bb.height/(self.ymax-self.ymin)+self.bb.top
  
  def plotPath( self, style, yidx=0 ):
    "Generates path-command-string and returns a path-element."
    
    pathstr = ""
    dataiter = iter(self.data)
    vals = next(dataiter)
    values = {'x':vals['x'],'y':vals['y'][yidx]}
    
    nextmove = 'M'
    if values['x'] > self.xmin and values['x'] < self.xmax and values['y'] > self.ymin and values['y'] < self.ymax:
      pathstr += '{}{},{}'.format( nextmove, self.transformx(values['x']), self.transformy(values['y']) )
      nextmove = 'L'
    
    prevalues=values
    while True:
      try:
        vals = next(dataiter)
        values = {'x':vals['x'],'y':vals['y'][yidx]}
      except StopIteration:
        break
      if values['x'] > self.xmin and values['x'] < self.xmax and values['y'] > self.ymin and values['y'] < self.ymax:
        if nextmove == 'M':
          interpoint = intersectionPoint(values,prevalues,self.xmin,self.xmax,self.ymin,self.ymax)
          pathstr += ' {}{},{}'.format( nextmove, self.transformx(interpoint['x']), self.transformy(interpoint['y']) )
          nextmove = 'L'
        pathstr += ' {}{},{}'.format( nextmove, self.transformx(values['x']), self.transformy(values['y']) )
        nextmove = 'L'
      else:
        if nextmove == 'L':
          interpoint = intersectionPoint(values,prevalues,self.xmin,self.xmax,self.ymin,self.ymax)
          pathstr += ' {}{},{}'.format( nextmove, self.transformx(interpoint['x']), self.transformy(interpoint['y']) )
        nextmove = 'M'
      prevalues = values
      
    newpath = PathElement(d=pathstr)
    newpath.style = style
    
    return newpath

  def createBorderLine(self,side,style):
    "Returns a border line of the given bounding box."
    
    line = Line()
    line.style = style
    if side == 'left':
      line.set('x1',self.bb.minimum.x)
      line.set('y1',self.bb.minimum.y)
      line.set('x2',self.bb.minimum.x)
      line.set('y2',self.bb.maximum.y)
    elif side == 'bottom':
      line.set('x1',self.bb.minimum.x)
      line.set('y1',self.bb.maximum.y)
      line.set('x2',self.bb.maximum.x)
      line.set('y2',self.bb.maximum.y)
    elif side == 'right':
      line.set('x1',self.bb.maximum.x)
      line.set('y1',self.bb.minimum.y)
      line.set('x2',self.bb.maximum.x)
      line.set('y2',self.bb.maximum.y)
    elif side == 'top':
      line.set('x1',self.bb.minimum.x)
      line.set('y1',self.bb.minimum.y)
      line.set('x2',self.bb.maximum.x)
      line.set('y2',self.bb.minimum.y)
    return line
    
  def effect(self):
  
    # Create some styles first

    linewidth = self.svg.unittouu(str(self.options.stroke_width)+self.options.stroke_width_unit)
    cssstyle = {
      'stroke': '#000000',
      'stroke-width': linewidth,
      'fill': 'none',
      'stroke-linecap': 'butt',
      'stroke-linejoin': 'round'
    }
    pathstyle = Style(cssstyle)
    cssstyle['stroke-linecap'] = 'square'
    borderstyle = Style(cssstyle)
    cssstyle['stroke-width'] = linewidth*0.6
    tickstyle = Style(cssstyle)
    cssstyle['stroke-width'] = linewidth*.3
    subtickstyle = Style(cssstyle)
    cssstyle['stroke'] = '#999'
    cssstyle['stroke-width'] = linewidth*0.5
    gridstyle = Style(cssstyle)
    cssstyle['stroke-width'] = linewidth*0.2
    subgridstyle = Style(cssstyle)

    self.ticksize    = self.svg.unittouu("8px")
    self.subticksize = self.svg.unittouu("4px")
    self.fontsize    = self.svg.unittouu("10pt")

    textstyle = {
      'font-size': self.fontsize,
      'fill-opacity': '1.0',
      'stroke': 'none',
      'text-align': 'end',
      'text-anchor': 'end',
      'font-weight': 'normal',
      'font-style': 'normal',
      'fill': '#000'
    }
    textrechtsbdg = Style(textstyle)
    textstyle['text-align']='center'
    textstyle['text-anchor']='middle'
    textzentriert = Style(textstyle)
    textstyle['font-size']=2*self.fontsize
    texttitle = Style(textstyle)

    # Check on selected object
    if len(self.svg.selected) != 1:
      raise AbortExtension(_("Please select exact one object, a rectangle is preferred."))

    yidxarray = [int(x) for x in re.split(r'[,;: ]',self.options.yidxs) ]
    
    # get CSV data
    self.data = getCSVData(self.options.csv_file,
                           self.options.csv_encoding,
                           { 'delimiter': self.options.csv_delimiter.replace('\\t', '\t') },
                           self.options.ignorefirst,
                           self.options.xidx, yidxarray)
    
    if self.data.len() < 2:
      raise AbortExtension(_("Less than 2 pairs of values. Nothing to plot."))
    
    # sort for x-values for a proper line
    self.data.sort()
    
    self.data.calculateMinMax()

    # Search minima and maxima for x- and y-values
    if not self.options.xmin or not self.options.xmax:
      (xmin, xmax) = self.data.getXMinMax()
    self.xmin = self.options.xmin if self.options.xmin else xmin
    self.xmax = self.options.xmax if self.options.xmax else xmax
    if self.xmin >= self.xmax:
      raise AbortExtension(_('xmin > xmax'))
    
    if not self.options.ymin or not self.options.ymax:
      (ymin, ymax) = self.data.getYMinMax()
    self.ymin = self.options.ymin if self.options.ymin else ymin
    self.ymax = self.options.ymax if self.options.ymax else ymax
    if self.ymin >= self.ymax:
      raise AbortExtension(_('ymin > ymax'))
    
    # Get the parent of the node
    (nodeid,node) = self.svg.selected.popitem()
    self.bb = node.bounding_box()
    parent = node.getparent()
    group = Group()
    parent.add(group)

    # get axis and path
    xAchse = Axis(Vector2d(self.bb.left,self.bb.bottom),Vector2d(self.bb.right,self.bb.bottom),self.xmin,self.xmax)
    yAchse = Axis(Vector2d(self.bb.left,self.bb.bottom),Vector2d(self.bb.left ,self.bb.top)   ,self.ymin,self.ymax)
    
    plot = []
    for i in range(len(yidxarray)):
      plot.append( self.plotPath(pathstyle,i) )

    # evaluate options and add all together
    if self.options.xgrid:
      group.add(xAchse.getTicks(   self.options.xtickn,                         0, -self.bb.height, gridstyle))
      group.add(xAchse.getSubTicks(self.options.xtickn, self.options.xsubtickn, 0, -self.bb.height, subgridstyle))
    if self.options.ygrid:
      group.add(yAchse.getTicks(   self.options.ytickn,                         0, self.bb.width, gridstyle))
      group.add(yAchse.getSubTicks(self.options.ytickn, self.options.ysubtickn, 0, self.bb.width, subgridstyle))
    if self.options.xtickn > 0:
      tlvon = -self.ticksize if self.options.xticksin  else 0
      tlbis =  self.ticksize if self.options.xticksout else 0
      group.add(xAchse.getTicks(   self.options.xtickn,                            tlvon,    tlbis, tickstyle))
      group.add(xAchse.getSubTicks(self.options.xtickn, self.options.xsubtickn, .5*tlvon, .5*tlbis, subtickstyle))
      group.add(xAchse.getNumbers( self.options.xtickn, self.options.xformat, 3*self.ticksize, 0, textzentriert))
    if self.options.ytickn > 0:
      tlvon = -self.ticksize if self.options.yticksout else 0
      tlbis =  self.ticksize if self.options.yticksin  else 0
      group.add(yAchse.getTicks(   self.options.ytickn,                            tlvon,    tlbis, tickstyle))
      group.add(yAchse.getSubTicks(self.options.ytickn, self.options.ysubtickn, .5*tlvon, .5*tlbis, subtickstyle))
      group.add(yAchse.getNumbers( self.options.ytickn, self.options.yformat, -2*self.ticksize, -.3*self.fontsize, textrechtsbdg))
    
    for i in range(len(yidxarray)):
      group.add(plot[i])

    if self.options.border_left:
      group.add( self.createBorderLine('left', borderstyle) )
    if self.options.border_bottom:
      group.add( self.createBorderLine('bottom', borderstyle) )
    if self.options.border_right:
      group.add( self.createBorderLine('right', borderstyle) )
    if self.options.border_top:
      group.add( self.createBorderLine('top', borderstyle) )
    if self.options.label_title:
      group.add( textAt(self.bb.center.x,self.bb.minimum.y-self.fontsize,self.options.label_title, texttitle) )
    if self.options.label_yaxis:
      group.add( textAt(self.bb.minimum.x-4*self.fontsize,self.bb.center.y,self.options.label_yaxis, textzentriert,-90) )
    if self.options.label_xaxis:
      group.add( textAt(self.bb.center.x,self.bb.maximum.y+3.5*self.fontsize,self.options.label_xaxis, textzentriert) )

    if self.options.storedata:
      group.set('data-values',str(self.data))
    
    if self.options.remove:
      parent.remove(node)
    
      
if __name__ == '__main__':
  e = XY_Data_Plot()
  e.run()
