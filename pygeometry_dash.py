import sys

import pygame
from pygame.locals import *
import pygments
from utils import *
from random import *

pygame.init()
'''
TODO:
rotar por supuesto, VOY A SUDAR
FIXME: prioridad: hace una copia de l a imagen cuando salta, pero esto genera problemas...
si se mantiene pulsaod el click izquierda que se mantenga saltando
animacion muerte
camara propia
voy a sudar para los obstáculos, y tener una buena jugabilidad
si el jugador está bajando del salto rota igualmente
en los columnas para pasar a través de ellas que haya más espacio entre ellas sino es muy difícil acertar
'''

# 
fps = 60
fpsClock = pygame.time.Clock() 
TILESIZE = 33
SCREEN_WIDHT, SCREEN_HEIGHT = 900, 476
FLOOR = SCREEN_HEIGHT-TILESIZE
screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))

class Player(pygame.sprite.Sprite):
    def __init__(self, pos) -> None:
        super().__init__()
        self.image = load_image('imgs/square.png',True,32,32)
        self.rect = self.image.get_rect(topleft=pos)
        self.initial_jump = -11
        self.direction = vec(0,0)
        self.on_ground = True
        self.speed =6
        self.copy_img = self.image.copy()
        self.ang = 0
        self.gravity = .8
        self.hit_rect = pygame.rect.Rect(0,0,self.image.get_width(),self.image.get_height())
        self.mask = pygame.mask.from_surface(self.image)
        # FIXME 
        self.died = False

        self.pos = vec(self.rect.center)
    
    def apply_gravity(self):
        self.direction.y += self.gravity
        self.pos.y += self.direction.y
        self.hit_rect.y = self.pos.y
    
    
    def rotate(self):
        if not self.on_ground:
            self.rotating = True
            self.ang += 7
            if self.ang >= 180:
                self.rotating = False
                self.ang = 180
            self.image = pygame.transform.rotate(self.copy_img,-self.ang)
            self.rect = self.image.get_rect(center=self.pos)
            self.hit_rect.topleft = self.pos
            self.mask = pygame.mask.from_surface(self.image)
        else:
            # tricky to figure out, at least for me
            #print("no rotando ",self.ang)
            if self.ang and self.ang%90:
                # calcular el más próximo a 90 o 180
                if abs(90-self.ang) <= abs(180-self.ang):
                    #print("mas proximo a 90")
                    self.ang = 90
                else:
                    #print("mas proximo a 180")
                    self.ang = 180
                #print(self.ang)
                self.image = pygame.transform.rotate(self.copy_img,-self.ang)
                self.rect = self.image.get_rect(center=self.pos)
                self.hit_rect.topleft = self.pos
                self.mask = pygame.mask.from_surface(self.image)
            

    def move(self):
        keys=pygame.key.get_pressed()
        self.direction.x = self.speed
        # if keys[K_a]:
        #     self.direction.x = -self.speed
        # elif keys[K_d]:
        #     self.direction.x = self.speed
        # else:
        #     self.direction.x = 0
        self.rect.center = self.hit_rect.center
        if keys[K_SPACE] and self.on_ground:
            self.ang = 0
            self.copy_img = self.image.copy()
            self.direction.y = self.initial_jump
        

    def update(self):
        self.rotate()
        self.move()

