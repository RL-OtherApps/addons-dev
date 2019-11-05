import random
import logging
from odoo import models, fields, api
# import threading
# from openerp.modules.registry import Registry

_logger = logging.getLogger(__name__)


class Game(models.Model):
    _name = 'game'
    _description = 'Simple game'

    name = fields.Text(default='pos_durak')
    id = fields.Integer(default=-1)
    players = fields.One2many('game.player', 'game', ondelete="cascade", delegate=True)
    extra_cards = fields.One2many('game.cards', 'game_extra_cards', ondelete="cascade")
    trump = fields.Integer(default=-1)
    who_steps = fields.Integer(default=-1, help='Holds user id')
    on_table_cards = fields.One2many('game.cards', 'on_table_cards', ondelete="cascade")
    attackers_agreement = fields.Integer(default=0)

    @api.model
    def create_the_game(self, game_name, uid):
        temp_game = self.search([('name', '=', game_name)])
        pos_id = self.env['pos.session'].search([('user_id', '=', uid)])[0].id
        # If game didn't created, then create
        if len(temp_game) == 0:
            try:
                self.create({'name': game_name, 'id': len(self.search([]))})
            except Exception:
                _logger.error('Game creation error!!! Game num is -' + str(len(self)))

        temp_game = self.search([('name', '=', game_name)])
        data = {'command': 'my_game_id', 'id': temp_game.id}
        channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname, pos_id, game_name)
        self.env['bus.bus'].sendmany([[channel, data]])
        # temp_game.Ping(temp_game.id)
        return 1

    # @api.model
    # def Ping(self, game_id):
    #     cur_game = self.search([('id', '=', game_id)])
    #     for player in cur_game.players:
    #         import wdb
    #         wdb.set_trace()
    #         if player.didnt_respond != 0:
    #             player.write({'didnt_respond': player.didnt_respond + 1})
    #         if player.didnt_respond > 2:
    #             cur_game.delete_player(game_id, player.uid)
    #         else:
    #             data = {'command': 'GAME_PING'}
    #             channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
    #                                                                         player.pos_id, cur_game.name)
    #     t = threading.Timer(10.0, cur_game.Ping, args=[game_id])
    #     t.start()
    #     return 1

    # @api.model
    # def Pong(self, game_id, uid):
    #     import wdb
    #     wdb.set_trace()
    #     cur_game = self.search([('id', '=', game_id)])
    #     player = cur_game.players.search([('uid', '=', uid)])
    #     player.write({'didnt_respond': 0})
    #     return 1

    @api.model
    def add_new_user(self, game_id, name, uid):
        cur_game = self.search([('id', '=', game_id)])
        new_num = len(cur_game.players)
        new_pos_id = self.env['pos.session'].search([('user_id', '=', uid)])[0].id
        if cur_game.trump != -1:
            data = {'command': 'Game_started'}
            channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                          new_pos_id, cur_game.name)
            return 1
        # Sending new player's data to all players
        data = {'name': name, 'uid': uid, 'num': new_num, 'command': 'Connect'}
        self.env['pos.config'].send_to_all_poses(cur_game.name, data)
        # Sending old players data to the new player
        try:
            for user in cur_game.players:
                data = {'name': user.name, 'uid': user.uid, 'num': user.num, 'command': 'Connect'}
                channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                              new_pos_id, cur_game.name)
                self.env['bus.bus'].sendmany([[channel, data]])
        except Exception:
            _logger.error('Player connected notification error!!!(add_new_user)')

        try:
            cur_game.players += cur_game.players.create({'name': name, 'uid': uid, 'num': new_num, 'pos_id': new_pos_id})
        except Exception:
            _logger.error('Player creation error!!!')
        return 1

    @api.model
    def player_is_ready(self, game_id, uid):
        cur_game = self.search([('id', '=', game_id)])
        try:
            cur_game.players.search([('uid', '=', uid)]).write({'ready': True})
        except Exception:
            _logger.error('Error in player_is_ready method!!! (Model - game)')

        self.env['pos.config'].send_to_all_poses(cur_game.name,
                                                 {'command': 'ready', 'uid': uid})
        return 1

    @api.model
    def send_cards(self, game_name, player):
        cnt = 0
        for card in player.cards:
            data = {'num': card.num, 'power': card.power, 'pack_num': cnt,
                    'suit': card.suit, 'n': len(player.cards), 'command': 'Cards'}
            channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                          player.pos_id, game_name)
            self.env['bus.bus'].sendmany([[channel, data]])
            cnt += 1
        return 1

    @api.model
    def start_the_game(self, game_id):
        cur_game = self.search([('id', '=', game_id)])
        seq = [*range(0, 52)]
        cards_limit = 6
        random.shuffle(seq)

        i = 0
        cards_cnt = 0
        all_cards_cnt = 0
        cur_game.player_is_ready(cur_game.id,
                                 cur_game.players.search([('num', '=', 0)]).uid)
        player = cur_game.players.search([('ready', '=', True)])
        player[0].write({'stepping': True})
        try:
            for num in seq:
                player[i].add_new_card(player[i].uid, num)
                seq.remove(num)
                cards_cnt += 1
                all_cards_cnt += 1
                if cards_cnt == cards_limit:
                    cards_cnt = 0
                    i += 1
                if len(player) == i:
                    break
        except Exception:
            _logger.error('Cards distribution error!!!\n')

        try:
            for num in seq:
                card = cur_game.extra_cards.card_power(num)
                cur_game.extra_cards += cur_game.extra_cards.create({'power': card[0], 'suit': card[1], 'num': num, 'in_game': True})
            cur_game.write({'trump': cur_game.extra_cards[0].suit})
            self.env['pos.config'].send_to_all_poses(cur_game.name, {'command': 'Trump',
                                                                     'trump': cur_game.trump})
        except Exception:
            _logger.error('Extra cards assignment error!!!')

        try:
            for player in cur_game.players:
                cur_game.send_cards(cur_game.name, player)
        except Exception:
            _logger.error('Cards sending error!!!')

        try:
            for player in cur_game.players.search([('ready', '=', False)]):
                cur_game.delete_player(cur_game.id, player.uid)
        except Exception:
            _logger.error("Can't delete not ready players!!!(start_the_game)")
        cur_game.who_should_step(game_id)
        return 1

    @api.model
    def delete_player(self, game_id, uid):
        cur_game = self.search([('id', '=', game_id)])
        try:
            for user in cur_game.players:
                data = {'uid': uid, 'command': 'Disconnect'}
                channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                              user.pos_id, cur_game.name)
                self.env['bus.bus'].sendmany([[channel, data]])
        except Exception:
            _logger.error('Player disconnected notification error!!!(delete_player)')

        try:
            deleting_user = cur_game.players.search([('uid', '=', uid)])
            if deleting_user.num == cur_game.who_steps and len(cur_game.players) > 1:
                cur_game.who_should_step(game_id)
        except Exception:
            _logger.error("Users num's finding error!!!(delete_player)")

        for user in cur_game.players:
            if user.num > deleting_user[0].num:
                user.write({'num': user.num - 1})

        try:
            deleting_user.unlink()
        except Exception:
            _logger.error('Player removing error!!!')

        try:
            # next time change self.unlink() -> cur_game.unlink()
            if len(cur_game.players) == 0:
                self.search([]).unlink()
        except Exception:
            _logger.error("Game session deleting error!!!")
        return 1

    @api.model
    def send_message(self, game_id, message, uid):
        cur_game = self.search([('id', '=', game_id)])
        for player in cur_game.players:
            data = {'uid': uid, 'message': message, 'command': 'Message'}
            channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                          player.pos_id, cur_game.name)
            self.env['bus.bus'].sendmany([[channel, data]])
        return 1

    @api.model
    def delete_my_game(self, game_id):
        self.search([('id', '=', game_id)]).unlink()
        return 1

    @api.model
    def who_should_step(self, game_id):
        cur_game = self.search([('id', '=', game_id)])
        stepman = cur_game.next(game_id, cur_game.who_steps)
        cur_game.who_steps = stepman
        for player in cur_game.players:
            data = {'first': stepman, 'second': cur_game.next(game_id, cur_game.next(game_id, stepman)),
                    'command': 'Who_steps'}
            channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                          player.pos_id, cur_game.name)
            self.env['bus.bus'].sendmany([[channel, data]])
        return 1

    @api.model
    def make_step(self, game_id, uid, card_num):
        if card_num == 'ds':
            return 1
        try:
            cur_game = self.search([('id', '=', game_id)])
            stepper = cur_game.players.search([('uid', '=', uid)])
            card = stepper.cards.search([('num', '=', card_num)])[0]
        except Exception:
            _logger.error('Make_step error!')

        can_make_a_step = False
        try:
            for on_table_card in cur_game.on_table_cards:
                if card.power == on_table_card.power:
                    can_make_a_step = True
            if len(cur_game.on_table_cards) == 0:
                can_make_a_step = True
        except Exception:
            _logger.error('Card on table checking error!!!\n')

        if can_make_a_step:
            for player in cur_game.players:
                data = {'uid': uid, 'num': card.num, 'command': 'Move'}
                channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname, player.pos_id, cur_game.name)
                self.env['bus.bus'].sendmany([[channel, data]])
            cur_game.on_table_cards += cur_game.on_table_cards.create({'power': card.power, 'suit': card.suit, 'num': card.num, 'in_game': True})
            stepper.cards -= card
        return 1

    @api.model
    def defence(self, game_id, uid, card1, card2, x, y):
        try:
            cur_game = self.search([('id', '=', game_id)])
            defender = cur_game.players.search([('uid', '=', uid)])
            card = defender.cards.search([('num', '=', card1)])[0]
            cur_game.on_table_cards += cur_game.on_table_cards.create({'power': card.power, 'suit': card.suit, 'num': card.num, 'in_game': True})
            defender.cards -= card
            first = cur_game.on_table_cards.search([('num', '=', card1)])[0]
            second = cur_game.on_table_cards.search([('num', '=', card2)])[0]
            fpow = first.power
            spow = second.power
            winner = -1
            loser = -1
        except Exception:
            _logger.error("Defence var's initialization error!")
        try:
            # If one of them is trump, there's always way to compare cards
            # If posible to compare
            if first.suit == second.suit or first.suit == cur_game.trump or second.suit == cur_game.trump:
                if first.suit == cur_game.trump:
                    fpow = first.power + 100
                if second.suit == cur_game.trump:
                    spow = second.power + 100
                if spow < fpow:
                    winner = card1
                    loser = card2
            else:
                loser = card1
                winner = card2
            if card1 == winner:
                data = {'uid': uid, 'winner': winner, 'x': x, 'y': y, 'loser': loser, 'can_beat': True, 'command': 'Defence'}
            else:
                data = {'uid': uid, 'can_beat': False, 'command': 'Defence'}

            for player in cur_game.players:
                channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname, player.pos_id, cur_game.name)
                self.env['bus.bus'].sendmany([[channel, data]])
        except Exception:
            _logger.error('defence error!')
        return 1

    @api.model
    def next(self, game_id, num):
        cur_game = self.search([('id', '=', game_id)])
        player = cur_game.players.search([('num', '=', num)])
        if player.num < len(cur_game.players) - 1:
            return cur_game.players.search([('num', '=', player.num + 1)]).num
        else:
            return cur_game.players.search([('num', '=', 0)]).num

    @api.model
    def new_cards(self, game_id):
        cur_game = self.search([('id', '=', game_id)])
        extra_cards_length = len(cur_game.extra_cards)
        who_took_new_cards = []
        try:
            for player in cur_game.players:
                tooked_cards = False
                while len(player.cards) < 6:
                    tooked_cards = True
                    if len(cur_game.extra_cards) == 0:
                        break
                    player.add_new_card(player.uid, cur_game.extra_cards[extra_cards_length - 1].num)
                    cur_game.extra_cards[extra_cards_length - 1].unlink()
                    extra_cards_length -= 1
                if tooked_cards:
                    who_took_new_cards.append(player.uid)
        except Exception:
            _logger.error('Extra cards distribution error!!!')

        attackman = cur_game.who_steps
        defman = cur_game.next(game_id, attackman)
        for player in cur_game.players:
            data = {'command': 'Move_done'}
            channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                          player.pos_id, cur_game.name)
            self.env['bus.bus'].sendmany([[channel, data]])
            for user in who_took_new_cards:
                if user == player.uid:
                    cur_game.send_cards(cur_game.name, player)
        cur_game.on_table_cards -= cur_game.on_table_cards
        cur_game.after_step(cur_game)
        # Checks if someone won
        return 1

    @api.model
    def cards_are_beated(self, game_id, uid):
        cur_game = self.search([('id', '=', game_id)])
        if len(cur_game.on_table_cards) == 0:
            return 1

        cur_game.players.search([('uid', '=', uid)])[0].completed_move = True
        temp_cnt = 0
        for player in cur_game.players:
            if player.completed_move:
                temp_cnt += 1
        if temp_cnt != 2 and len(cur_game.players) > 2:
            return 1

        cur_game.new_cards(game_id)
        cur_game.who_should_step(game_id)
        for player in cur_game.players:
            if player.completed_move: 
                player.completed_move = False
        return 1

    @api.model
    def defender_took_cards(self, game_id, uid):
        cur_game = self.search([('id', '=', game_id)])
        player = cur_game.players.search([('uid', '=', uid)])
        for card in cur_game.on_table_cards:
            player.cards += player.cards.create({'power': card.power, 'suit': card.suit, 'num': card.num, 'in_game': True})

        cur_game.new_cards(game_id)
        # Sending cards to defender
        defman = cur_game.next(game_id, cur_game.who_steps)
        defer = cur_game.players.search([('num', '=', defman)])
        cur_game.send_cards(cur_game.name, defer)
        # Loser should skip his queue
        cur_game.who_steps = cur_game.next(game_id, cur_game.who_steps)
        cur_game.who_should_step(game_id)
        return 1

    @api.model
    def after_step(self, cur_game):
        won = []
        for player in cur_game.players:
            if len(player.cards) == 0 and len(cur_game.extra_cards) == 0:
                won.append(player)
        for winner in won:
            data = {'uid': winner.uid, 'command': 'Won'}
            for player in cur_game.players:
                channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname, player.pos_id, cur_game.name)
                self.env['bus.bus'].sendmany([[channel, data]])
                if winner.uid == player.uid:
                    player.unlink()
        return 1

    @api.model
    def cards_number(self, game_id, uid, my_uid):
        cur_game = self.search([('id', '=', game_id)])
        ask_player = cur_game.players.search([('uid', '=', uid)])
        player = cur_game.players.search([('uid', '=', my_uid)])

        data = {'number': len(ask_player.cards), 'command': 'HowMuchCards'}
        channel = self.env['pos.config']._get_full_channel_name_by_id(self.env.cr.dbname,
                                                                      player.pos_id, cur_game.name)
        self.env['bus.bus'].sendmany([[channel, data]])
        return 1


