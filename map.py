import pygame
import pytmx
from pathlib import Path
from time import time
from random import randint, choice


class Event:
    
    def __init__(self, coords: tuple, img=None):
        if img is not None:
            self.image = img
            self.rect = self.image.get_rect()
        else:
            self.image = None
            self.rect = pygame.Rect(0, 0, 48, 48)

        x, y = coords
        self.rect.center = x, y
        
    # Wszystkie poniższe funkcje powinny, ale nie muszą zostać przeciążone 
    def check_stepped_on(self, game):
        pass
    
    def check_interact(self, game, tile):
        pass

    def draw(self, tile):
        if self.image is not None:
            image_rect = self.image.get_rect()
            image_rect.center = 24, 24
            tile.image.blit(self.image, image_rect)


class Teleport(Event):
    
    def __init__(self, coords, place_on_map: tuple, map=None, img=None):
        super().__init__(coords, img=img)
        self.dest_map = map
        self.map_coords = place_on_map

    def teleport(self, game):
        """Teleportuje gracza na wybrane koordynaty na wybranej mapie"""
        game.PLAYER.set_pos(self.map_coords)
        if self.dest_map is not None:
            game.map = self.dest_map

    def check_stepped_on(self, game):
        if self.rect.colliderect(game.PLAYER.get_rectangle()):
            self.teleport(game)

    def check_interact(self, game, tile):
        if game.map.check_if_looking_at(tile):
            self.teleport(game)
     
            
