import tornado.ioloop
import tornado.web
import tornado.httpserver

import json
import requests

import eosapi
import config

import os
import re
from helpers import format_timespan
from helpers import remote_ip
import ratelimit

# ------------------------------------------------------------------------------------------
# ------ token transfer limiter

def token_limit_exceed(handler):
    write_json_response(handler, {'msg': 'You have reached the max amount of tokens for {}'.format(format_timespan(config.RATE_LIMIT_TOKEN_EXPIRE))}, 403)

token_account_amount_limiter = ratelimit.RateLimitType(
  name = "token_account_amount",
  amount = config.RATE_LIMIT_TOKEN_AMOUNT,
  expire = config.RATE_LIMIT_TOKEN_EXPIRE,
  identity = lambda h: h.request.uri,
  on_exceed = token_limit_exceed)


# ------------------------------------------------------------------------------------------
# ------ common functions

def write_json_response(handler, msg, code=200):
  handler.set_status(code)
  handler.set_header('Content-Type', 'application/json; charset=UTF-8')
  handler.write(msg)

def is_valid_account_name(account_name):
  return len(account_name) < 13 and len(account_name) > 0 and not re.search(r'[^a-z1-5\.]', account_name)

def is_valid_newaccount_name(account_name):
  return len(account_name) == 12 and not re.search(r'[^a-z1-5\.]', account_name)

def unlock_wallet():
  param = json.dumps([
    config.NAME,
    config.PASSWD
  ])
  response = requests.request("POST", eosapi.WALLET_UNLOCK, data=param)
  return response.status_code == 200

def is_wallet_locked():
  response = requests.request("POST", eosapi.WALLET_GET_PUBLIC_KEYS)
  return response.status_code != 200

def get_first_arg_name_from_request(request):
  args = request.arguments.keys()
  if len(args) == 1:
    return args[0]
  else:
    return ''

def account_exists(account_name):
  payload = json.dumps({'account_name': account_name})
  response = requests.request("POST", eosapi.GET_ACCOUNT, data=payload)
  if response.status_code == 200:
    ret = json.loads(response.text)
    return ret['account_name'] == account_name
  else:
    return False

def generate_key():
  ret = os.popen('cleos create key --to-console').read()
  array = ret.split()
  if len(array) == 6:
    return { 'private': array[2], 'public': array[5] }
  else:
    return None

def unlock_wallet_if_locked():
  unlocked = False
  if is_wallet_locked():
    print('wallet "{}" locked, try to unlock...'.format(config.NAME))
    if unlock_wallet():
      unlocked = True
      print('wallet "{}" unlocked!'.format(config.NAME))
    else:
      print('wallet "{}" unlock failed'.format(config.NAME))
  else:
    unlocked = True
  return unlocked


# ------------------------------------------------------------------------------------------
# ------ Get Token Handler

class GetTokenHandler(tornado.web.RequestHandler):

  def __init__(self, application, request, **kwargs):
    tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

  def _assembly_args(self, data):
    if data.has_key('account') and is_valid_account_name(data['account']):
      p = {}
      p['from']     = config.ACCOUNT
      p['to']       = data['account']
      p['quantity'] = config.SEND_TOKEN_QUANTITY
      p['symbol']   = config.TOKEN
      if data.has_key('memo'): p['memo']   = data['memo']
      else:                    p['memo']   = ''
      return p
    else:
      return None

  def _os_cmd_transfer(self, param):
    cmdline = 'cleos --url {} --wallet-url {} transfer {} {} "{} {}" {} -p {}@{}'.format(eosapi.NODEOS_URL, eosapi.KEOSD_URL,
                                                                param['from'],
                                                                param['to'],
                                                                param['quantity'],
                                                                param['symbol'],
                                                                param['memo'],
                                                                config.ACCOUNT,
                                                                config.PERMISSION)
    result = os.system(cmdline)
    return result == 0

  def _make_transfer(self, p):
    if unlock_wallet_if_locked():
      return self._os_cmd_transfer(p)
    else:
      return False

  def _handle(self, data):
    param = self._assembly_args(data)
    if param:
      if self._make_transfer(param):
        token_account_amount_limiter.increase_amount(param['quantity'], self)
        write_json_response(self, {'msg': 'succeeded'})
      else:
        failmsg = {'msg': 'transaction failed, possible reason: account does not exist'}
        write_json_response(self, failmsg, 400)
    else:
      fmtmsg = {'msg':'please use request with URL of format: http://<your_server_ip>/get_token?valid_account_name'}
      write_json_response(self, fmtmsg, 400)

  @ratelimit.limit_by(token_account_amount_limiter)
  def post(self):
    data = {'account': get_first_arg_name_from_request(self.request)}
    # data = json.loads(self.request.body.decode())
    self._handle(data)

  @ratelimit.limit_by(token_account_amount_limiter)
  def get(self):
    data = {'account': get_first_arg_name_from_request(self.request)}
    self._handle(data)


