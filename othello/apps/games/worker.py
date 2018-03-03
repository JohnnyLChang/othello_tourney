from django.conf import settings
import logging as log
import sys, os, io
import shlex, traceback
import multiprocessing as mp

from .utils import get_strat
from .othello_admin import Strategy
from .othello_core import BLACK, WHITE, EMPTY
ORIGINAL_SYS = sys.path[:]

"""
Plan:
use django channel consumer for bg process
have that consumer use this runner to create 2 long running jailed processes beside it
this class will take consumer as an arg in order to send channel api messages
"""

class GameRunner:
    black = None
    white = None
    timelimit = 5
    emit_func = lambda *args: print(args)

    def __init__(self):
        student_folder = settings.MEDIA_ROOT
        folders = os.listdir(student_folder)
        log.debug('Listed student folders successfully')
        self.possible_names =  {x for x in folders if \
            x != '__pycache__' and \
            os.path.isdir(os.path.join(student_folder, x))
        }
    
    def run(self, comm_queue):
        """
        Main loop used to run the game in.
        Does not have multiprocess support yet.
        """
        print("Yay i have started to run {} vs {} ({})".format(
            self.black,
            self.white,
            self.timelimit
        ))
        
        strats = dict()
        do_start_game = True
        
        if self.black not in self.possible_names:
            if self.black == settings.OTHELLO_AI_HUMAN_PLAYER:
                strats[BLACK] = None
            else:
                self.emit_func({
                    "type": "game.error",
                    "error": "{} is not a valid AI name".format(self.black)
                })
                do_start_game = False
        else:
            strat = JailedRunnerCommunicator(self.black)
            strat.start()
            strats[BLACK] = strat
        
        if self.white not in self.possible_names:
            if self.white == settings.OTHELLO_AI_HUMAN_PLAYER:
                strats[WHITE] = None
            else:
                self.emit_func({
                    "type": "game.error",
                    "error": "{} is not a valid AI name".format(self.white)
                })
                do_start_game = False
        else:
            strat = JailedRunnerCommunicator(self.white)
            strat.start()
            strats[WHITE] = strat
        print("Inited strats")
        core = Strategy()
        player = BLACK
        board = core.initial_board()
        names = {
            BLACK: self.black,
            WHITE: self.white,
        }
        
        self.emit_func({
            "type": "board.update",
            "board": ''.join(board),
        })
        forfeit = False
        print("All things done")
        return "It turns out django channels pauses for each channel to finish executing, so I WILL need to run all this inside a process. Hopefully that's not too bad"
        while player is not None and not forfeit:
            player, forfeit, board = self.do_game_tick(comm_queue, core, board, player, strats, names)
            
        winner = EMPTY
        if forfeit:
            winner = core.opponent(player)
        else:
            winner = (EMPTY, BLACK, WHITE)[core.final_value(BLACK, board)]
        self.emit_func({
            "type": "board.update",
            "board": ''.join(board),
        })
        self.emit_func({
            "type": "game.end",
            "winner": winner,
            "forfeit": forfeit,
        })
        
    def do_game_tick(self, comm_queue, core, board, player, strats, names):
        """
        Runs one move in a game, handling all the board flips and game-ending edge cases.
        
        If a strat is `None`, it calls out for the user to input a move. Otherwise, it runs the strategy provided.
        """
        print("Ticking game")
        strat = strats[player]
        move = -1
        errs = None
        if strat is None:
            self.emit_func({"type":"move.request"})
            move = comm_queue.get()
        else:
            move, errs = strat.get_move(board, player, self.timelimit)
            
        if not core.is_legal(move, player, board):
            self.emit_func({
                'type': "game.error",
                'error': "{}: {} is an invalid move for board {}\nMore info:\n{}".format(names[player], move, ''.join(board), errs)
            })
            forfeit = True
            return player, forfeit, board
            
        board = core.make_move(move, player, board)
        self.emit_func({
            "type": "board.update", 
            "board": ''.join(board),
        })
        return player, False, board
    

