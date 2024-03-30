"""
CHIP-8 Specifications:
- Direct access up to 4KB (4,096 bytes) of memory
- 64x32 pixel monochrome display
- Program counter (PC), points to the current instruction in memory
- Index register (I), used to point to locations in memory
- Stack, used to remember the current location before a jump is performed
- 8-bit delay timer, which is decrementing at 60Hz (60 times per second) until it reaches 0
- 8-bit sound timer, which functions like the delay timer, but gives opff a beeping sound as long as it's not zero
- 16 8-bit data registers (V0-VF), used to store data
- - VF register is used as a flag for some instructions

"""

import pygame as pg
import random, sys, time, os
import winsound

rom_path = "roms/pong.ch8"

class Chip8:
    def __init__(self):
        self.memory = [0] * 4096 # 4KB of memory
        self.v = [0] * 16 # 16 8-bit data registers
        self.i = 0
        self.pc = 0x200
        self.stack = []
        self.sp = 0

        self.delay_timer = 0
        self.sound_timer = 0

        self.display = [0] * 64 * 32 # can be 0 or 1 (off or on)
        self.keys = [0] * 16

        self.fontset = [
            0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
            0x20, 0x60, 0x20, 0x20, 0x70, # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
            0x90, 0x90, 0xF0, 0x10, 0x10, # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
            0xF0, 0x10, 0x20, 0x40, 0x40, # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90, # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
            0xF0, 0x80, 0x80, 0x80, 0xF0, # C
            0xE0, 0x90, 0x90, 0x90, 0xE0, # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
            0xF0, 0x80, 0xF0, 0x80, 0x80  # F
        ]

        self.opcode = 0
        self.running = True

        self.screen = pg.display.set_mode((64*10, 32*10))
        pg.display.set_caption("CHIP-8 Emulator")
        self.clock = pg.time.Clock()


    def load_rom(self, path):
        with open(path, "rb") as f:
            data = f.read()
            for i in range(len(data)):
                self.memory[0x200 + i] = data[i]

    def emulate_cycle(self):
        # Fetch opcode
        self.opcode = self.memory[self.pc] << 8 | self.memory[self.pc + 1]

        # Decode opcode
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4

        if self.opcode == 0x00E0: # Clear the display (00E0)
            self.display = [0] * 64 * 32
            self.pc += 2
        elif self.opcode == 0x00EE: # Return from a subroutine (00EE)
            self.pc = self.stack.pop()
            self.pc += 2
        elif (self.opcode & 0xF000) == 0x1000: # Jump to address NNN (1NNN)
            self.pc = self.opcode & 0x0FFF
        elif (self.opcode & 0xF000) == 0x2000: # Call subroutine at NNN (2NNN)
            self.stack.append(self.pc)
            self.pc = self.opcode & 0x0FFF 
        elif (self.opcode & 0xF000) == 0x3000: # Skip next instruction if Vx == NN (3XNN)
            if self.v[x] == self.opcode & 0x00FF:
                self.pc += 4
            else:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0x4000: # Skip next instruction if Vx != NN (4XNN)
            if self.v[x] != self.opcode & 0x00FF:
                self.pc += 4
            else:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0x5000: # Skip next instruction if Vx == Vy (5XY0)
            if self.v[x] == self.v[y]:
                self.pc += 4
            else:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0x6000: # Set Vx = NN (6XNN)
            self.v[x] = self.opcode & 0x00FF
            self.pc += 2
        elif (self.opcode & 0xF000) == 0x7000: # Set Vx = Vx + NN (7XNN)
            self.v[x] += self.opcode & 0x00FF
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8000: # Set Vx = Vy (8XY0)
            self.v[x] = self.v[y]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8001: # Set Vx = Vx OR Vy (8XY1)
            self.v[x] |= self.v[y]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8002: # Set Vx = Vx AND Vy (8XY2)
            self.v[x] &= self.v[y]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8003: # Set Vx = Vx XOR Vy (8XY3)
            self.v[x] ^= self.v[y]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8004: # Set Vx = Vx + Vy, set VF = carry (8XY4)
            self.v[0xF] = 1 if self.v[x] + self.v[y] > 0xFF else 0
            self.v[x] += self.v[y]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8005: # Set Vx = Vx - Vy, set VF = NOT borrow (8XY5)
            self.v[0xF] = 0 if self.v[x] > self.v[y] else 1
            self.v[x] -= self.v[y]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8006: # Set Vx = Vx SHR 1 (8XY6)
            self.v[0xF] = self.v[x] & 0x1
            self.v[x] >>= 1
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x8007: # Set Vx = Vy - Vx, set VF = NOT borrow (8XY7)
            self.v[0xF] = 0 if self.v[y] > self.v[x] else 1
            self.v[x] = self.v[y] - self.v[x]
            self.pc += 2
        elif (self.opcode & 0xF00F) == 0x800E: # Set Vx = Vx SHL 1 (8XYE)
            self.v[0xF] = self.v[x] >> 7
            self.v[x] <<= 1
            self.pc += 2
        elif (self.opcode & 0xF000) == 0x9000: # Skip next instruction if Vx != Vy (9XY0)
            if self.v[x] != self.v[y]:
                self.pc += 4
            else:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0xA000: # Set I = NNN (ANNN)
            self.i = self.opcode & 0x0FFF
            self.pc += 2
        elif (self.opcode & 0xF000) == 0xB000: # Jump to location NNN + V0 (BNNN)
            self.pc = (self.opcode & 0x0FFF) + self.v[0]
        elif (self.opcode & 0xF000) == 0xC000: # Set Vx = random byte AND NN (CXNN)
            self.v[x] = random.randint(0, 255) & (self.opcode & 0x00FF)
            self.pc += 2
        elif (self.opcode & 0xF000) == 0xD000: # Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision (DXYN)
            x = self.v[x]
            y = self.v[y]
            height = self.opcode & 0x000F
            self.v[0xF] = 0

            for yline in range(height):
                pixel = self.memory[self.i + yline]
                for xline in range(8):
                    if (pixel & (0x80 >> xline)) != 0:
                        if self.display[(x + xline + ((y + yline) * 64)) % (64 * 32)] == 1:
                            self.v[0xF] = 1
                        if x + xline + ((y + yline) * 64) >= 64 * 32:
                            continue
                        self.display[x + xline + ((y + yline) * 64)] ^= 1

            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xE09E: # Skip next instruction if key with the value of Vx is pressed (EX9E)
            if self.keys[self.v[x]] == 1:
                self.pc += 4
            else:
                self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xE0A1: # Skip next instruction if key with the value of Vx is not pressed (EXA1)
            if self.keys[self.v[x]] == 0:
                self.pc += 4
            else:
                self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF007: # Set Vx = delay timer value (FX07)
            self.v[x] = self.delay_timer
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF00A: # Wait for a key press, store the value of the key in Vx (FX0A)
            key_pressed = False
            for i in range(16):
                if self.keys[i] == 1:
                    self.v[x] = i
                    key_pressed = True
            if not key_pressed:
                return
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF015: # Set delay timer = Vx (FX15)
            self.delay_timer = self.v[x]
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF018: # Set sound timer = Vx (FX18)
            self.sound_timer = self.v[x]
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF01E: # Set I = I + Vx (FX1E)
            self.i += self.v[x]
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF029: # Set I = location of sprite for digit Vx (FX29)
            self.i = self.v[x] * 5
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF033: # Store BCD representation of Vx in memory locations I, I+1, and I+2 (FX33)
            self.memory[self.i] = self.v[x] // 100
            self.memory[self.i + 1] = (self.v[x] // 10) % 10
            self.memory[self.i + 2] = self.v[x] % 10
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF055: # Store registers V0 through Vx in memory starting at location I (FX55)
            for i in range(x + 1):
                self.memory[self.i + i] = self.v[i]
            self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF065: # Read registers V0 through Vx from memory starting at location I (FX65)
            for i in range(x + 1):
                self.v[i] = self.memory[self.i + i]
            self.pc += 2
        else:
            print(f"Unknown opcode: {hex(self.opcode)}")
            self.running = False

    def draw_graphics(self):
        self.screen.fill((0, 0, 0))
        for y in range(32):
            for x in range(64):
                if self.display[x + y * 64] == 1:
                    pg.draw.rect(self.screen, (255, 255, 255), (x * 10, y * 10, 10, 10))
 
        # print debug info
        pg.display.set_caption(f"CHIP-8 Emulator - FPS: {int(self.clock.get_fps())}")

        pg.display.flip()

    def set_keys(self):
        keys = pg.key.get_pressed()
        self.keys = [0] * 16

        key_mapping = {
            pg.K_1: 0x1,
            pg.K_2: 0x2,
            pg.K_3: 0x3,
            pg.K_4: 0xC,
            pg.K_q: 0x4,
            pg.K_w: 0x5,
            pg.K_e: 0x6,
            pg.K_r: 0xD,
            pg.K_a: 0x7,
            pg.K_s: 0x8,
            pg.K_d: 0x9,
            pg.K_f: 0xE,
            pg.K_z: 0xA,
            pg.K_x: 0x0,
            pg.K_c: 0xB,
            pg.K_v: 0xF
        }

        for key, value in key_mapping.items():
            if keys[key]:
                self.keys[value] = 1

    # sound and delay timers
    def timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1

        if self.sound_timer > 0:
            if self.sound_timer == 1:
                winsound.Beep(440, 500)
            self.sound_timer -= 1
            

    def run(self):
        pg.init()

        for i in range(80):
            self.memory[i] = self.fontset[i]

        while self.running:
            self.emulate_cycle()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
            self.set_keys()
            self.draw_graphics()
            self.timers()
            self.clock.tick(120)

        pg.quit()
        sys.exit()

if __name__ == "__main__":
    chip8 = Chip8()
    chip8.load_rom(rom_path)
    chip8.run()