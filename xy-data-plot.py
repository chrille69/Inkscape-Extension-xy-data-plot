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

from inkex import TextElement, Effect, Line, PathElement, Style
from inkex import Group, Rectangle, Boolean as Bool, errormsg, AbortExtension
import csv
import math

def getCSVData(csvfile,fileencoding,csvoptions,ignorefirst,xidx,yidx):
  data = []
  with open(csvfile, newline='', encoding=fileencoding ) as f:
    reader = csv.reader(f,**csvoptions)
    try:
      for row in reader:
        if reader.line_num <= ignorefirst:
            continue
        try:
          data.append( { 'x': float(row[xidx]), 'y': float(row[yidx]) } )
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

def getMinMax( data, axis='x', round=True ):
  values = data[0]
  min = values[axis]
  max = values[axis]
  for values in data[1:]:
    if values[axis] < min: min = values[axis]
    if values[axis] > max: max = values[axis]
  if round:
    max = ceil(max)
    min = floor(min, decimals = 1 if max == 0 else int( math.log10(abs(max)) ) )
  return (min, max)

  
class XY_Data_Plot(Effect):
  def __init__(self):
    Effect.__init__(self)

    self.arg_parser.add_argument("--tab")
    self.arg_parser.add_argument("--csv_file",        dest="csv_file",      action="store", type=str,  default="")
    self.arg_parser.add_argument("--csv_encoding",    dest="csv_encoding",  action="store", type=str,  default="utf-8")
    self.arg_parser.add_argument("--csv_delimiter",   dest="csv_delimiter", action="store", type=str,  default=";")
    self.arg_parser.add_argument("--csv_columnx",     dest="xidx",          action="store", type=int,  default=0)
    self.arg_parser.add_argument("--csv_columny",     dest="yidx",          action="store", type=int,  default=1)
    self.arg_parser.add_argument("--csv_ignorefirst", dest="ignorefirst",   action="store", type=int,  default=0)
    
    self.arg_parser.add_argument("--xaxis_format"   ,  dest="xformat"   , action="store", type=str,   default="2.2f")
    self.arg_parser.add_argument("--xaxis_min"      ,  dest="xmin"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--xaxis_max"      ,  dest="xmax"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--xaxis_tick_n"   ,  dest="xtickn"    , action="store", type=int,   default=10)
    self.arg_parser.add_argument("--xaxis_subtick_n",  dest="xsubtickn" , action="store", type=int,   default=0)
    self.arg_parser.add_argument("--xaxis_ticksin"  ,  dest="xticksin"  , action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--xaxis_ticksout" ,  dest="xticksout" , action="store", type=Bool, default="false")
    self.arg_parser.add_argument("--xaxis_grid"     ,  dest="xgrid"     , action="store", type=Bool, default="false")
    
    self.arg_parser.add_argument("--yaxis_format"   ,  dest="yformat"   , action="store", type=str,   default="2.2f")
    self.arg_parser.add_argument("--yaxis_min"      ,  dest="ymin"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--yaxis_max"      ,  dest="ymax"      , action="store", type=float, default=0)
    self.arg_parser.add_argument("--yaxis_tick_n"   ,  dest="ytickn"    , action="store", type=int,   default=10)
    self.arg_parser.add_argument("--yaxis_subtick_n",  dest="ysubtickn" , action="store", type=int,   default=0)
    self.arg_parser.add_argument("--yaxis_ticksin"  ,  dest="yticksin"  , action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--yaxis_ticksout" ,  dest="yticksout" , action="store", type=Bool, default="false")
    self.arg_parser.add_argument("--yaxis_grid"     ,  dest="ygrid"     , action="store", type=Bool, default="false")

    self.arg_parser.add_argument("--border_create_new" , dest="border", action="store", type=Bool, default="true")
    self.arg_parser.add_argument("--shape_remove_old"  , dest="remove", action="store", type=Bool, default="false")

  def transformx(self,x):
    "Transforms x-data-values in screen coordinates."
    
    return (x-self.xmin)*self.bb.width/(self.xmax-self.xmin)+self.bb.left

  def transformy(self,y):
    "Transforms y-data-values in screen coordinates."
    
    return (self.ymax-y)*self.bb.height/(self.ymax-self.ymin)+self.bb.top

  def plotPath( self ):
    "Generates path-command-string and returns a path-element."
    
    pathstr = ""
    values = self.data[0]
    pathstr   +=  'M{},{}'.format( self.transformx(values['x']), self.transformy(values['y']) )
    
    for values in self.data[1:]:
      pathstr += ' L{},{}'.format( self.transformx(values['x']), self.transformy(values['y']) )
      
    newpath = PathElement(d=pathstr)
    newpath.style = self.pathstyle
    
    return newpath

  def xAxis( self ):
    "Generates x-axis und x-grid and returns group-elements."
    
    tickgroup = Group()
    textgroup = Group()
    gridgroup = Group()
    
    step = (self.xmax-self.xmin) / self.options.xtickn
    for i in range(self.options.xtickn+1):
      x = self.xmin + i * step
      line = Line(
        x1=str(self.transformx(x)),
        y1=str(self.transformy(self.ymin)-(self.ticksize if self.options.xticksin else 0)),
        x2=str(self.transformx(x)),
        y2=str(self.transformy(self.ymin)+(self.ticksize if self.options.xticksout else 0))
      )
      line.style = self.tickstyle
      tickgroup.add(line)
      
      textgroup.add(self.textAt(x,self.ymin,("{0:"+self.options.xformat+"}").format(x),'middle',0,1.5*self.fontsize))
      
      if self.options.xgrid:
        line = Line(
          x1=str(self.transformx(x)),
          y1=str(self.transformy(self.ymin)),
          x2=str(self.transformx(x)),
          y2=str(self.transformy(self.ymax))
        )
        line.style = self.gridstyle
        gridgroup.add(line)

      if self.options.xsubtickn != 0 and i < self.options.xtickn:
        for j in range(1,self.options.xsubtickn):
          xs = x + j * step / self.options.xsubtickn
          line = Line(
            x1=str(self.transformx(xs)),
            y1=str(self.transformy(self.ymin)-(self.subticksize if self.options.xticksin else 0)),
            x2=str(self.transformx(xs)),
            y2=str(self.transformy(self.ymin)+(self.subticksize if self.options.xticksout else 0))
          )
          line.style = self.subtickstyle
          tickgroup.add(line)
 
          if self.options.xgrid:
              line = Line(
                x1=str(self.transformx(xs)),
                y1=str(self.transformy(self.ymin)),
                x2=str(self.transformx(xs)),
                y2=str(self.transformy(self.ymax))
              )
              line.style = self.subgridstyle
              gridgroup.add(line)
 
    return tickgroup, textgroup, gridgroup
    
  def yAxis( self ):
    "Generates y-axis und y-grid and returns group-elements."
    
    tickgroup = Group()
    textgroup = Group()
    gridgroup = Group()
      
    step = (self.ymax-self.ymin) / self.options.ytickn
    for i in range(self.options.ytickn+1):
      y = self.ymin + i * step
      line = Line(
        x1=str(self.transformx(self.xmin)-(self.ticksize if self.options.yticksout else 0)),
        y1=str(self.transformy(y)),
        x2=str(self.transformx(self.xmin)+(self.ticksize if self.options.yticksin else 0)),
        y2=str(self.transformy(y))
      )
      line.style = self.tickstyle
      tickgroup.add(line)
      textgroup.add(self.textAt(self.xmin,y,("{0:"+self.options.yformat+"}").format(y),'end',-self.fontsize,self.fontsize/3))
      
      if self.options.ygrid:
        line = Line(
          x1=str(self.transformx(self.xmin)),
          y1=str(self.transformy(y)),
          x2=str(self.transformx(self.xmax)),
          y2=str(self.transformy(y))
        )
        line.style = self.gridstyle
        gridgroup.add(line)

      if self.options.ysubtickn != 0 and i < self.options.ytickn:
        for j in range(1,self.options.ysubtickn):
          ys = y + j * step / self.options.ysubtickn
          line = Line(
            x1=str(self.transformx(self.xmin)-(self.subticksize if self.options.yticksout else 0)),
            y1=str(self.transformy(ys)),
            x2=str(self.transformx(self.xmin)+(self.subticksize if self.options.yticksin else 0)),
            y2=str(self.transformy(ys))
          )
          line.style = self.subtickstyle
          tickgroup.add(line)
      
          if self.options.ygrid:
            line = Line(
              x1=str(self.transformx(self.xmin)),
              y1=str(self.transformy(ys)),
              x2=str(self.transformx(self.xmax)),
              y2=str(self.transformy(ys))
            )
            line.style = self.subgridstyle
            gridgroup.add(line)

    return tickgroup, textgroup, gridgroup

  def textAt(self, x, y, text, anchor, dx, dy):
    "Places a test-element at data-coordinates."
    
    elem = TextElement(x=str(self.transformx(x)+dx), y=str(self.transformy(y)+dy))
    elem.text = text
    elem.style = {
      'font-size': self.fontsize,
      'fill-opacity': '1.0',
      'stroke': 'none',
      'text-align': anchor if anchor != 'middle' else 'center',
      'text-anchor': anchor,
      'font-weight': 'normal',
      'font-style': 'normal',
      'fill': '#000'}
    return elem

  def createBorder(self):
    "Returns a rectangle of the given bounding box."
    rect = Rectangle(
      x=str(self.bb.minimum.x),
      y=str(self.bb.minimum.y),
      width=str(self.bb.width),
      height=str(self.bb.height)
    )
    rect.style = self.tickstyle
    return rect
    
  def effect(self):

    csvoptions = {
      'delimiter': self.options.csv_delimiter.replace('\\t', '\t')
    }
    
    cssstyle = {
      'stroke': '#000000',
      'stroke-width': self.svg.unittouu('1.5pt'),
      'fill': 'none',
      'stroke-linecap': 'square',
      'stroke-linejoin': 'round'
    }
    self.pathstyle = Style(cssstyle)
    cssstyle['stroke-width'] = self.svg.unittouu('1.0pt')
    self.tickstyle = Style(cssstyle)
    cssstyle['stroke-width'] = self.svg.unittouu('0.5pt')
    self.subtickstyle = Style(cssstyle)
    cssstyle['stroke'] = '#999'
    cssstyle['stroke-width'] = self.svg.unittouu('0.8pt')
    self.gridstyle = Style(cssstyle)
    cssstyle['stroke-width'] = self.svg.unittouu('0.4pt')
    self.subgridstyle = Style(cssstyle)
    
    self.ticksize    = self.svg.unittouu("8px")
    self.subticksize = self.svg.unittouu("4px")
    self.fontsize    = self.svg.unittouu("10pt")

    if len(self.svg.selected) != 1:
      raise AbortExtension(_("Please select exact one object, a rectangle is preferred."))
    
    self.data = getCSVData(self.options.csv_file,
                           self.options.csv_encoding,
                           csvoptions,
                           self.options.ignorefirst,
                           self.options.xidx, self.options.yidx)
    
    if len(self.data) < 2:
      raise AbortExtension(_("Less than 2 pair of values. Nothing to plot."))
    
    # Nach x-Werten sortieren
    self.data.sort(key=lambda tup: tup['x'])
    
    if not self.options.xmin or not self.options.xmax:
      (xmin, xmax) = getMinMax(self.data, 'x')
    self.xmin = self.options.xmin if self.options.xmin else xmin
    self.xmax = self.options.xmax if self.options.xmax else xmax
    if self.xmin >= self.xmax:
      raise AbortExtension(_('xmin > xmax'))
    
    if not self.options.ymin or not self.options.ymax:
      (ymin, ymax) = getMinMax(self.data, 'y')
    self.ymin = self.options.ymin if self.options.ymin else ymin
    self.ymax = self.options.ymax if self.options.ymax else ymax
    if self.ymin >= self.ymax:
      raise AbortExtension(_('ymin > ymax'))
    
    (nodeid,node) = self.svg.selected.popitem()
    self.bb = node.bounding_box()
    parent = node.getparent()
    group = Group()
    parent.add(group)
    
    border = self.createBorder()
    xticks, xtext, xgrid = self.xAxis()
    yticks, ytext, ygrid = self.yAxis()
    plot = self.plotPath()
    
    if self.options.xgrid:
      group.add(xgrid)
    if self.options.ygrid:
      group.add(ygrid)
    if self.options.xtickn > 0:
      group.add(xticks)
      group.add(xtext)
    if self.options.ytickn > 0:
      group.add(yticks)
      group.add(ytext)
    if self.options.border:
      group.add( border )
    group.add(plot)
    
    if self.options.remove:
      parent.remove(node)
    
      
if __name__ == '__main__':
  e = XY_Data_Plot()
  e.run()
