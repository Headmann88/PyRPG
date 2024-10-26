import pygame
import sys
import random
import time
import json
import os
from collections import defaultdict
import itertools

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 32
FPS = 60
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# New Item class
class Item:
    def __init__(self, name, effect, symbol, color, quantity=1):
        self.name = name
        self.effect = effect
        self.symbol = symbol
        self.color = color
        self.quantity = quantity

    def use(self, character):
        if self.effect == 'heal':
            heal_amount = 20
            character.health = min(character.health + heal_amount, 100)
            print(f"{character.__class__.__name__} used {self.name} and healed for {heal_amount} HP.")
        # Add more effects as needed

# New Inventory class
class Inventory:
    def __init__(self, size=8):
        self.items = [None] * size
        self.size = size

    def add_item(self, item):
        for i, existing_item in enumerate(self.items):
            if existing_item and existing_item.name == item.name:
                existing_item.quantity += item.quantity
                return True
        for i in range(self.size):
            if self.items[i] is None:
                self.items[i] = item
                return True
        return False  # Inventory is full

    def remove_item(self, index):
        if 0 <= index < self.size and self.items[index]:
            item = self.items[index]
            self.items[index] = None
            return item
        return None

    def get_item_by_name(self, name):
        for item in self.items:
            if item and item.name.lower() == name.lower():
                return item
        return None

# Update Character class to include inventory
class Character:
    def __init__(self, pos, health):
        self.pos = list(pos)
        self.health = health
        self.inventory = Inventory()

    def move(self, direction, game_map):
        dx, dy = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}.get(direction, (0, 0))
        new_pos = [self.pos[0] + dx, self.pos[1] + dy]
        if self.is_valid_move(new_pos, game_map):
            self.pos = new_pos

    def is_valid_move(self, new_pos, game_map):
        x, y = new_pos
        return (0 <= x < len(game_map[0]) and 
                0 <= y < len(game_map) and 
                game_map[y][x] != 'W' and
                game_map[y][x] != 'D')  # Add 'D' to collision check

    def use_item(self, item_name):
        item = self.inventory.get_item_by_name(item_name)
        if item:
            index = self.inventory.items.index(item)
            self.inventory.remove_item(index)
            item.use(self)
        else:
            print(f"{self.__class__.__name__} doesn't have {item_name}.")

# Update Player class
class Player(Character):
    def __init__(self, start_pos):
        super().__init__(start_pos, health=100)
        self.level = 1
        self.exp = 0
        self.exp_next_level = 100
        self.speed = 5

# Update Enemy class
class Enemy(Character):
    def __init__(self, name, pos, health, speed, damage_range):
        super().__init__(pos, health)
        self.name = name
        self.speed = speed
        self.damage_range = damage_range

    def attack(self):
        return random.randint(*self.damage_range)

    def random_move(self, game_map):
        direction = random.choice(['left', 'right', 'up', 'down'])
        self.move(direction, game_map)

# Create specific enemy types
class Goblin(Enemy):
    def __init__(self, pos):
        super().__init__("Goblin", pos, health=20, speed=4, damage_range=(2, 6))

class Orc(Enemy):
    def __init__(self, pos):
        super().__init__("Orc", pos, health=35, speed=3, damage_range=(4, 8))

class Skeleton(Enemy):
    def __init__(self, pos):
        super().__init__("Skeleton", pos, health=15, speed=5, damage_range=(3, 7))

class Dragon(Enemy):
    def __init__(self, pos):
        super().__init__("Dragon", pos, health=100, speed=7, damage_range=(10, 20))

