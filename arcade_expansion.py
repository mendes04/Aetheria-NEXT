"""Aetheria NEXT: added arcade modes, cinematic hub and user settings.

Designed as an additive extension to the original 5,243-line Aetheria source.
The original music modes, orchestration, LAN sync and scoreboards remain intact.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import random
import time
import pygame
from arcade_logic import BlockBoard, SimonEngine, PointDebouncer, distance

W,H = 1280,720
INK=(5,9,20); SURFACE=(15,23,41); BORDER=(51,67,99)
WHITE=(243,247,255); MUTED=(145,164,192)
CYAN=(67,230,248); VIOLET=(172,115,255); PINK=(255,83,157)
GOLD=(255,213,105); GREEN=(70,232,165); RED=(255,99,115)
PALETTE=[CYAN,VIOLET,PINK,GREEN,GOLD]


def font(sz=20, heavy=False):
    return pygame.font.SysFont('bahnschrift,arial,dejavusans',sz,bold=heavy)


def text(s, value, x,y, size=20, color=WHITE, bold=False, anchor='left'):
    face=font(size,bold); image=face.render(str(value),True,color)
    if anchor=='center': x-=image.get_width()//2
    if anchor=='right': x-=image.get_width()
    s.blit(image,(round(x),round(y)))


def panel(s,rect,fill=SURFACE,border=BORDER,radius=20):
    r=pygame.Rect(rect)
    shadow=r.move(0,9)
    pygame.draw.rect(s,(3,7,18),shadow,border_radius=radius)
    pygame.draw.rect(s,fill,r,border_radius=radius)
    pygame.draw.rect(s,border,r,1,border_radius=radius)
    pygame.draw.line(s,(62,78,111),(r.x+radius,r.y+2),(r.right-radius,r.y+2),1)


def round_button(s,rect,label,active=False,accent=CYAN,small=False):
    r=pygame.Rect(rect)
    pygame.draw.rect(s,accent if active else (29,40,63),r,border_radius=13)
    pygame.draw.rect(s,accent if active else BORDER,r,1,border_radius=13)
    text(s,label,r.centerx,r.centery-(9 if small else 11),17 if small else 20,
         INK if active else WHITE,True,anchor='center')


def bar(s,x,y,w,progress,color=CYAN):
    pygame.draw.rect(s,(37,45,70),(x,y,w,8),border_radius=4)
    pygame.draw.rect(s,color,(x,y,max(0,int(w*max(0,min(progress,1)))),8),border_radius=4)


def starfield(s, t=0, reduce_motion=False):
    s.fill(INK)
    pygame.draw.circle(s,(10,23,45),(W-100,110),360)
    pygame.draw.circle(s,(23,15,49),(80,H-80),310)
    for i in range(64):
        x=(i*191+59)%W; y=(i*137+31)%H
        pulse=0 if reduce_motion else int(math.sin(t*1.1+i)*30)
        pygame.draw.circle(s,(64+max(pulse,0),88,125),(x,y),1 if i%4 else 2)
    for j in range(11):
        y=H-60+j*22
        pygame.draw.line(s,(15,33,56),(0,y),(W,y),1)


class PlayerPreferences:
    DEFAULT={"volume":0.65,"gesture_sensitivity":1.0,"input_mode":"HYBRID", "tracking_quality":"BALANCED",
             "show_hands":True,"particles":True,"difficulty":"NORMAL",
             "session_minutes":12,"fullscreen":False,"tutorials":True}
    def __init__(self, location=None):
        self.path=Path(location or Path.home()/'.aetheria'/'settings.json')
        self.data=dict(self.DEFAULT)
        try:
            loaded=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(loaded,dict):
                for key, val in loaded.items():
                    if key in self.DEFAULT and type(val)==type(self.DEFAULT[key]):
                        self.data[key]=val
        except (OSError,ValueError): pass
        self.data['volume']=max(0.,min(1.,self.data['volume']))
        self.data['gesture_sensitivity']=max(.65,min(1.5,self.data['gesture_sensitivity']))
        if self.data['input_mode'] not in ['HYBRID','MOUSE','CAMERA']:
            self.data['input_mode']='HYBRID'
        if self.data['difficulty'] not in ['EASY','NORMAL','HARD']:
            self.data['difficulty']='NORMAL'
        if self.data['tracking_quality'] not in ['FAST','BALANCED','PRECISE']:
            self.data['tracking_quality']='BALANCED'
    def set(self,key,value):
        if key not in self.DEFAULT: return
        self.data[key]=value; self.save()
    def save(self):
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.data,indent=2),encoding='utf-8')
            os.replace(temp,self.path)
        except OSError: pass


class ArcadeScores:
    def __init__(self,location=None):
        self.path=Path(location or Path.home()/'.aetheria'/'arcade_scores.json')
        try:
            contents=json.loads(self.path.read_text(encoding='utf-8'))
            self.scores=contents if isinstance(contents,dict) else {}
        except (OSError,ValueError): self.scores={}
    def best(self,name):
        return max(0,int(self.scores.get(name,0)))
    def merge(self, incoming):
        # Scores arrive only from laptops on the local exhibition network.
        if not isinstance(incoming,dict): return
        valid_names={"BLOCK NOVA","NEON REACTOR","ECHO MATRIX","STAR PILOT"}
        for name,score in incoming.items():
            if name in valid_names and type(score) is int and 0 <= score <= 10**9:
                self.record(name,score)

    def record(self,name,score):
        if score>self.best(name):
            self.scores[name]=int(score)
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                temp=self.path.with_suffix('.tmp')
                temp.write_text(json.dumps(self.scores,indent=2),encoding='utf-8')
                os.replace(temp,self.path)
            except OSError: pass
            return True
        return False


class ArcadeGame:
    name='GAME'; subtitle=''; duration=90
    def __init__(self,scores):
        self.highscores=scores; self.reset()
    def reset(self):
        self.score=0; self.combo=0; self.over=False; self.elapsed=0.0; self.notice=''; self.notice_t=0
    def tick(self,dt):
        if not self.over:
            self.elapsed+=dt
            if self.duration and self.elapsed>=self.duration: self.finish()
        self.notice_t=max(0,self.notice_t-dt)
    def finish(self):
        if not self.over:
            self.over=True
            self.highscores.record(self.name,self.score)
    def ping(self,value):
        self.notice=value; self.notice_t=.9
    def pointer(self,x,y,pressed=False): pass
    def motion(self,x,y,dt): pass
    def keyboard(self,key): pass
    def draw_base(self,s):
        starfield(s,self.elapsed)
        panel(s,(28,18,1224,84))
        text(s,self.name,55,33,29,WHITE,True)
        text(s,self.subtitle,56,72,15,MUTED)
        text(s,'SCORE',690,33,14,MUTED,True)
        text(s,f'{self.score:,}',690,54,26,CYAN,True)
        text(s,'BEST',880,33,14,MUTED,True)
        text(s,f'{self.highscores.best(self.name):,}',880,54,24,GOLD,True)
        text(s,'TIME',1080,33,14,MUTED,True)
        text(s,f'{max(0,int(self.duration-self.elapsed)):02d}s' if self.duration else '--',1080,54,24,WHITE,True)
        if self.notice_t:
            text(s,self.notice,640,111,22,GREEN,True,anchor='center')
    def draw_gameover(self,s):
        tint=pygame.Surface((W,H),pygame.SRCALPHA);tint.fill((4,7,19,218));s.blit(tint,(0,0))
        panel(s,(366,193,548,335),fill=(19,29,51),border=VIOLET,radius=29)
        text(s,'RUN COMPLETE',640,235,37,WHITE,True,anchor='center')
        text(s,f'{self.score:,} POINTS',640,309,41,GOLD,True,anchor='center')
        text(s,f'PERSONAL BEST  {self.highscores.best(self.name):,}',640,376,19,MUTED,anchor='center')
        text(s,'[SPACE] RETRY     [ESC] HOME',640,452,20,CYAN,True,anchor='center')


class BlockNova(ArcadeGame):
    name='BLOCK NOVA'; subtitle='Tactical shape placement | Complete rows and columns'; duration=0
    GRID_X=393; GRID_Y=150; CELL=49
    def reset(self):
        super().reset();self.board=BlockBoard();self.selected=0;self.hint=None
    def slot_rect(self,i): return pygame.Rect(300+250*i,572,224,114)
    def pointer(self,x,y,pressed=False):
        if not pressed or self.over:return
        for i in range(3):
            if self.slot_rect(i).collidepoint(x,y) and self.board.tray[i]:
                self.selected=i;self.ping('SHAPE SELECTED');return
        gx=(x-self.GRID_X)//self.CELL; gy=(y-self.GRID_Y)//self.CELL
        if 0<=gx<8 and 0<=gy<8:
            outcome=self.board.place(self.selected,int(gx),int(gy))
            if outcome:
                self.score=self.board.score;self.combo=self.board.combo
                self.ping(f'+{outcome["points"]}  {outcome["lines"]} LINES')
                if self.board.game_over:self.finish()
                if self.board.tray[self.selected] is None:
                    self.selected=next((i for i,a in enumerate(self.board.tray) if a),0)
            else:self.ping('INVALID PLACEMENT')
    def keyboard(self,key):
        if key in (pygame.K_q,pygame.K_w,pygame.K_e):
            self.selected=(pygame.K_q,pygame.K_w,pygame.K_e).index(key)
    def draw(self,s,hover=None):
        self.draw_base(s)
        panel(s,(367,124,445,447),fill=(12,21,39),border=(70,93,145))
        hx=hy=-100
        if hover: hx=(hover[0]-self.GRID_X)//self.CELL;hy=(hover[1]-self.GRID_Y)//self.CELL
        sh=self.board.tray[self.selected]
        legal=sh and self.board.can_place(sh,hx,hy)
        ghost={(hx+dx,hy+dy) for dx,dy in (sh or [])} if legal else set()
        for y,row in enumerate(self.board.grid):
            for x,v in enumerate(row):
                rect=pygame.Rect(self.GRID_X+x*self.CELL,self.GRID_Y+y*self.CELL,self.CELL-4,self.CELL-4)
                color=PALETTE[(v-1)%5] if v else ((41,93,92) if (x,y) in ghost else (27,39,62))
                pygame.draw.rect(s,color,rect,border_radius=9)
                if v: pygame.draw.rect(s,(205,235,255),rect,1,border_radius=9)
        for i,shape in enumerate(self.board.tray):
            r=self.slot_rect(i); panel(s,r,border=CYAN if i==self.selected else BORDER)
            text(s,f'SLOT {i+1}',r.x+15,r.y+9,14,CYAN if i==self.selected else MUTED,True)
            if shape:
                for dx,dy in shape:
                    pygame.draw.rect(s,PALETTE[i],(r.x+40+dx*24,r.y+39+dy*23,20,20),border_radius=5)
            else: text(s,'PLACED',r.centerx,r.centery,17,MUTED,anchor='center')
        panel(s,(35,199,286,226))
        text(s,'THE RULES',58,221,22,WHITE,True)
        for j,line in enumerate(['1  Select a shape below','2  Tap a square to place','3  Fill a full row or column','4  Chain clears for a combo']):
            text(s,line,58,267+j*35,17,MUTED)
        text(s,f'COMBO  x{self.combo+1}',58,478,23,GOLD,True)
        text(s,'[Q W E] choose shape',58,513,17,MUTED)
        if self.over: self.draw_gameover(s)


class ReflexArena(ArcadeGame):
    name='NEON REACTOR';subtitle='Reflex target rush | Tap blue orbs, avoid red decoys';duration=75
    def reset(self):
        super().reset();self.target=random.randrange(16);self.bomb=random.choice([i for i in range(16) if i!=self.target]);self.expiry=0;self.lives=3
    def _cell(self,i): return pygame.Rect(372+(i%4)*145,145+(i//4)*120,112,95)
    def _reroll(self):
        self.target=random.randrange(16)
        self.bomb=random.choice([i for i in range(16) if i!=self.target]);self.expiry=0
    def tick(self,dt):
        super().tick(dt)
        if self.over:return
        self.expiry+=dt
        if self.expiry>max(.57,1.7-self.elapsed*.013):
            self.combo=0;self.lives-=1;self._reroll();self.ping('MISSED')
            if self.lives<=0:self.finish()
    def pointer(self,x,y,pressed=False):
        if not pressed or self.over:return
        for i in range(16):
            if self._cell(i).collidepoint(x,y):
                if i==self.target:
                    self.combo+=1;bonus=100+min(self.combo,15)*20;self.score+=bonus
                    self.ping(f'PERFECT  +{bonus}');self._reroll()
                else:
                    self.combo=0;self.lives-=1;self.ping('DECOY -1 LIFE')
                    if self.lives<=0:self.finish()
                break
    def draw(self,s,hover=None):
        self.draw_base(s)
        panel(s,(351,124,601,515))
        for i in range(16):
            rect=self._cell(i)
            col=CYAN if i==self.target else (RED if i==self.bomb else (32,48,76))
            pygame.draw.rect(s,(18,31,52),rect,border_radius=16)
            pygame.draw.rect(s,col,rect,2 if i in [self.target,self.bomb] else 1,border_radius=16)
            if i in [self.target,self.bomb]:
                pygame.draw.circle(s,col,rect.center,23)
                pygame.draw.circle(s,WHITE,rect.center,10 if i==self.target else 5)
        panel(s,(38,190,250,267))
        text(s,'REACTOR STATUS',61,215,21,WHITE,True)
        text(s,f'LIVES  {"♥ "*self.lives}',61,265,20,RED,True)
        text(s,f'COMBO  {self.combo}',61,323,25,GOLD,True)
        bar(s,60,395,205,1-self.expiry/max(.57,1.7-self.elapsed*.013),CYAN)
        text(s,'HIT  BLUE  /  AVOID  RED',640,663,19,MUTED,True,anchor='center')
        if self.over:self.draw_gameover(s)


class MemoryCircuit(ArcadeGame):
    name='ECHO MATRIX';subtitle='Train working memory | Repeat the illuminated sequence';duration=0
    def reset(self):
        super().reset();self.core=SimonEngine();self.core.reset();self.flash=-1;self.flash_t=0
    def _pad(self,i):return pygame.Rect(408+(i%2)*238,190+(i//2)*174,202,144)
    def tick(self,dt):
        self.elapsed+=dt;self.core.update(dt)
        if self.core.phase=='over':self.finish()
        self.score=self.core.score;self.combo=self.core.level-1
        self.flash_t=max(0.,self.flash_t-dt)
        self.notice_t=max(0,self.notice_t-dt)
    def pointer(self,x,y,pressed=False):
        if not pressed or self.over:return
        for i in range(4):
            if self._pad(i).collidepoint(x,y):
                outcome=self.core.press(i)
                if outcome=='wrong':self.ping('NOT QUITE - WATCH THE PATTERN')
                if outcome=='level':self.ping('SEQUENCE COMPLETE + BONUS')
                if outcome in ('correct','level'):
                    self.flash=i;self.flash_t=.20
                return
    def draw(self,s,hover=None):
        self.draw_base(s)
        panel(s,(368,149,545,403))
        colors=[CYAN,VIOLET,PINK,GREEN]
        for i in range(4):
            r=self._pad(i)
            lit=(self.core.phase=='preview' and self.core.preview_index<len(self.core.sequence)
                 and self.core.preview_index>=0 and self.core.sequence[self.core.preview_index]==i)
            lit=lit or (self.flash==i and self.flash_t>0)
            color=colors[i]
            pygame.draw.rect(s,color if lit else (25,38,61),r,border_radius=25)
            pygame.draw.rect(s,color,r,3,border_radius=25)
            text(s,str(i+1),r.centerx,r.centery-25,41,INK if lit else color,True,anchor='center')
        panel(s,(40,180,279,290))
        text(s,'CURRENT ROUND',60,205,19,MUTED,True)
        text(s,str(self.core.level),60,240,55,WHITE,True)
        text(s,'WATCH' if self.core.phase=='preview' else 'YOUR TURN',60,333,24,CYAN,True)
        text(s,f'LIVES  {self.core.lives}',60,392,21,RED,True)
        text(s,'Repeat each colour in order',640,593,19,MUTED,anchor='center')
        text(s,'[1-4] keyboard or pinch pad',640,636,19,MUTED,anchor='center')
        if self.over:self.draw_gameover(s)
    def keyboard(self,key):
        if key in [pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4]:
            self.pointer(*self._pad([pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4].index(key)).center,True)


class StarPilot(ArcadeGame):
    name='STAR PILOT';subtitle='Precision navigation | Collect energy, dodge incoming hazards';duration=85
    def reset(self):
        super().reset();self.ship=[640.,570.];self.objects=[];self.spawn=0.;self.lives=3;self.invinc=0.;self.dir=0
    def motion(self,x,y,dt):
        if not self.over:self.ship[0]+=(max(327,min(952,x))-self.ship[0])*min(1.,dt*14)
    def keyboard(self,key):
        if key==pygame.K_LEFT:self.dir=-1
        if key==pygame.K_RIGHT:self.dir=1
    def tick(self,dt):
        super().tick(dt)
        if self.over:return
        self.invinc=max(0,self.invinc-dt)
        self.ship[0]=max(327,min(952,self.ship[0]+self.dir*550*dt))
        self.dir=0
        self.spawn+=dt
        if self.spawn>max(.22,.62-self.elapsed*.003):
            self.spawn=0
            self.objects.append([random.randint(344,932),115.,random.choice([0,0,0,1]),False])
        speed=200+self.elapsed*4
        for obj in self.objects:
            obj[1]+=speed*dt
            if not obj[3] and distance(obj[:2],self.ship)<39:
                obj[3]=True
                if obj[2]:
                    if self.invinc<=0:
                        self.lives-=1;self.combo=0;self.invinc=1.;self.ping('SHIELD HIT')
                        if not self.lives:self.finish()
                else:
                    self.combo+=1;gain=45+min(self.combo,10)*10;self.score+=gain;self.ping(f'ENERGY +{gain}')
        self.objects=[o for o in self.objects if o[1]<690 and not o[3]]
    def draw(self,s,hover=None):
        self.draw_base(s)
        panel(s,(308,120,665,539),fill=(13,22,41))
        for i in range(7):
            x=342+i*93
            pygame.draw.line(s,(28,57,86),(x,137),(x,644),2)
        for j in range(16):
            y=int(140+((j*52+self.elapsed*160)%500))
            pygame.draw.line(s,(19,41,67),(320,y),(961,y),1)
        for x,y,hazard,_ in self.objects:
            col=RED if hazard else CYAN
            pygame.draw.circle(s,col,(int(x),int(y)),24)
            pygame.draw.circle(s,INK,(int(x),int(y)),12)
            if not hazard: pygame.draw.circle(s,WHITE,(int(x),int(y)),5)
        x,y=map(int,self.ship)
        if not(self.invinc and int(self.invinc*10)%2):
            pygame.draw.polygon(s,CYAN,[(x,y-31),(x-28,y+27),(x,y+17),(x+28,y+27)])
            pygame.draw.polygon(s,WHITE,[(x,y-18),(x-8,y+12),(x+8,y+12)])
        panel(s,(38,183,235,274))
        text(s,'MISSION HUD',60,208,22,WHITE,True)
        text(s,'ARMOUR',60,263,16,MUTED,True)
        text(s,'♥ '*self.lives,60,289,25,RED,True)
        text(s,'STREAK',60,360,16,MUTED,True)
        text(s,str(self.combo),60,387,35,GOLD,True)
        text(s,'Move hand or mouse to steer',640,667,18,MUTED,anchor='center')
        if self.over:self.draw_gameover(s)


GAME_DEFS=[
 ('GAME_1','FREESTYLE STUDIO','Eight playable instruments',CYAN,'ORIGINAL'),
 ('GAME_2','PIANO TILES','Accelerating rhythm highway',GREEN,'ORIGINAL'),
 ('GAME_3','SYNTH BLADE','Two-hand rhythm slasher',PINK,'ORIGINAL'),
 ('ORCHESTRA','GRAND ORCHESTRA','Conduct a live concert',GOLD,'ORIGINAL'),
 ('GAME_5','SINGULARITY','Celestial score catcher',VIOLET,'ORIGINAL'),
 ('GAME_6','SONIC SLINGSHOT','Physics meets musical chimes',CYAN,'ORIGINAL'),
 ('LOOP_STATION','LOOP LAB','Beat making and AI assistance',GREEN,'ORIGINAL'),
 ('LIVE_STAGE','LIVE PERFORMANCE','Create a musical identity',GOLD,'ORIGINAL'),
 ('BLOCK_NOVA','BLOCK NOVA','Strategic grid puzzler',CYAN,'NEW'),
 ('REFLEX','NEON REACTOR','Rapid-fire reflex challenge',PINK,'NEW'),
 ('MEMORY','ECHO MATRIX','Remember the signal sequence',VIOLET,'NEW'),
 ('STAR_PILOT','STAR PILOT','Gesture-steered arcade survival',GREEN,'NEW'),
]


class ArcadeShell:
    def __init__(self,preferences):
        self.cfg=preferences
        self.buttons=[];self.page=0;self.category='ALL';self.t=0.
    def clickable(self,s,rect,label,action,active=False,accent=CYAN,small=False):
        round_button(s,rect,label,active,accent,small)
        self.buttons.append((pygame.Rect(rect),action))
    def interact(self,x,y):
        for rect,action in reversed(self.buttons):
            if rect.collidepoint(x,y): return action
        return None
    def header(self,s,active):
        panel(s,(22,15,1236,78),fill=(11,19,34))
        text(s,'AETHERIA',43,33,29,WHITE,True)
        text(s,'NEXT  /  MOTION ARCADE',208,42,15,CYAN,True)
        labels=[('HOME','MENU'),('GAMES','ARCADE'),('SETTINGS','SETTINGS'),('HOW TO PLAY','HELP'),('LEGACY HUB','CLASSIC_HUB')]
        x=574
        for label,state in labels:
            width={'HOME':91,'GAMES':93,'SETTINGS':109,'HOW TO PLAY':147,'LEGACY HUB':137}[label]
            self.clickable(s,(x,30,width,45),label,('goto',state),state==active,small=True)
            x+=width+8
    def draw(self,s,state,scores=None):
        self.buttons=[];self.t+=1/60
        starfield(s,self.t,not self.cfg.data['particles'])
        self.header(s,state)
        if state=='MENU':self.home(s)
        elif state=='ARCADE':self.catalog(s,scores)
        elif state=='SETTINGS':self.settings(s)
        elif state=='HELP':self.help(s)
        text(s,'ESC  HOME    |    F1  PAUSE    |    G  GAMES    |    T  SETTINGS    |    F  FULLSCREEN',640,691,15,MUTED,anchor='center')
    def home(self,s):
        panel(s,(28,121,1224,380),fill=(12,23,43),border=(57,100,137),radius=30)
        for r in range(13):
            pygame.draw.circle(s,(18+r*2,57+r*4,89+r*3),(995,296),156-r*9,2)
        text(s,'THE NEXT GENERATION OF PLAY',77,160,17,CYAN,True)
        text(s,'CONTROL THE GAME',75,202,51,WHITE,True)
        text(s,'WITH YOUR HANDS.',75,265,51,CYAN,True)
        text(s,'12 experiences. Real-time motion control. Music, puzzles and reflexes.',77,348,21,MUTED)
        text(s,'No controller required. Mouse and keyboard also supported.',77,382,18,MUTED)
        self.clickable(s,(77,432,243,52),'EXPLORE GAMES',('goto','ARCADE'),True)
        self.clickable(s,(337,432,201,52),'QUICK START',('launch','BLOCK_NOVA'),False,VIOLET)
        card_data=[('04','NEW ARCADE GAMES',CYAN),('08','ORIGINAL MODES',VIOLET),('2','PLAYER LAN SYNC',GREEN)]
        for i,(num,description,col) in enumerate(card_data):
            x=28+i*416
            panel(s,(x,522,392,139),border=(51,75,104))
            text(s,num,x+22,538,45,col,True)
            text(s,description,x+103,558,19,WHITE,True)
            text(s,'CURATED ARCADE EXPERIENCE',x+103,591,13,MUTED)
    def catalog(self,s,scores):
        text(s,'GAME LIBRARY',45,112,36,WHITE,True)
        text(s,'All originals preserved, with four new experiences.',45,158,18,MUTED)
        for i,cat in enumerate(['ALL','NEW','ORIGINAL']):
            self.clickable(s,(700+i*165,115,151,43),cat,('filter',cat),self.category==cat,small=True)
        entries=[v for v in GAME_DEFS if self.category=='ALL' or v[4]==self.category]
        max_page=max(0,(len(entries)-8)//8 + (1 if len(entries)%8 else 0)-1)
        self.page=min(self.page,max_page)
        entries=entries[self.page*8:self.page*8+8]
        for i,(key,name,desc,col,category) in enumerate(entries):
            x=45+(i%4)*308;y=191+(i//4)*224
            panel(s,(x,y,291,209),fill=(17,26,46),border=(48,66,97),radius=21)
            pygame.draw.rect(s,col,(x+16,y+18,59,4),border_radius=2)
            text(s,category,x+274,y+19,13,col,True,anchor='right')
            text(s,name,x+17,y+49,22,WHITE,True)
            text(s,desc,x+17,y+92,15,MUTED)
            if scores and key in scores:
                text(s,f'BEST {scores[key].highscores.best(scores[key].name):,}',x+18,y+123,15,GOLD)
            self.clickable(s,(x+17,y+152,255,43),'PLAY NOW',('launch',key),True,col,small=True)
        self.clickable(s,(446,655,120,38),'PREVIOUS',('page',-1),self.page>0,small=True)
        text(s,f'PAGE {self.page+1} / {max_page+1}',640,663,17,MUTED,anchor='center')
        self.clickable(s,(714,655,120,38),'NEXT',('page',1),self.page<max_page,small=True)
    def settings(self,s):
        text(s,'PERSONALISE YOUR PLAY',45,120,33,WHITE,True)
        text(s,'Settings are saved automatically and applied instantly.',46,163,19,MUTED)
        fields=[
          ('INPUT MODE','input_mode',['HYBRID','CAMERA','MOUSE']),
          ('GAME DIFFICULTY','difficulty',['EASY','NORMAL','HARD']),
          ('CAMERA QUALITY','tracking_quality',['FAST','BALANCED','PRECISE']),
          ('HAND OVERLAY','show_hands',[True,False]),
          ('PARTICLE EFFECTS','particles',[True,False]),
          ('TUTORIAL HINTS','tutorials',[True,False]),
          ('SESSION LENGTH','session_minutes',[5,8,12,15,20]),
          ('MASTER VOLUME','volume',[0.,.25,.5,.75,1.]),
          ('PINCH SENSITIVITY','gesture_sensitivity',[.7,.85,1.,1.15,1.3]),
          ('FULLSCREEN','fullscreen',[False,True]),
        ]
        for i,(label,key,values) in enumerate(fields):
            row=i%5; col=i//5;x=48+col*605;y=201+row*88
            panel(s,(x,y,578,80))
            text(s,label,x+16,y+15,16,MUTED,True)
            val=self.cfg.data[key]
            if isinstance(val,float): displayed=f'{val:.2f}'
            else:displayed=str(val).upper()
            text(s,displayed,x+16,y+46,20,CYAN,True)
            self.clickable(s,(x+377,y+19,80,43),'–',('adjust',key,-1),False,small=True)
            self.clickable(s,(x+469,y+19,80,43),'+',('adjust',key,1),False,small=True)
        text(s,'PRECISE improves landmark detail but may lower FPS. Mouse mode works without a camera.',49,657,16,MUTED)
    def change(self,key,direction):
        options={
          'input_mode':['HYBRID','CAMERA','MOUSE'],'difficulty':['EASY','NORMAL','HARD'],
          'tracking_quality':['FAST','BALANCED','PRECISE'], 'fullscreen':[False,True],
          'show_hands':[False,True], 'particles':[False,True], 'tutorials':[False,True],
          'session_minutes':[5,8,12,15,20],'volume':[0.,.25,.5,.75,1.],
          'gesture_sensitivity':[.7,.85,1.,1.15,1.3]}
        if key not in options:return
        arr=options[key]; old=self.cfg.data[key]
        idx=min(range(len(arr)),key=lambda i:abs(arr[i]-old) if isinstance(old,(float,int)) else 0 if arr[i]==old else 1)
        self.cfg.set(key,arr[(idx+direction)%len(arr)])
    def help(self,s):
        text(s,'HOW TO PLAY',45,123,36,WHITE,True)
        content=[
          ('01','TRACK','Stand 0.5-1.5m from the camera in even lighting. Keep your hand in frame.'),
          ('02','SELECT','Bring thumb and index finger together to pinch; release to click.'),
          ('03','PLAY','Move your index finger to interact with targets or steer your ship.'),
          ('04','ALTERNATE','Use mouse click and movement; keyboard 1-6 and 7-0 for games.'),
          ('05','OPTIMISE','Use FAST camera quality for smooth FPS, PRECISE for finer fingertip detail.'),
        ]
        for i,(n,title,description) in enumerate(content):
            y=194+i*86;panel(s,(43,y,1191,72))
            text(s,n,66,y+19,28,CYAN,True)
            text(s,title,138,y+12,21,WHITE,True)
            text(s,description,138,y+41,16,MUTED)
        self.clickable(s,(520,635,240,43),'BACK TO GAMES',('goto','ARCADE'),True)
