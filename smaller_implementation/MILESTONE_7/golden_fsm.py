class GoldenFSM:
    def __init__(self):
        self.state = 0
        
    def reset(self):
        self.state = 0
        
    def step(self, opcode):
        if self.state == 0: # IDLE
            self.state = 1
        elif self.state == 1: # FETCH
            self.state = 2
        elif self.state == 2: # DECODE
            if opcode == 0x33:
                self.state = 3
            elif opcode in [0x03, 0x23]:
                self.state = 4
            elif opcode == 0x7F:
                self.state = 7
            else:
                self.state = 1
        elif self.state == 3: # EXEC_ALU
            self.state = 6
        elif self.state == 4: # EXEC_MEM
            self.state = 5
        elif self.state == 5: # MEM_WAIT
            if opcode == 0x00:
                self.state = 6 # Exit wait
            else:
                self.state = 5 # Hold in wait
        elif self.state == 6: # WRITEBACK
            self.state = 1
        elif self.state == 7: # TRAP
            self.state = 7
        return self.state
