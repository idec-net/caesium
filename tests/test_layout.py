from core.layout import GridLayout, CC, parse_constraint
from core.ui import Widget


def test_simple():
    layout = GridLayout()
    layout.add(w1 := Widget(), CC(hMin=3, hPref=3,
                                  wMin=10, wPref=20,
                                  hAlign='center', vAlign='center',
                                  pad="1 1 1 1"))
    layout.add(w2 := Widget(), CC(hMin=5, hPref=5,
                                  wMin=10, wPref=20,
                                  hAlign='left', vAlign='bottom',
                                  wrap=True))
    #
    layout.pack(width=100)
    assert (w1.y, w1.x, w1.w, w1.h) == (2, 16, 18, 1)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 50, 20, 5)
    #
    layout.pack(width=30)
    assert (w1.y, w1.x, w1.w, w1.h) == (2, 1, 13, 1)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 15, 15, 5)
    #
    layout.pack(offset_y=6, offset_x=5, width=100)
    assert (w1.y, w1.x, w1.w, w1.h) == (8, 21, 18, 1)
    assert (w2.y, w2.x, w2.w, w2.h) == (6, 55, 20, 5)


def test_shrink():
    layout = GridLayout()
    layout.add(w1 := Widget(), CC(hMin=3, hPref=9, wMin=9, wPref=20))
    layout.add(w2 := Widget(), CC(hMin=5, hPref=10, wMin=10, wPref=20))
    #
    layout.pack(height=6, width=21)
    assert (w1.y, w1.x, w1.w, w1.h) == (0, 0, 11, 6)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 11, 10, 6)


def test_grow():
    layout = GridLayout()
    layout.add(w1 := Widget(), CC(hPref=10, wPref=20))
    layout.add(w2 := Widget(), CC(hPref=10, wPref=20,
                                  fill=True, growX=True, wrap=True))
    layout.add(w3 := Widget(), CC(colSpan=2, fill=True, growY=True, wrap=True))
    #
    layout.pack(height=40, width=50)
    assert (w1.y, w1.x, w1.w, w1.h) == (0, 0, 20, 10)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 20, 30, 10)
    assert (w3.y, w3.x, w3.w, w3.h) == (10, 0, 50, 30)


def test_grow_spanned():
    layout = GridLayout()
    layout.add(w1 := Widget(), CC(w="100%", colSpan=2, fillX=True, wrap=True))
    layout.add(w2 := Widget(), CC(w="50%"))
    layout.add(w3 := Widget(), CC(width=5))
    #
    layout.pack(width=50)
    assert (w1.y, w1.x, w1.w, w1.h) == (0, 0, 50, 0)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 0, 25, 0)
    assert (w3.y, w3.x, w3.w, w3.h) == (0, 25, 5, 0)


def test_colspan():
    layout = GridLayout()
    # +---------+----+
    # |      w1 | w2 |
    # +----+----+----+
    # | w3 | w4 | w5 |
    # +----+----+----+
    layout.add(w1 := Widget(), CC(wMin=10, wPref=30, hAlign='right', colSpan=2))
    layout.add(w2 := Widget(), CC(wMin=10, wPref=20, wrap=True))
    #
    layout.add(w3 := Widget(), CC(wMin=10, wPref=20))
    layout.add(w4 := Widget(), CC(wMin=10, wPref=20))
    layout.add(w5 := Widget(), CC(wMin=10, wPref=20))
    #
    layout.pack(width=60)
    assert (w1.y, w1.x, w1.w, w1.h) == (0, 10, 30, 0)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 40, 20, 0)
    #
    layout.pack(offset_x=5, width=60)
    assert (w1.y, w1.x, w1.w, w1.h) == (0, 15, 30, 0)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 45, 20, 0)


def test_rowspan():
    layout = GridLayout()
    # +----+----+
    # |    | w2 |
    # |    +----+
    # | w1 | w3 |
    # +----+----+
    # | w4 | w5 |
    # +----+----+
    layout.add(w1 := Widget(), CC(hMin=10, hPref=30, vAlign='bottom', rowSpan=2))
    layout.add(w2 := Widget(), CC(hMin=10, hPref=20, wrap=True))
    #
    layout.add(w3 := Widget(), CC(hMin=10, hPref=20, wrap=True))
    #
    layout.add(w4 := Widget(), CC(hMin=10, hPref=20))
    layout.add(w5 := Widget(), CC(hMin=10, hPref=20))
    #
    layout.pack(height=60)
    assert (w1.y, w1.x, w1.w, w1.h) == (10, 0, 0, 30)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 0, 0, 20)
    assert (w3.y, w3.x, w3.w, w3.h) == (20, 0, 0, 20)
    assert (w4.y, w4.x, w4.w, w4.h) == (40, 0, 0, 20)
    #
    layout.pack(offset_y=5, height=60)
    assert (w1.y, w1.x, w1.w, w1.h) == (15, 0, 0, 30)
    assert (w2.y, w2.x, w2.w, w2.h) == (5, 0, 0, 20)
    assert (w3.y, w3.x, w3.w, w3.h) == (25, 0, 0, 20)
    assert (w4.y, w4.x, w4.w, w4.h) == (45, 0, 0, 20)


