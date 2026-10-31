"""Headless contract smoke tests; do not need a GPU, webcam or Pygame installed.

A minimal Pygame display double catches accidental use of unavailable drawing
APIs, invalid UI locations, and failures in the new arcade screens.
"""
import importlib
import sys
from types import SimpleNamespace

class FakeRect:
    def __init__(self,*args):
        if len(args)==1:
            a=args[0]
            args=(a.x,a.y,a.width,a.height) if isinstance(a,FakeRect) else tuple(a)
        self.x,self.y,self.width,self.height=map(int,args)
    @property
    def w(self):return self.width
    @property
    def h(self):return self.height
    @property
    def right(self):return self.x+self.width
    @property
    def centerx(self):return self.x+self.width//2
    @property
    def centery(self):return self.y+self.height//2
    @property
    def center(self):return self.centerx,self.centery
    def move(self,x,y):return FakeRect(self.x+x,self.y+y,self.width,self.height)
    def collidepoint(self,x,y=None):
        if y is None:x,y=x
        return self.x<=x<self.right and self.y<=y<self.y+self.height

class FakeRendered:
    def __init__(self,value):self.value=str(value)
    def get_width(self):return len(self.value)*10
    def get_height(self):return 24

class FakeSurface:
    def __init__(self,*_args,**_kwargs):pass
    def blit(self,*_args,**_kwargs):pass
    def fill(self,*_args,**_kwargs):pass

class FakeFont:
    def __init__(self,*_args,**_kwargs):pass
    def render(self,value,*_args):return FakeRendered(value)

def fake_pygame():
    kwargs={key:42+i for i,key in enumerate(['K_q','K_w','K_e','K_1','K_2','K_3','K_4','K_LEFT','K_RIGHT'])}
    draw=SimpleNamespace(rect=lambda *a,**k:None,line=lambda *a,**k:None,
                         circle=lambda *a,**k:None,polygon=lambda *a,**k:None)
    return SimpleNamespace(Rect=FakeRect,Surface=FakeSurface,SRCALPHA=1,draw=draw,
                           font=SimpleNamespace(SysFont=lambda *_args,**_kwargs:FakeFont()),**kwargs)


def test_all_new_screens_render_and_have_links(tmp_path,monkeypatch):
    monkeypatch.setitem(sys.modules,'pygame',fake_pygame())
    sys.modules.pop('arcade_expansion',None)
    new=importlib.import_module('arcade_expansion')
    settings=new.PlayerPreferences(tmp_path/'settings.json')
    shell=new.ArcadeShell(settings)
    scores=new.ArcadeScores(tmp_path/'scores.json')
    game_types=[new.BlockNova,new.ReflexArena,new.MemoryCircuit,new.StarPilot]
    games={game.name:game(scores) for game in game_types}
    surf=FakeSurface()
    for state in ['MENU','ARCADE','SETTINGS','HELP']:
        shell.draw(surf,state)
        assert shell.buttons
    for game in games.values():
        game.draw(surf)
        game.tick(.15)
        game.draw(surf)
        game.finish()
        game.draw(surf)


def test_settings_are_saved_and_buttons_change_value(tmp_path,monkeypatch):
    monkeypatch.setitem(sys.modules,'pygame',fake_pygame())
    new=importlib.import_module('arcade_expansion')
    settings=new.PlayerPreferences(tmp_path/'settings.json')
    shell=new.ArcadeShell(settings)
    shell.draw(FakeSurface(),'SETTINGS')
    original=settings.data['input_mode']
    shell.change('input_mode',1)
    assert settings.data['input_mode'] != original
    assert new.PlayerPreferences(tmp_path/'settings.json').data['input_mode']==settings.data['input_mode']
    assert shell.interact(1040,241)[0]=='adjust'
