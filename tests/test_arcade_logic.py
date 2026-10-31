from arcade_logic import BlockBoard, SimonEngine, GestureLatch, PointDebouncer

def test_block_can_place_and_overlap():
    b=BlockBoard(size=8, tray=[((0,0),(1,0)), None, None])
    assert b.can_place(b.tray[0],0,0)
    assert not b.can_place(b.tray[0],7,0)
    assert b.place(0,0,0)['points']==20
    assert b.grid[0][0] and b.grid[0][1]
    assert b.place(1,0,0) is None

def test_line_clear_and_combo():
    b=BlockBoard(size=8, tray=[((0,0),),((0,0),),((0,0),)])
    b.grid[2]=[1]*7+[0]
    result=b.place(0,7,2)
    assert result['lines']==1
    assert result['combo']==1
    assert all(v==0 for v in b.grid[2])
    assert b.score>=250

def test_game_over_detected():
    b=BlockBoard(size=8, tray=[((0,0),(1,0)),None,None])
    b.grid=[[1]*8 for _ in range(8)]
    assert not b.can_play_any()
    b.game_over=not b.can_play_any()
    assert b.place(0,0,0) is None

def test_simon_success_and_failure():
    s=SimonEngine(); s.reset()
    s.update(5.0)
    assert s.phase=='input'
    target=s.sequence[0]
    assert s.press(target)=='level'
    assert s.level==2
    s.update(5.0)
    assert s.press((s.sequence[0]+1)%4)=='wrong'
    assert s.lives==2

def test_gesture_stable_and_hysteresis():
    g=GestureLatch()
    assert not g.update(.20)
    assert g.update(.20)
    assert g.update(.39) # stay engaged inside deadband
    assert g.update(.60) # intermediate transition
    assert not g.update(.60)

def test_debounce_repeats_only_after_release():
    d=PointDebouncer(cooldown=.1)
    assert d.edge(True,1.0)
    assert not d.edge(True,1.2)
    assert not d.edge(False,1.3)
    assert d.edge(True,1.4)
