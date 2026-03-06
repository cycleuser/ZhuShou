from board import Board

# UI interface implementation
class BoardDisplay:
    def render_board(self):
        # Display the current board state
        board_state = self.board.get_board_state()
        print(f'Board:
{board_state}')

    def rules_display(self):
        # Display the game rules
        print('Game Rules:
1. Place coins to form a line of 5.
2. Win when five in a row.
3. Game ends when board is full.
4. Score is tracked and updated.
5. Game state is saved and loaded.
6. UI is interactive with the board.
7. Support for desktop and mobile platforms.
8. Memory-efficient for large boards.
9. High-performance for concurrent use.
10. Cross-platform compatibility.
11. Error handling for invalid positions and board states.
12. Real-time updates to the UI interface.
13. Clean, readable code for developers.
14. Proper documentation for users.
15. All dependencies are properly imported and used.