class Death(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.pos = pos
        self.image = pygame.Surface((200,200),SRCALPHA)
        self.rect = self.image.get_rect(center=self.pos)
        self.opacity = 255
        self.radius = 2

    def update(self):
        pygame.draw.circle(self.image,(142,142,142,self.opacity),(self.image.get_width()//2,self.image.get_height()//2),self.radius)
        self.radius += 2.5
        # if self.radius >= self.image.get_width()//2:
        #     self.kill()
        self.opacity -= 4
        if self.radius >= self.image.get_width()//2 or self.opacity < 0:
            print(self.radius)
            self.kill()
            

class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, xvel, yvel, size, color, gravity=None):
        super().__init__()
        self.color = color
        self.image = pygame.Surface((size,size))
        self.image.fill(color)
        self.pos = vec(pos)
        self.rect = self.image.get_rect(topleft=self.pos)
        self.vel = vec(xvel,yvel)
        self.gravity = gravity
        self.alpha = 255

    def update(self):
        self.pos.x += self.vel.x
        self.pos.y += self.vel.y
        if self.gravity != None:
            self.vel.y += self.gravity
        self.rect.topleft = self.pos
        self.image.set_alpha(self.alpha)
        self.alpha -= 5
        if self.alpha <= 0:
             self.kill()
        

# because everyone love particles, indeed...
class Particles:
    def __init__(self, pos) -> None:
        super().__init__()
        self.particles = pygame.sprite.Group()
        for _ in range(100):
            self.particles.add(Particle(pos[0],pos[1],uniform(-2,-1),uniform(-2,-1)))

    def update(self):
        self.particles.update()
        
class Obstacle(pygame.sprite.Sprite):
    def __init__(self, pos,width,height,img) -> None:
        super().__init__()
        self.image = load_image(img,True,width,height)
        self.rect = self.image.get_rect(topleft=pos)
        self.mask = pygame.mask.from_surface(self.image)

status = 'winner'
class Game():
    def read_map(self, name):
        file = ''
        with open(name) as file:
            file = file.readlines()
        return file

    def __init__(self) -> None:
        self.camera_x = 3
        self.death_ani = pygame.sprite.GroupSingle()
        self.copy_rect_player = None # for the camera
        self.restart = False
        self.collision_type = {'horizontal':False,'vertical':False,'ramp':False}
        self.obstacles =  pygame.sprite.Group()
        self.tiles_map = self.read_map("level.txt")
        self.camera = Camera(len(self.tiles_map[0])*TILESIZE,len(self.tiles_map)*TILESIZE)
        self.player = pygame.sprite.GroupSingle()
        self.init_pos = []
        self.load_map()
    
    def load_map(self):
        for row,line in enumerate(self.tiles_map):
            for col, char in enumerate(line):
                if char == "1":
                    self.obstacles.add(Obstacle((col*TILESIZE,row*TILESIZE),TILESIZE,TILESIZE,'imgs/block_1.png'))
                elif char == "P":
                    self.init_pos = [col*TILESIZE,row*TILESIZE]
                    self.player.add(Player(self.init_pos))

    def horizontal_movement(self):
        if not self.player.sprite:
            return
        global status
        player = self.player.sprite
        player.pos.x += player.direction.x
        player.hit_rect.x = player.pos.x
        # ecuaciones del movimiento
        self.collision_type['horizontal'] = False
        
        for obstacle in self.obstacles.sprites():
            if obstacle.rect.colliderect(player.hit_rect):
                offset = player.hit_rect.x - obstacle.rect.x, player.hit_rect.y - obstacle.rect.y
                # if pygame.sprite.spritecollide(player, self.obstacles, False, pygame.sprite.collide_mask):
                #     if player.direction.y:
                #         print('noooo')
                overlap = player.mask.overlap(obstacle.mask, offset)
                if overlap:
                    status = 'loser'
                    self.copy_rect_player = player.hit_rect.copy()
                    self.death_ani.add(Death(self.camera.apply(player.hit_rect).topright))
                    player.kill()
                # if player.direction.y:
                #     status = 'loser'
                
                if player.direction.x > 0:                        
                    player.hit_rect.right = obstacle.rect.left
                    player.pos.x = player.hit_rect.x

    def vertical_movement(self):
        if not self.player.sprite:
            return
        player = self.player.sprite
        #print("dt: ",self.dt)
        player.apply_gravity()
        self.collision_type['vertical'] = False
        for obstacle in self.obstacles.sprites():
            if obstacle.rect.colliderect(player.hit_rect):
                self.collision_type['vertical'] = True
                if player.direction.y > 0: # falling
                    player.hit_rect.bottom = obstacle.rect.top
                    player.pos.y = player.hit_rect.y
                    player.direction.y = 0
                    player.on_ground = True
                if player.direction.y < 0:
                    player.hit_rect.top = obstacle.rect.bottom
                    player.pos.y = player.hit_rect.y
                    player.direction.y = 0

        if player.on_ground and player.direction.y < 0 or player.direction.y > 1: # si lo tengo en player como antes, puedo saltar en el aire entre los dos rectángulos altos
            player.on_ground = False

    def update(self):
        self.horizontal_movement()
        self.vertical_movement()
        self.player.update()
        if self.player.sprite:
            self.camera.update(self.player.sprite.rect)
        self.death_ani.update()
        self.death_ani.draw(screen)
        #player.rect.center = player.hit_rect.center 
        
        
        
        #print(self.player.sprite.direction)
        #print(self.player.sprite.rotating)
    
    def move_map(self):
        pass
        # for spr in self.obstacles:
        #     spr.rect.x -= self.camera_x
                
        # player = self.player.sprite
        # player.rect.center = player.rect.center
        
        
    
    def draw(self, surface):
        player = self.player.sprite
        
        if player:
            surface.blit(player.image,self.camera.apply(player.rect)) 
        else:
            self.camera.apply(self.copy_rect_player)

        for sprite in self.obstacles.sprites():
            surface.blit(sprite.image,self.camera.apply(sprite.rect))
        
        # self.obstacles.draw(surface)
        # self.player.draw(surface)
        #pygame.draw.rect(screen,'red',self.camera.apply(player.hit_rect),2)
        
        #pygame.draw.rect(screen,'red',self.player.sprite.hit_rect)
# FIXME: no debería depender del jugdaor 

class Camera:
    def __init__(self, width, height) -> None:
        self.camera = pygame.Rect(0,0,width, height)
        self.width = width
        self.height = height

    def apply(self, target_rect):
        return target_rect.move(self.camera.topleft)
        

    def update(self, target_rect):
        #pygame.draw.rect(screen,'green',self.camera,4)
        x = -target_rect.centerx + SCREEN_WIDHT//6
        y = -target_rect.centery + SCREEN_HEIGHT//6
        x = min(x,0) # left
        y = min(y,0) # top
        x = max(SCREEN_WIDHT-self.width,x) # right
        y = max(SCREEN_HEIGHT-self.height,y) # bottom
        self.camera = pygame.Rect(x,y,self.width,self.height)
        

particles = pygame.sprite.Group()
# Game loop.
game = Game()

cont = 0
while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == MOUSEBUTTONDOWN:
            player = game.player.sprite
            game.death_ani.add(Death(pygame.mouse.get_pos()))
           
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                status = 'winner'
                game = Game()
            if event.key == pygame.K_a:
                game.player.sprite.rect.x += 1               

    # Update.
    screen.fill('lightblue')
    cont += 1
    game.update()
    player = game.player.sprite
    if player and player.on_ground:
        for _ in range(2):
            particles.add(Particle(game.camera.apply(player.hit_rect).bottomleft-vec(-3,6),uniform(-2,-1),uniform(-2,-1),5,'white',0.1))
    
    # Draw.
    pygame.draw.line(screen,'white',(0,FLOOR),(SCREEN_WIDHT,FLOOR))
    particles.update()
    particles.draw(screen)
    
    
    game.draw(screen)
    debug(str(status))
    debug(str(status),x=10,y=40)
    pygame.display.update()
    
    fpsClock.tick(fps)
    
