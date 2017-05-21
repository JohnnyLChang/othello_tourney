import socketio
import eventlet
from multiprocessing import Process, Value, Pipe
import os
import sys
import importlib
import logging as log
import time
import ctypes

from othello_admin import *

ailist_filename = '/web/activities/othello/static/ai_port_info.txt'
log.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=log.DEBUG)

class GameManager(socketio.Server):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.games = dict()
        self.pipes = dict()
        self.procs = dict()
        self.name2strat = dict()
        self.on('connect', self.create_game)
        self.on('prequest', self.start_game)
        self.on('disconnect', self.delete_game)
        self.on('refresh', self.refresh_game)
        self.on('movereply', self.send_move)
                

    def create_game(self, sid, environ):
        log.info('Client '+sid+' connected')
        self.games[sid] = GameRunner(self.name2strat)

    def start_game(self, sid, data):
        log.info('Client '+sid+' requests game '+str(data))
        parent_conn, child_conn = Pipe()

        if data['tml'].isdigit():
            timelimit = int(data['tml'])
        else:
            timelimit = 5
        
        self.games[sid].set_names(data['black'], data['white'])
        self.pipes[sid] = parent_conn
        self.procs[sid] = Process(target=self.games[sid].run_game, args=(child_conn, timelimit))

        self.procs[sid].start()
        log.debug('Started game for '+sid)

    def delete_game(self, sid):
        log.info('Client '+sid+' disconnected')
        if self.procs[sid].is_alive():
            self.procs[sid].terminate()
            
        del self.procs[sid]
        del self.pipes[sid]
        del self.games[sid]

    def refresh_game(self, sid, data):
        while self.pipes[sid].poll():
            mtype, data = self.pipes[sid].recv()
            log.debug(mtype+' '+str(data))
            if mtype == 'board':
                self.emit('reply', data=data, room=sid)
            elif mtype == 'getmove':
                self.emit('moverequest', data=dict(), room=sid)

    def send_move(self, sid, data):
        move = int(data['move'])
        self.pipes[sid].send(move)
        log.info('Recieved move '+str(move)+' from '+sid)

    def get_possible_files(self):
        folders = os.listdir(os.getcwd()+'/private/Students')
        log.debug('Listed Student folders successfully')
        return ['private.Students.'+x+'.strategy' for x in folders if x != '__pycache__']

    def spin_up_threads(self):
        files = self.get_possible_files()
        buf = ''
        
        old_path = os.getcwd()
        old_sys = sys.path
        
        for x in range(len(files)):
            
            name = files[x].split('.')[2]
            
            path = old_path+'/private/Students/'+name
            os.chdir(path)
            
            sys.path = [path] + old_sys
            
            #self.name2strat[name] = importlib.import_module(files[x]).Strategy().best_strategy
            #log.debug('Imported strategy '+name)
            
            buf += name +'\n'
            
        log.info('All strategies read')
        
        #self.name2strat['you'] = None
        
        pfile = open(ailist_filename, 'w')
        pfile.write(buf[:-1])
        pfile.close()
        
        log.info('Wrote names to webserver file')
        log.debug('Filename: '+ailist_filename)

class GameRunner:
    def __init__(self, name2strat):
        self.core = Strategy()
        self.name2strat = name2strat

    def set_names(self, nameA, nameB):
        print(self.name2strat)
        self.BLACK = nameA
        self.WHITE = nameB
        self.BLACK_STRAT = RemoteAI(nameA)
        self.WHITE_STRAT = RemoteAI(nameB)
        log.debug('Set names to '+nameA+' '+nameB)

    def run_game(self, conn, timelimit):
        board = self.core.initial_board()
        player = core.BLACK
	
        self.BLACK_STRAT.make_connection(timelimit)
        self.WHITE_STRAT.make_connection(timelimit)
        
        strategy = {core.BLACK: self.BLACK_STRAT, core.WHITE: self.WHITE_STRAT}
        names = {core.BLACK: self.BLACK, core.WHITE: self.WHITE}

        conn.send(('board', {'bSize':'8',
                                 'board':''.join(board),
                                 'black':self.BLACK, 'white':self.WHITE,
                                 'tomove':player
                                 }
            ))

        forfeit = False

        while player is not None and not forfeit:
            if strategy[player] is None:
                move = 0
                
                # clear out queue from moves sent by rouge client
                while conn.poll(): temp=conn.recv()
                
                while not self.core.is_legal(move, player, board):
                    conn.send(('getmove', 0))
                    move = conn.recv()
                    log.debug('Game recieved move '+str(move))

                log.debug('Move '+str(move)+' determined legal')
            else:
                move = strategy[player].get_move(board, player)
                log.debug('Strategy '+names[player]+' returned move '+str(move))

            if not self.core.is_legal(move, player, board):
                forfeit = True
                if player == core.BLACK:
                    black_score = -100
                else:
                    black_score = 100
                continue

            board = self.core.make_move(move, player, board)
            player = self.core.next_player(board, player)
            black_score = self.core.score(core.BLACK, board)

            log.debug(self.core.print_board(board))

            conn.send(('board', {'bSize':'8',
                                 'board':''.join(board),
                                 'black':self.BLACK, 'white':self.WHITE,
                                 'tomove':player
                                 }
            ))
