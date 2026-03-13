import re
from dataclasses import dataclass, field
from itertools import takewhile
from typing import TYPE_CHECKING, Tuple, List, Optional, Collection, Union

if TYPE_CHECKING:
    from ui import Widget


@dataclass(slots=True, frozen=True)
class Pad:
    left: int = None
    top: int = None
    right: int = None
    bottom: int = None

    def horizontal(self):
        return (self.left or 0) + (self.right or 0)

    def vertical(self):
        return (self.top or 0) + (self.bottom or 0)


PAD_EMPTY = Pad(0, 0, 0, 0)


def _parse_padding(pad: Union[Pad, str, int]):
    if isinstance(pad, int):
        return Pad(pad, pad, pad, pad)
    elif isinstance(pad, str):
        pads = list(map(int, filter(None, map(str.strip, pad.split(" ")))))
        count = len(pads)
        if count == 0:
            return PAD_EMPTY
        elif count == 1:
            return Pad(pads[0], pads[0], pads[0], pads[0])
        elif count == 2:
            return Pad(left=pads[0], top=pads[1], right=pads[0], bottom=pads[1])
        elif count == 4:
            return Pad(left=pads[0], top=pads[1], right=pads[2], bottom=pads[3])
        else:
            raise ValueError("Padding must contain 1, 2 or 4 ints :: " + pad)
    return pad


unit_template = re.compile(r"^[0-9]+%?$")


@dataclass(slots=True)
class Unit:
    src: Optional[Union[int, str]] = None
    val: int = None

    def __int__(self):
        return self.val


def _parse_percent_unit(val: Union[str, int], total: int = 0):
    if isinstance(val, str):
        if val.endswith("%"):
            return Unit(src=val, val=int(round(total / 100 * int(val[:-1]))))
        return Unit(src=val, val=int(val))
    if isinstance(val, Unit):
        if isinstance(val.src, str):
            if val.src.endswith("%"):
                val.val = int(round(total / 100 * int(val.src[:-1])))
    return val


@dataclass(slots=True)
class CC:
    """Component Constraint"""
    # Cell constraints
    w: Union[str, int] = None
    wMin: Union[str, int] = None
    wMax: Union[str, int] = None
    wPref: Union[str, int] = None

    h: Union[str, int] = None
    hMin: Union[str, int] = None
    hMax: Union[str, int] = None
    hPref: Union[str, int] = None

    rowSpan: int = None
    colSpan: int = None

    wrap: bool = None
    pad: Union[Pad, str] = PAD_EMPTY

    # Widget constraints
    width: Union[str, int] = None
    height: Union[str, int] = None
    fill: bool = None
    fillX: bool = None
    fillY: bool = None
    hAlign: str = None
    vAlign: str = None

    # Row/Column constraint
    grow: bool = None
    growX: bool = None
    growY: bool = None

    # noinspection DuplicatedCode
    def parse_percent_units(self, width, height):
        if isinstance(self.pad, str):
            self.pad = _parse_padding(self.pad)
        #
        self.w = _parse_percent_unit(self.w, width)
        if self.w:
            self.wMin = self.w
            self.wMax = self.w
            self.wPref = self.w
        else:
            self.wMin = _parse_percent_unit(self.wMin, width)
            self.wMax = _parse_percent_unit(self.wMax, width)
            self.wPref = _parse_percent_unit(self.wPref, width)
        #
        self.h = _parse_percent_unit(self.h, height)
        if self.h:
            self.hMin = self.h
            self.hMax = self.h
            self.hPref = self.h
        else:
            self.hMin = _parse_percent_unit(self.hMin, height)
            self.hMax = _parse_percent_unit(self.hMax, height)
            self.hPref = _parse_percent_unit(self.hPref, height)
        #
        self.width = _parse_percent_unit(self.width, width)
        self.height = _parse_percent_unit(self.height, height)


