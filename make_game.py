class makegame:
    def __init__(self):
        self.gametime = 30
        self.gamedifficulty = 1
        self.score = 0
             
    def reset(self):
        self.score = 0
        return(self.score)
        
    def printscore(self):
        print('The current score is: ' + str(self.currentscore))
        
    def incscore(self, points):
        self.currentscore += points
        
