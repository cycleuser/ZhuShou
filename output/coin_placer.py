from board import Board

# Coin placer class implementation
class CoinPlacer:
    def place_coin(self, position):
        # Validate the coin position
        if position in self.board.get_board_state():
            raise ValueError('Coin already placed at this position')
        # Place the coin
        self.board.update_board(position)

    def validate_coin_position(self, position):
        # Check if the position is valid
        if position < 0 or position >= len(self.board.get_board_state()):
            raise ValueError('Invalid position')
        # Check if the position is already occupied
        if position in self.board.get_board_state():
            raise ValueError('Coin already placed at this position')

    def get_board_state(self):
        return self.board.get_board_state()