def parse_constraint(scc):
    cc = CC()
    params = list(filter(None, map(lambda s: s.strip(), scc.split(' '))))
    for i, p in enumerate(params):
        if p == 'w':
            width = list(takewhile(unit_template.match, params[i + 1:]))
            i += len(width)
            if len(width) == 1:
                cc.w = int(width[0]) if str.isdigit(width[0]) else width[0]
            elif len(width) == 3:
                cc.wMin = int(width[0]) if str.isdigit(width[0]) else width[0]
                cc.wMax = int(width[1]) if str.isdigit(width[1]) else width[1]
                cc.wPref = int(width[2]) if str.isdigit(width[2]) else width[2]
            else:
                raise ValueError('Cell width must be 1 or 3 ints (min, max, pref)')
        elif p == 'wMin':
            i += 1
            cc.wMin = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'wMax':
            i += 1
            cc.wMax = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'wPref':
            i += 1
            cc.wPref = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'h':
            height = list(takewhile(unit_template.match, params[i + 1:]))
            i += len(height)
            if len(height) == 1:
                cc.h = int(height[0]) if str.isdigit(height[0]) else height[0]
            elif len(height) == 3:
                cc.hMin = int(height[0]) if str.isdigit(height[0]) else height[0]
                cc.hMax = int(height[1]) if str.isdigit(height[1]) else height[1]
                cc.hPref = int(height[2]) if str.isdigit(height[2]) else height[2]
            else:
                raise ValueError('Cell height must be 1 or 3 ints (min, max, pref)')
        elif p == 'hMin':
            i += 1
            cc.hMin = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'hMax':
            i += 1
            cc.hMax = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'hPref':
            i += 1
            cc.hPref = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'rowSpan':
            i += 1
            cc.rowSpan = int(params[i])
        elif p == 'colSpan':
            i += 1
            cc.colSpan = int(params[i])
        elif p == 'wrap':
            cc.wrap = True
        elif p == 'pad':
            paddings = list(takewhile(str.isdigit, params[i + 1:]))
            i += len(paddings)
            cc.pad = _parse_padding(' '.join(paddings))
        #
        elif p == 'width':
            i += 1
            cc.width = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'height':
            i += 1
            cc.height = int(params[i]) if str.isdigit(params[i]) else params[i]
        elif p == 'fill':
            cc.fill = True
        elif p == 'fillX':
            cc.fillX = True
        elif p == 'fillY':
            cc.fillY = True
        elif p == 'hAlign':
            i += 1
            cc.hAlign = params[i]
            if cc.hAlign not in ('left', 'center', 'right'):
                raise ValueError('hAlign must be one of left/center/right')
        elif p == 'vAlign':
            i += 1
            cc.vAlign = params[i]
            if cc.vAlign not in ('top', 'center', 'bottom'):
                raise ValueError('vAlign must be one of top/center/bottom')
        #
        elif p == 'grow':
            cc.grow = True
        elif p == 'growX':
            cc.growX = True
        elif p == 'growY':
            cc.growY = True
    return cc


def _clamp(min_, max_, pref, default):
    return max((int(min_ or 0), int(pref or 0))) or min((int(max_ or default), default))


@dataclass
class _Cell:
    row: int
    col: int
    wid: Union['Widget', 'Layout']
    cc: CC
    width: int = 0
    height: int = 0
    span: '_Cell' = None  # for col/row spanned cell, main span cell
    cSpan: int = None  # col spanned cell index (reversed)
    rSpan: int = None  # row spanned cell index (reversed)

    def calc(self):
        w = (self.wid.w if self.wid else 0)
        self.width = _clamp(self.cc.wMin, self.cc.wMax, self.cc.wPref, w)
        h = (self.wid.h if self.wid else 0)
        self.height = _clamp(self.cc.hMin, self.cc.hMax, self.cc.hPref, h)

    def is_r_spanned(self):
        return self.cc.rowSpan and self.cc.rowSpan > 1

    def is_c_spanned(self):
        return self.cc.colSpan and self.cc.colSpan > 1


@dataclass
class _DimContainer:  # Row/Column Dimension Container
    cells: List[Optional[_Cell]] = field(default_factory=list)
    sz: int = 0
    minSz: int = 0
    maxSz: int = 0
    grow: bool = None