# Update Game class
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('PyRPG 1.4')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

        self.maps = self.load_maps()
        self.current_map_index = 0
        self.game_map = self.maps[self.current_map_index]['layout']
        self.items_on_map = defaultdict(list)
        self.load_items()
        self.player = Player(self.find_player_start())
        self.enemies = self.create_enemies()

        self.running = True
        self.game_started = False
        self.in_battle = False
        self.current_enemy = None
        self.battle_options = ["Attack", "Defend", "Run"]
        self.selected_option = 0
        self.battle_messages = []
        self.encounter_message = None
        self.encounter_message_time = 0
        self.player_dead = False
        self.show_inventory = False
        self.inventory_selected_index = 0
        self.pickup_message = None
        self.pickup_message_time = 0
        self.messages = []
        self.message_duration = 2  # seconds
        self.show_action_menu = False
        self.action_options = ["Use", "Take", "Look around", "Remember"]
        self.action_selected_index = 0
        self.entity_display_index = 0
        self.last_entity_switch_time = 0
        self.show_battle_log = False
        self.battle_log = []  # Store all battle messages here

    def load_maps(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        maps_path = os.path.join(script_dir, 'maps.json')
        try:
            with open(maps_path, 'r') as f:
                data = json.load(f)
                maps = data['maps']
                for map_data in maps:
                    map_data['layout'] = [list(row) for row in map_data['layout']]
                return maps
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading maps: {e}")
            sys.exit(1)

    def find_player_start(self):
        for y, row in enumerate(self.game_map):
            if 'P' in row:
                return [row.index('P'), y]
        return [1, 1]  # Default position if 'P' is not found

    def create_enemies(self):
        enemies = []
        for y, row in enumerate(self.game_map):
            for x, cell in enumerate(row):
                if cell == 'g':
                    enemies.append(Goblin((x, y)))
                elif cell == 'o':
                    enemies.append(Orc((x, y)))
                elif cell == 's':
                    enemies.append(Skeleton((x, y)))
                elif cell == 'd':
                    enemies.append(Dragon((x, y)))
        return enemies

    def load_items(self):
        for y, row in enumerate(self.game_map):
            for x, cell in enumerate(row):
                if cell == 'H':
                    item = Item("Health Potion", "heal", 'H', RED)
                    self.items_on_map[(x, y)].append(item)
                    self.game_map[y][x] = ' '

    def render_map(self):
        map_width = len(self.game_map[0]) * TILE_SIZE
        map_height = len(self.game_map) * TILE_SIZE
        start_x = (SCREEN_WIDTH - map_width) // 2
        start_y = (SCREEN_HEIGHT - map_height) // 2

        for y, row in enumerate(self.game_map):
            for x, cell in enumerate(row):
                color = {
                    'W': (128, 128, 128),
                    'D': (139, 69, 19),
                }.get(cell, BLACK)
                pygame.draw.rect(self.screen, color, 
                                 (start_x + x * TILE_SIZE, start_y + y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Render entities (player, enemies, items) with loop display
        current_time = time.time()
        if current_time - self.last_entity_switch_time > 1:
            self.entity_display_index += 1
            self.last_entity_switch_time = current_time

        for y, row in enumerate(self.game_map):
            for x, cell in enumerate(row):
                pos = (x, y)
                entities = []
                if self.player.pos == list(pos):
                    entities.append(('P', RED))
                entities.extend((enemy.name[0], GREEN) for enemy in self.enemies if enemy.pos == list(pos))
                entities.extend((item.symbol, item.color) for item in self.items_on_map.get(pos, []))

                if entities:
                    entity_index = self.entity_display_index % len(entities)
                    symbol, color = entities[entity_index]
                    pygame.draw.rect(self.screen, color, 
                                     (start_x + x * TILE_SIZE, 
                                      start_y + y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                    text = self.small_font.render(symbol, True, WHITE)
                    text_rect = text.get_rect(center=(start_x + x * TILE_SIZE + TILE_SIZE // 2, 
                                                      start_y + y * TILE_SIZE + TILE_SIZE // 2))
                    self.screen.blit(text, text_rect)

        # Render pickup message
        if self.pickup_message:
            current_time = time.time()
            if current_time - self.pickup_message_time < 2:
                alpha = int(255 * (1 - (current_time - self.pickup_message_time) / 2))
                pickup_text = self.font.render(self.pickup_message, True, WHITE)
                pickup_text.set_alpha(alpha)
                text_rect = pickup_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
                self.screen.blit(pickup_text, text_rect)
            else:
                self.pickup_message = None

        # Render encounter message
        if self.encounter_message:
            current_time = time.time()
            if current_time - self.encounter_message_time < 2:
                alpha = int(255 * (1 - (current_time - self.encounter_message_time) / 2))
                encounter_text = self.font.render(self.encounter_message, True, WHITE)
                encounter_text.set_alpha(alpha)
                text_rect = encounter_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
                self.screen.blit(encounter_text, text_rect)
            else:
                self.encounter_message = None

        self.render_messages()

    def render_battle_screen(self):
        self.screen.fill(BLACK)
        player_text = self.font.render(f"Player (HP: {self.player.health})", True, WHITE)
        enemy_text = self.font.render(f"{self.current_enemy.name} (HP: {self.current_enemy.health})", True, RED)
        self.screen.blit(player_text, (50, 50))
        self.screen.blit(enemy_text, (SCREEN_WIDTH - 250, 50))

        for i, option in enumerate(self.battle_options):
            color = YELLOW if i == self.selected_option else WHITE
            option_text = self.font.render(option, True, color)
            self.screen.blit(option_text, (50, 300 + i * 50))

        # Render battle messages in a chat-like cell
        for i, message in enumerate(self.battle_messages[-5:]):
            message_text = self.small_font.render(message, True, (200, 200, 200))
            self.screen.blit(message_text, (50, SCREEN_HEIGHT - 150 + i * 30))

        if self.encounter_message:
            current_time = time.time()
            if current_time - self.encounter_message_time < 2:
                alpha = int(255 * (1 - (current_time - self.encounter_message_time) / 2))
                encounter_text = self.font.render(self.encounter_message, True, WHITE)
                encounter_text.set_alpha(alpha)
                text_rect = encounter_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
                self.screen.blit(encounter_text, text_rect)
            else:
                self.encounter_message = None

    def render_inventory(self):
        inventory_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        inventory_surface.set_alpha(200)
        inventory_surface.fill(BLACK)
        self.screen.blit(inventory_surface, (0, 0))

        # Render player stats
        stats_text = [
            f"Health: {self.player.health}/100",
            f"Level: {self.player.level}",
            f"EXP: {self.player.exp}/{self.player.exp_next_level}"
        ]
        for i, text in enumerate(stats_text):
            stat_surface = self.small_font.render(text, True, WHITE)
            self.screen.blit(stat_surface, (20, 20 + i * 30))

        # Inventory title
        inventory_text = self.font.render("Inventory", True, WHITE)
        self.screen.blit(inventory_text, (SCREEN_WIDTH // 2 - inventory_text.get_width() // 2, 100))

        # Render inventory grid
        start_x = (SCREEN_WIDTH - (4 * TILE_SIZE + 3 * 10)) // 2
        start_y = 150  # Moved down to make room for stats

        for i in range(8):
            x = start_x + (i % 4) * (TILE_SIZE + 10)
            y = start_y + (i // 4) * (TILE_SIZE + 10)
            
            # Highlight selected item
            if i == self.inventory_selected_index:
                pygame.draw.rect(self.screen, YELLOW, (x - 2, y - 2, TILE_SIZE + 4, TILE_SIZE + 4), 2)
            
            pygame.draw.rect(self.screen, WHITE, (x, y, TILE_SIZE, TILE_SIZE), 2)
            
            item = self.player.inventory.items[i]
            if item:
                pygame.draw.rect(self.screen, item.color, (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4))
                text = self.small_font.render(item.symbol, True, WHITE)
                text_rect = text.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
                self.screen.blit(text, text_rect)

        # Display item info
        selected_item = self.player.inventory.items[self.inventory_selected_index]
        if selected_item:
            item_info = f"{selected_item.name} - Press 'E' to use, 'D' to discard"
        else:
            item_info = "Empty slot"
        info_text = self.small_font.render(item_info, True, WHITE)
        self.screen.blit(info_text, (SCREEN_WIDTH // 2 - info_text.get_width() // 2, start_y + 2 * TILE_SIZE + 2 * 10))

        # Display controls info
        controls_text = self.small_font.render("Arrow keys to navigate, 'I' to close inventory", True, WHITE)
        self.screen.blit(controls_text, (SCREEN_WIDTH // 2 - controls_text.get_width() // 2, SCREEN_HEIGHT - 40))

    def render_action_menu(self):
        action_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        action_surface.set_alpha(200)
        action_surface.fill(BLACK)
        self.screen.blit(action_surface, (0, 0))

        # Render action menu title
        action_text = self.font.render("Actions", True, WHITE)
        self.screen.blit(action_text, (SCREEN_WIDTH // 2 - action_text.get_width() // 2, 100))

        # Render action options
        for i, option in enumerate(self.action_options):
            color = YELLOW if i == self.action_selected_index else WHITE
            option_text = self.font.render(option, True, color)
            self.screen.blit(option_text, (SCREEN_WIDTH // 2 - option_text.get_width() // 2, 200 + i * 50))

        # Display controls info
        controls_text = self.small_font.render("Arrow keys to navigate, ENTER to select, 'E' to close", True, WHITE)
        self.screen.blit(controls_text, (SCREEN_WIDTH // 2 - controls_text.get_width() // 2, SCREEN_HEIGHT - 40))

    def render_battle_log(self):
        log_surface = pygame.Surface((SCREEN_WIDTH - 100, SCREEN_HEIGHT - 100))
        log_surface.fill(BLACK)
        pygame.draw.rect(log_surface, WHITE, log_surface.get_rect(), 2)
        pygame.draw.rect(log_surface, YELLOW, log_surface.get_rect().inflate(-4, -4), 2)

        title = self.font.render("Battle Log", True, WHITE)
        log_surface.blit(title, (20, 20))

        # Calculate available space for messages
        available_height = log_surface.get_height() - 120  # 60 for top margin, 60 for bottom margin
        max_messages = available_height // 30  # 30 is the height of each message line

        # Get the last 'max_messages' entries from the battle log
        displayed_messages = self.battle_log[-max_messages:]

        for i, message in enumerate(displayed_messages):
            text = self.small_font.render(message, True, WHITE)
            log_surface.blit(text, (20, 60 + i * 30))

        close_text = self.small_font.render("Press ESC to close", True, WHITE)
        log_surface.blit(close_text, (20, log_surface.get_height() - 40))

        self.screen.blit(log_surface, (50, 50))

    def handle_battle_input(self, event):
        if event.key == pygame.K_UP:
            self.selected_option = (self.selected_option - 1) % len(self.battle_options)
        elif event.key == pygame.K_DOWN:
            self.selected_option = (self.selected_option + 1) % len(self.battle_options)
        elif event.key == pygame.K_RETURN:
            action = self.battle_options[self.selected_option]
            if action == "Attack":
                self.battle_attack()
            elif action == "Defend":
                self.battle_defend()
            elif action == "Run":
                self.battle_run()

    def battle_attack(self):
        player_damage = random.randint(5, 15)
        self.current_enemy.health -= player_damage
        self.add_battle_message(f"You dealt {player_damage} damage to {self.current_enemy.name}!")
        
        if self.current_enemy.health <= 0:
            self.add_battle_message(f"You defeated the {self.current_enemy.name}!")
            self.enemies.remove(self.current_enemy)
            self.game_map[self.current_enemy.pos[1]][self.current_enemy.pos[0]] = ' '
            self.in_battle = False
            self.current_enemy = None
        else:
            self.enemy_attack()

    def battle_defend(self):
        self.add_battle_message("You defended against the enemy's attack!")
        self.enemy_attack(damage_reduction=True)

    def battle_run(self):
        if self.current_enemy.speed > self.player.speed:
            self.add_battle_message("You can't run away! The enemy is faster than you.")
            self.enemy_attack()
        else:
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(directions)
            for dx, dy in directions:
                new_x, new_y = self.player.pos[0] + dx, self.player.pos[1] + dy
                if self.player.is_valid_move([new_x, new_y], self.game_map):
                    self.player.pos = [new_x, new_y]
                    self.add_battle_message("You successfully ran away!")
                    self.in_battle = False
                    self.current_enemy = None
                    return
            self.add_battle_message("You couldn't find a way to escape!")
            self.enemy_attack()

    def enemy_attack(self, damage_reduction=False):
        enemy_damage = self.current_enemy.attack()
        if damage_reduction:
            enemy_damage = max(1, enemy_damage // 2)
        self.player.health -= enemy_damage
        self.add_battle_message(f"{self.current_enemy.name} dealt {enemy_damage} damage to you!")
        
        if self.player.health <= 0:
            self.player_dead = True
            self.in_battle = False

    def handle_inventory_input(self, event):
        if event.key == pygame.K_LEFT:
            self.inventory_selected_index = max(0, self.inventory_selected_index - 1)
        elif event.key == pygame.K_RIGHT:
            self.inventory_selected_index = min(7, self.inventory_selected_index + 1)
        elif event.key == pygame.K_UP:
            self.inventory_selected_index = max(0, self.inventory_selected_index - 4)
        elif event.key == pygame.K_DOWN:
            self.inventory_selected_index = min(7, self.inventory_selected_index + 4)
        elif event.key == pygame.K_e:
            selected_item = self.player.inventory.items[self.inventory_selected_index]
            if selected_item:
                self.player.use_item(selected_item.name)
                self.add_message(f"Used {selected_item.name}")
        elif event.key == pygame.K_d:
            discarded_item = self.player.inventory.remove_item(self.inventory_selected_index)
            if discarded_item:
                self.add_message(f"Discarded {discarded_item.name}")

    def handle_action_menu_input(self, event):
        if event.key == pygame.K_UP:
            self.action_selected_index = (self.action_selected_index - 1) % len(self.action_options)
        elif event.key == pygame.K_DOWN:
            self.action_selected_index = (self.action_selected_index + 1) % len(self.action_options)
        elif event.key == pygame.K_RETURN:
            action = self.action_options[self.action_selected_index]
            if action == "Use":
                self.use_object()
            elif action == "Take":
                self.take_item()
            elif action == "Look around":
                self.look_around()
            elif action == "Remember":
                self.show_battle_log = True
            self.show_action_menu = False

    def use_object(self):
        player_x, player_y = self.player.pos
        adjacent_cells = [
            (player_x - 1, player_y),
            (player_x + 1, player_y),
            (player_x, player_y - 1),
            (player_x, player_y + 1)
        ]

        for x, y in adjacent_cells:
            if 0 <= x < len(self.game_map[0]) and 0 <= y < len(self.game_map):
                cell = self.game_map[y][x]
                if cell == 'D':
                    self.add_message("You opened the door.")
                    self.transition_to_next_map()
                    return
                elif cell == 'B':  # 'B' for button
                    self.add_message("You pressed the button.")
                    # Add button functionality here
                    return
                elif cell == 'S':  # 'S' for switch
                    self.add_message("You flipped the switch.")
                    # Add switch functionality here
                    return

        self.add_message("There's nothing to use here.")

    def transition_to_next_map(self):
        self.current_map_index = (self.current_map_index + 1) % len(self.maps)
        self.game_map = self.maps[self.current_map_index]['layout']
        self.player.pos = self.find_player_start()
        self.enemies = self.create_enemies()
        self.load_items()
        self.add_message("You entered a new area.")

    def take_item(self):
        player_pos = tuple(self.player.pos)
        if player_pos in self.items_on_map and self.items_on_map[player_pos]:
            item = self.items_on_map[player_pos][0]
            if self.player.inventory.add_item(item):
                self.items_on_map[player_pos].pop(0)
                if not self.items_on_map[player_pos]:
                    del self.items_on_map[player_pos]
                self.add_message(f"Picked up {item.name}")
            else:
                self.add_message("Inventory is full")

    def look_around(self):
        player_pos = tuple(self.player.pos)
        items = self.items_on_map.get(player_pos, [])
        enemies = [enemy for enemy in self.enemies if tuple(enemy.pos) == player_pos]
        
        if not items and not enemies:
            self.add_message("There's nothing interesting here.")
        else:
            if items:
                item_names = ", ".join(f"{item.name} (x{item.quantity})" for item in items)
                self.add_message(f"Items here: {item_names}")
            if enemies:
                enemy_names = ", ".join(enemy.name for enemy in enemies)
                self.add_message(f"Enemies here: {enemy_names}")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.game_started = True
                if event.key == pygame.K_q:
                    self.running = False
                if event.key == pygame.K_i and not self.show_action_menu and not self.show_battle_log:
                    self.show_inventory = not self.show_inventory
                    self.inventory_selected_index = 0
                if event.key == pygame.K_e and not self.show_inventory and not self.show_battle_log:
                    self.show_action_menu = not self.show_action_menu
                    self.action_selected_index = 0
                if self.game_started:
                    if self.show_inventory:
                        self.handle_inventory_input(event)
                    elif self.show_action_menu:
                        self.handle_action_menu_input(event)
                    elif self.show_battle_log:
                        if event.key == pygame.K_ESCAPE:
                            self.show_battle_log = False
                    elif self.in_battle:
                        self.handle_battle_input(event)
                    else:
                        self.handle_movement(event)

        if self.game_started and not self.in_battle and not self.show_inventory and not self.show_action_menu and not self.show_battle_log:
            self.check_for_encounter()
            self.check_for_map_transition()

    def handle_movement(self, event):
        direction = {
            pygame.K_a: 'left',
            pygame.K_d: 'right',
            pygame.K_w: 'up',
            pygame.K_s: 'down'
        }.get(event.key)
        
        if direction:
            old_pos = self.player.pos.copy()
            self.player.move(direction, self.game_map)
            if self.player.pos != old_pos:  # Only check for encounters if the player actually moved
                self.check_for_encounter()
            for enemy in self.enemies:
                enemy.random_move(self.game_map)

    def check_for_encounter(self):
        player_x, player_y = self.player.pos
        for enemy in self.enemies:
            enemy_x, enemy_y = enemy.pos
            if abs(player_x - enemy_x) <= 1 and abs(player_y - enemy_y) <= 1:
                self.add_message(f"You encountered a {enemy.name}!")
                self.in_battle = True
                self.current_enemy = enemy
                self.selected_option = 0
                break

    def check_for_map_transition(self):
        # Remove this method or leave it empty
        pass

    def run(self):
        while self.running:
            self.handle_events()
            self.screen.fill(BLACK)
            
            if not self.game_started:
                self.render_start_screen()
            elif self.in_battle:
                self.render_battle_screen()
            elif self.player_dead:
                self.render_death_screen()
            else:
                self.render_map()
                if self.show_inventory:
                    self.render_inventory()
                elif self.show_action_menu:
                    self.render_action_menu()
                elif self.show_battle_log:
                    self.render_battle_log()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def render_start_screen(self):
        title_text = self.font.render("Welcome to PyRPG", True, WHITE)
        start_text = self.small_font.render("Press ENTER to start", True, WHITE)
        self.screen.blit(title_text, title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)))
        self.screen.blit(start_text, start_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3)))

    def render_death_screen(self):
        death_text = self.font.render("You Died", True, RED)
        restart_text = self.small_font.render("Press R to restart", True, WHITE)
        self.screen.blit(death_text, death_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)))
        self.screen.blit(restart_text, restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3)))

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset_game()

    def reset_game(self):
        self.current_map_index = 0
        self.game_map = self.maps[self.current_map_index]['layout']
        self.player = Player(self.find_player_start())
        self.enemies = self.create_enemies()
        self.load_items()
        self.player_dead = False
        self.in_battle = False
        self.current_enemy = None
        self.battle_messages = []
        self.game_started = False

    def add_message(self, message):
        self.messages.append((message, time.time()))

    def add_battle_message(self, message):
        self.battle_messages.append(message)
        self.battle_log.append(message)  # Add to the persistent battle log
        if len(self.battle_messages) > 5:
            self.battle_messages.pop(0)

    def render_messages(self):
        current_time = time.time()
        self.messages = [(msg, t) for msg, t in self.messages if current_time - t < self.message_duration]
        
        for i, (message, timestamp) in enumerate(self.messages):
            alpha = int(255 * (1 - (current_time - timestamp) / self.message_duration))
            message_text = self.font.render(message, True, WHITE)
            message_text.set_alpha(alpha)
            text_rect = message_text.get_rect(center=(SCREEN_WIDTH // 2, 100 + i * 40))
            self.screen.blit(message_text, text_rect)

if __name__ == '__main__':
    game = Game()
    game.run()