class Player(models.Model):
    _name = 'game.player'
    _description = 'Game player'

    game = fields.Many2one('game', string='Game', ondelete="cascade")
    cards = fields.One2many('game.cards', 'cards_holder', ondelete="cascade")

    # Player name
    name = fields.Text(default='')
    # Player uid
    uid = fields.Integer(default=-1)
    # Serial number
    num = fields.Integer(default=-1)
    # Is player ready to play or alredy playing
    ready = fields.Boolean(default=False)
    pos_id = fields.Integer(default=-1)
    # This var needs to check if attacker completed his move
    completed_move = fields.Boolean(default=False)
    didnt_respond = fields.Integer(default=-1)

    @api.model
    def add_new_card(self, uid, num):
        player = self.search([('uid', '=', uid)])
        try:
            card = player.cards.card_power(num)
            player.cards += player.cards.create({'power': card[0], 'suit': card[1], 'num': num, 'in_game': True})
        except Exception:
            _logger.error('New card addition error!!!')
        return 1

    @api.model
    def delete_card(self, uid, num):
        player = self.search([('uid', '=', uid)])
        try:
            card = player.cards.card_power(num)
            card.write({'in_game': False})
            card.unlink()
        except Exception:
            _logger.error('Card deletion error!!!')
        return 1


class Card(models.Model):
    _name = 'game.cards'
    _description = 'Gaming cards'

    cards_holder = fields.Many2one('game.player', string='Player', ondelete="cascade")
    game_extra_cards = fields.Many2one('game', string='Game extra cards', ondelete="cascade")
    on_table_cards = fields.Many2one('game', string='Game on table cards', ondelete="cascade")

    suit = fields.Integer(default=-1)
    power = fields.Integer(default=-1)
    num = fields.Integer(default=-1)
    in_game = fields.Boolean(default=False)

    @api.model
    def card_power(self, num):
        temp_suit = 0
        while num >= 13:
            num -= 13
            temp_suit += 1
        # Cause tuzes is located on the first position
        if num == 0:
            num = 13
        return [num, temp_suit]