def _adjust_size(diff: int, items: Collection[_DimContainer]):
    if not items:
        return diff
    while diff != 0:
        prevDiff = diff
        if diff > 0:
            itDiff = max(1, diff // len(items))  # TODO: Skip min/max sized items
        else:
            itDiff = min(-1, diff // len(items))
        for it in items:
            it.sz += itDiff
            diff -= itDiff
            if it.maxSz and it.sz > it.maxSz:
                diff += it.sz - it.maxSz
                it.sz = it.maxSz
            elif it.minSz and it.sz < it.minSz:
                diff += it.sz - it.minSz
                it.sz = it.minSz
            if diff == 0:
                break  # no more shrink/grow
        if prevDiff == diff:
            break  # no shrink/grow preferred width, min/max width exceeded
    return diff


def _adjust_size_spanned(items: List[_DimContainer], itN, spanCells, col=True):
    maxGrow = 0
    for c in spanCells:
        spanItem = items[itN:itN + (c.cc.colSpan if col else c.cc.rowSpan)]
        spanWidth = sum(map(lambda _: _.sz, spanItem))
        if spanWidth < c.width:
            spanGrow = c.width - spanWidth
            if spanGrow > maxGrow:
                maxGrow = spanGrow
                maxGrow -= _adjust_size(spanGrow, spanItem)
            else:
                _adjust_size(spanGrow, spanItem)
    return maxGrow


class Layout:
    h: int = 0
    w: int = 0

    def add(self, wid, constraint=None):
        ...

    def pack(self, offset_y=0, offset_x=0, height=0, width=0):
        ...


class GridLayout(Layout):
    def __init__(self, *widgets: Tuple[Union['Widget', Layout],
                                       Optional[Union[CC, str]]]):
        self.rows = []  # type: List[_DimContainer]
        self.cols = []  # type: List[_DimContainer]
        self.widgets = []
        for wid, cc in widgets:
            self.add(wid, cc)

    def add(self, wid: Union['Widget', Layout],
            constraint: Optional[Union[CC, str]] = None):
        if constraint is None:
            constraint = CC()
        elif isinstance(constraint, str):
            constraint = parse_constraint(constraint)
        self.widgets.append((wid, constraint))

    def _init_grid(self):
        self.rows.clear()
        self.cols.clear()
        curRow = []
        rows = []
        for i, (wid, cc) in enumerate(self.widgets):
            curRow.append((wid, cc))
            if cc.wrap:
                rows.append(curRow)
                curRow = []
        if curRow:
            rows.append(curRow)
        # noinspection PyShadowingNames
        cols_count = max(map(lambda r: sum(map(lambda t: t[1].colSpan or 1, r)),
                             rows))
        rows_count = len(rows)
        for _ in range(rows_count):
            self.rows.append(_DimContainer(cells=[None] * cols_count))
        for _ in range(cols_count):
            self.cols.append(_DimContainer(cells=[None] * rows_count))

        for r, row in enumerate(rows):
            colN = 0
            for (wid, cc) in row:
                span_cell = None
                rSpan_offset = 0
                while self._get_cell(r, colN):
                    colN += 1  # skip prefilled row spanned cells
                #
                for rs in range(cc.rowSpan or 1, 0, -1):
                    cSpan_offset = 0
                    for cs in range(cc.colSpan or 1, 0, -1):
                        cell = _Cell(row=r + rSpan_offset,
                                     col=colN + cSpan_offset,
                                     wid=wid, cc=cc,
                                     span=span_cell, cSpan=cs, rSpan=rs)
                        self._put_cell(cell)
                        if not span_cell:
                            span_cell = cell
                        cSpan_offset += 1
                    rSpan_offset += 1
                colN += 1

    def pack(self, offset_y=0, offset_x=0, height=0, width=0):
        self.h = height
        self.w = width
        if not self.rows:
            self._init_grid()
        #
        for wid, cc in self.widgets:
            cc.parse_percent_units(width=width, height=height)
            if not cc.width and wid and wid.w:
                cc.width = wid.w + cc.pad.horizontal()
            if not cc.height and wid and wid.h:
                cc.height = wid.h + cc.pad.vertical()

        for col in self.cols:
            for cell in filter(None, col.cells):
                cell.calc()
        #
        growX = width
        for col in self.cols:
            no_span = list(filter(lambda _: _ and not _.is_c_spanned(), col.cells))
            if no_span:
                col.sz = max(map(lambda _: _.width, no_span))
                col.minSz = max(map(lambda _: int(_.cc.wMin or 0), no_span))
                col.maxSz = max(map(lambda _: int(_.cc.wMax or 0), no_span))
                col.grow = any(map(lambda _: _.cc.grow or _.cc.growX, no_span))
            growX -= col.sz or 0
        for cn, col in enumerate(self.cols):
            spCells = list(filter(lambda _: _ and _.is_c_spanned() and not _.span,
                                  col.cells))
            growX -= _adjust_size_spanned(self.cols, cn, spCells, col=True)
        if width > 0:
            _adjust_size(growX, list(filter(lambda _: _.grow, self.cols)) or self.cols)
        #
        growY = height
        for row in self.rows:
            no_span = list(filter(lambda _: _ and not _.is_r_spanned(), row.cells))
            if no_span:
                row.sz = max(map(lambda _: _.height, no_span))
                row.minSz = max(map(lambda _: int(_.cc.hMin or 0), no_span))
                row.maxSz = max(map(lambda _: int(_.cc.hMax or 0), no_span))
                row.grow = any(map(lambda _: _.cc.grow or _.cc.growY, no_span))
            growY -= row.sz or 0
        for rn, row in enumerate(self.rows):
            spCells = list(filter(lambda _: _ and _.is_r_spanned() and not _.span,
                                  row.cells))
            growY -= _adjust_size_spanned(self.rows, rn, spCells, col=False)
        if height > 0:
            _adjust_size(growY, list(filter(lambda _: _.grow, self.rows)) or self.rows)

        x = offset_x
        for cn, col in enumerate(self.cols):
            y = offset_y
            for rn, cell in enumerate(col.cells):
                if not cell:
                    y += self.rows[rn].sz
                    continue  # skip empty cells
                if cell.span:
                    if not cell.span.is_r_spanned():
                        y += self.rows[rn].sz
                    continue  # skip any spanned tails
                #
                ww = col.sz
                if cell.cc.colSpan and cell.cc.colSpan > 1:
                    spanned = self.cols[cell.col + 1:cell.col + cell.cc.colSpan]
                    ww += sum(map(lambda _: _.sz, spanned))
                #
                if cell.cc.width:
                    cell.width = int(_parse_percent_unit(cell.cc.width, cell.width))
                if cell.width > ww or cell.cc.fill or cell.cc.fillX:
                    cell.width = ww
                wx = x
                if cell.cc.hAlign == 'right':
                    wx += ww - cell.width
                elif cell.cc.hAlign == 'center':
                    wx += (ww - cell.width) // 2
                #
                row = self.rows[cell.row]
                wh = row.sz
                if cell.cc.rowSpan and cell.cc.rowSpan > 1:
                    spanned = self.rows[cell.row + 1:cell.row + cell.cc.rowSpan]
                    wh += sum(map(lambda _: _.sz, spanned))
                #
                if cell.cc.height:
                    cell.height = int(_parse_percent_unit(cell.cc.height, cell.height))
                if cell.height > wh or cell.cc.fill or cell.cc.fillY:
                    cell.height = wh
                wy = y
                if cell.cc.vAlign == 'bottom':
                    wy += wh - cell.height
                elif cell.cc.vAlign == 'center':
                    wy += (wh - cell.height) // 2
                #
                if isinstance(cell.wid, Layout):
                    cell.wid.pack(offset_y=wy + (cell.cc.pad.top or 0),
                                  offset_x=wx + (cell.cc.pad.left or 0),
                                  width=cell.width - cell.cc.pad.horizontal(),
                                  height=cell.height - cell.cc.pad.vertical())
                elif cell.wid:
                    cell.wid.y = wy + (cell.cc.pad.top or 0)
                    cell.wid.x = wx + (cell.cc.pad.left or 0)
                    cell.wid.w = cell.width - cell.cc.pad.horizontal()
                    cell.wid.h = cell.height - cell.cc.pad.vertical()
                #
                y += wh
            x += col.sz

    def _get_cell(self, row, col):
        if 0 <= row < len(self.rows):
            r = self.rows[row]
            if 0 <= col < len(r.cells):
                return r.cells[col]  #
        return None

    def _put_cell(self, cell: _Cell):
        self.rows[cell.row].cells[cell.col] = cell
        self.cols[cell.col].cells[cell.row] = cell