def test_percent():
    layout = GridLayout()
    #
    layout.add(w1 := Widget(), CC(wMin="10%", wPref=30, h="50%"))
    layout.add(w2 := Widget(), CC(w="50%", wrap=True))
    layout.add(w3 := Widget(), CC(hMin=5, fillX=True, fillY=True, colSpan=2))
    #
    layout.pack(width=30, height=40)
    assert (w1.y, w1.x, w1.w, w1.h) == (0, 0, 15, 20)
    assert (w2.y, w2.x, w2.w, w2.h) == (0, 15, 15, 0)
    assert (w3.y, w3.x, w3.w, w3.h) == (20, 0, 30, 20)


def test_complex():
    layout = GridLayout(
        (w1 := Widget(), CC(w="100%", pad="1 0", fillX=True, wrap=True)),
        (w2 := Widget(), CC(w="50%", pad="1 0", width="50%", wrap=True)),
        (w3 := Widget(), CC(w="100%", pad="1 0", width=10, wrap=True)),
        (w4 := Widget(), CC(w="100%", pad="1 0", wrap=True)),
        (w5 := Widget(), CC(w="100%", pad="1 0", wrap=True)),
        (w6 := Widget(), CC(w="100%", pad="1 0", wrap=True)),
        (w7 := Widget(), CC(w="100%", pad="1 0", wrap=True)),

        (GridLayout((w8 := Widget(), CC(w=10)),
                    (w9 := Widget(), CC(fillX=True))),
         CC(w="100%", h=1, pad="1 0", fillX=True, wrap=True)),

        (GridLayout((w10 := Widget(), CC(w=8)),
                    (w11 := Widget(), CC(wPref=10, hAlign='left'))),
         CC(w="100%", h=1, pad="1 0", fillX=True, wrap=True)),

        (w12 := Widget(), CC(w="100%", pad="1 0", fillX=True, wrap=True)),
    )
    layout.pack(offset_x=1, offset_y=1, width=78, height=10)
    assert (w1.y, w1.x, w1.w, w1.h) == (1, 2, 76, 0)
    assert (w2.y, w2.x, w2.w, w2.h) == (2, 2, 18, 0)  # - padding???
    assert (w3.y, w3.x, w3.w, w3.h) == (3, 2, 8, 0)  # - padding???
    assert (w4.y, w4.x, w4.w, w4.h) == (4, 2, 76, 0)
    assert (w5.y, w5.x, w5.w, w5.h) == (5, 2, 76, 0)
    assert (w6.y, w6.x, w6.w, w6.h) == (6, 2, 76, 0)
    assert (w7.y, w7.x, w7.w, w7.h) == (7, 2, 76, 0)

    assert (w8.y, w8.x, w8.w, w8.h) == (8, 2, 10, 0)
    assert (w9.y, w9.x, w9.w, w9.h) == (8, 12, 66, 0)

    assert (w10.y, w10.x, w10.w, w10.h) == (9, 2, 8, 0)
    assert (w11.y, w11.x, w11.w, w11.h) == (9, 10, 10, 0)

    assert (w12.y, w12.x, w12.w, w12.h) == (10, 2, 76, 0)


def test_parse_constraint():
    assert CC(w="50%") == parse_constraint("w 50%")

    assert (CC(w="100%", h=1, fillX=True, colSpan=2, wrap=True)
            == parse_constraint("w 100% h 1 fillX colSpan 2 wrap"))

    assert (CC(wMin=1, wMax=2, wPref="3%",
               hMin=2, hMax=3, hPref="4%",
               width="30%", height=25,
               rowSpan=2, colSpan=3, wrap=True,
               fill=True, fillX=True, fillY=True,
               grow=True, growX=True, growY=True)
            == parse_constraint("w 1 2 3% h 2 3 4% rowSpan 2 colSpan 3 wrap"
                                " width 30% height 25"
                                " fillX fillY fill"
                                " grow growX growY"))