# ------------------------------------------------------------------------------------------
# ------ account creation limiter

def newaccount_limit_exceed(handler):
    write_json_response(handler, {'msg': 'You have reached the max amount of account creation for {}'.format(format_timespan(config.RATE_LIMIT_ACCOUNT_EXPIRE))}, 403)

newaccount_ip_amount_limiter = ratelimit.RateLimitType(
  name = "newaccount_ip_amount",
  amount = config.RATE_LIMIT_ACCOUNT_AMOUNT,
  expire = config.RATE_LIMIT_ACCOUNT_EXPIRE,
  identity = lambda h: remote_ip(h.request),
  on_exceed = newaccount_limit_exceed)


# ------------------------------------------------------------------------------------------
# ------ Create Account Handler

class CreateAccountHandler(tornado.web.RequestHandler):

  def __init__(self, application, request, **kwargs):
    tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

  def _assembly_args(self, account_name, owner_key, active_key):
    p = {
      'creator':        config.ACCOUNT,
      'account':        account_name,
      'owner_key':      owner_key,
      'active_key':     active_key,
      'stake-cpu':      '1 ' + config.TOKEN,
      'stake-net':      '1 ' + config.TOKEN,
      'buy-ram-kbytes': 8
    }
    return p

  def _os_cmd_create_account(self, p):
    cmdline = 'cleos --url {} --wallet-url {} system newaccount --stake-net \'{}\' --stake-cpu \'{}\' --buy-ram-kbytes {} {} {} {} {} -p {}@{}'.format(
      eosapi.NODEOS_URL, eosapi.KEOSD_URL,
      p['stake-net'],
      p['stake-cpu'],
      p['buy-ram-kbytes'],
      p['creator'],
      p['account'],
      p['owner_key'],
      p['active_key'],
      config.ACCOUNT,
      config.PERMISSION
    )
    result = os.system(cmdline)
    return result == 0

  def _create_account(self, p):
    if unlock_wallet_if_locked():
      return self._os_cmd_create_account(p)
    else:
      return False

  def _handle(self, request):
    name = get_first_arg_name_from_request(request)

    if not is_valid_newaccount_name(name):
      failmsg = {'msg': 'failed, unsupported account name \'{}\''.format(name)}
      write_json_response(self, failmsg, 400)
      return

    if account_exists(name):
      failmsg = {'msg': 'failed, account \'{}\' exists already'.format(name)}
      write_json_response(self, failmsg, 400)
      return

    owner_key = generate_key()
    active_key = generate_key()
    if owner_key and active_key:
      p = self._assembly_args(name, owner_key['public'], active_key['public'])
      if self._create_account(p):
        newaccount_ip_amount_limiter.increase_amount(1, self)
        retmsg = {
          'msg':      'succeeded',
          'account':  name,
          'keys':     { 'owner_key':  owner_key, 'active_key': active_key }
        }
        write_json_response(self, retmsg)
      else:
        failmsg = {'msg': 'failed, failed to create account'}
        write_json_response(self, failmsg, 400)
    else:
      failmsg = {'msg': 'failed, failed to generate keys'}
      write_json_response(self, failmsg, 400)

  @ratelimit.limit_by(newaccount_ip_amount_limiter)
  def post(self):
    self._handle(self.request)

  @ratelimit.limit_by(newaccount_ip_amount_limiter)
  def get(self):
    self._handle(self.request)


# ------------------------------------------------------------------------------------------
# ------ service app

def make_app():
  return tornado.web.Application([
    (r"/get_token", GetTokenHandler),
    (r"/create_account", CreateAccountHandler),
  ])

if __name__ == "__main__":
  app = make_app()
  server = tornado.httpserver.HTTPServer(app)
  server.bind(config.HTTP_LISTEN_PORT)
  server.start(0)
  tornado.ioloop.IOLoop.current().start()
