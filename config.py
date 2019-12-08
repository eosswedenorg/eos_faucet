
# paste your testnet account (to create accounts, transfer tokens) name
ACCOUNT = ""

TOKEN="EOS"

# Set the permission to use when creating accounts/transfer tokens
# NOTE: if using custom permission you must set the following auths:
#   eosio::newaccount
#   eosio::delegatebw
#   eosio::buyrambytes
#   eosio::sellram
#   eosio.token::transfer
PERMISSION="active"

# paste your local wallet name
NAME = ""

# paste your local wallet password
PASSWD = ""

#  Server
# -------------------------

# What port http should be served on.
HTTP_LISTEN_PORT = 80

#  Rate Limit
# -------------------------

# account creation (per ip)
RATE_LIMIT_ACCOUNT_AMOUNT=1000 # 1000 accounts can be created. counter is cleared after 'RATE_LIMIT_ACCOUNT_EXPIRE' seconds.
RATE_LIMIT_ACCOUNT_EXPIRE=24 * 60 * 60 # expire after 24h (this value is represented in seconds)

# token transfer (per ip)
RATE_LIMIT_TOKEN_AMOUNT=1000 # 1000 tokens can be sent. counter is cleared after 'RATE_LIMIT_TOKEN_EXPIRE' seconds.
RATE_LIMIT_TOKEN_EXPIRE=24 * 60 * 60 # expire after 24h (this value is represented in seconds)