class LocalRunner:
    def __init__(self, ai_name):
        self.name = ai_name
        self.strat = None
        self.new_path = self.old_path = os.getcwd()
        self.new_sys = self.old_sys = ORIGINAL_SYS
        self.strat, self.new_path, self.new_sys = get_strat(self.name)
    
    def strat_wrapper(self, board, player, best_shared, running, pipe_to_parent):
        try:
            self.strat(board, player, best_shared, running)
            pipe_to_parent.send(None)
        except:
            pipe_to_parent.send(traceback.format_exc())

    def get_move(self, board, player, timelimit, kill_event):
        best_shared = mp.Value("i", -1)
        running = mp.Value("i", 1)
        
        os.chdir(self.new_path)
        sys.path = self.new_sys
        to_child, to_self = Pipe()
        try:
            p = mp.Process(target=self.strat_wrapper, args=("".join(list(board)), player, best_shared, running, to_child))
            p.start()
            if kill_event:
                kill_event.wait(timelimit)
                p.join(0.01)
            else:
                p.join(timelimit)
            if p.is_alive():
                running.value = 0
                p.join(0.01)
                if p.is_alive(): p.terminate()
            move = best_shared.value
            if to_self.poll():
                err = to_self.recv()
                log.info("There is an error")
            else:
                err = None
                log.info("There was no error thrown")
            return move, err
        except:
            traceback.print_exc()
            return -1, 'Server Error'
        finally:
            os.chdir(self.old_path)
            sys.path = self.old_sys


class JailedRunner:
    """
    The class that is run in the subprocess to handle the games
    Keeps running until it is killed forcefully
    """
    
    AIClass = LocalRunner
    def __init__(self, ai_name):
        # I don't know what to put here yet
        self.strat = self.AIClass(ai_name)
    
    def handle(self, client_in, client_out, client_err):
        """
        Handles one incoming request for getting a move from the target AI
        given the current board, player to move, and time limit.
        
        client_in, client_out, and client_err are socket-like objects.
        input received on client_in, output sent out on client_out, any 
        errors the AI throws are sent on client_err
        """
        name = client_in.readline().strip()
        timelimit = client_in.readline().strip()
        player = client_in.readline().strip()
        board = client_in.readline().strip()
        log.debug("Got data {} {} {} {}".format(name, timelimit, player, board))
        
        if name in self.possible_names and \
           (player == oc.BLACK or player == oc.WHITE):

            try:
                timelimit = float(timelimit)
            except ValueError:
                timelimit = 5
            log.debug("Data is ok")
            # Now, we don't want any debug statements
            # messing up the output. So, we replace
            # sys.stdout temporarily
            
            #save_err = sys.stderr
            #sys.stderr = io.BytesIO()
            save_stdout = sys.stdout
            sys.stdout = io.TextIOWrapper(io.BytesIO())
            
            move, err = self.strat.get_move(board, player, timelimit, False)
            
            # And then put stdout back where we found it
            sys.stdout = save_stdout
            #sys.stderr = save_err
            if err is not None: client_err.write(err)
            
            log.debug("Got move {}".format(move))
            client_out.write(str(move)+"\n")
        else:
            log.debug("Data not ok")
            client_out.write("-1"+"\n")
        client_out.flush()
        client_err.flush()
        
    def run(self):
        while True:
            self.handle(sys.stdin, sys.stdout, sys.stderr)
            
class JailedRunnerCommunicator:
    """
    Class used to communicate with a jailed process.
    
    Standard usage:
    ai = JailedRunnerCommunicator(ai_name)
    ai.start()
    ...
    move, errors = ai.get_move(board, player, timelimit)
    if core.is_legal(board, move): core.make_flips(board, move)
    ...
    ai.stop()
    """
    def __init__(self, ai_name):
        self.name = ai_name
        self.proc = None
        
    def start(self):
        """
        Starts running the specified AI in a subprocess
        """
        command = settings.OTHELLO_AI_RUN_COMMAND.replace(settings.OTHELLO_AI_NAME_REPLACE, self.name)
        command_args = shlex.split(command)
        self.proc = subprocess.Popen(command_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, \
                                    universal_newlines=True, bufsize=1, cwd=settings.PROJECT_ROOT)

    def get_move(self, board, player, timelimit):
        """
        Gets a move from the running subprocess, providing it with all the data it
        needs to make a decision.
        
        Data format needs to be same as JailedRunner expects it, namely,
        b"duv\n5\n@\n?????..??o@?????\n"
        """
        data = self.name+"\n"+str(timelimit)+"\n"+player+"\n"+str(board)+"\n"

        log.debug('Started subprocess')
        self.proc.stdin.write(data.encode('utf-8'))
        self.proc.stdin.flush()
        outs = self.proc.stdout.readline()
        errs = self.proc.stderr.read()
        log.debug('Got move from subprocess')
        try:
            move = int(outs.decode('utf-8').split("\n")[0])
        except:
            traceback.print_exc()
            move = -1
        return move, errs.decode()
        
    def stop(self):
        """
        Stops the currently running subprocess.
        Will throw an error if the subprocess is not running.
        """
        self.proc.kill()
        self.proc = None
        
    def __del__(self):
        self.stop()
        super().__del__()