class Dialogue(Event):

    def __init__(self, coords, img=None, npc=None):
        super().__init__(coords, img=img)
        self.NPC = npc
        if npc.__class__.__name__.lower() == "lockeddoor":
            self.NPC_NAME = ""
        else:
            self.NPC_NAME = self.NPC.__class__.__name__
        self.current_tree = None
        self.radiant_selected = False

    def check_interact(self, game, tile):
        if game.map.check_if_looking_at(tile):
            if self.NPC.is_available() is not None:
                self.dialogue(game)
            else:
                pass
        else:
            pass

    def dialogue(self, game):

        if self.current_tree is None:
            self.current_tree = self.NPC.get_dialogue()

        if self.current_tree.__class__.__name__ == "RadiantTree" and not self.radiant_selected:
            self.current_tree.choose_random()
            self.radiant_selected = True

        game.map.in_dialogue = True

        if self.current_tree.get_current_line() is not None:
            game.SCREEN.fill((0, 0, 0))
            game.map.current_dialogue = self
            name_tag, name_tag_rect = self.create_name_tag(game)

            content_tag, content_tag_rect = self.create_content_tag(game)
            content_tag.fill((128, 0, 32))

            npc_name, npc_name_rect = game.FONT.render(self.NPC_NAME, size=36, fgcolor=(255,255,255))
            npc_name_rect.center = name_tag_rect.w // 2, name_tag_rect.h // 2
            name_tag.blit(npc_name, npc_name_rect)

            content = self.current_tree.get_content()
            content, content_rect = game.FONT.render(content, size=24, fgcolor=(255,255,255))
            content_rect.center = content_tag_rect.w // 2, content_tag_rect.h // 2
            content_tag.blit(content, content_rect)

            game.map.dialogue_card.fill((0, 0, 0))
            game.map.dialogue_card.blit(npc_name, npc_name_rect)
            game.map.dialogue_card.blit(content_tag, content_tag_rect)
            self.current_tree.go_to_next()

        else:
            game.map.current_dialogue = None
            game.map.in_dialogue = False
            self.current_tree = None
            self.radiant_selected = False

    def create_name_tag(self, game):
        name_tag = pygame.Surface((game.map.dialogue_card_rect.w // 6, game.map.dialogue_card_rect.h // 3))
        name_tag_rect = name_tag.get_rect()
        name_tag_rect.center = name_tag_rect.w // 2, game.map.dialogue_card_rect.h // 6
        return name_tag, name_tag_rect

    def create_content_tag(self, game):
        content_tag = pygame.Surface((game.map.dialogue_card_rect.w, 2 * game.map.dialogue_card_rect.h // 3))
        content_tag_rect = content_tag.get_rect()
        content_tag_rect.center = content_tag_rect.w // 2, 2 * game.map.dialogue_card_rect.h // 3
        return content_tag, content_tag_rect


class DangerZone(Event):

    def __init__(self, coords, enemies: list, game, max_level: int, img=None):
        super().__init__(coords, img)
        self.enemies = enemies
        self.game = game
        self.max_level = max_level

    def start_a_fight(self):
        enemy = choice(self.enemies)
        level = randint(1, self.max_level)
        for x in range(level - 1):
            enemy.level_up()
        self.game.STATE_MANAGER.change_state("FIGHT")
        self.game.FIGHTSCREEN.set_enemy(enemy)

    def check_stepped_on(self, game):
        roll = randint(1, 10000)
        if self.rect.colliderect(game.PLAYER.get_rectangle()) and roll <= 20:
            self.start_a_fight()
        if self.rect.colliderect(game.PLAYER.get_rectangle()) and 100 <= roll <= 200:
            self.game.INVENTORY.add_item("Junk", amount=randint(1, 7))


class Shop(Dialogue):
    def __init__(self, coords: tuple, img=None, npc=None):
        super().__init__(coords, img, npc)

    def dialogue(self, game):
        super().dialogue(game)
        if not game.map.in_dialogue:
            game.STATE_MANAGER.change_state(6)
            game.SHOPSCREEN.set_for_refresh()


class Cure(Dialogue):
    def __init__(self, coords: tuple, img=None, npc=None):
        super().__init__(coords, img, npc)

    def dialogue(self, game):
        super().dialogue(game)
        for creature in game.PLAYER.creatures:
            creature.revitalize()


class Tile:
    def __init__(self, image, rect, impassable, danger_zone, size, x, y, layer):
        self.image = image
        self.rect = rect
        self.size = size
        self.x = x
        self.y = y
        self.layer = layer
        self.rect.center = x * self.size[0] + 24, y * self.size[1] + 24
        self.impassable = impassable
        self.danger_zone = danger_zone
        self.width_pos = ((self.rect.x + 1) - (self.size[0] // 2), self.rect.x + (self.size[0] // 2))
        self.height_pos = ((self.rect.y + 1) - (self.size[1] // 2), self.rect.y + (self.size[1] // 2))
        self.events = []
        
    def add_event(self, event):
        self.events.append(event)

    def get_center(self):
        return self.rect.center


class Map:
    def __init__(self, game):

        self.game = game
        self.tmx_map_data = None
        self.layers = []
        self.map_width = None
        self.map_height = None
        self.last_press = time()
        self.cooldown = 0.25
        self.baked = 0
        self.scale = 1
        self.in_dialogue = False
        self.current_dialogue = None
        self.dialogue_card = pygame.Surface((self.game.SCR_WIDTH, self.game.SCR_HEIGHT // 4))
        self.dialogue_card_rect = self.dialogue_card.get_rect()
        self.dialogue_card_rect.center = self.game.SCR_WIDTH // 2,  7 * (self.game.SCR_HEIGHT // 8)

    def load_map(self, mapname):
        """Funkcja ta wczytuje mapę z pliku .tmx"""
        if mapname[:-4] != ".tmx":
            mapname += ".tmx"
            
        map_path = Path.cwd()
        map_path /= Path(f"maps/{mapname.lower()}")
        self.tmx_map_data = pytmx.load_pygame(map_path)
        layer_num = 0
        
        for layer in self.tmx_map_data:
            self.layers.append([])
            
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    image = self.tmx_map_data.get_tile_image_by_gid(gid)
                    if image is not None:
                        data = self.tmx_map_data.get_tile_properties_by_gid(gid)
                        impassable = data["impassable"]
                        danger_zone = data["danger_zone"]
                        rect = image.get_rect()
                        tile = Tile(image, rect, impassable, danger_zone, (self.tmx_map_data.tilewidth,
                                                              self.tmx_map_data.tileheight), x, y, layer_num)
                        self.layers[layer_num].append(tile)
                        
            layer_num += 1
        
    def _handle_input(self, keys_pressed, game):

        cur_time = time()
        if keys_pressed[pygame.K_e] and not self.in_dialogue and cur_time - self.last_press > 0.5:
            for layer in self.layers:
                for tile in layer:
                    if len(tile.events) != 0:
                        for event in tile.events:
                            event.check_interact(game, tile)
                            self.last_press = cur_time

        elif (keys_pressed[pygame.K_SPACE] or keys_pressed[pygame.K_e] or keys_pressed[pygame.K_RETURN]) and self.in_dialogue and cur_time - self.last_press > self.cooldown:
            self.current_dialogue.current_tree.flip_go_to_next()
            self.last_press = cur_time

        if keys_pressed[pygame.K_ESCAPE] and cur_time - self.last_press > self.cooldown and cur_time - self.game.func_key_used > self.cooldown:
            self.game.STATE_MANAGER.change_state(1)
            self.last_press = cur_time
            self.game.func_key_used = cur_time

        if keys_pressed[pygame.K_i] and cur_time - self.last_press > self.cooldown and cur_time - self.game.func_key_used > self.cooldown:
            self.game.STATE_MANAGER.change_state(2)
            self.last_press = cur_time
            self.game.func_key_used = cur_time

        # if keys_pressed[pygame.K_f] and cur_time - self.last_press > self.cooldown and cur_time - self.game.func_key_used > self.cooldown:
        #     self.game.STATE_MANAGER.change_state(5)
        #     self.last_press = cur_time
        #     self.game.func_key_used = cur_time

    def update(self, keys_pressed, game):
        if self.in_dialogue:
            self.current_dialogue.dialogue(self.game)
        self._handle_input(keys_pressed, game)

    def draw_map(self):
        # Ustawienie warstwy na pierwszą warstwę
        layer_num = 1
        # Przygotowanie powierzchni
        self.game.map_surface = pygame.Surface((self.tmx_map_data.width * self.tmx_map_data.tilewidth,
                                                self.tmx_map_data.height * self.tmx_map_data.tileheight))
        
        # Pętla wyrysowująca kolejne kafelki na powierzchni
        for layer in self.layers:
            
            for tile in layer:
                self.game.map_surface.blit(tile.image, tile.rect)
                for event in tile.events:
                    if event.image is not None:
                        self.game.map_surface.blit(event.image, tile.rect)
                
            if layer_num == 1:
                self.game.PLAYER.draw(self.game.map_surface)
                
            layer_num += 1
        
        # Dostosowanie powierzchni do odpowiedniej skali
        self.game.map_surface = pygame.transform.scale(self.game.map_surface,
                                                       (self.game.map_surface.get_width() * self.game.scale,
                                                        self.game.map_surface.get_height() * self.game.scale))

        pos_x, pos_y = self.game.PLAYER.get_pos()
        
        # Obliczenie wymaganego offsetu tak, aby ekran był zawsze wycentrowany 
        map_offset_x = (self.game.SCR_WIDTH // 2) - (pos_x * self.game.scale)
        map_offset_y = (self.game.SCR_HEIGHT // 2) - (pos_y * self.game.scale)
        
        # Wyrysowanie powierzchni na ekranie
        self.game.SCREEN.blit(self.game.map_surface, (map_offset_x, map_offset_y))

        if self.in_dialogue:
            self.game.SCREEN.blit(self.dialogue_card, self.dialogue_card_rect)

    def clear_dialogue_card(self):
        self.dialogue_card = pygame.Surface((self.game.SCR_WIDTH, self.game.SCR_HEIGHT // 4))
        self.dialogue_card_rect = self.dialogue_card.get_rect()
        self.dialogue_card_rect.center = self.game.SCR_WIDTH // 2, self.game.SCR_HEIGHT // 8

    def get_layers(self):
        return self.layers

    def get_tile(self, layer, x, y):
        return self.layers[layer][x + self.tmx_map_data.width * y]

    def get_tile_center(self, tile):
        return tuple(tile.rect.center)

    def add_event(self, tile: Tile, event: Event):
        tile.add_event(event)

    def add_teleport(self, tile: Tile, place_on_map: tuple, mapname, img=None):
        cx, cy = self.get_tile_center(tile)
        px, py = place_on_map
        px = 24 + px * 48
        py = 24 + py * 48
        event = Teleport((cx, cy), (px, py), mapname, img=img)
        self.add_event(tile, event)

    def add_dialogue(self, tile, img=None, npc=None):
        cx, cy = self.get_tile_center(tile)
        event = Dialogue((cx, cy), img=img, npc=npc)
        self.add_event(tile, event)
        tile.impassable = True

    def add_shop(self, tile, img=None, npc=None):
        cx, cy = self.get_tile_center(tile)
        event = Shop((cx, cy), img=img, npc=npc)
        self.add_event(tile, event)
        tile.impassable = True

    def add_cure(self, tile, img=None, npc=None):
        cx, cy = self.get_tile_center(tile)
        event = Cure((cx, cy), img=img, npc=npc)
        self.add_event(tile, event)
        tile.impassable = True

    def add_dangerzone(self, tile, enemies, game, max_level, img=None):
        cx, cy = self.get_tile_center(tile)
        event = DangerZone((cx, cy), enemies, game, max_level, img=img)
        self.add_event(tile, event)

    def get_neighbours(self, tile):
        try:
            top = self.get_tile(tile.layer, tile.x, tile.y - 1)
        except IndexError:
            top = None

        try:
            bottom = self.get_tile(tile.layer, tile.x, tile.y + 1)
        except IndexError:
            bottom = None

        try:
            left = self.get_tile(tile.layer, tile.x - 1, tile.y)
        except IndexError:
            left = None

        try:
            right = self.get_tile(tile.layer, tile.x + 1, tile.y)
        except IndexError:
            right = None

        return top, bottom, left, right

    def check_if_looking_at(self, tile):
        top, bottom, left, right = self.get_neighbours(tile)
        try:
            if top.rect.collidepoint(self.game.PLAYER.get_pos()) and self.game.PLAYER.get_orient() == 2:
                return True
        except AttributeError:
            pass

        try:
            if bottom.rect.collidepoint(self.game.PLAYER.get_pos()) and self.game.PLAYER.get_orient() == 0:
                return True
        except AttributeError:
            pass

        try:
            if left.rect.collidepoint(self.game.PLAYER.get_pos()) and self.game.PLAYER.get_orient() == 1:
                return True
        except AttributeError:
            pass

        try:
            if right.rect.collidepoint(self.game.PLAYER.get_pos()) and self.game.PLAYER.get_orient() == 3:
                return True
        except AttributeError:
            pass

        return False


class TestMap(Map):

    def __init__(self, game):
        super().__init__(game)
        self.load_map("testmap")
        self.enemies = [self.game.spawn_leafwing(), self.game.spawn_flametorch()]

    def bake_events(self):
        tile = self.get_tile(0, 0, 19)
        self.add_teleport(tile, (0, 1), TestMap2(self.game))
        for layer in self.layers:
            for tile in layer:
                if tile.danger_zone:
                    self.add_dangerzone(tile, self.enemies, self.game, 5, None)
        self.baked = 1


class TestMap2(Map):

    def __init__(self, game):
        super().__init__(game)
        self.load_map("testmap2")
        self.enemies = [self.game.spawn_aquashade(), self.game.spawn_leafwing()]
    
    def bake_events(self):
        tile = self.get_tile(0, 0, 0)
        self.add_teleport(tile, (0, 18), TestMap(self.game))
        tile = self.get_tile(0, 0, 7)
        self.add_teleport(tile, (28, 1), Dockersville(self.game))
        for layer in self.layers:
            for tile in layer:
                if tile.danger_zone:
                    self.add_dangerzone(tile, self.enemies, self.game, 5, None)
        self.baked = 1


class Dockersville(Map):

    def __init__(self, game):
        super().__init__(game)
        self.load_map("dockersville")

    def bake_events(self):
        tile = self.get_tile(0, 29, 1)
        self.add_teleport(tile, (1, 7), TestMap2(self.game))
        tile = self.get_tile(0, 18, 5)
        self.add_teleport(tile, (8, 13), House(self.game), self.game.ASSETS["MAP_DOOR"])
        tile = self.get_tile(0, 25, 7)
        self.add_dialogue(tile, self.game.LAVENDER.get_image(), self.game.LAVENDER)
        tile = self.get_tile(0, 7, 7)
        self.add_dialogue(tile, self.game.LOCKEDDOOR.get_image(), self.game.LOCKEDDOOR)
        tile = self.get_tile(0, 21, 14)
        self.add_teleport(tile, (7, 13), CreatureCenter(self.game), self.game.ASSETS["MAP_DOOR"])
        self.baked = 1


class House(Map):

    def __init__(self, game):
        super().__init__(game)
        self.load_map(mapname="house")

    def bake_events(self):
        tile = self.get_tile(0, 8, 15)
        self.add_teleport(tile, (18, 6), Dockersville(self.game))

        tile = self.get_tile(0, 7, 3)
        self.add_dialogue(tile, img=self.game.BRIGITTE.get_image(), npc=self.game.BRIGITTE)
        tile = self.get_tile(0, 13, 12)
        self.add_shop(tile, self.game.TRADER.get_image(), self.game.TRADER)
        self.baked = 1


class CreatureCenter(Map):
    def __init__(self, game):
        super().__init__(game)
        self.load_map("creature_center")

    def bake_events(self):
        tile = self.get_tile(0, 7, 14)
        self.add_teleport(tile, (21, 15), Dockersville(self.game))
        tile = self.get_tile(0, 7, 5)
        self.add_cure(tile, img=None, npc=self.game.HEALER)
        tile = self.get_tile(0, 7, 4)
        self.add_cure(tile, img=self.game.HEALER.get_image(), npc=self.game.HEALER)
        self.baked = 1
