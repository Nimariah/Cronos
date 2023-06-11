import pygame
from pathlib import Path
from time import time

# Custom made modules
import map 
import person
import statemanager
import inventory


class Game:
    
    def __init__(self):
        
        pygame.init()
        self.CLOCK = pygame.time.Clock()
        screen_info = pygame.display.get_desktop_sizes()
        self.SCR_WIDTH, self.SCR_HEIGHT = screen_info[0][0], screen_info[0][1]
        self.SCREEN = pygame.display.set_mode((self.SCR_WIDTH, self.SCR_HEIGHT)) 
        self._running = True
                
        self.game_state = "MENU"
        self.STATE_MANAGER = statemanager.State_manager(self)
        self.STATE_MANAGER.change_state(3)

        self.FUNC_KEY_COOLDOWN = 0.2
        self.func_key_used = time()
        self.current_time = self.func_key_used

        self.scale = 1

        self.map_surface = pygame.Surface((1, 1))
        self.map = map.Test_map(self)

        self.FONT = pygame.freetype.Font(Path.cwd() / Path("fonts") / Path ("VCR_OSD_MONO_1.001.ttf"), 16)
        self.ASSETS = {}
        self.PATH_TO_ASSETS = Path(Path.cwd()) / Path("assets")

        self.NPCS = {
            "BRIGITTE": person.Brigitte,
            "THOMAS": person.Thomas
        }
        
        for asset in self.PATH_TO_ASSETS.iterdir():
            if asset.is_file():
                filename = asset.name[:-4]
                print(filename)
                self.ASSETS[filename.upper()] = pygame.image.load(asset).convert_alpha()
            
        self.PLAYER = person.Player(self.ASSETS["CHAR_BLUE_EYES_PERSON"], self.SCR_WIDTH // 2, self.SCR_HEIGHT // 2, [self.ASSETS["CHAR_JEANS"], self.ASSETS["CHAR_STRIPED_SHIRT"]])
        self.PLAYER.read_scale(self.scale)
        
        self.INVENTORY = inventory.Inventory(self.PLAYER, self.ASSETS)
        
        self.INVENTORY.add_item("Candy")
        self.INVENTORY.add_item("Small HP Restore")
        self.INVENTORY.add_item("Small SP Restore")
        
        self.NUMBERED_ASSETS = {}
        count = 0
        
        for asset in self.ASSETS.values():
            self.NUMBERED_ASSETS[count] = asset
            count += 1

        self.PLAYER.set_pos((48, 192))
        self.main()

    def main(self):
        
        while self._running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.exit

            match self.game_state:
                
                case "TEST":
                    self.map_state()
                    
                case "MENU":
                    self.menu_state()
                    
                case "INVENTORY":
                    self.inventory_state()
                    
                case "MAP":
                    self.map_state()
                    
                case _:
                    self.map_state()
            
            self.flip_n_tick()
    
    def map_state(self):
        
        # Input
        if not self.map.baked:
            self.map.bake_events()
        
        self.current_time = time()
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_ESCAPE] and self.current_time - self.func_key_used > self.FUNC_KEY_COOLDOWN:
            pygame.quit()
            self.func_key_used = self.current_time
        
        if keys[pygame.K_i] and self.current_time - self.func_key_used > self.FUNC_KEY_COOLDOWN:
            self.STATE_MANAGER.change_state(2)
            self.func_key_used = self.current_time
        
        self.PLAYER.update(keys, self)
        self.map.update(keys, self)
        
        # Draw
        self.map_surface.fill((0, 0, 0))
        self.SCREEN.fill((0, 0, 0))
        self.map.draw_map()
            
    def inventory_state(self):
        
        # Input
        self.current_time = time()
        keys = pygame.key.get_pressed()    
        
        if (keys[pygame.K_i] or keys[pygame.K_ESCAPE]) and self.current_time - self.func_key_used > self.FUNC_KEY_COOLDOWN:
            self.STATE_MANAGER.change_state(3)
            self.func_key_used = self.current_time
        self.INVENTORY.update(keys)
        
        # Draw    
        self.SCREEN.fill((0, 0, 0))
        self.INVENTORY.draw(self.FONT, self.SCREEN)

    def menu_state(self):
        pass
    
    def flip_n_tick(self, fps=60):
        pygame.display.flip()
        self.CLOCK.tick(fps)
